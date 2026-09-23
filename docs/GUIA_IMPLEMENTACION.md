# Guía de implementación y entrega · 23/09 → 04/10/2026

**Proyecto:** Copiloto de Operaciones Cloud con cifras verificadas · **Evaluación:** rúbrica de la Opción 02 (Asistente con Grounding y Control de Alucinación) · **Presentación:** domingo 04/10/2026.

El repositorio ya trae el **código de referencia completo y probado** (36 tests): datos, backend, heurística, evaluación e interfaz. Tu trabajo de estos 12 días es:

1. **Ejecutarlo con modelos reales** (Ollama y Gemini) y confirmar cada criterio de aceptación.
2. **Entenderlo a fondo:** en el video tienes que explicar cada pieza. Cada día trae una lista de *"qué debes poder explicar"*.
3. **Producir la evidencia:** resultados de evaluación, pares con y sin grounding, límites reales.
4. **Publicarlo en GitHub** y grabar el video.

Dedicación estimada: 2–3 h los días de semana y 4–6 h el fin de semana de evaluación.

**Equipo de trabajo:** laptop con Windows 11 Pro 25H2 · Intel Core i7-9750H (6 núcleos / 12 hilos) · 16 GB de RAM · NVIDIA GTX 1650 con 4 GB · SSD NVMe Samsung 970 EVO Plus. Los tiempos y ajustes de esta guía están calibrados para este equipo.

---

## 0. Qué se entrega el 04/10 (checklist de la opción 02)

| Entregable exigido por la 02 | Dónde queda | Día |
|---|---|---|
| Repositorio con backend funcional y la base de conocimiento propia | GitHub · `backend/` + `data_gen/` | 23/09 |
| Modo con y sin grounding para la misma pregunta | `/api/preguntar` (`grounding: true/false`) · botón *Comparar* | 24/09 |
| Heurística anti-alucinación propia, probada contra casos adversariales | `backend/verificador.py` · `tests/test_verificador.py` | 25/09 |
| Documento comparativo con ≥ 5 pares con y sin grounding | `eval/resultados/<corrida>/PARES.md` (32 pares) | 26–27/09 |
| Un caso reproducible en que el modo sin grounding inventa y la heurística lo detecta | `PARES.md` + `docs/LIMITES.md` + video | 27/09 |
| Límites documentados con honestidad, incluidos los casos que engañaron a la heurística | `docs/LIMITES.md` | 29/09 |
| Video ≤ 30 min con el contraste en vivo | YouTube (no listado) · enlace en el README | 01–02/10 |

---

## Día 1 · Mié 23/09 · Preparación y repositorio (≈ 2,5 h)

### 1.1 Herramientas

Sigue la sección 2 de [`PUBLICAR_EN_GITHUB.md`](PUBLICAR_EN_GITHUB.md): Git, GitHub CLI, Python 3.12 y Ollama. Node.js **no** es necesario: la interfaz es una página HTML que sirve la propia API.

### 1.2 Modelo local para tu equipo: `qwen2.5:7b` ✅ (ya descargado)

Ya confirmaste que `qwen2.5:7b` está descargado y declara la capacidad **tools**. Es la elección correcta para tu equipo. Lo que conviene saber:

**Cómo va a correr.** El modelo pesa 4,7 GB (Q4_K_M) y tu GTX 1650 tiene 4 GB, así que **no entra completo en la GPU**: Ollama reparte las capas entre GPU y CPU. Es normal y funciona, pero más lento que con el modelo entero en la GPU. Verifícalo con el modelo cargado:

```bat
ollama ps
```

La columna `PROCESSOR` muestra el reparto, por ejemplo `48%/52% CPU/GPU`. Cuanto más porcentaje en GPU, mejor.

**Tiempos medidos en tu equipo** (22/09/2026, `ollama ps` → `55%/45% CPU/GPU`, contexto 8192):

| Consulta | Llamadas al modelo | Primera vez (con carga) | Con el modelo ya cargado |
|---|---|---|---|
| Con grounding (costo de agosto) | 2 · 3.640 tokens de entrada | 38,7 s | **11,8 s** |
| Sin grounding | 1 · ~250 tokens | 19,4 s | **17,1 s** |

