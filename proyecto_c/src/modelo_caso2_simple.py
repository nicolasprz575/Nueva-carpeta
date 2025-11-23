"""
modelo_caso2_simple.py

MODELO SIMPLIFICADO para debugging del Caso 2:
- SIN restricciones de combustible
- SOLO capacidad de carga
- Usado para verificar que el problema base es factible

Este modelo es equivalente al Caso 1 pero usando los datos del Caso 2.
"""

import pyomo.environ as pyo
from typing import Dict


def build_model_caso2_simple(data2: dict) -> pyo.ConcreteModel:
    """
    Construye modelo SIMPLIFICADO sin combustible (solo capacidad).
    """
    
    DEPOT = data2['DEPOT']
    CLIENTS = data2['CLIENTS']
    NODES = [DEPOT] + CLIENTS  # SOLO depot y clientes (sin estaciones)
    VEHICLES = data2['VEHICLES']
    
    dist = data2['dist']
    demanda = data2['demanda']
    load_cap = data2['load_cap']
    C_fixed = data2['C_fixed']
    C_km = data2['C_km']
    
    model = pyo.ConcreteModel(name="CVRP_Caso2_Simple")
    
    # Conjuntos
    model.V = pyo.Set(initialize=VEHICLES)
    model.N = pyo.Set(initialize=NODES)
    model.C = pyo.Set(initialize=CLIENTS)
    
    ARCS = [(i, j) for i in NODES for j in NODES if i != j]
    model.A = pyo.Set(initialize=ARCS, dimen=2)
    
    # Parámetros
    model.dist = pyo.Param(model.A, initialize=lambda m, i, j: dist.get((i, j), 0))
    model.demanda = pyo.Param(model.C, initialize=lambda m, i: demanda[i])
    model.load_cap = pyo.Param(model.V, initialize=lambda m, v: load_cap[v])
    model.C_fixed = pyo.Param(initialize=C_fixed)
    model.C_km = pyo.Param(initialize=C_km)
    
    # Variables
    model.x = pyo.Var(model.V, model.A, domain=pyo.Binary)
    model.y = pyo.Var(model.V, domain=pyo.Binary)
    model.cargo = pyo.Var(model.V, model.N, domain=pyo.NonNegativeReals)
    
    # Objetivo
    def objetivo_rule(m):
        costo_fijo = sum(m.C_fixed * m.y[v] for v in m.V)
        costo_distancia = sum(m.C_km * m.dist[i, j] * m.x[v, i, j] 
                             for v in m.V for (i, j) in m.A)
        return costo_fijo + costo_distancia
    
    model.objetivo = pyo.Objective(rule=objetivo_rule, sense=pyo.minimize)
    
    # Restricciones
    
    # R1: Cada cliente visitado exactamente una vez
    def asignacion_clientes_rule(m, c):
        return sum(m.x[v, i, c] for v in m.V for i in m.N if (i, c) in m.A) == 1
    
    model.asignacion_clientes = pyo.Constraint(model.C, rule=asignacion_clientes_rule)
    
    # R2: Salida del depósito
    def salida_depot_rule(m, v):
        return sum(m.x[v, DEPOT, j] for j in m.N if (DEPOT, j) in m.A) == m.y[v]
    
    model.salida_depot = pyo.Constraint(model.V, rule=salida_depot_rule)
    
    # R3: Retorno al depósito
    def retorno_depot_rule(m, v):
        return sum(m.x[v, i, DEPOT] for i in m.N if (i, DEPOT) in m.A) == m.y[v]
    
    model.retorno_depot = pyo.Constraint(model.V, rule=retorno_depot_rule)
    
    # R4: Conservación de flujo
    def conservacion_flujo_rule(m, v, i):
        if i == DEPOT:
            return pyo.Constraint.Skip
        entrada = sum(m.x[v, j, i] for j in m.N if (j, i) in m.A)
        salida = sum(m.x[v, i, j] for j in m.N if (i, j) in m.A)
        return entrada == salida
    
    model.conservacion_flujo = pyo.Constraint(model.V, model.N, rule=conservacion_flujo_rule)
    
    # R5: Carga inicial = 0
    def carga_inicial_rule(m, v):
        return m.cargo[v, DEPOT] == 0
    
    model.carga_inicial = pyo.Constraint(model.V, rule=carga_inicial_rule)
    
    # R6: Balance de carga
    def balance_carga_rule(m, v, i, j):
        if i == DEPOT or j == DEPOT:
            return pyo.Constraint.Skip
        M = m.load_cap[v]
        return m.cargo[v, j] >= m.cargo[v, i] + m.demanda[j] - M * (1 - m.x[v, i, j])
    
    model.balance_carga = pyo.Constraint(model.V, model.A, rule=balance_carga_rule)
    
    # R7: Capacidad máxima
    def capacidad_carga_rule(m, v, i):
        return m.cargo[v, i] <= m.load_cap[v]
    
    model.capacidad_carga = pyo.Constraint(model.V, model.N, rule=capacidad_carga_rule)
    
    return model
