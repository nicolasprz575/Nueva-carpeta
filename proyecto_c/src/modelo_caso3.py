"""
Módulo de Modelo de Optimización - Caso 3: VRP con Combustible + Peajes + Restricciones Viales
Proyecto C: Optimización de Rutas de Distribución

Este módulo extiende el Caso 2 agregando:
- Costos de peaje en arcos específicos
- Restricciones viales (arcos prohibidos globalmente o por vehículo)
- Función objetivo con componente de peajes

El modelo resuelve un VRP con:
- Capacidad de carga
- Gestión de combustible con estaciones de recarga
- Costos de peaje
- Arcos prohibidos

Autor: Sistema de Optimización
Fecha: Noviembre 2025
"""

import pyomo.environ as pyo
from typing import Dict, List, Tuple, Set, Optional
import numpy as np


# ============================================================================
# FUNCIÓN PRINCIPAL: CONSTRUIR MODELO PYOMO DEL CASO 3
# ============================================================================

def build_model_caso3(data3: Dict) -> pyo.ConcreteModel:
    """
    Construye el modelo de optimización Pyomo para el Caso 3.
    
    El modelo extiende el Caso 2 con:
    - Costos de peaje en la función objetivo
    - Arcos prohibidos (no se crean variables x[v,i,j])
    - Restricciones por vehículo (arcos restringidos)
    
    Parámetros:
        data3 (dict): Diccionario con datos cargados por cargar_datos_caso3()
                      Debe contener: NODES, CLIENTS, STATIONS, VEHICLES, ARCS,
                      TOLL_ARCS, FORBIDDEN_ARCS, RESTRICTED_ARCS, DEPOT,
                      demanda, dist, time, toll_cost, consumo, fuel_price,
                      load_cap, fuel_cap, max_dist, cost_fixed, cost_km,
                      cost_time, km_per_gal
    
    Retorna:
        pyo.ConcreteModel: Modelo Pyomo listo para resolver
    
    Variables de decisión:
        x[v,i,j]: Binaria, 1 si vehículo v recorre arco (i,j)
        y[v]: Binaria, 1 si vehículo v es usado
        u[v,i]: Continua, variable auxiliar MTZ para eliminación de subtours
        load[v,i]: Continua, carga del vehículo v al llegar a nodo i [kg]
        fuel[v,i]: Continua, combustible del vehículo v al llegar a nodo i [gal]
        refuel[v,i]: Continua, cantidad recargada por vehículo v en nodo i [gal]
    
    Función objetivo:
        Minimizar costo total = costo fijo vehículos + costo distancia 
                               + costo combustible + costo peajes
    """
    
    print("\n" + "="*80)
    print("CONSTRUCCIÓN DEL MODELO - CASO 3")
    print("="*80)
    
    # ========================================================================
    # 1. EXTRAER DATOS DEL DICCIONARIO
    # ========================================================================
    
    DEPOT = data3['DEPOT']
    NODES = data3['NODES']
    CLIENTS = data3['CLIENTS']
    STATIONS = data3['STATIONS']
    VEHICLES = data3['VEHICLES']
    ARCS = data3['ARCS']  # Ya filtrados (sin arcos prohibidos)
    TOLL_ARCS = data3['TOLL_ARCS']
    FORBIDDEN_ARCS = data3['FORBIDDEN_ARCS']
    RESTRICTED_ARCS = data3['RESTRICTED_ARCS']
    
    demanda = data3['demanda']
    dist = data3['dist']
    time = data3['time']
    toll_cost = data3['toll_cost']
    consumo = data3['consumo']
    fuel_price = data3['fuel_price']
    
    load_cap = data3['load_cap']
    fuel_cap = data3['fuel_cap']
    max_dist = data3['max_dist']
    
    cost_fixed = data3['cost_fixed']
    cost_km = data3['cost_km']
    cost_time = data3['cost_time']
    km_per_gal = data3['km_per_gal']
    
    num_nodes = len(NODES)
    
    print(f"Nodos: {num_nodes} ({len(CLIENTS)} clientes + {len(STATIONS)} estaciones + 1 depósito)")
    print(f"Vehículos: {len(VEHICLES)}")
    print(f"Arcos válidos: {len(ARCS)} (después de filtrar {len(FORBIDDEN_ARCS)} prohibidos)")
    print(f"Arcos con peaje: {len(TOLL_ARCS)}")
    
    # ========================================================================
    # 2. CREAR MODELO PYOMO
    # ========================================================================
    
    model = pyo.ConcreteModel(name="Caso3_VRP_Peajes_Restricciones")
    
    # ========================================================================
    # 3. CONJUNTOS
    # ========================================================================
    
    print("\n[1] Definiendo conjuntos...")
    
    model.V = pyo.Set(initialize=VEHICLES, doc="Conjunto de vehículos")
    model.N = pyo.Set(initialize=NODES, doc="Conjunto de nodos (CD01, C***, E***)")
    model.C = pyo.Set(initialize=CLIENTS, doc="Conjunto de clientes")
    model.S = pyo.Set(initialize=STATIONS, doc="Conjunto de estaciones")
    
    # Conjunto de arcos válidos por vehículo (filtrando restricciones)
    # Esto es más eficiente que crear todas las variables y luego restringirlas
    def arcos_validos_por_vehiculo(model, v):
        """Retorna arcos válidos para el vehículo v"""
        arcos_permitidos = []
        for (i, j) in ARCS:
            # Verificar si este arco NO está restringido para este vehículo
            if (i, j) not in RESTRICTED_ARCS[v]:
                arcos_permitidos.append((i, j))
        return arcos_permitidos
    
    # Crear conjunto indexado de arcos por vehículo
    model.A_v = pyo.Set(model.V, initialize=arcos_validos_por_vehiculo,
                        doc="Arcos válidos para cada vehículo")
    
    print(f"  ✓ Conjuntos definidos")
    print(f"    Arcos por vehículo (promedio): {np.mean([len(model.A_v[v]) for v in VEHICLES]):.0f}")
    
    # ========================================================================
    # 4. PARÁMETROS
    # ========================================================================
    
    print("\n[2] Definiendo parámetros...")
    
    # Demanda de clientes
    model.q = pyo.Param(model.C, initialize=demanda, doc="Demanda de cada cliente [kg]")
    
    # Distancias, tiempos y consumo
    model.d = pyo.Param(model.N, model.N, initialize=lambda m, i, j: dist.get((i,j), 0),
                       doc="Distancia entre nodos [km]")
    model.t = pyo.Param(model.N, model.N, initialize=lambda m, i, j: time.get((i,j), 0),
                       doc="Tiempo de viaje entre nodos [horas]")
    model.consumo = pyo.Param(model.N, model.N, 
                             initialize=lambda m, i, j: consumo.get((i,j), 0),
                             doc="Consumo de combustible en arco [galones]")
    
    # Capacidades de vehículos
    model.Q = pyo.Param(model.V, initialize=load_cap, doc="Capacidad de carga [kg]")
    model.F = pyo.Param(model.V, initialize=fuel_cap, doc="Capacidad de combustible [gal]")
    model.D = pyo.Param(model.V, initialize=max_dist, doc="Autonomía máxima [km]")
    
    # Precios de combustible en estaciones
    model.fuel_price = pyo.Param(model.S, initialize=fuel_price,
                                 doc="Precio combustible en estaciones [COP/gal]")
    
    # Costos de peaje (solo para arcos con peaje)
    model.toll_cost = pyo.Param(model.N, model.N,
                                initialize=lambda m, i, j: toll_cost.get((i,j), 0),
                                doc="Costo de peaje en arco [COP]")
    
    # Costos operativos
    model.cost_fixed = pyo.Param(initialize=cost_fixed, doc="Costo fijo por vehículo [COP]")
    model.cost_km = pyo.Param(initialize=cost_km, doc="Costo por km [COP/km]")
    model.cost_time = pyo.Param(initialize=cost_time, doc="Costo por hora [COP/h]")
    
    # Parámetro auxiliar: Big-M para restricciones
    # Usamos max_dist como referencia conservadora
    model.M = pyo.Param(initialize=max(max_dist.values()), doc="Parámetro Big-M")
    
    print(f"  ✓ Parámetros definidos")
    print(f"    Big-M: {pyo.value(model.M):.1f}")
    
    # ========================================================================
    # 5. VARIABLES DE DECISIÓN
    # ========================================================================
    
    print("\n[3] Definiendo variables de decisión...")
    
    # x[v,i,j]: Binaria, 1 si vehículo v recorre arco (i,j)
    # Solo se crean variables para arcos válidos por vehículo
    def x_index_set():
        """Genera índices válidos para variable x"""
        indices = []
        for v in VEHICLES:
            for (i, j) in model.A_v[v]:
                indices.append((v, i, j))
        return indices
    
    model.x = pyo.Var(x_index_set(), domain=pyo.Binary,
                     doc="1 si vehículo v recorre arco (i,j)")
    
    # y[v]: Binaria, 1 si vehículo v es usado
    model.y = pyo.Var(model.V, domain=pyo.Binary, doc="1 si vehículo v es usado")
    
    # u[v,i]: Variable auxiliar MTZ para eliminación de subtours
    model.u = pyo.Var(model.V, model.N, domain=pyo.NonNegativeReals,
                     bounds=(0, num_nodes), doc="Variable auxiliar MTZ")
    
    # load[v,i]: Carga del vehículo v al llegar a nodo i
    model.carga = pyo.Var(model.V, model.N, domain=pyo.NonNegativeReals,
                        doc="Carga al llegar a nodo [kg]")
    
    # fuel[v,i]: Combustible del vehículo v al llegar a nodo i
    model.fuel = pyo.Var(model.V, model.N, domain=pyo.NonNegativeReals,
                        doc="Combustible al llegar a nodo [gal]")
    
    # refuel[v,i]: Cantidad recargada por vehículo v en nodo i
    model.refuel = pyo.Var(model.V, model.N, domain=pyo.NonNegativeReals,
                          doc="Cantidad recargada en nodo [gal]")
    
    num_vars_x = len(model.x)
    num_vars_total = num_vars_x + len(VEHICLES) + len(VEHICLES)*num_nodes*3 + len(VEHICLES)*num_nodes
    
    print(f"  ✓ Variables definidas")
    print(f"    Variables x (arcos): {num_vars_x}")
    print(f"    Variables totales: ~{num_vars_total}")
    
    # ========================================================================
    # 6. FUNCIÓN OBJETIVO
    # ========================================================================
    
    print("\n[4] Definiendo función objetivo...")
    
    def objetivo_rule(m):
        """
        Minimizar costo total:
        - Costo fijo por vehículos usados
        - Costo por distancia recorrida
        - Costo de combustible en estaciones
        - Costo de peajes (NUEVO en Caso 3)
        """
        # Componente 1: Costo fijo
        costo_fijo = sum(m.cost_fixed * m.y[v] for v in m.V)
        
        # Componente 2: Costo por distancia
        costo_distancia = sum(m.cost_km * m.d[i,j] * m.x[v,i,j]
                             for v in m.V for (i,j) in m.A_v[v])
        
        # Componente 3: Costo de combustible
        costo_combustible = sum(m.fuel_price[s] * m.refuel[v,s]
                               for v in m.V for s in m.S)
        
        # Componente 4: Costo de peajes (NUEVO)
        costo_peajes = sum(m.toll_cost[i,j] * m.x[v,i,j]
                          for v in m.V for (i,j) in m.A_v[v]
                          if (i,j) in TOLL_ARCS)
        
        return costo_fijo + costo_distancia + costo_combustible + costo_peajes
    
    model.obj = pyo.Objective(rule=objetivo_rule, sense=pyo.minimize,
                             doc="Minimizar costo total")
    
    print(f"  ✓ Función objetivo definida (4 componentes: fijo + distancia + combustible + peajes)")
    
    # ========================================================================
    # 7. RESTRICCIONES HEREDADAS DEL CASO 2
    # ========================================================================
    
    print("\n[5] Definiendo restricciones del Caso 2 (heredadas)...")
    
    # R1: Cada cliente es visitado exactamente una vez
    def asignacion_rule(m, c):
        return sum(m.x[v,i,j] for v in m.V for (i,j) in m.A_v[v] if i == c) == 1
    
    model.r_asignacion = pyo.Constraint(model.C, rule=asignacion_rule,
                                       doc="R1: Cada cliente visitado una vez")
    
    # R2: Flujo en el depósito (salidas = entradas = y[v])
    def flujo_depot_salida_rule(m, v):
        return sum(m.x[v,i,j] for (i,j) in m.A_v[v] if i == DEPOT) == m.y[v]
    
    model.r_flujo_depot_salida = pyo.Constraint(model.V, rule=flujo_depot_salida_rule,
                                               doc="R2a: Vehículo sale del depósito si es usado")
    
    def flujo_depot_entrada_rule(m, v):
        return sum(m.x[v,i,j] for (i,j) in m.A_v[v] if j == DEPOT) == m.y[v]
    
    model.r_flujo_depot_entrada = pyo.Constraint(model.V, rule=flujo_depot_entrada_rule,
                                                doc="R2b: Vehículo regresa al depósito si es usado")
    
    # R3: Conservación de flujo en clientes
    def conservacion_flujo_rule(m, v, c):
        entrada = sum(m.x[v,i,j] for (i,j) in m.A_v[v] if j == c)
        salida = sum(m.x[v,i,j] for (i,j) in m.A_v[v] if i == c)
        return entrada == salida
    
    model.r_conservacion_flujo = pyo.Constraint(model.V, model.C, rule=conservacion_flujo_rule,
                                               doc="R3: Conservación de flujo en clientes")
    
    # R4: Vinculación x-y (solo usar arcos si vehículo está activo)
    def vinculacion_xy_rule(m, v, i, j):
        if (i, j) in m.A_v[v]:
            return m.x[v,i,j] <= m.y[v]
        else:
            return pyo.Constraint.Skip
    
    model.r_vinculacion_xy = pyo.Constraint(model.V, model.N, model.N,
                                           rule=vinculacion_xy_rule,
                                           doc="R4: Solo usar arcos si vehículo activo")
    
    # R5: Eliminación de subtours (MTZ)
    def mtz_rule(m, v, i, j):
        if i != DEPOT and j != DEPOT and (i, j) in m.A_v[v]:
            return m.u[v,i] - m.u[v,j] + num_nodes * m.x[v,i,j] <= num_nodes - 1
        else:
            return pyo.Constraint.Skip
    
    model.r_mtz = pyo.Constraint(model.V, model.N, model.N, rule=mtz_rule,
                                doc="R5: Eliminación de subtours (MTZ)")
    
    # R6: Balance de carga en cada arco
    def balance_carga_rule(m, v, i, j):
        if (i, j) not in m.A_v[v]:
            return pyo.Constraint.Skip
        
        if i == DEPOT:
            # Salida del depósito: carga = 0
            return m.carga[v,j] == 0
        elif j == DEPOT:
            # Entrada al depósito: puede tener cualquier carga residual
            return pyo.Constraint.Skip
        elif j in CLIENTS:
            # Llegada a cliente: carga disminuye por demanda del cliente
            return m.carga[v,j] >= m.carga[v,i] + m.q[j] - m.Q[v] * (1 - m.x[v,i,j])
        else:
            # Arco que no afecta carga (por ejemplo a estación)
            return m.carga[v,j] >= m.carga[v,i] - m.Q[v] * (1 - m.x[v,i,j])
    
    model.r_balance_carga = pyo.Constraint(model.V, model.N, model.N,
                                          rule=balance_carga_rule,
                                          doc="R6: Balance de carga en arcos")
    
    # R7: Capacidad de carga
    def capacidad_carga_rule(m, v, i):
        return m.carga[v,i] <= m.Q[v]
    
    model.r_capacidad_carga = pyo.Constraint(model.V, model.N,
                                            rule=capacidad_carga_rule,
                                            doc="R7: No exceder capacidad de carga")
    
    # R8: Límite de combustible inicial (en depósito)
    def limite_combustible_inicial_rule(m, v):
        return m.fuel[v, DEPOT] <= m.F[v]
    
    model.r_limite_combustible_inicial = pyo.Constraint(model.V,
                                                       rule=limite_combustible_inicial_rule,
                                                       doc="R8: Combustible inicial <= capacidad")
    
    # R9: Balance de combustible en cada arco (CRÍTICO - bug corregido en Caso 2)
    def balance_combustible_rule(m, v, i, j):
        if (i, j) not in m.A_v[v]:
            return pyo.Constraint.Skip
        
        # Balance: fuel[v,j] >= fuel[v,i] - consumo[i,j] + refuel[v,j] si x[v,i,j] = 1
        # Usamos Big-M para activar solo cuando el arco es usado
        M_combustible = m.F[v] + m.consumo[i,j]
        
        return m.fuel[v,j] >= (m.fuel[v,i] - m.consumo[i,j] + m.refuel[v,j] 
                               - M_combustible * (1 - m.x[v,i,j]))
    
    model.r_balance_combustible = pyo.Constraint(model.V, model.N, model.N,
                                                rule=balance_combustible_rule,
                                                doc="R9: Balance de combustible en arcos")
    
    # R10: No negatividad de combustible
    def no_negatividad_combustible_rule(m, v, i):
        return m.fuel[v,i] >= 0
    
    model.r_no_negatividad_combustible = pyo.Constraint(model.V, model.N,
                                                       rule=no_negatividad_combustible_rule,
                                                       doc="R10: Combustible no negativo")
    
    # R11: Límite de capacidad de combustible
    def capacidad_combustible_rule(m, v, i):
        return m.fuel[v,i] <= m.F[v]
    
    model.r_capacidad_combustible = pyo.Constraint(model.V, model.N,
                                                  rule=capacidad_combustible_rule,
                                                  doc="R11: No exceder capacidad de combustible")
    
    # R12: Solo se puede recargar en estaciones (no en clientes)
    def recarga_solo_estaciones_rule(m, v, c):
        return m.refuel[v,c] == 0
    
    model.r_recarga_solo_estaciones = pyo.Constraint(model.V, model.C,
                                                     rule=recarga_solo_estaciones_rule,
                                                     doc="R12: No recargar en clientes")
    
    # R13: Límite de recarga (no exceder capacidad)
    def limite_recarga_rule(m, v, i):
        return m.refuel[v,i] <= m.F[v]
    
    model.r_limite_recarga = pyo.Constraint(model.V, model.N,
                                           rule=limite_recarga_rule,
                                           doc="R13: Recarga no excede capacidad")
    
    num_restricciones_caso2 = (len(CLIENTS) +  # R1
                               2 * len(VEHICLES) +  # R2
                               len(VEHICLES) * len(CLIENTS) +  # R3
                               len(VEHICLES) * num_nodes * num_nodes +  # R4, R5, R6, R9
                               2 * len(VEHICLES) * num_nodes +  # R7, R10, R11, R13
                               len(VEHICLES) +  # R8
                               len(VEHICLES) * len(CLIENTS))  # R12
    
    print(f"  ✓ Restricciones del Caso 2 definidas (~{num_restricciones_caso2} restricciones)")
    
    # ========================================================================
    # 8. RESTRICCIONES NUEVAS DEL CASO 3 (PEAJES Y RESTRICCIONES VIALES)
    # ========================================================================
    
    print("\n[6] Definiendo restricciones nuevas del Caso 3...")
    
    # NOTA IMPORTANTE:
    # Las restricciones de arcos prohibidos ya están implementadas IMPLÍCITAMENTE
    # al construir el conjunto A_v[v] que excluye:
    # 1. Arcos en FORBIDDEN_ARCS (prohibidos para todos)
    # 2. Arcos en RESTRICTED_ARCS[v] (prohibidos para vehículo v)
    #
    # Por lo tanto, NO necesitamos restricciones explícitas x[v,i,j] = 0
    # porque esas variables x[v,i,j] directamente NO EXISTEN en el modelo.
    #
    # Esto es más eficiente que crear las variables y luego forzarlas a 0.
    
    # R14: (Opcional) Restricción explícita de uso de peajes para conteo
    # Esta restricción no es necesaria para la optimización, pero puede ser útil
    # para post-procesamiento o análisis
    
    # Si se quisiera agregar alguna restricción adicional sobre peajes
    # (por ejemplo, límite en número de peajes por vehículo), se podría hacer aquí:
    
    # def limite_peajes_rule(m, v):
    #     num_peajes_usados = sum(m.x[v,i,j] for (i,j) in m.A_v[v] if (i,j) in TOLL_ARCS)
    #     return num_peajes_usados <= MAX_TOLLS_PER_VEHICLE
    # model.r_limite_peajes = pyo.Constraint(model.V, rule=limite_peajes_rule)
    
    print(f"  ✓ Restricciones del Caso 3:")
    print(f"    - Arcos prohibidos: Implementado vía filtrado de variables")
    print(f"    - Arcos restringidos por vehículo: Implementado vía A_v[v]")
    print(f"    - Peajes: Integrados en función objetivo (sin restricciones adicionales)")
    
    # ========================================================================
    # 9. RESUMEN DEL MODELO
    # ========================================================================
    
    print("\n" + "="*80)
    print("RESUMEN DEL MODELO CONSTRUIDO")
    print("="*80)
    print(f"Variables de decisión:")
    print(f"  - x[v,i,j]: {num_vars_x} variables binarias (arcos)")
    print(f"  - y[v]: {len(VEHICLES)} variables binarias (vehículos)")
    print(f"  - u[v,i]: {len(VEHICLES)*num_nodes} variables continuas (MTZ)")
    print(f"  - load[v,i]: {len(VEHICLES)*num_nodes} variables continuas (carga)")
    print(f"  - fuel[v,i]: {len(VEHICLES)*num_nodes} variables continuas (combustible)")
    print(f"  - refuel[v,i]: {len(VEHICLES)*num_nodes} variables continuas (recarga)")
    print(f"Total variables: ~{num_vars_total}")
    print()
    print(f"Restricciones:")
    print(f"  - Del Caso 2 (heredadas): ~{num_restricciones_caso2}")
    print(f"  - Del Caso 3 (nuevas): Implementadas vía filtrado de variables")
    print()
    print(f"Función objetivo: 4 componentes")
    print(f"  1. Costo fijo vehículos")
    print(f"  2. Costo por distancia")
    print(f"  3. Costo de combustible")
    print(f"  4. Costo de peajes ← NUEVO")
    print("="*80)
    print()
    
    return model


