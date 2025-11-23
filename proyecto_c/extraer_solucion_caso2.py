"""
Script simplificado para extraer y visualizar la solución del Caso 2
Resuelve el modelo y extrae rutas correctamente
"""

import sys
from pathlib import Path
import pyomo.environ as pyo
import csv
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).parent / 'src'))
from datos_caso2 import cargar_datos_caso2
from modelo_caso2 import build_model_caso2

# Configuración
PROJECT_ROOT = Path(__file__).parent
DATA_CASO2 = PROJECT_ROOT.parent / 'project_c' / 'Proyecto_C_Caso2'
DATA_BASE = PROJECT_ROOT.parent / 'Proyecto_Caso_Base'
RESULTS_DIR = PROJECT_ROOT / 'results' / 'caso2'

# Clientes para el escenario oficial
CLIENTES_OFICIALES = ['C005', 'C014']

print("="*80)
print("EXTRACCIÓN DE SOLUCIÓN - CASO 2")
print("="*80)
print()

# 1. Cargar datos
print("[1] Cargando datos...")
data_full = cargar_datos_caso2(str(DATA_CASO2), str(DATA_BASE))

# 2. Preparar subset
DEPOT = data_full['DEPOT']
STATIONS = data_full['STATIONS']
VEHICLES = data_full['VEHICLES']
NODES_SUBSET = [DEPOT] + CLIENTES_OFICIALES + STATIONS

data_subset = {
    'DEPOT': DEPOT,
    'CLIENTS': CLIENTES_OFICIALES,
    'STATIONS': STATIONS,
    'NODES': NODES_SUBSET,
    'VEHICLES': VEHICLES,
    'demanda': {k: v for k, v in data_full['demanda'].items() if k in CLIENTES_OFICIALES},
    'load_cap': data_full['load_cap'],
    'fuel_cap': data_full['fuel_cap'],
    'fuel_efficiency': data_full['fuel_efficiency'],
    'fuel_price': data_full['fuel_price'],
    'fuel_price_depot': data_full['fuel_price_depot'],
    'dist': {(i, j): data_full['dist'][(i, j)] for i in NODES_SUBSET for j in NODES_SUBSET if i != j},
    'C_fixed': data_full['C_fixed'],
    'C_km': data_full['C_km'],
    'C_time': data_full['C_time'],
    'coords': data_full['coords']
}

print(f"  Clientes: {CLIENTES_OFICIALES}")
print(f"  Estaciones: {len(STATIONS)}")
print(f"  Vehículos: {len(VEHICLES)}")
print()

# 3. Construir y resolver modelo
print("[2] Construyendo modelo...")
model = build_model_caso2(data_subset)
print(f"  Variables: {model.nvariables()}")
print(f"  Restricciones: {model.nconstraints()}")
print()

print("[3] Resolviendo modelo (60 segundos)...")
solver = pyo.SolverFactory('appsi_highs')
solver.options['mip_rel_gap'] = 0.10
solver.options['time_limit'] = 60
solver.options['output_flag'] = True

results = solver.solve(model, tee=True)
print()

costo_total = pyo.value(model.objetivo)
print(f"✓ Solución encontrada")
print(f"  Costo: ${costo_total:,.2f} COP")
print()

# 4. Extraer rutas - método mejorado
print("[4] Extrayendo rutas...")

# Debug: Verificar variables x activas
print("  Variables x activas (arcos con flujo):")
arcos_activos = []
for v in VEHICLES:
    for i in NODES_SUBSET:
        for j in NODES_SUBSET:
            if i != j:
                try:
                    val = pyo.value(model.x[v, i, j])
                    if val is not None and val > 0.5:
                        arcos_activos.append((v, i, j))
                        print(f"    {v}: {i} → {j}")
                except KeyError:
                    continue

if not arcos_activos:
    print("  ⚠ No se encontraron arcos activos")
    print("  Verificando variables y (uso de vehículos):")
    for v in VEHICLES:
        try:
            y_val = pyo.value(model.y[v])
            print(f"    {v}: y = {y_val}")
        except:
            print(f"    {v}: ERROR al acceder a y[{v}]")
    sys.exit(1)

