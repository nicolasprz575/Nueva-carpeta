# -*- coding: utf-8 -*-
"""
Script de Ejecución - Caso 3: VRP con Combustible + Peajes + Restricciones Viales
Proyecto C: Optimización de Rutas de Distribución

Este script ejecuta el flujo completo del Caso 3:
1. Carga datos (depots, clientes, estaciones, vehículos, parámetros, peajes, restricciones)
2. Construye modelo de optimización Pyomo
3. Resuelve con solver MIP (HiGHS)
4. Extrae solución y genera outputs:
   - verificacion_caso3.csv (información detallada por vehículo)
   - rutas_caso3.png (visualización de rutas con peajes)

Autor: Sistema de Optimización
Fecha: Noviembre 2025
"""

import sys
import os

# Configurar encoding UTF-8 para salida de consola
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from pathlib import Path
import csv
import time
import pyomo.environ as pyo
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from typing import Dict, List, Tuple

# Agregar directorio src al path para imports
sys.path.insert(0, str(Path(__file__).parent))

# Importar módulos del proyecto
from datos_caso3 import cargar_datos_caso3
from modelo_caso3 import build_model_caso3, extraer_solucion_caso3, validar_solucion


# ============================================================================
# CONFIGURACIÓN GLOBAL
# ============================================================================

# Parámetros del solver
SOLVER_NAME = "highs"  # Solver MIP (también puede ser "cbc", "gurobi", "cplex")
TIME_LIMIT = 1800  # Límite de tiempo en segundos (30 minutos)
GAP_TOLERANCE = 0.10  # Gap de optimalidad relativo (10%)
THREADS = 4  # Número de threads paralelos

# Rutas de datos y outputs
DATA_PATH = Path("../project_c/Proyecto_C_Caso3")
COORDS_PATH = Path("../Proyecto_Caso_Base")  # Coordenadas del Caso Base
RESULTS_PATH = Path("results/caso3")

# Configuración de subset para pruebas rápidas (None para todos los clientes)
# Descomenta la siguiente línea para probar con un subset pequeño:
SUBSET_CLIENTS = ['C001', 'C002']  # Probar con 2 clientes primero
# SUBSET_CLIENTS = None  # None = usar todos los clientes


# ============================================================================
# FUNCIÓN: EXPORTAR CSV DE VERIFICACIÓN
# ============================================================================

