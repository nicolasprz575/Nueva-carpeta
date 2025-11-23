"""
modelo_caso1.py
---------------
Modelo de optimización CVRP (Capacitated Vehicle Routing Problem) para el Caso 1 (Proyecto C).

Este módulo implementa un modelo de programación lineal entera mixta (MILP) en Pyomo para
resolver el problema de ruteo de vehículos con capacidad y autonomía limitadas.

CARACTERÍSTICAS DEL MODELO:
  - Flota homogénea de vehículos con capacidades y autonomías variables
  - Un único depósito (CD01 - Puerto de Barranquilla)
  - Múltiples clientes (municipios) con demandas conocidas
  - Restricciones de capacidad de carga
  - Restricciones de autonomía (distancia máxima por vehículo)
  - Función objetivo con costos fijos y variables por distancia

FORMULACIÓN OPTIMIZADA:
  Variables de decisión:
    - x[v,i,j]: binaria, 1 si el vehículo v recorre el arco i→j (solo arcos válidos)
    - y[v]: binaria, 1 si el vehículo v se utiliza
    - u[v,i]: continua MTZ, orden de visita para eliminar subtours

  Función objetivo:
    Minimizar: Costo_fijo * Σy[v] + Costo_km * Σd[i,j]*x[v,i,j]

  Restricciones principales:
    1. Asignación: cada cliente visitado exactamente una vez
    2. Flujo depósito: vehículos usados salen y regresan al depósito
    3. Conservación de flujo: continuidad de rutas
    4. Capacidad: suma de demandas no excede capacidad del vehículo
    5. Autonomía: distancia total por vehículo no excede maxDist
    6. MTZ: eliminación de subtours con variables de orden
    7. Vinculación: x[v,i,j] activa y[v]

Autor: Asistente IA (GitHub Copilot)
Fecha: Noviembre 2025
"""

import pyomo.environ as pyo
from typing import Dict, List, Tuple, Any


