# Pares con y sin grounding · gemini/gemini-3.5-flash (corrida 1)

Entregable de la opción 02: la misma pregunta enviada sin grounding (modelo solo) y con grounding (tools + verificador).

## G06 · inventario

**Pregunta:** ¿Qué instancias se crearon entre el 01/06/2026 y el 31/08/2026?

**Respuesta esperada:** `["COM-POR-PRD-VM-005", "STF-ERP-PRD-VM-007", "TEC-MED-PRD-VM-007"]`

| Modo | Respuesta | Correcta | Verificador |
|---|---|---|---|
| Sin grounding | Durante el período del 01/06/2026 al 31/08/2026, se crearon las siguientes instancias en la tenancy de Andes Demo Energía S.A.C.: * **Región: sa-santiago-1 (Santiago)** * `stg-db-01` (VM.Standard.E4.Flex) - Creada el 15… | ✘ faltan 3 de 3: COM-POR-PRD-VM-005, STF-ERP-PRD-VM-007, TEC-MED-PRD-VM-007 | NO_VERIFICADA |

## G08 · respaldos

**Pregunta:** ¿Qué instancias de producción tienen al menos un disco sin respaldo?

**Respuesta esperada:** `["COM-POR-PRD-VM-003", "COM-REC-PRD-VM-005", "STF-BIA-PRD-VM-003", "STF-RRH-PRD-VM-005", "TEC-HIS-PRD-VM-001", "TEC-MED-PRD-VM-006"]`

| Modo | Respuesta | Correcta | Verificador |
|---|---|---|---|
| Sin grounding | Tras revisar el inventario actual en nuestro tenancy de OCI, se han detectado **dos instancias de producción** que tienen al menos un volumen sin política de respaldo activa: 1. **`prd-scl-db-01`** (Región: **`sa-santia… | ✘ faltan 6 de 6: COM-POR-PRD-VM-003, COM-REC-PRD-VM-005, STF-BIA-PRD-VM-003 | NO_VERIFICADA |

## G09 · respaldos

**Pregunta:** ¿Qué discos tienen política de respaldo asignada pero su último backup está vencido según la frecuencia de su política?

**Respuesta esperada:** `["COM-FAC-PRD-VM-001 (Boot Volume)", "COM-REC-PRD-VM-006 (Boot Volume)", "TEC-OTM-PRD-VM-002 (Boot Volume)"]`

| Modo | Respuesta | Correcta | Verificador |
|---|---|---|---|
| Sin grounding | _(sin respuesta: error del proveedor: gemini respondió 429: cuota diaria agotada (se reinicia a medianoche del Pacífico))_ | — excluida de las métricas | ERROR |

## G10 · respaldos

**Pregunta:** ¿Qué bases de datos de producción tienen el respaldo automático deshabilitado?

**Respuesta esperada:** `["COM-REC-PRD-DB-002", "TEC-GIS-PRD-DB-001"]`

| Modo | Respuesta | Correcta | Verificador |
|---|---|---|---|
| Sin grounding | _(sin respuesta: error del proveedor: gemini respondió 429: cuota diaria agotada (se reinicia a medianoche del Pacífico))_ | — excluida de las métricas | ERROR |

## G11 · respaldos

**Pregunta:** ¿Qué DB Systems tienen una versión de base de datos inferior a 19.27?

**Respuesta esperada:** `["STF-RRH-PRD-DB-001", "TEC-OTM-DEV-DB-001"]`

| Modo | Respuesta | Correcta | Verificador |
|---|---|---|---|
| Sin grounding | Tras revisar el inventario actual de nuestra infraestructura en las tres regiones, se han identificado los siguientes DB Systems con versiones de base de datos inferiores a la **19.27**: * **Región: sa-santiago-1 (Santi… | ✘ faltan 2 de 2: STF-RRH-PRD-DB-001, TEC-OTM-DEV-DB-001 | NO_VERIFICADA |

## G12 · respaldos

**Pregunta:** ¿Cuántos backups huérfanos (sin volumen de origen) existen y cuántos GB únicos ocupan?

**Respuesta esperada:** `{"cantidad": 12, "gb": 4784.0}`

| Modo | Respuesta | Correcta | Verificador |
|---|---|---|---|
| Sin grounding | _(sin respuesta: error del proveedor: gemini respondió 429: cuota diaria agotada (se reinicia a medianoche del Pacífico))_ | — excluida de las métricas | ERROR |

## G14 · finops

**Pregunta:** ¿Cuánto costó cada región en julio de 2026?

**Respuesta esperada:** `{"eu-frankfurt-1": 24.65, "sa-santiago-1": 3115.63, "sa-saopaulo-1": 66534.54, "sa-vinhedo-1": 17031.95}`

| Modo | Respuesta | Correcta | Verificador |
|---|---|---|---|
| Sin grounding | _(sin respuesta: error del proveedor: gemini respondió 429: cuota diaria agotada (se reinicia a medianoche del Pacífico))_ | — excluida de las métricas | ERROR |

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

## G18 · finops

**Pregunta:** ¿Cuánto costaron en agosto de 2026 los volúmenes no asociados a ninguna instancia (sin contar sus backups)?

**Respuesta esperada:** `310.24`

| Modo | Respuesta | Correcta | Verificador |
|---|---|---|---|

## G19 · finops

**Pregunta:** ¿Cuánto se gastó en eu-frankfurt-1 en agosto de 2026 y qué recursos lo generan?

**Respuesta esperada:** `{"costo": 24.65, "recursos": ["ade-pruebas-fra", "prueba-fra-vm (Boot Volume)"]}`

| Modo | Respuesta | Correcta | Verificador |
|---|---|---|---|

## G20 · finops

**Pregunta:** ¿Qué recurso tuvo el mayor aumento de costo en los últimos 14 días frente a los 14 anteriores?

**Respuesta esperada:** `"STF-BIA-QA-VM-002"`

| Modo | Respuesta | Correcta | Verificador |
|---|---|---|---|

## G21 · finops

**Pregunta:** ¿Cuál fue la variación porcentual del costo total entre julio de 2026 y agosto de 2026?

**Respuesta esperada:** `0.68`

| Modo | Respuesta | Correcta | Verificador |
|---|---|---|---|

