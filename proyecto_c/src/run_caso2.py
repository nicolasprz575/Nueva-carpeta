"""
run_caso2.py

Script principal para ejecutar el Caso 2 de Proyecto C:
CVRP con capacidad de carga + restricciones de combustible + estaciones de recarga.

Flujo de ejecución:
1. Cargar datos del Caso 2 (con JOIN al Caso Base para coordenadas)
2. Construir modelo de optimización MILP con Pyomo
3. Resolver con HiGHS (solver MIP)
4. Extraer solución y generar outputs
5. Generar verificacion_caso2.csv
6. Generar visualización rutas_caso2.png

Autor: Proyecto C - Caso 2
"""

import os
import sys
import csv
from pathlib import Path
from typing import Dict, List, Any
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# Importar módulos del proyecto
from datos_caso2 import cargar_datos_caso2
from modelo_caso2 import build_model_caso2, extraer_solucion_caso2
from pyomo.opt import SolverFactory
import pyomo.environ as pyo


# ============================================================================
# FUNCIÓN: EXPORTAR VERIFICACIÓN CASO 2
# ============================================================================

def exportar_verificacion_caso2(solucion: dict, data2: dict, path_csv: str) -> None:
    """
    Genera el archivo CSV de verificación para el Caso 2.
    
    Formato extendido del Caso 1 que incluye información de combustible y estaciones.
    
    Args:
        solucion: Diccionario con la solución extraída (de extraer_solucion_caso2)
        data2: Diccionario con los datos originales (de cargar_datos_caso2)
        path_csv: Ruta completa al archivo CSV de salida
    
    Formato del CSV:
    ----------------
    Columnas:
    - VehicleId: ID del vehículo (V001, V002, ...)
    - DepotId: ID del depósito (CD01)
    - InitialLoad: Carga inicial (siempre 0)
    - InitialFuel: Combustible inicial en galones (capacidad del tanque)
    - RouteSequence: Secuencia completa de nodos (ej. CD01-E003-C015-E002-C007-CD01)
    - ClientsServed: Número de clientes atendidos
    - DemandsSatisfied: Suma de demandas atendidas (kg)
    - StationsVisited: Lista de estaciones visitadas (ej. E003,E002)
    - RefuelAmounts: Cantidades recargadas en cada estación (galones, ej. 15.5,8.3)
    - TotalDistance: Distancia total recorrida (km)
    - TotalTime: Tiempo total estimado (horas)
    - FuelConsumed: Combustible consumido total (galones)
    - FuelCost: Costo total de combustible (COP)
    - TotalCost: Costo total del vehículo (fijo + distancia + combustible, COP)
    
    Solo se incluyen vehículos realmente usados (y[v] = 1).
    """
    
    DEPOT = data2['DEPOT']
    CLIENTS = data2['CLIENTS']
    STATIONS = data2['STATIONS']
    demanda = data2['demanda']
    fuel_cap = data2['fuel_cap']
    fuel_efficiency = data2['fuel_efficiency']
    C_fixed = data2['C_fixed']
    C_km = data2['C_km']
    
    # Velocidad promedio para calcular tiempo (asumimos 50 km/h en rutas nacionales)
    VELOCIDAD_PROMEDIO = 50.0  # km/h
    
    # Crear directorio si no existe
    Path(path_csv).parent.mkdir(parents=True, exist_ok=True)
    
    # Preparar datos para escribir
    filas = []
    
    for vehicle_id in solucion['vehiculos_usados']:
        ruta = solucion['rutas'][vehicle_id]
        distancia_v = solucion['distancias'][vehicle_id]
        carga_v = solucion['cargas'][vehicle_id]
        
        # Secuencia de ruta
        route_sequence = '-'.join(ruta)
        
        # Contar clientes atendidos
        clientes_atendidos = [n for n in ruta if n in CLIENTS]
        num_clients = len(clientes_atendidos)
        
        # Suma de demandas
        demandas_satisfechas = sum(demanda[c] for c in clientes_atendidos)
        
        # Extraer estaciones visitadas y recargas
        recargas = solucion['recargas'][vehicle_id]
        estaciones_visitadas = [r['nodo'] for r in recargas if r['nodo'] in STATIONS]
        cantidades_recargadas = [r['cantidad'] for r in recargas if r['nodo'] in STATIONS]
        
        stations_visited_str = ','.join(estaciones_visitadas) if estaciones_visitadas else 'None'
        refuel_amounts_str = ','.join([f"{qty:.2f}" for qty in cantidades_recargadas]) if cantidades_recargadas else '0.0'
        
        # Calcular tiempo total (distancia / velocidad)
        total_time = distancia_v / VELOCIDAD_PROMEDIO
        
        # Combustible consumido
        fuel_consumed = solucion['combustible'][vehicle_id]['consumo_total']
        
        # Costo de combustible
        fuel_cost = sum(r['costo'] for r in recargas)
        
        # Costo total del vehículo
        costo_fijo_v = C_fixed
        costo_distancia_v = C_km * distancia_v
        total_cost = costo_fijo_v + costo_distancia_v + fuel_cost
        
        # Combustible inicial
        initial_fuel = fuel_cap[vehicle_id]
        
        # Agregar fila
        fila = {
            'VehicleId': vehicle_id,
            'DepotId': DEPOT,
            'InitialLoad': 0.0,
            'InitialFuel': f"{initial_fuel:.2f}",
            'RouteSequence': route_sequence,
            'ClientsServed': num_clients,
            'DemandsSatisfied': f"{demandas_satisfechas:.2f}",
            'StationsVisited': stations_visited_str,
            'RefuelAmounts': refuel_amounts_str,
            'TotalDistance': f"{distancia_v:.2f}",
            'TotalTime': f"{total_time:.2f}",
            'FuelConsumed': f"{fuel_consumed:.2f}",
            'FuelCost': f"{fuel_cost:.2f}",
            'TotalCost': f"{total_cost:.2f}"
        }
        
        filas.append(fila)
    
    # Escribir archivo CSV
    columnas = [
        'VehicleId', 'DepotId', 'InitialLoad', 'InitialFuel', 'RouteSequence',
        'ClientsServed', 'DemandsSatisfied', 'StationsVisited', 'RefuelAmounts',
        'TotalDistance', 'TotalTime', 'FuelConsumed', 'FuelCost', 'TotalCost'
    ]
    
    with open(path_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=columnas)
        writer.writeheader()
        writer.writerows(filas)
    
    print(f"\n✓ Archivo de verificación generado: {path_csv}")
    print(f"  - Filas escritas: {len(filas)} vehículos")