def build_model(data: Dict) -> pyo.ConcreteModel:
    """
    Construye el modelo de optimización CVRP para el Caso 1.
    
    Args:
        data: Diccionario con conjuntos, parámetros y costos generado por cargar_datos_caso1()
              Claves esperadas: 'NODES', 'CLIENTS', 'VEHICLES', 'DEPOT', 'demanda', 'dist',
                               'load_cap', 'max_dist', 'cost_fixed', 'cost_km'
    
    Returns:
        modelo: Modelo Pyomo ConcreteModel listo para resolver
    """
    
    model = pyo.ConcreteModel(name="CVRP_Caso1_ProyectoC")
    
    # =============================
    # CONJUNTOS
    # =============================
    
    # V: Conjunto de vehículos disponibles
    model.V = pyo.Set(initialize=data['VEHICLES'], doc="Vehículos disponibles")
    
    # N: Conjunto de todos los nodos (depósito + clientes)
    model.N = pyo.Set(initialize=data['NODES'], doc="Todos los nodos (depósito + clientes)")
    
    # C: Conjunto de clientes (subset de N, sin el depósito)
    model.C = pyo.Set(initialize=data['CLIENTS'], doc="Clientes (municipios)")
    
    # Depósito único
    depot = data['DEPOT']
    
    print(f"✓ Conjuntos definidos: {len(model.V)} vehículos, {len(model.N)} nodos, {len(model.C)} clientes")
    
    # =============================
    # PARÁMETROS
    # =============================
    
    # d[i,j]: Distancia entre nodos i y j (km)
    model.d = pyo.Param(
        model.N, model.N,
        initialize=data['dist'],
        doc="Distancia entre nodos (km)"
    )
    
    # q[i]: Demanda del cliente i (kg)
    # Para el depósito, la demanda es 0
    demanda_con_depot = {depot: 0.0}
    demanda_con_depot.update(data['demanda'])
    model.q = pyo.Param(
        model.N,
        initialize=demanda_con_depot,
        doc="Demanda en cada nodo (kg)"
    )
    
    # Q[v]: Capacidad de carga del vehículo v (kg)
    model.Q = pyo.Param(
        model.V,
        initialize=data['load_cap'],
        doc="Capacidad de carga del vehículo (kg)"
    )
    
    # maxDist[v]: Autonomía máxima del vehículo v (km)
    model.maxDist = pyo.Param(
        model.V,
        initialize=data['max_dist'],
        doc="Autonomía máxima del vehículo (km)"
    )
    
    # Parámetros de costos
    model.C_fixed = pyo.Param(
        initialize=data['cost_fixed'],
        doc="Costo fijo por vehículo usado (COP)"
    )
    
    model.C_dist = pyo.Param(
        initialize=data['cost_km'],
        doc="Costo por kilómetro recorrido (COP/km)"
    )
    
    # Parámetros adicionales (preparados para extensión en Casos 2 y 3)
    model.C_time = pyo.Param(
        initialize=data.get('cost_time', 0.0),
        doc="Costo por minuto de tiempo (COP/min)"
    )
    
    model.C_fuel = pyo.Param(
        initialize=data.get('cost_fuel', 0.0),
        doc="Costo por galón de combustible (COP/galón)"
    )
    
    print(f"✓ Parámetros definidos: distancias, demandas, capacidades, costos")
    
    # =============================
    # VARIABLES DE DECISIÓN
    # =============================
    
    # x[v,i,j]: Variable binaria, 1 si el vehículo v recorre el arco i→j
    # OPTIMIZACIÓN: Solo crear variables para arcos válidos (no i→i, no depot→depot)
    def valid_arcs_init():
        """Genera solo los arcos válidos para reducir número de variables."""
        arcs = []
        for v in data['VEHICLES']:
            # Depot → Clientes
            for j in data['CLIENTS']:
                arcs.append((v, depot, j))
            # Cliente → Cliente
            for i in data['CLIENTS']:
                for j in data['CLIENTS']:
                    if i != j:
                        arcs.append((v, i, j))
            # Clientes → Depot
            for i in data['CLIENTS']:
                arcs.append((v, i, depot))
        return arcs
    
    model.ARCS = pyo.Set(initialize=valid_arcs_init(), dimen=3, doc="Arcos válidos (v,i,j)")
    
    model.x = pyo.Var(
        model.ARCS,
        domain=pyo.Binary,
        doc="1 si vehículo v recorre arco i→j"
    )
    
    # y[v]: Variable binaria, 1 si el vehículo v se utiliza
    model.y = pyo.Var(
        model.V,
        domain=pyo.Binary,
        doc="1 si vehículo v se utiliza"
    )
    
    # u[v,i]: Variable MTZ para orden de visita (elimina subtours)
    # Solo necesaria para clientes, no para el depósito
    model.u = pyo.Var(
        model.V, model.C,
        domain=pyo.NonNegativeReals,
        bounds=(1, len(data['CLIENTS'])),
        doc="Orden de visita del cliente i por vehículo v (MTZ)"
    )
    
    num_arcs = len(model.ARCS)
    print(f"✓ Variables definidas:")
    print(f"  - x[v,i,j]: {num_arcs:,} variables binarias (solo arcos válidos)")
    print(f"  - y[v]: {len(model.V)} variables binarias")
    print(f"  - u[v,i]: {len(model.V) * len(model.C):,} variables continuas (MTZ)")
    
    # =============================
    # RESTRICCIONES
    # =============================
    
    # -----------------------------------------------------------------
    # R1: ASIGNACIÓN DE CLIENTES
    # Cada cliente debe ser visitado exactamente una vez por algún vehículo
    # -----------------------------------------------------------------
    def rule_asignacion_clientes(model, i):
        """Cada cliente i debe ser visitado exactamente una vez."""
        return sum(model.x[v, j, i] for (v, j, k) in model.ARCS if k == i) == 1
    
    model.rest_asignacion = pyo.Constraint(
        model.C,
        rule=rule_asignacion_clientes,
        doc="Cada cliente visitado exactamente una vez"
    )
    
    # -----------------------------------------------------------------
    # R2: FLUJO EN EL DEPÓSITO
    # Si un vehículo se usa, debe salir del depósito exactamente una vez
    # y regresar al depósito exactamente una vez
    # -----------------------------------------------------------------
    def rule_salida_deposito(model, v):
        """Vehículo v sale del depósito una vez si se usa."""
        return sum(model.x[v, depot, j] for (veh, i, j) in model.ARCS if veh == v and i == depot) == model.y[v]
    
    model.rest_salida_deposito = pyo.Constraint(
        model.V,
        rule=rule_salida_deposito,
        doc="Vehículo usado sale del depósito una vez"
    )
    
    def rule_regreso_deposito(model, v):
        """Vehículo v regresa al depósito una vez si se usa."""
        return sum(model.x[v, i, depot] for (veh, i, j) in model.ARCS if veh == v and j == depot) == model.y[v]
    
    model.rest_regreso_deposito = pyo.Constraint(
        model.V,
        rule=rule_regreso_deposito,
        doc="Vehículo usado regresa al depósito una vez"
    )
    
    # -----------------------------------------------------------------
    # R3: CONSERVACIÓN DE FLUJO EN CLIENTES
    # Para cada cliente, lo que entra debe salir (por el mismo vehículo)
    # -----------------------------------------------------------------
    def rule_conservacion_flujo(model, v, i):
        """Para cada vehículo v y cliente i: flujo entrante = flujo saliente."""
        entrada = sum(model.x[veh, j, k] for (veh, j, k) in model.ARCS if veh == v and k == i)
        salida = sum(model.x[veh, i2, j] for (veh, i2, j) in model.ARCS if veh == v and i2 == i)
        return entrada == salida
    
    model.rest_conservacion = pyo.Constraint(
        model.V, model.C,
        rule=rule_conservacion_flujo,
        doc="Conservación de flujo en cada cliente"
    )
    
    # -----------------------------------------------------------------
    # R4: RESTRICCIÓN DE CAPACIDAD (Simplificada)
    # La suma de demandas atendidas por un vehículo no excede su capacidad
    # -----------------------------------------------------------------
    def rule_capacidad(model, v):
        """Capacidad total del vehículo v no debe excederse."""
        return sum(
            model.q[i] * sum(model.x[veh, j, i] for (veh, j, k) in model.ARCS if veh == v and k == i)
            for i in model.C
        ) <= model.Q[v]
    
    model.rest_capacidad = pyo.Constraint(
        model.V,
        rule=rule_capacidad,
        doc="Suma de demandas no excede capacidad"
    )
    
    # -----------------------------------------------------------------
    # R5: RESTRICCIÓN DE AUTONOMÍA (Distancia máxima por vehículo)
    # La suma de distancias de los arcos recorridos por un vehículo
    # no puede exceder su autonomía máxima
    # -----------------------------------------------------------------
    def rule_autonomia(model, v):
        """Distancia total recorrida por vehículo v no excede su autonomía."""
        return sum(
            model.d[i, j] * model.x[v, i, j]
            for (veh, i, j) in model.ARCS if veh == v
        ) <= model.maxDist[v]
    
    model.rest_autonomia = pyo.Constraint(
        model.V,
        rule=rule_autonomia,
        doc="Distancia total no excede autonomía del vehículo"
    )
    
    # -----------------------------------------------------------------
    # R6: ELIMINACIÓN DE SUBTOURS (MTZ - Miller-Tucker-Zemlin)
    # Variables u[v,i] representan el orden de visita
    # Si el vehículo v va de i a j (ambos clientes), entonces u[v,j] > u[v,i]
    # -----------------------------------------------------------------
    def rule_mtz(model, v, i, j):
        """Restricción MTZ para eliminar subtours."""
        if i == j:
            return pyo.Constraint.Skip
        # Solo aplicar entre clientes (no involucra el depósito)
        if i not in model.C or j not in model.C:
            return pyo.Constraint.Skip
        
        n = len(model.C)
        # Si x[v,i,j] = 1, entonces u[v,j] >= u[v,i] + 1
        # Formulación: u[v,i] - u[v,j] + n*x[v,i,j] <= n - 1
        if (v, i, j) in model.ARCS:
            return model.u[v, i] - model.u[v, j] + n * model.x[v, i, j] <= n - 1
        else:
            return pyo.Constraint.Skip
    
    model.rest_mtz = pyo.Constraint(
        model.V, model.C, model.C,
        rule=rule_mtz,
        doc="MTZ: eliminación de subtours"
    )
    
    # -----------------------------------------------------------------
    # R7: VINCULACIÓN x-y
    # Si algún arco x[v,i,j] = 1, entonces y[v] = 1
    # -----------------------------------------------------------------
    def rule_vinculacion_x_y(model, v, i, j):
        """Si vehículo v usa arco i→j, entonces y[v] = 1."""
        return model.x[v, i, j] <= model.y[v]
    
    model.rest_vinculacion = pyo.Constraint(
        model.ARCS,
        rule=rule_vinculacion_x_y,
        doc="Uso de arco implica uso de vehículo"
    )
    
    print(f"✓ Restricciones definidas: {len(list(model.component_objects(pyo.Constraint)))} grupos")
    
    # =============================
    # FUNCIÓN OBJETIVO
    # =============================
    
    # Minimizar el costo total:
    #   - Costo fijo por cada vehículo usado
    #   - Costo variable por kilómetro recorrido
    
    def rule_funcion_objetivo(model):
        """
        Función objetivo: Minimizar costo total.
        
        Componentes:
          1. Costo fijo: C_fixed * Σ y[v]
          2. Costo por distancia: C_dist * Σ d[i,j] * x[v,i,j]
        """
        # Costo fijo por vehículos usados
        costo_fijo = model.C_fixed * sum(model.y[v] for v in model.V)
        
        # Costo por distancia recorrida
        costo_distancia = model.C_dist * sum(
            model.d[i, j] * model.x[v, i, j]
            for (v, i, j) in model.ARCS
        )
        
        # Costo total
        return costo_fijo + costo_distancia
    
    model.objetivo = pyo.Objective(
        rule=rule_funcion_objetivo,
        sense=pyo.minimize,
        doc="Minimizar costo total (fijo + distancia)"
    )
    
    print(f"✓ Función objetivo definida: minimizar costo fijo + costo por distancia")
    print("\n" + "="*60)
    print("MODELO CONSTRUIDO EXITOSAMENTE (OPTIMIZADO)")
    print("="*60)
    print(f"Variables: {num_arcs + len(model.V) + len(model.V) * len(model.C):,}")
    print(f"  - x[v,i,j]: {num_arcs:,} variables binarias (reducción del {100*(1-num_arcs/(len(model.V)*len(model.N)**2)):.1f}%)")
    print(f"  - y[v]: {len(model.V)} variables binarias")
    print(f"  - u[v,i]: {len(model.V) * len(model.C):,} variables continuas (MTZ)")
    print(f"Restricciones: ~{len(model.C) + 2*len(model.V) + len(model.V)*len(model.C) + len(model.V) + len(model.V)*len(model.C)**2 + num_arcs:,}")
    print("="*60 + "\n")
    
    return model


