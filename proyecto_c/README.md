# PROYECTO C: Optimización de Rutas de Vehículos (CVRP)

## 📋 Descripción General

Este proyecto resuelve problemas de ruteo de vehículos capacitados (CVRP - Capacitated Vehicle Routing Problem) para optimizar la distribución de mercancías desde un centro de distribución hacia múltiples clientes, minimizando costos operativos.

El proyecto está dividido en **tres casos progresivos**:
- **Caso 1:** CVRP básico con restricciones de capacidad y autonomía
- **Caso 2:** Caso 1 + estaciones de recarga intermedias
- **Caso 3:** Caso 2 + consideración de peajes

## 🎯 Objetivo

Desarrollar un modelo de optimización que permita:
1. Determinar qué vehículos usar de la flota disponible
2. Asignar clientes a cada vehículo
3. Definir el orden de visita de cada ruta
4. Minimizar costos fijos (uso de vehículos) y variables (distancia recorrida)
5. Cumplir restricciones de capacidad, autonomía y atención completa

## 📁 Estructura del Proyecto

```
proyecto_c/
├── README.md                          # Este archivo
├── src/                               # Código fuente
│   ├── datos_caso1.py                # Carga y preprocesamiento de datos
│   ├── modelo_caso1.py               # Modelo de optimización Pyomo
│   └── run_caso1.py                  # Script principal de ejecución
├── results/                           # Resultados de optimización
│   └── caso1/                        # Resultados del Caso 1
│       ├── verificacion_caso1.csv    # ✅ Archivo de verificación de rutas
│       ├── rutas_caso1.png           # ✅ Visualización geográfica de rutas
│       └── resumen.txt               # Resumen de métricas
├── docs/                             # Documentación
│   └── informe_caso1.md              # ✅ Informe técnico completo del Caso 1
└── data/                             # (Vacío, apunta a ../Proyecto_Caso_Base/)
```

## 📊 Datos de Entrada

Los datos se encuentran en: `../Proyecto_Caso_Base/`

| Archivo | Descripción | Contenido |
|---------|-------------|-----------|
| `depots.csv` | Centros de distribución | 1 depósito (CD01 - Barranquilla) |
| `clients.csv` | Clientes/municipios | 24 clientes (C001-C024) con ubicación y demanda |
| `vehicles.csv` | Flota de vehículos | 8 vehículos con capacidad y autonomía variables |
| `parameters_base.csv` | Parámetros de costos | Costos fijos, por km, combustible, etc. |

**Datos del Caso 1:**
- **Depósito:** CD01 en Barranquilla (4.7434°N, -74.1535°W)
- **Clientes:** 24 municipios con demanda total de 377 kg
- **Flota:** 8 vehículos con capacidad total de 839 kg
- **Costos:** $300,000 COP fijo por vehículo + $3,000 COP/km

## 🚀 Instalación y Ejecución

### Requisitos Previos

- Python 3.9 o superior
- Virtual environment (recomendado)

### 1. Crear y Activar Virtual Environment

```powershell
# Crear virtual environment
python -m venv .venv

# Activar (Windows PowerShell)
.\.venv\Scripts\Activate.ps1
```

### 2. Instalar Dependencias

```powershell
pip install pandas numpy matplotlib pyomo highspy
```

**Paquetes instalados:**
- `pandas`: Carga y manipulación de datos CSV
- `numpy`: Cálculos numéricos y matrices
- `matplotlib`: Visualización de rutas
- `pyomo`: Framework de optimización
- `highspy`: Solver de optimización (HiGHS)

### 3. Ejecutar el Caso 1

```powershell
# Opción 1: Desde la raíz del proyecto
python proyecto_c/src/run_caso1.py

# Opción 2: Desde el directorio src/
cd proyecto_c/src
python run_caso1.py

# Opción 3: Con encoding UTF-8 explícito (recomendado en Windows)
$env:PYTHONIOENCODING='utf-8'; python proyecto_c/src/run_caso1.py
```

