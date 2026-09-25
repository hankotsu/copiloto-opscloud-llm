# Pares con y sin grounding · gemini/gemini-3.5-flash (corrida 1)

Entregable de la opción 02: la misma pregunta enviada sin grounding (modelo solo) y con grounding (tools + verificador).

## G01 · inventario

**Pregunta:** ¿Cuántas instancias de cómputo hay en total en el tenancy?

**Respuesta esperada:** `120`

| Modo | Respuesta | Correcta | Verificador |
|---|---|---|---|
| Sin grounding | Actualmente, el tenancy de Andes Demo Energía S.A.C. cuenta con un total de **16 instancias de cómputo** activas, distribuidas de la siguiente manera: * **sa-santiago-1 (Santiago):** 8 instancias (Producción y Core). * … | ✘ espera 120 | NO_VERIFICADA |

## G02 · inventario

**Pregunta:** ¿Cuántas instancias están en estado RUNNING en sa-saopaulo-1?

**Respuesta esperada:** `74`

| Modo | Respuesta | Correcta | Verificador |
|---|---|---|---|
| Sin grounding | En la región **sa-saopaulo-1**, actualmente tenemos **8 instancias** de cómputo en estado **RUNNING**. | ✘ espera 74 | NO_VERIFICADA |

## G03 · inventario

**Pregunta:** ¿Cuántas OCPUs suman las instancias RUNNING de producción?

**Respuesta esperada:** `390`

| Modo | Respuesta | Correcta | Verificador |
|---|---|---|---|
| Sin grounding | Actualmente, las instancias en estado **RUNNING** en el compartimento de Producción suman un total de **24 OCPUs**, distribuidas de la siguiente manera: * **sa-santiago-1 (Producción Principal):** 16 OCPUs (4 instancias… | ✘ espera 390 | NO_VERIFICADA |

## G04 · inventario

**Pregunta:** ¿Qué porcentaje de instancias tiene completo el etiquetado obligatorio?

**Respuesta esperada:** `89.2`

| Modo | Respuesta | Correcta | Verificador |
|---|---|---|---|
| Sin grounding | Actualmente, el **85%** de las instancias de cómputo en las tres regiones (`sa-santiago-1`, `sa-saopaulo-1` y `sa-vinhedo-1`) cuenta con el etiquetado obligatorio completo (tags: `Proyecto`, `Entorno` y `Propietario`). … | ✘ espera 89.2 ± 0.5% | NO_VERIFICADA |

## G05 · inventario

**Pregunta:** ¿Cuántas instancias Windows hay en producción?

**Respuesta esperada:** `19`

| Modo | Respuesta | Correcta | Verificador |
|---|---|---|---|
| Sin grounding | Actualmente tenemos **3 instancias Windows** activas en el compartimento de producción (`PROD`): * **2 en sa-santiago-1** (AD-Secondary y APP-Win01) * **1 en sa-saopaulo-1** (AD-Primary) * **0 en sa-vinhedo-1** | ✘ espera 19 | NO_VERIFICADA |

## G07 · respaldos

**Pregunta:** ¿Cuántos discos asociados a instancias de producción no tienen ningún respaldo?

**Respuesta esperada:** `9`

| Modo | Respuesta | Correcta | Verificador |
|---|---|---|---|
| Sin grounding | Tras revisar el inventario actual en las tres regiones de operación, se identificaron **3 discos (volúmenes)** asociados a instancias de producción que no cuentan con ninguna política de respaldo (backup) activa: * **sa… | ✘ espera 9 | NO_VERIFICADA |

## G12 · respaldos

**Pregunta:** ¿Cuántos backups huérfanos (sin volumen de origen) existen y cuántos GB únicos ocupan?

**Respuesta esperada:** `{"cantidad": 12, "gb": 4784.0}`

| Modo | Respuesta | Correcta | Verificador |
|---|---|---|---|
| Sin grounding | _(sin respuesta: error del proveedor: gemini respondió 503)_ | — excluida de las métricas | ERROR |

## G14 · finops

**Pregunta:** ¿Cuánto costó cada región en julio de 2026?

**Respuesta esperada:** `{"eu-frankfurt-1": 24.65, "sa-santiago-1": 3115.63, "sa-saopaulo-1": 66534.54, "sa-vinhedo-1": 17031.95}`

| Modo | Respuesta | Correcta | Verificador |
|---|---|---|---|
| Sin grounding | _(sin respuesta: error del proveedor: gemini respondió 503)_ | — excluida de las métricas | ERROR |

## G15 · finops

**Pregunta:** ¿Qué servicio tuvo el mayor costo en agosto de 2026?

**Respuesta esperada:** `"Database"`

| Modo | Respuesta | Correcta | Verificador |
|---|---|---|---|
| Sin grounding | _(sin respuesta: error del proveedor: gemini respondió 429: cuota diaria agotada (se reinicia a medianoche del Pacífico))_ | — excluida de las métricas | ERROR |

## G16 · finops

**Pregunta:** ¿Cuáles son los 5 recursos con mayor costo en agosto de 2026?

**Respuesta esperada:** `["COM-FAC-PRD-DB-001", "TEC-MED-PRD-DB-001", "COM-FAC-PRD-DB-002", "COM-REC-PRD-DB-001", "TEC-GIS-PRD-DB-001"]`

| Modo | Respuesta | Correcta | Verificador |
|---|---|---|---|

## G17 · finops

**Pregunta:** ¿Qué instancia detenida sigue generando costo y cuánto costó en agosto de 2026?

**Respuesta esperada:** `{"nombre": "STF-BIA-DEV-GPU-001", "costo": 2976.0}`

| Modo | Respuesta | Correcta | Verificador |
|---|---|---|---|

## G21 · finops

**Pregunta:** ¿Cuál fue la variación porcentual del costo total entre julio de 2026 y agosto de 2026?

**Respuesta esperada:** `0.68`

| Modo | Respuesta | Correcta | Verificador |
|---|---|---|---|

