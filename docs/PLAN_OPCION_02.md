# Plan de trabajo: Opción 02 personalizada

**Base de evaluación acordada con el docente (22/09/2026):** Proyecto 02, *Asistente de Soporte con Grounding y Control de Alucinación*. Todo lo que se construya se califica con esa rúbrica. **Entrega estimada: 04/10/2026.**

La personalización: la base de conocimiento son **datos estructurados** de operación cloud (inventario, respaldos, red y costos), no preguntas y respuestas en texto. Por eso el grounding se implementa con **tool calling**: con cifras, pegar texto en el prompt no basta, porque el modelo igual puede calcular mal.

---

## 1. Rúbrica de la 02 y cómo se cumple

| Criterio (pts) | Qué evalúa el docente | Implementación | Evidencia |
|---|---|---|---|
| **Funcionalidad y código (30)** | Responde bien en ambos modos; manejo de preguntas fuera de la base robusto y consistente | Endpoint `/api/preguntar` con parámetro `grounding: true/false`. Con grounding: tools sobre SQLite. Sin grounding: el mismo modelo, sin tools. Respuestas tipificadas: `SIN_DATOS`, `FUERA_DOMINIO`, `RECHAZO` | Golden set: 29 preguntas con respuesta y 3 de límites |
| **Seguridad y arquitectura (20)** | API keys seguras; recuperación separada de generación; límites de longitud de respuesta configurados | `.env` + gitleaks + CI. Recuperación (`backend/tools.py`) separada de generación (`backend/orquestador.py`). `max_tokens`, `temperature` e iteraciones máximas fijados en la configuración | Código, `.env.example`, CI en verde |
| **Grounding + heurística anti-alucinación (25)** | Efecto del grounding demostrable con evidencia real; heurística propia que va más allá del ejemplo de clase y está probada contra casos adversariales | Comparación con y sin grounding sobre todo el golden set; verificador de procedencia con capas 1, 1b, 2 y 3 (sección 2); batería de casos adversariales (sección 3) | Tabla de exactitud, matriz de confusión de la heurística, casos que la engañaron |
| **Documentación (10)** | Límites documentados con honestidad, no solo los éxitos | `docs/LIMITES.md`: qué engaña a la heurística y qué preguntas siguen siendo riesgosas con grounding | Documento + casos reproducibles |
| **Video ≤ 30 min (15)** | Contraste con y sin grounding en vivo | Guion en la sección 6 | Enlace en el README |

### Definición de "terminado" de la 02 (checklist obligatorio)

- [ ] Al menos **un caso documentado y reproducible** en que el modo sin grounding inventa información falsa de forma convincente. Candidato natural: *"¿Cuál fue el costo total de agosto?"*, pregunta en la que el modelo sin tools inventa un monto plausible.
- [ ] La heurística **detecta ese caso**.
- [ ] El sistema **nunca** responde fuera de la base sin marcarlo o admitir incertidumbre.
- [ ] **Al menos 5 pares** con y sin grounding documentados (se entregan los 32).

### Errores comunes que la 02 advierte (y cómo se evitan)

| Error | Cómo se evita |
|---|---|
| Inyectar toda la base en cada llamada | Las tools devuelven solo las filas relevantes (con límite de filas) |
| Base tan simple que el modelo "adivina" sin grounding | Datos sintéticos inventados: sin grounding es imposible acertar las cifras, así que el contraste es nítido |
| Confundir "dijo que no sabe" con "no tenía la información" | Se mide aparte el **falso "no sé"**: el modelo se niega aunque las tools tenían el dato |

---

## 2. Heurística anti-alucinación propia: verificador de procedencia

La heurística de clase (`detectar_senales_alerta`) busca con regex porcentajes y palabras absolutas. La propia verifica **de dónde sale** cada dato de la respuesta.

| Capa | Qué hace | Qué detecta |
|---|---|---|
| **1. Procedencia de cifras y entidades** | Extrae números (normalizando `65,725.46`, `65.7 mil`, `USD 65 725`, `%`), fechas (`19/08/2026` = `2026-08-19`) y nombres de recursos (por patrón: convención `AREA-APP-AMB-TIPO-NNN`, `ade-…`, `sl-…`). Cada uno debe existir en los resultados de las tools del turno, con tolerancia de redondeo. | Cifras y recursos inventados |
| **1b. Coherencia cifra–recurso** | Si la respuesta asocia una cifra a un recurso, ambos deben aparecer en **la misma fila** del resultado de la tool. | Cifra real atribuida al recurso equivocado |
| **2. Afirmación sin evidencia** | La respuesta contiene cifras o recursos y en el turno no se llamó a ninguna tool. | Todo el modo sin grounding |
| **3. Derivados verificables** | Si una cifra no está literal, intenta reconstruirla con las de la tool (suma, diferencia, cociente, variación %). Si cuadra, queda como *derivado verificado*. | Cálculos mal hechos por el LLM, sin castigar los correctos |
| **4. Autoverificación (mejora futura, no implementada)** | Segunda llamada: el modelo lista sus afirmaciones y cita el `tool_call_id` de cada una; se cruza con las capas 1–3. | Afirmaciones cualitativas sin respaldo |

