"""
Test de Factibilidad Caso 2 - TAMAÑO MEDIO
============================================
Probar con 5 clientes + 5 estaciones para determinar dónde se vuelve infactible
"""

import sys
from pathlib import Path
import pyomo.environ as pyo

# Añadir src al path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / 'src'))

try:
    from carga_datos import cargar_caso_base, cargar_caso2
    from modelo_caso2 import build_model_caso2
except ImportError as e:
    print(f"Error importando módulos: {e}")
    print(f"PROJECT_ROOT: {PROJECT_ROOT}")
    print(f"sys.path: {sys.path[:3]}")
    sys.exit(1)

def main():
    # 1. Cargar datos completos
    data_base = cargar_caso_base()
    data2 = cargar_caso2(data_base)
    
    DEPOT = data2['DEPOT']
    
    # 2. SELECCIONAR SUBSET DE CLIENTES Y ESTACIONES
    # Usar 5 clientes más lejanos (requieren combustible) + 5 estaciones
    clientes_lejanos = ['C005', 'C007', 'C010', 'C012', 'C014']  # Los que exceden autonomía
    estaciones_cercanas = ['E001', 'E002', 'E003', 'E004', 'E005']
    
    CLIENTS_MINI = clientes_lejanos
    STATIONS_MINI = estaciones_cercanas
    NODES_MINI = [DEPOT] + CLIENTS_MINI + STATIONS_MINI
    
    # Usar solo V001, V002, V005 (mix de capacidades)
    VEHICLES_MINI = ['V001', 'V002', 'V005']
    
    print("=" * 80)
    print("TEST DE FACTIBILIDAD - TAMAÑO MEDIO")
    print("=" * 80)
    print(f"Clientes: {len(CLIENTS_MINI)} ({', '.join(CLIENTS_MINI)})")
    print(f"Estaciones: {len(STATIONS_MINI)} ({', '.join(STATIONS_MINI)})")
    print(f"Vehículos: {len(VEHICLES_MINI)} ({', '.join(VEHICLES_MINI)})")
    print()
    
    # 3. ANÁLISIS DE FACTIBILIDAD GEOMÉTRICA
    print("[ANÁLISIS DE FACTIBILIDAD]")
    for vid in VEHICLES_MINI:
        vdata = data2['veh'][vid]
        autonomia = vdata['fuel_cap'] * data2['km_per_gallon']
        print(f"{vid} - Autonomía: {autonomia} km")
        
        for cid in CLIENTS_MINI:
            dist_ida = data2['dist'][(DEPOT, cid)]
            dist_vuelta = data2['dist'][(cid, DEPOT)]
            dist_total = dist_ida + dist_vuelta
            
            if dist_total > autonomia:
                print(f"  {DEPOT} -> {cid} -> {DEPOT}: {dist_total:.1f} km [EXCEDE por {dist_total - autonomia:.1f} km] ❌")
            else:
                print(f"  {DEPOT} -> {cid} -> {DEPOT}: {dist_total:.1f} km [OK] ✓")
    
    print()
    print("[ESTACIONES INTERMEDIAS]")
    for cid in CLIENTS_MINI:
        dist_directa = data2['dist'][(DEPOT, cid)] + data2['dist'][(cid, DEPOT)]
        print(f"Ruta a {cid}: directa={dist_directa:.0f}km ", end="")
        
        # Buscar estación más cercana
        mejor_estacion = None
        mejor_dist = float('inf')
        for eid in STATIONS_MINI:
            dist_via_e = data2['dist'][(DEPOT, eid)] + data2['dist'][(eid, cid)] + data2['dist'][(cid, DEPOT)]
            if dist_via_e < mejor_dist:
                mejor_dist = dist_via_e
                mejor_estacion = eid
        
        print(f"/ Vía {mejor_estacion}: {DEPOT}(0km)->{mejor_estacion[1:]}({data2['dist'][(DEPOT, mejor_estacion)]:.0f}km)->{cid}({data2['dist'][(mejor_estacion, cid)]:.0f}km) = {mejor_dist:.0f} km total")
    
    print()
    
    # 4. Filtrar datos para mini-problema
    data_mini = {
        'DEPOT': DEPOT,
        'CLIENTS': CLIENTS_MINI,
        'STATIONS': STATIONS_MINI,
        'NODES': NODES_MINI,
        'VEHICLES': VEHICLES_MINI,
        'demanda': {k: v for k, v in data2['demanda'].items() if k in CLIENTS_MINI},
        'veh': {k: v for k, v in data2['veh'].items() if k in VEHICLES_MINI},
        'stations': {k: v for k, v in data2['stations'].items() if k in STATIONS_MINI},
        'dist': {(i, j): data2['dist'][(i, j)] for i in NODES_MINI for j in NODES_MINI if i != j},
        'fixed_cost': data2['fixed_cost'],
        'cost_per_km': data2['cost_per_km'],
        'cost_per_h': data2['cost_per_h'],
        'km_per_gallon': data2['km_per_gallon'],
        'velocity': data2['velocity']
    }
    
    # 5. Construir y resolver modelo
    print("[CONSTRUYENDO MODELO]")
    model = build_model_caso2(data_mini)
    
    print(f"Tamaño: {model.nconstraints()} restricciones, {model.nvariables()} variables")
    print()
    
    # 6. Resolver con HiGHS
    print("[RESOLVIENDO CON HIGHS - límite 120 segundos]")
    solver = pyo.SolverFactory('appsi_highs')
    solver.options['mip_rel_gap'] = 0.10
    solver.options['time_limit'] = 120  # 2 minutos
    solver.options['output_flag'] = True
    
    results = solver.solve(model, tee=True)
    
    print()
    print("=" * 80)
    print("RESULTADO MEDIO-INSTANCIA")
    print("=" * 80)
    print()
    
    termination = results.solver.termination_condition
    
    if termination == pyo.TerminationCondition.optimal:
        print("✓ Solución ÓPTIMA encontrada")
        print(f"→ El problema con {len(CLIENTS_MINI)} clientes ES FACTIBLE")
        objetivo = pyo.value(model.objetivo)
        print(f"→ Costo total: ${objetivo:,.2f} COP")
    elif termination == pyo.TerminationCondition.maxTimeLimit:
        if results.problem.upper_bound < float('inf'):
            print("✓ Solución FACTIBLE encontrada (tiempo límite)")
            print(f"→ El problema con {len(CLIENTS_MINI)} clientes ES FACTIBLE")
            objetivo = results.problem.upper_bound
            print(f"→ Costo total: ${objetivo:,.2f} COP")
        else:
            print("❌ NO se encontró solución factible en 120 segundos")
            print(f"→ El problema con {len(CLIENTS_MINI)} clientes podría ser INFACTIBLE")
            print(f"→ O necesita más tiempo de resolución")
    else:
        print(f"❌ Terminación: {termination}")
        print("→ Problema INFACTIBLE o error en modelo")
    
    print()
    print(results.solver)
    print()


if __name__ == '__main__':
    main()