def extraer_solucion(model: pyo.ConcreteModel, data: Dict) -> Dict[str, Any]:
    """
    Extrae la solución del modelo resuelto y la organiza en un formato legible.
    
    Args:
        model: Modelo Pyomo resuelto
        data: Diccionario de datos original (para obtener información adicional)
    
    Returns:
        Diccionario con la solución estructurada:
          - 'costo_total': Costo total del sistema
          - 'costo_fijo_total': Suma de costos fijos
          - 'costo_distancia_total': Suma de costos por distancia
          - 'num_vehiculos_usados': Número de vehículos utilizados
          - 'distancia_total_sistema': Distancia total recorrida por todos los vehículos
          - 'rutas': Lista de diccionarios, uno por cada vehículo usado, con:
              - 'vehiculo_id': ID del vehículo
              - 'ruta_indices': Lista ordenada de nodos visitados (IDs)
              - 'ruta_secuencia': String con la secuencia (ej: "CD01-C005-C012-CD01")
              - 'distancia_total': Distancia total de la ruta (km)
              - 'demanda_total': Demanda total atendida (kg)
              - 'demandas_por_cliente': Lista de demandas en orden de visita
              - 'costo_fijo': Costo fijo del vehículo
              - 'costo_distancia': Costo por distancia de la ruta
              - 'costo_total_ruta': Costo total de la ruta
    """
    
    print("\n" + "="*60)
    print("EXTRAYENDO SOLUCIÓN")
    print("="*60)
    
    depot = data['DEPOT']
    
    # Obtener valor de la función objetivo
    costo_total = pyo.value(model.objetivo)
    
    # Inicializar contadores
    num_vehiculos_usados = 0
    costo_fijo_total = 0.0
    costo_distancia_total = 0.0
    distancia_total_sistema = 0.0
    
    rutas = []
    
    # Iterar sobre cada vehículo
    for v in model.V:
        # Verificar si el vehículo se usa
        if pyo.value(model.y[v]) > 0.5:  # Tolerancia numérica
            num_vehiculos_usados += 1
            
            # Reconstruir la ruta del vehículo
            ruta = reconstruir_ruta(model, v, depot, data)
            
            if ruta:  # Si se encontró una ruta válida
                # Calcular métricas de la ruta
                distancia_total = calcular_distancia_ruta(ruta, data['dist'])
                demanda_total, demandas_por_cliente = calcular_demanda_ruta(ruta, data['demanda'], depot)
                
                # Calcular costos
                costo_fijo = pyo.value(model.C_fixed)
                costo_distancia = pyo.value(model.C_dist) * distancia_total
                costo_total_ruta = costo_fijo + costo_distancia
                
                # Acumular totales
                costo_fijo_total += costo_fijo
                costo_distancia_total += costo_distancia
                distancia_total_sistema += distancia_total
                
                # Crear secuencia como string
                ruta_secuencia = "-".join(ruta)
                
                # Guardar información de la ruta
                ruta_info = {
                    'vehiculo_id': v,
                    'ruta_indices': ruta,
                    'ruta_secuencia': ruta_secuencia,
                    'num_clientes': len(ruta) - 2,  # Sin contar depósito inicial y final
                    'distancia_total': round(distancia_total, 2),
                    'demanda_total': round(demanda_total, 1),
                    'demandas_por_cliente': [round(d, 1) for d in demandas_por_cliente],
                    'costo_fijo': round(costo_fijo, 2),
                    'costo_distancia': round(costo_distancia, 2),
                    'costo_total_ruta': round(costo_total_ruta, 2),
                    'capacidad_vehiculo': pyo.value(model.Q[v]),
                    'utilizacion_capacidad': round(demanda_total / pyo.value(model.Q[v]) * 100, 1),
                    'autonomia_vehiculo': pyo.value(model.maxDist[v]),
                    'utilizacion_autonomia': round(distancia_total / pyo.value(model.maxDist[v]) * 100, 1),
                }
                
                rutas.append(ruta_info)
                
                print(f"\n✓ Vehículo {v}:")
                print(f"  Ruta: {ruta_secuencia}")
                print(f"  Clientes atendidos: {len(ruta) - 2}")
                print(f"  Distancia: {distancia_total:.2f} km")
                print(f"  Demanda: {demanda_total:.1f} kg")
                print(f"  Utilización: {demanda_total / pyo.value(model.Q[v]) * 100:.1f}% capacidad, "
                      f"{distancia_total / pyo.value(model.maxDist[v]) * 100:.1f}% autonomía")
    
    # Verificar que todos los clientes fueron atendidos
    clientes_atendidos = set()
    for ruta_info in rutas:
        for nodo in ruta_info['ruta_indices']:
            if nodo != depot:
                clientes_atendidos.add(nodo)
    
    clientes_esperados = set(data['CLIENTS'])
    if clientes_atendidos != clientes_esperados:
        print("\n⚠ ADVERTENCIA: No todos los clientes fueron atendidos")
        print(f"  Esperados: {len(clientes_esperados)}")
        print(f"  Atendidos: {len(clientes_atendidos)}")
        clientes_faltantes = clientes_esperados - clientes_atendidos
        if clientes_faltantes:
            print(f"  Faltantes: {clientes_faltantes}")
    
    # Construir diccionario de solución
    solucion = {
        'costo_total': round(costo_total, 2),
        'costo_fijo_total': round(costo_fijo_total, 2),
        'costo_distancia_total': round(costo_distancia_total, 2),
        'num_vehiculos_usados': num_vehiculos_usados,
        'distancia_total_sistema': round(distancia_total_sistema, 2),
        'clientes_atendidos': len(clientes_atendidos),
        'clientes_totales': len(clientes_esperados),
        'rutas': rutas,
    }
    
    print("\n" + "="*60)
    print("RESUMEN DE SOLUCIÓN")
    print("="*60)
    print(f"Costo total: {costo_total:,.2f} COP")
    print(f"  - Costo fijo: {costo_fijo_total:,.2f} COP")
    print(f"  - Costo distancia: {costo_distancia_total:,.2f} COP")
    print(f"Vehículos usados: {num_vehiculos_usados}/{len(model.V)}")
    print(f"Distancia total: {distancia_total_sistema:.2f} km")
    print(f"Clientes atendidos: {len(clientes_atendidos)}/{len(clientes_esperados)}")
    print("="*60 + "\n")
    
    return solucion


