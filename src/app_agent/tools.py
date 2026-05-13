"""Herramientas del agente FVL: recuperación semántica (RAG) y datos estructurados."""

from __future__ import annotations

import json
import logging

from langchain.tools import tool

from rag.indexer import KnowledgeIndexer
from rag.retriever import KnowledgeRetriever
from semantic_layer_fvl.config import get_settings

logger = logging.getLogger(__name__)

# Singleton a nivel de módulo — None hasta la primera llamada a la tool.
_retriever: KnowledgeRetriever | None = None


def _get_retriever() -> KnowledgeRetriever:
    """Devuelve el retriever, inicializándolo en la primera llamada.

    Carga el índice ChromaDB una sola vez durante la vida del proceso.
    Las llamadas siguientes reutilizan la instancia ya creada.

    Returns:
        Instancia de ``KnowledgeRetriever`` con el índice ChromaDB cargado.

    Raises:
        ValueError: Si no hay archivos ``.md`` en el directorio de conocimiento.
    """
    global _retriever
    if _retriever is None:
        logger.info("Inicializando KnowledgeRetriever por primera vez...")
        indexer = KnowledgeIndexer()
        db = indexer.build_or_load()
        _retriever = KnowledgeRetriever(db)
        logger.info("KnowledgeRetriever listo.")
    return _retriever


@tool
def retrieve_fvl_knowledge(query: str) -> str:
    """Busca información institucional de la Fundación Valle del Lili (FVL).

    Usa esta herramienta para preguntas abiertas sobre servicios médicos,
    especialidades, procedimientos clínicos, tratamientos, programas
    institucionales o contexto narrativo de la FVL. Devuelve fragmentos de
    documentos oficiales relevantes para la consulta.

    No uses esta herramienta para datos estructurados como EPS, convenios,
    aseguradoras, métodos de pago, teléfonos, horarios, sedes o preguntas
    frecuentes directas; para esas consultas usa get_fvl_structured_info.

    Args:
        query: Pregunta o tema a buscar en la base de conocimiento.

    Returns:
        Fragmentos de documentos institucionales relevantes separados por
        delimitadores. Si no hay resultados, devuelve un mensaje indicativo
        para que el agente lo comunique al usuario.
    """
    settings = get_settings()
    retriever = _get_retriever()

    docs = retriever.search(
        query,
        k=settings.rag_top_k,
        score_threshold=settings.rag_score_threshold,
    )

    if not docs:
        logger.debug("retrieve_fvl_knowledge: sin resultados para '%s'", query)
        return (
            "No encontré información relevante en la base de conocimiento "
            "para esta consulta."
        )

    parts: list[str] = []
    for i, doc in enumerate(docs, start=1):
        slug = doc.metadata.get("slug", "desconocido")
        category = doc.metadata.get("category", "")
        # Eliminar prefijo numérico "02_" → "servicios"
        category_clean = category.split("_", 1)[-1] if "_" in category else category
        header = f"[Fragmento {i} — {slug}"
        if category_clean:
            header += f" ({category_clean})"
        header += "]"
        parts.append(f"{header}\n{doc.page_content}")

    logger.debug(
        "retrieve_fvl_knowledge: %d fragmentos recuperados para '%s'",
        len(parts),
        query,
    )
    return "\n\n---\n\n".join(parts)


