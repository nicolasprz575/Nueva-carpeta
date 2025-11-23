# 🚀 Guía Rápida - Caso 1 Completado

## ✅ Estado del Proyecto

**CASO 1: COMPLETADO**

Todos los archivos requeridos han sido generados exitosamente:

```
✅ results/caso1/verificacion_caso1.csv    (Archivo de verificación)
✅ results/caso1/rutas_caso1.png           (Visualización de rutas)
✅ docs/informe_caso1.md                    (Informe técnico completo)
✅ results/caso1/resumen.txt                (Resumen ejecutivo)
✅ README.md                                 (Documentación del proyecto)
```

---

## 📊 Resultados Principales

| Métrica | Valor |
|---------|-------|
| **Costo Total** | $1,523,781 COP |
| Vehículos Usados | 3 de 8 (V001, V002, V008) |
| Distancia Total | 207.93 km |
| Clientes Atendidos | 24 de 24 (100%) |
| Utilización Promedio | 98% capacidad |

**Ahorro vs. solución trivial:** ~$7.5 millones COP (83% de reducción)

---

## 🔍 Ver Resultados

### 1. Archivo de Verificación CSV
```powershell
# Abrir en Excel/LibreOffice
start results/caso1/verificacion_caso1.csv

# O ver en terminal
Get-Content results/caso1/verificacion_caso1.csv
```

### 2. Visualización de Rutas
```powershell
# Abrir imagen PNG
start results/caso1/rutas_caso1.png
```

### 3. Informe Técnico
```powershell
# Abrir en VS Code
code docs/informe_caso1.md

# O en navegador (requiere extensión Markdown)
```

### 4. Resumen Ejecutivo
```powershell
Get-Content results/caso1/resumen.txt
```

---

## 🔄 Volver a Ejecutar

Si necesitas regenerar los resultados:

```powershell
# Desde la raíz del proyecto
$env:PYTHONIOENCODING='utf-8'; python src/run_caso1.py

# Tiempo estimado: ~120 segundos
```

**Nota:** Los resultados pueden variar ligeramente debido a la naturaleza heurística del solver (límite de tiempo).

---

## 📄 Exportar Informe a PDF

### Opción 1: VS Code + Extensión (Más fácil)
1. Abrir `docs/informe_caso1.md` en VS Code
2. Instalar extensión: "Markdown PDF" (yzane.markdown-pdf)
3. Click derecho → "Markdown PDF: Export (pdf)"
4. PDF generado en: `docs/informe_caso1.pdf`

### Opción 2: Pandoc (Profesional)
```powershell
# Instalar Pandoc: https://pandoc.org/installing.html
pandoc docs/informe_caso1.md -o docs/informe_caso1.pdf --pdf-engine=xelatex
```

### Opción 3: Servicio Web (Sin instalar nada)
1. Ir a: https://www.markdowntopdf.com/
2. Subir `docs/informe_caso1.md`
3. Descargar PDF generado

---

## 📦 Estructura Final del Proyecto

```
proyecto_c/
├── README.md                          # Documentación principal
├── src/                               # Código fuente
│   ├── datos_caso1.py                # Carga de datos
│   ├── modelo_caso1.py               # Modelo de optimización
│   ├── run_caso1.py                  # Script principal ⭐
│   └── export_pdf.py                 # Exportador de PDF (auxiliar)
├── results/caso1/                    # Resultados
│   ├── verificacion_caso1.csv        # ✅ Verificación (requerido)
│   ├── rutas_caso1.png               # ✅ Visualización (requerido)
│   └── resumen.txt                   # Resumen ejecutivo
└── docs/                             # Documentación
    ├── informe_caso1.md              # ✅ Informe completo (requerido)
    └── ARCHIVOS_GENERADOS.md         # Esta guía

Datos (externos):
../Proyecto_Caso_Base/
├── depots.csv                        # 1 depósito (CD01)
├── clients.csv                       # 24 clientes
├── vehicles.csv                      # 8 vehículos
└── parameters_base.csv               # Costos
```

---

## 🎯 Próximos Pasos

### Para Casos 2 y 3

Cuando estés listo para extender el proyecto:

**Caso 2: Estaciones de Carga**
- Agregar archivo: `stations.csv` en `Proyecto_Caso_Base/`
- Crear: `src/datos_caso2.py`, `src/modelo_caso2.py`, `src/run_caso2.py`
- Generar: `verificacion_caso2.csv`, `rutas_caso2.png`, `informe_caso2.md`

**Caso 3: Peajes**
- Agregar archivo: `tolls.csv` en `Proyecto_Caso_Base/`
- Crear: `src/datos_caso3.py`, `src/modelo_caso3.py`, `src/run_caso3.py`
- Generar: `verificacion_caso3.csv`, `rutas_caso3.png`, `informe_caso3.md`

---

## ❓ Preguntas Frecuentes

### ¿Puedo cambiar el límite de tiempo?
Sí, edita `src/run_caso1.py` líneas 56-58:
```python
SOLVER_TIME_LIMIT = 120  # Cambiar a 60, 300, etc.
SOLVER_GAP = 0.05        # Cambiar a 0.01 (1%), 0.10 (10%), etc.
```

### ¿Por qué el gap es 57.73% si el objetivo era 5%?
El solver alcanzó el límite de tiempo (120s) antes de llegar al gap del 5%. La solución encontrada es **factible** (cumple todas las restricciones) y representa un ahorro del 83% vs. soluciones triviales. Para mejorar el gap, aumenta `SOLVER_TIME_LIMIT` a 600 o más.

### ¿Cómo verifico que la solución es correcta?
```powershell
# Ver archivo de verificación
Get-Content results/caso1/verificacion_caso1.csv

# Sumar clientes atendidos: debe ser 24
# Sumar demandas por vehículo: V001=130, V002=140, V008=107
# Verificar secuencias: todas empiezan y terminan en CD01
```

### ¿Puedo usar otro solver (CBC, GLPK)?
Sí, edita `src/run_caso1.py` línea 56:
```python
SOLVER_NAME = "cbc"  # o "glpk"
```
Luego instala: `pip install pyomo-extensions` o `pip install python-glpk`

---

## 📞 Soporte

Si encuentras errores o necesitas ayuda:

1. **Error de encoding:** Asegúrate de usar `$env:PYTHONIOENCODING='utf-8'`
2. **Solver no encontrado:** Reinstalar `pip install highspy`
3. **Archivos no encontrados:** Verificar estructura de carpetas
4. **Modelo muy lento:** Reducir `SOLVER_TIME_LIMIT` o aumentar `SOLVER_GAP`

---

## ✨ Resumen

**¡Felicitaciones!** Has completado exitosamente el Caso 1 del Proyecto C.

Todos los archivos requeridos están generados y listos para entrega:
- ✅ Archivo de verificación CSV con rutas detalladas
- ✅ Visualización PNG de las rutas optimizadas
- ✅ Informe técnico completo en Markdown (convertible a PDF)

El modelo encontró una solución que usa **solo 3 vehículos** (en lugar de 8) para atender los 24 clientes, logrando un **ahorro del 83%** en costos comparado con soluciones triviales.

**Costo total:** $1,523,781 COP  
**Distancia total:** 207.93 km  
**Eficiencia:** 98% de utilización de capacidad

---

**Fecha:** 23 de noviembre de 2025  
**Versión:** 1.0