def reconstruir_ruta(model: pyo.ConcreteModel, vehiculo: str, depot: str, data: Dict) -> List[str]:
    """
    Reconstruye la ruta ordenada de un vehículo a partir de las variables x[v,i,j].
    
    Args:
        model: Modelo Pyomo resuelto
        vehiculo: ID del vehículo
        depot: ID del depósito
        data: Diccionario de datos
    
    Returns:
        Lista ordenada de nodos visitados (IDs), comenzando y terminando en el depósito
    """
    # Construir diccionario de arcos activos para este vehículo
    arcos_activos = {}
    for (v, i, j) in model.ARCS:
        if v == vehiculo and pyo.value(model.x[v, i, j]) > 0.5:
            arcos_activos[i] = j
    
    if not arcos_activos:
        return []
    
    # Reconstruir ruta comenzando desde el depósito
    ruta = [depot]
    nodo_actual = depot
    max_iteraciones = len(data['NODES']) + 1  # Prevenir loops infinitos
    
    for _ in range(max_iteraciones):
        if nodo_actual in arcos_activos:
            siguiente_nodo = arcos_activos[nodo_actual]
            ruta.append(siguiente_nodo)
            nodo_actual = siguiente_nodo
            
            # Si regresamos al depósito, terminamos
            if nodo_actual == depot:
                break
        else:
            break
    
    return ruta