def exportar_verificacion_caso3(sol3: Dict, data3: Dict, path_csv: Path) -> None:
    """
    Exporta la solución del Caso 3 a un archivo CSV de verificación.
    
    El archivo generado contiene una fila por cada vehículo usado, con:
    - Identificación del vehículo y depósito
    - Estado inicial (carga y combustible)
    - Ruta completa (secuencia de nodos visitados)
    - Clientes servidos y demandas satisfechas
    - Estaciones visitadas y recargas realizadas
    - Número de peajes cruzados y costo total de peajes
    - Distancia, tiempo y costos totales
    
    Parámetros:
        sol3 (dict): Solución extraída por extraer_solucion_caso3()
        data3 (dict): Datos originales del problema
        path_csv (Path): Ruta del archivo CSV a generar
    """
    
    print(f"\n{'='*80}")
    print("GENERANDO ARCHIVO DE VERIFICACIÓN CSV")
    print(f"{'='*80}")
    
    # Crear directorio si no existe
    path_csv.parent.mkdir(parents=True, exist_ok=True)
    
    # Abrir archivo CSV
    with open(path_csv, 'w', newline='', encoding='utf-8') as csvfile:
        # Definir columnas del CSV
        fieldnames = [
            'VehicleId',           # ID del vehículo (ej. V001)
            'DepotId',             # ID del depósito de origen (ej. CD01)
            'InitialLoad',         # Carga inicial al salir del depósito [kg]
            'InitialFuel',         # Combustible inicial al salir del depósito [gal]
            'RouteSequence',       # Secuencia de nodos: CD01 → E003 → C015 → CD01
            'ClientsServed',       # Lista de clientes servidos (ej. "C014, C005")
            'DemandsSatisfied',    # Demandas individuales servidas (ej. "10.0kg, 15.0kg")
            'StationsVisited',     # Lista de estaciones visitadas (ej. "E003, E005")
            'RefuelAmounts',       # Cantidades recargadas (ej. "E003: 25.3gal, E005: 18.7gal")
            'TollsCount',          # Número de arcos con peaje cruzados
            'TollsCost',           # Costo total de peajes [COP]
            'TotalDistance',       # Distancia total recorrida [km]
            'TotalTime',           # Tiempo total de viaje [horas]
            'FuelCost',            # Costo total de combustible [COP]
            'TotalCost'            # Costo total del vehículo [COP]
        ]
        
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        # Escribir una fila por cada vehículo usado
        for v in sol3['vehiculos_usados']:
            ruta = sol3['rutas'][v]
            clientes = sol3['clientes_servidos'][v]
            estaciones = sol3['estaciones_visitadas'][v]
            recargas = sol3['recargas'][v]
            peajes = sol3['peajes_usados'][v]
            
            # Formatear secuencia de ruta
            route_sequence = ' → '.join(ruta)
            
            # Formatear clientes servidos
            clients_str = ', '.join(clientes) if clientes else 'Ninguno'
            
            # Formatear demandas satisfechas
            demandas_list = [f"{data3['demanda'][c]:.1f}kg" for c in clientes]
            demands_str = ', '.join(demandas_list) if demandas_list else 'Ninguna'
            
            # Formatear estaciones visitadas
            stations_str = ', '.join(estaciones) if estaciones else 'Ninguna'
            
            # Formatear recargas
            if recargas:
                refuel_parts = [f"{est}: {gal:.2f}gal" for est, gal in recargas.items()]
                refuel_str = ', '.join(refuel_parts)
            else:
                refuel_str = 'Ninguna'
            
            # Carga y combustible inicial (valores al salir del depósito)
            # Asumimos carga inicial = 0 y combustible inicial = capacidad
            initial_load = 0.0
            initial_fuel = data3['fuel_cap'][v]
            
            # Escribir fila
            writer.writerow({
                'VehicleId': v,
                'DepotId': data3['DEPOT'],
                'InitialLoad': f"{initial_load:.1f}",
                'InitialFuel': f"{initial_fuel:.2f}",
                'RouteSequence': route_sequence,
                'ClientsServed': clients_str,
                'DemandsSatisfied': demands_str,
                'StationsVisited': stations_str,
                'RefuelAmounts': refuel_str,
                'TollsCount': len(peajes),
                'TollsCost': f"{sol3['costo_peajes'][v]:.2f}",
                'TotalDistance': f"{sol3['distancia_total'][v]:.2f}",
                'TotalTime': f"{sol3['tiempo_total'][v]:.2f}",
                'FuelCost': f"{sol3['costo_combustible'][v]:.2f}",
                'TotalCost': f"{sol3['costo_total_vehiculo'][v]:.2f}"
            })
    
    print(f"\n✓ Archivo CSV generado: {path_csv}")
    print(f"  Vehículos registrados: {len(sol3['vehiculos_usados'])}")
    print(f"  Columnas: {len(fieldnames)}")


# ============================================================================
# FUNCIÓN: GENERAR VISUALIZACIÓN DE RUTAS
# ============================================================================

