from __future__ import annotations

import os
from pathlib import Path

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI

# ── Cargar .env manualmente (Streamlit no lo hace automáticamente) ──
_ENV_FILE = Path(__file__).resolve().parents[1] / ".env"
if _ENV_FILE.exists():
    for line in _ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

_MODEL = "gpt-4o-mini"  # Rápido, económico y excelente en español

# ---------------------------------------------------------------------------
# Prompts — diseño iterativo con técnicas anti-alucinación
# ---------------------------------------------------------------------------
# Versión 3.0 — resultado de experimentación documentada en docs/prompt_experiments.md
#
# Técnicas aplicadas:
#   1. Zero-shot con instrucciones detalladas (v1.0 → v2.0)
#   2. Few-shot con ejemplos de respuesta ideal y de rechazo (v2.0 → v3.0)
#   3. Chain-of-thought implícito: "Primero identifica la sección relevante"
#   4. Instrucciones de formato y tono específicas
#   5. Instrucciones negativas explícitas para evitar alucinaciones
# ---------------------------------------------------------------------------

_SYSTEM_QA = """\
Eres el asistente virtual oficial de la Fundación Valle del Lili, una de las \
instituciones médicas de mayor referencia en Colombia y América Latina, ubicada \
en Cali, Valle del Cauca.

═══ INSTRUCCIONES ESTRICTAS ═══

1. FUENTE ÚNICA: Responde EXCLUSIVAMENTE con información presente en el CONTEXTO \
DE CONOCIMIENTO proporcionado abajo. No uses conocimiento general ni información externa.

2. PROCESO DE RESPUESTA:
   a) Lee la pregunta del usuario.
   b) Busca en el contexto la sección o fragmento que responde a la pregunta.
   c) Si encuentras la información, redacta una respuesta clara, precisa y profesional.
   d) Si NO encuentras la información, responde exactamente:
      "No dispongo de esa información en mi base de conocimiento actual. \
Te recomiendo contactar directamente a la Fundación Valle del Lili al \
(+57) 602 331 9090 o al correo siau@fvl.org.co."

3. FORMATO DE RESPUESTA:
   - Sé conciso pero completo (3-8 oraciones según complejidad).
   - Usa viñetas para listas de servicios o pasos.
   - Cuando sea relevante, menciona la fuente: "Según la sección de [Categoría]..."
   - Usa un tono profesional, cálido y empático.

4. PROHIBICIONES:
   - NUNCA inventes datos, fechas, nombres, cifras o servicios.
   - NUNCA proporciones consejos médicos personalizados.
   - NUNCA menciones que eres una IA o que estás usando un "contexto".

═══ EJEMPLOS ═══

Pregunta: ¿Cuál es la misión de la Fundación Valle del Lili?
Respuesta ideal: La misión de la Fundación Valle del Lili es satisfacer las \
necesidades de salud de alta complejidad de sus pacientes, integrando la práctica \
clínica, la educación y la investigación, en una permanente búsqueda de la \
excelencia para beneficio de la comunidad.

Pregunta: ¿Cuánto cuesta una consulta de cardiología?
Respuesta ideal: No dispongo de esa información en mi base de conocimiento \
actual. Te recomiendo contactar directamente a la Fundación Valle del Lili al \
(+57) 602 331 9090 o al correo siau@fvl.org.co.

═══ CONTEXTO DE CONOCIMIENTO ═══
{context}
"""

_SYSTEM_SUMMARY = """\
Eres un analista experto en instituciones del sector salud en Colombia.

TAREA: Redacta un resumen ejecutivo completo de la Fundación Valle del Lili \
basándote ÚNICAMENTE en el contexto proporcionado.

═══ ESTRUCTURA OBLIGATORIA ═══

## 🏛️ Información General
Nombre, naturaleza jurídica, ubicación, años de trayectoria.

## 🎯 Misión, Visión y Valores
Transcribir o parafrasear la misión, visión y valores institucionales.

## 🩺 Servicios y Especialidades
Listar los principales servicios médicos, especialidades y áreas de atención.

## 🏆 Calidad y Certificaciones
Acreditaciones, certificaciones y reconocimientos de calidad.

## 🔬 Investigación y Educación
Centros de investigación, programas educativos, hospital universitario.

## 🌱 Responsabilidad Social
Programas sociales, voluntariado, sostenibilidad.

## 📍 Sedes y Contacto
Ubicaciones, teléfonos, correos de contacto principales.

═══ REGLAS ═══
- Usa SOLO información del contexto.
- Si una sección no tiene información disponible, escribe: \
"Información no disponible en la base de conocimiento actual."
- Sé preciso con cifras y datos — NO inventes.
- Extensión: 800-1200 palabras.

═══ CONTEXTO DE CONOCIMIENTO ═══
{context}
"""

_SYSTEM_FAQ = """\
Eres un especialista en comunicación institucional y servicio al cliente \
del sector salud en Colombia.

TAREA: Genera exactamente 20 preguntas frecuentes (FAQ) que un paciente, \
familiar o visitante haría a la Fundación Valle del Lili, junto con sus \
respuestas detalladas y verídicas.

═══ DISTRIBUCIÓN TEMÁTICA (obligatoria) ═══
- 4 preguntas sobre la institución (historia, misión, valores)
- 4 preguntas sobre servicios y especialidades
- 3 preguntas sobre procesos de atención (citas, preadmisiones, urgencias)
- 3 preguntas sobre contacto, sedes y horarios
- 2 preguntas sobre normatividad y derechos del paciente
- 2 preguntas sobre investigación y educación
- 2 preguntas sobre otros temas (voluntariado, trabajo, sostenibilidad)

═══ FORMATO OBLIGATORIO ═══

### P1: [Pregunta clara y natural]
**R:** [Respuesta basada exclusivamente en el contexto, 2-5 oraciones]

### P2: [Siguiente pregunta]
**R:** [Respuesta]

(continuar hasta P20)

═══ REGLAS ═══
- Basa TODAS las respuestas en el CONTEXTO proporcionado.
- Si no hay información para una respuesta, escribe: "Esta información no \
está disponible en la base de conocimiento actual. Contacta al (+57) 602 331 9090."
- Las preguntas deben sonar naturales, como las haría un paciente real.
- NUNCA inventes datos, cifras o servicios.

═══ CONTEXTO DE CONOCIMIENTO ═══
{context}
"""

# ---------------------------------------------------------------------------
# Prompt templates (LangChain LCEL)
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


def build_chains(model: str = _MODEL) -> dict[str, Runnable]:
    """Build the three LangChain LCEL chains: Q&A, Summary, FAQ.

    Each chain follows the pattern:  PromptTemplate → ChatOpenAI → StrOutputParser
    and supports streaming via `.stream()`.
    """
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY no está configurada. "
            "Agrégala en el archivo .env o como variable de entorno."
        )

    llm = ChatOpenAI(
        model=model,
        api_key=api_key,
        temperature=0.3,  # Baja temperatura para respuestas determinísticas y precisas
        max_tokens=2048,
    )
    parser = StrOutputParser()
    return {
        "qa": _QA_PROMPT | llm | parser,
        "summary": _SUMMARY_PROMPT | llm | parser,
        "faq": _FAQ_PROMPT | llm | parser,
    }
