"""
Test mini-instancia para verificar factibilidad del Caso 2
Prueba solo con V005 (el más restrictivo) y los clientes problemáticos
"""
import sys
from pathlib import Path
import pyomo.environ as pyo
from pyomo.opt import SolverFactory

sys.path.insert(0, str(Path(__file__).parent / 'src'))
from datos_caso2 import cargar_datos_caso2
from modelo_caso2 import build_model_caso2

# Cargar datos completos
DATA_CASO2 = Path(__file__).parent.parent / 'project_c' / 'Proyecto_C_Caso2'
DATA_BASE = Path(__file__).parent.parent / 'Proyecto_Caso_Base'

print("=" * 80)
print("TEST MINI-INSTANCIA - CASO 2")
print("=" * 80)

data2 = cargar_datos_caso2(str(DATA_CASO2), str(DATA_BASE))

# Filtrar a mini-instancia
DEPOT = data2['DEPOT']
MINI_CLIENTS = ['C005', 'C014']  # Los más lejanos
MINI_VEHICLES = ['V005']  # El más restrictivo

# Filtrar solo las 3 estaciones más cercanas al cluster de clientes
# Seleccionar manualmente estaciones estratégicas
MINI_STATIONS = ['E001', 'E002', 'E003']  

print(f"\n[MINI-INSTANCIA]")
print(f"Vehículos: {MINI_VEHICLES}")
print(f"Clientes: {MINI_CLIENTS}")
print(f"Estaciones: {MINI_STATIONS}")

# Verificar autonomía vs distancias
fuel_cap = data2['fuel_cap']
fuel_eff = data2['fuel_efficiency']
dist = data2['dist']

print(f"\n[ANÁLISIS DE FACTIBILIDAD]")
print(f"Rendimiento: {fuel_eff} km/gal")

for v in MINI_VEHICLES:
    autonomia = fuel_cap[v] * fuel_eff
    print(f"\n{v} - Autonomía: {autonomia:.1f} km")
    
    for c in MINI_CLIENTS:
        dist_ida = dist[(DEPOT, c)]
        dist_vuelta = dist[(c, DEPOT)]
        dist_total = dist_ida + dist_vuelta
        
        print(f"  {DEPOT} -> {c} -> {DEPOT}: {dist_total:.1f} km", end="")
        
        if dist_total > autonomia:
            print(f" [EXCEDE por {dist_total - autonomia:.1f} km] ❌")
        else:
            print(f" [OK, margen {autonomia - dist_total:.1f} km] ✓")

# Verificar si hay estaciones intermedias útiles
print(f"\n[ESTACIONES INTERMEDIAS]")
for c in MINI_CLIENTS:
    print(f"\nRuta a {c} (dist desde CD01: {dist[(DEPOT, c)]:.1f} km):")
    
    # Ver estaciones cercanas al cliente
    for e in MINI_STATIONS:
        d_depot_station = dist[(DEPOT, e)]
        d_station_client = dist[(e, c)]
        d_client_depot = dist[(c, DEPOT)]
        ruta_con_estacion = d_depot_station + d_station_client + d_client_depot
        
        print(f"  Vía {e}: CD01({d_depot_station:.0f}km)->E({d_station_client:.0f}km)->C({d_client_depot:.0f}km) = {ruta_con_estacion:.0f} km total")

# Intentar resolver mini-instancia
print(f"\n" + "=" * 80)
print("INTENTANDO RESOLVER MINI-INSTANCIA")
print("=" * 80)

# Crear mini-data
mini_data = data2.copy()
mini_data['CLIENTS'] = MINI_CLIENTS
mini_data['STATIONS'] = MINI_STATIONS
mini_data['VEHICLES'] = MINI_VEHICLES
mini_data['NODES'] = [DEPOT] + MINI_CLIENTS + MINI_STATIONS

print(f"\nConstruyendo modelo mini...")
try:
    model_mini = build_model_caso2(mini_data, scale_fuel_cost=0.001)
    print(f"[OK] Modelo construido")
    
    print(f"\nResolviendo con HiGHS (60s límite)...")
    solver = SolverFactory('appsi_highs')
    solver.options['time_limit'] = 60
    solver.options['mip_rel_gap'] = 0.10
    
    results = solver.solve(model_mini, tee=True, load_solutions=False)
    
    print(f"\n" + "=" * 80)
    print("RESULTADO MINI-INSTANCIA")
    print("=" * 80)
    
    termination = results.solver.termination_condition
    
    if termination == pyo.TerminationCondition.optimal:
        print("\n✓ Solución ÓPTIMA encontrada")
        print("→ El problema ES FACTIBLE con estaciones intermedias")
    elif termination == pyo.TerminationCondition.feasible:
        print("\n✓ Solución FACTIBLE encontrada")
        print("→ El problema ES FACTIBLE con estaciones intermedias")
    elif termination == pyo.TerminationCondition.maxTimeLimit:
        if hasattr(results.problem, 'upper_bound') and results.problem.upper_bound < float('inf'):
            print("\n⚠️ Tiempo límite alcanzado pero hay solución factible")
            print("→ El problema ES FACTIBLE con estaciones intermedias")
        else:
            print("\n❌ Tiempo límite SIN encontrar solución factible")
            print("→ El problema probablemente es INFACTIBLE")
    elif termination == pyo.TerminationCondition.infeasible:
        print("\n❌ Problema INFACTIBLE")
        print("→ No existe solución que satisfaga todas las restricciones")
    else:
        print(f"\n❌ Terminación inesperada: {termination}")

except Exception as e:
    print(f"\n[ERROR] {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

print(f"\n" + "=" * 80)
