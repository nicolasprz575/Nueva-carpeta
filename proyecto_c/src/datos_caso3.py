# ============================================================
# datos_caso3.py — Loader COMPLETO y FINAL para Caso 3
# Compatible 100% con el modelo_caso3.py que te entregué
# ============================================================

from pathlib import Path
import pandas as pd
import numpy as np

# ---------------------------------------------
# Haversine
# ---------------------------------------------
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1 = np.radians(lat1)
    phi2 = np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)
    a = np.sin(dphi/2)**2 + np.cos(phi1)*np.cos(phi2)*np.sin(dlambda/2)**2
    return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))


# ---------------------------------------------
# Cargar datos del Caso 3
# ---------------------------------------------
def cargar_datos_caso3(ruta_caso3: Path, ruta_caso_base: Path):

    ruta_caso3 = Path(ruta_caso3)
    ruta_caso_base = Path(ruta_caso_base)

    # ---------------------------------------------------------
    # 1. DEPOT
    # ---------------------------------------------------------
    df_dep = pd.read_csv(ruta_caso3 / "depots.csv")
    depot_id = df_dep.iloc[0]["StandardizedID"]
    depot_lat = float(df_dep.iloc[0]["Latitude"])
    depot_lon = float(df_dep.iloc[0]["Longitude"])

    # ---------------------------------------------------------
    # 2. CLIENTS (join con Caso Base para coords)
    # ---------------------------------------------------------
    df_c3 = pd.read_csv(ruta_caso3 / "clients.csv")
    df_base = pd.read_csv(ruta_caso_base / "clients.csv")

    df_clients = pd.merge(
        df_c3,
        df_base[["LocationID", "Latitude", "Longitude"]],
        on="LocationID",
        how="left"
    )

    CLIENTS = list(df_clients["StandardizedID"])

    demanda = {row["StandardizedID"]: float(row["Demand"])
               for _, row in df_clients.iterrows()}

    max_weight = {
        row["StandardizedID"]: (
            float(row["MaxWeight"]) if not pd.isna(row["MaxWeight"]) else float("inf")
        )
        for _, row in df_clients.iterrows()
    }

    coords_clients = {
        row["StandardizedID"]: (float(row["Latitude"]), float(row["Longitude"]))
        for _, row in df_clients.iterrows()
    }

    # mapa ClientID → StandardizedID para peajes
    map_clientid_std = {
        int(row["ClientID"]): row["StandardizedID"]
        for _, row in df_c3.iterrows()
    }

    # ---------------------------------------------------------
    # 3. STATIONS
    # ---------------------------------------------------------
    df_st = pd.read_csv(ruta_caso3 / "stations.csv")

    STATIONS = list(df_st["StandardizedID"])

    fuel_price = {
        row["StandardizedID"]: float(row["FuelCost"])
        for _, row in df_st.iterrows()
    }

    coords_stations = {
        row["StandardizedID"]: (float(row["Latitude"]), float(row["Longitude"]))
        for _, row in df_st.iterrows()
    }

    fuel_price_depot = float(np.mean(list(fuel_price.values())))

    # ---------------------------------------------------------
    # 4. VEHICLES
    # ---------------------------------------------------------
    df_veh = pd.read_csv(ruta_caso3 / "vehicles.csv")

    VEHICLES = list(df_veh["StandardizedID"])

    load_cap = {row["StandardizedID"]: float(row["Capacity"])
                for _, row in df_veh.iterrows()}

    vehicle_range = {row["StandardizedID"]: float(row["Range"])
                     for _, row in df_veh.iterrows()}

    # combustible
    df_params = pd.read_csv(ruta_caso3 / "parameters_national.csv")

    def get_param(name, default):
        row = df_params[df_params["Parameter"] == name]
        if len(row) == 0:
            return default
        return float(row.iloc[0]["Value"])

    fuel_eff = get_param("fuel_efficiency_full_min", 8.0)
    C_fixed = get_param("C_fixed", 80000)
    C_km = get_param("C_dist", 4500)
    C_time = get_param("C_time", 9000)

    fuel_cap = {
        v: (vehicle_range[v] / fuel_eff)
        for v in VEHICLES
    }

    # ---------------------------------------------------------
    # 5. TOLLS
    # ---------------------------------------------------------
    df_tolls = pd.read_csv(ruta_caso3 / "tolls.csv")

    TOLLS = list(df_tolls["StandardizedID"])

    toll_base_rate = {
        row["StandardizedID"]: float(row["BaseRate"])
        for _, row in df_tolls.iterrows()
    }

    toll_rate_per_ton = {
        row["StandardizedID"]: float(row["RatePerTon"])
        for _, row in df_tolls.iterrows()
    }

    toll_client = {}
    for _, row in df_tolls.iterrows():
        p = row["StandardizedID"]
        cid = row["ClientID"]
        if not pd.isna(cid) and int(cid) in map_clientid_std:
            toll_client[p] = map_clientid_std[int(cid)]
        else:
            toll_client[p] = ""

    # ---------------------------------------------------------
    # 6. COORDENADAS + DISTANCIAS
    # ---------------------------------------------------------
    coords = {depot_id: (depot_lat, depot_lon)}
    coords.update(coords_clients)
    coords.update(coords_stations)

    NODES = [depot_id] + CLIENTS + STATIONS

    dist = {}
    for i in NODES:
        for j in NODES:
            if i == j:
                dist[(i, j)] = 0.0
            else:
                lat1, lon1 = coords[i]
                lat2, lon2 = coords[j]
                dist[(i, j)] = haversine(lat1, lon1, lat2, lon2)

    # ---------------------------------------------------------
    # RETORNO FINAL
    # ---------------------------------------------------------
    return {
        "DEPOT": depot_id,
        "CLIENTS": CLIENTS,
        "STATIONS": STATIONS,
        "VEHICLES": VEHICLES,
        "NODES": NODES,

        "coords": coords,
        "dist": dist,

        "demanda": demanda,
        "load_cap": load_cap,
        "fuel_cap": fuel_cap,
        "fuel_efficiency": fuel_eff,

        "fuel_price": fuel_price,
        "fuel_price_depot": fuel_price_depot,

        "C_fixed": C_fixed,
        "C_km": C_km,
        "C_time": C_time,

        "max_weight": max_weight,

        "TOLLS": TOLLS,
        "toll_base_rate": toll_base_rate,
        "toll_rate_per_ton": toll_rate_per_ton,
        "toll_client": toll_client,
    }
