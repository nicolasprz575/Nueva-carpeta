"""
modelo_caso2.py

Modelo de optimización para el Caso 2 de Proyecto C:
CVRP con capacidad de carga + restricciones de combustible + estaciones de recarga.

Formulación MILP en Pyomo con variables de ruta, carga, combustible y recargas.
Usa el solver HiGHS (highs) para resolver el problema.

Autor: Proyecto C - Caso 2
"""

import pyomo.environ as pyo
from pyomo.opt import SolverFactory
from typing import Dict, List, Tuple, Any


def build_model_caso2(data2: dict, scale_fuel_cost: float = 0.001) -> pyo.ConcreteModel:
    """
    Construye el modelo de optimización MILP para el Caso 2 (CVRP + Combustible).
    
    Args:
        data2: Diccionario con los datos cargados por cargar_datos_caso2()
        scale_fuel_cost: Factor de escala para costos de combustible (default: 0.001)
                        Reduce la magnitud de los costos para mejorar condicionamiento
    
    Returns:
        pyo.ConcreteModel: Modelo de Pyomo listo para resolver
    
    El modelo incluye:
    - Variables de ruta x[v,i,j] (binarias)
    - Variables de uso de vehículo y[v] (binarias)
    - Variables de carga load[v,i] (continuas)
    - Variables de combustible fuel[v,i] (continuas)
    - Variables de recarga refuel[v,i] (continuas)
    
    Restricciones:
    - Asignación de clientes (cada cliente visitado exactamente una vez)
    - Flujo en depósito (salida y retorno)
    - Conservación de flujo en nodos
    - Balance de carga
    - Balance de combustible
    - Límites de capacidad (carga y tanque)
    - Recargas solo en estaciones y depósito
    """
    
    # =========================================================================
    # PASO 1: EXTRAER DATOS DEL DICCIONARIO
    # =========================================================================
    
    DEPOT = data2['DEPOT']
    CLIENTS = data2['CLIENTS']
    STATIONS = data2['STATIONS']
    NODES = data2['NODES']
    VEHICLES = data2['VEHICLES']
    
    dist = data2['dist']
    demanda = data2['demanda']
    load_cap = data2['load_cap']
    fuel_cap = data2['fuel_cap']
    fuel_efficiency = data2['fuel_efficiency']  # km/galón
    fuel_price = data2['fuel_price']
    
    C_fixed = data2['C_fixed']
    C_km = data2['C_km']
    C_time = data2.get('C_time', 0)
    
    # =========================================================================
    # PASO 2: CREAR MODELO
    # =========================================================================
    
    model = pyo.ConcreteModel(name="CVRP_Caso2_Combustible")
    
    # =========================================================================
    # PASO 3: DEFINIR CONJUNTOS
    # =========================================================================
    
    model.V = pyo.Set(initialize=VEHICLES, doc="Vehículos disponibles")
    model.N = pyo.Set(initialize=NODES, doc="Todos los nodos (depot + clientes + estaciones)")
    model.C = pyo.Set(initialize=CLIENTS, doc="Clientes a visitar")
    model.S = pyo.Set(initialize=STATIONS, doc="Estaciones de combustible")
    
    # Arcos válidos: todos los pares (i,j) donde i ≠ j
    ARCS = [(i, j) for i in NODES for j in NODES if i != j]
    model.A = pyo.Set(initialize=ARCS, dimen=2, doc="Arcos válidos (i,j)")
    
    # =========================================================================
    # PASO 4: DEFINIR PARÁMETROS
    # =========================================================================
    
    model.dist = pyo.Param(model.A, initialize=lambda m, i, j: dist.get((i, j), 0), 
                           doc="Distancia entre nodos (km)")
    
    model.demanda = pyo.Param(model.C, initialize=lambda m, i: demanda[i], 
                              doc="Demanda del cliente (kg)")
    
    model.load_cap = pyo.Param(model.V, initialize=lambda m, v: load_cap[v], 
                               doc="Capacidad de carga del vehículo (kg)")
    
    model.fuel_cap = pyo.Param(model.V, initialize=lambda m, v: fuel_cap[v], 
                               doc="Capacidad de combustible del vehículo (galones)")
    
    model.fuel_efficiency = pyo.Param(initialize=fuel_efficiency, 
                                     doc="Rendimiento de combustible (km/galón)")
    
    # Precio de combustible en cada nodo (solo aplica para estaciones y depósito)
    # ESCALADO: multiplicar por scale_fuel_cost para mejorar condicionamiento numérico
    def init_fuel_price(m, i):
        if i in STATIONS:
            return fuel_price[i] * scale_fuel_cost
        elif i == DEPOT:
            # Precio promedio de estaciones para el depósito
            return (sum(fuel_price.values()) / len(fuel_price)) * scale_fuel_cost
        else:
            # Clientes no venden combustible (precio alto para evitar recargas)
            return 1e6 * scale_fuel_cost
    
    model.fuel_price = pyo.Param(model.N, initialize=init_fuel_price, 
                                 doc="Precio de combustible por galón (COP/gal) - ESCALADO")
    model.fuel_scale = pyo.Param(initialize=1.0/scale_fuel_cost, doc="Factor de reescalado para costos")
    
    model.C_fixed = pyo.Param(initialize=C_fixed, doc="Costo fijo por vehículo (COP)")
    model.C_km = pyo.Param(initialize=C_km, doc="Costo variable por km (COP/km)")
    
    # =========================================================================
    # PASO 5: DEFINIR VARIABLES DE DECISIÓN
    # =========================================================================
    
    # x[v,i,j] = 1 si el vehículo v recorre el arco i→j
    model.x = pyo.Var(model.V, model.A, domain=pyo.Binary, 
                      doc="Ruta: vehículo v recorre arco (i,j)")
    
    # y[v] = 1 si el vehículo v es usado
    model.y = pyo.Var(model.V, domain=pyo.Binary, 
                      doc="Uso del vehículo v")
    
    # cargo[v,i] = carga del vehículo v al llegar al nodo i
    model.cargo = pyo.Var(model.V, model.N, domain=pyo.NonNegativeReals, 
                          doc="Carga del vehículo v al llegar a nodo i (kg)")
    
    # combustible[v,i] = combustible del vehículo v al llegar al nodo i
    model.combustible = pyo.Var(model.V, model.N, domain=pyo.NonNegativeReals, 
                                doc="Combustible del vehículo v al llegar a nodo i (galones)")
    
    # recarga[v,i] = cantidad de combustible recargado por vehículo v en nodo i
    model.recarga = pyo.Var(model.V, model.N, domain=pyo.NonNegativeReals, 
                            doc="Combustible recargado por vehículo v en nodo i (galones)")
    
    # =========================================================================
    # PASO 6: FUNCIÓN OBJETIVO
    # =========================================================================
    
    def objetivo_rule(m):
        """
        Minimizar costo total:
        - Costo fijo por vehículo usado
        - Costo variable por distancia recorrida
        - Costo de combustible recargado
        """
        costo_fijo = sum(m.C_fixed * m.y[v] for v in m.V)
        
        costo_distancia = sum(m.C_km * m.dist[i, j] * m.x[v, i, j] 
                             for v in m.V for (i, j) in m.A)
        
        costo_combustible = sum(m.fuel_price[i] * m.recarga[v, i] 
                               for v in m.V for i in m.N)
        
        return costo_fijo + costo_distancia + costo_combustible
    
    model.objetivo = pyo.Objective(rule=objetivo_rule, sense=pyo.minimize, 
                                   doc="Minimizar costo total (fijo + distancia + combustible)")
    
    # =========================================================================
    # PASO 7: RESTRICCIONES DE ASIGNACIÓN Y FLUJO
    # =========================================================================
    
    # R1: Cada cliente debe ser visitado exactamente una vez
    def asignacion_clientes_rule(m, c):
        """Cada cliente c es visitado por exactamente un vehículo."""
        return sum(m.x[v, i, c] for v in m.V for i in m.N if (i, c) in m.A) == 1
    
    model.asignacion_clientes = pyo.Constraint(model.C, rule=asignacion_clientes_rule, 
                                               doc="Cada cliente visitado exactamente una vez")
    
    # R2: Si un vehículo se usa, debe salir del depósito
    def salida_depot_rule(m, v):
        """Si vehículo v se usa, debe salir del depósito."""
        return sum(m.x[v, DEPOT, j] for j in m.N if (DEPOT, j) in m.A) == m.y[v]
    
    model.salida_depot = pyo.Constraint(model.V, rule=salida_depot_rule, 
                                       doc="Vehículo usado sale del depósito")
    
    # R3: Si un vehículo se usa, debe regresar al depósito
    def retorno_depot_rule(m, v):
        """Si vehículo v se usa, debe regresar al depósito."""
        return sum(m.x[v, i, DEPOT] for i in m.N if (i, DEPOT) in m.A) == m.y[v]
    
    model.retorno_depot = pyo.Constraint(model.V, rule=retorno_depot_rule, 
                                        doc="Vehículo usado regresa al depósito")
    
    # R4: Conservación de flujo en nodos intermedios
    def conservacion_flujo_rule(m, v, i):
        """
        Para cada vehículo y nodo intermedio (no depósito):
        Si entra, debe salir.
        """
        if i == DEPOT:
            return pyo.Constraint.Skip
        
        entrada = sum(m.x[v, j, i] for j in m.N if (j, i) in m.A)
        salida = sum(m.x[v, i, j] for j in m.N if (i, j) in m.A)
        
        return entrada == salida
    
    model.conservacion_flujo = pyo.Constraint(model.V, model.N, rule=conservacion_flujo_rule, 
                                             doc="Conservación de flujo en nodos")
    
    # =========================================================================
    # PASO 8: RESTRICCIONES DE CARGA
    # =========================================================================
    
    # R5: Carga en el depósito (inicio) es 0
    def carga_inicial_rule(m, v):
        """Carga al salir del depósito es 0."""
        return m.cargo[v, DEPOT] == 0
    
    model.carga_inicial = pyo.Constraint(model.V, rule=carga_inicial_rule, 
                                        doc="Carga inicial en depósito = 0")
    
    # R6: Balance de carga a lo largo de las rutas
    def balance_carga_rule(m, v, i, j):
        """
        Si vehículo v recorre arco (i,j):
        load[v,j] = load[v,i] + demanda[j] (si j es cliente)
        
        Formulación con Big-M:
        load[v,j] >= load[v,i] + demanda[j] - M*(1 - x[v,i,j])
        """
        if i == DEPOT or j == DEPOT:
            return pyo.Constraint.Skip
        
        # Big-M: Exactamente la capacidad del vehículo (tight bound)
        M = m.load_cap[v]
        
        demanda_j = demanda[j] if j in CLIENTS else 0
        
        return m.cargo[v, j] >= m.cargo[v, i] + demanda_j - M * (1 - m.x[v, i, j])
    
    model.balance_carga = pyo.Constraint(model.V, model.A, rule=balance_carga_rule, 
                                        doc="Balance de carga en arcos")
    
    # R7: Capacidad máxima de carga
    def capacidad_carga_rule(m, v, i):
        """Carga no puede exceder capacidad del vehículo."""
        return m.cargo[v, i] <= m.load_cap[v]
    
    model.capacidad_carga = pyo.Constraint(model.V, model.N, rule=capacidad_carga_rule, 
                                          doc="Carga no excede capacidad")
    
    # =========================================================================
    # PASO 9: RESTRICCIONES DE COMBUSTIBLE
    # =========================================================================
    
    # R8: Combustible inicial al salir del depósito (tanque lleno)
    def combustible_inicial_rule(m, v):
        """Vehículo sale del depósito con tanque lleno."""
        return m.combustible[v, DEPOT] == m.fuel_cap[v]
    
    model.combustible_inicial = pyo.Constraint(model.V, rule=combustible_inicial_rule, 
                                               doc="Combustible inicial = tanque lleno")
    
    # R9: Balance de combustible a lo largo de las rutas
    def balance_combustible_rule(m, v, i, j):
        """
        Si vehículo v recorre arco (i,j):
        fuel[v,j] = fuel[v,i] - consumo(i,j) + refuel[v,j]
        
        Donde consumo(i,j) = dist[i,j] / fuel_efficiency
        
        Formulación con Big-M:
        fuel[v,j] >= fuel[v,i] - consumo(i,j) + refuel[v,j] - M*(1 - x[v,i,j])
        
        IMPORTANTE: NO skip cuando j == DEPOT para garantizar combustible suficiente al regresar
        """
        # Big-M: Capacidad del tanque + consumo del arco (tighter bound)
        # Esto permite que la restricción sea más ajustada cuando x[v,i,j]=0
        consumo = m.dist[i, j] / m.fuel_efficiency
        M = m.fuel_cap[v] + consumo
        
        consumo = m.dist[i, j] / m.fuel_efficiency
        
        return m.combustible[v, j] >= m.combustible[v, i] - consumo + m.recarga[v, j] - M * (1 - m.x[v, i, j])
    
    model.balance_combustible = pyo.Constraint(model.V, model.A, rule=balance_combustible_rule, 
                                              doc="Balance de combustible en arcos")
    
    # R10: Capacidad máxima de combustible
    def capacidad_combustible_rule(m, v, i):
        """Combustible no puede exceder capacidad del tanque (ya incluye recarga en balance)."""
        return m.combustible[v, i] <= m.fuel_cap[v]
    
    model.capacidad_combustible = pyo.Constraint(model.V, model.N, rule=capacidad_combustible_rule, 
                                                doc="Combustible no excede capacidad del tanque")
    
    # R11: Recargas solo en estaciones y depósito
    def recarga_solo_estaciones_rule(m, v, i):
        """
        Solo se puede recargar en estaciones o en el depósito.
        En clientes regulares, refuel[v,i] = 0.
        """
        if i in STATIONS or i == DEPOT:
            return pyo.Constraint.Skip
        
        return m.recarga[v, i] == 0
    
    model.recarga_solo_estaciones = pyo.Constraint(model.V, model.N, rule=recarga_solo_estaciones_rule, 
                                                   doc="Recargas solo en estaciones/depósito")
    
    # R12: Combustible no negativo
    def combustible_no_negativo_rule(m, v, i):
        """Combustible debe ser no negativo."""
        return m.combustible[v, i] >= 0
    
    model.combustible_no_negativo = pyo.Constraint(model.V, model.N, rule=combustible_no_negativo_rule, 
                                                   doc="Combustible no negativo")
    
    return model


