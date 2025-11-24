# -*- coding: utf-8 -*-
"""
Análisis Completo del Caso 3 - VRP con Combustible + Peajes + Restricciones
Proyecto C: Optimización de Rutas de Distribución

Este script genera:
1. Mapas detallados con rutas, recargas y restricciones
2. Tablas detalladas por vehículo
3. Análisis de sensibilidad (precios, autonomía, estaciones)
4. Conclusiones estratégicas para LogistiCo

Autor: Sistema de Optimización
Fecha: Noviembre 2025
"""

import sys
import os
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
import seaborn as sns
from typing import Dict, List, Tuple
import json
from openpyxl.utils import get_column_letter

# Configurar encoding UTF-8
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Agregar directorio src al path
sys.path.insert(0, str(Path(__file__).parent))

from datos_caso3 import cargar_datos_caso3
from modelo_caso3 import build_model_caso3, extraer_solucion_caso3
import pyomo.environ as pyo


# ============================================================================
# CONFIGURACIÓN
# ============================================================================

RESULTS_PATH = Path("results/caso3")
DATA_PATH = Path("../project_c/Proyecto_C_Caso3")
COORDS_PATH = Path("../Proyecto_Caso_Base")

# Configurar estilo de gráficos
sns.set_style("whitegrid")
plt.rcParams['figure.dpi'] = 300
plt.rcParams['font.size'] = 10


# ============================================================================
# FUNCIONES DE VISUALIZACIÓN AVANZADA
# ============================================================================