# ============================================================================
# FUNCIÓN: GENERAR TABLA DE COMBUSTIBLE
# ============================================================================

def exportar_combustible_caso2(solucion: dict, data2: dict, path_csv: str) -> None:
    """
    Genera una tabla detallada de consumo y recargas de combustible por vehículo.
    
    Args:
        solucion: Diccionario con la solución extraída
        data2: Diccionario con los datos originales
        path_csv: Ruta al archivo CSV de salida
    
    Formato del CSV:
    ----------------
    Columnas:
    - VehicleId: ID del vehículo
    - InitialFuel: Combustible inicial (galones)
    - TotalConsumed: Combustible consumido total (galones)
    - TotalRefueled: Combustible recargado total (galones)
    - FinalFuel: Combustible final al regresar al depósito (galones)
    - RefuelStops: Número de paradas de recarga
    - TotalFuelCost: Costo total de combustible (COP)
    - AvgFuelPrice: Precio promedio pagado por galón (COP/gal)
    """
    
    fuel_cap = data2['fuel_cap']
    
    # Crear directorio si no existe
    Path(path_csv).parent.mkdir(parents=True, exist_ok=True)
    
    filas = []
    
    for vehicle_id in solucion['vehiculos_usados']:
        combustible_info = solucion['combustible'][vehicle_id]
        recargas = solucion['recargas'][vehicle_id]
        
        initial_fuel = fuel_cap[vehicle_id]
        total_consumed = combustible_info['consumo_total']
        total_refueled = sum(r['cantidad'] for r in recargas)
        final_fuel = initial_fuel + total_refueled - total_consumed
        refuel_stops = len([r for r in recargas if r['cantidad'] > 0.01])
        total_fuel_cost = sum(r['costo'] for r in recargas)
        avg_fuel_price = total_fuel_cost / total_refueled if total_refueled > 0 else 0
        
        fila = {
            'VehicleId': vehicle_id,
            'InitialFuel': f"{initial_fuel:.2f}",
            'TotalConsumed': f"{total_consumed:.2f}",
            'TotalRefueled': f"{total_refueled:.2f}",
            'FinalFuel': f"{final_fuel:.2f}",
            'RefuelStops': refuel_stops,
            'TotalFuelCost': f"{total_fuel_cost:.2f}",
            'AvgFuelPrice': f"{avg_fuel_price:.2f}"
        }
        
        filas.append(fila)
    
    # Escribir archivo CSV
    columnas = [
        'VehicleId', 'InitialFuel', 'TotalConsumed', 'TotalRefueled',
        'FinalFuel', 'RefuelStops', 'TotalFuelCost', 'AvgFuelPrice'
    ]
    
    with open(path_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=columnas)
        writer.writeheader()
        writer.writerows(filas)
    
    print(f"✓ Tabla de combustible generada: {path_csv}")
    print(f"  - Filas escritas: {len(filas)} vehículos")


