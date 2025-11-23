# Archivos de Salida Generados - Caso 1

## ✅ Archivos Obligatorios

### 1. Archivo de Verificación CSV
**Ubicación:** `results/caso1/verificacion_caso1.csv`

**Formato:**
```csv
VehicleId,DepotId,InitialLoad,RouteSequence,ClientsServed,DemandsSatisfied,TotalDistance,TotalTime,FuelCost
V001,CD01,130,CD01-C001-C004-C015-C022-C017-C003-C014-C023-CD01,8,13-15-17-18-25-12-15-15,43.46,43.5,23613.0
V002,CD01,140,CD01-C010-C024-C016-C007-C021-C002-C008-C011-C013-CD01,9,15-11-10-17-14-15-20-17-21,103.05,103.0,55990.0
V008,CD01,107,CD01-C019-C020-C012-C009-C005-C018-C006-CD01,7,11-15-12-20-20-12-17,61.42,61.4,33372.0
```

**Columnas:**
- `VehicleId`: ID del vehículo usado
- `DepotId`: ID del depósito (CD01)
- `InitialLoad`: Carga inicial del vehículo (kg)
- `RouteSequence`: Secuencia completa de la ruta (CD01-C00X-...-CD01)
- `ClientsServed`: Número de clientes atendidos
- `DemandsSatisfied`: Demandas en orden (separadas por guiones)
- `TotalDistance`: Distancia total de la ruta (km)
- `TotalTime`: Tiempo total estimado (minutos)
- `FuelCost`: Costo de combustible (COP)

---

### 2. Visualización de Rutas PNG
**Ubicación:** `results/caso1/rutas_caso1.png`

**Contenido:**
- Mapa geográfico con coordenadas (latitud/longitud)
- Depósito CD01 marcado como cuadrado rojo
- Clientes C001-C024 marcados como círculos numerados
- Rutas de vehículos dibujadas con líneas de colores diferentes:
  - V001: Color 1 (8 clientes)
  - V002: Color 2 (9 clientes)
  - V008: Color 3 (7 clientes)

**Leyenda:** Muestra qué color corresponde a cada vehículo

---

### 3. Informe Técnico Completo
**Ubicación:** `docs/informe_caso1.md`

**Secciones:**
1. Resumen Ejecutivo
2. Descripción del Problema
3. Metodología (modelo matemático, restricciones, cálculo de distancias)
4. Resultados (métricas globales, detalle por vehículo)
5. Interpretación y Análisis
6. Conclusiones
7. Referencias (a archivos CSV, PNG, código fuente)
8. Anexos (validaciones, especificaciones técnicas)

**Formato:** Markdown (convertible a PDF)

---

## 📊 Archivo Adicional: Resumen Ejecutivo TXT
**Ubicación:** `results/caso1/resumen.txt`

**Contenido:**
- Fecha de ejecución
- Solver utilizado
- Métricas globales (costo total, vehículos, distancia)
- Detalle de cada ruta (secuencia, clientes, utilización)

---

## 🔄 Casos Futuros

Cuando se extiendan los casos 2 y 3, se generarán de forma análoga:

### Caso 2 (Con estaciones de carga)
- `results/caso2/verificacion_caso2.csv`
- `results/caso2/rutas_caso2.png`
- `docs/informe_caso2.md`

### Caso 3 (Con peajes)
- `results/caso3/verificacion_caso3.csv`
- `results/caso3/rutas_caso3.png`
- `docs/informe_caso3.md`

---

## 📤 Exportar Informe a PDF

### Método 1: VS Code (Recomendado)
1. Instalar extensión: "Markdown PDF" (yzane.markdown-pdf)
2. Abrir `docs/informe_caso1.md`
3. Click derecho → "Markdown PDF: Export (pdf)"

### Método 2: Pandoc (Línea de comandos)
```powershell
# Instalar Pandoc primero: https://pandoc.org/installing.html
pandoc docs/informe_caso1.md -o docs/informe_caso1.pdf --pdf-engine=xelatex
```

### Método 3: Script Python auxiliar
```powershell
python src/export_pdf.py
```
(Lee el script para ver opciones disponibles)

### Método 4: Servicio web
- Visitar: https://www.markdowntopdf.com/
- Subir `informe_caso1.md`
- Descargar PDF

---

## ✅ Verificación Completa

Verifica que existan todos los archivos:

```powershell
# Listar archivos generados
ls results/caso1/
# Debe mostrar: verificacion_caso1.csv, rutas_caso1.png, resumen.txt

ls docs/
# Debe mostrar: informe_caso1.md
```

---

**Última actualización:** 23 de noviembre de 2025