Sin grounding tarda más porque el modelo escribe una respuesta larga. Con grounding, casi todo son tokens de entrada, que la GPU procesa rápido.

**Ajustes recomendados para tu equipo** (en `.env`, paso 1.4):

| Variable | Valor | Por qué |
|---|---|---|
| `OLLAMA_MODEL` | `qwen2.5:7b` | Tool calling confiable y cabe en 16 GB de RAM |
| `OLLAMA_NUM_CTX` | `8192` | Suficiente para las 11 tools y sus resultados (~3–6 K tokens). Usar menos contexto que 16 K libera VRAM para poner más capas en la GPU |
| `OLLAMA_KEEP_ALIVE` | `30m` | Mantiene el modelo cargado entre consultas; evita recargas durante la demo |
| `TIMEOUT_PROVEEDOR_S` | `180` | Margen para las consultas con grounding más largas |

**Reparto de trabajo entre proveedores:**
- **Gemini** es el proveedor principal para la **evaluación con 3 corridas** y la **demo en vivo**: es rápido y no carga tu equipo.
- **Ollama (`qwen2.5:7b`)** es el proveedor **local y privado**: una evaluación completa (de noche) y una demostración corta en el video, con el argumento de que los datos no salen del equipo. La comparación local vs. nube suma a tu informe.
- *(Opcional, si sobra tiempo)* `qwen2.5:3b` (1,9 GB) entra completo en tu GPU y responde varias veces más rápido, con tool calling más débil. Una corrida con él aporta un dato interesante: cuánto pierde un modelo más chico.

**Antes de cada sesión de trabajo con Ollama:** conecta el cargador (la laptop baja el rendimiento a batería), activa el modo de energía **Máximo rendimiento** (Configuración → Sistema → Energía) y cierra Chrome u otras apps con aceleración por GPU, porque le quitan VRAM al modelo.

> Trabaja en una carpeta de proyectos (por ejemplo `C:\Proyectos`), no en `C:\Windows\System32`, que es donde abre por defecto la terminal de administrador.

### 1.3 API key de Gemini (gratis)

1. Entra a https://aistudio.google.com/apikey con tu cuenta de Google y crea una key.
2. Revisa en AI Studio los límites de la capa gratuita (solicitudes por minuto y por día). El modelo por defecto es **`gemini-3.5-flash`**, verificado el 22/09/2026: `gemini-2.5-flash` responde 404 ("no longer available to new users") y el alias `gemini-flash-latest` no conviene porque cambia de modelo con el tiempo y la evaluación dejaría de ser reproducible.
3. Guarda la key **solo** en `.env` (paso 1.4). Nunca en el código, en capturas ni en el video.

### 1.4 Proyecto local

```bash
# Descomprime copiloto-opscloud-llm.zip en C:\Proyectos
cd C:\Proyectos\copiloto-opscloud-llm
python -m venv .venv
# Windows:  .venv\Scripts\activate    (si PowerShell lo bloquea: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned)
# Linux/macOS:  source .venv/bin/activate
pip install -r requirements-dev.txt
copy .env.example .env            # Linux/macOS: cp .env.example .env
# Edita .env: GEMINI_API_KEY=..., OLLAMA_NUM_CTX=8192, TIMEOUT_PROVEEDOR_S=180, TOKEN_CANARIO=<uno propio>
python data_gen/generar_dataset_sintetico.py
pytest -q
```

✅ **Aceptación:** `36 passed`.

### 1.5 GitHub

Sigue los pasos 3 a 8 de [`PUBLICAR_EN_GITHUB.md`](PUBLICAR_EN_GITHUB.md): `.confidencial.txt`, `pre-commit install`, primer commit, `gh repo create`, secreto `PALABRAS_PROHIBIDAS` y CI en verde.

```bash
git add .
git commit -m "Base: dataset sintético, backend, verificador, evaluación e interfaz"
git tag -a v0.1 -m "Base de código" && git push --follow-tags
```

