"""
run_caso1.py
------------
Script principal para ejecutar el Caso 1 (Proyecto C - CVRP básico).

Este script orquesta todo el flujo de trabajo:
  1. Carga de datos desde CSV
  2. Construcción del modelo de optimización en Pyomo
  3. Resolución con solver MIP (CBC por defecto)
  4. Extracción de la solución (rutas, métricas, costos)
  5. Generación de archivo de verificación (CSV)
  6. Visualización de rutas (PNG)

Uso:
    python src/run_caso1.py

Requisitos:
    - Python 3.8+
    - Pyomo
    - pandas
    - numpy
    - matplotlib
    - Solver MIP instalado (CBC, HiGHS, Gurobi, o CPLEX)

Salidas generadas:
    - results/caso1/verificacion_caso1.csv: Archivo de verificación con rutas y métricas
    - results/caso1/rutas_caso1.png: Visualización de las rutas en mapa
    - results/caso1/resumen.txt: Resumen textual de la solución

Autor: Asistente IA (GitHub Copilot)
Fecha: Noviembre 2025
"""

import sys
from pathlib import Path
import csv
import json
from typing import Dict, Any

# Añadir directorio raíz al path para imports
proyecto_root = Path(__file__).parent.parent
sys.path.insert(0, str(proyecto_root))

# Imports de módulos del proyecto
from src.datos_caso1 import cargar_datos_caso1
from src.modelo_caso1 import build_model, extraer_solucion

# Imports para optimización y visualización
import pyomo.environ as pyo
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from datetime import datetime


# ===========================
# CONFIGURACIÓN GLOBAL
# ===========================

# Directorio de datos (en el nivel superior del workspace, no dentro de proyecto_c)
# La estructura es: Nueva carpeta/Proyecto_Caso_Base/ y Nueva carpeta/proyecto_c/
RUTA_DATA = proyecto_root.parent / "Proyecto_Caso_Base"

# Directorio de resultados
RUTA_RESULTS = proyecto_root / "results" / "caso1"

# Configuración del solver
# Opciones: "cbc", "highs", "gurobi", "cplex", "glpk"
SOLVER_NAME = "appsi_highs"  # HiGHS es moderno y eficiente
SOLVER_TIME_LIMIT = 120  # Límite de tiempo en segundos (2 minutos - ajustable)
SOLVER_GAP = 0.05  # Gap de optimalidad aceptable (5% - ajustable entre 0.05-0.10)

# Parámetros para cálculo de tiempos y combustible
VELOCIDAD_PROMEDIO = 60.0  # km/h (velocidad promedio en carretera para tractomulas)


# ===========================
# FUNCIÓN: EXPORTAR VERIFICACIÓN
# ===========================

