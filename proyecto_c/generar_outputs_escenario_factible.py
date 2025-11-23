"""
generar_outputs_escenario_factible.py
======================================
Genera outputs oficiales del Caso 2 usando el escenario factible más grande
identificado en los tests de escalabilidad.

IMPORTANTE: Este script usa un SUBCONJUNTO de clientes del Caso 2 completo.
El problema completo con 14 clientes resultó ser computacionalmente intratable
dentro del tiempo disponible (no encontró solución factible en 600s).

El escenario usado aquí representa una instancia OPERATIVA del Caso 2 donde:
- Se incluyen los clientes MÁS LEJANOS (que requieren estaciones de recarga)
- Se mantienen TODAS las estaciones de servicio (12)
- Se usa la FLOTA COMPLETA de vehículos (5)
- El modelo COMPLETO con restricciones de combustible y recargas

CLIENTES INCLUIDOS: Se determina automáticamente al ejecutar este script
basado en los resultados del test de escalabilidad.

Outputs generados:
1. results/caso2/verificacion_caso2.csv - Datos detallados de rutas
2. results/caso2/rutas_caso2.png - Visualización de rutas

Autor: Asistente IA (GitHub Copilot)
Fecha: Noviembre 2025
"""

import os
import sys
import csv
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import pyomo.environ as pyo
from pyomo.opt import SolverFactory

# Importar módulos
sys.path.insert(0, str(Path(__file__).parent / 'src'))
from datos_caso2 import cargar_datos_caso2
from modelo_caso2 import build_model_caso2

# Rutas
PROJECT_ROOT = Path(__file__).parent
RESULTS_DIR = PROJECT_ROOT / 'results' / 'caso2'
DATA_CASO2 = PROJECT_ROOT.parent / 'project_c' / 'Proyecto_C_Caso2'
DATA_BASE = PROJECT_ROOT.parent / 'Proyecto_Caso_Base'

# CONFIGURACIÓN DEL ESCENARIO
# Estos valores se deben actualizar según los resultados del test de escalabilidad
N_CLIENTES_ESCENARIO = None  # Se determinará automáticamente leyendo test_escalabilidad_resultados.txt
TIME_LIMIT = 300  # 5 minutos para obtener mejor solución
GAP_TOLERANCE = 0.15  # 15% de gap aceptable

# Clientes ordenados por distancia (más lejanos primero)
CLIENTES_LEJANOS = [
    'C005',  # ~706 km
    'C014',  # ~698 km
    'C007',  # ~676 km
    'C010',  # ~620 km
    'C012',  # ~580 km
    'C008',  # ~550 km
    'C013',  # ~520 km
    'C009',  # ~480 km
    'C006',  # ~450 km
    'C011',  # ~420 km
    'C004',  # ~380 km
    'C003',  # ~340 km
    'C002',  # ~280 km
    'C001',  # ~240 km
]


def determinar_escenario_factible():
    """
    Lee los resultados del test de escalabilidad y determina
    el número máximo de clientes que se pudo resolver.
    """
    resultado_file = PROJECT_ROOT / 'test_escalabilidad_resultados.txt'
    
    if not resultado_file.exists():
        print("⚠️  No se encontró test_escalabilidad_resultados.txt")
        print("   Usando escenario por defecto: 6 clientes")
        return 6
    
    # Leer archivo y buscar escenarios factibles
    with open(resultado_file, 'r', encoding='utf-8') as f:
        contenido = f.read()
    
    # Buscar el máximo número de clientes con status factible
    max_factible = 2  # Por defecto al menos 2 clientes
    
    for linea in contenido.split('\n'):
        if 'Escenario:' in linea and 'clientes' in linea:
            try:
                n = int(linea.split(':')[1].strip().split()[0])
            except:
                continue
        elif 'Status:' in linea:
            if 'optimal' in linea.lower() or 'feasible' in linea.lower():
                max_factible = max(max_factible, n)
    
    print(f"✓ Escenario factible más grande identificado: {max_factible} clientes")
    return max_factible