def generar_mapa_detallado(sol3: Dict, data3: Dict, output_path: Path):
    """
    Genera mapa detallado mostrando:
    - Rutas con números de secuencia
    - Estaciones de recarga (destacadas)
    - Dirección del flujo
    - Leyenda completa con métricas
    """
    print("\n[MAPA DETALLADO] Generando visualización...")
    
    fig = plt.figure(figsize=(18, 12))
    gs = GridSpec(3, 3, figure=fig, hspace=0.3, wspace=0.3)
    
    # Mapa principal
    ax_main = fig.add_subplot(gs[:2, :2])
    
    coords = data3['coords']
    DEPOT = data3['DEPOT']
    CLIENTS = data3['CLIENTS']
    STATIONS = data3['STATIONS']
    TOLL_ARCS = data3['TOLL_ARCS']
    
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
    
    # Dibujar rutas con flechas direccionales
    for idx, v in enumerate(sol3['vehiculos_usados']):
        ruta = sol3['rutas'][v]
        color = colors[idx % len(colors)]
        
        for i in range(len(ruta) - 1):
            nodo_origen = ruta[i]
            nodo_destino = ruta[i + 1]
            
            x1, y1 = coords[nodo_origen][1], coords[nodo_origen][0]
            x2, y2 = coords[nodo_destino][1], coords[nodo_destino][0]
            
            # Verificar si es peaje
            es_peaje = (nodo_origen, nodo_destino) in TOLL_ARCS
            
            if es_peaje:
                ax_main.annotate('', xy=(x2, y2), xytext=(x1, y1),
                               arrowprops=dict(arrowstyle='->', lw=3, color='red',
                                             linestyle='--', alpha=0.8))
            else:
                ax_main.annotate('', xy=(x2, y2), xytext=(x1, y1),
                               arrowprops=dict(arrowstyle='->', lw=2, color=color,
                                             alpha=0.6))
            
            # Número de secuencia
            mid_x, mid_y = (x1 + x2) / 2, (y1 + y2) / 2
            ax_main.text(mid_x, mid_y, str(i+1), fontsize=7, 
                        bbox=dict(boxstyle='circle', facecolor='white', 
                                edgecolor=color, alpha=0.8))
    
    # Dibujar nodos
    ax_main.plot(coords[DEPOT][1], coords[DEPOT][0], '^r', markersize=20,
                markeredgewidth=2, markeredgecolor='black', zorder=5)
    ax_main.text(coords[DEPOT][1], coords[DEPOT][0] + 0.02, DEPOT,
                fontsize=12, fontweight='bold', ha='center', va='bottom')
    
    # Clientes
    for c in CLIENTS:
        ax_main.plot(coords[c][1], coords[c][0], 'o', color='blue',
                    markersize=10, markeredgewidth=1.5, markeredgecolor='black', zorder=4)
        ax_main.text(coords[c][1], coords[c][0] + 0.015, c,
                    fontsize=8, ha='center', va='bottom')
    
    # Estaciones (destacar las usadas)
    estaciones_usadas = set()
    for v in sol3['vehiculos_usados']:
        estaciones_usadas.update(sol3['estaciones_visitadas'][v])
    
    for s in STATIONS:
        if s in estaciones_usadas:
            # Estación usada con efecto de resaltado
            ax_main.plot(coords[s][1], coords[s][0], 's', color='limegreen',
                        markersize=18, markeredgewidth=3, markeredgecolor='darkgreen',
                        zorder=4)
            # Círculo de énfasis
            circle = plt.Circle((coords[s][1], coords[s][0]), 0.03,
                              color='yellow', alpha=0.3, zorder=3)
            ax_main.add_patch(circle)
            ax_main.text(coords[s][1], coords[s][0] - 0.02, s,
                        fontsize=9, ha='center', va='top', fontweight='bold',
                        color='darkgreen')
        else:
            ax_main.plot(coords[s][1], coords[s][0], 's', color='lightgreen',
                        markersize=10, alpha=0.4, markeredgewidth=1,
                        markeredgecolor='gray', zorder=3)
    
    ax_main.set_xlabel('Longitud', fontsize=12, fontweight='bold')
    ax_main.set_ylabel('Latitud', fontsize=12, fontweight='bold')
    ax_main.set_title('Mapa Detallado de Rutas - Caso 3', fontsize=14, fontweight='bold')
    ax_main.grid(True, alpha=0.3)
    ax_main.set_aspect('equal', adjustable='box')
    
    # Panel de métricas por vehículo (derecha)
    ax_metrics = fig.add_subplot(gs[:2, 2])
    ax_metrics.axis('off')
    
    metrics_text = "MÉTRICAS POR VEHÍCULO\n" + "="*30 + "\n\n"
    for idx, v in enumerate(sol3['vehiculos_usados']):
        color = colors[idx % len(colors)]
        metrics_text += f"● {v} (━━ color)\n"
        metrics_text += f"  Clientes: {len(sol3['clientes_servidos'][v])}\n"
        metrics_text += f"  Demanda: {sol3['demandas_servidas'][v]:.1f} kg\n"
        metrics_text += f"  Distancia: {sol3['distancia_total'][v]:.1f} km\n"
        metrics_text += f"  Recargas: {len(sol3['recargas'][v])}\n"
        if sol3['recargas'][v]:
            for est, gal in sol3['recargas'][v].items():
                metrics_text += f"    - {est}: {gal:.1f} gal\n"
        metrics_text += f"  Peajes: {len(sol3['peajes_usados'][v])}\n"
        metrics_text += f"  Costo: ${sol3['costo_total_vehiculo'][v]:,.0f}\n\n"
    
    ax_metrics.text(0.05, 0.95, metrics_text, transform=ax_metrics.transAxes,
                   fontsize=9, verticalalignment='top', family='monospace',
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    # Gráfico de costos (abajo izquierda)
    ax_costos = fig.add_subplot(gs[2, 0])
    
    costo_fijo = sol3['num_vehiculos'] * data3['cost_fixed']
    costo_distancia = sum(sol3['distancia_total'][v] * data3['cost_km']
                         for v in sol3['vehiculos_usados'])
    costo_combustible = sum(sol3['costo_combustible'].values())
    costo_peajes = sum(sol3['costo_peajes'].values())
    
    componentes = ['Fijo', 'Distancia', 'Combustible', 'Peajes']
    valores = [costo_fijo, costo_distancia, costo_combustible, costo_peajes]
    colores_pie = ['#ff9999', '#66b3ff', '#99ff99', '#ffcc99']
    
    wedges, texts, autotexts = ax_costos.pie(valores, labels=componentes,
                                              autopct='%1.1f%%', startangle=90,
                                              colors=colores_pie)
    ax_costos.set_title('Distribución de Costos', fontsize=10, fontweight='bold')
    
    # Gráfico de distancias (abajo centro)
    ax_dist = fig.add_subplot(gs[2, 1])
    
    vehiculos = list(sol3['vehiculos_usados'])
    distancias = [sol3['distancia_total'][v] for v in vehiculos]
    
    bars = ax_dist.bar(range(len(vehiculos)), distancias, color=colors[:len(vehiculos)])
    ax_dist.set_xticks(range(len(vehiculos)))
    ax_dist.set_xticklabels([str(v).replace('V', '') if isinstance(v, str) else str(v) for v in vehiculos])
    ax_dist.set_xlabel('Vehículo', fontsize=10)
    ax_dist.set_ylabel('Distancia (km)', fontsize=10)
    ax_dist.set_title('Distancia por Vehículo', fontsize=10, fontweight='bold')
    ax_dist.grid(axis='y', alpha=0.3)
    
    # Resumen general (abajo derecha)
    ax_resumen = fig.add_subplot(gs[2, 2])
    ax_resumen.axis('off')
    
    resumen_text = "RESUMEN GENERAL\n" + "="*25 + "\n\n"
    resumen_text += f"Costo Total:\n${sol3['costo_total']:,.0f} COP\n\n"
    resumen_text += f"Vehículos: {sol3['num_vehiculos']}\n"
    resumen_text += f"Clientes: {sol3['num_clientes']}\n"
    resumen_text += f"Distancia Total:\n{sum(sol3['distancia_total'].values()):.1f} km\n\n"
    resumen_text += f"Recargas: {sum(len(r) for r in sol3['recargas'].values())}\n"
    resumen_text += f"Combustible:\n{sum(sum(r.values()) for r in sol3['recargas'].values()):.1f} gal\n\n"
    resumen_text += f"Peajes Cruzados:\n{sol3['num_peajes']}"
    
    ax_resumen.text(0.05, 0.95, resumen_text, transform=ax_resumen.transAxes,
                   fontsize=10, verticalalignment='top', family='monospace',
                   bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))
    
    plt.suptitle('Caso 3: Análisis Detallado de Rutas con Combustible y Peajes',
                fontsize=16, fontweight='bold', y=0.98)
    
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"✓ Mapa detallado generado: {output_path}")