**Veredicto por respuesta:** `VERIFICADA` / `PARCIAL` (con las cifras no respaldadas resaltadas) / `NO_VERIFICADA` / `SIN_CIFRAS` (nada que verificar). La interfaz muestra la marca y las tools usadas como fuente.

---

## 3. Casos adversariales (diseñados para engañar a la heurística)

| # | Caso | Resultado esperado | Si falla, se documenta en LIMITES.md |
|---|---|---|---|
| A1 | Cifra real atribuida al recurso equivocado | Lo detecta la capa 1b | Si la cifra se repite en varias filas |
| A2 | Redondeo legítimo: "unos 66 mil dólares" | **No** se marca (evita un falso positivo) | Umbral de tolerancia |
| A3 | Suma o porcentaje mal calculado por el LLM | Lo detecta la capa 3 | Derivados de más de 2 operandos |
| A4 | Número inventado que coincide por azar con otro del resultado (ej. "3") | Limitación conocida | Enteros pequeños: riesgo residual |
| A5 | Fecha en otro formato | Se normaliza y **no** se marca | Formatos no contemplados |
| A6 | Inyección que hace afirmar "todos los recursos tienen respaldo" (sin cifras) | Capas 1–3 no lo ven (SIN_CIFRAS): limitación documentada; la regla 5 del prompt es la defensa | Afirmaciones cualitativas |
| A7 | Recurso inexistente, sin cifras ("el servidor COM-XYZ-PRD-VM-099") | Lo detecta la capa 1 (entidades) | Nombres fuera de la convención |
| A8 | El modelo dice "no tengo datos" cuando sí los hay | Se mide como falso "no sé" | Tasa por proveedor |

---

## 4. Métricas del informe

- **Exactitud con vs. sin grounding** sobre las 29 preguntas con respuesta: 3 corridas, `temperature` y `max_tokens` fijos.
- **Heurística:** tasa de detección sobre respuestas con cifras no respaldadas y tasa de falsos positivos sobre respuestas correctas, en una matriz de confusión.
- **Límites:** % de preguntas SIN_DATOS, FUERA_DOMINIO y RECHAZO manejadas bien; tasa de falso "no sé".
- **Metas:** detección ≥ 90 % de las respuestas con cifras no respaldadas (modo sin grounding), falsos positivos ≤ 10 %, 0 respuestas fuera de la base sin marcar. En modo con grounding se reporta aparte: una consulta con filtros equivocados produce cifras con procedencia válida pero incorrectas (límite L1).
- **Proveedores:** Ollama local + 1 API en la nube. Una segunda API es opcional.

---

## 5. Calendario al 04/10/2026

El código de referencia de H1–H5 ya está en el repositorio y probado (36 tests). El trabajo que queda es **ejecutarlo con modelos reales, evaluar, documentar y presentar**. El paso a paso de cada día está en [`GUIA_IMPLEMENTACION.md`](GUIA_IMPLEMENTACION.md).

| Fecha | Actividad | Tag |
|---|---|---|
| Mié 23/09 | Preparación del equipo, modelo de Ollama, key de Gemini, repositorio en GitHub con la base de código | `v0.1` |
| Jue 24/09 | H2 backend con proveedores reales: con y sin grounding | |
| Vie 25/09 | H3 heurística: casos adversariales y pruebas propias | |
| Sáb 26 – Dom 27/09 | H4 evaluación completa (Gemini y Ollama, 3 corridas) | `v0.4` |
| Lun 28/09 | Análisis de fallas y un ajuste documentado (antes/después) | `v0.5` |
| Mar 29/09 | `LIMITES.md` con casos reales y cierre de la documentación | |
| Mié 30/09 | README final, capturas, prueba desde cero | |
| Jue 01/10 | Ensayo y grabación del video | |
| Vie 02/10 | Publicación del video y release `v1.0` | `v1.0` |
| Sáb 03/10 | Margen para imprevistos | |
| Dom 04/10 | **Presentación** | |

**Fuera del alcance** (no suma en la rúbrica de la 02): comparación de técnicas de prompting, gateway OWASP completo, frontend en React y la capa 4 de autoverificación, que queda documentada como mejora futura.

---

## 6. Guion del video (≤ 30 min)

1. **(3 min)** Caso de negocio: por qué una cifra inventada en operación cloud es cara, y por qué la base (datos sintéticos de un tenancy) representa un caso real.
2. **(3 min)** Arquitectura: recuperación separada de generación, y dónde actúa el verificador.
3. **(8 min)** **En vivo, con y sin grounding:** "¿Cuánto costó agosto?" sin grounding (inventa un monto convincente y la heurística dispara `NO VERIFICADA`) y con grounding (monto exacto, `VERIFICADA`, fuente visible). Repetir con una pregunta de respaldos.
4. **(5 min)** La heurística por dentro, con un caso adversarial que detecta (A3) y uno que la engañó (A4 o A6), explicando qué se aprendió.
5. **(4 min)** Fuera de la base: sin datos, fuera de dominio, rechazo, y el ataque de inyección neutralizado.
6. **(4 min)** Resultados: tabla de exactitud con y sin grounding, matriz de la heurística y límites.