def extraer_solucion_caso2(model: pyo.ConcreteModel, data2: dict) -> dict:
    """
    Extrae la solución del modelo optimizado del Caso 2.
    
    Args:
        model: Modelo de Pyomo resuelto
        data2: Diccionario con los datos originales
    
    Returns:
        Diccionario con la solución estructurada:
        - rutas: Dict[str, List[str]] - Rutas por vehículo
        - vehiculos_usados: List[str] - Vehículos utilizados
        - distancias: Dict[str, float] - Distancia por vehículo
        - cargas: Dict[str, float] - Carga total por vehículo
        - combustible: Dict[str, Dict] - Detalle de combustible por vehículo
        - recargas: Dict[str, List[Dict]] - Recargas por vehículo
        - costo_total: float
        - costo_fijo: float
        - costo_distancia: float
        - costo_combustible: float
        - distancia_total: float
        - num_vehiculos: int
        - clientes_visitados: int
    """
    
    DEPOT = data2['DEPOT']
    VEHICLES = data2['VEHICLES']
    CLIENTS = data2['CLIENTS']
    STATIONS = data2['STATIONS']
    NODES = data2['NODES']
    dist = data2['dist']
    demanda = data2['demanda']
    
    # Extraer rutas de cada vehículo
    rutas = {}
    vehiculos_usados = []
    distancias = {}
    cargas = {}
    combustible_detalles = {}
    recargas_detalles = {}
    
    for v in VEHICLES:
        if pyo.value(model.y[v]) > 0.5:  # Vehículo usado
            vehiculos_usados.append(v)
            
            # Reconstruir la ruta del vehículo
            ruta = [DEPOT]
            nodo_actual = DEPOT
            visitados = set([DEPOT])
            
            while True:
                # Buscar el siguiente nodo
                siguiente = None
                for j in NODES:
                    if j not in visitados and (nodo_actual, j) in model.A:
                        if pyo.value(model.x[v, nodo_actual, j]) > 0.5:
                            siguiente = j
                            break
                
                if siguiente is None or siguiente == DEPOT:
                    ruta.append(DEPOT)
                    break
                
                ruta.append(siguiente)
                visitados.add(siguiente)
                nodo_actual = siguiente
            
            rutas[v] = ruta
            
            # Calcular distancia total del vehículo
            distancia_v = 0.0
            for i in range(len(ruta) - 1):
                distancia_v += dist[(ruta[i], ruta[i+1])]
            distancias[v] = distancia_v
            
            # Calcular carga total (suma de demandas de clientes visitados)
            carga_v = sum(demanda[c] for c in ruta if c in CLIENTS)
            cargas[v] = carga_v
            
            # Extraer información de combustible
            combustible_info = {
                'inicial': pyo.value(model.combustible[v, DEPOT]),
                'minimo': min(pyo.value(model.combustible[v, i]) for i in ruta),
                'final': pyo.value(model.combustible[v, DEPOT]) if len(ruta) > 1 else 0,
                'consumo_total': 0.0
            }
            
            # Calcular consumo total
            for i in range(len(ruta) - 1):
                consumo = dist[(ruta[i], ruta[i+1])] / data2['fuel_efficiency']
                combustible_info['consumo_total'] += consumo
            
            combustible_detalles[v] = combustible_info
            
            # Extraer recargas
            recargas_v = []
            for i in ruta:
                recarga_i = pyo.value(model.recarga[v, i])
                if recarga_i > 0.01:  # Umbral para considerar recarga
                    precio_i = data2['fuel_price'].get(i, pyo.value(model.fuel_price[i]))
                    recargas_v.append({
                        'nodo': i,
                        'cantidad': recarga_i,
                        'precio_unitario': precio_i,
                        'costo': recarga_i * precio_i
                    })
            
            recargas_detalles[v] = recargas_v
    
    # Calcular costos
    costo_fijo = sum(pyo.value(model.C_fixed * model.y[v]) for v in VEHICLES)
    
    costo_distancia = sum(pyo.value(model.C_km * model.dist[i, j] * model.x[v, i, j]) 
                         for v in VEHICLES 
                         for (i, j) in model.A)
    
    # IMPORTANTE: Reescalar costos de combustible al valor original
    fuel_scale = pyo.value(model.fuel_scale)
    costo_combustible = sum(pyo.value(model.fuel_price[i] * model.recarga[v, i]) * fuel_scale
                           for v in VEHICLES 
                           for i in NODES)
    
    costo_total = pyo.value(model.objetivo)
    
    distancia_total = sum(distancias.values())
    
    # Contar clientes visitados
    clientes_visitados = set()
    for ruta in rutas.values():
        clientes_visitados.update([n for n in ruta if n in CLIENTS])
    
    return {
        'rutas': rutas,
        'vehiculos_usados': vehiculos_usados,
        'distancias': distancias,
        'cargas': cargas,
        'combustible': combustible_detalles,
        'recargas': recargas_detalles,
        'costo_total': costo_total,
        'costo_fijo': costo_fijo,
        'costo_distancia': costo_distancia,
        'costo_combustible': costo_combustible,
        'distancia_total': distancia_total,
        'num_vehiculos': len(vehiculos_usados),
        'clientes_visitados': len(clientes_visitados)
    }