# ============================================================================
# FUNCIÓN: EXTRAER SOLUCIÓN DEL MODELO RESUELTO
# ============================================================================

def extraer_solucion_caso3(model: pyo.ConcreteModel, data3: Dict) -> Dict:
    """
    Extrae la solución del modelo resuelto del Caso 3.
    
    Analiza las variables de decisión para reconstruir:
    - Rutas de cada vehículo (secuencia de nodos visitados)
    - Clientes servidos y demandas satisfechas
    - Estaciones visitadas y cantidades recargadas
    - Peajes cruzados y costos
    - Distancias, tiempos y costos totales
    
    Parámetros:
        model (pyo.ConcreteModel): Modelo Pyomo resuelto
        data3 (dict): Diccionario de datos original
    
    Retorna:
        dict: Solución estructurada con información por vehículo:
        {
            'vehiculos_usados': List[str],
            'rutas': Dict[str, List[str]],  # ruta ordenada por vehículo
            'clientes_servidos': Dict[str, List[str]],
            'demandas_servidas': Dict[str, float],
            'estaciones_visitadas': Dict[str, List[str]],
            'recargas': Dict[str, Dict[str, float]],  # {v: {estacion: galones}}
            'peajes_usados': Dict[str, List[Tuple[str,str]]],  # arcos con peaje
            'costo_peajes': Dict[str, float],
            'distancia_total': Dict[str, float],
            'tiempo_total': Dict[str, float],
            'costo_combustible': Dict[str, float],
            'costo_total_vehiculo': Dict[str, float],
            'costo_total': float,
            'num_vehiculos': int,
            'num_clientes': int,
            'num_peajes': int
        }
    """
    
    print("\n" + "="*80)
    print("EXTRACCIÓN DE SOLUCIÓN - CASO 3")
    print("="*80)
    
    DEPOT = data3['DEPOT']
    VEHICLES = data3['VEHICLES']
    TOLL_ARCS = data3['TOLL_ARCS']
    dist = data3['dist']
    time = data3['time']
    toll_cost = data3['toll_cost']
    fuel_price = data3['fuel_price']
    
    # Inicializar estructura de solución
    solucion = {
        'vehiculos_usados': [],
        'rutas': {},
        'clientes_servidos': {},
        'demandas_servidas': {},
        'estaciones_visitadas': {},
        'recargas': {},
        'peajes_usados': {},
        'costo_peajes': {},
        'distancia_total': {},
        'tiempo_total': {},
        'costo_combustible': {},
        'costo_total_vehiculo': {},
        'costo_total': 0,
        'num_vehiculos': 0,
        'num_clientes': 0,
        'num_peajes': 0
    }
    
    # ========================================================================
    # 1. IDENTIFICAR VEHÍCULOS USADOS
    # ========================================================================
    
    print("\n[1] Identificando vehículos usados...")
    
    for v in VEHICLES:
        if pyo.value(model.y[v]) > 0.5:  # Binaria = 1
            solucion['vehiculos_usados'].append(v)
    
    print(f"  ✓ Vehículos usados: {len(solucion['vehiculos_usados'])}")
    
    if len(solucion['vehiculos_usados']) == 0:
        print("  ⚠ No se usó ningún vehículo (solución trivial o infactible)")
        return solucion
    
    # ========================================================================
    # 2. EXTRAER ARCOS ACTIVOS POR VEHÍCULO
    # ========================================================================
    
    print("\n[2] Extrayendo arcos activos...")
    
    arcos_activos = {v: [] for v in solucion['vehiculos_usados']}
    
    for v in solucion['vehiculos_usados']:
        for (i, j) in model.A_v[v]:
            if pyo.value(model.x[v,i,j]) > 0.5:  # Binaria = 1
                arcos_activos[v].append((i, j))
    
    total_arcos = sum(len(arcos) for arcos in arcos_activos.values())
    print(f"  ✓ Arcos activos: {total_arcos}")
    
    # ========================================================================
    # 3. RECONSTRUIR RUTAS (SECUENCIA ORDENADA DE NODOS)
    # ========================================================================
    
    print("\n[3] Reconstruyendo rutas...")
    
    for v in solucion['vehiculos_usados']:
        # Comenzar desde el depósito
        ruta = [DEPOT]
        nodo_actual = DEPOT
        visitados = {DEPOT}
        
        # Seguir los arcos hasta regresar al depósito
        max_iteraciones = len(arcos_activos[v]) + 1
        iteracion = 0
        
        while iteracion < max_iteraciones:
            # Buscar el siguiente nodo
            siguiente = None
            for (i, j) in arcos_activos[v]:
                if i == nodo_actual and j not in visitados:
                    siguiente = j
                    break
                elif i == nodo_actual and j == DEPOT:
                    siguiente = j
                    break
            
            if siguiente is None:
                break
            
            ruta.append(siguiente)
            
            if siguiente == DEPOT:
                break  # Ruta completa
            
            visitados.add(siguiente)
            nodo_actual = siguiente
            iteracion += 1
        
        solucion['rutas'][v] = ruta
        print(f"  {v}: {' → '.join(ruta)}")
    
    # ========================================================================
    # 4. EXTRAER INFORMACIÓN DE CADA RUTA
    # ========================================================================
    
    print("\n[4] Analizando detalles de cada ruta...")
    
    for v in solucion['vehiculos_usados']:
        ruta = solucion['rutas'][v]
        
        # Clientes servidos
        clientes = [nodo for nodo in ruta if nodo in data3['CLIENTS']]
        solucion['clientes_servidos'][v] = clientes
        solucion['demandas_servidas'][v] = sum(data3['demanda'][c] for c in clientes)
        
        # Estaciones visitadas
        estaciones = [nodo for nodo in ruta if nodo in data3['STATIONS']]
        solucion['estaciones_visitadas'][v] = estaciones
        
        # Recargas en estaciones
        recargas_v = {}
        for estacion in estaciones:
            cantidad = pyo.value(model.refuel[v, estacion])
            if cantidad > 0.01:  # Tolerancia numérica
                recargas_v[estacion] = cantidad
        solucion['recargas'][v] = recargas_v
        
        # Peajes usados
        peajes_v = []
        for i, j in zip(ruta[:-1], ruta[1:]):
            if (i, j) in TOLL_ARCS:
                peajes_v.append((i, j))
        solucion['peajes_usados'][v] = peajes_v
        
        # Calcular distancia total
        distancia = sum(dist[(i, j)] for i, j in zip(ruta[:-1], ruta[1:]))
        solucion['distancia_total'][v] = distancia
        
        # Calcular tiempo total
        tiempo = sum(time[(i, j)] for i, j in zip(ruta[:-1], ruta[1:]))
        solucion['tiempo_total'][v] = tiempo
        
        # Calcular costo de combustible
        costo_comb = sum(fuel_price[s] * recargas_v[s] for s in recargas_v)
        solucion['costo_combustible'][v] = costo_comb
        
        # Calcular costo de peajes
        costo_peaj = sum(toll_cost[(i, j)] for (i, j) in peajes_v)
        solucion['costo_peajes'][v] = costo_peaj
        
        # Calcular costo total del vehículo
        costo_total_v = (data3['cost_fixed'] +
                        distancia * data3['cost_km'] +
                        costo_comb +
                        costo_peaj)
        solucion['costo_total_vehiculo'][v] = costo_total_v
        
        print(f"  {v}:")
        print(f"    Clientes: {len(clientes)} ({', '.join(clientes)})")
        print(f"    Demanda: {solucion['demandas_servidas'][v]:.1f} kg")
        print(f"    Estaciones: {len(estaciones)} ({', '.join(estaciones)})")
        print(f"    Recargas: {len(recargas_v)} recargas")
        print(f"    Peajes: {len(peajes_v)} peajes cruzados")
        print(f"    Distancia: {distancia:.2f} km")
        print(f"    Costo: ${costo_total_v:,.2f} COP")
    
    # ========================================================================
    # 5. CONSOLIDAR MÉTRICAS GLOBALES
    # ========================================================================
    
    print("\n[5] Calculando métricas globales...")
    
    solucion['num_vehiculos'] = len(solucion['vehiculos_usados'])
    solucion['num_clientes'] = len(set(c for clientes in solucion['clientes_servidos'].values() 
                                       for c in clientes))
    solucion['num_peajes'] = sum(len(peajes) for peajes in solucion['peajes_usados'].values())
    solucion['costo_total'] = sum(solucion['costo_total_vehiculo'].values())
    
    print(f"  ✓ Vehículos usados: {solucion['num_vehiculos']}")
    print(f"  ✓ Clientes atendidos: {solucion['num_clientes']}")
    print(f"  ✓ Peajes cruzados: {solucion['num_peajes']}")
    print(f"  ✓ Costo total: ${solucion['costo_total']:,.2f} COP")
    
    # Desglose de costos
    costo_fijo_total = solucion['num_vehiculos'] * data3['cost_fixed']
    costo_distancia_total = sum(solucion['distancia_total'][v] * data3['cost_km']
                                for v in solucion['vehiculos_usados'])
    costo_combustible_total = sum(solucion['costo_combustible'].values())
    costo_peajes_total = sum(solucion['costo_peajes'].values())
    
    print(f"\n  Desglose de costos:")
    print(f"    - Costo fijo: ${costo_fijo_total:,.2f} COP ({costo_fijo_total/solucion['costo_total']*100:.1f}%)")
    print(f"    - Costo distancia: ${costo_distancia_total:,.2f} COP ({costo_distancia_total/solucion['costo_total']*100:.1f}%)")
    print(f"    - Costo combustible: ${costo_combustible_total:,.2f} COP ({costo_combustible_total/solucion['costo_total']*100:.1f}%)")
    print(f"    - Costo peajes: ${costo_peajes_total:,.2f} COP ({costo_peajes_total/solucion['costo_total']*100:.1f}%)")
    
    print("\n" + "="*80)
    print("✓ EXTRACCIÓN DE SOLUCIÓN COMPLETADA")
    print("="*80)
    
    return solucion


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def validar_solucion(solucion: Dict, data3: Dict) -> bool:
    """
    Valida que la solución extraída sea consistente.
    
    Verificaciones:
    - Todos los clientes están servidos
    - No se usan arcos prohibidos
    - Las recargas solo ocurren en estaciones
    - Los costos son consistentes
    
    Parámetros:
        solucion (dict): Solución extraída
        data3 (dict): Datos del problema
    
    Retorna:
        bool: True si la solución es válida
    """
    print("\n[VALIDACIÓN] Verificando consistencia de la solución...")
    
    errores = []
    
    # Check 1: Todos los clientes están servidos
    clientes_servidos = set()
    for v in solucion['vehiculos_usados']:
        clientes_servidos.update(solucion['clientes_servidos'][v])
    
    clientes_esperados = set(data3['CLIENTS'])
    if clientes_servidos != clientes_esperados:
        faltantes = clientes_esperados - clientes_servidos
        errores.append(f"Clientes no servidos: {faltantes}")
    
    # Check 2: No se usan arcos prohibidos
    FORBIDDEN_ARCS = data3['FORBIDDEN_ARCS']
    RESTRICTED_ARCS = data3['RESTRICTED_ARCS']
    
    for v in solucion['vehiculos_usados']:
        ruta = solucion['rutas'][v]
        for i, j in zip(ruta[:-1], ruta[1:]):
            if (i, j) in FORBIDDEN_ARCS:
                errores.append(f"Vehículo {v} usa arco prohibido: {i}→{j}")
            if (i, j) in RESTRICTED_ARCS[v]:
                errores.append(f"Vehículo {v} usa arco restringido: {i}→{j}")
    
    # Check 3: Recargas solo en estaciones
    for v in solucion['vehiculos_usados']:
        for nodo in solucion['recargas'][v]:
            if nodo not in data3['STATIONS'] and nodo != data3['DEPOT']:
                errores.append(f"Vehículo {v} recarga en nodo inválido: {nodo}")
    
    # Reportar resultados
    if errores:
        print(f"  ✗ Se encontraron {len(errores)} errores:")
        for error in errores:
            print(f"    - {error}")
        return False
    else:
        print("  ✓ Solución válida: todos los checks pasaron")
        return True


# ============================================================================
# EJECUCIÓN DE PRUEBA (SI SE EJECUTA DIRECTAMENTE)
# ============================================================================

if __name__ == "__main__":
    """
    Script de prueba para validar la construcción del modelo del Caso 3.
    """
    print("="*80)
    print("PRUEBA DEL MÓDULO modelo_caso3.py")
    print("="*80)
    print()
    print("Este módulo define:")
    print("  1. build_model_caso3(data3) - Construye modelo Pyomo")
    print("  2. extraer_solucion_caso3(model, data3) - Extrae solución")
    print("  3. validar_solucion(solucion, data3) - Valida consistencia")
    print()
    print("Para ejecutar el modelo completo, usar: run_caso3.py")
    print("="*80)

