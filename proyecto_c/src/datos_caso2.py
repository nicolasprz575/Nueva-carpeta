"""
datos_caso2.py
--------------
Módulo para cargar y preprocesar datos del Caso 2 (Proyecto C - CVRP con estaciones de recarga).

Este módulo extiende el Caso 1 añadiendo la infraestructura de estaciones de servicio donde
los vehículos pueden recargar combustible durante sus rutas. Lee archivos CSV y construye
las estructuras de datos necesarias para el modelo de optimización con balance de combustible.

ARCHIVOS ESPERADOS en `project_c/Proyecto_C_Caso2/`:
  - depots.csv: información del depósito (CD01, coordenadas)
  - clients.csv: información de clientes (C001-C024, demanda, coordenadas)
  - stations.csv: información de estaciones (E001-E012, coordenadas, precio combustible)
  - vehicles.csv: información de vehículos (V001-V005, capacidad, autonomía)
  - parameters_national.csv: parámetros de costo y rendimiento de combustible

DIFERENCIAS CLAVE VS. CASO 1:
  - Nuevos nodos: Estaciones de servicio (E001, E002, ..., E012)
  - Matriz de distancias extendida: incluye depot + clientes + estaciones
  - Precio de combustible variable por estación (FuelCost en stations.csv)
  - Rendimiento de combustible: fuel_efficiency_full_min (8 km/gal recomendado)
  - FuelCap se calcula como: Range / fuel_efficiency (galones)
  
CONJUNTOS Y PARÁMETROS GENERADOS:
  Conjuntos:
    - DEPOT: depósito único (CD01)
    - CLIENTS: clientes con demanda (C001-C024)
    - STATIONS: estaciones de recarga (E001-E012)
    - NODES: todos los nodos = DEPOT ∪ CLIENTS ∪ STATIONS
    - VEHICLES: flota disponible (V001-V005)
  
  Parámetros:
    - demanda[c]: demanda del cliente c en kg
    - coords[i]: coordenadas (lat, lon) del nodo i
    - dist[i,j]: distancia Haversine entre nodos i y j (km)
    - load_cap[v]: capacidad de carga del vehículo v (kg)
    - fuel_cap[v]: capacidad del tanque del vehículo v (galones)
    - fuel_efficiency: rendimiento global (km/galón, carga completa)
    - fuel_price[e]: precio del combustible en estación e (COP/galón)
    - C_fixed: costo fijo por vehículo (COP)
    - C_km: costo variable por km (COP/km)
    - C_time: costo por hora (COP/hora, opcional)

SUPUESTOS Y DECISIONES DE MODELADO:
  - Distancias: Haversine (línea recta sobre esfera)
  - Consumo de combustible: proporcional a distancia, NO al peso
  - Rendimiento: usamos fuel_efficiency_full_min = 8 km/gal (conservador, carga completa)
  - FuelCap: calculado como Range / fuel_efficiency (no viene explícito en CSV)
  - Precio en depósito: si el vehículo recarga en CD01, usamos precio promedio de estaciones
  - Las estaciones NO tienen demanda (no son clientes)
  - Las estaciones PUEDEN visitarse múltiples veces si el modelo lo decide

Autor: Asistente IA (GitHub Copilot)
Fecha: Noviembre 2025
"""

import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Any
import numpy as np