def resolver_modelo_caso2(data2: dict, solver_name: str = 'highs', 
                          time_limit: int = 300, 
                          mip_gap: float = 0.01) -> Tuple[pyo.ConcreteModel, dict]:
    """
    Función auxiliar para construir, resolver y extraer la solución del Caso 2.
    
    Args:
        data2: Datos del problema
        solver_name: Nombre del solver ('highs', 'glpk', 'cbc', etc.)
        time_limit: Límite de tiempo en segundos
        mip_gap: Gap de optimalidad aceptable (ej. 0.01 = 1%)
    
    Returns:
        Tuple[model, solucion]: Modelo resuelto y diccionario de solución
    """
    
    print("=" * 70)
    print("CONSTRUYENDO MODELO CASO 2 (CVRP + COMBUSTIBLE)")
    print("=" * 70)
    
    model = build_model_caso2(data2)
    
    print(f"\n✓ Modelo construido exitosamente")
    print(f"  - Variables de decisión: {len(list(model.component_objects(pyo.Var, active=True)))}")
    print(f"  - Restricciones: {len(list(model.component_objects(pyo.Constraint, active=True)))}")
    
    print("\n" + "=" * 70)
    print(f"RESOLVIENDO CON {solver_name.upper()}")
    print("=" * 70)
    
    solver = SolverFactory(solver_name)
    
    # Configurar opciones del solver
    if solver_name == 'highs':
        solver.options['time_limit'] = time_limit
        solver.options['mip_rel_gap'] = mip_gap
    elif solver_name == 'cbc':
        solver.options['seconds'] = time_limit
        solver.options['ratio'] = mip_gap
    elif solver_name == 'glpk':
        solver.options['tmlim'] = time_limit
        solver.options['mipgap'] = mip_gap
    
    # Resolver
    results = solver.solve(model, tee=True)
    
    # Verificar estado de la solución
    if results.solver.termination_condition == pyo.TerminationCondition.optimal:
        print("\n✓ Solución óptima encontrada")
    elif results.solver.termination_condition == pyo.TerminationCondition.feasible:
        print("\n✓ Solución factible encontrada (no necesariamente óptima)")
    else:
        print(f"\n⚠️  Estado del solver: {results.solver.termination_condition}")
        raise RuntimeError("No se encontró una solución factible")
    
    # Extraer solución
    print("\n" + "=" * 70)
    print("EXTRAYENDO SOLUCIÓN")
    print("=" * 70)
    
    solucion = extraer_solucion_caso2(model, data2)
    
    print(f"\n✓ Solución extraída exitosamente")
    print(f"  - Vehículos usados: {solucion['num_vehiculos']}")
    print(f"  - Clientes visitados: {solucion['clientes_visitados']}")
    print(f"  - Distancia total: {solucion['distancia_total']:.2f} km")
    print(f"  - Costo total: ${solucion['costo_total']:,.0f} COP")
    
    return model, solucion