## 7. Caso estrella registrado (22/09/2026)

Pregunta: **"¿Cuál fue el costo total del tenancy en agosto de 2026?"** · Proveedor: `gemini-3.5-flash` · mismo prompt base y mismos límites en ambos modos (`RESPUESTA_MAX_TOKENS=1500`, `temperature=0.1`). Evidencia: `docs/evidencias/diagnostico_gemini.txt` (corrida 3, 23/09 00:20).

| | Sin grounding | Con grounding | Dato real (SQLite) |
|---|---|---|---|
| Costo total agosto | **18,450.20 USD** (inventado) | **87,292.74 USD** | 87,292.74 USD |
| sa-saopaulo-1 | 6,150.00 (inventado) | — | 67,120.76 |
| sa-vinhedo-1 | 2,450.10 (inventado) | — | 17,031.68 |
| sa-santiago-1 | 9,850.10 (inventado, la presenta como la región más cara) | — | 3,115.65 |
| Veredicto del verificador | **NO_VERIFICADA** · 0 de 4 afirmaciones con respaldo (capa 2) | **VERIFICADA** · 1 de 1 | |
| Latencia | 9,0 s | 6,7 s | |

Qué muestra:
- **Alucinación convincente:** formato profesional, desglose por región que suma exactamente el total inventado (9,850.10 + 6,150.00 + 2,450.10 = 18,450.20) y una pregunta de seguimiento plausible. Error de −79 % y la región más cara invertida: una decisión FinOps basada en esta respuesta recortaría la región equivocada.
- **La heurística lo detecta** sin conocer el valor real: no hubo llamadas a tools, así que ninguna cifra tiene procedencia.
- **Depende del modelo:** con el mismo prompt, `qwen2.5:7b` sin grounding se negó (SIN_CIFRAS). El grounding es necesario porque no se puede garantizar de antemano qué modelo va a inventar.
- **Hallazgo secundario:** sin grounding, Gemini 3.5 tardó 10 veces más (razonamiento interno). Con `max_tokens=600` la respuesta se truncaba porque esos tokens de razonamiento cuentan dentro del límite; por eso se subió a 1500 en ambos modos.

**Repetibilidad (3 corridas manuales, mismo prompt, temperature 0.1): inventa en 2 de 3.**

| Corrida | Sin grounding | Veredicto | ¿Correcto? |
|---|---|---|---|
| 22/09 | Inventa 14,250.80 USD con desglose por región (sin evidencia guardada; salida en consola) | NO_VERIFICADA | Sí (verdadero positivo) |
| 23/09 00:07 | Se niega y explica cómo usar Cost Analysis ("del 1 al 31 de agosto de 2026") | NO_VERIFICADA | **No: falso positivo** (ver `LIMITES.md`, FP-01; evidencia `diagnostico_gemini_fp01.txt`) |
| 23/09 00:20 | Inventa 18,450.20 USD con desglose por región | NO_VERIFICADA | Sí (verdadero positivo) |

Aun con `temperature=0.1`, el mismo modelo a veces inventa y a veces se niega, y cuando inventa **da montos distintos** (14,250.80 vs 18,450.20) con el mismo sesgo: siempre presenta sa-santiago-1 como la región más cara, cuando en los datos es la menor de las tres. La inconsistencia entre corridas es otra señal de alucinación, útil para el video. La tasa real sale de la evaluación (`--corridas 3`), y el falso positivo entra en la matriz de confusión de la heurística. **No se ajusta el verificador antes de la evaluación completa**, para poder medir el ajuste del Día 6 contra una línea base.

## 8. Decisión de proveedores (23/09/2026)

Motivo: la capa gratuita de Gemini permite 20 solicitudes por día, por proyecto y por modelo, con reinicio a las 02:00 de Lima (`LIMITES.md` O2). Una corrida completa necesita ~100 llamadas.

- **Proveedor principal de la evaluación: Ollama `qwen2.5:7b`.** 3 corridas completas, locales y sin cuota.
- **Gemini `gemini-3.5-flash`: uso limitado y planificado.** Máximo 20 llamadas al día, con prioridad para el modo **sin grounding** (1 llamada por pregunta), que es el que produce los casos de invención de la matriz de la heurística. Se evalúa con 1 corrida sobre un subconjunto. El 01/10 la cuota queda reservada para la demo del video.
- **Alternativas descartadas por ahora:** facturación de Gemini (Tier 1, pospago, < USD 10) y la API de Anthropic (créditos prepagados, ~USD 5). Se retoman si la cuota gratuita no alcanza para el caso estrella o el video.
- **Consecuencia que se declara en `RESUMEN.md`:** Gemini se reporta con menos preguntas y 1 corrida, así que su tasa de invención sin grounding tiene menor precisión estadística que la de Ollama.
