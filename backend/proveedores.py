"""
Adaptadores de proveedores LLM detrás de una interfaz común (mismo patrón que la Sesión 5).

  * ProveedorOllama        → API nativa de Ollama (/api/chat), permite fijar num_ctx
  * ProveedorOpenAICompat  → cualquier endpoint compatible con OpenAI: OpenAI y Gemini
  * ProveedorSimulado      → sin LLM: respuestas deterministas para CI y demo sin red

Todos exponen:
  chat(mensajes, tools) -> RespuestaLLM
  mensaje_asistente(respuesta) -> dict      (para reinyectar la llamada a tools)
  mensaje_tool(llamada, contenido) -> dict  (resultado de una tool)
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass, field
from typing import Optional

import httpx

from .config import CONFIG, Config


class ErrorProveedor(RuntimeError):
    """El proveedor no respondió o respondió con error (mensaje apto para el usuario)."""


@dataclass
class LlamadaTool:
    id: str
    nombre: str
    argumentos: dict | str


@dataclass
class RespuestaLLM:
    texto: str
    tool_calls: list[LlamadaTool] = field(default_factory=list)
    tokens_entrada: int = 0
    tokens_salida: int = 0
    crudo: dict = field(default_factory=dict)


class ProveedorOllama:
    nombre = "ollama"

    def __init__(self, cfg: Config = CONFIG, transport: Optional[httpx.BaseTransport] = None):
        self.cfg, self.modelo, self.modo_simulado = cfg, cfg.ollama_model, False
        self.cliente = httpx.Client(base_url=cfg.ollama_base_url, timeout=cfg.timeout_s, transport=transport)

    def chat(self, mensajes, tools=None) -> RespuestaLLM:
        payload = {"model": self.modelo, "messages": mensajes, "stream": False, "keep_alive": self.cfg.ollama_keep_alive,
                   "options": {"temperature": self.cfg.temperature, "num_ctx": self.cfg.ollama_num_ctx,
                               "num_predict": self.cfg.max_tokens}}
        if tools:
            payload["tools"] = tools
        try:
            r = self.cliente.post("/api/chat", json=payload)
            r.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise ErrorProveedor(f"Ollama respondió {e.response.status_code}: {e.response.text[:200]}") from e
        except httpx.HTTPError as e:
            raise ErrorProveedor(f"No se pudo conectar con Ollama en {self.cfg.ollama_base_url}. ¿Está corriendo 'ollama serve'?") from e
        data = r.json()
        msg = data.get("message", {})
        calls = [LlamadaTool(id=f"call_{i}", nombre=tc["function"]["name"], argumentos=tc["function"].get("arguments") or {})
                 for i, tc in enumerate(msg.get("tool_calls") or [])]
        return RespuestaLLM(texto=msg.get("content") or "", tool_calls=calls,
                            tokens_entrada=data.get("prompt_eval_count", 0), tokens_salida=data.get("eval_count", 0), crudo=msg)

    def mensaje_asistente(self, r: RespuestaLLM) -> dict:
        m = {"role": "assistant", "content": r.texto}
        if r.crudo.get("tool_calls"):
            m["tool_calls"] = r.crudo["tool_calls"]
        return m

    def mensaje_tool(self, llamada: LlamadaTool, contenido: str) -> dict:
        return {"role": "tool", "content": contenido, "tool_name": llamada.nombre}


class ProveedorOpenAICompat:
    """OpenAI, o Gemini a través de su endpoint compatible con OpenAI."""

    def __init__(self, nombre: str, base_url: str, api_key: str, modelo: str, cfg: Config = CONFIG,
                 transport: Optional[httpx.BaseTransport] = None):
        self.nombre, self.modelo, self.cfg, self.modo_simulado = nombre, modelo, cfg, False
        self.cliente = httpx.Client(base_url=base_url.rstrip("/"), timeout=cfg.timeout_s, transport=transport,
                                    headers={"Authorization": f"Bearer {api_key}"})

    def chat(self, mensajes, tools=None) -> RespuestaLLM:
        payload = {"model": self.modelo, "messages": mensajes, "temperature": self.cfg.temperature,
                   "max_tokens": self.cfg.max_tokens}
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        for intento in range(3):  # backoff simple ante 429 / 5xx
            try:
                r = self.cliente.post("/chat/completions", json=payload)
                if r.status_code in (429, 500, 502, 503) and intento < 2:
                    time.sleep(2 ** (intento + 1))
                    continue
                r.raise_for_status()
                break
            except httpx.HTTPStatusError as e:
                raise ErrorProveedor(f"{self.nombre} respondió {e.response.status_code}") from e
            except httpx.HTTPError as e:
                raise ErrorProveedor(f"No se pudo conectar con {self.nombre}") from e
        data = r.json()
        msg = data["choices"][0]["message"]
        calls = [LlamadaTool(id=tc.get("id") or f"call_{i}", nombre=tc["function"]["name"],
                             argumentos=tc["function"].get("arguments") or "{}")
                 for i, tc in enumerate(msg.get("tool_calls") or [])]
        uso = data.get("usage") or {}
        return RespuestaLLM(texto=msg.get("content") or "", tool_calls=calls, tokens_entrada=uso.get("prompt_tokens", 0),
                            tokens_salida=uso.get("completion_tokens", 0), crudo=msg)

    def mensaje_asistente(self, r: RespuestaLLM) -> dict:
        m = {"role": "assistant", "content": r.texto or None}
        if r.crudo.get("tool_calls"):
            m["tool_calls"] = r.crudo["tool_calls"]
        return m

    def mensaje_tool(self, llamada: LlamadaTool, contenido: str) -> dict:
        return {"role": "tool", "tool_call_id": llamada.id, "content": contenido}


# ─────────────────────────────── proveedor simulado (sin LLM)
MESES = {"enero": "01", "febrero": "02", "marzo": "03", "abril": "04", "mayo": "05", "junio": "06", "julio": "07",
         "agosto": "08", "septiembre": "09", "setiembre": "09", "octubre": "10", "noviembre": "11", "diciembre": "12"}


class ProveedorSimulado:
    """Imita a un LLM con reglas simples: sirve para CI, pruebas y para demostrar el flujo sin red.
    Con tools, elige una por palabras clave y resume su resultado; sin tools, 'alucina' una cifra
    determinista (el comportamiento típico que el verificador debe detectar)."""
    nombre, modelo, modo_simulado = "simulado", "reglas-v1", True

    def __init__(self, cfg: Config = CONFIG, mes_defecto: str = "2026-08"):
        self.cfg, self.mes_defecto = cfg, mes_defecto

    def _mes(self, q: str) -> str:
        for nom, num in MESES.items():
            m = re.search(rf"\b{nom}\b(?: de)?(?: (\d{{4}}))?", q)
            if m:
                return f"{m.group(1) or self.mes_defecto[:4]}-{num}"
        return self.mes_defecto

    @staticmethod
    def _filtros(q: str) -> dict:
        f = {}
        m = re.search(r"\b(sa-saopaulo-1|sa-vinhedo-1|sa-santiago-1|eu-frankfurt-1|us-[a-z]+-\d)\b", q)
        if m:
            f["region"] = m.group(1)
        if "producción" in q:
            f["ambiente"] = "PRD"
        if "running" in q:
            f["estado"] = "RUNNING"
        if "windows" in q:
            f["sistema_operativo"] = "Windows"
        return f

    def _elegir_tool(self, q: str):
        q = q.lower()
        filtros = self._filtros(q)
        if any(w in q for w in ("costo", "costó", "gast", "factur")):
            if "detenida" in q:
                return "instancias_detenidas_con_costo", {"mes": self._mes(q)}
            if "variación" in q or "entre" in q:
                meses = [f"{a or self.mes_defecto[:4]}-{MESES[n]}" for n, a in
                         re.findall(r"\b(" + "|".join(MESES) + r")\b(?: de (\d{4}))?", q)]
                if len(meses) >= 2:
                    return "variacion_costos", {"tipo": "meses", "mes_a": meses[0], "mes_b": meses[1]}
            if "aumento" in q:
                return "variacion_costos", {"tipo": "recursos"}
            agr = "region" if "región" in q else "servicio" if "servicio" in q else "recurso" if "recursos" in q else "dia" if "día" in q else "total"
            args = {"mes": self._mes(q), "agrupar_por": agr, "region": filtros.get("region")}
            if "egreso" in q:
                args["sku_contiene"] = "Outbound Data Transfer"
            m = re.search(r"\b(\d+) recursos", q)
            if m:
                args["top"] = int(m.group(1))
            return "consultar_costos", args
        if "respaldo" in q or "backup" in q:
            if "base" in q:
                return "estado_bases_datos", {"ambiente": "PRD", "auto_backup": False}
            return "cobertura_respaldo", {"ambiente": "PRD" if "producción" in q else None, "estado_respaldo": "SIN RESPALDO"}
        if "base" in q and "dato" in q:
            return "estado_bases_datos", {}
        if any(w in q for w in ("regla", "puerto", "ssh", "rdp")):
            return "reglas_ingreso", {"solo_publicas": True}
        if "bucket" in q:
            return "buckets", {"publicos": True} if "públic" in q else {}
        if "etiquet" in q:
            return "cumplimiento_etiquetado", {}
        if "instancia" in q or "servidor" in q:
            return "consultar_instancias", {k: v for k, v in filtros.items()}
        return None, None

    def chat(self, mensajes, tools=None) -> RespuestaLLM:
        ultimo = mensajes[-1]
        pregunta = next(m["content"] for m in reversed(mensajes) if m["role"] == "user")
        if not tools:
            h = int(hashlib.sha256(pregunta.encode()).hexdigest()[:6], 16)
            return RespuestaLLM(texto=(f"Según los registros del tenancy, el valor solicitado es de USD {40000 + h % 20000:,}.{h % 100:02d}; "
                                       f"además hay {60 + h % 50} instancias activas en sa-saopaulo-1."),
                                tokens_entrada=len(pregunta) // 4, tokens_salida=40)
        if ultimo["role"] == "tool":
            datos = json.loads(ultimo["content"])
            if datos.get("error"):
                return RespuestaLLM(texto="SIN_DATOS: la consulta a la herramienta falló.")
            if datos.get("sin_datos"):
                p = datos["periodo_disponible"]
                return RespuestaLLM(texto=f"SIN_DATOS: solo hay datos entre {p['desde']} y {p['hasta']}.")
            partes = []
            for k, v in datos.items():
                if isinstance(v, (int, float)) and not isinstance(v, bool) and k not in ("filas_devueltas", "filas_totales"):
                    partes.append(f"{k.replace('_', ' ')}: {v:,}" if isinstance(v, int) else f"{k.replace('_', ' ')}: {v:,.2f}")
            for lista in ("mayores_aumentos",):
                for f in datos.get(lista, [])[:1]:
                    partes.append(f"mayor aumento: {f['recurso']} (+{f['aumento_usd']:,.2f} USD)")
            nombres = [f.get("nombre") or f.get("security_list") or f.get("disco") for f in datos.get("filas", [])[:5]]
            nombres += [d.get(datos.get("agrupado_por", "")) for d in datos.get("desglose", [])[:5]]
            nombres = [n for n in nombres if n]
            texto = "; ".join(partes) or "Consulta realizada"
            if nombres:
                texto += ". Principales: " + ", ".join(dict.fromkeys(nombres))
            return RespuestaLLM(texto=texto + ".", tokens_entrada=len(ultimo["content"]) // 4, tokens_salida=60)
        tool, args = self._elegir_tool(pregunta)
        if not tool:
            return RespuestaLLM(texto="FUERA_DOMINIO: solo respondo sobre inventario, respaldos, red y costos del tenancy.")
        args = {k: v for k, v in args.items() if v is not None}
        return RespuestaLLM(texto="", tool_calls=[LlamadaTool("sim_0", tool, args)],
                            crudo={"tool_calls": [{"id": "sim_0", "type": "function",
                                                   "function": {"name": tool, "arguments": json.dumps(args)}}]})

    def mensaje_asistente(self, r: RespuestaLLM) -> dict:
        return {"role": "assistant", "content": r.texto, **({"tool_calls": r.crudo["tool_calls"]} if r.crudo.get("tool_calls") else {})}

    def mensaje_tool(self, llamada: LlamadaTool, contenido: str) -> dict:
        return {"role": "tool", "tool_call_id": llamada.id, "content": contenido}


PROVEEDORES = ("ollama", "gemini", "openai", "simulado")


def crear_proveedor(nombre: str, cfg: Config = CONFIG):
    """Si falta la API key de un proveedor en la nube, cae a modo simulado (patrón del curso)."""
    if cfg.modo_simulado or nombre == "simulado":
        return ProveedorSimulado(cfg)
    if nombre == "ollama":
        return ProveedorOllama(cfg)
    if nombre == "gemini":
        return (ProveedorOpenAICompat("gemini", cfg.gemini_base_url, cfg.gemini_api_key, cfg.gemini_model, cfg)
                if cfg.gemini_api_key else ProveedorSimulado(cfg))
    if nombre == "openai":
        return (ProveedorOpenAICompat("openai", cfg.openai_base_url, cfg.openai_api_key, cfg.openai_model, cfg)
                if cfg.openai_api_key else ProveedorSimulado(cfg))
    raise ValueError(f"Proveedor desconocido: {nombre}")