def extraer_solucion_completa(model, data2):
    """Extrae la solución del modelo con datos completos de combustible"""
    
    vehiculos = data2['VEHICLES']
    DEPOT = data2['DEPOT']
    CLIENTS = data2['CLIENTS']
    STATIONS = data2['STATIONS']
    dist = data2['dist']
    demanda = data2['demanda']
    fuel_cap = data2['fuel_cap']
    fuel_efficiency = data2['fuel_efficiency']
    fuel_price = data2['fuel_price']
    
    solucion = {
        'rutas': {},
        'vehiculos_usados': [],
        'distancias': {},
        'cargas': {},
        'combustible': {},  # Niveles de combustible por nodo
        'recargas': {},  # Recargas por estación
        'costo_total': 0,
        'costo_fijo': 0,
        'costo_distancia': 0,
        'costo_combustible': 0,
        'distancia_total': 0,
        'num_vehiculos': 0,
        'clientes_visitados': 0
    }
    
    for vid in vehiculos:
        # Verificar si el vehículo fue usado
        if pyo.value(model.y[vid]) < 0.5:
            continue
        
        solucion['vehiculos_usados'].append(vid)
        solucion['num_vehiculos'] += 1
        
        # Reconstruir ruta
        ruta = [DEPOT]
        visitados = {DEPOT}
        actual = DEPOT
        
        while True:
            # Buscar próximo nodo
            siguiente = None
            for i, j in model.A:
                if i == actual and pyo.value(model.x[vid, i, j]) > 0.5:
                    siguiente = j
                    break
            
            if siguiente is None or siguiente == DEPOT:
                ruta.append(DEPOT)
                break
            
            if siguiente in visitados and siguiente != DEPOT:
                print(f"⚠️  Ciclo detectado en ruta de {vid}")
                break
            
            ruta.append(siguiente)
            visitados.add(siguiente)
            actual = siguiente
        
        solucion['rutas'][vid] = ruta
        
        # Calcular distancia de la ruta
        dist_ruta = 0
        for i in range(len(ruta) - 1):
            dist_ruta += dist[(ruta[i], ruta[i+1])]
        solucion['distancias'][vid] = dist_ruta
        solucion['distancia_total'] += dist_ruta
        
        # Calcular carga total entregada
        carga_total = sum(demanda.get(nodo, 0) for nodo in ruta if nodo in CLIENTS)
        solucion['cargas'][vid] = carga_total
        solucion['clientes_visitados'] += sum(1 for nodo in ruta if nodo in CLIENTS)
        
        # Extraer datos de combustible
        combustible_nodos = {}
        recargas_nodos = {}
        
        for nodo in ruta:
            fuel_level = pyo.value(model.combustible[vid, nodo])
            combustible_nodos[nodo] = fuel_level
            
            refuel_amount = pyo.value(model.recarga[vid, nodo])
            if refuel_amount > 0.1:  # Threshold para evitar ruido numérico
                recargas_nodos[nodo] = refuel_amount
        
        solucion['combustible'][vid] = combustible_nodos
        solucion['recargas'][vid] = recargas_nodos
    
    # Calcular costos
    solucion['costo_fijo'] = solucion['num_vehiculos'] * data2['C_fixed']
    solucion['costo_distancia'] = solucion['distancia_total'] * data2['C_km']
    
    # Costo de combustible (sumando todas las recargas)
    costo_fuel = 0
    for vid in solucion['vehiculos_usados']:
        for nodo, cantidad in solucion['recargas'][vid].items():
            precio = fuel_price.get(nodo, data2['fuel_price_depot'])
            costo_fuel += cantidad * precio
    
    solucion['costo_combustible'] = costo_fuel
    solucion['costo_total'] = solucion['costo_fijo'] + solucion['costo_distancia'] + solucion['costo_combustible']
    
    return solucion