def generar_mapa_rutas_caso3(sol3: Dict, data3: Dict, path_png: Path) -> None:
    """
    Genera un mapa visual de las rutas del Caso 3.
    
    Características del mapa:
    - Muestra depot, clientes y estaciones con símbolos diferenciados
    - Dibuja rutas de cada vehículo con colores diferentes
    - Resalta arcos con peaje usando línea discontinua roja más gruesa
    - Destaca estaciones donde se recargó combustible
    - Incluye leyenda explicativa
    
    Parámetros:
        sol3 (dict): Solución extraída
        data3 (dict): Datos del problema (incluye coordenadas)
        path_png (Path): Ruta donde guardar la imagen
    """
    
    print(f"\n{'='*80}")
    print("GENERANDO MAPA DE RUTAS")
    print(f"{'='*80}")
    
    # Crear directorio si no existe
    path_png.parent.mkdir(parents=True, exist_ok=True)
    
    # Configurar figura
    fig, ax = plt.subplots(figsize=(14, 10))
    
    coords = data3['coords']
    DEPOT = data3['DEPOT']
    CLIENTS = data3['CLIENTS']
    STATIONS = data3['STATIONS']
    TOLL_ARCS = data3['TOLL_ARCS']
    
    # Colores para vehículos (ciclo de colores)
    vehicle_colors = ['blue', 'green', 'orange', 'purple', 'brown', 'pink', 'gray', 'olive']
    
    # ========================================================================
    # 1. DIBUJAR RUTAS DE VEHÍCULOS
    # ========================================================================
    
    for idx, v in enumerate(sol3['vehiculos_usados']):
        ruta = sol3['rutas'][v]
        color = vehicle_colors[idx % len(vehicle_colors)]
        
        # Dibujar arcos de la ruta
        for i, j in zip(ruta[:-1], ruta[1:]):
            x_vals = [coords[i][1], coords[j][1]]  # Longitudes
            y_vals = [coords[i][0], coords[j][0]]  # Latitudes
            
            # Verificar si es un arco con peaje
            if (i, j) in TOLL_ARCS:
                # Arco con peaje: línea roja discontinua más gruesa
                ax.plot(x_vals, y_vals, 'r--', linewidth=3, alpha=0.8, zorder=2)
            else:
                # Arco normal: línea del color del vehículo
                ax.plot(x_vals, y_vals, color=color, linewidth=2, alpha=0.6, zorder=1)
    
    # ========================================================================
    # 2. DIBUJAR NODOS (DEPOT, CLIENTES, ESTACIONES)
    # ========================================================================
    
    # Depot (triángulo rojo grande)
    depot_coord = coords[DEPOT]
    ax.plot(depot_coord[1], depot_coord[0], '^r', markersize=20, 
            markeredgewidth=2, markeredgecolor='black', zorder=5, label='Depósito')
    ax.text(depot_coord[1], depot_coord[0] + 0.02, DEPOT, 
            fontsize=10, fontweight='bold', ha='center', va='bottom')
    
    # Clientes (círculos azules)
    for c in CLIENTS:
        coord = coords[c]
        ax.plot(coord[1], coord[0], 'o', color='blue', markersize=8, 
                markeredgewidth=1, markeredgecolor='black', zorder=4)
        ax.text(coord[1], coord[0] + 0.015, c, fontsize=8, ha='center', va='bottom')
    
    # Estaciones (cuadrados verdes)
    # Distinguir entre estaciones usadas y no usadas
    estaciones_usadas = set()
    for v in sol3['vehiculos_usados']:
        estaciones_usadas.update(sol3['estaciones_visitadas'][v])
    
    for s in STATIONS:
        coord = coords[s]
        if s in estaciones_usadas:
            # Estación usada: cuadrado verde grande con borde negro
            ax.plot(coord[1], coord[0], 's', color='limegreen', markersize=12,
                    markeredgewidth=2, markeredgecolor='black', zorder=4)
            ax.text(coord[1], coord[0] - 0.015, s, fontsize=8, 
                    ha='center', va='top', fontweight='bold')
        else:
            # Estación no usada: cuadrado verde pequeño transparente
            ax.plot(coord[1], coord[0], 's', color='lightgreen', markersize=8,
                    alpha=0.5, markeredgewidth=1, markeredgecolor='gray', zorder=3)
    
    # ========================================================================
    # 3. CONFIGURAR LEYENDA Y FORMATO
    # ========================================================================
    
    # Crear elementos de leyenda
    legend_elements = [
        mpatches.Patch(color='none', label=f'CASO 3: {len(sol3["vehiculos_usados"])} vehículos, {sol3["num_clientes"]} clientes'),
        plt.Line2D([0], [0], marker='^', color='w', markerfacecolor='r', 
                   markersize=12, markeredgecolor='black', markeredgewidth=1.5,
                   label='Depósito'),
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='blue',
                   markersize=8, markeredgecolor='black', markeredgewidth=1,
                   label='Cliente'),
        plt.Line2D([0], [0], marker='s', color='w', markerfacecolor='limegreen',
                   markersize=10, markeredgecolor='black', markeredgewidth=1.5,
                   label='Estación (usada)'),
        plt.Line2D([0], [0], marker='s', color='w', markerfacecolor='lightgreen',
                   markersize=8, markeredgecolor='gray', alpha=0.5,
                   label='Estación (no usada)'),
        plt.Line2D([0], [0], color='blue', linewidth=2, alpha=0.6,
                   label='Ruta (sin peaje)'),
        plt.Line2D([0], [0], color='red', linewidth=3, linestyle='--', alpha=0.8,
                   label=f'Ruta con peaje ({sol3["num_peajes"]} arcos)')
    ]
    
    # Agregar vehículos a la leyenda
    for idx, v in enumerate(sol3['vehiculos_usados']):
        color = vehicle_colors[idx % len(vehicle_colors)]
        num_clientes = len(sol3['clientes_servidos'][v])
        dist = sol3['distancia_total'][v]
        legend_elements.append(
            plt.Line2D([0], [0], color=color, linewidth=2,
                       label=f'{v}: {num_clientes} clientes, {dist:.0f} km')
        )
    
    ax.legend(handles=legend_elements, loc='upper left', fontsize=9, 
              framealpha=0.95, edgecolor='black')
    
    # Configurar ejes y título
    ax.set_xlabel('Longitud', fontsize=12, fontweight='bold')
    ax.set_ylabel('Latitud', fontsize=12, fontweight='bold')
    ax.set_title(f'CASO 3: Rutas de Distribución con Peajes y Restricciones\n'
                 f'Costo Total: ${sol3["costo_total"]:,.0f} COP | '
                 f'Peajes: {sol3["num_peajes"]} arcos con peaje',
                 fontsize=14, fontweight='bold', pad=20)
    
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.set_aspect('equal', adjustable='box')
    
    # Ajustar márgenes
    plt.tight_layout()
    
    # Guardar figura
    plt.savefig(path_png, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"\n✓ Mapa de rutas generado: {path_png}")
    print(f"  Resolución: 300 DPI")
    print(f"  Formato: PNG")