# ===========================
# FUNCIONES AUXILIARES
# ===========================

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calcula la distancia en kilómetros entre dos puntos geográficos usando la fórmula de Haversine.
    
    Args:
        lat1, lon1: Latitud y longitud del primer punto (grados)
        lat2, lon2: Latitud y longitud del segundo punto (grados)
    
    Returns:
        Distancia en kilómetros
    """
    R = 6371.0  # Radio de la Tierra en km
    
    # Convertir grados a radianes
    lat1_rad = np.radians(lat1)
    lon1_rad = np.radians(lon1)
    lat2_rad = np.radians(lat2)
    lon2_rad = np.radians(lon2)
    
    # Diferencias
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    # Fórmula de Haversine
    a = np.sin(dlat/2)**2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon/2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
    
    distance = R * c
    return distance


def construir_matriz_distancias(coords: Dict[str, Tuple[float, float]], 
                                 nodos: List[str]) -> Dict[Tuple[str, str], float]:
    """
    Construye una matriz de distancias (diccionario) entre todos los pares de nodos.
    
    Args:
        coords: Diccionario {node_id: (lat, lon)}
        nodos: Lista de IDs de nodos a incluir en la matriz
    
    Returns:
        Diccionario {(i, j): distancia_km} para todos los pares de nodos
    """
    dist = {}
    
    for i in nodos:
        for j in nodos:
            if i == j:
                dist[(i, j)] = 0.0
            else:
                lat_i, lon_i = coords[i]
                lat_j, lon_j = coords[j]
                dist[(i, j)] = haversine_distance(lat_i, lon_i, lat_j, lon_j)
    
    return dist


# ===========================
# FUNCIÓN PRINCIPAL: CARGAR DATOS CASO 2
# ===========================

def cargar_datos_caso2(ruta_data: str, ruta_caso_base: str = None) -> Dict[str, Any]:
    """
    Carga todos los datos necesarios para el Caso 2 (CVRP con estaciones de recarga).
    
    Args:
        ruta_data: Ruta absoluta o relativa a la carpeta con los archivos CSV
                   (ej. "project_c/Proyecto_C_Caso2")
        ruta_caso_base: Ruta al Caso Base para JOIN de coordenadas (opcional)
    
    Returns:
        Diccionario con las siguientes claves:
        
        CONJUNTOS:
          - 'DEPOT': str, ID del depósito (ej. 'CD01')
          - 'CLIENTS': list[str], IDs de clientes (ej. ['C001', 'C002', ...])
          - 'STATIONS': list[str], IDs de estaciones (ej. ['E001', 'E002', ...])
          - 'NODES': list[str], todos los nodos (depot + clients + stations)
          - 'VEHICLES': list[str], IDs de vehículos (ej. ['V001', 'V002', ...])
        
        PARÁMETROS TOPOLÓGICOS:
          - 'coords': dict, {node_id: (lat, lon)}
          - 'dist': dict, {(i, j): distancia_km}
          - 'demanda': dict, {client_id: demanda_kg} (solo clientes)
        
        PARÁMETROS DE VEHÍCULOS:
          - 'load_cap': dict, {vehicle_id: capacidad_kg}
          - 'fuel_cap': dict, {vehicle_id: capacidad_galones}
          - 'fuel_efficiency': float, rendimiento global (km/galón)
        
        PARÁMETROS DE COMBUSTIBLE:
          - 'fuel_price': dict, {station_id: precio_COP_por_galon}
          - 'fuel_price_depot': float, precio en depósito (promedio estaciones)
        
        PARÁMETROS DE COSTOS:
          - 'C_fixed': float, costo fijo por vehículo (COP)
          - 'C_km': float, costo variable por km (COP/km)
          - 'C_time': float, costo por hora (COP/hora)
        
        METADATOS:
          - 'num_clients': int, número de clientes
          - 'num_stations': int, número de estaciones
          - 'num_nodes': int, número total de nodos
          - 'num_vehicles': int, número de vehículos
          - 'demanda_total': float, suma de todas las demandas (kg)
          - 'capacidad_total_flota': float, suma de capacidades de carga (kg)
    
    Raises:
        FileNotFoundError: Si algún archivo CSV no se encuentra
        ValueError: Si faltan columnas requeridas o hay datos inválidos
    """
    
    ruta_base = Path(ruta_data)
    
    # ============================================================
    # PASO 0: BUSCAR CASO BASE AUTOMÁTICAMENTE SI NO SE PROPORCIONA
    # ============================================================
    
    if ruta_caso_base is None:
        # Buscar Proyecto_Caso_Base en el directorio padre
        base_dir = ruta_base.parent.parent  # Subir 2 niveles desde Proyecto_C_Caso2
        ruta_caso_base = base_dir / 'Proyecto_Caso_Base'
        if not ruta_caso_base.exists():
            raise FileNotFoundError(f"❌ ERROR: No se encuentra el Caso Base en {ruta_caso_base}")
    else:
        ruta_caso_base = Path(ruta_caso_base)
    
    # ============================================================
    # PASO 1: VALIDAR QUE LOS ARCHIVOS EXISTEN
    # ============================================================
    
    archivos_requeridos = {
        'depots': ruta_base / 'depots.csv',
        'clients': ruta_base / 'clients.csv',
        'stations': ruta_base / 'stations.csv',
        'vehicles': ruta_base / 'vehicles.csv',
        'parameters': ruta_base / 'parameters_national.csv',
        'clients_base': ruta_caso_base / 'clients.csv'  # Para JOIN
    }
    
    print(f"✓ Archivos de datos encontrados en: {ruta_base}")
    print(f"✓ Usando coordenadas del Caso Base: {ruta_caso_base}")
    
    for nombre, archivo in archivos_requeridos.items():
        if not archivo.exists():
            raise FileNotFoundError(f"❌ ERROR: No se encontró el archivo {archivo}")
    
    # ============================================================
    # PASO 2: CARGAR DEPÓSITO (CD01)
    # ============================================================
    
    df_depots = pd.read_csv(archivos_requeridos['depots'])
    
    # Validar columnas
    columnas_depot = ['StandardizedID', 'Latitude', 'Longitude']
    if not all(col in df_depots.columns for col in columnas_depot):
        raise ValueError(f"❌ ERROR: depots.csv debe tener columnas {columnas_depot}")
    
    if len(df_depots) != 1:
        raise ValueError(f"❌ ERROR: Se esperaba 1 depósito, se encontraron {len(df_depots)}")
    
    depot_id = df_depots.iloc[0]['StandardizedID']
    depot_lat = float(df_depots.iloc[0]['Latitude'])
    depot_lon = float(df_depots.iloc[0]['Longitude'])
    
    print(f"✓ Depósito cargado: {depot_id} en ({depot_lat}, {depot_lon})")
    
    # ============================================================
    # PASO 3: CARGAR CLIENTES (C001, C002, ...) CON JOIN
    # ============================================================
    
    # Cargar clientes del Caso 2 (atributos + demanda)
    df_clients_caso2 = pd.read_csv(archivos_requeridos['clients'])
    
    # Validar columnas mínimas requeridas
    columnas_client_min = ['StandardizedID', 'Demand', 'LocationID']
    if not all(col in df_clients_caso2.columns for col in columnas_client_min):
        raise ValueError(f"❌ ERROR: clients.csv debe tener columnas {columnas_client_min}")
    
    # Cargar clientes del Caso Base (con coordenadas)
    df_clients_base = pd.read_csv(archivos_requeridos['clients_base'])
    
    # Validar que el Caso Base tenga coordenadas
    if not all(col in df_clients_base.columns for col in ['LocationID', 'Latitude', 'Longitude']):
        raise ValueError(f"❌ ERROR: clients.csv del Caso Base debe tener LocationID, Latitude, Longitude")
    
    # JOIN: Caso 2 + Caso Base usando LocationID
    df_clients = pd.merge(
        df_clients_caso2[['StandardizedID', 'Demand', 'LocationID']],
        df_clients_base[['LocationID', 'Latitude', 'Longitude']],
        on='LocationID',
        how='left'
    )
    
    # Validar que todas las coordenadas se encontraron
    if df_clients[['Latitude', 'Longitude']].isna().any().any():
        faltantes = df_clients[df_clients[['Latitude', 'Longitude']].isna().any(axis=1)]
        raise ValueError(f"❌ ERROR: No se encontraron coordenadas para LocationIDs: {faltantes['LocationID'].tolist()}")
    
    # Extraer datos de clientes
    clients = []
    demanda = {}
    coords_clients = {}
    
    for _, row in df_clients.iterrows():
        client_id = row['StandardizedID']
        clients.append(client_id)
        demanda[client_id] = float(row['Demand'])
        coords_clients[client_id] = (float(row['Latitude']), float(row['Longitude']))
    
    demanda_total = sum(demanda.values())
    
    print(f"✓ Clientes cargados: {len(clients)} clientes ({clients[0]} a {clients[-1]})")
    print(f"  Demanda total: {demanda_total} kg")
    
    # ============================================================
    # PASO 4: CARGAR ESTACIONES (E001, E002, ...)
    # ============================================================
    
    df_stations = pd.read_csv(archivos_requeridos['stations'])
    
    # Validar columnas
    columnas_station = ['StandardizedID', 'Latitude', 'Longitude', 'FuelCost']
    if not all(col in df_stations.columns for col in columnas_station):
        raise ValueError(f"❌ ERROR: stations.csv debe tener columnas {columnas_station}")
    
    # Extraer datos
    stations = []
    fuel_price = {}
    coords_stations = {}
    
    for _, row in df_stations.iterrows():
        station_id = row['StandardizedID']
        stations.append(station_id)
        fuel_price[station_id] = float(row['FuelCost'])
        coords_stations[station_id] = (float(row['Latitude']), float(row['Longitude']))
    
    # Precio promedio para usar en depósito si es necesario
    fuel_price_depot = np.mean(list(fuel_price.values()))
    
    print(f"✓ Estaciones cargadas: {len(stations)} estaciones ({stations[0]} a {stations[-1]})")
    print(f"  Rango de precios: {min(fuel_price.values()):.0f} - {max(fuel_price.values()):.0f} COP/gal")
    print(f"  Precio promedio: {fuel_price_depot:.0f} COP/gal")
    
    # ============================================================
    # PASO 5: CONSTRUIR CONJUNTO DE TODOS LOS NODOS Y COORDENADAS
    # ============================================================
    
    nodes = [depot_id] + clients + stations
    
    coords = {depot_id: (depot_lat, depot_lon)}
    coords.update(coords_clients)
    coords.update(coords_stations)
    
    print(f"✓ Nodos totales: {len(nodes)} (1 depósito + {len(clients)} clientes + {len(stations)} estaciones)")
    
    # ============================================================
    # PASO 6: CONSTRUIR MATRIZ DE DISTANCIAS (HAVERSINE)
    # ============================================================
    
    print("  Calculando matriz de distancias (Haversine)...")
    dist = construir_matriz_distancias(coords, nodes)
    
    num_pares = len(nodes) ** 2
    print(f"✓ Matriz de distancias construida: {num_pares} pares (i, j)")
    
    # Estadísticas de distancias
    distancias_no_cero = [d for (i, j), d in dist.items() if i != j]
    print(f"  Distancia promedio: {np.mean(distancias_no_cero):.1f} km")
    print(f"  Distancia máxima: {max(distancias_no_cero):.1f} km")
    
    # ============================================================
    # PASO 7: CARGAR VEHÍCULOS (V001, V002, ...)
    # ============================================================
    
    df_vehicles = pd.read_csv(archivos_requeridos['vehicles'])
    
    # Validar columnas
    columnas_vehicle = ['StandardizedID', 'Capacity', 'Range']
    if not all(col in df_vehicles.columns for col in columnas_vehicle):
        raise ValueError(f"❌ ERROR: vehicles.csv debe tener columnas {columnas_vehicle}")
    
    vehicles = []
    load_cap = {}
    vehicle_range = {}  # Autonomía en km (temporal)
    
    for _, row in df_vehicles.iterrows():
        vehicle_id = row['StandardizedID']
        vehicles.append(vehicle_id)
        load_cap[vehicle_id] = float(row['Capacity'])
        vehicle_range[vehicle_id] = float(row['Range'])
    
    capacidad_total = sum(load_cap.values())
    
    print(f"✓ Vehículos cargados: {len(vehicles)} vehículos ({vehicles[0]} a {vehicles[-1]})")
    print(f"  Capacidad total de flota: {capacidad_total} kg")
    print(f"  Autonomía promedio: {np.mean(list(vehicle_range.values())):.0f} km")
    
    # ============================================================
    # PASO 8: CARGAR PARÁMETROS DE RENDIMIENTO Y COSTOS
    # ============================================================
    
    df_params = pd.read_csv(archivos_requeridos['parameters'], comment='#')
    
    # Función auxiliar para extraer parámetro
    def get_param(df: pd.DataFrame, param_name: str, default_value: float = None) -> float:
        """Extrae un parámetro del DataFrame de parámetros"""
        row = df[df['Parameter'] == param_name]
        if len(row) == 0:
            if default_value is not None:
                return default_value
            else:
                raise ValueError(f"❌ ERROR: Parámetro '{param_name}' no encontrado en parameters_national.csv")
        return float(row.iloc[0]['Value'])
    
    # Rendimiento de combustible (usamos fuel_efficiency_full_min = 8 km/gal, conservador)
    fuel_efficiency = get_param(df_params, 'fuel_efficiency_full_min', default_value=8.0)
    
    # Costos
    C_fixed = get_param(df_params, 'C_fixed', default_value=80000.0)
    C_km = get_param(df_params, 'C_dist', default_value=4500.0)
    C_time = get_param(df_params, 'C_time', default_value=9000.0)
    
    print(f"✓ Parámetros de costos cargados:")
    print(f"  - Costo fijo por vehículo: {C_fixed:,.0f} COP")
    print(f"  - Costo por km: {C_km:,.0f} COP/km")
    print(f"  - Costo por hora: {C_time:,.0f} COP/hora")
    print(f"  - Rendimiento combustible: {fuel_efficiency:.1f} km/galón (carga completa)")
    
    # ============================================================
    # PASO 9: CALCULAR CAPACIDAD DE COMBUSTIBLE (FuelCap)
    # ============================================================
    
    # FuelCap = Range / fuel_efficiency
    # Esto asume que 'Range' es la autonomía máxima con tanque lleno
    
    fuel_cap = {}
    for v in vehicles:
        fuel_cap[v] = vehicle_range[v] / fuel_efficiency
    
    print(f"✓ Capacidad de combustible calculada:")
    print(f"  - Promedio: {np.mean(list(fuel_cap.values())):.1f} galones")
    print(f"  - Rango: {min(fuel_cap.values()):.1f} - {max(fuel_cap.values()):.1f} galones")
    
    # ============================================================
    # PASO 10: CONSTRUIR DICCIONARIO DE SALIDA
    # ============================================================
    
    data2 = {
        # CONJUNTOS
        'DEPOT': depot_id,
        'CLIENTS': clients,
        'STATIONS': stations,
        'NODES': nodes,
        'VEHICLES': vehicles,
        
        # PARÁMETROS TOPOLÓGICOS
        'coords': coords,
        'dist': dist,
        'demanda': demanda,
        
        # PARÁMETROS DE VEHÍCULOS
        'load_cap': load_cap,
        'fuel_cap': fuel_cap,
        'fuel_efficiency': fuel_efficiency,
        
        # PARÁMETROS DE COMBUSTIBLE
        'fuel_price': fuel_price,
        'fuel_price_depot': fuel_price_depot,
        
        # PARÁMETROS DE COSTOS
        'C_fixed': C_fixed,
        'C_km': C_km,
        'C_time': C_time,
        
        # METADATOS
        'num_clients': len(clients),
        'num_stations': len(stations),
        'num_nodes': len(nodes),
        'num_vehicles': len(vehicles),
        'demanda_total': demanda_total,
        'capacidad_total_flota': capacidad_total,
        'ratio_capacidad_demanda': capacidad_total / demanda_total if demanda_total > 0 else 0
    }
    
    # ============================================================
    # PASO 11: VALIDACIONES FINALES
    # ============================================================
    
    print("\n" + "="*60)
    print("RESUMEN DE DATOS CARGADOS (CASO 2)")
    print("="*60)
    print(f"Nodos totales: {data2['num_nodes']} (1 depósito + {data2['num_clients']} clientes + {data2['num_stations']} estaciones)")
    print(f"Vehículos disponibles: {data2['num_vehicles']}")
    print(f"Demanda total: {data2['demanda_total']} kg")
    print(f"Capacidad total de flota: {data2['capacidad_total_flota']} kg")
    print(f"Ratio capacidad/demanda: {data2['ratio_capacidad_demanda']:.2f}")
    print(f"Estaciones disponibles: {data2['num_stations']}")
    print(f"Rango de precios combustible: {min(fuel_price.values()):.0f} - {max(fuel_price.values()):.0f} COP/gal")
    print("="*60 + "\n")
    
    # Validaciones
    if data2['ratio_capacidad_demanda'] < 1.0:
        print("⚠️  ADVERTENCIA: La capacidad total de la flota es menor que la demanda total.")
        print("   El problema podría ser infactible.")
    
    if data2['num_stations'] == 0:
        print("⚠️  ADVERTENCIA: No se encontraron estaciones de servicio.")
        print("   El Caso 2 requiere estaciones para recargas.")
    
    return data2


# ===========================
# FUNCIÓN DE PRUEBA (OPCIONAL)
# ===========================

if __name__ == "__main__":
    """
    Prueba del módulo cargando datos del Caso 2.
    Ejecutar desde la raíz del proyecto:
        python src/datos_caso2.py
    """
    from pathlib import Path
    
    # Ruta a los datos del Caso 2
    proyecto_root = Path(__file__).parent.parent.parent
    ruta_data_caso2 = proyecto_root / "project_c" / "Proyecto_C_Caso2"
    
    print("="*70)
    print("PRUEBA DEL MÓDULO datos_caso2.py")
    print("="*70 + "\n")
    
    try:
        data = cargar_datos_caso2(str(ruta_data_caso2))
        
        print("\n" + "="*70)
        print("✅ CARGA DE DATOS EXITOSA")
        print("="*70)
        
        # Mostrar algunas estadísticas adicionales
        print("\n📊 ESTADÍSTICAS ADICIONALES:\n")
        
        # Distancia promedio desde depósito a clientes
        dist_depot_clients = [data['dist'][(data['DEPOT'], c)] for c in data['CLIENTS']]
        print(f"Distancia promedio depot → clientes: {np.mean(dist_depot_clients):.1f} km")
        
        # Distancia promedio desde depósito a estaciones
        dist_depot_stations = [data['dist'][(data['DEPOT'], e)] for e in data['STATIONS']]
        print(f"Distancia promedio depot → estaciones: {np.mean(dist_depot_stations):.1f} km")
        
        # Cliente más cercano y más lejano
        closest_client = min(data['CLIENTS'], key=lambda c: data['dist'][(data['DEPOT'], c)])
        farthest_client = max(data['CLIENTS'], key=lambda c: data['dist'][(data['DEPOT'], c)])
        print(f"Cliente más cercano al depot: {closest_client} ({data['dist'][(data['DEPOT'], closest_client)]:.1f} km)")
        print(f"Cliente más lejano del depot: {farthest_client} ({data['dist'][(data['DEPOT'], farthest_client)]:.1f} km)")
        
        # Estación más barata y más cara
        cheapest_station = min(data['STATIONS'], key=lambda e: data['fuel_price'][e])
        expensive_station = max(data['STATIONS'], key=lambda e: data['fuel_price'][e])
        print(f"Estación más barata: {cheapest_station} ({data['fuel_price'][cheapest_station]:.0f} COP/gal)")
        print(f"Estación más cara: {expensive_station} ({data['fuel_price'][expensive_station]:.0f} COP/gal)")
        
        print("\n" + "="*70)
        
    except Exception as e:
        print(f"\n❌ ERROR durante la carga: {e}")
        import traceback
        traceback.print_exc()
