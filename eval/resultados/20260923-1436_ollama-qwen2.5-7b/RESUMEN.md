# Resultados de evaluación · ollama/qwen2.5:7b

Fecha 2026-09-23 14:37 · 4 preguntas · 1 corrida(s) · parámetros fijos: temperature=0.1, max_tokens=1500, max_iteraciones=5

## 1. Efecto del grounding

| Métrica | Sin grounding | Con grounding |
|---|---|---|
| Exactitud total (%) | 25.0 | 100.0 |
| Desviación entre corridas (pp) | 0.0 | 0.0 |
| Exactitud en preguntas con respuesta (%) | 0.0 | 100.0 |
| Límites bien manejados: sin datos, fuera de dominio, rechazo (%) | 50.0 | 100.0 |
| Falso «no sé» (%) | 0.0 | 0.0 |
| Tokens promedio por consulta | 165 | 2330 |
| Latencia promedio (s) | 9.61 | 9.24 |

### Exactitud por categoría (%)

| Categoría | Sin grounding | Con grounding |
|---|---|---|
| finops | 0.0 | 100.0 |
| rechazo | 100.0 | 100.0 |
| sin_datos | 0.0 | 100.0 |

### Veredictos del verificador

| Veredicto | Sin grounding | Con grounding |
|---|---|---|
| VERIFICADA | 0 | 3 |
| PARCIAL | 0 | 0 |
| NO_VERIFICADA | 0 | 0 |
| SIN_CIFRAS | 4 | 1 |

## 2. Heurística anti-alucinación (matriz de confusión)

Positivo = respuesta con cifras **incorrecta**. Alerta = veredicto PARCIAL o NO_VERIFICADA.

| | Alertada | No alertada |
|---|---|---|
| **Incorrecta** | 0 (VP) | 0 (FN) |
| **Correcta** | 0 (FP) | 2 (VN) |

- Tasa de detección global: **None %** · meta ≥ 90 % sobre cifras no respaldadas (modo sin grounding)
- Tasa de falsos positivos: **0.0 %** (meta ≤ 10 %)
- Precisión de las alertas: None %

| Modo | Incorrectas | Alertadas | Detección (%) | Correctas | Falsas alertas | Falsos positivos (%) |
|---|---|---|---|---|---|---|
| sin grounding | 0 | 0 | — | 0 | 0 | — |
| con grounding | 0 | 0 | — | 2 | 0 | 0.0 |

Nota: el verificador comprueba la **procedencia** de las cifras, no que la herramienta se haya consultado con los filtros correctos. Una respuesta con grounding puede ser incorrecta y aun así quedar VERIFICADA si el modelo consultó mal (ver sección 4 y `docs/LIMITES.md`).

## 3. Inyección indirecta

0 de 0 casos neutralizados.


## 4. Casos para documentar

Respuestas incorrectas que el verificador **no** alertó (falsos negativos): revisar para `docs/LIMITES.md`.

- Ninguno.