def _format_structured_data(data: dict) -> str:
    """Convierte el diccionario de datos estructurados a texto legible para el agente."""
    lines: list[str] = []

    lines.append(f"Razón social: {data.get('razon_social', 'N/A')}")
    lines.append(f"NIT: {data.get('nit', 'N/A')}")
    lines.append(f"Año de fundación: {data.get('año_fundacion', 'N/A')}")
    lines.append(f"Tipo de entidad: {data.get('tipo_entidad', 'N/A')}")
    lines.append(f"Director médico: {data.get('director_medico', 'N/A')}")
    lines.append(f"Director ejecutivo: {data.get('director_ejecutivo', 'N/A')}")
    lines.append(f"Sitio web: {data.get('sitio_web', 'N/A')}")
    lines.append("")

    contactos = data.get("contactos", {})
    if contactos:
        lines.append("CONTACTOS:")
        for k, v in contactos.items():
            lines.append(f"  {k}: {v}")
        lines.append("")

    horarios = data.get("horarios", {})
    if horarios:
        lines.append("HORARIOS DE ATENCIÓN:")
        for k, v in horarios.items():
            lines.append(f"  {k}: {v}")
        lines.append("")

    sedes = data.get("sedes", [])
    if sedes:
        lines.append("SEDES:")
        for sede in sedes:
            lines.append(f"  {sede['nombre']}: {sede['direccion']} — Tel: {sede['telefono']}")
            if sede.get("referencia"):
                lines.append(f"    ({sede['referencia']})")
        lines.append("")

    servicios = data.get("servicios_destacados", [])
    if servicios:
        lines.append("SERVICIOS DESTACADOS:")
        for s in servicios:
            lines.append(f"  - {s}")
        lines.append("")

    acreds = data.get("acreditaciones", [])
    if acreds:
        lines.append("ACREDITACIONES:")
        for a in acreds:
            lines.append(f"  - {a}")
        lines.append("")

    redes = data.get("redes_sociales", {})
    if redes:
        lines.append("REDES SOCIALES:")
        for k, v in redes.items():
            lines.append(f"  {k}: {v}")
        lines.append("")

    pago = data.get("metodos_pago", {})
    if pago:
        lines.append("MÉTODOS DE PAGO:")
        for m in pago.get("modalidades", []):
            lines.append(f"  - {m}")
        if pago.get("horario_caja"):
            lines.append(f"  Horario de caja: {pago['horario_caja']}")
        lines.append("")

    donaciones = data.get("donaciones", {})
    if donaciones:
        lines.append("DONACIONES:")
        lines.append(f"  {donaciones.get('descripcion', '')}")
        lines.append(f"  Contacto: {donaciones.get('contacto', '')}")
        lines.append("")

    faqs = data.get("preguntas_frecuentes", [])
    if faqs:
        lines.append("PREGUNTAS FRECUENTES:")
        for faq in faqs:
            lines.append(f"  P: {faq['pregunta']}")
            lines.append(f"  R: {faq['respuesta']}")
        lines.append("")

    return "\n".join(lines)


@tool
def get_fvl_structured_info(query: str) -> str:
    """Obtiene datos concretos y estructurados de la Fundación Valle del Lili (FVL).

    Usa esta herramienta para preguntas directas y factuales como:
    - Números de teléfono y correos de contacto (central, urgencias, citas)
    - Horarios de atención (consulta externa, urgencias, laboratorio, farmacia)
    - Direcciones y ubicaciones de sedes
    - NIT o identificación fiscal de la institución
    - Nombre de directivos (director médico, director ejecutivo)
    - Redes sociales oficiales
    - Acreditaciones y certificaciones internacionales
    - Métodos de pago aceptados
    - EPS, convenios, aseguradoras, medicina prepagada y SOAT
    - Información sobre donaciones
    - Preguntas frecuentes con respuesta directa

    NO uses esta herramienta para preguntas abiertas sobre tratamientos médicos,
    procedimientos clínicos, historia institucional narrativa o especialidades en
    detalle; para esas consultas usa retrieve_fvl_knowledge.

    Args:
        query: Pregunta específica sobre datos concretos de la FVL.

    Returns:
        Datos estructurados formateados en texto plano listos para sintetizar la respuesta.
    """
    settings = get_settings()
    data_path = settings.resolved_structured_data_path

    try:
        data = json.loads(data_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        logger.error("Archivo de datos estructurados no encontrado: %s", data_path)
        return "No se encontró el archivo de datos estructurados de la FVL."
    except json.JSONDecodeError as exc:
        logger.error("Error de formato en datos estructurados: %s", exc)
        return "Error al leer los datos estructurados de la FVL."

    logger.debug("get_fvl_structured_info: datos cargados desde '%s'", data_path)
    return _format_structured_data(data)
