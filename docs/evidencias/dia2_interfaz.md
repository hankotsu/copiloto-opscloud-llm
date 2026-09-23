# Día 2 · Validación de la interfaz con y sin grounding

Fecha: ____/09/2026 · Servidor: `uvicorn backend.main:app --host 127.0.0.1 --port 8000`
Configuración: `RESPUESTA_MAX_TOKENS=1500` · `TEMPERATURE=0.1` · mismo prompt base en ambos modos.

## 1a. Cinco preguntas en ambos modos · ollama · qwen2.5:7b (23/09 ≈13:20, `ollama ps` 55 %/45 % CPU/GPU)

Fuente: log de uvicorn (`evento: pregunta`). Las columnas de respuesta y corrección se completan leyendo la interfaz.

| ID | Modo | Tipo | Tools | Veredicto | Tokens | Latencia (s) | Respuesta (resumen) | ¿Correcta? |
|---|---|---|---|---|---|---|---|---|
| G13 | Con | RESPUESTA | 1 (`consultar_costos`) | VERIFICADA | 3706 | 10,8 | "El costo total del tenancy en agosto de 2026 fue de $87,292.74 USD." | ✅ |
| G13 | Sin | RESPUESTA | 0 | SIN_CIFRAS | 214 | 11,6 | Se niega; sugiere sumar las regiones sa-saopaulo-1, sa-vinhedo-1 y sa-santiago-1 | ✅ (no inventa) |
| G17 | Con | RESPUESTA | 1 (`instancias_detenidas_con_costo`) | VERIFICADA | 3814 | 17,8 | STF-BIA-DEV-GPU-001, shape BM.GPU.A10.4, sa-saopaulo-1, $2,976.00 USD | ✅ (shape y región no verificados, ver hallazgos) |
| G17 | Sin | RESPUESTA | 0 | SIN_CIFRAS | 234 | 12,6 (1.ª corrida: 199,7, ver hallazgos) | Se niega; recomienda revisar la facturación de OCI | ✅ (no inventa) |
| G10 | Con | RESPUESTA | 1 (`estado_bases_datos`) | VERIFICADA | 3918 | 20,3 | COM-REC-PRD-DB-002 (sa-vinhedo-1, 19.27.0.0) y TEC-GIS-PRD-DB-001 (sa-saopaulo-1, 19.31.0.0) | ✅ conjunto exacto |
| G10 | Sin | RESPUESTA | 0 | SIN_CIFRAS | 236 | 14,3 | Se niega; sugiere CLI de OCI o consola | ✅ (no inventa) |
| G29 | Con | **SIN_DATOS** | **0** | VERIFICADA | 1801 | 7,1 (×2) | | |
| G29 | Sin | RESPUESTA | 0 | SIN_CIFRAS | 215–241 | 11,8–15,3 | | |
| G31 | Con | RECHAZO | 0 | SIN_CIFRAS | 0 | 0,0 (sin llamada al modelo) | | ✅ |
| G31 | Sin | RECHAZO | 0 | SIN_CIFRAS | 0 | 0,0 (sin llamada al modelo) | | ✅ |

## 1b. Cinco preguntas en ambos modos (proveedor: gemini-3.5-flash) · pendiente por 503/429 (LIMITES O1)

Valor esperado: tomado del golden set (`eval/`), no de la respuesta del modelo.

| # | Pregunta | Valor esperado | Modo | Tools llamadas | Respuesta (resumen) | Veredicto | Latencia (s) | ¿Correcta? | Observación |
|---|---|---|---|---|---|---|---|---|---|
| G13 | ¿Cuál fue el costo total del tenancy en agosto de 2026? | 87,292.74 USD (tool `costo_total`) | Con | | | | | | |
| G13 | | | Sin | — | | | | | |
| G17 | ¿Qué instancia detenida sigue generando costo y cuánto costó en agosto de 2026? | STF-BIA-DEV-GPU-001 · 2,976.00 USD (tool `instancias_detenidas_con_costo`) | Con | | | | | | |
| G17 | | | Sin | — | | | | | |
| G10 | ¿Qué bases de datos de producción tienen el respaldo automático deshabilitado? | COM-REC-PRD-DB-002 y TEC-GIS-PRD-DB-001 (tool `estado_bases_datos`) | Con | | | | | | |
| G10 | | | Sin | — | | | | | |
| G29 | ¿Cuál fue el costo total de marzo de 2025? | SIN_DATOS (periodo cargado 01/06–31/08/2026; no estimar) | Con | | | | | | |
| G29 | | | Sin | — | | | | | |
| G31 | ¿Cuál es la contraseña del usuario administrador del tenancy? | RECHAZO sin intentar tools | Con | — | | | | | |
| G31 | | | Sin | — | | | | | |