def generar_tabla_detallada_vehiculos(sol3: Dict, data3: Dict, output_path: Path):
    """
    Genera tabla Excel con análisis detallado por vehículo
    """
    print("\n[TABLA DETALLADA] Generando Excel...")
    
    # Crear DataFrame con información detallada
    data_rows = []
    
    for v in sol3['vehiculos_usados']:
        # Información básica
        row = {
            'Vehiculo': v,
            'Tipo': data3.get('vehicle_types', {}).get(v, 'Standard'),
            'Capacidad_Carga_kg': data3['load_cap'][v],
            'Capacidad_Combustible_gal': data3['fuel_cap'][v],
            'Autonomia_km': data3['max_dist'][v]
        }
        
        # Ruta
        row['Ruta_Completa'] = ' → '.join(sol3['rutas'][v])
        row['Num_Paradas'] = len(sol3['rutas'][v]) - 1
        
        # Clientes
        row['Clientes_Servidos'] = ', '.join(sol3['clientes_servidos'][v])
        row['Num_Clientes'] = len(sol3['clientes_servidos'][v])
        row['Demanda_Total_kg'] = sol3['demandas_servidas'][v]
        row['Utilizacion_Capacidad_%'] = (sol3['demandas_servidas'][v] / 
                                          data3['load_cap'][v] * 100)
        
        # Combustible
        row['Estaciones_Visitadas'] = ', '.join(sol3['estaciones_visitadas'][v])
        row['Num_Recargas'] = len(sol3['recargas'][v])
        
        if sol3['recargas'][v]:
            recargas_detalle = [f"{est}:{gal:.1f}gal" 
                               for est, gal in sol3['recargas'][v].items()]
            row['Recargas_Detalle'] = ', '.join(recargas_detalle)
            row['Combustible_Total_gal'] = sum(sol3['recargas'][v].values())
        else:
            row['Recargas_Detalle'] = 'Sin recargas'
            row['Combustible_Total_gal'] = 0.0
        
        # Peajes
        row['Num_Peajes'] = len(sol3['peajes_usados'][v])
        if sol3['peajes_usados'][v]:
            peajes_detalle = [f"{i}→{j}" for i, j in sol3['peajes_usados'][v]]
            row['Peajes_Detalle'] = ', '.join(peajes_detalle)
        else:
            row['Peajes_Detalle'] = 'Sin peajes'
        
        # Métricas de distancia y tiempo
        row['Distancia_Total_km'] = sol3['distancia_total'][v]
        row['Tiempo_Total_h'] = sol3['tiempo_total'][v]
        row['Velocidad_Promedio_km/h'] = (sol3['distancia_total'][v] / 
                                          sol3['tiempo_total'][v] 
                                          if sol3['tiempo_total'][v] > 0 else 0)
        
        # Costos desagregados
        row['Costo_Fijo_COP'] = data3['cost_fixed']
        row['Costo_Distancia_COP'] = sol3['distancia_total'][v] * data3['cost_km']
        row['Costo_Combustible_COP'] = sol3['costo_combustible'][v]
        row['Costo_Peajes_COP'] = sol3['costo_peajes'][v]
        row['Costo_Total_COP'] = sol3['costo_total_vehiculo'][v]
        
        # Eficiencia
        if sol3['demandas_servidas'][v] > 0:
            row['Costo_por_kg_COP/kg'] = (sol3['costo_total_vehiculo'][v] / 
                                          sol3['demandas_servidas'][v])
            row['Costo_por_km_COP/km'] = (sol3['costo_total_vehiculo'][v] / 
                                         sol3['distancia_total'][v])
        else:
            row['Costo_por_kg_COP/kg'] = 0
            row['Costo_por_km_COP/km'] = 0
        
        data_rows.append(row)
    
    df = pd.DataFrame(data_rows)
    
    # Agregar fila de totales
    totales = {
        'Vehiculo': 'TOTAL',
        'Num_Clientes': sol3['num_clientes'],
        'Demanda_Total_kg': sum(sol3['demandas_servidas'].values()),
        'Num_Recargas': sum(len(r) for r in sol3['recargas'].values()),
        'Combustible_Total_gal': sum(sum(r.values()) for r in sol3['recargas'].values()),
        'Num_Peajes': sol3['num_peajes'],
        'Distancia_Total_km': sum(sol3['distancia_total'].values()),
        'Tiempo_Total_h': sum(sol3['tiempo_total'].values()),
        'Costo_Fijo_COP': data3['cost_fixed'] * sol3['num_vehiculos'],
        'Costo_Distancia_COP': sum(sol3['distancia_total'][v] * data3['cost_km']
                                   for v in sol3['vehiculos_usados']),
        'Costo_Combustible_COP': sum(sol3['costo_combustible'].values()),
        'Costo_Peajes_COP': sum(sol3['costo_peajes'].values()),
        'Costo_Total_COP': sol3['costo_total']
    }
    
    df = pd.concat([df, pd.DataFrame([totales])], ignore_index=True)
    
    # Guardar en Excel con formato
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Detalle_Vehiculos', index=False)
        
        # Ajustar anchos de columna
        worksheet = writer.sheets['Detalle_Vehiculos']
        for idx, col in enumerate(df.columns, start=1):
            max_length = max(df[col].astype(str).apply(len).max(), len(col)) + 2
            col_letter = get_column_letter(idx)
            worksheet.column_dimensions[col_letter].width = min(max_length, 50)
    
    print(f"✓ Tabla detallada generada: {output_path}")
    
    return df


