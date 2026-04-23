from __future__ import annotations

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langchain_ollama import ChatOllama

_MODEL = "llama3.2:1b"
_NUM_CTX = 16384  # 16k tokens — más rápido en CPU, deja ~5k tokens para respuesta

# ---------------------------------------------------------------------------
# Prompts — zero-shot con instrucciones anti-alucinación
# ---------------------------------------------------------------------------

_SYSTEM_QA = """\
Eres el asistente virtual oficial de la Fundación Valle del Lili, una de las \
instituciones médicas de mayor referencia en Colombia y América Latina.

INSTRUCCIONES:
- Responde de forma precisa, amable y profesional.
- Basa tu respuesta EXCLUSIVAMENTE en el contexto de conocimiento proporcionado.
- Si la información solicitada NO está en el contexto, responde con honestidad:
  "No tengo información específica sobre eso en mi base de conocimiento actual."
- Nunca inventes datos, fechas, nombres, cifras ni servicios que no aparezcan en el contexto.
- Cita la sección de origen cuando sea relevante (ej. "Según la sección de Cardiología...").

CONTEXTO DE CONOCIMIENTO:
{context}
"""

_SYSTEM_SUMMARY = """\
Eres un analista experto en organizaciones del sector salud.
Basándote ÚNICAMENTE en el contexto proporcionado, redacta un resumen ejecutivo \
completo y bien estructurado de la Fundación Valle del Lili.

El resumen debe cubrir obligatoriamente:
1. Misión, visión y valores
2. Historia e hitos relevantes
3. Servicios y especialidades principales
4. Reconocimientos, certificaciones y calidad
5. Investigación y educación
6. Presencia y contacto

Usa subtítulos claros (##) para cada sección. Sé preciso y no añadas información \
que no esté en el contexto.

CONTEXTO DE CONOCIMIENTO:
{context}
"""

_SYSTEM_FAQ = """\
Eres un experto en comunicación institucional y servicio al cliente del sector salud.
Basándote ÚNICAMENTE en el contexto proporcionado, genera exactamente 20 preguntas \
frecuentes que un paciente, familiar o visitante haría a la Fundación Valle del Lili, \
con sus respuestas detalladas y verídicas.

Formato obligatorio para cada ítem:
**P{{n}}: [Pregunta]**
R: [Respuesta basada en el contexto]

Cubre variedad de temas: servicios, contacto, sedes, especialidades, procesos \
administrativos, investigación, educación.
Si la respuesta no está en el contexto, escribe: "Esta información no está \
disponible en la base de conocimiento actual."

CONTEXTO DE CONOCIMIENTO:
{context}
"""

# ---------------------------------------------------------------------------
# Prompt templates (LangChain)
# ---------------------------------------------------------------------------

_QA_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", _SYSTEM_QA),
        ("human", "{question}"),
    ]
)

_SUMMARY_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", _SYSTEM_SUMMARY),
        ("human", "Genera el resumen ejecutivo completo de la Fundación Valle del Lili."),
    ]
)

_FAQ_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", _SYSTEM_FAQ),
        ("human", "Genera las 20 preguntas frecuentes más importantes con sus respuestas."),
    ]
)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_chains(model: str = _MODEL, num_ctx: int = _NUM_CTX) -> dict[str, Runnable]:
    llm = ChatOllama(model=model, num_ctx=num_ctx)
    parser = StrOutputParser()
    return {
        "qa": _QA_PROMPT | llm | parser,
        "summary": _SUMMARY_PROMPT | llm | parser,
        "faq": _FAQ_PROMPT | llm | parser,
    }