def exportar_verificacion(solucion, data2, output_path):
    """
    Exporta CSV con columnas extendidas incluyendo información de combustible y estaciones
    """
    print(f"\nExportando verificación a: {output_path}")
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Header extendido
        writer.writerow([
            'VehicleId',
            'DepotId', 
            'InitialLoad',
            'InitialFuel',
            'RouteSequence',
            'ClientsServed',
            'DemandsSatisfied',
            'StationsVisited',
            'RefuelAmounts',
            'TotalDistance',
            'TotalTime',
            'FuelCost',
            'TotalCost'
        ])
        
        for vid in solucion['vehiculos_usados']:
            ruta = solucion['rutas'][vid]
            
            # Clientes servidos
            clientes = [nodo for nodo in ruta if nodo in data2['CLIENTS']]
            demandas = [data2['demanda'][c] for c in clientes]
            
            # Estaciones visitadas
            estaciones = [nodo for nodo in ruta if nodo in data2['STATIONS']]
            
            # Recargas
            recargas_info = []
            fuel_cost_veh = 0
            for est, cantidad in solucion['recargas'][vid].items():
                precio = data2['fuel_price'].get(est, data2['fuel_price_depot'])
                recargas_info.append(f"{est}:{cantidad:.1f}gal")
                fuel_cost_veh += cantidad * precio
            
            # Tiempo estimado
            tiempo_h = solucion['distancias'][vid] / 60  # Asumiendo 60 km/h promedio
            
            # Costo individual del vehículo
            costo_veh = (data2['C_fixed'] + 
                        solucion['distancias'][vid] * data2['C_km'] +
                        fuel_cost_veh)
            
            writer.writerow([
                vid,
                data2['DEPOT'],
                0,  # InitialLoad (sale vacío)
                data2['fuel_cap'][vid],  # InitialFuel (tanque lleno)
                ' -> '.join(ruta),
                ', '.join(clientes),
                ', '.join(f"{d:.1f}kg" for d in demandas),
                ', '.join(estaciones) if estaciones else 'NINGUNA',
                '; '.join(recargas_info) if recargas_info else 'NINGUNA',
                f"{solucion['distancias'][vid]:.2f}",
                f"{tiempo_h:.2f}",
                f"{fuel_cost_veh:.2f}",
                f"{costo_veh:.2f}"
            ])
    
    print(f"✓ Verificación exportada: {len(solucion['vehiculos_usados'])} vehículos")


def visualizar_rutas(solucion, data2, output_path):
    """
    Genera visualización de rutas destacando las estaciones donde se recarga
    """
    print(f"\nGenerando visualización de rutas...")
    
    fig, ax = plt.subplots(figsize=(14, 10))
    
    # Obtener coordenadas desde data2
    coords = {}
    
    # Cargar coordenadas originales
    depots_df = pd.read_csv(DATA_BASE / 'depots.csv')
    clients_df = pd.read_csv(DATA_BASE / 'clients.csv')
    stations_df = pd.read_csv(DATA_CASO2 / 'stations.csv')
    
    # Depot
    depot_row = depots_df[depots_df['DepotId'] == data2['DEPOT']].iloc[0]
    coords[data2['DEPOT']] = (depot_row['Latitude'], depot_row['Longitude'])
    
    # Clientes
    for _, row in clients_df.iterrows():
        coords[row['ClientId']] = (row['Latitude'], row['Longitude'])
    
    # Estaciones
    for _, row in stations_df.iterrows():
        coords[row['StationId']] = (row['Latitude'], row['Longitude'])
    
    # Identificar estaciones con recarga
    estaciones_con_recarga = set()
    for vid in solucion['vehiculos_usados']:
        estaciones_con_recarga.update(solucion['recargas'][vid].keys())
    
    # Colores para vehículos
    colores = ['blue', 'green', 'orange', 'purple', 'brown']
    
    # Dibujar rutas
    for idx, vid in enumerate(solucion['vehiculos_usados']):
        ruta = solucion['rutas'][vid]
        color = colores[idx % len(colores)]
        
        for i in range(len(ruta) - 1):
            nodo_i = ruta[i]
            nodo_j = ruta[i+1]
            
            if nodo_i in coords and nodo_j in coords:
                lat_i, lon_i = coords[nodo_i]
                lat_j, lon_j = coords[nodo_j]
                
                # Estilo de línea: sólida para rutas, punteada si pasa por estación
                if nodo_i in data2['STATIONS'] or nodo_j in data2['STATIONS']:
                    ax.plot([lon_i, lon_j], [lat_i, lat_j], 
                           color=color, linewidth=1.5, linestyle='--', alpha=0.7,
                           label=f'{vid}' if i == 0 else '')
                else:
                    ax.plot([lon_i, lon_j], [lat_i, lat_j], 
                           color=color, linewidth=2, alpha=0.8,
                           label=f'{vid}' if i == 0 else '')
    
    # Dibujar nodos
    # Depot
    depot_coords = coords[data2['DEPOT']]
    ax.scatter(depot_coords[1], depot_coords[0], c='red', s=300, marker='s', 
              edgecolors='black', linewidth=2, zorder=5, label='Depósito')
    
    # Clientes
    clientes_visitados = set()
    for vid in solucion['vehiculos_usados']:
        clientes_visitados.update(c for c in solucion['rutas'][vid] if c in data2['CLIENTS'])
    
    for cliente in clientes_visitados:
        if cliente in coords:
            lat, lon = coords[cliente]
            ax.scatter(lon, lat, c='lightblue', s=150, marker='o',
                      edgecolors='darkblue', linewidth=1.5, zorder=4)
            ax.annotate(cliente, (lon, lat), fontsize=8, ha='center', va='bottom')
    
    # Estaciones sin recarga (grises)
    for est in data2['STATIONS']:
        if est not in estaciones_con_recarga and est in coords:
            lat, lon = coords[est]
            ax.scatter(lon, lat, c='lightgray', s=100, marker='^',
                      edgecolors='gray', linewidth=1, zorder=3, alpha=0.5)
    
    # Estaciones CON recarga (verde brillante)
    for est in estaciones_con_recarga:
        if est in coords:
            lat, lon = coords[est]
            ax.scatter(lon, lat, c='limegreen', s=200, marker='^',
                      edgecolors='darkgreen', linewidth=2, zorder=5)
            ax.annotate(f"{est}\n⛽", (lon, lat), fontsize=9, ha='center', 
                       va='bottom', fontweight='bold', color='darkgreen')
    
    ax.set_xlabel('Longitud', fontsize=12)
    ax.set_ylabel('Latitud', fontsize=12)
    ax.set_title(f'Caso 2 - Rutas con Recargas ({len(clientes_visitados)} clientes)', 
                fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(loc='best', fontsize=10)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"✓ Visualización guardada: {output_path}")
    plt.close()


