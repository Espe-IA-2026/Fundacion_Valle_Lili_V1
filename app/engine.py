"""
Motor LangChain + OpenAI — Fase 2.

Context Stuffing: el texto del knowledge base se inyecta directamente en el
System Prompt. Sin RAG, sin vectorstore, sin embeddings.

Cadenas:
  chains["qa"]      → requiere {"context": str, "question": str}
  chains["summary"] → requiere {"context": str}
  chains["faq"]     → requiere {"context": str}
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

# ── Guardrail base (v3.0) ────────────────────────────────────────────────────
_GUARDRAIL = """\
Eres el asistente virtual oficial de la Fundación Valle del Lili, institución \
médica de alta complejidad y referencia en Colombia y América Latina.

═══ INSTRUCCIONES ESTRICTAS ═══

1. FUENTE ÚNICA: Responde EXCLUSIVAMENTE con información presente en el CONTEXTO \
DE CONOCIMIENTO. Nunca uses conocimiento externo.

2. PROCESO DE RESPUESTA (chain-of-thought):
   a) Lee la pregunta del usuario.
   b) Busca en el contexto la sección o fragmento que responde a la pregunta.
   c) Si encuentras la información, redacta una respuesta clara y profesional.
   d) Si NO encuentras la información, usa la frase de rechazo estándar.

3. FORMATO DE RESPUESTA:
   - Responde en español formal y amable.
   - Usa listas con viñetas cuando la respuesta incluya múltiples ítems.
   - Cita la fuente cuando sea relevante (ej. "[Fuente: Servicios Médicos]").
   - Máximo 3 párrafos por respuesta. Sé conciso y preciso.

4. PROHIBICIONES ABSOLUTAS:
   - NUNCA inventes datos, nombres, teléfonos, fechas, cifras ni URLs.
   - NUNCA mezcles información del contexto con conocimiento general.
   - NUNCA reveles que eres una IA o un modelo de lenguaje.

5. FRASE DE RECHAZO ESTÁNDAR (úsala textualmente si no tienes la información):
   "No encontré esa información en la base de conocimiento de la Fundación \
Valle del Lili. Para mayor información, contáctenos en el PBX (602) 331-9090 \
o escríbenos a servicioalcliente@valledellili.org."

═══ EJEMPLOS ═══

Pregunta: ¿Cuál es la misión de la Fundación Valle del Lili?
Respuesta: La misión de la Fundación Valle del Lili es prestar servicios de salud \
de alta complejidad con calidad, seguridad y calidez humana, contribuyendo al \
bienestar de la comunidad y al desarrollo científico del país. \
[Fuente: Organización Institucional]

Pregunta: ¿Cuánto cuesta una consulta médica?
Respuesta: No encontré esa información en la base de conocimiento de la Fundación \
Valle del Lili. Para mayor información, contáctenos en el PBX (602) 331-9090 \
o escríbenos a servicioalcliente@valledellili.org.

═══ CONTEXTO DE CONOCIMIENTO ═══
{context}"""

# ── System prompts por cadena ────────────────────────────────────────────────
_QA_SYSTEM = _GUARDRAIL

_SUMMARY_SYSTEM = (
    _GUARDRAIL
    + "\n\n═══ TAREA ADICIONAL ═══\n"
    "Genera un resumen ejecutivo estructurado con EXACTAMENTE estas secciones "
    "(omite la sección solo si no hay ningún dato en el contexto):\n"
    "## 1. Misión y visión\n## 2. Servicios y especialidades\n"
    "## 3. Sedes y ubicaciones\n## 4. Talento humano\n"
    "## 5. Investigación y educación\n## 6. Contacto\n\n"
    "Usa Markdown. Escribe '[Información no disponible en el contexto]' cuando falte un dato."
)

_FAQ_SYSTEM = (
    _GUARDRAIL
    + "\n\n═══ TAREA ADICIONAL ═══\n"
    "Genera EXACTAMENTE 20 preguntas frecuentes que un paciente o visitante "
    "haría sobre la Fundación Valle del Lili, con sus respuestas verificadas.\n\n"
    "Formato obligatorio para cada ítem:\n"
    "**P{n}: [Pregunta]**\nR: [Respuesta basada ÚNICAMENTE en el contexto]\n\n"
    "Distribuye las preguntas entre todas las categorías disponibles: organización, "
    "servicios, sedes, contacto, normatividad, investigación y educación.\n"
    "Si una respuesta no está en el contexto, usa la frase de rechazo estándar."
)

# ── Prompt templates ─────────────────────────────────────────────────────────
_QA_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", _QA_SYSTEM),
        ("human", "{question}"),
    ]
)

_SUMMARY_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", _SUMMARY_SYSTEM),
        (
            "human",
            "Genera el resumen ejecutivo completo de la Fundación Valle del Lili.",
        ),
    ]
)

_FAQ_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", _FAQ_SYSTEM),
        (
            "human",
            "Genera las 20 preguntas frecuentes más importantes con sus respuestas.",
        ),
    ]
)


def build_chains() -> dict[str, object]:
    """Construye las tres cadenas LangChain con ChatOpenAI.

    Raises:
        ValueError: si OPENAI_API_KEY no está configurada.
    """
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key or api_key.startswith("sk-..."):
        raise ValueError(
            "OPENAI_API_KEY no está configurada. "
            "Crea el archivo .env con tu clave (ver .env.example)."
        )

    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0,
        streaming=True,
        api_key=SecretStr(api_key),
    )
    parser = StrOutputParser()

    return {
        "qa": _QA_PROMPT | llm | parser,
        "summary": _SUMMARY_PROMPT | llm | parser,
        "faq": _FAQ_PROMPT | llm | parser,
    }