print()

# 5. Reconstruir rutas desde arcos activos
print("[5] Reconstruyendo rutas...")
rutas_por_vehiculo = {}

for v in VEHICLES:
    arcos_v = [(i, j) for (vh, i, j) in arcos_activos if vh == v]
    
    if not arcos_v:
        continue
    
    # Construir ruta desde el depósito
    ruta = [DEPOT]
    nodo_actual = DEPOT
    visitados = set([DEPOT])
    
    while len(ruta) < 20:  # Límite de seguridad
        # Buscar siguiente nodo
        siguiente = None
        for (i, j) in arcos_v:
            if i == nodo_actual and j not in visitados:
                siguiente = j
                break
            elif i == nodo_actual and j == DEPOT:
                siguiente = DEPOT
                break
        
        if siguiente is None:
            break
        
        ruta.append(siguiente)
        if siguiente == DEPOT:
            break
        
        visitados.add(siguiente)
        nodo_actual = siguiente
    
    if len(ruta) > 2:  # Tiene ruta real (no solo DEPOT->DEPOT)
        rutas_por_vehiculo[v] = ruta
        print(f"  {v}: {' → '.join(ruta)}")

if not rutas_por_vehiculo:
    print("  ⚠ No se pudieron reconstruir rutas")
    sys.exit(1)

print()

# 6. Generar CSV
print("[6] Generando CSV...")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
csv_path = RESULTS_DIR / 'verificacion_caso2.csv'