def calcular_distancia_ruta(ruta: List[str], dist: Dict[Tuple[str, str], float]) -> float:
    """
    Calcula la distancia total de una ruta.
    
    Args:
        ruta: Lista ordenada de nodos
        dist: Diccionario de distancias {(i, j): distancia}
    
    Returns:
        Distancia total en km
    """
    distancia_total = 0.0
    for i in range(len(ruta) - 1):
        nodo_actual = ruta[i]
        nodo_siguiente = ruta[i + 1]
        distancia_total += dist[(nodo_actual, nodo_siguiente)]
    
    return distancia_total


def calcular_demanda_ruta(ruta: List[str], demanda: Dict[str, float], depot: str) -> Tuple[float, List[float]]:
    """
    Calcula la demanda total atendida en una ruta y las demandas individuales.
    
    Args:
        ruta: Lista ordenada de nodos
        demanda: Diccionario de demandas {cliente_id: demanda}
        depot: ID del depósito
    
    Returns:
        Tupla (demanda_total, lista_demandas_por_cliente)
    """
    demanda_total = 0.0
    demandas_por_cliente = []
    
    for nodo in ruta:
        if nodo != depot:
            dem = demanda[nodo]
            demanda_total += dem
            demandas_por_cliente.append(dem)
    
    return demanda_total, demandas_por_cliente
