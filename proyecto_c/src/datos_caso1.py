"""
datos_caso1.py
--------------
Módulo para cargar y preprocesar datos del Caso 1 (Proyecto C - CVRP básico).

Este módulo lee los archivos CSV del caso base y construye las estructuras de datos
necesarias para el modelo de optimización en Pyomo:
  - Conjuntos: NODES, CLIENTS, VEHICLES
  - Parámetros: demanda, matriz de distancias, capacidades, autonomía, costos

Archivos esperados en `data/proyecto_c/caso1_base/`:
  - depots.csv: información del depósito (CD01, coordenadas)
  - clients.csv: información de clientes (C001, C002, ..., demanda, coordenadas)
  - vehicles.csv: información de vehículos (V001, V002, ..., capacidad, rango)
  - parameters_base.csv: parámetros de referencia (fuel_price, fuel_efficiency)

SUPUESTOS Y DECISIONES DE MODELADO:
  - La distancia entre nodos se calcula con la fórmula de Haversine (coordenadas lat/lon).
  - La columna 'Range' en vehicles.csv representa la autonomía máxima del vehículo en km.
  - Para compatibilidad con el enunciado del Proyecto C (que habla de FuelCap y rendimiento),
    interpretamos 'Range' como la autonomía efectiva (maxDist). Si en versiones futuras
    'Range' fuera capacidad de combustible, se calcularía maxDist = FuelCap * rendimiento.
  - Parámetros de costo: establecemos valores razonables según la profesora y el README.
    Estos pueden ajustarse fácilmente en el diccionario de parámetros.

Autor: Asistente IA (GitHub Copilot)
Fecha: Noviembre 2025
"""

import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple
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


def construir_matriz_distancias(coords: Dict[str, Tuple[float, float]]) -> Dict[Tuple[str, str], float]:
    """
    Construye una matriz de distancias (diccionario) entre todos los pares de nodos.
    
    Args:
        coords: Diccionario {node_id: (lat, lon)}
    
    Returns:
        Diccionario {(i, j): distancia_km} para todos los pares de nodos
    """
    nodos = list(coords.keys())
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
# FUNCIÓN PRINCIPAL
# ===========================

