"""
test_simple.py

Prueba el modelo simplificado (sin combustible) para verificar
que el problema base del Caso 2 es factible.
"""

import sys
import pyomo.environ as pyo
from pyomo.opt import SolverFactory

from src.datos_caso2 import cargar_datos_caso2
from src.modelo_caso2_simple import build_model_caso2_simple


def main():
    print("="*70)
    print("PRUEBA MODELO SIMPLIFICADO CASO 2 (sin combustible)")
    print("="*70)
    
    # 1. Cargar datos
    print("\n📂 Cargando datos...")
    ruta_caso2 = "../project_c/Proyecto_C_Caso2"
    ruta_base = "../Proyecto_Caso_Base"
    
    data2 = cargar_datos_caso2(ruta_caso2, ruta_base)
    
    print(f"   ✓ Clientes: {len(data2['CLIENTS'])}")
    print(f"   ✓ Vehículos: {len(data2['VEHICLES'])}")
    print(f"   ✓ Demanda total: {sum(data2['demanda'].values())} kg")
    print(f"   ✓ Capacidad total: {sum(data2['load_cap'].values())} kg")
    
    # 2. Construir modelo
    print("\n🔨 Construyendo modelo simplificado...")
    model = build_model_caso2_simple(data2)
    
    # Estadísticas
    num_vars = len([v for v in model.component_data_objects(pyo.Var)])
    num_binary = len([v for v in model.component_data_objects(pyo.Var, active=True) 
                     if v.domain == pyo.Binary])
    num_constr = len([c for c in model.component_data_objects(pyo.Constraint, active=True)])
    
    print(f"   ✓ Variables: {num_vars} ({num_binary} binarias)")
    print(f"   ✓ Restricciones: {num_constr}")
    
    # 3. Resolver
    print("\n⚙️  Resolviendo con HiGHS...")
    solver = SolverFactory('appsi_highs')
    solver.options['time_limit'] = 180
    solver.options['mip_rel_gap'] = 0.10
    
    results = solver.solve(model, tee=True, load_solutions=False)
    
    termination = results.solver.termination_condition
    
    # 4. Analizar resultado
    print("\n" + "="*70)
    print("RESULTADO")
    print("="*70)
    
    if termination == pyo.TerminationCondition.optimal:
        print("✅ Solución ÓPTIMA encontrada")
        model.solutions.load_from(results)
        
        costo_total = pyo.value(model.objetivo)
        vehiculos_usados = sum(1 for v in model.V if pyo.value(model.y[v]) > 0.5)
        
        print(f"\n📊 RESUMEN:")
        print(f"   • Costo total: ${costo_total:,.2f} COP")
        print(f"   • Vehículos usados: {vehiculos_usados}")
        
        print("\n✅ CONCLUSIÓN: El problema BASE es FACTIBLE")
        print("   → El error del modelo completo está en las restricciones de COMBUSTIBLE")
        
    elif termination == pyo.TerminationCondition.feasible:
        print("✅ Solución FACTIBLE encontrada (no óptima)")
        model.solutions.load_from(results)
        
        costo_total = pyo.value(model.objetivo)
        print(f"   Costo: ${costo_total:,.2f} COP")
        print("\n✅ CONCLUSIÓN: El problema BASE es FACTIBLE")
        
    elif termination == pyo.TerminationCondition.maxTimeLimit:
        if hasattr(results, 'problem') and results.problem.upper_bound < float('inf'):
            print("⚠️  Límite de tiempo alcanzado, pero HAY solución factible")
            model.solutions.load_from(results)
            costo_total = pyo.value(model.objetivo)
            print(f"   Costo: ${costo_total:,.2f} COP")
            print("\n✅ CONCLUSIÓN: El problema BASE es FACTIBLE")
        else:
            print("❌ Límite de tiempo SIN solución factible")
            print(f"   Dual bound: {results.problem.lower_bound:,.2f}")
            print("\n⚠️  CONCLUSIÓN: Incluso sin combustible el problema es difícil")
            print("   → Considerar reducir número de clientes para prueba")
    
    else:
        print(f"❌ Estado: {termination}")
        print("\n⚠️  CONCLUSIÓN: Problema en formulación base")


if __name__ == "__main__":
    main()
