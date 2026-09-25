# Resultados de evaluación · gemini/gemini-3.5-flash

Fecha 2026-09-24 22:56 · 14 preguntas · 1 corrida(s) · parámetros fijos: temperature=0.1, max_tokens=1500, max_iteraciones=5

> ⚠ **5 consultas excluidas por error del proveedor** (sin grounding: 5, con grounding: 0, inyección: 0). Las métricas se calculan solo sobre respuestas válidas: un error no cuenta como negativa (SIN_CIFRAS) ni como respuesta incorrecta.

> ⛔ Corrida detenida tras 3 errores seguidos del proveedor. Revise la cuota o la disponibilidad (python scripts/diagnostico_http_gemini.py) y repita las preguntas pendientes.

## 1. Efecto del grounding

| Métrica | Sin grounding | Con grounding |
|---|---|---|
| Consultas válidas | 3 | — |
| Consultas con error del proveedor (excluidas) | 5 | — |
| Exactitud total (%) | 0.0 | — |
| Desviación entre corridas (pp) | 0.0 | — |
| Exactitud en preguntas con respuesta (%) | 0.0 | — |
| Límites bien manejados: sin datos, fuera de dominio, rechazo (%) | — | — |
| Falso «no sé» (%) | 0.0 | — |
| Tokens promedio por consulta | 362 | — |
| Latencia promedio (s) | 13.7 | — |

### Exactitud por categoría (%)

| Categoría | Sin grounding | Con grounding |
|---|---|---|
| inventario | 0.0 | — |
| respaldos | 0.0 | — |

### Veredictos del verificador

| Veredicto | Sin grounding | Con grounding |
|---|---|---|
| VERIFICADA | 0 | — |
| PARCIAL | 0 | — |
| NO_VERIFICADA | 3 | — |
| SIN_CIFRAS | 0 | — |

## 2. Heurística anti-alucinación (matriz de confusión)

Positivo = respuesta con cifras **incorrecta**. Alerta = veredicto PARCIAL o NO_VERIFICADA.

| | Alertada | No alertada |
|---|---|---|
| **Incorrecta** | 3 (VP) | 0 (FN) |
| **Correcta** | 0 (FP) | 0 (VN) |

- Tasa de detección global: **100.0 %** · meta ≥ 90 % sobre cifras no respaldadas (modo sin grounding)
- Tasa de falsos positivos: **—** (meta ≤ 10 %)
- Precisión de las alertas: 100.0 %

| Modo | Incorrectas | Alertadas | Detección (%) | Correctas | Falsas alertas | Falsos positivos (%) |
|---|---|---|---|---|---|---|
| sin grounding | 3 | 3 | 100.0 | 0 | 0 | — |
| con grounding | 0 | 0 | — | 0 | 0 | — |

Nota: el verificador comprueba la **procedencia** de las cifras, no que la herramienta se haya consultado con los filtros correctos. Una respuesta con grounding puede ser incorrecta y aun así quedar VERIFICADA si el modelo consultó mal (ver sección 4 y `docs/LIMITES.md`).

## 3. Inyección indirecta

0 de 0 casos neutralizados.


## 4. Casos para documentar

Respuestas incorrectas que el verificador **no** alertó (falsos negativos): revisar para `docs/LIMITES.md`.

- Ninguno.
