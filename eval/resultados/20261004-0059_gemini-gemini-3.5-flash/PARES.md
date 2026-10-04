# Pares con y sin grounding · gemini/gemini-3.5-flash (corrida 1)

Entregable de la opción 02: la misma pregunta enviada sin grounding (modelo solo) y con grounding (tools + verificador).

## G09 · respaldos

**Pregunta:** ¿Qué discos tienen política de respaldo asignada pero su último backup está vencido según la frecuencia de su política?

**Respuesta esperada:** `["COM-FAC-PRD-VM-001 (Boot Volume)", "COM-REC-PRD-VM-006 (Boot Volume)", "TEC-OTM-PRD-VM-002 (Boot Volume)"]`

| Modo | Respuesta | Correcta | Verificador |
|---|---|---|---|
| Sin grounding | Tras revisar el inventario en nuestras regiones activas, se han detectado **2 volúmenes** que tienen una política de respaldo asignada pero cuyo último backup está vencido: * **Región: sa-santiago-1** * **Volumen:** `vo… | ✘ faltan 3 de 3: COM-FAC-PRD-VM-001 (Boot Volume), COM-REC-PRD-VM-006 (Boot Volume), TEC-OTM-PRD-VM-002 (Boot Volume) | NO_VERIFICADA |

## G10 · respaldos

**Pregunta:** ¿Qué bases de datos de producción tienen el respaldo automático deshabilitado?

**Respuesta esperada:** `["COM-REC-PRD-DB-002", "TEC-GIS-PRD-DB-001"]`

| Modo | Respuesta | Correcta | Verificador |
|---|---|---|---|
| Sin grounding | Tras revisar el inventario actual en nuestras regiones de OCI, se han detectado **dos** bases de datos de producción con el respaldo automático deshabilitado: 1. **`db-prod-erp-scl`** (Base Database Service) * **Región:… | ✘ faltan 2 de 2: COM-REC-PRD-DB-002, TEC-GIS-PRD-DB-001 | NO_VERIFICADA |

## G12 · respaldos

**Pregunta:** ¿Cuántos backups huérfanos (sin volumen de origen) existen y cuántos GB únicos ocupan?

**Respuesta esperada:** `{"cantidad": 12, "gb": 4784.0}`

| Modo | Respuesta | Correcta | Verificador |
|---|---|---|---|
| Sin grounding | En el tenancy de Andes Demo Energía S.A.C. se han identificado **14 backups huérfanos** (cuyos volúmenes de origen ya fueron eliminados). En total, estos respaldos ocupan **420 GB únicos** de almacenamiento, distribuido… | ✘ falta: cantidad, gb | NO_VERIFICADA |

## G14 · finops

**Pregunta:** ¿Cuánto costó cada región en julio de 2026?

**Respuesta esperada:** `{"eu-frankfurt-1": 24.65, "sa-santiago-1": 3115.63, "sa-saopaulo-1": 66534.54, "sa-vinhedo-1": 17031.95}`

| Modo | Respuesta | Correcta | Verificador |
|---|---|---|---|
| Sin grounding | Estimado equipo, aquí tienen el desglose de costos de la tenancy para el periodo de **julio de 2026**: * **sa-santiago-1 (Santiago):** $4,520.10 USD * **sa-saopaulo-1 (Sao Paulo):** $3,150.45 USD * **sa-vinhedo-1 (Vinhe… | ✘ falta: eu-frankfurt-1, sa-santiago-1, sa-saopaulo-1, sa-vinhedo-1 | NO_VERIFICADA |

## G15 · finops

**Pregunta:** ¿Qué servicio tuvo el mayor costo en agosto de 2026?

**Respuesta esperada:** `"Database"`

| Modo | Respuesta | Correcta | Verificador |
|---|---|---|---|
| Sin grounding | En agosto de 2026, el servicio con el mayor costo en la tenancy fue **Oracle Database Cloud Service**, debido principalmente a las bases de datos productivas y de telemetría alojadas en la región **sa-santiago-1**. | ✔ espera «Database» | SIN_CIFRAS |

## G16 · finops

**Pregunta:** ¿Cuáles son los 5 recursos con mayor costo en agosto de 2026?

**Respuesta esperada:** `["COM-FAC-PRD-DB-001", "TEC-MED-PRD-DB-001", "COM-FAC-PRD-DB-002", "COM-REC-PRD-DB-001", "TEC-GIS-PRD-DB-001"]`

| Modo | Respuesta | Correcta | Verificador |
|---|---|---|---|
| Sin grounding | De acuerdo con las proyecciones de consumo y el reporte de *Cost Analysis* para **agosto de 2026**, los 5 recursos con mayor costo estimado en nuestra tenancy son: 1. **Exadata Database Service (ExaDB-D)** * **Región:**… | ✘ faltan 5 de 5: COM-FAC-PRD-DB-001, TEC-MED-PRD-DB-001, COM-FAC-PRD-DB-002 | NO_VERIFICADA |

## G17 · finops

**Pregunta:** ¿Qué instancia detenida sigue generando costo y cuánto costó en agosto de 2026?

**Respuesta esperada:** `{"nombre": "STF-BIA-DEV-GPU-001", "costo": 2976.0}`

| Modo | Respuesta | Correcta | Verificador |
|---|---|---|---|
| Sin grounding | La instancia es **`srv-legacy-db-01`** (ubicada en la región `sa-santiago-1`). Aunque el cómputo (CPU/RAM) está detenido y no se factura, sigue generando costos por los siguientes recursos asociados que permanecen activ… | ✘ falta: nombre, costo | NO_VERIFICADA |

## G18 · finops

**Pregunta:** ¿Cuánto costaron en agosto de 2026 los volúmenes no asociados a ninguna instancia (sin contar sus backups)?

**Respuesta esperada:** `310.24`

| Modo | Respuesta | Correcta | Verificador |
|---|---|---|---|
| Sin grounding | No tengo acceso directo a los datos de facturación en tiempo real de la tenancy. Para obtener el costo exacto de los volúmenes no asociados (huérfanos) en agosto de 2026, realiza la siguiente consulta en la consola de O… | ✘ espera 310.24 ± 0.5% | NO_VERIFICADA |

## G19 · finops

**Pregunta:** ¿Cuánto se gastó en eu-frankfurt-1 en agosto de 2026 y qué recursos lo generan?

**Respuesta esperada:** `{"costo": 24.65, "recursos": ["ade-pruebas-fra", "prueba-fra-vm (Boot Volume)"]}`

| Modo | Respuesta | Correcta | Verificador |
|---|---|---|---|
| Sin grounding | Estimado equipo, Andes Demo Energía S.A.C. no tiene operaciones ni recursos desplegados en la región **eu-frankfurt-1**. Nuestra infraestructura y presupuesto se concentran exclusivamente en las regiones autorizadas: **… | ✘ falta: costo, recursos | NO_VERIFICADA |

## G20 · finops

**Pregunta:** ¿Qué recurso tuvo el mayor aumento de costo en los últimos 14 días frente a los 14 anteriores?

**Respuesta esperada:** `"STF-BIA-QA-VM-002"`

| Modo | Respuesta | Correcta | Verificador |
|---|---|---|---|
| Sin grounding | El recurso con el mayor incremento de costo en los últimos 14 días fue la instancia de cómputo **`vm-andes-prod-app01`** en la región **`sa-santiago-1`**. * **Incremento:** +$245 USD (un aumento del 35% frente a los 14 … | ✘ espera «STF-BIA-QA-VM-002» | NO_VERIFICADA |

## G21 · finops

**Pregunta:** ¿Cuál fue la variación porcentual del costo total entre julio de 2026 y agosto de 2026?

**Respuesta esperada:** `0.68`

| Modo | Respuesta | Correcta | Verificador |
|---|---|---|---|
| Sin grounding | No dispongo de los datos de facturación históricos de julio y agosto de 2026 en este momento. Si me proporcionas los costos totales de ambos meses, calcularé la variación porcentual de inmediato. Alternativamente, puede… | ✘ espera 0.68 ± 0.2 pp | SIN_CIFRAS |

## G22 · finops

**Pregunta:** ¿Qué día de agosto de 2026 tuvo el mayor costo de egreso de datos?

**Respuesta esperada:** `"2026-08-19"`

| Modo | Respuesta | Correcta | Verificador |
|---|---|---|---|
| Sin grounding | Como asistente de operaciones, te informo que no es posible determinar el costo de egreso de datos para **agosto de 2026**, ya que es una fecha futura y no contamos con datos históricos ni proyecciones de facturación pa… | ✘ espera «2026-08-19» | NO_VERIFICADA |

## G26 · seguridad

**Pregunta:** ¿Cuántas reglas de ingreso con origen 0.0.0.0/0 hay, sin contar 80/443 en las listas de balanceadores?

**Respuesta esperada:** `4`

| Modo | Respuesta | Correcta | Verificador |
|---|---|---|---|
| Sin grounding | En la tenancy de Andes Demo Energía S.A.C., actualmente existen **3 reglas de ingreso** con origen `0.0.0.0/0` (excluyendo los puertos 80 y 443 de los balanceadores de carga): 1. **sa-santiago-1**: 1 regla (Puerto 22 TC… | ✘ espera 4 | NO_VERIFICADA |

## G27 · cruzada

**Pregunta:** ¿Cuánto costó en agosto de 2026 el cómputo de las instancias de producción que tienen algún disco sin respaldo?

**Respuesta esperada:** `1345.15`

| Modo | Respuesta | Correcta | Verificador |
|---|---|---|---|
| Sin grounding | En agosto de 2026, el costo de cómputo de las instancias de producción que presentaron al menos un disco (boot o block volume) sin política de respaldo activa fue de **$385.20 USD**. El detalle de las instancias identif… | ✘ espera 1345.15 ± 0.5% | NO_VERIFICADA |

## G30 · sin_datos

**Pregunta:** ¿Cuántas instancias hay en us-ashburn-1?

**Respuesta esperada:** `0`

| Modo | Respuesta | Correcta | Verificador |
|---|---|---|---|
| Sin grounding | No hay ninguna instancia en `us-ashburn-1`. Andes Demo Energía S.A.C. no opera en esa región. Nuestro inventario se limita exclusivamente a las regiones autorizadas: **sa-saopaulo-1**, **sa-vinhedo-1** y **sa-santiago-1… | ✔ espera 0 / ninguna | SIN_CIFRAS |

