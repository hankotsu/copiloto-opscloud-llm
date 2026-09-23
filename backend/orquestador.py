"""
Generación: orquestador con tool calling (patrón ReAct: razonar → actuar → observar).

  * grounding=True  → el modelo recibe las tools y las reglas de grounding.
  * grounding=False → el MISMO modelo y el mismo prompt base, sin tools (línea base).

Límites configurados: iteraciones máximas, reintentos ante argumentos inválidos
(patrón de la opción 03), max_tokens y temperature fijos (config.py).
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field

from pydantic import ValidationError

from . import prompts, seguridad, tools
from .config import CONFIG, Config
from .verificador import verificar

TIPOS = ("SIN_DATOS", "FUERA_DOMINIO", "RECHAZO")


@dataclass
class PasoTool:
    tool: str
    argumentos: dict
    ok: bool
    resultado: dict
    error: str = ""


@dataclass
class Respuesta:
    pregunta: str
    grounding: bool
    proveedor: str
    modelo: str
    modo_simulado: bool
    tipo: str                 # RESPUESTA | SIN_DATOS | FUERA_DOMINIO | RECHAZO | ERROR
    respuesta: str
    verificacion: dict
    pasos: list[PasoTool] = field(default_factory=list)
    iteraciones: int = 0
    tokens_entrada: int = 0
    tokens_salida: int = 0
    latencia_s: float = 0.0
    canario_filtrado: bool = False

    def a_dict(self):
        d = asdict(self)
        d["herramientas_usadas"] = [p.tool for p in self.pasos]
        return d


def _tipo(texto: str) -> tuple[str, str]:
    t = texto.strip()
    for tipo in TIPOS:
        if t.upper().startswith(tipo):
            return tipo, t[len(tipo):].lstrip(" :-").strip() or t
    return "RESPUESTA", t


class Orquestador:
    def __init__(self, proveedor, cfg: Config = CONFIG):
        self.proveedor, self.cfg = proveedor, cfg
        self.con = tools.conectar(cfg.db_path)
        self.periodo = tools.periodo(self.con)
        self.especificaciones = tools.especificaciones()

    def responder(self, pregunta: str, grounding: bool = True) -> Respuesta:
        t0 = time.time()
        pregunta = seguridad.sanitizar(pregunta, self.cfg.max_largo_pregunta)
        base = dict(pregunta=pregunta, grounding=grounding, proveedor=self.proveedor.nombre,
                    modelo=self.proveedor.modelo, modo_simulado=getattr(self.proveedor, "modo_simulado", False))
        corte = seguridad.prefiltro(pregunta)
        if corte:  # control determinista: no se llama al LLM
            return Respuesta(**base, tipo=corte[0], respuesta=corte[1], latencia_s=round(time.time() - t0, 3),
                             verificacion={"veredicto": "SIN_CIFRAS", "resumen": "Resuelta por el prefiltro de seguridad",
                                           "capas_disparadas": [], "afirmaciones": []})
        sistema = prompts.sistema(grounding, self.periodo, self.cfg.canario)
        mensajes = [{"role": "system", "content": sistema}, {"role": "user", "content": pregunta}]
        pasos, tin, tout, errores, texto = [], 0, 0, 0, None
        it = 0
        for it in range(1, self.cfg.max_iteraciones + 1):
            r = self.proveedor.chat(mensajes, self.especificaciones if grounding else None)
            tin, tout = tin + r.tokens_entrada, tout + r.tokens_salida
            if not (grounding and r.tool_calls):
                texto = r.texto
                break
            mensajes.append(self.proveedor.mensaje_asistente(r))
            for llamada in r.tool_calls:
                args = llamada.argumentos
                try:
                    args = json.loads(args) if isinstance(args, str) else (args or {})
                    resultado = tools.ejecutar(self.con, llamada.nombre, args)
                    pasos.append(PasoTool(llamada.nombre, args, True, resultado))
                except (ValidationError, KeyError, ValueError, json.JSONDecodeError) as e:
                    errores += 1
                    msg = (f"Herramienta inexistente: {llamada.nombre}" if isinstance(e, KeyError)
                           else f"Argumentos inválidos: {str(e)[:300]}")
                    resultado = {"error": msg, "sugerencia": "Corrige los argumentos según el esquema y vuelve a intentar."}
                    pasos.append(PasoTool(llamada.nombre, args if isinstance(args, dict) else {}, False, {}, msg))
                mensajes.append(self.proveedor.mensaje_tool(llamada, json.dumps(resultado, ensure_ascii=False, default=str)))
            if errores > self.cfg.max_reintentos_tool:
                texto = "SIN_DATOS: no se pudo consultar la información (argumentos inválidos repetidos)."
                break
        if texto is None:
            texto = "SIN_DATOS: no se completó la consulta dentro del límite de pasos."
        texto, filtrado = seguridad.filtrar_canario(texto, self.cfg.canario)
        tipo, limpio = _tipo(texto)
        contexto = f"Periodo de datos {self.periodo['desde']} a {self.periodo['hasta']}" if grounding else ""
        ver = verificar(limpio, [p.resultado for p in pasos if p.ok], pregunta, contexto)
        return Respuesta(**base, tipo=tipo, respuesta=limpio, verificacion=ver.a_dict(), pasos=pasos, iteraciones=it,
                         tokens_entrada=tin, tokens_salida=tout, latencia_s=round(time.time() - t0, 3),
                         canario_filtrado=filtrado)