**Tiempo de ejecución:** ~120 segundos (límite configurado)

## 📈 Resultados del Caso 1

### Métricas Principales

| Métrica | Valor |
|---------|-------|
| **Costo total** | $1,523,781 COP |
| Costo fijo | $900,000 COP |
| Costo variable | $623,781 COP |
| **Vehículos usados** | 3 de 8 (37.5%) |
| **Distancia total** | 207.93 km |
| **Clientes atendidos** | 24 de 24 (100%) |
| **Utilización promedio de capacidad** | 98.0% |
| **Gap de optimalidad** | 57.73% |

### Rutas Optimizadas

**Vehículo V001:** CD01 → C001 → C004 → C015 → C022 → C017 → C003 → C014 → C023 → CD01  
- 8 clientes, 43.5 km, 130 kg (100% capacidad)

**Vehículo V002:** CD01 → C010 → C024 → C016 → C007 → C021 → C002 → C008 → C011 → C013 → CD01  
- 9 clientes, 103.0 km, 140 kg (100% capacidad)

**Vehículo V008:** CD01 → C019 → C020 → C012 → C009 → C005 → C018 → C006 → CD01  
- 7 clientes, 61.4 km, 107 kg (93.9% capacidad)

### Archivos Generados

1. **`results/caso1/verificacion_caso1.csv`**  
   Formato: VehicleId, DepotId, InitialLoad, RouteSequence, ClientsServed, DemandsSatisfied, TotalDistance, TotalTime, FuelCost
   
2. **`results/caso1/rutas_caso1.png`**  
   Visualización geográfica con depósito (cuadrado rojo) y rutas coloreadas por vehículo
   
3. **`results/caso1/resumen.txt`**  
   Resumen ejecutivo con métricas clave y detalle por vehículo

4. **`docs/informe_caso1.md`**  
   Informe técnico completo con metodología, resultados, análisis e interpretación

## 🔧 Metodología Técnica

### Modelo Matemático

**Tipo:** Programa Lineal Entero Mixto (MILP)  
**Variables:** 5,000 (4,800 binarias x[v,i,j], 8 binarias y[v], 192 continuas u[v,i])  
**Restricciones:** ~9,464

**Restricciones principales:**
- R1: Cada cliente visitado exactamente una vez
- R2: Flujo en el depósito (vehículos salen/regresan)
- R3: Conservación de flujo (entrada = salida)
- R4: Capacidad (carga ≤ capacidad del vehículo)
- R5: Autonomía (distancia ≤ autonomía del vehículo)
- R6: Eliminación de subtours (formulación MTZ)
- R7: Vinculación x-y (arcos solo en vehículos activos)

**Función objetivo:**
```
Minimizar: Σ(Costo_fijo × y[v]) + Σ(Costo_km × distancia[i,j] × x[v,i,j])
```

### Cálculo de Distancias

**Fórmula de Haversine:** Distancia de gran círculo entre dos puntos geográficos (lat/lon)

```python
d = 2r × arcsin(√(sin²(Δφ/2) + cos(φ₁)·cos(φ₂)·sin²(Δλ/2)))
```

Donde r = 6,371 km (radio de la Tierra)

### Solver y Configuración

**Solver:** HiGHS 1.12.0 (open-source MIP solver)  
**Configuración:**
- Límite de tiempo: 120 segundos
- Gap de tolerancia: 5%
- Presolve: Activado
- Paralelización: Activada

**Rendimiento:**
- Primera solución factible: 0.7 segundos
- Mejor solución encontrada: 120 segundos
- Nodos explorados: 952
- Iteraciones LP: 258,045

## 📖 Documentación Detallada

Para información completa sobre el modelado, resultados y análisis, consultar:

📄 **[Informe Técnico del Caso 1](docs/informe_caso1.md)**

El informe incluye:
- Descripción matemática completa del modelo
- Análisis detallado de cada ruta
- Interpretación de resultados
- Comparación con soluciones triviales (ahorro del 83%)
- Análisis de sensibilidad y factores limitantes
- Referencias a archivos de verificación y visualización