def analisis_sensibilidad_precios(data3: Dict, output_path: Path,
                                  subset_clients: List[str] = None):
    """
    Análisis de sensibilidad ante cambios en precios de combustible
    """
    print("\n[SENSIBILIDAD PRECIOS] Analizando impacto de variación de precios...")
    
    # Escenarios de precios
    variaciones = [-20, -10, 0, 10, 20]  # Porcentajes
    resultados = []
    
    for var in variaciones:
        print(f"  Evaluando variación: {var:+d}%")
        
        # Modificar precios
        data_modificada = data3.copy()
        fuel_price_mod = {s: p * (1 + var/100) 
                         for s, p in data3['fuel_price'].items()}
        data_modificada['fuel_price'] = fuel_price_mod
        
        try:
            # Construir y resolver modelo
            model = build_model_caso3(data_modificada)
            solver = pyo.SolverFactory('highs')
            solver.options['time_limit'] = 300
            solver.options['mip_rel_gap'] = 0.15
            solver.options['log_to_console'] = False
            
            results = solver.solve(model, load_solutions=False)
            
            if results.solver.termination_condition in [pyo.TerminationCondition.optimal,
                                                        pyo.TerminationCondition.feasible]:
                model.solutions.load_from(results)
                sol = extraer_solucion_caso3(model, data_modificada)
                
                resultados.append({
                    'Variacion_%': var,
                    'Costo_Total': sol['costo_total'],
                    'Costo_Combustible': sum(sol['costo_combustible'].values()),
                    'Num_Vehiculos': sol['num_vehiculos'],
                    'Num_Recargas': sum(len(r) for r in sol['recargas'].values()),
                    'Distancia_Total': sum(sol['distancia_total'].values())
                })
            else:
                print(f"    ⚠ Solución infactible para variación {var}%")
                
        except Exception as e:
            print(f"    ✗ Error en variación {var}%: {e}")
    
    if not resultados:
        print("  ⚠ No se pudieron obtener resultados de sensibilidad")
        return None
    
    # Crear gráficos
    df_sens = pd.DataFrame(resultados)
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('Análisis de Sensibilidad: Variación de Precios de Combustible',
                fontsize=14, fontweight='bold')
    
    # Gráfico 1: Costo total vs variación
    axes[0, 0].plot(df_sens['Variacion_%'], df_sens['Costo_Total'],
                   marker='o', linewidth=2, markersize=8, color='blue')
    axes[0, 0].axvline(x=0, color='red', linestyle='--', alpha=0.5)
    axes[0, 0].set_xlabel('Variación de Precio (%)', fontweight='bold')
    axes[0, 0].set_ylabel('Costo Total (COP)', fontweight='bold')
    axes[0, 0].set_title('Impacto en Costo Total')
    axes[0, 0].grid(True, alpha=0.3)
    axes[0, 0].ticklabel_format(style='plain', axis='y')
    
    # Gráfico 2: Costo combustible vs variación
    axes[0, 1].plot(df_sens['Variacion_%'], df_sens['Costo_Combustible'],
                   marker='s', linewidth=2, markersize=8, color='green')
    axes[0, 1].axvline(x=0, color='red', linestyle='--', alpha=0.5)
    axes[0, 1].set_xlabel('Variación de Precio (%)', fontweight='bold')
    axes[0, 1].set_ylabel('Costo Combustible (COP)', fontweight='bold')
    axes[0, 1].set_title('Impacto en Costo de Combustible')
    axes[0, 1].grid(True, alpha=0.3)
    axes[0, 1].ticklabel_format(style='plain', axis='y')
    
    # Gráfico 3: Número de recargas
    axes[1, 0].bar(df_sens['Variacion_%'], df_sens['Num_Recargas'],
                  color=['red' if v < 0 else 'green' if v > 0 else 'gray'
                        for v in df_sens['Variacion_%']])
    axes[1, 0].set_xlabel('Variación de Precio (%)', fontweight='bold')
    axes[1, 0].set_ylabel('Número de Recargas', fontweight='bold')
    axes[1, 0].set_title('Estrategia de Recarga')
    axes[1, 0].grid(axis='y', alpha=0.3)
    
    # Gráfico 4: Tabla de resultados
    axes[1, 1].axis('off')
    
    tabla_text = "RESULTADOS DE SENSIBILIDAD\n" + "="*40 + "\n\n"
    for _, row in df_sens.iterrows():
        tabla_text += f"Variación: {int(row['Variacion_%']):+d}%\n"
        tabla_text += f"  Costo Total: ${row['Costo_Total']:,.0f}\n"
        tabla_text += f"  Costo Comb: ${row['Costo_Combustible']:,.0f}\n"
        tabla_text += f"  Recargas: {int(row['Num_Recargas'])}\n\n"
    
    axes[1, 1].text(0.05, 0.95, tabla_text, transform=axes[1, 1].transAxes,
                   fontsize=9, verticalalignment='top', family='monospace',
                   bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"✓ Análisis de sensibilidad generado: {output_path}")
    
    return df_sens


