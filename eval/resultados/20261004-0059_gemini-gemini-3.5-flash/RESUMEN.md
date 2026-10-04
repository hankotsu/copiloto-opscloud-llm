# Resultados de evaluación · gemini/gemini-3.5-flash

Fecha 2026-10-04 01:03 · 15 preguntas · 1 corrida(s) · parámetros fijos: temperature=0.1, max_tokens=1500, max_iteraciones=5

## 1. Efecto del grounding

| Métrica | Sin grounding | Con grounding |
|---|---|---|
| Consultas válidas | 15 | — |
| Consultas con error del proveedor (excluidas) | 0 | — |
| Exactitud total (%) | 13.3 | — |
| Desviación entre corridas (pp) | 0.0 | — |
| Exactitud en preguntas con respuesta (%) | 13.3 | — |
| Límites bien manejados: sin datos, fuera de dominio, rechazo (%) | — | — |
| Falso «no sé» (%) | 0.0 | — |
| Tokens promedio por consulta | 262 | — |
| Latencia promedio (s) | 7.53 | — |

### Exactitud por categoría (%)

| Categoría | Sin grounding | Con grounding |
|---|---|---|
| cruzada | 0.0 | — |
| finops | 11.1 | — |
| respaldos | 0.0 | — |
| seguridad | 0.0 | — |
| sin_datos | 100.0 | — |

### Veredictos del verificador

| Veredicto | Sin grounding | Con grounding |
|---|---|---|
| VERIFICADA | 0 | — |
| PARCIAL | 0 | — |
| NO_VERIFICADA | 12 | — |
| SIN_CIFRAS | 3 | — |

## 2. Heurística anti-alucinación (matriz de confusión)

Positivo = respuesta con cifras **incorrecta**. Alerta = veredicto PARCIAL o NO_VERIFICADA.

| | Alertada | No alertada |
|---|---|---|
| **Incorrecta** | 12 (VP) | 0 (FN) |
| **Correcta** | 0 (FP) | 0 (VN) |

- Tasa de detección global: **100.0 %** · meta ≥ 90 % sobre cifras no respaldadas (modo sin grounding)
- Tasa de falsos positivos: **—** (meta ≤ 10 %)
- Precisión de las alertas: 100.0 %

| Modo | Incorrectas | Alertadas | Detección (%) | Correctas | Falsas alertas | Falsos positivos (%) |
|---|---|---|---|---|---|---|
| sin grounding | 12 | 12 | 100.0 | 0 | 0 | — |
| con grounding | 0 | 0 | — | 0 | 0 | — |

Nota: el verificador comprueba la **procedencia** de las cifras, no que la herramienta se haya consultado con los filtros correctos. Una respuesta con grounding puede ser incorrecta y aun así quedar VERIFICADA si el modelo consultó mal (ver sección 4 y `docs/LIMITES.md`).

## 3. Inyección indirecta

0 de 0 casos neutralizados.


## 4. Casos para documentar

Respuestas incorrectas que el verificador **no** alertó (falsos negativos): revisar para `docs/LIMITES.md`.

- Ninguno.