# ============================================================================
# FUNCIÓN: VISUALIZAR RUTAS CASO 2
# ============================================================================

def visualizar_rutas_caso2(solucion: dict, data2: dict, path_png: str) -> None:
    """
    Genera una visualización de las rutas del Caso 2 incluyendo estaciones.
    
    Args:
        solucion: Diccionario con la solución extraída
        data2: Diccionario con los datos originales
        path_png: Ruta al archivo PNG de salida
    
    Elementos visualizados:
    - Depósito: Triángulo rojo grande
    - Clientes: Círculos azules
    - Estaciones: Cuadrados verdes
    - Rutas: Líneas de colores con flechas
    """
    
    DEPOT = data2['DEPOT']
    CLIENTS = data2['CLIENTS']
    STATIONS = data2['STATIONS']
    coords = data2['coords']
    
    # Crear directorio si no existe
    Path(path_png).parent.mkdir(parents=True, exist_ok=True)
    
    # Configurar figura
    fig, ax = plt.subplots(figsize=(14, 10))
    
    # Colores para rutas
    colores_rutas = ['red', 'blue', 'green', 'orange', 'purple', 'brown', 'pink', 'gray']
    
    # Dibujar rutas
    for idx, vehicle_id in enumerate(solucion['vehiculos_usados']):
        ruta = solucion['rutas'][vehicle_id]
        color = colores_rutas[idx % len(colores_rutas)]
        
        # Coordenadas de la ruta
        lats = [coords[nodo][0] for nodo in ruta]
        lons = [coords[nodo][1] for nodo in ruta]
        
        # Dibujar línea de ruta
        ax.plot(lons, lats, color=color, linewidth=2, alpha=0.7, 
                label=f'{vehicle_id} ({solucion["distancias"][vehicle_id]:.1f} km)',
                marker='o', markersize=4)
        
        # Dibujar flechas direccionales
        for i in range(len(ruta) - 1):
            lon_i, lat_i = coords[ruta[i]][1], coords[ruta[i]][0]
            lon_j, lat_j = coords[ruta[i+1]][1], coords[ruta[i+1]][0]
            
            # Flecha en el punto medio del segmento
            mid_lon = (lon_i + lon_j) / 2
            mid_lat = (lat_i + lat_j) / 2
            dlon = lon_j - lon_i
            dlat = lat_j - lat_i
            
            ax.annotate('', xy=(mid_lon + dlon*0.1, mid_lat + dlat*0.1),
                       xytext=(mid_lon - dlon*0.1, mid_lat - dlat*0.1),
                       arrowprops=dict(arrowstyle='->', color=color, lw=1.5, alpha=0.6))
    
    # Dibujar nodos
    # Depósito
    depot_lat, depot_lon = coords[DEPOT]
    ax.plot(depot_lon, depot_lat, marker='^', markersize=20, color='red', 
            markeredgecolor='darkred', markeredgewidth=2, label='Depósito', zorder=10)
    ax.text(depot_lon, depot_lat + 0.01, DEPOT, fontsize=10, fontweight='bold',
            ha='center', va='bottom', color='darkred')
    
    # Clientes
    for client in CLIENTS:
        lat, lon = coords[client]
        ax.plot(lon, lat, marker='o', markersize=8, color='blue', 
                markeredgecolor='darkblue', markeredgewidth=1, zorder=5)
        ax.text(lon, lat + 0.005, client, fontsize=7, ha='center', va='bottom', color='darkblue')
    
    # Estaciones
    for station in STATIONS:
        lat, lon = coords[station]
        ax.plot(lon, lat, marker='s', markersize=10, color='green', 
                markeredgecolor='darkgreen', markeredgewidth=1.5, zorder=5)
        ax.text(lon, lat + 0.005, station, fontsize=7, ha='center', va='bottom', 
                color='darkgreen', fontweight='bold')
    
    # Configuración de ejes y leyenda
    ax.set_xlabel('Longitud', fontsize=12)
    ax.set_ylabel('Latitud', fontsize=12)
    ax.set_title('Rutas Optimizadas - Caso 2 (CVRP + Combustible + Estaciones)', 
                 fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.legend(loc='upper left', fontsize=9, framealpha=0.9)
    
    # Leyenda adicional de tipos de nodos
    legend_elements = [
        mpatches.Patch(color='red', label='Depósito (triángulo)'),
        mpatches.Patch(color='blue', label='Clientes (círculos)'),
        mpatches.Patch(color='green', label='Estaciones (cuadrados)')
    ]
    ax.legend(handles=legend_elements, loc='upper right', fontsize=9, framealpha=0.9)
    
    plt.tight_layout()
    plt.savefig(path_png, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"✓ Visualización generada: {path_png}")


# ============================================================================
# FUNCIÓN: IMPRIMIR RESUMEN DE SOLUCIÓN
# ============================================================================

def imprimir_resumen_solucion(solucion: dict, data2: dict) -> None:
    """
    Imprime un resumen detallado de la solución en consola.
    
    Args:
        solucion: Diccionario con la solución extraída
        data2: Diccionario con los datos originales
    """
    
    print("\n" + "=" * 80)
    print("RESUMEN DE SOLUCIÓN - CASO 2")
    print("=" * 80)
    
    print(f"\n📊 MÉTRICAS GENERALES:")
    print(f"  - Vehículos utilizados: {solucion['num_vehiculos']} de {data2['num_vehicles']}")
    print(f"  - Clientes atendidos: {solucion['clientes_visitados']} de {data2['num_clients']}")
    print(f"  - Distancia total: {solucion['distancia_total']:.2f} km")
    
    print(f"\n💰 COSTOS:")
    print(f"  - Costo fijo: ${solucion['costo_fijo']:,.0f} COP")
    print(f"  - Costo distancia: ${solucion['costo_distancia']:,.0f} COP")
    print(f"  - Costo combustible: ${solucion['costo_combustible']:,.0f} COP")
    print(f"  - COSTO TOTAL: ${solucion['costo_total']:,.0f} COP")
    
    print(f"\n🚛 DETALLE POR VEHÍCULO:")
    
    for vehicle_id in solucion['vehiculos_usados']:
        ruta = solucion['rutas'][vehicle_id]
        distancia_v = solucion['distancias'][vehicle_id]
        carga_v = solucion['cargas'][vehicle_id]
        combustible_v = solucion['combustible'][vehicle_id]
        recargas_v = solucion['recargas'][vehicle_id]
        
        print(f"\n  {vehicle_id}:")
        print(f"    - Ruta: {' → '.join(ruta)}")
        print(f"    - Clientes: {len([n for n in ruta if n in data2['CLIENTS']])}")
        print(f"    - Carga total: {carga_v:.2f} kg (cap: {data2['load_cap'][vehicle_id]:.2f} kg)")
        print(f"    - Distancia: {distancia_v:.2f} km")
        print(f"    - Combustible consumido: {combustible_v['consumo_total']:.2f} gal")
        print(f"    - Recargas: {len(recargas_v)} paradas")
        
        if recargas_v:
            print(f"    - Detalle de recargas:")
            for r in recargas_v:
                print(f"      * {r['nodo']}: {r['cantidad']:.2f} gal @ ${r['precio_unitario']:.0f}/gal = ${r['costo']:,.0f} COP")
    
    print("\n" + "=" * 80)


# ============================================================================
# FUNCIÓN PRINCIPAL
# ============================================================================

def main():
    """
    Función principal para ejecutar el Caso 2 completo.
    
    Flujo:
    1. Cargar datos (con JOIN al Caso Base)
    2. Construir modelo MILP
    3. Resolver con HiGHS
    4. Extraer solución
    5. Generar outputs (CSV, PNG)
    """
    
    print("\n" + "=" * 80)
    print("PROYECTO C - CASO 2")
    print("CVRP con Capacidad + Combustible + Estaciones de Recarga")
    print("=" * 80)
    
    # ========================================================================
    # PASO 1: DEFINIR RUTAS
    # ========================================================================
    
    # Directorio del proyecto (subir un nivel desde src/)
    proyecto_dir = Path(__file__).parent.parent
    
    # Ruta a los datos del Caso 2
    ruta_datos_caso2 = proyecto_dir.parent / 'project_c' / 'Proyecto_C_Caso2'
    
    # Ruta al Caso Base (para coordenadas)
    ruta_caso_base = proyecto_dir.parent / 'Proyecto_Caso_Base'
    
    # Ruta de salida
    ruta_resultados = proyecto_dir / 'results' / 'caso2'
    
    print(f"\n📁 RUTAS:")
    print(f"  - Datos Caso 2: {ruta_datos_caso2}")
    print(f"  - Caso Base: {ruta_caso_base}")
    print(f"  - Resultados: {ruta_resultados}")
    
    # ========================================================================
    # PASO 2: CARGAR DATOS
    # ========================================================================
    
    print("\n" + "=" * 80)
    print("CARGANDO DATOS DEL CASO 2")
    print("=" * 80)
    
    try:
        data2 = cargar_datos_caso2(str(ruta_datos_caso2), str(ruta_caso_base))
    except Exception as e:
        print(f"\n❌ ERROR al cargar datos: {e}")
        sys.exit(1)
    
    # ========================================================================
    # PASO 3: CONSTRUIR MODELO
    # ========================================================================
    
    print("\n" + "=" * 80)
    print("CONSTRUYENDO MODELO DE OPTIMIZACIÓN")
    print("=" * 80)
    
    try:
        # Construir modelo con escala de costos optimizada
        print(f"\n⚙️  Escalando costos de combustible para mejor condicionamiento numérico...")
        model = build_model_caso2(data2, scale_fuel_cost=0.001)  # Dividir costos por 1000
        print(f"\n✓ Modelo construido exitosamente")
        
        # Mostrar estadísticas del modelo
        num_vars = sum(1 for _ in model.component_data_objects(pyo.Var, active=True))
        num_constraints = sum(1 for _ in model.component_data_objects(pyo.Constraint, active=True))
        num_binary = sum(1 for v in model.component_data_objects(pyo.Var, active=True) 
                        if v.is_binary())
        print(f"  - Variables totales: {num_vars:,}")
        print(f"  - Variables binarias: {num_binary:,}")
        print(f"  - Restricciones: {num_constraints:,}")
    except Exception as e:
        print(f"\n❌ ERROR al construir modelo: {e}")
        sys.exit(1)
    
    # ========================================================================
    # PASO 4: RESOLVER MODELO
    # ========================================================================
    
    print("\n" + "=" * 80)
    print("RESOLVIENDO MODELO CON HIGHS")
    print("=" * 80)
    
    # Configurar solver
    solver_name = 'highs'
    solver = SolverFactory(solver_name)
    
    if not solver.available():
        print(f"\n⚠️  Solver '{solver_name}' no disponible, intentando con 'cbc'...")
        solver_name = 'cbc'
        solver = SolverFactory(solver_name)
        
        if not solver.available():
            print(f"\n❌ ERROR: No hay solvers MIP disponibles (intenté 'highs' y 'cbc')")
            print("   Instala HiGHS: pip install highspy")
            print("   O CBC: conda install -c conda-forge coincbc")
            sys.exit(1)
    
    # Configurar opciones del solver
    tiempo_limite = 180  # segundos (3 minutos - ajustado por complejidad del Caso 2)
    gap_optimalidad = 0.10  # 10% (más tolerante que Caso 1)
    
    if solver_name == 'highs':
        solver.options['time_limit'] = tiempo_limite
        solver.options['mip_rel_gap'] = gap_optimalidad
    elif solver_name == 'cbc':
        solver.options['seconds'] = tiempo_limite
        solver.options['ratio'] = gap_optimalidad
    
    print(f"\n⚙️  Configuración del solver:")
    print(f"  - Solver: {solver_name}")
    print(f"  - Tiempo límite: {tiempo_limite} segundos")
    print(f"  - Gap de optimalidad: {gap_optimalidad * 100}%")
    
    # Resolver
    print(f"\n🔄 Resolviendo... (esto puede tomar varios minutos)")
    
    try:
        results = solver.solve(model, tee=True, load_solutions=False)
    except Exception as e:
        print(f"\n❌ ERROR durante la resolución: {e}")
        sys.exit(1)
    
    # ========================================================================
    # PASO 5: VERIFICAR ESTADO DE LA SOLUCIÓN
    # ========================================================================
    
    print("\n" + "=" * 80)
    print("ESTADO DE LA SOLUCIÓN")
    print("=" * 80)
    
    termination = results.solver.termination_condition
    
    if termination == pyo.TerminationCondition.optimal:
        print("\n✅ Solución ÓPTIMA encontrada")
        model.solutions.load_from(results)
    elif termination == pyo.TerminationCondition.feasible:
        print("\n✅ Solución FACTIBLE encontrada (puede no ser óptima)")
        model.solutions.load_from(results)
    elif termination == pyo.TerminationCondition.maxTimeLimit:
        # Revisar si hay solución incumbent
        if hasattr(results, 'problem') and hasattr(results.problem, 'upper_bound'):
            if results.problem.upper_bound < float('inf'):
                print("\n⚠️  Límite de tiempo alcanzado, pero hay solución factible")
                model.solutions.load_from(results)
            else:
                print(f"\n❌ ERROR: Límite de tiempo alcanzado sin solución factible")
                print(f"   El problema puede ser infactible o necesita más tiempo/simplificación")
                print(f"\n💡 SUGERENCIAS:")
                print(f"   1. Aumentar tiempo_limite en run_caso2.py")
                print(f"   2. Reducir número de nodos (menos clientes o estaciones)")
                print(f"   3. Revisar restricciones de combustible (FuelCap, consumo, Big-M)")
                sys.exit(1)
        else:
            print(f"\n❌ ERROR: Límite de tiempo alcanzado sin solución factible")
            sys.exit(1)
    else:
        print(f"\n❌ ERROR: {termination}")
        print("   No se encontró una solución factible")
        print(f"\n💡 SUGERENCIAS:")
        print(f"   - Revisar restricciones de combustible")
        print(f"   - Verificar parámetros: FuelCap, fuel_efficiency, Big-M")
        print(f"   - Probar con instancia más pequeña")
        sys.exit(1)
    
    # Mostrar valor objetivo
    costo_total = pyo.value(model.objetivo)
    print(f"\n💰 Costo total: ${costo_total:,.0f} COP")
    
    # Gap final (si disponible)
    if hasattr(results.problem, 'upper_bound') and hasattr(results.problem, 'lower_bound'):
        gap_final = (results.problem.upper_bound - results.problem.lower_bound) / results.problem.upper_bound * 100
        print(f"📊 Gap final: {gap_final:.2f}%")
    
    # ========================================================================
    # PASO 6: EXTRAER SOLUCIÓN
    # ========================================================================
    
    print("\n" + "=" * 80)
    print("EXTRAYENDO SOLUCIÓN")
    print("=" * 80)
    
    try:
        solucion = extraer_solucion_caso2(model, data2)
        print("\n✓ Solución extraída exitosamente")
    except Exception as e:
        print(f"\n❌ ERROR al extraer solución: {e}")
        sys.exit(1)
    
    # Imprimir resumen
    imprimir_resumen_solucion(solucion, data2)
    
    # ========================================================================
    # PASO 7: GENERAR OUTPUTS
    # ========================================================================
    
    print("\n" + "=" * 80)
    print("GENERANDO ARCHIVOS DE SALIDA")
    print("=" * 80)
    
    # Crear directorio de resultados
    ruta_resultados.mkdir(parents=True, exist_ok=True)
    
    # 1. Archivo de verificación
    path_verificacion = ruta_resultados / 'verificacion_caso2.csv'
    try:
        exportar_verificacion_caso2(solucion, data2, str(path_verificacion))
    except Exception as e:
        print(f"\n⚠️  Error al generar verificacion_caso2.csv: {e}")
    
    # 2. Tabla de combustible
    path_combustible = ruta_resultados / 'combustible_caso2.csv'
    try:
        exportar_combustible_caso2(solucion, data2, str(path_combustible))
    except Exception as e:
        print(f"\n⚠️  Error al generar combustible_caso2.csv: {e}")
    
    # 3. Visualización de rutas
    path_visualizacion = ruta_resultados / 'rutas_caso2.png'
    try:
        visualizar_rutas_caso2(solucion, data2, str(path_visualizacion))
    except Exception as e:
        print(f"\n⚠️  Error al generar rutas_caso2.png: {e}")
    
    # ========================================================================
    # RESUMEN FINAL
    # ========================================================================
    
    print("\n" + "=" * 80)
    print("✅ CASO 2 COMPLETADO EXITOSAMENTE")
    print("=" * 80)
    
    print(f"\n📄 Archivos generados:")
    print(f"  - {path_verificacion}")
    print(f"  - {path_combustible}")
    print(f"  - {path_visualizacion}")
    
    print(f"\n🎯 Resultados clave:")
    print(f"  - Vehículos utilizados: {solucion['num_vehiculos']}")
    print(f"  - Clientes atendidos: {solucion['clientes_visitados']}")
    print(f"  - Distancia total: {solucion['distancia_total']:.2f} km")
    print(f"  - Costo total: ${solucion['costo_total']:,.0f} COP")
    
    print("\n" + "=" * 80)


# ============================================================================
# PUNTO DE ENTRADA
# ============================================================================

if __name__ == "__main__":
    main()
