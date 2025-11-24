"""
Módulo de Carga de Datos - Caso 3: VRP con Combustible + Peajes + Restricciones Viales
Proyecto C: Optimización de Rutas de Distribución

Este módulo extiende el Caso 2 agregando:
- Peajes en arcos específicos (toll_cost)
- Restricciones viales (arcos prohibidos globalmente o por vehículo)
- Opcionalmente: escenarios para análisis de sensibilidad

Autor: Sistema de Optimización
Fecha: Noviembre 2025
"""

import pandas as pd
import numpy as np
from pathlib import Path
from math import radians, sin, cos, sqrt, atan2
from typing import Dict, List, Tuple, Set, Optional
import json


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def calcular_distancia_haversine(lat1: float, lon1: float, 
                                lat2: float, lon2: float) -> float:
    """
    Calcula la distancia de gran círculo entre dos puntos en la Tierra.
    
    Parámetros:
        lat1, lon1: Coordenadas del primer punto (grados)
        lat2, lon2: Coordenadas del segundo punto (grados)
    
    Retorna:
        Distancia en kilómetros
    """
    R = 6371.0  # Radio de la Tierra en km
    
    lat1_rad = radians(lat1)
    lon1_rad = radians(lon1)
    lat2_rad = radians(lat2)
    lon2_rad = radians(lon2)
    
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = sin(dlat/2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    return R * c


def validar_archivo(ruta: Path, nombre: str, columnas_requeridas: List[str]) -> pd.DataFrame:
    """
    Valida que un archivo CSV existe y contiene las columnas requeridas.
    
    Normaliza nombres de columnas para aceptar variantes:
    - DepotID -> DepotId
    - ClientID -> ClientId
    - EstationID -> EstationId (luego StandardizedId -> StationId)
    - FuelCost -> FuelPrice
    - StandardizedID -> StandardizedId
    
    Parámetros:
        ruta: Path al archivo CSV
        nombre: Nombre descriptivo del archivo (para mensajes de error)
        columnas_requeridas: Lista de nombres de columnas que deben existir
    
    Retorna:
        DataFrame con los datos cargados y columnas normalizadas
    
    Raises:
        FileNotFoundError: Si el archivo no existe
        ValueError: Si faltan columnas requeridas
    """
    if not ruta.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {ruta}")
    
    df = pd.read_csv(ruta)
    
    # Normalizar nombres de columnas
    # 1. Reemplazar ID por Id (DepotID -> DepotId, ClientID -> ClientId, etc.)
    df.columns = df.columns.str.replace('ID', 'Id', regex=False)
    
    # 2. Renombrar StandardizedId según el contexto
    # Para todos los archivos del Caso 3, StandardizedId contiene el ID real del nodo
    if 'StandardizedId' in df.columns:
        # Para estaciones: renombrar a StationId
        if 'FuelPrice' in df.columns or 'FuelCost' in df.columns:
            df['StationId'] = df['StandardizedId']
        # Para clientes: renombrar a ClientId (sobrescribir si existe ClientId numérico)
        elif 'Demand' in df.columns:
            df['ClientId'] = df['StandardizedId']
        # Para depósitos: renombrar a DepotId
        elif len(df) <= 2:  # Depósitos típicamente son 1-2 filas
            df['DepotId'] = df['StandardizedId']
    
    # 3. Renombrar FuelCost a FuelPrice
    if 'FuelCost' in df.columns:
        df['FuelPrice'] = df['FuelCost']
    
    # 4. Mapeo para vehículos: Capacity -> LoadCapacity, Range -> autonomía
    if 'Capacity' in df.columns and 'Type' in df.columns:
        # Es el archivo de vehículos
        df['LoadCapacity'] = df['Capacity'] * 1000  # Convertir toneladas a kg
        # FuelCapacity se calculará más tarde basado en Range y km_per_gal
    
    columnas_faltantes = set(columnas_requeridas) - set(df.columns)
    if columnas_faltantes:
        raise ValueError(
            f"Archivo {nombre} ({ruta.name}) falta columnas: {columnas_faltantes}"
        )
    
    return df


# ============================================================================
# FUNCIÓN PRINCIPAL: CARGAR DATOS DEL CASO 3
# ============================================================================

def cargar_datos_caso3(
    ruta_data: str, 
    ruta_coords: Optional[str] = None,
    escenario: str = 'base',
    clientes_subset: Optional[List[str]] = None
) -> Dict:
    """
    Carga todos los datos necesarios para el Caso 3 del Proyecto C.
    
    El Caso 3 extiende el Caso 2 con:
    - Peajes en arcos específicos
    - Restricciones viales (arcos prohibidos)
    - Costos adicionales en la función objetivo
    
    Parámetros:
        ruta_data (str): Ruta a la carpeta con datos del Caso 3
                         Ejemplo: 'data/proyecto_c/caso3_base/'
        ruta_coords (str, opcional): Ruta alternativa para coordenadas de nodos
                                     Si None, usa coordenadas de ruta_data
        escenario (str): Nombre del escenario a cargar (default: 'base')
        clientes_subset (list, opcional): Lista de IDs de clientes a incluir
                                          Si None, incluye todos los clientes
    
    Retorna:
        dict: Diccionario con todos los conjuntos y parámetros del modelo:
        
        CONJUNTOS:
            'NODES': List[str] - Todos los nodos (CD01, C***, E***)
            'CLIENTS': List[str] - Solo clientes C***
            'STATIONS': List[str] - Solo estaciones E***
            'VEHICLES': List[str] - IDs de vehículos disponibles
            'ARCS': List[Tuple[str,str]] - Todos los arcos válidos (i,j)
            'TOLL_ARCS': Set[Tuple[str,str]] - Arcos con peaje
            'FORBIDDEN_ARCS': Set[Tuple[str,str]] - Arcos prohibidos globalmente
            'RESTRICTED_ARCS': Dict[str, Set[Tuple[str,str]]] - Arcos restringidos por vehículo
        
        PARÁMETROS DE NODOS:
            'DEPOT': str - ID del depósito (CD01)
            'demanda': Dict[str, float] - Demanda de cada cliente [kg]
            'coords': Dict[str, Tuple[float,float]] - Coordenadas (lat,lon) de cada nodo
            'fuel_price': Dict[str, float] - Precio combustible en cada estación [COP/gal]
        
        PARÁMETROS DE ARCOS:
            'dist': Dict[Tuple[str,str], float] - Distancia entre nodos [km]
            'time': Dict[Tuple[str,str], float] - Tiempo de viaje [horas]
            'toll_cost': Dict[Tuple[str,str], float] - Costo de peaje [COP]
            'consumo': Dict[Tuple[str,str], float] - Consumo combustible [galones]
        
        PARÁMETROS DE VEHÍCULOS:
            'load_cap': Dict[str, float] - Capacidad de carga [kg]
            'fuel_cap': Dict[str, float] - Capacidad de combustible [galones]
            'max_dist': Dict[str, float] - Autonomía máxima [km]
        
        PARÁMETROS DE COSTOS:
            'cost_fixed': float - Costo fijo por vehículo [COP]
            'cost_km': float - Costo por kilómetro [COP/km]
            'cost_time': float - Costo por hora [COP/h]
            'km_per_gal': float - Rendimiento combustible [km/gal]
        
        METADATA:
            'num_nodes': int - Número total de nodos
            'num_clients': int - Número de clientes
            'num_stations': int - Número de estaciones
            'num_vehicles': int - Número de vehículos
            'num_toll_arcs': int - Número de arcos con peaje
            'num_forbidden_arcs': int - Número de arcos prohibidos
            'demanda_total': float - Suma de todas las demandas
            'capacidad_total': float - Suma de capacidades de todos los vehículos
            'escenario': str - Nombre del escenario cargado
    """
    
    # ========================================================================
    # 1. VALIDAR RUTAS Y PREPARAR PATHS
    # ========================================================================
    
    base_path = Path(ruta_data)
    if not base_path.exists():
        raise FileNotFoundError(f"Carpeta de datos no encontrada: {ruta_data}")
    
    # Si se proporciona ruta alternativa para coordenadas (como en Caso 2)
    coords_path = Path(ruta_coords) if ruta_coords else base_path
    
    print("="*80)
    print("CARGA DE DATOS - CASO 3: VRP CON PEAJES Y RESTRICCIONES")
    print("="*80)
    print(f"Carpeta de datos: {base_path}")
    if ruta_coords:
        print(f"Carpeta de coordenadas: {coords_path}")
    print(f"Escenario: {escenario}")
    print()
    
    # ========================================================================
    # 2. CARGAR DATOS BÁSICOS (IGUAL QUE CASO 2)
    # ========================================================================
    
    print("[1] Cargando nodos (depósito, clientes, estaciones)...")
    
    # 2.1 Depósito
    depots_file = base_path / 'depots.csv'
    df_depots = validar_archivo(depots_file, "Depósitos", ['DepotId'])
    
    if len(df_depots) == 0:
        raise ValueError("No se encontró ningún depósito en depots.csv")
    
    DEPOT = df_depots.iloc[0]['DepotId']
    print(f"  ✓ Depósito: {DEPOT}")
    
    # 2.2 Clientes
    clients_file = base_path / 'clients.csv'
    df_clients = validar_archivo(clients_file, "Clientes", 
                                 ['ClientId', 'Demand'])
    
    # Filtrar subset si se especifica
    if clientes_subset:
        df_clients = df_clients[df_clients['ClientId'].isin(clientes_subset)]
        if len(df_clients) == 0:
            raise ValueError(f"Ningún cliente del subset {clientes_subset} encontrado")
        print(f"  ✓ Usando subset de {len(df_clients)} clientes: {clientes_subset}")
    
    CLIENTS = df_clients['ClientId'].tolist()
    demanda = df_clients.set_index('ClientId')['Demand'].to_dict()
    demanda_total = sum(demanda.values())
    
    print(f"  ✓ Clientes: {len(CLIENTS)} clientes ({CLIENTS[0]} a {CLIENTS[-1]})")
    print(f"    Demanda total: {demanda_total:.1f} kg")
    
    # 2.3 Estaciones de servicio
    stations_file = base_path / 'stations.csv'
    df_stations = validar_archivo(stations_file, "Estaciones",
                                  ['StationId', 'FuelPrice'])
    
    STATIONS = df_stations['StationId'].tolist()
    fuel_price = df_stations.set_index('StationId')['FuelPrice'].to_dict()
    
    precio_min = min(fuel_price.values())
    precio_max = max(fuel_price.values())
    precio_prom = np.mean(list(fuel_price.values()))
    
    print(f"  ✓ Estaciones: {len(STATIONS)} estaciones ({STATIONS[0]} a {STATIONS[-1]})")
    print(f"    Rango de precios: {precio_min:.0f} - {precio_max:.0f} COP/gal")
    print(f"    Precio promedio: {precio_prom:.0f} COP/gal")
    
    # 2.4 Coordenadas (pueden venir de archivo separado como en Caso 2)
    print(f"  ✓ Cargando coordenadas desde: {coords_path}")
    
    # Intentar cargar coordenadas de depósito
    coords_depots_file = coords_path / 'depots.csv'
    df_coords_depots = validar_archivo(coords_depots_file, "Coordenadas Depósito",
                                      ['DepotId', 'Latitude', 'Longitude'])
    
    coords = {}
    depot_row = df_coords_depots[df_coords_depots['DepotId'] == DEPOT].iloc[0]
    coords[DEPOT] = (depot_row['Latitude'], depot_row['Longitude'])
    print(f"    {DEPOT}: ({coords[DEPOT][0]:.6f}, {coords[DEPOT][1]:.6f})")
    
    # Coordenadas de clientes
    coords_clients_file = coords_path / 'clients.csv'
    df_coords_clients = validar_archivo(coords_clients_file, "Coordenadas Clientes",
                                       ['ClientId', 'Latitude', 'Longitude'])
    
    for _, row in df_coords_clients.iterrows():
        if row['ClientId'] in CLIENTS:
            coords[row['ClientId']] = (row['Latitude'], row['Longitude'])
    
    # Coordenadas de estaciones (SIEMPRE desde base_path, ya que tienen coordenadas integradas)
    # Las estaciones en Caso 3 tienen Latitude/Longitude en el mismo archivo
    for _, row in df_stations.iterrows():
        if row['StationId'] in STATIONS:
            if 'Latitude' in df_stations.columns and 'Longitude' in df_stations.columns:
                coords[row['StationId']] = (row['Latitude'], row['Longitude'])
    
    # Si no se encontraron coordenadas en df_stations, intentar desde coords_path
    if not all(s in coords for s in STATIONS):
        coords_stations_file = coords_path / 'stations.csv'
        if coords_stations_file.exists():
            df_coords_stations = validar_archivo(coords_stations_file, "Coordenadas Estaciones",
                                                ['StationId', 'Latitude', 'Longitude'])
            
            for _, row in df_coords_stations.iterrows():
                if row['StationId'] in STATIONS and row['StationId'] not in coords:
                    coords[row['StationId']] = (row['Latitude'], row['Longitude'])
    
    # Consolidar todos los nodos
    NODES = [DEPOT] + CLIENTS + STATIONS
    print(f"  ✓ Nodos totales: {len(NODES)} ({len([DEPOT])} depósito + {len(CLIENTS)} clientes + {len(STATIONS)} estaciones)")
    
    # ========================================================================
    # 3. CARGAR VEHÍCULOS
    # ========================================================================
    
    print("\n[2] Cargando vehículos...")
    
    vehicles_file = base_path / 'vehicles.csv'
    df_vehicles = validar_archivo(vehicles_file, "Vehículos",
                                  ['VehicleId', 'LoadCapacity'])
    
    VEHICLES = df_vehicles['VehicleId'].tolist()
    load_cap = df_vehicles.set_index('VehicleId')['LoadCapacity'].to_dict()
    
    # FuelCapacity: Si existe en archivo, usarlo. Si no, calcular desde Range y km_per_gal
    if 'FuelCapacity' in df_vehicles.columns:
        fuel_cap = df_vehicles.set_index('VehicleId')['FuelCapacity'].to_dict()
    elif 'Range' in df_vehicles.columns:
        # Cargar km_per_gal primero (necesitamos adelantar esta carga)
        params_file_temp = base_path / 'parameters_national.csv'
        df_params_temp = validar_archivo(params_file_temp, "Parámetros",
                                        ['Parameter', 'Value'])
        params_temp = df_params_temp.set_index('Parameter')['Value'].to_dict()
        km_per_gal_temp = params_temp.get('km_per_gal', 3.5)  # Default 3.5 km/gal
        
        # Calcular fuel_cap = Range / km_per_gal
        fuel_cap = {}
        for idx, row in df_vehicles.iterrows():
            v_id = row['VehicleId']
            range_km = row['Range']
            fuel_cap[v_id] = range_km / km_per_gal_temp
    else:
        raise ValueError("Archivo vehicles.csv debe tener 'FuelCapacity' o 'Range'")
    
    capacidad_total = sum(load_cap.values())
    
    print(f"  ✓ Vehículos: {len(VEHICLES)} vehículos ({VEHICLES[0]} a {VEHICLES[-1]})")
    print(f"    Capacidad de carga total: {capacidad_total:.1f} kg")
    print(f"    Ratio capacidad/demanda: {capacidad_total/demanda_total:.2f}")
    print(f"    Capacidad combustible: {min(fuel_cap.values()):.1f} - {max(fuel_cap.values()):.1f} galones")
    
    # ========================================================================
    # 4. CARGAR PARÁMETROS DE COSTOS
    # ========================================================================
    
    print("\n[3] Cargando parámetros de costos...")
    
    params_file = base_path / 'parameters_national.csv'
    df_params = validar_archivo(params_file, "Parámetros",
                                ['Parameter', 'Value'])
    
    params = df_params.set_index('Parameter')['Value'].to_dict()
    
    cost_fixed = float(params.get('CostFixedVehicle', 80000))
    cost_km = float(params.get('CostPerKm', 4500))
    cost_time = float(params.get('CostPerHour', 9000))
    km_per_gal = float(params.get('KmPerGallon', 8.0))
    avg_speed = float(params.get('AverageSpeed', 60.0))  # km/h
    
    print(f"  ✓ Costo fijo por vehículo: {cost_fixed:,.0f} COP")
    print(f"  ✓ Costo por km: {cost_km:,.0f} COP/km")
    print(f"  ✓ Costo por hora: {cost_time:,.0f} COP/h")
    print(f"  ✓ Rendimiento combustible: {km_per_gal:.1f} km/gal")
    print(f"  ✓ Velocidad promedio: {avg_speed:.1f} km/h")
    
    # ========================================================================
    # 5. CALCULAR DISTANCIAS Y TIEMPOS (MATRIZ COMPLETA)
    # ========================================================================
    
    print("\n[4] Calculando matriz de distancias (Haversine)...")
    
    dist = {}
    time = {}
    consumo = {}
    
    for i in NODES:
        for j in NODES:
            if i != j:
                lat1, lon1 = coords[i]
                lat2, lon2 = coords[j]
                d = calcular_distancia_haversine(lat1, lon1, lat2, lon2)
                dist[(i, j)] = d
                time[(i, j)] = d / avg_speed  # Tiempo en horas
                consumo[(i, j)] = d / km_per_gal  # Consumo en galones
    
    num_arcs = len(dist)
    dist_promedio = np.mean(list(dist.values()))
    dist_max = max(dist.values())
    
    print(f"  ✓ Matriz de distancias: {num_arcs} arcos (pares i≠j)")
    print(f"    Distancia promedio: {dist_promedio:.1f} km")
    print(f"    Distancia máxima: {dist_max:.1f} km")
    
    # Calcular autonomía máxima por vehículo
    max_dist = {v: fuel_cap[v] * km_per_gal for v in VEHICLES}
    autonomia_prom = np.mean(list(max_dist.values()))
    
    print(f"  ✓ Autonomía promedio de vehículos: {autonomia_prom:.1f} km")
    
    # ========================================================================
    # 6. CARGAR PEAJES (NUEVO EN CASO 3)
    # ========================================================================
    
    print("\n[5] Cargando información de peajes...")
    
    tolls_file = base_path / 'tolls.csv'
    
    TOLL_ARCS = set()
    toll_cost = {}
    
    if tolls_file.exists():
        df_tolls = pd.read_csv(tolls_file)
        
        # Validar columnas requeridas
        required_cols = ['OriginNodeId', 'DestinationNodeId', 'TollCost']
        if not all(col in df_tolls.columns for col in required_cols):
            print(f"  ⚠ Archivo tolls.csv falta columnas requeridas, se asume sin peajes")
        else:
            for _, row in df_tolls.iterrows():
                origin = row['OriginNodeId']
                dest = row['DestinationNodeId']
                cost = float(row['TollCost'])
                
                # Validar que los nodos existen
                if origin in NODES and dest in NODES:
                    TOLL_ARCS.add((origin, dest))
                    toll_cost[(origin, dest)] = cost
                    
                    # Si es bidireccional (columna opcional)
                    if 'IsBidirectional' in df_tolls.columns:
                        if row['IsBidirectional']:
                            TOLL_ARCS.add((dest, origin))
                            toll_cost[(dest, origin)] = cost
            
            if len(TOLL_ARCS) > 0:
                costo_min_peaje = min(toll_cost.values())
                costo_max_peaje = max(toll_cost.values())
                costo_prom_peaje = np.mean(list(toll_cost.values()))
                
                print(f"  ✓ Arcos con peaje: {len(TOLL_ARCS)} arcos")
                print(f"    Costo peaje: {costo_min_peaje:,.0f} - {costo_max_peaje:,.0f} COP")
                print(f"    Promedio: {costo_prom_peaje:,.0f} COP/paso")
            else:
                print(f"  ⚠ Archivo tolls.csv existe pero no contiene arcos válidos")
    else:
        print(f"  ⚠ Archivo tolls.csv no encontrado, se asume sin peajes")
    
    # ========================================================================
    # 7. CARGAR RESTRICCIONES VIALES (NUEVO EN CASO 3)
    # ========================================================================
    
    print("\n[6] Cargando restricciones viales...")
    
    restrictions_file = base_path / 'restrictions.csv'
    
    FORBIDDEN_ARCS = set()
    RESTRICTED_ARCS = {v: set() for v in VEHICLES}  # Restricciones por vehículo
    
    if restrictions_file.exists():
        df_restrictions = pd.read_csv(restrictions_file)
        
        required_cols = ['RestrictionType', 'VehicleId', 'OriginNodeId', 'DestinationNodeId']
        if not all(col in df_restrictions.columns for col in required_cols):
            print(f"  ⚠ Archivo restrictions.csv falta columnas, se asume sin restricciones")
        else:
            for _, row in df_restrictions.iterrows():
                rtype = row['RestrictionType'].upper()
                vehicle = row['VehicleId']
                origin = row['OriginNodeId']
                dest = row['DestinationNodeId']
                
                # Validar que los nodos existen
                if origin not in NODES or dest not in NODES:
                    continue
                
                arc = (origin, dest)
                
                if rtype == 'FORBIDDEN' and vehicle == 'ALL':
                    # Prohibido para todos los vehículos
                    FORBIDDEN_ARCS.add(arc)
                elif rtype == 'RESTRICTED' and vehicle in VEHICLES:
                    # Prohibido solo para un vehículo específico
                    RESTRICTED_ARCS[vehicle].add(arc)
            
            num_restricted_total = sum(len(arcs) for arcs in RESTRICTED_ARCS.values())
            
            if len(FORBIDDEN_ARCS) > 0:
                print(f"  ✓ Arcos prohibidos (globales): {len(FORBIDDEN_ARCS)} arcos")
            
            if num_restricted_total > 0:
                print(f"  ✓ Arcos restringidos (por vehículo): {num_restricted_total} restricciones")
                for v in VEHICLES:
                    if len(RESTRICTED_ARCS[v]) > 0:
                        print(f"    - {v}: {len(RESTRICTED_ARCS[v])} arcos prohibidos")
            
            if len(FORBIDDEN_ARCS) == 0 and num_restricted_total == 0:
                print(f"  ⚠ Archivo restrictions.csv existe pero no contiene restricciones válidas")
    else:
        print(f"  ⚠ Archivo restrictions.csv no encontrado, se asume sin restricciones")
    
    # ========================================================================
    # 8. CONSTRUIR CONJUNTO DE ARCOS VÁLIDOS
    # ========================================================================
    
    print("\n[7] Construyendo conjunto de arcos válidos...")
    
    # Inicialmente, todos los arcos i≠j son candidatos
    ARCS = [(i, j) for i in NODES for j in NODES if i != j]
    
    # Filtrar arcos prohibidos globalmente
    ARCS = [(i, j) for (i, j) in ARCS if (i, j) not in FORBIDDEN_ARCS]
    
    print(f"  ✓ Arcos válidos (después de filtrar prohibidos): {len(ARCS)} arcos")
    print(f"    Arcos eliminados (prohibidos): {num_arcs - len(ARCS)}")
    
    # ========================================================================
    # 9. CARGAR ESCENARIOS (OPCIONAL)
    # ========================================================================
    
    print("\n[8] Verificando configuración de escenarios...")
    
    scenarios_file = base_path / 'scenarios.json'
    scenario_config = {}
    
    if scenarios_file.exists():
        try:
            with open(scenarios_file, 'r', encoding='utf-8') as f:
                scenarios_data = json.load(f)
            
            if escenario in scenarios_data:
                scenario_config = scenarios_data[escenario]
                print(f"  ✓ Escenario '{escenario}' cargado:")
                print(f"    Descripción: {scenario_config.get('description', 'N/A')}")
                
                # Aplicar modificadores del escenario
                if 'toll_multiplier' in scenario_config:
                    mult = scenario_config['toll_multiplier']
                    if mult != 1.0:
                        toll_cost = {arc: cost * mult for arc, cost in toll_cost.items()}
                        print(f"    Multiplicador de peajes: {mult}x")
                
                if 'additional_forbidden_arcs' in scenario_config:
                    extra_forbidden = scenario_config['additional_forbidden_arcs']
                    for arc_list in extra_forbidden:
                        if len(arc_list) == 2:
                            arc = tuple(arc_list)
                            FORBIDDEN_ARCS.add(arc)
                            # Remover de ARCS si existe
                            if arc in ARCS:
                                ARCS.remove(arc)
                    if len(extra_forbidden) > 0:
                        print(f"    Arcos prohibidos adicionales: {len(extra_forbidden)}")
            else:
                print(f"  ⚠ Escenario '{escenario}' no encontrado en scenarios.json")
                print(f"    Escenarios disponibles: {list(scenarios_data.keys())}")
        except Exception as e:
            print(f"  ⚠ Error al cargar scenarios.json: {e}")
    else:
        print(f"  ⚠ Archivo scenarios.json no encontrado, usando configuración base")
    
    # ========================================================================
    # 10. CONSTRUIR DICCIONARIO DE DATOS FINAL
    # ========================================================================
    
    print("\n[9] Consolidando datos...")
    
    datos = {
        # ========== CONJUNTOS ==========
        'NODES': NODES,
        'CLIENTS': CLIENTS,
        'STATIONS': STATIONS,
        'VEHICLES': VEHICLES,
        'ARCS': ARCS,
        'TOLL_ARCS': TOLL_ARCS,
        'FORBIDDEN_ARCS': FORBIDDEN_ARCS,
        'RESTRICTED_ARCS': RESTRICTED_ARCS,
        
        # ========== PARÁMETROS DE NODOS ==========
        'DEPOT': DEPOT,
        'demanda': demanda,
        'coords': coords,
        'fuel_price': fuel_price,
        
        # ========== PARÁMETROS DE ARCOS ==========
        'dist': dist,
        'time': time,
        'toll_cost': toll_cost,  # Diccionario puede estar vacío si no hay peajes
        'consumo': consumo,
        
        # ========== PARÁMETROS DE VEHÍCULOS ==========
        'load_cap': load_cap,
        'fuel_cap': fuel_cap,
        'max_dist': max_dist,
        
        # ========== PARÁMETROS DE COSTOS ==========
        'cost_fixed': cost_fixed,
        'cost_km': cost_km,
        'cost_time': cost_time,
        'km_per_gal': km_per_gal,
        
        # ========== METADATA ==========
        'num_nodes': len(NODES),
        'num_clients': len(CLIENTS),
        'num_stations': len(STATIONS),
        'num_vehicles': len(VEHICLES),
        'num_toll_arcs': len(TOLL_ARCS),
        'num_forbidden_arcs': len(FORBIDDEN_ARCS),
        'demanda_total': demanda_total,
        'capacidad_total': capacidad_total,
        'escenario': escenario,
        'scenario_config': scenario_config
    }
    
    # ========================================================================
    # 11. RESUMEN FINAL
    # ========================================================================
    
    print()
    print("="*80)
    print("RESUMEN DE DATOS CARGADOS (CASO 3)")
    print("="*80)
    print(f"Nodos totales: {datos['num_nodes']} ({len([DEPOT])} depósito + {datos['num_clients']} clientes + {datos['num_stations']} estaciones)")
    print(f"Vehículos disponibles: {datos['num_vehicles']}")
    print(f"Demanda total: {datos['demanda_total']:.1f} kg")
    print(f"Capacidad total de flota: {datos['capacidad_total']:.1f} kg")
    print(f"Ratio capacidad/demanda: {datos['capacidad_total']/datos['demanda_total']:.2f}")
    print(f"Arcos válidos: {len(ARCS)}")
    print(f"Arcos con peaje: {datos['num_toll_arcs']}")
    print(f"Arcos prohibidos: {datos['num_forbidden_arcs']}")
    print(f"Escenario: {escenario}")
    print("="*80)
    print()
    
    return datos


# ============================================================================
# FUNCIONES AUXILIARES ADICIONALES
# ============================================================================

def validar_consistencia_datos(datos: Dict) -> bool:
    """
    Valida la consistencia de los datos cargados.
    
    Verificaciones:
    - Todos los clientes tienen coordenadas
    - Todas las estaciones tienen precios de combustible
    - Los arcos con peaje existen en la red
    - Los arcos prohibidos existen en la red
    - La capacidad total es suficiente para la demanda
    
    Parámetros:
        datos: Diccionario retornado por cargar_datos_caso3()
    
    Retorna:
        True si todos los checks pasan, False en caso contrario
    """
    print("Validando consistencia de datos...")
    errores = []
    
    # Check 1: Coordenadas completas
    for client in datos['CLIENTS']:
        if client not in datos['coords']:
            errores.append(f"Cliente {client} no tiene coordenadas")
    
    for station in datos['STATIONS']:
        if station not in datos['coords']:
            errores.append(f"Estación {station} no tiene coordenadas")
    
    # Check 2: Precios de combustible
    for station in datos['STATIONS']:
        if station not in datos['fuel_price']:
            errores.append(f"Estación {station} no tiene precio de combustible")
    
    # Check 3: Arcos con peaje existen
    all_nodes = set(datos['NODES'])
    for arc in datos['TOLL_ARCS']:
        i, j = arc
        if i not in all_nodes or j not in all_nodes:
            errores.append(f"Arco con peaje {arc} contiene nodos inexistentes")
    
    # Check 4: Arcos prohibidos existen
    for arc in datos['FORBIDDEN_ARCS']:
        i, j = arc
        if i not in all_nodes or j not in all_nodes:
            errores.append(f"Arco prohibido {arc} contiene nodos inexistentes")
    
    # Check 5: Capacidad vs demanda
    if datos['capacidad_total'] < datos['demanda_total']:
        errores.append(
            f"Capacidad total ({datos['capacidad_total']:.1f} kg) "
            f"insuficiente para demanda total ({datos['demanda_total']:.1f} kg)"
        )
    
    # Reportar resultados
    if errores:
        print(f"✗ Se encontraron {len(errores)} errores:")
        for error in errores:
            print(f"  - {error}")
        return False
    else:
        print("✓ Todos los checks de consistencia pasaron")
        return True


def imprimir_resumen_detallado(datos: Dict):
    """
    Imprime un resumen detallado de los datos cargados.
    
    Útil para debugging y verificación de datos.
    
    Parámetros:
        datos: Diccionario retornado por cargar_datos_caso3()
    """
    print()
    print("="*80)
    print("RESUMEN DETALLADO DE DATOS - CASO 3")
    print("="*80)
    
    # Nodos
    print("\n[NODOS]")
    print(f"  Depósito: {datos['DEPOT']}")
    print(f"  Clientes ({len(datos['CLIENTS'])}): {', '.join(datos['CLIENTS'][:5])}...")
    print(f"  Estaciones ({len(datos['STATIONS'])}): {', '.join(datos['STATIONS'][:5])}...")
    
    # Vehículos
    print("\n[VEHÍCULOS]")
    for v in datos['VEHICLES']:
        print(f"  {v}: Carga={datos['load_cap'][v]}kg, Combustible={datos['fuel_cap'][v]}gal, Autonomía={datos['max_dist'][v]:.1f}km")
    
    # Demandas
    print("\n[DEMANDAS]")
    for c in sorted(datos['demanda'].items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"  {c[0]}: {c[1]:.1f} kg")
    print(f"  ... Total: {datos['demanda_total']:.1f} kg")
    
    # Peajes
    print("\n[PEAJES]")
    if len(datos['TOLL_ARCS']) > 0:
        print(f"  Total arcos con peaje: {len(datos['TOLL_ARCS'])}")
        for arc in list(datos['TOLL_ARCS'])[:5]:
            print(f"  {arc[0]} → {arc[1]}: {datos['toll_cost'][arc]:,.0f} COP")
        if len(datos['TOLL_ARCS']) > 5:
            print(f"  ... y {len(datos['TOLL_ARCS'])-5} más")
    else:
        print("  Sin peajes")
    
    # Restricciones
    print("\n[RESTRICCIONES]")
    if len(datos['FORBIDDEN_ARCS']) > 0:
        print(f"  Arcos prohibidos (globales): {len(datos['FORBIDDEN_ARCS'])}")
        for arc in list(datos['FORBIDDEN_ARCS'])[:3]:
            print(f"  {arc[0]} → {arc[1]}: PROHIBIDO")
    
    num_restricted = sum(len(arcs) for arcs in datos['RESTRICTED_ARCS'].values())
    if num_restricted > 0:
        print(f"  Arcos restringidos (por vehículo): {num_restricted}")
        for v in datos['VEHICLES']:
            if len(datos['RESTRICTED_ARCS'][v]) > 0:
                print(f"  {v}: {len(datos['RESTRICTED_ARCS'][v])} arcos prohibidos")
    
    if len(datos['FORBIDDEN_ARCS']) == 0 and num_restricted == 0:
        print("  Sin restricciones")
    
    # Costos
    print("\n[PARÁMETROS DE COSTOS]")
    print(f"  Costo fijo por vehículo: {datos['cost_fixed']:,.0f} COP")
    print(f"  Costo por km: {datos['cost_km']:,.0f} COP/km")
    print(f"  Costo por hora: {datos['cost_time']:,.0f} COP/h")
    print(f"  Rendimiento combustible: {datos['km_per_gal']:.1f} km/gal")
    
    print("\n" + "="*80)


# ============================================================================
# EJECUCIÓN DE PRUEBA (SI SE EJECUTA DIRECTAMENTE)
# ============================================================================

if __name__ == "__main__":
    """
    Script de prueba para validar la carga de datos del Caso 3.
    """
    import sys
    
    # Ajustar rutas según estructura del proyecto
    RUTA_CASO3 = "Proyecto_C_Caso3"
    RUTA_COORDS = "Proyecto_Caso_Base"  # Coordenadas del caso base
    
    try:
        # Cargar datos
        datos = cargar_datos_caso3(
            ruta_data=RUTA_CASO3,
            ruta_coords=RUTA_COORDS,
            escenario='base'
        )
        
        # Validar consistencia
        print()
        if validar_consistencia_datos(datos):
            print("\n✓ Datos cargados correctamente y validados")
        else:
            print("\n✗ Se encontraron problemas en los datos")
            sys.exit(1)
        
        # Resumen detallado
        imprimir_resumen_detallado(datos)
        
    except Exception as e:
        print(f"\n✗ ERROR al cargar datos: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