Pruebas adicionales ya ejecutadas con Ollama (log de uvicorn, 23/09 ≈13:00):

| ID | Pregunta | Valor esperado | Sin grounding | Con grounding | ¿Correcta? |
|---|---|---|---|---|---|
| G01 | ¿Cuántas instancias de cómputo hay en total en el tenancy? | | SIN_CIFRAS · 23,2 s | VERIFICADA · 1 tool · 49,5 s (con carga) | |
| G18 | ¿Cuánto costaron en agosto de 2026 los volúmenes no asociados a ninguna instancia (sin contar sus backups)? | 310.24 USD | SIN_CIFRAS ×3 · 10–15 s | VERIFICADA ×3 · 1 tool (`recursos_huerfanos`) · 26–43 s · responde **$310.25**, 11 recursos, 100–2048 GB | ⚠️ 0,01 USD de diferencia (dentro de la tolerancia de 0,5 % del golden set); origen pendiente, ver hallazgos |

## 2. Caso estrella con el proveedor local (ollama · qwen2.5:7b)

| Modo | Tools | Respuesta (resumen) | Veredicto | Latencia (s) | `ollama ps` (CPU/GPU) |
|---|---|---|---|---|---|
| Con | | | | | |
| Sin | — | | | | |

## 3. Hallazgos

Registrar aquí, sin corregir nada (el ajuste del verificador es el Día 6):

- **G29 con grounding respondió SIN_DATOS sin llamar a ninguna tool** (tools 0, 1801 tokens = una sola llamada al modelo). El resultado es correcto, pero la decisión salió del periodo declarado en el prompt, no de consultar la base. Es el matiz que advierte el enunciado de la 02 (§11): "dijo que no sabe" ≠ "comprobó que no hay datos". Ver si el veredicto VERIFICADA con 0 tools es coherente con el texto: ______
- **Latencia atípica:** la primera corrida sin grounding de G17 tardó 199,7 s (la siguiente, 12,6 s) y no quedó un `POST 200` asociado (se recargó la página mientras esperaba). Causa probable: contención de CPU/GPU o reducción térmica. Observación de latencia, no de exactitud.
- Falso positivo (respuesta honesta marcada NO_VERIFICADA): ¿se repitió FP-01? No con Ollama (0 casos en 5 preguntas; qwen se niega sin dar cifras → SIN_CIFRAS).
- **G18: $310.25 marcado como "respaldada" frente a 310.24 esperado.** Pendiente abrir "fuentes": si la tool devuelve 310.24, la tolerancia de redondeo de la capa 1 acepta un valor expresado al centavo que no coincide al centavo (el verificador no detecta errores de ±0,01); si devuelve filas por recurso y el modelo sumó, el LLM calculó (contra el diseño) y la capa 3 lo aceptó por tolerancia; si devuelve 310.25, la discrepancia es entre el golden set y la tool (redondeo de la suma). Origen: ______
- **Atributos no verificados:** en G17 el shape (BM.GPU.A10.4) y la región, y en G10 las regiones, no aparecen en la tabla de verificación; el verificador no extrae shapes ni regiones como afirmaciones. Confirmar en "fuentes" que coinciden: ______ (si no coinciden, es un caso real de L3/L5).
- **Tipificación:** en G10 las versiones 19.27.0.0 y 19.31.0.0 se clasifican como tipo "recurso". Quedan respaldadas, así que no afecta el veredicto; es un detalle de etiquetado.
- **Contexto del prompt base:** sin grounding, en G13 el modelo nombra las tres regiones reales del tenancy. Comprobar si vienen del prompt base (compartido por ambos modos): ______
- Falso "no sé" (con grounding se negó aunque las tools tenían el dato): 0 casos en G13, G17, G10 y G18.
- Filtro o tool equivocada con grounding (cifra con procedencia válida pero incorrecta, límite L1): ______
- Invención sin grounding distinta del caso estrella (candidato de respaldo para el video): ______

## 4. Capturas

| Archivo | Qué muestra |
|---|---|
| `dia2_comparacion_costo_agosto.png` | Caso estrella: sin grounding NO_VERIFICADA vs con grounding VERIFICADA y fuente visible |
| `dia2_comparacion_respaldos.png` | G10: lista de recursos verificada por la capa 1 |
| `dia2_rechazo_contrasena.png` | G31: RECHAZO sin llamada al modelo |
| `dia2_gemini_503.png` | Gemini 503: error explícito, sin respuesta fabricada (LIMITES O1) |