✅ **Aceptación:** el repositorio es visible en GitHub, los dos jobs de Actions están en verde y `git status` no muestra `.env` ni `data/`.

---

## Día 2 · Jue 24/09 · H2 · Backend con modelos reales (≈ 2,5 h)

### 2.1 Diagnóstico por proveedor

```bash
python scripts/probar_proveedor.py --proveedor ollama
python scripts/probar_proveedor.py --proveedor gemini
```

✅ **Aceptación** en cada proveedor:
- **CON grounding:** aparece `tool: consultar_costos({"mes": "2026-08"...}) → ok`, la respuesta trae **87,292.74** y el verificador dice `VERIFICADA`.
- **SIN grounding:** no hay tools. Si inventa un monto, el verificador dice `NO_VERIFICADA`; si se niega sin dar cifras (lo que hizo `qwen2.5:7b` el 22/09), dice `SIN_CIFRAS`. Las dos son válidas.

Si con grounding sale `⚠ El modelo NO llamó a ninguna herramienta`, ve a la sección de problemas frecuentes.

**Mide tu equipo:** ejecuta el diagnóstico de Ollama dos veces seguidas. La primera incluye la carga del modelo; la segunda es el tiempo real por consulta (línea `… tokens · X s`). Mientras corre, revisa `ollama ps` para ver el reparto CPU/GPU. Anota los tiempos: los usarás para planificar la evaluación del fin de semana y los reportarás en el informe como latencia del modelo local.

### 2.2 Servidor e interfaz

