# Límites conocidos del sistema

> La rúbrica de la opción 02 valora documentar con honestidad lo que **no** funciona. Este documento parte de los límites comprobados con tests (`tests/test_verificador.py`) y **se completa con los resultados reales** de `eval/resultados/` (sección 4 de cada `RESUMEN.md`).

## 1. Límites del verificador de procedencia

| # | Límite | Evidencia | Mitigación posible |
|---|---|---|---|
| L1 | **Comprueba procedencia, no pertinencia.** Si el modelo consulta la tool con un filtro equivocado (otra región, otro mes), la cifra sí proviene de la tool y la respuesta queda VERIFICADA aunque sea incorrecta. | Falsos negativos del modo con grounding en `RESUMEN.md` | Mostrar al usuario los filtros usados (la interfaz ya los muestra en "fuentes"); segundo paso que compare la pregunta con los argumentos |
| L2 | **Coincidencia por azar (A4).** Un número pequeño inventado (ej. "3") puede coincidir con otro valor de los resultados, como el largo de una lista. | `test_A4_LIMITACION_...` | Exigir coherencia cifra–recurso (capa 1b) también para enteros pequeños |
| L3 | **Afirmaciones cualitativas (A6).** "Todos los recursos tienen respaldo" no tiene cifras ni recursos: el verificador devuelve SIN_CIFRAS. | `test_A6_LIMITACION_...` | Capa 4 (autoverificación con el LLM) o reglas para afirmaciones universales ("todos", "ninguno") |
| L4 | **Derivados de más de dos operandos.** La capa 3 reconstruye operaciones entre dos valores o la suma de una columna completa; una suma parcial de tres filas queda como no respaldada. | Diseño de `_derivable` | Pedir el agregado a una tool en lugar de calcularlo |
| L6 | **Rangos derivados de la pregunta (FP-01).** "Del 1 al 31 de agosto de 2026" en una negativa honesta se marca como afirmación no respaldada. | Sección 3, FP-01 | Tratar como "del usuario" los límites del periodo preguntado (día 1 y último día del mes mencionado) |
| L5 | **Nombres fuera de la convención.** Los recursos se detectan por patrón (`AREA-APP-AMB-TIPO-NNN`, `ade-…`, `sl-…`). Un nombre inventado con otro formato no se detecta como recurso. | Diseño de `RE_ENTIDAD` | Cruzar contra el catálogo completo de nombres de la BD |

## 2. Límites del grounding

| # | Límite | Evidencia |
|---|---|---|
| G1 | El modelo puede elegir mal la herramienta o sus filtros, sobre todo los modelos locales pequeños. | Completar con `RESUMEN.md` (exactitud por categoría, modo con grounding) |
| G2 | **Falso «no sé»:** el modelo responde SIN_DATOS aunque la tool tenía el dato. | Métrica "Falso «no sé»" en `RESUMEN.md` |
| G3 | Preguntas que requieren encadenar herramientas (categoría *cruzada*) fallan más. | Completar |
| G4 | La variabilidad entre corridas no es cero, aun con temperature baja. | Desviación entre corridas en `RESUMEN.md` |
| G5 | **El comportamiento sin grounding depende del modelo.** Con el mismo prompt, `qwen2.5:7b` se niega y `gemini-3.5-flash` inventa un monto con desglose coherente (ver `PLAN_OPCION_02.md` §7). Una prueba con un solo modelo no demuestra que el riesgo no exista. | `docs/evidencias/diagnostico_ollama.txt` vs `diagnostico_gemini.txt` |
| G6 | **Los modelos con razonamiento consumen `max_tokens` antes de escribir.** Con 600 la respuesta de Gemini 3.5 se truncaba sin error visible. | Diagnóstico del 22/09 (100+23 tokens, respuesta cortada) |
| G7 | **SIN_DATOS decidido con el contexto, sin consultar la base.** Con grounding, el prompt incluye el periodo cargado (leído de la BD al iniciar). Ante un mes fuera de rango (G29, marzo de 2025), `qwen2.5:7b` respondió SIN_DATOS sin llamar a ninguna tool. Es correcto mientras el periodo inyectado lo sea, pero el "no sé" no se comprobó con una consulta. Además, el verificador acepta las fechas del periodo como respaldadas por ese contexto, y la interfaz muestra "herramientas: ninguna" junto a "respaldada", lo que puede confundir. | `docs/evidencias/dia2_interfaz.md` (G29) · `orquestador.py:69,113` · `prompts.py:12` |

## 3. Casos reales que engañaron al sistema

> Completar después de la evaluación con al menos 2 casos: pregunta, respuesta, por qué falló y qué se aprendió.

