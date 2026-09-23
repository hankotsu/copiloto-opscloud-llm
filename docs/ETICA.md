# Checklist ético del PoC (marco de la Sesión 5)

Checklist de 7 preguntas mapeadas a NIST AI RMF 1.0 y al Reglamento de IA de la UE, aplicado a este proyecto. Un "No" es bloqueante.

| Pregunta | Marco | Respuesta | Justificación |
|---|---|---|---|
| ¿El usuario sabe que habla con un sistema de IA? | EU AI Act (transparencia, riesgo limitado) | Sí | La interfaz indica "Asistente de IA" y que las respuestas se verifican contra los datos |
| ¿Hay una ruta para escalar a un humano? | NIST AI RMF · Gestionar | Sí | Las respuestas FUERA_DOMINIO remiten al equipo de infraestructura |
| ¿Se evita pedir o almacenar datos sensibles? | NIST AI RMF · Mapear | Sí | Datos 100 % sintéticos; los logs no guardan el contenido de las preguntas (solo su huella); el prefiltro rechaza pedidos de credenciales |
| ¿El dataset incluye preguntas para detectar sesgo? | NIST AI RMF · Medir | No aplica | El dominio es técnico (inventario y costos), sin decisiones sobre personas |
| ¿Hay instrucciones y pruebas para rechazar lo que está fuera del alcance? | OWASP LLM06 + NIST Gobernar | Sí | Reglas 3 y 4 del prompt, prefiltro determinista y preguntas G31/G32 del golden set |
| ¿Cada corrida de evaluación queda registrada? | NIST AI RMF · Gobernar | Sí | `eval/resultados/<fecha>_<proveedor>/` versionado en git, con parámetros y respuestas |
| ¿Hay un plan si cambia el modelo o el dataset queda desactualizado? | NIST AI RMF · Gestionar | Sí | El runner se vuelve a ejecutar con el modelo nuevo y el golden set se regenera con el generador y los tests de CI |
