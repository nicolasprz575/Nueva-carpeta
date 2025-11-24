# ============================================================
# run_caso3.py — FINAL COMPLETO (OPTIMIZADO Y ESTABLE)
# ============================================================

import csv
from pathlib import Path
import pyomo.environ as pyo

from datos_caso3 import cargar_datos_caso3
from modelo_caso3 import build_model_caso3


def main():

    ROOT = Path(__file__).resolve().parents[2]
    DATA_C3 = ROOT / "project_c" / "Proyecto_C_Caso3"
    BASE = ROOT / "Proyecto_Caso_Base"
    OUT = ROOT / "proyecto_c" / "results" / "caso3"
    OUT.mkdir(parents=True, exist_ok=True)

    print("\n===============================================")
    print("CASO 3 – MODELO COMPLETO")
    print("===============================================\n")

    # ----------------------------
    # 1. LOAD DATA
    # ----------------------------
    data = cargar_datos_caso3(DATA_C3, BASE)

    # ----------------------------
    # 2. BUILD MODEL
    # ----------------------------
    model = build_model_caso3(data)

    # ----------------------------
    # 3. SOLVER CONFIG (OPTIMIZADO)
    # ----------------------------
    solver = pyo.SolverFactory("appsi_highs")

    # TIEMPO Y GAP (IMPORTANTE)
    solver.options["time_limit"] = 60             # límite duro: 60 segundos
    solver.options["mip_rel_gap"] = 0.20          # GAP permisivo (20%)

    # PREVENT FREEZE / SPEED IMPROVEMENTS
    solver.options["presolve"] = "on"
    solver.options["parallel"] = "on"
    solver.options["random_seed"] = 42
    solver.options["heuristic_effort"] = "high"
    solver.options["mip_heuristic_strategy"] = "aggressive"
    solver.options["mip_detect_symmetry"] = "on"

    # LOGGING
    solver.options["output_flag"] = True
    solver.options["log_to_console"] = True

    # solve
    res = solver.solve(model, tee=True, load_solutions=False)

    if res.solver.termination_condition not in (
        pyo.TerminationCondition.optimal,
        pyo.TerminationCondition.feasible,
        pyo.TerminationCondition.maxTimeLimit,
    ):
        print("❌ No se encontró solución.")
        return

    model.solutions.load_from(res)

    DEPOT = data["DEPOT"]
    CLIENTS = data["CLIENTS"]
    VEHICLES = data["VEHICLES"]
    NODES = data["NODES"]
    dist = data["dist"]
    demanda = data["demanda"]
    toll_client = data["toll_client"]
    toll_base = data["toll_base_rate"]
    toll_rate = data["toll_rate_per_ton"]

    # ----------------------------
    # 4. RECONSTRUIR RUTAS
    # ----------------------------
    rutas = {}

    for v in VEHICLES:
        arcs_v = [(i, j) for (i, j) in model.A if pyo.value(model.x[v, i, j]) > 0.5]
        if not arcs_v:
            continue

        ruta = [DEPOT]
        actual = DEPOT

        for _ in range(300):
            siguiente = None
            for (i, j) in arcs_v:
                if i == actual:
                    siguiente = j
                    break
            if siguiente is None:
                break
            ruta.append(siguiente)
            if siguiente == DEPOT:
                break
            actual = siguiente

        rutas[v] = ruta

    # ----------------------------
    # 5. EXPORTAR verificacion_caso3.csv
    # ----------------------------
    out_csv = OUT / "verificacion_caso3.csv"

    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)

        # COLUMNAS EXACTAS DEL ENUNCIADO
        w.writerow([
            "VehicleID",
            "RouteSequence",
            "VisitedClients",
            "TotalDemand",
            "TotalDistance",
            "TotalTimeHours",
            "UsedCapacity",
            "FuelPurchased",
            "TollsPassed",
            "BaseTollCost",
            "WeightTollCost",
            "TotalCost"
        ])

        for v, ruta in rutas.items():

            visited = [n for n in ruta if n in CLIENTS]

            # Distancia
            dist_total = sum(dist[(ruta[k], ruta[k+1])] for k in range(len(ruta)-1))
            time_h = dist_total / 60.0  # suposición estándar del enunciado

            # Demanda total atendida
            demand_total = sum(demanda[c] for c in visited)

            # Capacidad usada
            used_cap = max(pyo.value(model.u[v, n]) for n in NODES)

            # Fuel purchased
            fuel_purch = sum(pyo.value(model.r[v, n]) for n in NODES)

            # Peajes
            tolls_pass = []
            base_cost = 0.0
            weight_cost = 0.0

            for (i, j) in zip(ruta[:-1], ruta[1:]):
                for p in data["TOLLS"]:
                    if toll_client.get(p, "") == j:
                        tolls_pass.append(p)
                        base_cost += toll_base[p]
                        weight_cost += toll_rate[p] * (pyo.value(model.t_weight[v, p]) / 1000.0)

            total_cost = pyo.value(model.obj)

            w.writerow([
                v,
                " → ".join(ruta),
                ",".join(visited),
                demand_total,
                dist_total,
                time_h,
                used_cap,
                fuel_purch,
                ",".join(tolls_pass) if tolls_pass else "None",
                base_cost,
                weight_cost,
                total_cost
            ])

    print(f"\n✓ Archivo generado: {out_csv}\n")
    print("===============================================")
    print("CASO 3 COMPLETADO")
    print("===============================================\n")


if __name__ == "__main__":
    main()