def exportar_verificacion_caso1(solucion: Dict[str, Any], data: Dict, path_csv: Path) -> None:
    """
    Genera el archivo CSV de verificación con las rutas y métricas de cada vehículo.
    
    Formato del CSV (según requerimientos de la profesora):
      - VehicleId: ID estandarizado del vehículo (V001, V002, ...)
      - DepotId: ID estandarizado del depósito (CD01)
      - InitialLoad: Carga inicial al salir del depósito (kg)
      - RouteSequence: Secuencia completa de la ruta (CD01-C005-C012-CD01)
      - ClientsServed: Número de clientes atendidos en la ruta
      - DemandsSatisfied: Demandas satisfechas en orden de visita, separadas por guiones
      - TotalDistance: Distancia total recorrida (km)
      - TotalTime: Tiempo total estimado (minutos)
      - FuelCost: Costo de combustible estimado (COP)
    
    Args:
        solucion: Diccionario con la solución del modelo (retornado por extraer_solucion)
        data: Diccionario con los datos de entrada (para obtener parámetros)
        path_csv: Ruta donde se guardará el archivo CSV
    """
    
    print(f"\n{'='*60}")
    print("GENERANDO ARCHIVO DE VERIFICACIÓN")
    print(f"{'='*60}")
    
    # Crear directorio si no existe
    path_csv.parent.mkdir(parents=True, exist_ok=True)
    
    # Obtener parámetros necesarios
    depot = data['DEPOT']
    fuel_efficiency = data['fuel_efficiency']  # km/galón
    fuel_price = data['cost_fuel']  # COP/galón
    
    # Abrir archivo CSV para escritura
    with open(path_csv, 'w', newline='', encoding='utf-8') as csvfile:
        # Definir columnas según formato requerido
        fieldnames = [
            'VehicleId',
            'DepotId',
            'InitialLoad',
            'RouteSequence',
            'ClientsServed',
            'DemandsSatisfied',
            'TotalDistance',
            'TotalTime',
            'FuelCost'
        ]
        
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        # Escribir una fila por cada vehículo usado
        for ruta_info in solucion['rutas']:
            # Calcular tiempo total (distancia / velocidad, convertido a minutos)
            tiempo_total = (ruta_info['distancia_total'] / VELOCIDAD_PROMEDIO) * 60.0
            
            # Calcular consumo de combustible y costo
            # Consumo (galones) = distancia / rendimiento
            consumo_galones = ruta_info['distancia_total'] / fuel_efficiency
            costo_combustible = consumo_galones * fuel_price
            
            # Formatear lista de demandas como string separado por guiones
            demandas_str = "-".join(str(int(d)) for d in ruta_info['demandas_por_cliente'])
            
            # Crear fila del CSV
            fila = {
                'VehicleId': ruta_info['vehiculo_id'],
                'DepotId': depot,
                'InitialLoad': int(ruta_info['demanda_total']),
                'RouteSequence': ruta_info['ruta_secuencia'],
                'ClientsServed': ruta_info['num_clientes'],
                'DemandsSatisfied': demandas_str,
                'TotalDistance': round(ruta_info['distancia_total'], 2),
                'TotalTime': round(tiempo_total, 1),
                'FuelCost': round(costo_combustible, 0)
            }
            
            writer.writerow(fila)
            
            print(f"✓ {ruta_info['vehiculo_id']}: {ruta_info['num_clientes']} clientes, "
                  f"{ruta_info['distancia_total']:.1f} km, {tiempo_total:.1f} min")
    
    print(f"\n✓ Archivo guardado: {path_csv}")
    print(f"{'='*60}\n")


# ===========================
# FUNCIÓN: VISUALIZAR RUTAS
# ===========================