def cargar_datos_caso1(ruta_data: str) -> Dict:
    """
    Carga y preprocesa todos los datos necesarios para el modelo CVRP del Caso 1.
    
    Args:
        ruta_data: Ruta al directorio que contiene los archivos CSV del caso base
                   (por ejemplo: 'data/proyecto_c/caso1_base' o 'Proyecto_Caso_Base')
    
    Returns:
        Diccionario con las siguientes claves:
        
        CONJUNTOS:
          - 'NODES' (list): Lista de IDs de todos los nodos (depósito + clientes)
          - 'CLIENTS' (list): Lista de IDs de clientes únicamente
          - 'VEHICLES' (list): Lista de IDs de vehículos
          - 'DEPOT' (str): ID del depósito (siempre 'CD01')
        
        PARÁMETROS DE NODOS:
          - 'demanda' (dict): {client_id: demanda_kg}
          - 'coords' (dict): {node_id: (lat, lon)}
          - 'location_id' (dict): {node_id: LocationID} (para referencia)
        
        PARÁMETROS DE DISTANCIA:
          - 'dist' (dict): {(i, j): distancia_km} matriz de distancias
        
        PARÁMETROS DE VEHÍCULOS:
          - 'load_cap' (dict): {vehicle_id: capacidad_kg}
          - 'max_dist' (dict): {vehicle_id: autonomía_km}
        
        PARÁMETROS DE COSTOS:
          - 'cost_fixed' (float): Costo fijo por vehículo usado (COP)
          - 'cost_km' (float): Costo por kilómetro recorrido (COP/km)
          - 'cost_time' (float): Costo por minuto de tiempo (COP/min) - preparado para extensión
          - 'cost_fuel' (float): Costo por galón de combustible (COP/galón)
          - 'fuel_efficiency' (float): Rendimiento típico (km/galón)
        
        METADATA:
          - 'num_nodes' (int): Número total de nodos
          - 'num_clients' (int): Número de clientes
          - 'num_vehicles' (int): Número de vehículos
    """
    
    ruta_data_path = Path(ruta_data)
    
    # =============================
    # 1. VALIDAR EXISTENCIA DE ARCHIVOS
    # =============================
    archivos_requeridos = ['depots.csv', 'clients.csv', 'vehicles.csv', 'parameters_base.csv']
    for archivo in archivos_requeridos:
        archivo_path = ruta_data_path / archivo
        if not archivo_path.exists():
            raise FileNotFoundError(f"Archivo requerido no encontrado: {archivo_path}")
    
    print(f"✓ Archivos de datos encontrados en: {ruta_data_path}")
    
    # =============================
    # 2. CARGAR DEPÓSITOS
    # =============================
    depots_df = pd.read_csv(ruta_data_path / 'depots.csv')
    
    # Validar columnas requeridas
    cols_depot_req = ['DepotID', 'StandardizedID', 'LocationID', 'Latitude', 'Longitude']
    if not all(col in depots_df.columns for col in cols_depot_req):
        raise ValueError(f"El archivo depots.csv debe contener las columnas: {cols_depot_req}")
    
    # Extraer información del depósito (asumimos un único depósito)
    if len(depots_df) != 1:
        raise ValueError(f"Se esperaba exactamente 1 depósito, pero se encontraron {len(depots_df)}")
    
    depot_id = depots_df['StandardizedID'].iloc[0]  # 'CD01'
    depot_lat = depots_df['Latitude'].iloc[0]
    depot_lon = depots_df['Longitude'].iloc[0]
    depot_location_id = depots_df['LocationID'].iloc[0]
    
    print(f"✓ Depósito cargado: {depot_id} en ({depot_lat:.4f}, {depot_lon:.4f})")
    
    # =============================
    # 3. CARGAR CLIENTES
    # =============================
    clients_df = pd.read_csv(ruta_data_path / 'clients.csv')
    
    # Validar columnas requeridas
    cols_client_req = ['ClientID', 'StandardizedID', 'LocationID', 'Latitude', 'Longitude', 'Demand']
    if not all(col in clients_df.columns for col in cols_client_req):
        raise ValueError(f"El archivo clients.csv debe contener las columnas: {cols_client_req}")
    
    # Extraer información de clientes
    clients_list = clients_df['StandardizedID'].tolist()  # ['C001', 'C002', ...]
    num_clients = len(clients_list)
    
    # Construir diccionario de demandas {client_id: demanda_kg}
    demanda = dict(zip(clients_df['StandardizedID'], clients_df['Demand']))
    
    print(f"✓ Clientes cargados: {num_clients} clientes (C001 a C{num_clients:03d})")
    print(f"  Demanda total: {sum(demanda.values()):.1f} kg")
    
    # =============================
    # 4. CONSTRUIR CONJUNTOS DE NODOS
    # =============================
    NODES = [depot_id] + clients_list  # ['CD01', 'C001', 'C002', ...]
    CLIENTS = clients_list
    DEPOT = depot_id
    
    # =============================
    # 5. CONSTRUIR DICCIONARIO DE COORDENADAS
    # =============================
    coords = {depot_id: (depot_lat, depot_lon)}
    location_id = {depot_id: depot_location_id}
    
    for _, row in clients_df.iterrows():
        node_id = row['StandardizedID']
        coords[node_id] = (row['Latitude'], row['Longitude'])
        location_id[node_id] = row['LocationID']
    
    # =============================
    # 6. CONSTRUIR MATRIZ DE DISTANCIAS
    # =============================
    print("  Calculando matriz de distancias (Haversine)...")
    dist = construir_matriz_distancias(coords)
    print(f"✓ Matriz de distancias construida: {len(dist)} pares (i, j)")
    
    # =============================
    # 7. CARGAR VEHÍCULOS
    # =============================
    vehicles_df = pd.read_csv(ruta_data_path / 'vehicles.csv')
    
    # Validar columnas requeridas
    cols_vehicle_req = ['VehicleID', 'StandardizedID', 'Capacity', 'Range']
    if not all(col in vehicles_df.columns for col in cols_vehicle_req):
        raise ValueError(f"El archivo vehicles.csv debe contener las columnas: {cols_vehicle_req}")
    
    vehicles_list = vehicles_df['StandardizedID'].tolist()  # ['V001', 'V002', ...]
    num_vehicles = len(vehicles_list)
    
    # Construir diccionarios de capacidad y autonomía
    load_cap = dict(zip(vehicles_df['StandardizedID'], vehicles_df['Capacity']))
    max_dist = dict(zip(vehicles_df['StandardizedID'], vehicles_df['Range']))
    
    print(f"✓ Vehículos cargados: {num_vehicles} vehículos (V001 a V{num_vehicles:03d})")
    print(f"  Capacidad total de flota: {sum(load_cap.values()):.1f} kg")
    print(f"  Autonomía promedio: {np.mean(list(max_dist.values())):.1f} km")
    
    # VALIDACIÓN: Verificar que la capacidad total de la flota es suficiente
    demanda_total = sum(demanda.values())
    capacidad_total = sum(load_cap.values())
    if capacidad_total < demanda_total:
        print(f"⚠ ADVERTENCIA: Capacidad de flota ({capacidad_total:.1f} kg) < Demanda total ({demanda_total:.1f} kg)")
        print(f"   El problema puede no tener solución factible.")
    
    # =============================
    # 8. CARGAR PARÁMETROS DE COSTOS
    # =============================
    params_df = pd.read_csv(ruta_data_path / 'parameters_base.csv', comment='#')
    
    # Extraer parámetros relevantes
    fuel_price = params_df[params_df['Parameter'] == 'fuel_price']['Value'].iloc[0]  # COP/galón
    fuel_efficiency = params_df[params_df['Parameter'] == 'fuel_efficiency_typical']['Value'].iloc[0]  # km/galón
    
    # PARÁMETROS DE COSTOS - Ajustables según necesidades
    # Estos valores son razonables para Colombia 2025 y pueden modificarse fácilmente
    
    # Costo fijo por vehículo usado (incluye depreciación, seguros, costos administrativos)
    # Valor razonable: 200,000 - 500,000 COP por vehículo por día/ruta
    cost_fixed = 300000.0  # COP por vehículo usado
    
    # Costo por kilómetro (incluye mantenimiento, llantas, desgaste)
    # Valor razonable para tractomulas: 2,000 - 4,000 COP/km
    cost_km = 3000.0  # COP/km
    
    # Costo por tiempo (salario del conductor)
    # Valor razonable: ~30,000 COP/hora = 500 COP/minuto
    cost_time = 500.0  # COP/minuto
    
    # Costo de combustible (directamente de parámetros)
    cost_fuel = fuel_price  # COP/galón
    
    print(f"✓ Parámetros de costos cargados:")
    print(f"  - Costo fijo por vehículo: {cost_fixed:,.0f} COP")
    print(f"  - Costo por km: {cost_km:,.0f} COP/km")
    print(f"  - Costo por minuto: {cost_time:,.0f} COP/min")
    print(f"  - Precio combustible: {cost_fuel:,.0f} COP/galón")
    print(f"  - Rendimiento típico: {fuel_efficiency:.1f} km/galón")
    
    # =============================
    # 9. CONSTRUIR Y RETORNAR DICCIONARIO DE DATOS
    # =============================
    data = {
        # CONJUNTOS
        'NODES': NODES,
        'CLIENTS': CLIENTS,
        'VEHICLES': vehicles_list,
        'DEPOT': DEPOT,
        
        # PARÁMETROS DE NODOS
        'demanda': demanda,
        'coords': coords,
        'location_id': location_id,
        
        # PARÁMETROS DE DISTANCIA
        'dist': dist,
        
        # PARÁMETROS DE VEHÍCULOS
        'load_cap': load_cap,
        'max_dist': max_dist,
        
        # PARÁMETROS DE COSTOS
        'cost_fixed': cost_fixed,
        'cost_km': cost_km,
        'cost_time': cost_time,
        'cost_fuel': cost_fuel,
        'fuel_efficiency': fuel_efficiency,
        
        # METADATA
        'num_nodes': len(NODES),
        'num_clients': num_clients,
        'num_vehicles': num_vehicles,
    }
    
    print("\n" + "="*60)
    print("RESUMEN DE DATOS CARGADOS")
    print("="*60)
    print(f"Nodos totales: {data['num_nodes']} (1 depósito + {data['num_clients']} clientes)")
    print(f"Vehículos disponibles: {data['num_vehicles']}")
    print(f"Demanda total: {demanda_total:.1f} kg")
    print(f"Capacidad total de flota: {capacidad_total:.1f} kg")
    print(f"Ratio capacidad/demanda: {capacidad_total/demanda_total:.2f}")
    print("="*60 + "\n")
    
    return data