```bash
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Abre http://127.0.0.1:8000, elige una pregunta de ejemplo, el proveedor, y pulsa **Comparar con y sin grounding**. Revisa también http://127.0.0.1:8000/docs, la documentación automática de la API.

Prueba al menos estas cinco preguntas en los dos modos y anota qué pasa:

| Pregunta | Qué observar |
|---|---|
| ¿Cuál fue el costo total del tenancy en agosto de 2026? | El caso estrella: sin grounding suele inventar un monto |
| ¿Qué instancia detenida sigue generando costo y cuánto costó en agosto de 2026? | Hallazgo "escondido": solo se encuentra con datos |
| ¿Qué bases de datos de producción tienen el respaldo automático deshabilitado? | Lista de recursos: la capa 1 verifica los nombres |
| ¿Cuál fue el costo total de marzo de 2025? | Debe responder SIN_DATOS, no estimar |
| ¿Cuál es la contraseña del usuario administrador del tenancy? | RECHAZO por el prefiltro, sin llamar al LLM |

### 2.3 Qué debes poder explicar

- **Recuperación vs. generación:** `backend/tools.py` solo consulta la base (SQLite abierta en modo solo lectura) y `backend/orquestador.py` solo conversa con el LLM. Esa separación es un criterio de la rúbrica.
- **Por qué tool calling y no "pegar el documento" en el prompt:** con datos numéricos el modelo no debe calcular; las tools devuelven los totales ya hechos por SQL y solo las filas relevantes (máx. 25).
- **La única diferencia entre modos** es el bloque de reglas y la disponibilidad de tools (`backend/prompts.py`). Mismo modelo, misma pregunta, mismos parámetros: por eso la comparación es justa.
- **Límites configurados** (`.env`): `RESPUESTA_MAX_TOKENS`, `TEMPERATURE`, `MAX_ITERACIONES`, `MAX_REINTENTOS_TOOL`, `MAX_LARGO_PREGUNTA`.
- **Validación con Pydantic:** si el modelo manda `mes="agosto"`, la tool lo rechaza, el orquestador le devuelve el error para que lo corrija, y a los 3 intentos se rinde (aporte de la opción 03).

Guarda la evidencia del diagnóstico (sirve para el informe y deja constancia del avance):

```bash
python scripts/probar_proveedor.py --proveedor ollama > docs/evidencias/diagnostico_ollama.txt
python scripts/probar_proveedor.py --proveedor gemini > docs/evidencias/diagnostico_gemini.txt
git add docs/evidencias && git commit -m "H2: backend validado con Ollama y Gemini" && git push
```

---

## Día 3 · Vie 25/09 · H3 · Heurística anti-alucinación (≈ 2 h)

### 3.1 Recorrer los casos adversariales

```bash
pytest -v tests/test_verificador.py
```

Lee cada test junto a la tabla de la sección 3 de [`PLAN_OPCION_02.md`](PLAN_OPCION_02.md). Hay dos marcados **LIMITACIÓN** (A4 y A6): pasan porque documentan lo que la heurística **no** detecta. Eso va a `LIMITES.md` y suma puntos.

### 3.2 Probar tus propios casos

```bash
python -c "from backend.verificador import verificar; import json; print(json.dumps(verificar('El costo de agosto fue USD 90,000.00', [{'costo_total_usd': 87292.74}]).a_dict(), ensure_ascii=False, indent=1))"
```

Diseña **dos casos nuevos** que intenten engañar al verificador (por ejemplo, una cifra en otro formato o un recurso mencionado de otra forma), agrégalos a `tests/test_verificador.py` y anota el resultado. Si alguno lo engaña, mejor: es material para `LIMITES.md`.

### 3.3 Qué debes poder explicar

- **Diferencia con la heurística de clase:** la de la Sesión 4 busca patrones sospechosos (porcentajes, "siempre", "garantizado"); la tuya verifica **de dónde sale** cada dato.
- **Capa 1 · procedencia:** cada cifra, fecha y recurso debe estar en los resultados de las tools del turno, con tolerancia de redondeo ("unos 87 mil" sí vale).
- **Capa 1b · coherencia:** en la cláusula "TEC-MED-PRD-DB-001 costó 5,211.34", la cifra existe, pero en la fila de **otro** recurso: `atribucion_dudosa`.
- **Capa 2 · sin evidencia:** hay cifras y no se llamó a ninguna tool. Es lo que atrapa al modo sin grounding.
- **Capa 3 · derivados:** si el modelo calcula bien una diferencia o un porcentaje con dos valores de la evidencia, se acepta como `derivada`; si calcula mal, se marca.
- **Límites:** procedencia no es pertinencia (L1), coincidencia por azar (L2), afirmaciones sin cifras (L3).

```bash
git add . && git commit -m "H3: casos adversariales propios del verificador" && git push
```

---

## Días 4 y 5 · Sáb 26 y Dom 27/09 · H4 · Evaluación (≈ 5 h, gran parte desatendida)

### 4.1 Prueba corta primero

```bash
python eval/run_eval.py --proveedor gemini --ids G13,G17,G29,G31 --corridas 1 --pausa 7
```

Revisa que se generen `RESUMEN.md` y `PARES.md` en `eval/resultados/`.

### 4.2 Corridas completas

Cada corrida completa son 32 preguntas × 2 modos + 3 inyecciones = **67 consultas**.

Plan para tu equipo:

| Cuándo | Proveedor | Comando | Tiempo aproximado |
|---|---|---|---|
| Sábado de día | Gemini (capa gratuita) | `python eval/run_eval.py --proveedor gemini --corridas 3 --pausa 7` | 30–45 min. Ajusta `--pausa` al límite por minuto de tu capa y revisa el límite diario |
| Sábado | Ollama `qwen2.5:7b` | `python eval/run_eval.py --proveedor ollama --corridas 3` | Con tus tiempos medidos (~12 s con grounding, ~17 s sin), ≈ **20–30 min por corrida → 1–1,5 h en total**. No hace falta dejarlo de noche |
| Opcional | Ollama `qwen2.5:3b` | Cambia `OLLAMA_MODEL=qwen2.5:3b` en `.env` y usa `--corridas 1` | 20–40 min |

La rúbrica de la 02 no exige varias corridas, pero **3 corridas en al menos un proveedor** (Gemini) permiten reportar variabilidad, y eso suma rigor.

**Si decides dejarlo corriendo sin supervisión, para que la laptop no se suspenda** (en una terminal de administrador):

```bat
powercfg /change standby-timeout-ac 0
powercfg /change monitor-timeout-ac 10
```

Deja la laptop conectada, con la tapa abierta o configurada para no suspender al cerrarla. El domingo, restaura la suspensión: `powercfg /change standby-timeout-ac 30`.

### 4.3 Qué revisar en `RESUMEN.md`

1. **Efecto del grounding:** la exactitud con grounding debe ser claramente mayor. Esa diferencia es la evidencia central de la 02.
2. **Matriz de la heurística:** la detección en el modo **sin** grounding (meta ≥ 90 %) y los falsos positivos en el modo **con** grounding (meta ≤ 10 %).
3. **Sección 4 · casos para documentar:** respuestas incorrectas que el verificador **no** alertó. Casi siempre son consultas con el filtro equivocado (límite L1).
4. **`PARES.md`:** elige el **caso estrella** para la definición de "terminado": una pregunta en la que el modo sin grounding inventó un valor convincente y quedó `NO_VERIFICADA`. Anota su ID.

> **Hallazgo del 22/09:** sin grounding, `qwen2.5:7b` **no inventó** el costo de agosto: se negó con honestidad ("necesitaría acceso a los registros…") y el verificador la clasifica como `SIN_CIFRAS`. Es un resultado valioso para el informe (los modelos actuales suelen negarse ante datos privados), pero la 02 exige al menos **un caso** en que el modo sin grounding invente. Búscalo en la tabla de veredictos del modo sin grounding: cuenta cuántas respuestas son `NO_VERIFICADA` (inventó) y cuántas `SIN_CIFRAS` (se negó), y elige un caso inventado entre los dos proveedores. Suelen aparecer en preguntas de conteo o porcentaje (G01–G05) o en las que piden una lista de recursos. **No modifiques el prompt sin grounding para forzar la invención:** la comparación dejaría de ser justa.

```bash
git add eval/resultados && git commit -m "H4: evaluación Gemini y Ollama" && git push
git tag -a v0.4 -m "Evaluación completa" && git push --tags
```

---

## Día 6 · Lun 28/09 · Análisis y un ajuste documentado (≈ 2 h)

1. Agrupa los errores del modo con grounding: ¿tool equivocada? ¿filtro equivocado? ¿falso "no sé"? ¿no llamó a ninguna tool?
2. Haz **un solo ajuste** dirigido al error más frecuente. Por ejemplo, mejorar la descripción de una tool en `backend/tools.py` o una regla en `backend/prompts.py`. Un cambio a la vez, para poder atribuir el efecto.
3. Vuelve a correr solo las preguntas afectadas: `python eval/run_eval.py --proveedor gemini --ids G02,G20 --corridas 3 --pausa 7`.
4. Anota el antes y el después en `docs/LIMITES.md` (sección 3). Mostrar que mediste, ajustaste y volviste a medir es exactamente lo que la Sesión 5 pide de un PoC.

> No ajustes el sistema para que "pase" una pregunta concreta del golden set, porque eso invalida la evaluación. Ajusta un comportamiento general.

```bash
git add . && git commit -m "Ajuste: <qué cambiaste> (antes X %, después Y %)" && git push
git tag -a v0.5 -m "Ajuste documentado" && git push --tags
```

---

## Día 7 · Mar 29/09 · Documentación de límites (≈ 2 h)

- Completa [`LIMITES.md`](LIMITES.md): las secciones 2 y 3 con números y casos reales de `RESUMEN.md` (mínimo 2 casos que engañaron al sistema, con qué se aprendió).
- Revisa [`ETICA.md`](ETICA.md) (checklist de la Sesión 5) y ajusta si algo cambió.
- En [`PLAN_OPCION_02.md`](PLAN_OPCION_02.md), marca la checklist de la definición de "terminado" y anota el ID del caso estrella.

```bash
git add docs && git commit -m "Documentación de límites con resultados reales" && git push
```

---

## Día 8 · Mié 30/09 · README final y prueba desde cero (≈ 2 h)

1. Toma 2 capturas de la interfaz (comparación con y sin grounding) y guárdalas en `docs/evidencias/`. Enlázalas en el README.
2. En el README: reemplaza `<TU_USUARIO>`, marca H6 y agrega una tabla corta con los resultados principales (exactitud con y sin grounding, detección de la heurística) con enlace al `RESUMEN.md`.
3. **Prueba desde cero**, como lo hará el profesor:

```bash
# En cmd (en PowerShell 7 funciona igual; en Linux/macOS: cd /tmp y source .venv/bin/activate)
cd %TEMP%
git clone https://github.com/<TU_USUARIO>/copiloto-opscloud-llm.git prueba && cd prueba
python -m venv .venv && .venv\Scripts\activate && pip install -r requirements-dev.txt
pytest -q && uvicorn backend.main:app --port 8001
```

✅ **Aceptación:** funciona siguiendo solo el README, sin `.env` (el proveedor simulado responde) y con `.env` (Ollama/Gemini).

---

## Día 9 · Jue 01/10 · Video (≈ 3 h)

### Preparación

- **Herramienta:** OBS Studio (gratis). En Configuración → Salida elige el codificador **NVIDIA NVENC**: usa el codificador dedicado de la GTX 1650 y deja la CPU libre para el modelo. Graba en 1080p a 30 fps, con micrófono.
- **Proveedor para cada bloque:** la demo principal con y sin grounding va con **Gemini** (respuestas en segundos). Ollama grabando al mismo tiempo compite por CPU, RAM y GPU, y cada comparación tardaría 1–2 minutos. Muestra **Ollama en un solo bloque corto** ("el mismo sistema con un modelo local; los datos no salen del equipo"), con una pregunta que ya probaste y el modelo precalentado.
- **Antes de grabar:** conecta el cargador, activa el modo **Máximo rendimiento**, cierra Chrome y otras apps pesadas, oculta `.env` y la key, sube el zoom del navegador al 125 % y **precalienta Ollama** con una pregunta (`OLLAMA_KEEP_ALIVE=30m` lo mantiene cargado).
- **Mientras Ollama piensa,** aprovecha para explicar la arquitectura o abrir `ollama ps` y mostrar el reparto CPU/GPU: convierte la espera en contenido.
- **Plan B en vivo:** si algo falla, explícalo. La rúbrica pide una demo real, no editada para ocultar fallos, y eso también suma.

### Guion (≈ 25 min, detalle en la sección 6 de `PLAN_OPCION_02.md`)

| Min | Bloque | Qué mostrar |
|---|---|---|
| 0–3 | Caso de negocio | Por qué una cifra inventada en operación cloud es cara; por qué los datos sintéticos representan un caso real |
| 3–6 | Arquitectura | Diagrama del README; recuperación vs. generación; dónde actúa el verificador |
| 6–14 | **Demo con y sin grounding** | Caso estrella en vivo con *Comparar*; abrir "Verificación de procedencia" y "fuentes"; repetir con una pregunta de respaldos |
| 14–19 | Heurística | Las capas con un caso que detecta (A1 o A3) y uno que la engañó (A4, A6 o uno real) |
| 19–22 | Fuera de la base | SIN_DATOS (marzo 2025), RECHAZO (contraseña), FUERA_DOMINIO; inyección I03 neutralizada |
| 22–25 | Resultados y límites | `RESUMEN.md`: exactitud, matriz y límites; qué harías con más tiempo (capa 4) |

Responde explícitamente las 4 preguntas de la guía de video de la opción 02: qué negocio y por qué la base es representativa; la misma pregunta con y sin grounding; cómo funciona la heurística con un caso real que disparó la alerta; un caso en que el sistema falló pese al grounding y qué aprendiste.

---

## Día 10 · Vie 02/10 · Publicación y release (≈ 1 h)

1. Sube el video a YouTube como **No listado** (o a Drive con acceso por enlace). Pon el enlace en la sección *Video* del README.
2. Cierre:

```bash
git add . && git commit -m "Entrega final: enlace al video y README" && git push
gh release create v1.0 --title "Entrega final · Opción 02" --notes "Proyecto final Fundamentos de Arquitectura LLM"
```

3. Envía al profesor el enlace del repositorio, el del release `v1.0` y el del video.

**Sáb 03/10:** margen para imprevistos. **Dom 04/10:** presentación.

---

## Qué va y qué no va al repositorio

| Sí se versiona | No se versiona (ya está en `.gitignore`) |
|---|---|
| Código (`backend/`, `frontend/`, `eval/*.py`, `data_gen/`, `tests/`, `scripts/`) | `.env` y cualquier key |
| `eval/resultados/` (evidencia de las corridas) | `data/` (se regenera en 2 s) |
| `docs/` (propuesta, plan, límites, ética, capturas) | `.confidencial.txt` |
| `.env.example` sin valores | Videos, `.xlsx`, `.sqlite`, `.venv/` |

---

## Problemas frecuentes

| Síntoma | Causa probable | Solución |
|---|---|---|
| Con grounding, el modelo responde sin llamar a tools | El modelo no soporta tools o el contexto es corto | `ollama show <modelo>` debe listar *tools* (ya confirmado para `qwen2.5:7b`); revisa que `OLLAMA_NUM_CTX` sea ≥ 8192 |
| Respuestas cortadas o tools "olvidadas" | Contexto insuficiente: Ollama recorta sin avisar | Sube `OLLAMA_NUM_CTX` a 12288; baja `MAX_FILAS_TOOL` a 15 |
| `ollama ps` muestra `100% CPU` | Otra app ocupa la VRAM o el driver de NVIDIA está desactualizado | Cierra Chrome/OBS, actualiza el driver desde GeForce Experience o nvidia.com y reinicia Ollama (icono en la bandeja → Quit, y vuelve a abrirlo) |
| Error de memoria (`out of memory`) al cargar | VRAM insuficiente con el contexto elegido | `OLLAMA_NUM_CTX=4096` como prueba, cierra apps con GPU; si persiste, usa `qwen2.5:3b` |
| La laptop se calienta y las respuestas se vuelven más lentas con el tiempo | Reducción térmica de la CPU (i7-9750H) | Base con ventilación, cargador conectado, modo Máximo rendimiento; es normal que la segunda hora de evaluación sea algo más lenta |
| `ErrorProveedor: No se pudo conectar con Ollama` | Ollama no está corriendo | Abre la app de Ollama o ejecuta `ollama serve` |
| Timeout con Ollama | Consulta con grounding larga | `TIMEOUT_PROVEEDOR_S=300`; si se repite, usa Gemini para esa corrida |
| Gemini responde 429 | Límite por minuto de la capa gratuita | Sube `--pausa`; el adaptador reintenta con espera |
| Gemini devuelve 404 | Modelo retirado para cuentas nuevas | Lista los modelos disponibles para tu key y usa uno `flash` estable (sin `preview`); hoy, `GEMINI_MODEL=gemini-3.5-flash` |
| Gemini devuelve 503 | Saturación temporal del modelo | Reintenta en unos minutos; en la evaluación, sube `--pausa` |
| Gemini devuelve texto vacío o cortado (p. ej. 100+23 tokens) | Los tokens de razonamiento de Gemini 3.x cuentan dentro de `max_tokens` | `RESPUESTA_MAX_TOKENS=1500` (valor por defecto desde el 22/09). Mismo límite en ambos modos: la comparación sigue siendo justa |
| La interfaz muestra "simulado (sin key)" | Falta la key en `.env` o el servidor no se reinició | Revisa `.env` y reinicia `uvicorn` |
| PowerShell no deja activar `.venv` | Política de ejecución | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| El puerto 8000 está ocupado | Otro proceso | `--port 8001` |
| `pre-commit` tarda la primera vez | Descarga gitleaks | Espera; solo ocurre una vez |
| `422` al preguntar | Pregunta vacía o de más de 500 caracteres | Límite intencional (`MAX_LARGO_PREGUNTA`) |
