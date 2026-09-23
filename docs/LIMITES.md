# Límites conocidos del sistema

> La rúbrica de la opción 02 valora documentar con honestidad lo que **no** funciona. Este documento parte de los límites comprobados con tests (`tests/test_verificador.py`) y **se completa con los resultados reales** de `eval/resultados/` (sección 4 de cada `RESUMEN.md`).

## 1. Límites del verificador de procedencia

| # | Límite | Evidencia | Mitigación posible |
|---|---|---|---|
| L1 | **Comprueba procedencia, no pertinencia.** Si el modelo consulta la tool con un filtro equivocado (otra región, otro mes), la cifra sí proviene de la tool y la respuesta queda VERIFICADA aunque sea incorrecta. | Falsos negativos del modo con grounding en `RESUMEN.md` | Mostrar al usuario los filtros usados (la interfaz ya los muestra en "fuentes"); segundo paso que compare la pregunta con los argumentos |
| L2 | **Coincidencia por azar (A4).** Un número pequeño inventado (ej. "3") puede coincidir con otro valor de los resultados, como el largo de una lista. | `test_A4_LIMITACION_...` | Exigir coherencia cifra–recurso (capa 1b) también para enteros pequeños |
| L3 | **Afirmaciones cualitativas (A6).** "Todos los recursos tienen respaldo" no tiene cifras ni recursos: el verificador devuelve SIN_CIFRAS. | `test_A6_LIMITACION_...` | Capa 4 (autoverificación con el LLM) o reglas para afirmaciones universales ("todos", "ninguno") |
| L4 | **Derivados de más de dos operandos.** La capa 3 reconstruye operaciones entre dos valores o la suma de una columna completa; una suma parcial de tres filas queda como no respaldada. | Diseño de `_derivable` | Pedir el agregado a una tool en lugar de calcularlo |
| L5 | **Nombres fuera de la convención.** Los recursos se detectan por patrón (`AREA-APP-AMB-TIPO-NNN`, `ade-…`, `sl-…`). Un nombre inventado con otro formato no se detecta como recurso. | Diseño de `RE_ENTIDAD` | Cruzar contra el catálogo completo de nombres de la BD |

## 2. Límites del grounding

| # | Límite | Evidencia |
|---|---|---|
| G1 | El modelo puede elegir mal la herramienta o sus filtros, sobre todo los modelos locales pequeños. | Completar con `RESUMEN.md` (exactitud por categoría, modo con grounding) |
| G2 | **Falso «no sé»:** el modelo responde SIN_DATOS aunque la tool tenía el dato. | Métrica "Falso «no sé»" en `RESUMEN.md` |
| G3 | Preguntas que requieren encadenar herramientas (categoría *cruzada*) fallan más. | Completar |
| G4 | La variabilidad entre corridas no es cero, aun con temperature baja. | Desviación entre corridas en `RESUMEN.md` |

## 3. Casos reales que engañaron al sistema

> Completar después de la evaluación con al menos 2 casos: pregunta, respuesta, por qué falló y qué se aprendió.

| Caso | Proveedor / modo | Qué pasó | Qué se aprendió |
|---|---|---|---|
| | | | |

## 4. Fuera del alcance

- Los datos son sintéticos y estáticos; no hay conexión en vivo con OCI.
- Las tarifas de costos son ilustrativas.
- El puntaje automático (`eval/puntaje.py`) verifica que la respuesta **contenga** el valor esperado; una respuesta con datos correctos y además una afirmación falsa puede puntuar como correcta (el verificador la marcaría PARCIAL).