# ============================================================================
# FUNCIÓN PRINCIPAL
# ============================================================================

def main():
    """
    Función principal para ejecutar el Caso 3 completo.
    
    Flujo:
    1. Carga datos del Caso 3 (con peajes y restricciones)
    2. Construye modelo de optimización Pyomo
    3. Resuelve con solver MIP
    4. Extrae y valida solución
    5. Genera outputs (CSV + PNG)
    """
    
    print("\n" + "="*80)
    print("PROYECTO C - CASO 3: VRP CON COMBUSTIBLE + PEAJES + RESTRICCIONES")
    print("="*80)
    print(f"Fecha de ejecución: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Solver: {SOLVER_NAME.upper()}")
    print(f"Límite de tiempo: {TIME_LIMIT} segundos ({TIME_LIMIT/60:.1f} minutos)")
    print(f"Gap de optimalidad: {GAP_TOLERANCE*100:.1f}%")
    
    if SUBSET_CLIENTS:
        print(f"MODO PRUEBA: Usando subset de {len(SUBSET_CLIENTS)} clientes")
    else:
        print("MODO COMPLETO: Usando todos los clientes disponibles")
    
    print("="*80)
    
    try:
        # ====================================================================
        # PASO 1: CARGAR DATOS
        # ====================================================================
        
        print("\n" + "="*80)
        print("PASO 1: CARGANDO DATOS DEL CASO 3")
        print("="*80)
        
        t_start_data = time.time()
        
        # Cargar datos con subset opcional y coordenadas del Caso Base
        data3 = cargar_datos_caso3(
            ruta_data=str(DATA_PATH),
            ruta_coords=str(COORDS_PATH),
            clientes_subset=SUBSET_CLIENTS,
            escenario='base'  # Puede ser 'base', 'high_tolls', etc.
        )
        
        t_end_data = time.time()
        
        print(f"\n✓ Datos cargados exitosamente en {t_end_data - t_start_data:.2f} segundos")
        print(f"  Nodos: {len(data3['NODES'])} (depot + clientes + estaciones)")
        print(f"  Clientes: {len(data3['CLIENTS'])}")
        print(f"  Estaciones: {len(data3['STATIONS'])}")
        print(f"  Vehículos: {len(data3['VEHICLES'])}")
        print(f"  Arcos válidos: {len(data3['ARCS'])}")
        print(f"  Arcos con peaje: {len(data3['TOLL_ARCS'])}")
        print(f"  Arcos prohibidos: {len(data3['FORBIDDEN_ARCS'])}")
        
        # ====================================================================
        # PASO 2: CONSTRUIR MODELO
        # ====================================================================
        
        print("\n" + "="*80)
        print("PASO 2: CONSTRUYENDO MODELO DE OPTIMIZACIÓN")
        print("="*80)
        
        t_start_model = time.time()
        
        model = build_model_caso3(data3)
        
        t_end_model = time.time()
        
        print(f"\n✓ Modelo construido exitosamente en {t_end_model - t_start_model:.2f} segundos")
        
        # ====================================================================
        # PASO 3: RESOLVER MODELO
        # ====================================================================
        
        print("\n" + "="*80)
        print("PASO 3: RESOLVIENDO MODELO CON SOLVER MIP")
        print("="*80)
        
        # Crear solver
        solver = pyo.SolverFactory(SOLVER_NAME)
        
        # Configurar opciones del solver según el tipo
        if SOLVER_NAME == "highs":
            solver.options['time_limit'] = TIME_LIMIT
            solver.options['mip_rel_gap'] = GAP_TOLERANCE
            solver.options['threads'] = THREADS
            solver.options['log_to_console'] = True
        elif SOLVER_NAME == "cbc":
            solver.options['seconds'] = TIME_LIMIT
            solver.options['ratioGap'] = GAP_TOLERANCE
            solver.options['threads'] = THREADS
        elif SOLVER_NAME in ["gurobi", "cplex"]:
            solver.options['TimeLimit'] = TIME_LIMIT
            solver.options['MIPGap'] = GAP_TOLERANCE
            solver.options['Threads'] = THREADS
        
        print(f"Solver configurado: {SOLVER_NAME.upper()}")
        print(f"  Límite de tiempo: {TIME_LIMIT}s")
        print(f"  Gap objetivo: {GAP_TOLERANCE*100:.1f}%")
        print(f"  Threads: {THREADS}")
        print("\nIniciando resolución...")
        print("-" * 80)
        
        t_start_solve = time.time()
        
        # Resolver modelo
        results = solver.solve(model, tee=True, load_solutions=False)
        
        t_end_solve = time.time()
        tiempo_resolucion = t_end_solve - t_start_solve
        
        print("-" * 80)
        print(f"Resolución completada en {tiempo_resolucion:.2f} segundos ({tiempo_resolucion/60:.2f} minutos)")
        
        # ====================================================================
        # PASO 4: ANALIZAR RESULTADOS
        # ====================================================================
        
        print("\n" + "="*80)
        print("PASO 4: ANALIZANDO RESULTADOS")
        print("="*80)
        
        # Verificar estado del solver
        solver_status = results.solver.status
        termination_condition = results.solver.termination_condition
        
        print(f"\nEstado del solver: {solver_status}")
        print(f"Condición de terminación: {termination_condition}")
        
        # Verificar si hay solución factible
        if termination_condition == pyo.TerminationCondition.optimal:
            print("✓ Solución ÓPTIMA encontrada")
            model.solutions.load_from(results)
        elif termination_condition == pyo.TerminationCondition.feasible:
            print("✓ Solución FACTIBLE encontrada (no óptima)")
            model.solutions.load_from(results)
        elif termination_condition == pyo.TerminationCondition.maxTimeLimit:
            print("⚠ Límite de tiempo alcanzado")
            if results.solution.status == pyo.SolutionStatus.feasible:
                print("  Pero hay una solución factible disponible")
                model.solutions.load_from(results)
            else:
                print("  ✗ No hay solución factible disponible")
                print("\nEjecución abortada: No se puede extraer solución sin factibilidad")
                return
        else:
            print(f"✗ No se encontró solución factible")
            print(f"  Condición: {termination_condition}")
            print("\nEjecución abortada")
            return
        
        # Obtener valor de la función objetivo
        costo_total = pyo.value(model.obj)
        print(f"\n{'='*80}")
        print(f"COSTO TOTAL: ${costo_total:,.2f} COP")
        print(f"{'='*80}")
        
        # Calcular gap si disponible
        if hasattr(results.problem, 'lower_bound') and hasattr(results.problem, 'upper_bound'):
            lb = results.problem.lower_bound
            ub = results.problem.upper_bound
            if lb is not None and ub is not None and ub > 0:
                gap = (ub - lb) / ub * 100
                print(f"Gap final: {gap:.2f}%")
                print(f"Lower bound: ${lb:,.2f} COP")
                print(f"Upper bound: ${ub:,.2f} COP")
        
        # ====================================================================
        # PASO 5: EXTRAER SOLUCIÓN
        # ====================================================================
        
        print("\n" + "="*80)
        print("PASO 5: EXTRAYENDO SOLUCIÓN DETALLADA")
        print("="*80)
        
        sol3 = extraer_solucion_caso3(model, data3)
        
        # ====================================================================
        # PASO 6: VALIDAR SOLUCIÓN
        # ====================================================================
        
        print("\n" + "="*80)
        print("PASO 6: VALIDANDO SOLUCIÓN")
        print("="*80)
        
        es_valida = validar_solucion(sol3, data3)
        
        if not es_valida:
            print("\n⚠ ADVERTENCIA: La solución tiene inconsistencias")
            print("  Revisar logs anteriores para detalles")
        
        # ====================================================================
        # PASO 7: GENERAR OUTPUTS
        # ====================================================================
        
        print("\n" + "="*80)
        print("PASO 7: GENERANDO OUTPUTS")
        print("="*80)
        
        # Crear directorio de resultados
        RESULTS_PATH.mkdir(parents=True, exist_ok=True)
        
        # Generar CSV de verificación
        csv_path = RESULTS_PATH / "verificacion_caso3.csv"
        exportar_verificacion_caso3(sol3, data3, csv_path)
        
        # Generar mapa de rutas
        png_path = RESULTS_PATH / "rutas_caso3.png"
        generar_mapa_rutas_caso3(sol3, data3, png_path)
        
        # ====================================================================
        # PASO 8: RESUMEN EJECUTIVO
        # ====================================================================
        
        print("\n" + "="*80)
        print("RESUMEN EJECUTIVO - CASO 3")
        print("="*80)
        
        print(f"\n📊 MÉTRICAS GENERALES:")
        print(f"  • Vehículos usados: {sol3['num_vehiculos']}")
        print(f"  • Clientes atendidos: {sol3['num_clientes']}")
        print(f"  • Distancia total: {sum(sol3['distancia_total'].values()):.2f} km")
        print(f"  • Tiempo total: {sum(sol3['tiempo_total'].values()):.2f} horas")
        
        print(f"\n💰 ANÁLISIS DE COSTOS:")
        costo_fijo = sol3['num_vehiculos'] * data3['cost_fixed']
        costo_distancia = sum(sol3['distancia_total'][v] * data3['cost_km'] 
                             for v in sol3['vehiculos_usados'])
        costo_combustible = sum(sol3['costo_combustible'].values())
        costo_peajes = sum(sol3['costo_peajes'].values())
        
        print(f"  • Costo fijo: ${costo_fijo:,.2f} COP ({costo_fijo/costo_total*100:.1f}%)")
        print(f"  • Costo distancia: ${costo_distancia:,.2f} COP ({costo_distancia/costo_total*100:.1f}%)")
        print(f"  • Costo combustible: ${costo_combustible:,.2f} COP ({costo_combustible/costo_total*100:.1f}%)")
        print(f"  • Costo peajes: ${costo_peajes:,.2f} COP ({costo_peajes/costo_total*100:.1f}%)")
        print(f"  • COSTO TOTAL: ${costo_total:,.2f} COP")
        
        print(f"\n🛣️  ANÁLISIS DE PEAJES:")
        print(f"  • Arcos con peaje cruzados: {sol3['num_peajes']}")
        print(f"  • Costo promedio por peaje: ${costo_peajes/sol3['num_peajes']:,.2f} COP" if sol3['num_peajes'] > 0 else "  • Sin peajes")
        print(f"  • Proporción de costo de peajes: {costo_peajes/costo_total*100:.2f}%")
        
        print(f"\n⛽ ANÁLISIS DE COMBUSTIBLE:")
        num_recargas = sum(len(sol3['recargas'][v]) for v in sol3['vehiculos_usados'])
        cantidad_total = sum(sum(r.values()) for r in sol3['recargas'].values())
        print(f"  • Número de recargas: {num_recargas}")
        print(f"  • Combustible total recargado: {cantidad_total:.2f} galones")
        if num_recargas > 0:
            print(f"  • Recarga promedio: {cantidad_total/num_recargas:.2f} galones")
        
        print(f"\n📁 ARCHIVOS GENERADOS:")
        print(f"  • {csv_path}")
        print(f"  • {png_path}")
        
        print(f"\n⏱️  TIEMPOS DE EJECUCIÓN:")
        print(f"  • Carga de datos: {t_end_data - t_start_data:.2f}s")
        print(f"  • Construcción del modelo: {t_end_model - t_start_model:.2f}s")
        print(f"  • Resolución: {tiempo_resolucion:.2f}s ({tiempo_resolucion/60:.2f} min)")
        print(f"  • TOTAL: {time.time() - t_start_data:.2f}s ({(time.time() - t_start_data)/60:.2f} min)")
        
        print("\n" + "="*80)
        print("✓ CASO 3 COMPLETADO EXITOSAMENTE")
        print("="*80)
        
    except FileNotFoundError as e:
        print(f"\n✗ ERROR: Archivo no encontrado")
        print(f"  {e}")
        print(f"\nVerificar que la carpeta de datos existe: {DATA_PATH}")
        return
    
    except ImportError as e:
        print(f"\n✗ ERROR: Módulo no encontrado")
        print(f"  {e}")
        print(f"\nVerificar que los módulos datos_caso3.py y modelo_caso3.py existen en src/")
        return
    
    except Exception as e:
        print(f"\n✗ ERROR INESPERADO:")
        print(f"  {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return


# ============================================================================
# PUNTO DE ENTRADA
# ============================================================================

if __name__ == "__main__":
    main()
