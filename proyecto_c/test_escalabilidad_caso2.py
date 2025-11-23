"""
Test de Escalabilidad - Caso 2
================================
Prueba sistemática añadiendo clientes gradualmente para encontrar
el punto donde el modelo se vuelve infactible o muy difícil de resolver.

Escenarios a probar:
- 2 clientes (baseline: sabemos que funciona)
- 4 clientes
- 6 clientes  
- 8 clientes
- 10 clientes
- 12 clientes
- 14 clientes (problema completo)

Para cada escenario, usar:
- Los clientes MÁS LEJANOS (que requieren estaciones)
- Todas las estaciones disponibles
- Todos los vehículos (5)
- Límite de tiempo: 120 segundos por escenario
"""

import sys
from pathlib import Path
import pyomo.environ as pyo
import time
from datetime import datetime

# Importar módulos
sys.path.insert(0, str(Path(__file__).parent / 'src'))
from datos_caso2 import cargar_datos_caso2
from modelo_caso2 import build_model_caso2

PROJECT_ROOT = Path(__file__).parent
DATA_CASO2 = PROJECT_ROOT.parent / 'project_c' / 'Proyecto_C_Caso2'
DATA_BASE = PROJECT_ROOT.parent / 'Proyecto_Caso_Base'

# Clientes ordenados por distancia al depósito (más lejanos primero)
# Estos son los que MÁS necesitan estaciones
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