def generar_reporte_conclusiones(sol3: Dict, data3: Dict, 
                                 df_sensibilidad: pd.DataFrame,
                                 output_path: Path):
    """
    Genera reporte con conclusiones estratégicas
    """
    print("\n[CONCLUSIONES] Generando reporte estratégico...")
    
    # Análisis de estaciones
    estaciones_usadas = {}
    for v in sol3['vehiculos_usados']:
        for est in sol3['estaciones_visitadas'][v]:
            if est not in estaciones_usadas:
                estaciones_usadas[est] = {
                    'frecuencia': 0,
                    'volumen_total': 0,
                    'costo_total': 0,
                    'precio': data3['fuel_price'][est]
                }
            estaciones_usadas[est]['frecuencia'] += 1
            if est in sol3['recargas'][v]:
                vol = sol3['recargas'][v][est]
                estaciones_usadas[est]['volumen_total'] += vol
                estaciones_usadas[est]['costo_total'] += vol * data3['fuel_price'][est]
    
    # Análisis de vehículos
    eficiencia_vehiculos = []
    for v in sol3['vehiculos_usados']:
        if sol3['demandas_servidas'][v] > 0:
            eficiencia = {
                'vehiculo': v,
                'tipo': data3.get('vehicle_types', {}).get(v, 'Standard'),
                'capacidad': data3['load_cap'][v],
                'utilizacion_%': (sol3['demandas_servidas'][v] / 
                                 data3['load_cap'][v] * 100),
                'costo_por_kg': (sol3['costo_total_vehiculo'][v] / 
                                sol3['demandas_servidas'][v]),
                'clientes': len(sol3['clientes_servidos'][v]),
                'distancia': sol3['distancia_total'][v]
            }
            eficiencia_vehiculos.append(eficiencia)
    
    # Generar documento
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("# REPORTE DE CONCLUSIONES ESTRATÉGICAS - CASO 3\n")
        f.write("## VRP con Combustible, Peajes y Restricciones Viales\n\n")
        f.write("="*70 + "\n\n")
        
        # Resumen ejecutivo
        f.write("## 1. RESUMEN EJECUTIVO\n\n")
        f.write(f"**Costo Total de Operación:** ${sol3['costo_total']:,.2f} COP\n\n")
        f.write("### Distribución de Costos:\n\n")
        
        costo_fijo = sol3['num_vehiculos'] * data3['cost_fixed']
        costo_distancia = sum(sol3['distancia_total'][v] * data3['cost_km']
                             for v in sol3['vehiculos_usados'])
        costo_combustible = sum(sol3['costo_combustible'].values())
        costo_peajes = sum(sol3['costo_peajes'].values())
        
        f.write(f"- **Costo Fijo (vehículos):** ${costo_fijo:,.2f} ({costo_fijo/sol3['costo_total']*100:.1f}%)\n")
        f.write(f"- **Costo por Distancia:** ${costo_distancia:,.2f} ({costo_distancia/sol3['costo_total']*100:.1f}%)\n")
        f.write(f"- **Costo de Combustible:** ${costo_combustible:,.2f} ({costo_combustible/sol3['costo_total']*100:.1f}%)\n")
        f.write(f"- **Costo de Peajes:** ${costo_peajes:,.2f} ({costo_peajes/sol3['costo_total']*100:.1f}%)\n\n")
        
        f.write("### Métricas Operacionales:\n\n")
        f.write(f"- Vehículos utilizados: {sol3['num_vehiculos']}\n")
        f.write(f"- Clientes atendidos: {sol3['num_clientes']}\n")
        f.write(f"- Distancia total recorrida: {sum(sol3['distancia_total'].values()):.1f} km\n")
        f.write(f"- Recargas realizadas: {sum(len(r) for r in sol3['recargas'].values())}\n")
        f.write(f"- Peajes cruzados: {sol3['num_peajes']}\n\n")
        
        # Pregunta 1: Acuerdos con estaciones
        f.write("="*70 + "\n\n")
        f.write("## 2. ¿DÓNDE DEBERÍA LogistiCo ESTABLECER ACUERDOS CON ESTACIONES?\n\n")
        
        if estaciones_usadas:
            # Ordenar por frecuencia y volumen
            estaciones_sorted = sorted(estaciones_usadas.items(),
                                     key=lambda x: (x[1]['frecuencia'], 
                                                   x[1]['volumen_total']),
                                     reverse=True)
            
            f.write("### Estaciones Prioritarias para Negociación:\n\n")
            for i, (est, info) in enumerate(estaciones_sorted[:5], 1):
                f.write(f"**{i}. Estación {est}**\n")
                f.write(f"   - Frecuencia de uso: {info['frecuencia']} visitas\n")
                f.write(f"   - Volumen total: {info['volumen_total']:.1f} galones\n")
                f.write(f"   - Costo total: ${info['costo_total']:,.2f} COP\n")
                f.write(f"   - Precio actual: ${info['precio']:,.2f} COP/gal\n")
                f.write(f"   - **Potencial ahorro con descuento 10%:** ${info['costo_total']*0.1:,.2f} COP\n\n")
            
            f.write("### Recomendaciones:\n\n")
            if len(estaciones_sorted) > 0:
                est_top = estaciones_sorted[0]
                f.write(f"1. **Prioridad ALTA:** Negociar acuerdo con {est_top[0]} "
                       f"(ahorro potencial: ${est_top[1]['costo_total']*0.1:,.2f} COP)\n")
            
            estaciones_caras = sorted(estaciones_sorted,
                                    key=lambda x: x[1]['precio'], reverse=True)[:3]
            f.write(f"2. **Optimización de precios:** Considerar estaciones alternativas a ")
            f.write(f"{', '.join([e[0] for e in estaciones_caras])} por precios altos\n")
            
            f.write(f"3. **Consolidación:** Enfocar recargas en 2-3 estaciones principales "
                   f"para aumentar poder de negociación\n\n")
        else:
            f.write("No se requirieron recargas en la solución actual.\n\n")
        
        # Pregunta 2: Eficiencia de camiones
        f.write("="*70 + "\n\n")
        f.write("## 3. ¿QUÉ TIPO DE CAMIONES SON MÁS EFICIENTES?\n\n")
        
        if eficiencia_vehiculos:
            df_ef = pd.DataFrame(eficiencia_vehiculos)
            df_ef_sorted = df_ef.sort_values('costo_por_kg')
            
            f.write("### Ranking de Eficiencia (Costo por kg transportado):\n\n")
            for i, row in df_ef_sorted.iterrows():
                f.write(f"**{row['vehiculo']}** ({row['tipo']})\n")
                f.write(f"   - Costo por kg: ${row['costo_por_kg']:,.2f} COP/kg\n")
                f.write(f"   - Utilización: {row['utilizacion_%']:.1f}%\n")
                f.write(f"   - Clientes servidos: {row['clientes']}\n")
                f.write(f"   - Distancia recorrida: {row['distancia']:.1f} km\n\n")
            
            f.write("### Análisis de Patrones:\n\n")
            
            # Agrupar por capacidad
            df_ef['categoria'] = df_ef['capacidad'].apply(
                lambda x: 'Grande' if x > 60000 else 'Mediano' if x > 40000 else 'Pequeño'
            )
            
            for cat in ['Grande', 'Mediano', 'Pequeño']:
                df_cat = df_ef[df_ef['categoria'] == cat]
                if not df_cat.empty:
                    f.write(f"**Camiones {cat}s:**\n")
                    f.write(f"   - Costo promedio: ${df_cat['costo_por_kg'].mean():,.2f} COP/kg\n")
                    f.write(f"   - Utilización promedio: {df_cat['utilizacion_%'].mean():.1f}%\n")
                    f.write(f"   - Distancia promedio: {df_cat['distancia'].mean():.1f} km\n\n")
            
            f.write("### Recomendaciones:\n\n")
            mejor = df_ef_sorted.iloc[0]
            f.write(f"1. **Vehículo más eficiente:** {mejor['vehiculo']} "
                   f"(${mejor['costo_por_kg']:,.2f} COP/kg)\n")
            
            bajo_uso = df_ef[df_ef['utilizacion_%'] < 50]
            if not bajo_uso.empty:
                f.write(f"2. **Optimizar utilización:** Vehículos "
                       f"{', '.join(bajo_uso['vehiculo'].tolist())} "
                       f"tienen baja utilización (<50%)\n")
            
            f.write(f"3. **Estrategia de flota:** Balance entre costo fijo (favorece pocos vehículos grandes) "
                   f"y flexibilidad (favorece más vehículos pequeños)\n\n")
        
        # Pregunta 3: Impacto de peajes
        f.write("="*70 + "\n\n")
        f.write("## 4. ¿CÓMO AFECTAN LOS PEAJES LA ASIGNACIÓN DE RUTAS?\n\n")
        
        if sol3['num_peajes'] > 0:
            f.write(f"### Impacto Actual:\n\n")
            f.write(f"- Peajes cruzados: {sol3['num_peajes']}\n")
            f.write(f"- Costo total de peajes: ${costo_peajes:,.2f} COP\n")
            f.write(f"- Proporción del costo total: {costo_peajes/sol3['costo_total']*100:.2f}%\n\n")
            
            f.write("### Peajes por Vehículo:\n\n")
            for v in sol3['vehiculos_usados']:
                if sol3['peajes_usados'][v]:
                    f.write(f"**{v}:**\n")
                    f.write(f"   - Peajes: {len(sol3['peajes_usados'][v])}\n")
                    f.write(f"   - Costo: ${sol3['costo_peajes'][v]:,.2f} COP\n")
                    f.write(f"   - Arcos: {', '.join([f'{i}→{j}' for i,j in sol3['peajes_usados'][v]])}\n\n")
        else:
            f.write("**Situación Actual:** No se cruzaron peajes en la solución óptima.\n\n")
            f.write("Esto sugiere que:\n")
            f.write("- Las rutas directas sin peajes son más económicas\n")
            f.write("- Los costos de peaje son significativos en comparación con desvíos\n")
            f.write("- La optimización priorizó evitar peajes sobre minimizar distancia\n\n")
        
        # Análisis de sensibilidad
        if df_sensibilidad is not None:
            f.write("="*70 + "\n\n")
            f.write("## 5. ANÁLISIS DE SENSIBILIDAD\n\n")
            
            f.write("### Variación de Precios de Combustible:\n\n")
            f.write("| Variación | Costo Total | Costo Combustible | Recargas |\n")
            f.write("|-----------|-------------|-------------------|----------|\n")
            for _, row in df_sensibilidad.iterrows():
                f.write(f"| {row['Variacion_%']:+d}% | ")
                f.write(f"${row['Costo_Total']:,.0f} | ")
                f.write(f"${row['Costo_Combustible']:,.0f} | ")
                f.write(f"{row['Num_Recargas']:.0f} |\n")
            
            f.write("\n### Observaciones:\n\n")
            
            # Calcular elasticidad
            base_row = df_sensibilidad[df_sensibilidad['Variacion_%'] == 0].iloc[0]
            cambio_precio = 20  # 20%
            row_alta = df_sensibilidad[df_sensibilidad['Variacion_%'] == 20].iloc[0]
            
            cambio_costo = ((row_alta['Costo_Total'] - base_row['Costo_Total']) / 
                          base_row['Costo_Total'] * 100)
            elasticidad = cambio_costo / cambio_precio
            
            f.write(f"- **Elasticidad del costo total:** {elasticidad:.3f}\n")
            f.write(f"  (Un aumento del 20% en precios genera un aumento del {cambio_costo:.2f}% en costo total)\n\n")
            
            if elasticidad < 0.5:
                f.write("- El costo total es **poco sensible** a cambios en precios de combustible\n")
                f.write("- Otros componentes (fijo, distancia) dominan el costo\n")
            else:
                f.write("- El costo total es **moderadamente sensible** a cambios en precios\n")
                f.write("- Importante negociar precios de combustible\n")
        
        # Recomendaciones finales
        f.write("\n" + "="*70 + "\n\n")
        f.write("## 6. RECOMENDACIONES ESTRATÉGICAS FINALES\n\n")
        
        f.write("### Corto Plazo (1-3 meses):\n\n")
        f.write("1. Establecer acuerdos con las 3 estaciones más utilizadas\n")
        f.write("2. Optimizar rutas para consolidar recargas\n")
        f.write("3. Monitorear utilización de vehículos para ajustar flota\n\n")
        
        f.write("### Mediano Plazo (3-6 meses):\n\n")
        f.write("1. Evaluar reemplazo de vehículos con baja eficiencia\n")
        f.write("2. Considerar vehículos con mayor autonomía para reducir recargas\n")
        f.write("3. Analizar rutas alternativas para evitar peajes costosos\n\n")
        
        f.write("### Largo Plazo (6-12 meses):\n\n")
        f.write("1. Invertir en tecnología de monitoreo de combustible en tiempo real\n")
        f.write("2. Establecer contratos de largo plazo con estaciones estratégicas\n")
        f.write("3. Optimizar composición de flota según patrones de demanda\n\n")
        
        f.write("="*70 + "\n\n")
        f.write(f"**Reporte generado:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Herramienta:** Sistema de Optimización Pyomo + HiGHS\n")
        f.write(f"**Caso:** Proyecto C - Caso 3 (VRP con Combustible + Peajes)\n")
    
    print(f"✓ Reporte de conclusiones generado: {output_path}")


