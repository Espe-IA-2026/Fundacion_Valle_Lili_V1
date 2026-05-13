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

    Usa esta herramienta para cualquier pregunta sobre servicios médicos,
    especialidades, sedes, procedimientos, horarios, contactos o datos
    institucionales de la FVL. Devuelve fragmentos de documentos oficiales
    relevantes para la consulta.

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
    """Convierte el diccionario de datos estructurados a texto legible para el agente.

    Lee la estructura real del archivo fvl_info.json con sus secciones anidadas:
    informacion_corporativa, contactos_clave, horarios_atencion, sedes_y_ubicaciones,
    convenios_eps_y_aseguradoras, servicios_destacados, servicios_de_apoyo,
    servicios_digitales.
    """
    lines: list[str] = []

    # ── Información corporativa ────────────────────────────────────────────────
    corp = data.get("informacion_corporativa", {})
    if corp:
        lines.append(f"Razón social: {corp.get('nombre_legal', 'N/A')}")
        lines.append(f"NIT: {corp.get('nit', 'N/A')}")
        lines.append(f"Naturaleza jurídica: {corp.get('naturaleza_juridica', 'N/A')}")
        lines.append(f"Sitio web: {corp.get('pagina_web', 'N/A')}")
        if corp.get("ranking_reputacion"):
            lines.append(f"Reconocimiento: {corp['ranking_reputacion']}")
        lines.append("")

        acreds = corp.get("acreditaciones", [])
        if acreds:
            lines.append("ACREDITACIONES:")
            for a in acreds:
                lines.append(f"  - {a}")
            lines.append("")

    # ── Contactos ─────────────────────────────────────────────────────────────
    contactos = data.get("contactos_clave", {})
    if contactos:
        lines.append("CONTACTOS:")
        _CONTACT_LABELS = {
            "central_telefonica": "Central telefónica",
            "urgencias_directo": "Urgencias (directo)",
            "citas_medicas": "Citas médicas",
            "whatsapp_citas": "WhatsApp citas",
            "email_informacion": "Correo información",
            "email_pqrs_quejas": "Correo PQRS / quejas",
            "extension_objetos_perdidos": "Ext. objetos perdidos",
        }
        for k, v in contactos.items():
            label = _CONTACT_LABELS.get(k, k.replace("_", " ").capitalize())
            lines.append(f"  {label}: {v}")
        lines.append("")

    # ── Horarios ──────────────────────────────────────────────────────────────
    horarios = data.get("horarios_atencion", {})
    if horarios:
        lines.append("HORARIOS DE ATENCIÓN:")
        _HORARIO_LABELS = {
            "urgencias": "Urgencias",
            "consulta_externa": "Consulta externa",
            "laboratorio_clinico": "Laboratorio clínico",
            "visitas_hospitalizacion": "Visitas hospitalización",
            "banco_de_sangre": "Banco de sangre",
        }
        for k, v in horarios.items():
            label = _HORARIO_LABELS.get(k, k.replace("_", " ").capitalize())
            lines.append(f"  {label}: {v}")
        lines.append("")

    # ── Sedes ─────────────────────────────────────────────────────────────────
    sedes = data.get("sedes_y_ubicaciones", [])
    if sedes:
        lines.append("SEDES:")
        for sede in sedes:
            ciudad = sede.get("ciudad", "")
            ciudad_str = f" ({ciudad})" if ciudad else ""
            lines.append(f"  {sede['nombre']}{ciudad_str}: {sede['direccion']}")
            if sede.get("servicios_principales"):
                lines.append(f"    Servicios: {sede['servicios_principales']}")
        lines.append("")

    # ── Convenios, EPS y aseguradoras ─────────────────────────────────────────
    convenios = data.get("convenios_eps_y_aseguradoras", {})
    if convenios:
        lines.append("CONVENIOS, EPS Y ASEGURADORAS:")
        eps_contrib = convenios.get("eps_regimen_contributivo", [])
        if eps_contrib:
            lines.append("  EPS Régimen Contributivo:")
            for eps in eps_contrib:
                lines.append(f"    - {eps}")
        prepagada = convenios.get("medicina_prepagada", [])
        if prepagada:
            lines.append("  Medicina Prepagada:")
            for mp in prepagada:
                lines.append(f"    - {mp}")
        otros = convenios.get("aseguradoras_y_otros", [])
        if otros:
            lines.append("  Aseguradoras y otros:")
            for o in otros:
                lines.append(f"    - {o}")
        if convenios.get("nota_importante"):
            lines.append(f"  Nota: {convenios['nota_importante']}")
        lines.append("")

    # ── Servicios destacados ──────────────────────────────────────────────────
    servicios = data.get("servicios_destacados", [])
    if servicios:
        lines.append("SERVICIOS DESTACADOS:")
        for s in servicios:
            lines.append(f"  - {s}")
        lines.append("")

    # ── Servicios de apoyo ────────────────────────────────────────────────────
    apoyo = data.get("servicios_de_apoyo", {})
    if apoyo:
        lines.append("SERVICIOS DE APOYO:")
        for k, v in apoyo.items():
            label = k.replace("_", " ").capitalize()
            lines.append(f"  {label}: {v}")
        lines.append("")

    # ── Servicios digitales ───────────────────────────────────────────────────
    digitales = data.get("servicios_digitales", {})
    if digitales:
        lines.append("SERVICIOS DIGITALES:")
        for k, v in digitales.items():
            label = k.replace("_", " ").capitalize()
            lines.append(f"  {label}: {v}")
        lines.append("")

    return "\n".join(lines)


@tool
def get_fvl_structured_info(query: str) -> str:
    """Obtiene datos concretos y estructurados de la Fundación Valle del Lili (FVL).

    Usa esta herramienta para preguntas directas y factuales como:
    - Números de teléfono y correos de contacto (central, urgencias, citas, WhatsApp)
    - Horarios de atención (consulta externa, urgencias, laboratorio, banco de sangre)
    - Direcciones y ubicaciones de sedes (sede principal, Limonar, Avenida Estación, Alfaguara)
    - NIT o identificación fiscal de la institución
    - Acreditaciones y certificaciones internacionales (JCI, MinSalud)
    - Convenios con EPS del régimen contributivo (Sura, Sanitas, Compensar, Nueva EPS, etc.)
    - Medicina prepagada (Colmédica, Medisanitas, Coomeva, Allianz, etc.)
    - Aseguradoras, SOAT, ARL y pólizas internacionales
    - Preguntas del tipo '¿atienden con mi EPS?', '¿tienen convenio con X?'
    - Servicios de apoyo (banco de sangre, capilla, restaurante, parqueadero)
    - Servicios digitales (telemedicina, App FVL Responde)

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