def main():
    print("=" * 80)
    print("GENERACIÓN DE OUTPUTS - CASO 2 (ESCENARIO OPERATIVO)")
    print("=" * 80)
    print()
    
    # Crear directorio de resultados
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1. Determinar escenario factible
    n_clientes = determinar_escenario_factible()
    clientes_subset = CLIENTES_LEJANOS[:n_clientes]
    
    print()
    print("Configuración del escenario:")
    print(f"  - Clientes incluidos: {n_clientes} ({', '.join(clientes_subset)})")
    print(f"  - Estaciones: 12 (todas disponibles)")
    print(f"  - Vehículos: 5 (todos disponibles)")
    print(f"  - Límite de tiempo: {TIME_LIMIT}s")
    print(f"  - Gap objetivo: {GAP_TOLERANCE*100}%")
    print()
    
    # 2. Cargar datos completos
    print("Cargando datos del Caso 2...")
    data_full = cargar_datos_caso2(str(DATA_CASO2), str(DATA_BASE))
    
    # 3. Filtrar al subset
    DEPOT = data_full['DEPOT']
    STATIONS = data_full['STATIONS']
    VEHICLES = data_full['VEHICLES']
    NODES_SUBSET = [DEPOT] + clientes_subset + STATIONS
    
    data_subset = {
        'DEPOT': DEPOT,
        'CLIENTS': clientes_subset,
        'STATIONS': STATIONS,
        'NODES': NODES_SUBSET,
        'VEHICLES': VEHICLES,
        'demanda': {k: v for k, v in data_full['demanda'].items() if k in clientes_subset},
        'load_cap': data_full['load_cap'],
        'fuel_cap': data_full['fuel_cap'],
        'fuel_efficiency': data_full['fuel_efficiency'],
        'fuel_price': data_full['fuel_price'],
        'fuel_price_depot': data_full['fuel_price_depot'],
        'dist': {(i, j): data_full['dist'][(i, j)] for i in NODES_SUBSET for j in NODES_SUBSET if i != j},
        'C_fixed': data_full['C_fixed'],
        'C_km': data_full['C_km'],
        'C_time': data_full['C_time']
    }
    
    print("[OK] Datos filtrados para escenario")
    print()
    
    # 4. Construir modelo
    print("Construyendo modelo completo con combustible...")
    model = build_model_caso2(data_subset)
    print(f"[OK] Modelo construido")
    print()
    
    # 5. Resolver
    print(f"Resolviendo con HiGHS (límite: {TIME_LIMIT}s)...")
    solver = pyo.SolverFactory('appsi_highs')
    solver.options['mip_rel_gap'] = GAP_TOLERANCE
    solver.options['time_limit'] = TIME_LIMIT
    solver.options['output_flag'] = True
    
    results = solver.solve(model, tee=True)
    
    print()
    
    # Verificar resultado
    termination = results.solver.termination_condition
    
    if termination == pyo.TerminationCondition.optimal:
        print("[OK] Solución ÓPTIMA encontrada")
        model.solutions.load_from(results)
    elif termination == pyo.TerminationCondition.maxTimeLimit:
        if results.problem.upper_bound < float('inf'):
            print("[ADVERTENCIA] Límite de tiempo alcanzado, pero hay solución factible")
            model.solutions.load_from(results)
        else:
            print("[ERROR] No se encontró solución factible")
            sys.exit(1)
    else:
        print(f"[ERROR] {termination}")
        sys.exit(1)
    
    costo_total = pyo.value(model.objetivo)
    print(f"\nCosto total: ${costo_total:,.2f} COP")
    
    # 6. Extraer solución
    print("\nExtrayendo solución...")
    solucion = extraer_solucion_completa(model, data_subset)
    print(f"[OK] Vehículos usados: {solucion['num_vehiculos']}")
    print(f"[OK] Distancia total: {solucion['distancia_total']:.2f} km")
    print(f"[OK] Clientes servidos: {solucion['clientes_visitados']}")
    
    # Mostrar estaciones con recarga
    estaciones_usadas = set()
    for vid in solucion['vehiculos_usados']:
        estaciones_usadas.update(solucion['recargas'][vid].keys())
    print(f"[OK] Estaciones con recarga: {len(estaciones_usadas)} ({', '.join(sorted(estaciones_usadas))})")
    
    # 7. Generar outputs
    print("\n" + "=" * 80)
    print("GENERANDO ARCHIVOS DE SALIDA")
    print("=" * 80)
    
    # Necesitamos pandas para la visualización
    import pandas as pd
    
    path_verificacion = RESULTS_DIR / 'verificacion_caso2.csv'
    exportar_verificacion(solucion, data_subset, str(path_verificacion))
    
    path_visualizacion = RESULTS_DIR / 'rutas_caso2.png'
    visualizar_rutas(solucion, data_subset, str(path_visualizacion))
    
    # 8. Resumen final
    print("\n" + "=" * 80)
    print("[COMPLETADO] GENERACIÓN COMPLETADA")
    print("=" * 80)
    
    print(f"\nArchivos generados:")
    print(f"  - {path_verificacion}")
    print(f"  - {path_visualizacion}")
    
    print(f"\nResultados del escenario operativo:")
    print(f"  - Clientes servidos: {solucion['clientes_visitados']} de {n_clientes}")
    print(f"  - Vehículos: {solucion['num_vehiculos']}")
    print(f"  - Distancia: {solucion['distancia_total']:.2f} km")
    print(f"  - Estaciones usadas: {len(estaciones_usadas)}")
    print(f"  - Costo total: ${solucion['costo_total']:,.2f} COP")
    print(f"    - Costo fijo: ${solucion['costo_fijo']:,.2f}")
    print(f"    - Costo distancia: ${solucion['costo_distancia']:,.2f}")
    print(f"    - Costo combustible: ${solucion['costo_combustible']:,.2f}")
    
    print("\n" + "=" * 80)
    print("\n⚠️  NOTA IMPORTANTE:")
    print("Este escenario usa un SUBCONJUNTO de los 14 clientes del Caso 2.")
    print("El problema completo no fue resoluble en tiempo razonable.")
    print("Este escenario demuestra el funcionamiento del modelo con recargas.")
    print("=" * 80)


if __name__ == '__main__':
    main()