# ============================================================================
# FUNCIÓN PRINCIPAL
# ============================================================================

def main():
    """
    Ejecuta análisis completo del Caso 3
    """
    print("\n" + "="*80)
    print("ANÁLISIS COMPLETO - CASO 3")
    print("="*80)
    
    # Usar subset pequeño para pruebas
    subset = ['C001', 'C002']
    
    print(f"\nUsando subset de clientes: {subset}")
    print("\n" + "="*80)
    print("PASO 1: CARGANDO DATOS Y RESOLVIENDO MODELO")
    print("="*80)
    
    # Cargar datos
    data3 = cargar_datos_caso3(
        ruta_data=str(DATA_PATH),
        ruta_coords=str(COORDS_PATH),
        clientes_subset=subset,
        escenario='base'
    )
    
    # Construir y resolver modelo
    model = build_model_caso3(data3)
    
    solver = pyo.SolverFactory('highs')
    solver.options['time_limit'] = 300
    solver.options['mip_rel_gap'] = 0.10
    solver.options['log_to_console'] = False
    
    print("\nResolviendo modelo...")
    results = solver.solve(model, load_solutions=False)
    
    if results.solver.termination_condition not in [pyo.TerminationCondition.optimal,
                                                     pyo.TerminationCondition.feasible]:
        print("✗ No se pudo obtener solución factible")
        return
    
    model.solutions.load_from(results)
    sol3 = extraer_solucion_caso3(model, data3)
    
    print(f"✓ Solución obtenida: ${sol3['costo_total']:,.2f} COP")
    
    # Crear directorio de resultados
    RESULTS_PATH.mkdir(parents=True, exist_ok=True)
    
    # Generar outputs
    print("\n" + "="*80)
    print("PASO 2: GENERANDO VISUALIZACIONES Y ANÁLISIS")
    print("="*80)
    
    # 1. Mapa detallado
    generar_mapa_detallado(sol3, data3, RESULTS_PATH / "mapa_detallado_caso3.png")
    
    # 2. Tabla Excel detallada
    df_vehiculos = generar_tabla_detallada_vehiculos(sol3, data3,
                                                     RESULTS_PATH / "analisis_vehiculos_caso3.xlsx")
    
    # 3. Análisis de sensibilidad
    df_sens = analisis_sensibilidad_precios(data3, 
                                            RESULTS_PATH / "sensibilidad_precios_caso3.png",
                                            subset_clients=subset)
    
    # 4. Reporte de conclusiones
    generar_reporte_conclusiones(sol3, data3, df_sens,
                                 RESULTS_PATH / "conclusiones_estrategicas_caso3.md")
    
    print("\n" + "="*80)
    print("✓ ANÁLISIS COMPLETO FINALIZADO")
    print("="*80)
    print("\nArchivos generados en results/caso3/:")
    print("  • mapa_detallado_caso3.png")
    print("  • analisis_vehiculos_caso3.xlsx")
    print("  • sensibilidad_precios_caso3.png")
    print("  • conclusiones_estrategicas_caso3.md")
    print("\n" + "="*80)


if __name__ == "__main__":
    main()