## 🔍 Validación de Resultados

### Verificación Manual

✅ **Asignación:** Los 24 clientes aparecen en las rutas (sin duplicados)  
✅ **Capacidades:** V001: 130≤130 | V002: 140≤140 | V008: 107≤114  
✅ **Autonomías:** V001: 43.5≤170 | V002: 103.0≤200 | V008: 61.4≤140  
✅ **Rutas cerradas:** Todas las rutas inician y terminan en CD01  
✅ **Sin subtours:** No existen ciclos sin el depósito

### Calidad de la Solución

- **Solución factible:** ✅ Cumple todas las restricciones
- **Gap:** 57.73% (solución puede mejorarse con más tiempo de cómputo)
- **Ahorro vs. solución trivial:** ~$7.5 millones COP (83% de reducción de costos)
- **Eficiencia:** 98% de utilización promedio de capacidad

## 🛠️ Optimizaciones Implementadas

Para lograr tiempos de ejecución razonables:

1. **Reducción de arcos:** Eliminación de arcos inválidos (i→i, depot→depot)
2. **Formulación MTZ simplificada:** Reemplazo de sistema complejo de carga por MTZ estándar
3. **Variables reducidas:** De 5,208 a 5,000 variables (4% reducción)
4. **Presolve del solver:** HiGHS reduce automáticamente el problema antes de resolver
5. **Bounds ajustados:** Límites estrictos en variables continuas u[v,i]

**Resultado:** Modelo presolve de 9,464 filas × 5,000 columnas con 46,312 no-ceros

## 📦 Extensiones Futuras

### Caso 2: Estaciones de Recarga

**Nuevos componentes:**
- Archivo: `stations.csv` con ubicaciones de estaciones
- Restricción: Vehículos deben recargar cuando autonomía < umbral
- Archivos de salida: `verificacion_caso2.csv`, `rutas_caso2.png`

### Caso 3: Peajes

**Nuevos componentes:**
- Archivo: `tolls.csv` con costos de peajes por segmento
- Modificación: Función objetivo con costos adicionales de peajes
- Archivos de salida: `verificacion_caso3.csv`, `rutas_caso3.png`

## 🐛 Troubleshooting

### Error: "No module named 'pyomo'"
```powershell
pip install pyomo highspy
```

### Error: "Solver 'appsi_highs' not found"
```powershell
pip install --upgrade highspy
```

### Error: Encoding issues (caracteres extraños)
```powershell
$env:PYTHONIOENCODING='utf-8'; python src/run_caso1.py
```

### Error: "Archivos no encontrados"
Verificar que la carpeta `Proyecto_Caso_Base` esté al mismo nivel que `proyecto_c`:
```
Nueva carpeta/
├── proyecto_c/
└── Proyecto_Caso_Base/
```

### Modelo toma demasiado tiempo
Ajustar límites en `src/run_caso1.py`:
```python
SOLVER_TIME_LIMIT = 60  # Reducir a 60 segundos
SOLVER_GAP = 0.10       # Aumentar gap aceptable a 10%
```

## 📚 Referencias

1. Dantzig & Ramser (1959). The truck dispatching problem. *Management Science*.
2. Toth & Vigo (2014). *Vehicle Routing: Problems, Methods, and Applications*.
3. Laporte (1992). The vehicle routing problem: An overview. *European Journal of Operational Research*.
4. Miller, Tucker & Zemlin (1960). Integer programming formulation of TSP. *Journal of the ACM*.
5. HiGHS Documentation: https://highs.dev/

## 👤 Autor

**Nicolás**  
Proyecto C - Optimización de Ruteo de Vehículos  
Noviembre 2025

## 📄 Licencia

Este proyecto es parte de un trabajo académico. Para uso educativo.

---

**Última actualización:** 23 de noviembre de 2025  
**Versión:** 1.0 (Caso 1 completo)