| Caso | Proveedor / modo | Qué pasó | Qué se aprendió |
|---|---|---|---|
| **FP-01** (23/09) · "¿Cuál fue el costo total del tenancy en agosto de 2026?" | gemini-3.5-flash · sin grounding | El modelo se negó con honestidad ("No tengo acceso directo…") y explicó cómo consultar Cost Analysis: "configura el rango **del 1 al 31 de agosto de 2026**". El verificador marcó **NO_VERIFICADA** (capa 2) por "1" y "31 de agosto de 2026". **Falso positivo:** no hay ninguna afirmación sobre los datos. | La capa 2 trata toda cifra o fecha como afirmación, incluso los límites del periodo que el usuario preguntó y los números de una instrucción. La corrección de `fechas_usuario` (fecha literal de la pregunta) no cubre fechas **derivadas** de la pregunta (primer y último día del mes). Candidato al ajuste documentado del Día 6, medido antes y después con la matriz de confusión. |
| **FN-01** (23/09) · G18 "¿Cuánto costaron en agosto de 2026 los volúmenes no asociados a ninguna instancia…?" | qwen2.5:7b · con grounding | Respuesta: "$310.25. Estos volúmenes están distribuidos en la región **sa-saopaulo-1** y tienen tamaños que van desde 100 GB hasta 2048 GB." Veredicto **VERIFICADA, 3 de 3**. La cifra, el 100 y el 2048 son correctos, pero la tool devolvió 11 volúmenes y uno, `prueba-fra-vm (Boot Volume)`, está en **eu-frankfurt-1**. **Falso negativo:** una afirmación falsa pasa como verificada. En otra corrida de la misma pregunta el modelo no mencionó la región: la invención es intermitente. | Las regiones no son un tipo de afirmación que la capa 1 extraiga (solo cifras, fechas y recursos por patrón), y una afirmación universal sin cifra ("todos en X") es exactamente L3. El grounding reduce la invención, pero el modelo puede **generalizar de más** sobre datos reales: resumió 11 filas por la mayoría. Mitigación posible: extraer regiones (catálogo cerrado de 4 valores) y comprobar que toda región mencionada aparezca en las filas, y que "en la región X" no se afirme si hay filas de otra región. No se ajusta antes de la línea base. Evidencia: `docs/evidencias/dia2_fuentes_g18.txt`. |

## 4. Fuera del alcance

- Los datos son sintéticos y estáticos; no hay conexión en vivo con OCI.
- Las tarifas de costos son ilustrativas.
- El puntaje automático (`eval/puntaje.py`) verifica que la respuesta **contenga** el valor esperado; una respuesta con datos correctos y además una afirmación falsa puede puntuar como correcta (el verificador la marcaría PARCIAL).
- **Consistencia golden set ↔ tool (G18):** la tool `recursos_huerfanos` devuelve 310.25 y el golden set espera 310.24. Es una diferencia de redondeo al generar la clave (suma de valores redondeados frente a redondeo de la suma). La tolerancia de 0,5 % la absorbe, así que no altera el puntaje.
- **Puntaje de SIN_DATOS en el modo sin grounding:** ese modo no recibe la regla que pide el prefijo "SIN_DATOS:", así que una negativa honesta (G29, marzo de 2025) se puntúa como incorrecta. Para ese modo, la lectura correcta es "no inventó" (veredicto SIN_CIFRAS), no "falló".

## 5. Límites operativos

| # | Límite | Evidencia | Mitigación |
|---|---|---|---|
| O1 | **Disponibilidad del proveedor en la nube.** El 23/09 (12:50–13:15) `gemini-3.5-flash` respondió 503 `UNAVAILABLE` (servicio saturado) en los 3 intentos de cada consulta. El sistema devolvió un error explícito y **no generó ninguna respuesta**: degrada de forma segura, pero queda sin servicio. | `docs/evidencias/dia2_gemini_503.png` · log de uvicorn (`error_proveedor`) · `docs/evidencias/diagnostico_gemini_reintento.txt` | Proveedor local (Ollama) como respaldo; `--pausa` en la evaluación; Ollama precalentado como plan B del video |
| O2 | **Cuota diaria de la capa gratuita.** A las 13:54 la API devolvió 429 `RESOURCE_EXHAUSTED`: 20 solicitudes por día, por proyecto y por modelo (`GenerateRequestsPerDayPerProjectPerModel-FreeTier`), con reinicio a medianoche del Pacífico (02:00 en Lima). `GET /models` respondió 200 y listó el modelo, así que la key y la configuración estaban bien. Los diagnósticos y reintentos del día agotaron la cuota; todo indica que los intentos fallidos por 503 también cuentan. Una corrida completa necesita ~100 llamadas, así que 3 corridas son inviables en la capa gratuita. | `docs/evidencias/diagnostico_http_gemini.txt` | Tier 1 (facturación) o Ollama como proveedor principal; no reintentar ante un 429 diario (el `retryDelay` de 58 s no aplica a la cuota por día) |
| O3 | **Errores del proveedor contados como negativas (defecto del instrumento, corregido el 23/09 antes de la línea base).** Con la cuota agotada, `run_eval.py` registró cada 429 como `SIN_CIFRAS` y respuesta incorrecta. En una evaluación real, eso habría inflado la tasa de "no inventó" sin grounding y bajado la exactitud con grounding por fallas ajenas al modelo. **Corrección:** la consulta queda con tipo y veredicto `ERROR`, se excluye de todas las métricas y `RESUMEN.md` informa cuántas se excluyeron; la corrida se detiene tras 3 errores seguidos (`--max-errores-seguidos`); y el adaptador ya no reintenta un 429 de cuota **diaria**. | `docs/evidencias/eval_gemini_429_contaminada.jsonl` · `tests/test_eval.py` (5 tests) | Revisar en cada `RESUMEN.md` la fila "Consultas con error del proveedor (excluidas)" y repetir las preguntas afectadas |