def visualizar_rutas(solucion: Dict[str, Any], data: Dict, path_png: Path) -> None:
    """
    Genera una visualización gráfica de las rutas en un mapa de coordenadas.
    
    Args:
        solucion: Diccionario con la solución del modelo
        data: Diccionario con los datos de entrada (coordenadas)
        path_png: Ruta donde se guardará la imagen PNG
    """
    
    print(f"\n{'='*60}")
    print("GENERANDO VISUALIZACIÓN DE RUTAS")
    print(f"{'='*60}")
    
    # Crear directorio si no existe
    path_png.parent.mkdir(parents=True, exist_ok=True)
    
    # Obtener coordenadas
    coords = data['coords']
    depot = data['DEPOT']
    
    # Crear figura y ejes
    fig, ax = plt.subplots(figsize=(14, 10))
    
    # Colores para las rutas (ciclo de colores distintos)
    colores = plt.cm.tab10(range(10))  # Hasta 10 colores distintos
    
    # Dibujar cada ruta
    for idx, ruta_info in enumerate(solucion['rutas']):
        ruta = ruta_info['ruta_indices']
        color = colores[idx % len(colores)]
        
        # Extraer coordenadas de la ruta
        lats = [coords[nodo][0] for nodo in ruta]
        lons = [coords[nodo][1] for nodo in ruta]
        
        # Dibujar línea de la ruta
        ax.plot(lons, lats, 'o-', 
                color=color, 
                linewidth=2, 
                markersize=6,
                label=f"{ruta_info['vehiculo_id']} ({ruta_info['num_clientes']} clientes)",
                alpha=0.7)
        
        # Añadir flechas direccionales en algunos segmentos
        for i in range(0, len(ruta) - 1, max(1, len(ruta) // 3)):
            dx = lons[i+1] - lons[i]
            dy = lats[i+1] - lats[i]
            ax.annotate('', 
                       xy=(lons[i+1], lats[i+1]), 
                       xytext=(lons[i], lats[i]),
                       arrowprops=dict(arrowstyle='->', color=color, lw=1.5, alpha=0.6))
    
    # Dibujar depósito (marcador especial)
    depot_lat, depot_lon = coords[depot]
    ax.plot(depot_lon, depot_lat, 
           marker='s',  # Cuadrado para el depósito
           markersize=15, 
           color='red', 
           markeredgecolor='darkred',
           markeredgewidth=2,
           label='Depósito (CD01)',
           zorder=10)
    
    # Dibujar clientes
    for cliente in data['CLIENTS']:
        lat, lon = coords[cliente]
        ax.plot(lon, lat, 
               marker='o', 
               markersize=5, 
               color='lightgray',
               markeredgecolor='black',
               markeredgewidth=0.5,
               zorder=5)
    
    # Configuración de ejes y etiquetas
    ax.set_xlabel('Longitud', fontsize=12, fontweight='bold')
    ax.set_ylabel('Latitud', fontsize=12, fontweight='bold')
    ax.set_title('Rutas Optimizadas - Caso 1 (Proyecto C)\n'
                f'Costo Total: {solucion["costo_total"]:,.0f} COP | '
                f'Distancia Total: {solucion["distancia_total_sistema"]:.1f} km | '
                f'Vehículos: {solucion["num_vehiculos_usados"]}',
                fontsize=14, fontweight='bold', pad=20)
    
    # Grid y leyenda
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.legend(loc='best', fontsize=9, framealpha=0.9)
    
    # Ajustar márgenes
    plt.tight_layout()
    
    # Guardar figura
    plt.savefig(path_png, dpi=300, bbox_inches='tight')
    print(f"✓ Gráfico guardado: {path_png}")
    print(f"{'='*60}\n")
    
    plt.close()


# ===========================
# FUNCIÓN: GUARDAR RESUMEN TEXTUAL
# ===========================

def guardar_resumen(solucion: Dict[str, Any], data: Dict, path_txt: Path) -> None:
    """
    Guarda un resumen textual de la solución.
    
    Args:
        solucion: Diccionario con la solución del modelo
        data: Diccionario con los datos de entrada
        path_txt: Ruta donde se guardará el archivo de texto
    """
    
    # Crear directorio si no existe
    path_txt.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path_txt, 'w', encoding='utf-8') as f:
        f.write("=" * 70 + "\n")
        f.write("RESUMEN DE SOLUCIÓN - CASO 1 (PROYECTO C)\n")
        f.write("=" * 70 + "\n\n")
        
        f.write(f"Fecha de ejecución: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Solver utilizado: {SOLVER_NAME.upper()}\n\n")
        
        f.write("-" * 70 + "\n")
        f.write("MÉTRICAS GLOBALES\n")
        f.write("-" * 70 + "\n")
        f.write(f"Costo total: {solucion['costo_total']:,.2f} COP\n")
        f.write(f"  - Costo fijo: {solucion['costo_fijo_total']:,.2f} COP\n")
        f.write(f"  - Costo distancia: {solucion['costo_distancia_total']:,.2f} COP\n")
        f.write(f"Vehículos usados: {solucion['num_vehiculos_usados']} de {data['num_vehicles']}\n")
        f.write(f"Distancia total: {solucion['distancia_total_sistema']:.2f} km\n")
        f.write(f"Clientes atendidos: {solucion['clientes_atendidos']} de {solucion['clientes_totales']}\n\n")
        
        f.write("-" * 70 + "\n")
        f.write("DETALLE DE RUTAS\n")
        f.write("-" * 70 + "\n\n")
        
        for ruta_info in solucion['rutas']:
            f.write(f"Vehículo: {ruta_info['vehiculo_id']}\n")
            f.write(f"  Ruta: {ruta_info['ruta_secuencia']}\n")
            f.write(f"  Clientes atendidos: {ruta_info['num_clientes']}\n")
            f.write(f"  Distancia: {ruta_info['distancia_total']:.2f} km\n")
            f.write(f"  Demanda: {ruta_info['demanda_total']:.1f} kg\n")
            f.write(f"  Utilización capacidad: {ruta_info['utilizacion_capacidad']:.1f}%\n")
            f.write(f"  Utilización autonomía: {ruta_info['utilizacion_autonomia']:.1f}%\n")
            f.write(f"  Costo: {ruta_info['costo_total_ruta']:,.2f} COP\n")
            f.write("\n")
        
        f.write("=" * 70 + "\n")
    
    print(f"✓ Resumen guardado: {path_txt}\n")


# ===========================
# FUNCIÓN PRINCIPAL
# ===========================

def main():
    """
    Función principal que ejecuta todo el flujo del Caso 1.
    """
    
    print("\n" + "=" * 70)
    print("CASO 1 - PROYECTO C: CVRP BÁSICO")
    print("=" * 70 + "\n")
    
    try:
        # -----------------------------------------------------------------
        # PASO 1: CARGAR DATOS
        # -----------------------------------------------------------------
        print("PASO 1: Cargando datos del caso base...\n")
        
        # RUTA_DATA ya es un Path absoluto
        if not RUTA_DATA.exists():
            raise FileNotFoundError(
                f"No se encontró el directorio de datos: {RUTA_DATA}\n"
                f"Asegúrate de que los archivos CSV estén en la ubicación correcta."
            )
        
        data = cargar_datos_caso1(str(RUTA_DATA))
        
        # -----------------------------------------------------------------
        # PASO 2: CONSTRUIR MODELO
        # -----------------------------------------------------------------
        print("\nPASO 2: Construyendo modelo de optimización...\n")
        
        model = build_model(data)
        
        # -----------------------------------------------------------------
        # PASO 3: CONFIGURAR Y EJECUTAR SOLVER
        # -----------------------------------------------------------------
        print(f"\nPASO 3: Resolviendo modelo con solver {SOLVER_NAME.upper()}...\n")
        
        # Intentar crear el solver
        try:
            solver = pyo.SolverFactory(SOLVER_NAME)
            
            if not solver.available():
                raise RuntimeError(
                    f"El solver '{SOLVER_NAME}' no está disponible.\n"
                    f"Opciones:\n"
                    f"  1. Instalar CBC: conda install -c conda-forge coincbc\n"
                    f"  2. Instalar HiGHS: pip install highspy\n"
                    f"  3. Usar GLPK: cambiar SOLVER_NAME a 'glpk'\n"
                    f"  4. Si tienes licencia: 'gurobi' o 'cplex'"
                )
        except Exception as e:
            raise RuntimeError(f"Error al crear solver '{SOLVER_NAME}': {e}")
        
        # Configurar opciones del solver
        solver_options = {}
        
        # HiGHS usa opciones específicas
        if SOLVER_NAME == 'appsi_highs':
            # time_limit en segundos
            solver_options['time_limit'] = SOLVER_TIME_LIMIT
            # mip_rel_gap es el gap relativo (5% = 0.05)
            solver_options['mip_rel_gap'] = SOLVER_GAP
            # Configuraciones adicionales para mejorar rendimiento
            solver_options['presolve'] = 'on'
            solver_options['parallel'] = 'on'  # Usar procesamiento paralelo
        elif SOLVER_NAME in ['cbc', 'gurobi', 'cplex']:
            solver_options['seconds'] = SOLVER_TIME_LIMIT  # Límite de tiempo
            solver_options['ratio'] = SOLVER_GAP  # Gap de optimalidad
        
        if SOLVER_NAME == 'gurobi':
            solver_options['MIPGap'] = SOLVER_GAP
            solver_options['TimeLimit'] = SOLVER_TIME_LIMIT
        
        if SOLVER_NAME == 'cplex':
            solver_options['timelimit'] = SOLVER_TIME_LIMIT
            solver_options['mip_tolerances_mipgap'] = SOLVER_GAP
        
        # Resolver el modelo
        print(f"Configuración del solver:")
        print(f"  - Límite de tiempo: {SOLVER_TIME_LIMIT} segundos")
        print(f"  - Gap de optimalidad aceptable: {SOLVER_GAP * 100}%")
        print(f"\nResolviendo... (se detendrá al alcanzar el tiempo límite o gap objetivo)\n")
        
        resultado = solver.solve(model, tee=True, options=solver_options)
        
        # -----------------------------------------------------------------
        # PASO 4: VERIFICAR ESTADO DE TERMINACIÓN
        # -----------------------------------------------------------------
        print(f"\n{'='*70}")
        print("RESULTADO DE LA OPTIMIZACIÓN")
        print(f"{'='*70}")
        
        termination_condition = resultado.solver.termination_condition
        solver_status = resultado.solver.status
        
        print(f"Estado del solver: {solver_status}")
        print(f"Condición de terminación: {termination_condition}")
        
        # Verificar si se encontró una solución factible
        if termination_condition == pyo.TerminationCondition.optimal:
            print("✓ Solución óptima encontrada")
        elif termination_condition == pyo.TerminationCondition.feasible:
            print("✓ Solución factible encontrada (puede no ser óptima)")
            print(f"  El solver alcanzó el límite de tiempo o gap aceptable")
        elif termination_condition == pyo.TerminationCondition.maxTimeLimit:
            print("✓ Solución factible encontrada (límite de tiempo alcanzado)")
            print(f"  Se usará la mejor solución encontrada hasta el momento")
        elif termination_condition == pyo.TerminationCondition.other:
            # HiGHS puede retornar 'other' cuando alcanza el gap objetivo
            print("✓ Solución factible encontrada (criterio de parada alcanzado)")
            print(f"  El gap objetivo o límite de tiempo fue alcanzado")
        else:
            raise RuntimeError(
                f"El solver no encontró una solución factible.\n"
                f"Condición de terminación: {termination_condition}\n"
                f"Posibles causas:\n"
                f"  - El problema es infactible (capacidad insuficiente, autonomía limitada)\n"
                f"  - El tiempo límite fue muy corto ({SOLVER_TIME_LIMIT}s)\n"
                f"  - Error en la formulación del modelo\n"
                f"Sugerencias:\n"
                f"  - Aumentar SOLVER_TIME_LIMIT en run_caso1.py\n"
                f"  - Aumentar SOLVER_GAP (ej. 0.10 para 10%)\n"
                f"  - Revisar capacidades y autonomías de vehículos"
            )
        
        # Mostrar valor de la función objetivo
        valor_objetivo = pyo.value(model.objetivo)
        print(f"\nValor de la función objetivo: {valor_objetivo:,.2f} COP")
        print(f"{'='*70}\n")
        
        # -----------------------------------------------------------------
        # PASO 5: EXTRAER SOLUCIÓN
        # -----------------------------------------------------------------
        print("PASO 4: Extrayendo solución del modelo...")
        
        solucion = extraer_solucion(model, data)
        
        # -----------------------------------------------------------------
        # PASO 6: CREAR DIRECTORIO DE RESULTADOS
        # -----------------------------------------------------------------
        print("\nPASO 5: Generando archivos de salida...\n")
        
        RUTA_RESULTS.mkdir(parents=True, exist_ok=True)
        
        # -----------------------------------------------------------------
        # PASO 7: EXPORTAR ARCHIVO DE VERIFICACIÓN
        # -----------------------------------------------------------------
        path_verificacion = RUTA_RESULTS / "verificacion_caso1.csv"
        exportar_verificacion_caso1(solucion, data, path_verificacion)
        
        # -----------------------------------------------------------------
        # PASO 8: GENERAR VISUALIZACIÓN
        # -----------------------------------------------------------------
        path_grafico = RUTA_RESULTS / "rutas_caso1.png"
        visualizar_rutas(solucion, data, path_grafico)
        
        # -----------------------------------------------------------------
        # PASO 9: GUARDAR RESUMEN TEXTUAL
        # -----------------------------------------------------------------
        path_resumen = RUTA_RESULTS / "resumen.txt"
        guardar_resumen(solucion, data, path_resumen)
        
        # -----------------------------------------------------------------
        # PASO 10: RESUMEN FINAL
        # -----------------------------------------------------------------
        print("=" * 70)
        print("EJECUCIÓN COMPLETADA EXITOSAMENTE")
        print("=" * 70)
        print(f"\nArchivos generados:")
        print(f"  ✓ {path_verificacion}")
        print(f"  ✓ {path_grafico}")
        print(f"  ✓ {path_resumen}")
        print(f"\nCosto total: {solucion['costo_total']:,.2f} COP")
        print(f"Vehículos usados: {solucion['num_vehiculos_usados']}/{data['num_vehicles']}")
        print(f"Distancia total: {solucion['distancia_total_sistema']:.2f} km")
        print(f"Clientes atendidos: {solucion['clientes_atendidos']}/{solucion['clientes_totales']}")
        print("\n" + "=" * 70 + "\n")
        
    except FileNotFoundError as e:
        print(f"\n❌ ERROR: Archivos no encontrados")
        print(f"{e}")
        sys.exit(1)
        
    except RuntimeError as e:
        print(f"\n❌ ERROR: Problema durante la optimización")
        print(f"{e}")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ ERROR INESPERADO: {type(e).__name__}")
        print(f"{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


# ===========================
# PUNTO DE ENTRADA
# ===========================

if __name__ == "__main__":
    main()
