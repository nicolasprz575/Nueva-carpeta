import pyomo.environ as pyo

def build_model_caso3(data):

    DEPOT      = data["DEPOT"]
    CLIENTS    = data["CLIENTS"]
    STATIONS   = data.get("STATIONS", [])
    VEHICLES   = data["VEHICLES"]
    NODES      = data["NODES"]

    demanda    = data["demanda"]
    dist       = data["dist"]

    load_cap   = data["load_cap"]
    fuel_cap   = data.get("fuel_cap", {v: 1e9 for v in VEHICLES})
    fuel_eff   = data.get("fuel_efficiency", 8.0)
    fuel_price = data.get("fuel_price", {})
    fuel_price_depot = data.get("fuel_price_depot", 0.0)

    C_fixed = data["C_fixed"]
    C_km    = data["C_km"]
    C_time  = data.get("C_time", 0.0)

    max_weight = data.get("max_weight", {})

    TOLLS             = data.get("TOLLS", [])
    toll_base_rate    = data.get("toll_base_rate", {})
    toll_rate_per_ton = data.get("toll_rate_per_ton", {})
    toll_client       = data.get("toll_client", {})

    model = pyo.ConcreteModel()

    # ======================
    # Sets
    # ======================
    model.V = pyo.Set(initialize=VEHICLES)
    model.N = pyo.Set(initialize=NODES)
    model.C = pyo.Set(initialize=CLIENTS)
    model.S = pyo.Set(initialize=STATIONS)
    model.P = pyo.Set(initialize=TOLLS)

    # Arcs (completos sin loops)
    model.A = pyo.Set(initialize=[(i, j) for i in NODES for j in NODES if i != j])

    # ======================
    # Variables
    # ======================
    # x[v,i,j] = 1 si el vehículo v recorre el arco (i,j)
    model.x = pyo.Var(model.V, model.A, within=pyo.Binary)

    # u[v,n]: carga transportada al salir de n
    BIGL = max(load_cap.values()) if load_cap else 0.0
    model.u = pyo.Var(model.V, model.N, bounds=(0, BIGL))

    # f[v,n]: "estado" de combustible en n
    BIGF = max(fuel_cap.values()) if fuel_cap else 0.0
    if BIGF <= 0:
        BIGF = 1e6
    model.f = pyo.Var(model.V, model.N, bounds=(0, BIGF))

    # r[v,n]: combustible comprado en n
    model.r = pyo.Var(model.V, model.N, bounds=(0, BIGF))

    # t_weight[v,p]: peso (carga) relevante al pasar por peaje p
    BIGW = BIGL if BIGL > 0 else 1e5
    model.t_weight = pyo.Var(model.V, model.P, bounds=(0, BIGW))

    # ======================
    # Objetivo (lineal)
    # ======================
    def obj(m):
        # Distancia
        cost_dist = sum(
            m.x[v, i, j] * dist[(i, j)] * C_km
            for v in m.V for (i, j) in m.A
        )

        # Costo fijo: si el vehículo v sale del depósito (usa al menos una ruta desde el depósito)
        cost_fixed = sum(
            C_fixed * sum(m.x[v, DEPOT, j] for j in m.N if j != DEPOT)
            for v in m.V
        )

        # Costo de combustible comprado (simplificado)
        cost_refuel = 0.0
        for v in m.V:
            for n in m.N:
                price = fuel_price_depot
                if n in fuel_price:
                    price = fuel_price[n]
                cost_refuel += price * m.r[v, n]

        # Costo de peajes base (si se entra al cliente asociado)
        cost_tolls_base = 0.0
        for p in m.P:
            c_p = toll_client.get(p, None)
            if c_p is None or c_p == "":
                continue
            # si algún vehículo entra a c_p, se paga base rate (por vehículo que entra)
            for v in m.V:
                incoming = sum(m.x[v, i, c_p] for i in m.N if i != c_p)
                cost_tolls_base += toll_base_rate.get(p, 0.0) * incoming

        # Costo de peajes dependiente del peso (lineal en t_weight)
        cost_tolls_weight = 0.0
        for v in m.V:
            for p in m.P:
                rate = toll_rate_per_ton.get(p, 0.0)
                # asumimos que t_weight está en kg y dividimos por 1000 para pasarlo a ton
                cost_tolls_weight += rate * (m.t_weight[v, p] / 1000.0)

        return cost_dist + cost_fixed + cost_refuel + cost_tolls_base + cost_tolls_weight

    model.obj = pyo.Objective(rule=obj, sense=pyo.minimize)

    # ======================
    # Restricciones de visita
    # ======================

    # Cada cliente se visita EXACTAMENTE una vez en total (por algún vehículo)
    def out_degree(m, c):
        return sum(m.x[v, c, j] for v in m.V for j in m.N if j != c) == 1
    model.out_degree = pyo.Constraint(model.C, rule=out_degree)

    def in_degree(m, c):
        return sum(m.x[v, i, c] for v in m.V for i in m.N if i != c) == 1
    model.in_degree = pyo.Constraint(model.C, rule=in_degree)

    # Inicio y fin en el depósito por vehículo (a lo sumo una ruta)
    def start(m, v):
        return sum(m.x[v, DEPOT, j] for j in m.N if j != DEPOT) <= 1
    model.start = pyo.Constraint(model.V, rule=start)

    def end(m, v):
        return sum(m.x[v, i, DEPOT] for i in m.N if i != DEPOT) <= 1
    model.end = pyo.Constraint(model.V, rule=end)

    # Continuidad / conservación de flujo por vehículo
    def flow_balance(m, v, n):
        if n == DEPOT:
            return pyo.Constraint.Skip
        return (
            sum(m.x[v, i, n] for i in m.N if i != n)
            - sum(m.x[v, n, j] for j in m.N if j != n)
            == 0
        )
    model.flow_balance = pyo.Constraint(model.V, model.N, rule=flow_balance)

    # ======================
    # Carga y capacidad (MTZ simplificado)
    # ======================

    # Acumulación de carga estilo MTZ: u[v,j] ≥ u[v,i] + demanda[j] - M(1 - x[v,i,j])
    def load_mtz(m, v, i, j):
        if j == DEPOT:
            # No definimos carga al regresar al depósito
            return pyo.Constraint.Skip
        dem_j = demanda.get(j, 0.0)
        return m.u[v, j] >= m.u[v, i] + dem_j - BIGL * (1 - m.x[v, i, j])
    model.load_mtz = pyo.Constraint(model.V, model.A, rule=load_mtz)

    # Cota superior: la carga al salir de cualquier nodo no puede exceder la capacidad
    def load_cap_constr(m, v, n):
        return m.u[v, n] <= load_cap[v]
    model.load_cap_constr = pyo.Constraint(model.V, model.N, rule=load_cap_constr)

    # Si el vehículo v visita el cliente c, su carga en c debe ser al menos la demanda de c
    def load_visit_lb(m, v, c):
        incoming = sum(m.x[v, i, c] for i in m.N if i != c)
        return m.u[v, c] >= demanda[c] * incoming
    model.load_visit_lb = pyo.Constraint(model.V, model.C, rule=load_visit_lb)

    # ======================
    # Restricción de peso municipal
    # ======================
    def municipal_weight(m, v, c):
        limite = max_weight.get(c, float("inf"))
        if limite == float("inf"):
            return pyo.Constraint.Skip
        return m.u[v, c] <= limite
    model.municipal_weight = pyo.Constraint(model.V, model.C, rule=municipal_weight)

    # ======================
    # Autonomía / combustible (simplificada)
    # ======================

    # Consumo total de combustible ≈ distancia total / fuel_eff
    # y no puede exceder el fuel_cap[v]
    def fuel_autonomy(m, v):
        total_dist = sum(dist[(i, j)] * m.x[v, i, j] for (i, j) in m.A)
        return (total_dist / fuel_eff) <= fuel_cap[v]
    model.fuel_autonomy = pyo.Constraint(model.V, rule=fuel_autonomy)


    # ======================
    # Peajes: enlazar t_weight con la carga en el cliente asociado
    # ======================
    def toll_link_upper_load(m, v, p):
        c = toll_client.get(p, None)
        if (c is None) or (c == "") or (c not in m.C):
            return m.t_weight[v, p] == 0
        # peso en peaje no puede ser mayor que la carga en el cliente
        return m.t_weight[v, p] <= m.u[v, c]
    model.toll_link_upper_load = pyo.Constraint(model.V, model.P, rule=toll_link_upper_load)

    def toll_link_upper_visit(m, v, p):
        c = toll_client.get(p, None)
        if (c is None) or (c == "") or (c not in m.C):
            return pyo.Constraint.Skip
        incoming = sum(m.x[v, i, c] for i in m.N if i != c)
        return m.t_weight[v, p] <= BIGW * incoming
    model.toll_link_upper_visit = pyo.Constraint(model.V, model.P, rule=toll_link_upper_visit)

    def toll_link_lower(m, v, p):
        c = toll_client.get(p, None)
        if (c is None) or (c == "") or (c not in m.C):
            return pyo.Constraint.Skip
        incoming = sum(m.x[v, i, c] for i in m.N if i != c)
        # Si entra, t_weight ≈ u[v,c]; si no, puede ser 0
        return m.t_weight[v, p] >= m.u[v, c] - BIGW * (1 - incoming)
    model.toll_link_lower = pyo.Constraint(model.V, model.P, rule=toll_link_lower)

    return model
