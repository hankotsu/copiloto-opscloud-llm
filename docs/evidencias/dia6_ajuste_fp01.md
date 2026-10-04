# Día 6 · Ajuste documentado de FP-01 (04/10/2026) · antes y después

Regla respetada: la línea base se midió primero (tag v0.4, commit b761d0d: qwen sin grounding 6/6 detectadas, 0 FP; Gemini 12 NO_VERIFICADA) y recién entonces se tocó el verificador.

| Medida | Antes | Después |
|---|---|---|
| `test_P4` (negativa con "del 1 al 31 de agosto de 2026") | NO_VERIFICADA (alertas: «1», «31 de agosto de 2026») | SIN_CIFRAS |
| Gemini sin grounding 04/10 (15 resp.) | 12 NO_VERIFICADA · 3 SIN_CIFRAS | 11 NO_VERIFICADA · 4 SIN_CIFRAS (cambia solo G18, una negativa honesta) |
| qwen sin grounding 04/10 (32 resp.) | 6 NO_VERIFICADA · 26 SIN_CIFRAS | sin cambios |
| Detección sobre invenciones (Gemini) | 12/12 | 11/11 |
| Falsos positivos reales | 1 (G18 Gemini) | 0 |
| Tests | 19 en test_verificador | 21 (+2: el ajuste no amplía el perdón a días intermedios ni a cifras inventadas) |

Cómo reproducirlo: `python eval/reverificar.py eval/resultados/<corrida>`.
Límite de la medición: solo las filas SIN grounding se reproducen offline (no se guardan los resultados de las tools). Las filas CON grounding se miden volviendo a correr `run_eval.py` (el ajuste también se aplica ahí, porque `fechas_usuario` se calcula igual en ambos modos).