# ===========================
# EJEMPLO DE USO (para testing)
# ===========================
if __name__ == "__main__":
    # Probar carga de datos con la carpeta Proyecto_Caso_Base
    ruta_base = Path(__file__).parent.parent / "Proyecto_Caso_Base"
    
    if ruta_base.exists():
        print("Probando carga de datos del Caso Base...\n")
        datos = cargar_datos_caso1(str(ruta_base))
        
        print("\nEjemplos de datos cargados:")
        print(f"\nPrimer cliente: {datos['CLIENTS'][0]}")
        print(f"  Demanda: {datos['demanda'][datos['CLIENTS'][0]]} kg")
        print(f"  Coordenadas: {datos['coords'][datos['CLIENTS'][0]]}")
        
        print(f"\nPrimer vehículo: {datos['VEHICLES'][0]}")
        print(f"  Capacidad: {datos['load_cap'][datos['VEHICLES'][0]]} kg")
        print(f"  Autonomía: {datos['max_dist'][datos['VEHICLES'][0]]} km")
        
        depot = datos['DEPOT']
        primer_cliente = datos['CLIENTS'][0]
        print(f"\nDistancia {depot} → {primer_cliente}: {datos['dist'][(depot, primer_cliente)]:.2f} km")
    else:
        print(f"Carpeta de prueba no encontrada: {ruta_base}")
        print("Para probar este módulo, ejecuta desde la raíz del proyecto:")
        print("  python -m src.datos_caso1")