def test_escenario(n_clientes, time_limit=120):
    """
    Prueba un escenario con n_clientes más lejanos
    
    Returns:
        dict con resultado del test
    """
    print("=" * 80)
    print(f"ESCENARIO: {n_clientes} CLIENTES")
    print("=" * 80)
    
    # 1. Cargar datos completos
    data_full = cargar_datos_caso2(str(DATA_CASO2), str(DATA_BASE))
    
    DEPOT = data_full['DEPOT']
    CLIENTS_SUBSET = CLIENTES_LEJANOS[:n_clientes]
    STATIONS = data_full['STATIONS']  # Todas las estaciones disponibles
    VEHICLES = data_full['VEHICLES']  # Todos los vehículos disponibles
    
    NODES_SUBSET = [DEPOT] + CLIENTS_SUBSET + STATIONS
    
    print(f"Configuración:")
    print(f"  - Clientes: {n_clientes} ({', '.join(CLIENTS_SUBSET[:3])}...)")
    print(f"  - Estaciones: {len(STATIONS)} (todas disponibles)")
    print(f"  - Vehículos: {len(VEHICLES)} (todos disponibles)")
    print(f"  - Límite de tiempo: {time_limit}s")
    print()
    
    # 2. Análisis de demanda vs capacidad
    demanda_total = sum(data_full['demanda'][c] for c in CLIENTS_SUBSET)
    capacidad_total = sum(data_full['load_cap'][v] for v in VEHICLES)
    
    print(f"Análisis de capacidad:")
    print(f"  - Demanda total: {demanda_total:.1f} kg")
    print(f"  - Capacidad flota: {capacidad_total:.1f} kg")
    print(f"  - Ratio: {capacidad_total / demanda_total:.2f}x")
    
    if capacidad_total < demanda_total:
        print("  ⚠️  CAPACIDAD INSUFICIENTE!")
        return {
            'n_clientes': n_clientes,
            'status': 'infeasible_capacity',
            'tiempo': 0,
            'objetivo': None,
            'gap': None,
            'nodos': 0
        }
    print()
    
    # 3. Análisis de autonomía
    print(f"Análisis de autonomía:")
    autonomias = {v: data_full['fuel_cap'][v] * data_full['fuel_efficiency'] 
                  for v in VEHICLES}
    autonomia_max = max(autonomias.values())
    
    clientes_problema = []
    for c in CLIENTS_SUBSET:
        dist_directa = data_full['dist'][(DEPOT, c)] + data_full['dist'][(c, DEPOT)]
        if dist_directa > autonomia_max:
            clientes_problema.append((c, dist_directa))
    
    if clientes_problema:
        print(f"  {len(clientes_problema)} clientes exceden autonomía máxima ({autonomia_max:.0f} km):")
        for c, d in clientes_problema[:3]:
            print(f"    - {c}: {d:.0f} km")
        print("  → Requieren recargas intermedias en estaciones")
    else:
        print(f"  ✓ Todos los clientes accesibles sin estaciones")
    print()
    
    # 4. Filtrar datos para el subset
    data_subset = {
        'DEPOT': DEPOT,
        'CLIENTS': CLIENTS_SUBSET,
        'STATIONS': STATIONS,
        'NODES': NODES_SUBSET,
        'VEHICLES': VEHICLES,
        'demanda': {k: v for k, v in data_full['demanda'].items() if k in CLIENTS_SUBSET},
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
    
    # 5. Construir modelo
    print("[CONSTRUYENDO MODELO]")
    start_build = time.time()
    model = build_model_caso2(data_subset)
    time_build = time.time() - start_build
    
    print(f"  Variables: {model.nvariables()}")
    print(f"  Restricciones: {model.nconstraints()}")
    print(f"  Tiempo construcción: {time_build:.2f}s")
    print()
    
    # 6. Resolver
    print(f"[RESOLVIENDO - límite {time_limit}s]")
    solver = pyo.SolverFactory('appsi_highs')
    solver.options['mip_rel_gap'] = 0.10
    solver.options['time_limit'] = time_limit
    solver.options['output_flag'] = True
    
    start_solve = time.time()
    results = solver.solve(model, tee=True)
    time_solve = time.time() - start_solve
    
    # 7. Analizar resultado
    print()
    print("-" * 80)
    
    termination = results.solver.termination_condition
    resultado = {
        'n_clientes': n_clientes,
        'tiempo_build': time_build,
        'tiempo_solve': time_solve,
        'variables': model.nvariables(),
        'restricciones': model.nconstraints()
    }
    
    if termination == pyo.TerminationCondition.optimal:
        objetivo = pyo.value(model.objetivo)
        gap = results.problem.upper_bound - results.problem.lower_bound
        gap_pct = (gap / results.problem.upper_bound) * 100 if results.problem.upper_bound > 0 else 0
        
        print(f"✓ OPTIMO encontrado")
        print(f"  Costo: ${objetivo:,.0f}")
        print(f"  Gap: {gap_pct:.2f}%")
        print(f"  Tiempo: {time_solve:.2f}s")
        
        resultado.update({
            'status': 'optimal',
            'objetivo': objetivo,
            'gap': gap_pct,
            'solvable': True
        })
        
    elif termination == pyo.TerminationCondition.maxTimeLimit:
        if results.problem.upper_bound < float('inf'):
            objetivo = results.problem.upper_bound
            gap = results.problem.upper_bound - results.problem.lower_bound
            gap_pct = (gap / results.problem.upper_bound) * 100 if results.problem.upper_bound > 0 else 0
            
            print(f"✓ FACTIBLE encontrado (tiempo límite)")
            print(f"  Costo: ${objetivo:,.0f}")
            print(f"  Gap: {gap_pct:.2f}%")
            print(f"  Tiempo: {time_solve:.2f}s")
            
            resultado.update({
                'status': 'feasible_time_limit',
                'objetivo': objetivo,
                'gap': gap_pct,
                'solvable': True
            })
        else:
            print(f"❌ NO FACTIBLE en {time_limit}s")
            print(f"  Dual bound: {results.problem.lower_bound:,.0f}")
            print(f"  Tiempo: {time_solve:.2f}s")
            
            resultado.update({
                'status': 'infeasible_time_limit',
                'objetivo': None,
                'gap': None,
                'solvable': False
            })
    else:
        print(f"❌ INFACTIBLE")
        print(f"  Terminacion: {termination}")
        
        resultado.update({
            'status': 'infeasible',
            'objetivo': None,
            'gap': None,
            'solvable': False
        })
    
    print()
    return resultado


def main():
    print("=" * 80)
    print("TEST DE ESCALABILIDAD - CASO 2")
    print("=" * 80)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("Objetivo: Encontrar el punto donde el modelo completo")
    print("          se vuelve difícil de resolver o infactible")
    print()
    print("Estrategia:")
    print("  1. Usar clientes MAS LEJANOS (requieren estaciones)")
    print("  2. Incluir TODAS las estaciones (12)")
    print("  3. Incluir TODOS los vehiculos (5)")
    print("  4. Escalar numero de clientes: 2 -> 4 -> 6 -> 8 -> 10 -> 12 -> 14")
    print("  5. Limite: 120 segundos por escenario")
    print()
    print("=" * 80)
    print()
    
    # Escenarios a probar
    escenarios = [2, 4, 6, 8, 10, 12, 14]
    
    resultados = []
    
    for n_clientes in escenarios:
        resultado = test_escenario(n_clientes, time_limit=120)
        resultados.append(resultado)
        
        # Pausa breve entre escenarios
        time.sleep(2)
    
    # Resumen final
    print()
    print("=" * 80)
    print("RESUMEN DE RESULTADOS")
    print("=" * 80)
    print()
    print(f"{'Clientes':<10} {'Status':<25} {'Tiempo':<10} {'Objetivo':<15} {'Gap':<10}")
    print("-" * 80)
    
    for r in resultados:
        status_str = r['status']
        tiempo_str = f"{r['tiempo_solve']:.1f}s" if 'tiempo_solve' in r else "N/A"
        objetivo_str = f"${r['objetivo']:,.0f}" if r['objetivo'] else "N/A"
        gap_str = f"{r['gap']:.1f}%" if r['gap'] is not None else "N/A"
        
        print(f"{r['n_clientes']:<10} {status_str:<25} {tiempo_str:<10} {objetivo_str:<15} {gap_str:<10}")
    
    print()
    print("-" * 80)
    
    # Identificar umbral de factibilidad
    solvables = [r for r in resultados if r.get('solvable', False)]
    if solvables:
        max_solvable = max(r['n_clientes'] for r in solvables)
        print(f"\n✓ Maximo numero de clientes resuelto: {max_solvable}")
        print(f"  → Usar este escenario para generar outputs oficiales del Caso 2")
    else:
        print(f"\n❌ Ningun escenario fue factible")
        print(f"  → Revisar restricciones del modelo")
    
    print()
    
    # Guardar resultados en archivo
    output_file = Path(__file__).parent / 'test_escalabilidad_resultados.txt'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("RESULTADOS TEST DE ESCALABILIDAD - CASO 2\n")
        f.write("=" * 80 + "\n")
        f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("\n")
        
        for r in resultados:
            f.write(f"\nEscenario: {r['n_clientes']} clientes\n")
            f.write(f"  Status: {r['status']}\n")
            if 'tiempo_solve' in r:
                f.write(f"  Tiempo resolución: {r['tiempo_solve']:.2f}s\n")
            if r['objetivo']:
                f.write(f"  Objetivo: ${r['objetivo']:,.0f}\n")
            if r['gap'] is not None:
                f.write(f"  Gap: {r['gap']:.2f}%\n")
            if 'variables' in r:
                f.write(f"  Variables: {r['variables']}\n")
                f.write(f"  Restricciones: {r['restricciones']}\n")
    
    print(f"Resultados guardados en: {output_file}")
    print()


if __name__ == '__main__':
    main()
