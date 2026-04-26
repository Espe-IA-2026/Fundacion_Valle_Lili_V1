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

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

# ── Guardrail compartido ─────────────────────────────────────────────────────
_GUARDRAIL = """\
Eres el asistente virtual oficial de la Fundación Valle del Lili, institución \
médica de referencia en Colombia y América Latina.

REGLAS ESTRICTAS (sin excepción):
1. Responde ÚNICAMENTE con información presente en el CONTEXTO DE CONOCIMIENTO.
2. Si la información NO está en el contexto, di exactamente:
   "No encontré esa información en la base de conocimiento de la Fundación Valle del Lili."
3. NUNCA inventes datos, nombres, teléfonos, fechas, cifras ni URLs.
4. Cita la fuente cuando sea relevante (ej. "[Fuente: Servicios Médicos]").
5. Responde en español formal y amable.

CONTEXTO DE CONOCIMIENTO:
{context}"""

# ── System prompts por cadena ────────────────────────────────────────────────
_QA_SYSTEM = _GUARDRAIL

_SUMMARY_SYSTEM = (
    _GUARDRAIL + "\n\nGenera un resumen ejecutivo estructurado con estas secciones "
    "(solo si la información aparece en el contexto): "
    "## 1. Misión y visión | ## 2. Servicios y especialidades | "
    "## 3. Sedes y ubicaciones | ## 4. Talento humano | "
    "## 5. Investigación y educación | ## 6. Contacto. "
    "Usa Markdown. Indica '[Información no disponible]' cuando falte."
)

_FAQ_SYSTEM = (
    _GUARDRAIL
    + "\n\nGenera EXACTAMENTE 20 preguntas frecuentes que un paciente o visitante "
    "haría sobre la Fundación Valle del Lili, con sus respuestas verificadas. "
    "Formato obligatorio para cada ítem:\n"
    "**P{n}: [Pregunta]**\nR: [Respuesta basada en el contexto]\n\n"
    "Si una respuesta no está en el contexto: "
    "'Esta información no está disponible en la base de conocimiento actual.'"
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
        api_key=api_key,
    )
    parser = StrOutputParser()

    return {
        "qa": _QA_PROMPT | llm | parser,
        "summary": _SUMMARY_PROMPT | llm | parser,
        "faq": _FAQ_PROMPT | llm | parser,
    }