with open(csv_path, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow([
        'VehicleId', 'DepotId', 'InitialLoad', 'InitialFuel',
        'RouteSequence', 'ClientsServed', 'DemandsSatisfied',
        'StationsVisited', 'RefuelAmounts', 'TotalDistance',
        'TotalTime', 'FuelCost', 'TotalCost'
    ])
    
    for v, ruta in rutas_por_vehiculo.items():
        # Extraer info
        clientes = [n for n in ruta if n in CLIENTES_OFICIALES]
        estaciones = [n for n in ruta if n in STATIONS]
        
        # Calcular distancia
        distancia = sum(
            data_subset['dist'][(ruta[i], ruta[i+1])]
            for i in range(len(ruta)-1)
        )
        
        # Calcular demanda
        demanda_total = sum(data_subset['demanda'].get(c, 0) for c in clientes)
        
        # Extraer combustible y recargas
        recargas = []
        for nodo in estaciones:
            try:
                recarga_val = pyo.value(model.recarga[v, nodo])
                if recarga_val and recarga_val > 0.1:
                    recargas.append(f"{nodo}:{recarga_val:.1f}gal")
            except:
                pass
        
        # Calcular costo de combustible
        costo_combustible = 0
        for nodo in estaciones:
            try:
                recarga_val = pyo.value(model.recarga[v, nodo])
                if recarga_val and recarga_val > 0.1:
                    precio = data_subset['fuel_price'][nodo]
                    costo_combustible += recarga_val * precio
            except:
                pass
        
        # Tiempo
        tiempo_h = distancia / 60.0
        
        # Costos
        costo_fijo = data_subset['C_fixed']
        costo_dist = distancia * data_subset['C_km']
        costo_tiempo = tiempo_h * data_subset['C_time']
        costo_total_veh = costo_fijo + costo_dist + costo_tiempo + costo_combustible
        
        writer.writerow([
            v,
            DEPOT,
            f"{0:.1f}",
            f"{data_subset['fuel_cap'][v]:.1f}",
            ' → '.join(ruta),
            ', '.join(clientes) if clientes else 'Ninguno',
            ', '.join(f"{data_subset['demanda'][c]:.1f}kg" for c in clientes) if clientes else 'Ninguno',
            ', '.join(estaciones) if estaciones else 'Ninguna',
            ', '.join(recargas) if recargas else 'Ninguna',
            f"{distancia:.2f}",
            f"{tiempo_h:.2f}",
            f"{costo_combustible:.2f}",
            f"{costo_total_veh:.2f}"
        ])

print(f"✓ CSV generado: {csv_path}")
print()

# 7. Generar visualización
print("[7] Generando visualización...")
png_path = RESULTS_DIR / 'rutas_caso2.png'

fig, ax = plt.subplots(figsize=(14, 10))

colores_vehiculos = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6']

# Dibujar rutas
for idx, (v, ruta) in enumerate(rutas_por_vehiculo.items()):
    color = colores_vehiculos[idx % len(colores_vehiculos)]
    
    # Coordenadas de la ruta
    ruta_coords = [data_full['coords'][nodo] for nodo in ruta]
    lats = [c[0] for c in ruta_coords]
    lons = [c[1] for c in ruta_coords]
    
    ax.plot(lons, lats, 'o-', color=color, linewidth=2.5,
            markersize=8, label=f"{v}", alpha=0.8, zorder=2)
    
    # Marcar estaciones visitadas
    estaciones_ruta = [n for n in ruta if n in STATIONS]
    for est in estaciones_ruta:
        est_coords = data_full['coords'][est]
        ax.plot(est_coords[1], est_coords[0], 'o',
               color=color, markersize=18,
               markerfacecolor='yellow', markeredgewidth=3, zorder=3)

# Dibujar nodos
# Depósito
depot_coords = data_full['coords'][DEPOT]
ax.plot(depot_coords[1], depot_coords[0], 's', color='red',
       markersize=22, label='Depósito', zorder=5, markeredgecolor='darkred',
       markeredgewidth=2)
ax.text(depot_coords[1], depot_coords[0], DEPOT,
       fontsize=11, ha='right', weight='bold', color='white', zorder=6)

# Clientes
for c in CLIENTES_OFICIALES:
    c_coords = data_full['coords'][c]
    ax.plot(c_coords[1], c_coords[0], 'o', color='blue',
           markersize=14, label='Cliente' if c == CLIENTES_OFICIALES[0] else '',
           zorder=4, markeredgecolor='darkblue', markeredgewidth=2)
    ax.text(c_coords[1], c_coords[0], c,
           fontsize=10, ha='left', weight='bold', color='white', zorder=6)

# Estaciones visitadas
estaciones_visitadas = set()
for ruta in rutas_por_vehiculo.values():
    estaciones_visitadas.update([n for n in ruta if n in STATIONS])

for e in estaciones_visitadas:
    e_coords = data_full['coords'][e]
    ax.plot(e_coords[1], e_coords[0], '^', color='green',
           markersize=12, label='Estación' if e == list(estaciones_visitadas)[0] else '',
           zorder=3, alpha=0.7, markeredgecolor='darkgreen', markeredgewidth=1.5)
    ax.text(e_coords[1], e_coords[0], e,
           fontsize=8, ha='center', style='italic', va='bottom')

ax.set_xlabel('Longitud', fontsize=13, weight='bold')
ax.set_ylabel('Latitud', fontsize=13, weight='bold')
ax.set_title('Caso 2: Rutas con Estaciones de Recarga\n(Escenario Oficial: 2 Clientes)',
            fontsize=15, weight='bold', pad=15)
ax.grid(True, alpha=0.3, linestyle='--')
ax.legend(loc='best', fontsize=11, framealpha=0.95)
ax.margins(0.15)

plt.tight_layout()
plt.savefig(png_path, dpi=300, bbox_inches='tight')
plt.close()

print(f"✓ Visualización generada: {png_path}")
print()

print("="*80)
print("EXTRACCIÓN COMPLETADA")
print("="*80)
print(f"Archivos generados:")
print(f"  - {csv_path}")
print(f"  - {png_path}")
print()
print(f"Vehículos usados: {len(rutas_por_vehiculo)}")
print(f"Costo total: ${costo_total:,.2f} COP")
print("="*80)
