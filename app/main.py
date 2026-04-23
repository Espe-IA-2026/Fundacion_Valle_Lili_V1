from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st  # noqa: E402

from app.engine import build_chains  # noqa: E402
from app.knowledge_loader import load_knowledge_base  # noqa: E402

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Asistente FVL — Módulo 1",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Cached resources
# ---------------------------------------------------------------------------

KNOWLEDGE_DIR = _ROOT / "knowledge"


@st.cache_resource(show_spinner="Cargando base de conocimiento…")
def get_knowledge() -> tuple[str, dict]:
    return load_knowledge_base(KNOWLEDGE_DIR)


@st.cache_resource(show_spinner="Inicializando modelo…")
def get_chains() -> dict:
    return build_chains()


_MAX_CONTEXT_CHARS = 38_000  # ~11k tokens — deja ~5k tokens para respuesta dentro de 16k ctx

context_full, stats = get_knowledge()
context = context_full[:_MAX_CONTEXT_CHARS]
chains = get_chains()

# ---------------------------------------------------------------------------
# Sidebar — estadísticas del knowledge base
# ---------------------------------------------------------------------------

with st.sidebar:
    st.image(
        "https://valledellili.org/wp-content/uploads/2021/05/logo-fvl.svg",
        width="stretch",
    )
    st.markdown("## 📚 Base de Conocimiento")
    st.metric("Documentos cargados", stats["total_documents"])
    st.metric("Caracteres en contexto", f"{stats['estimated_chars']:,}")
    st.divider()
    st.markdown("### Categorías")
    category_labels = {
        "01_organizacion": "🏛️ Organización",
        "02_servicios": "🩺 Servicios",
        "03_talento_humano": "👨‍⚕️ Talento Humano",
        "04_sedes_ubicaciones": "📍 Sedes",
        "05_contacto": "📞 Contacto",
        "06_normatividad": "⚖️ Normatividad",
        "07_investigacion": "🔬 Investigación",
        "08_educacion": "🎓 Educación",
        "09_noticias": "📰 Noticias",
        "10_multimedia": "🎬 Multimedia",
    }
    for cat, docs in stats["categories"].items():
        label = category_labels.get(cat, cat)
        with st.expander(f"{label} ({len(docs)})"):
            for doc in docs:
                st.caption(f"• {doc}")
    st.divider()
    st.caption("Módulo 1 — Capa Semántica FVL")
    st.caption("Modelo: llama3.2:1b (Ollama) · Contexto 38k chars")

# ---------------------------------------------------------------------------
# Main area
# ---------------------------------------------------------------------------

st.title("🏥 Sistema Q&A — Fundación Valle del Lili")
st.caption(
    "Base de conocimiento extraída del sitio oficial. "
    "Las respuestas se generan exclusivamente a partir del contenido indexado."
)
st.divider()

tab_qa, tab_summary, tab_faq = st.tabs(["💬 Preguntas y Respuestas", "📋 Resumen Ejecutivo", "❓ FAQ"])

# ---------------------------------------------------------------------------
# Tab 1: Q&A
# ---------------------------------------------------------------------------

with tab_qa:
    st.subheader("Hazle una pregunta al asistente")
    st.markdown(
        "Escribe cualquier pregunta sobre la Fundación Valle del Lili. "
        "El asistente responderá basándose únicamente en la base de conocimiento."
    )

    question = st.text_input(
        "Tu pregunta:",
        placeholder="¿Cuáles son las especialidades médicas disponibles?",
        key="qa_input",
    )

    col1, col2 = st.columns([1, 5])
    with col1:
        ask = st.button("Consultar", type="primary", use_container_width=True)

    if ask and question.strip():
        st.markdown("---")
        st.markdown(f"**Pregunta:** {question}")
        st.markdown("**Respuesta:**")
        placeholder = st.empty()
        full_answer = ""
        try:
            for chunk in chains["qa"].stream({"context": context, "question": question}):
                full_answer += chunk
                placeholder.markdown(full_answer + "▌")
            placeholder.markdown(full_answer or "_Sin respuesta — el modelo no generó texto._")
        except Exception as e:
            placeholder.error(f"Error del modelo: {e}")
        if full_answer:
            st.session_state["last_qa_question"] = question
            st.session_state["last_qa_answer"] = full_answer

    elif "last_qa_answer" in st.session_state:
        st.markdown("---")
        st.markdown(f"**Pregunta:** {st.session_state['last_qa_question']}")
        st.markdown("**Respuesta:**")
        st.markdown(st.session_state["last_qa_answer"])

    elif ask and not question.strip():
        st.warning("Por favor escribe una pregunta antes de consultar.")

    with st.expander("💡 Preguntas de ejemplo"):
        example_questions = [
            "¿Cuál es la misión de la Fundación Valle del Lili?",
            "¿Qué especialidades médicas ofrece la institución?",
            "¿Cómo puedo solicitar una cita médica?",
            "¿Dónde están ubicadas las sedes de la fundación?",
            "¿Qué es el programa de cuidados paliativos?",
            "¿Cuáles son los derechos del paciente?",
            "¿La fundación tiene programas de investigación clínica?",
            "¿Qué convenios con entidades de salud tiene la institución?",
            "¿Cómo puedo solicitar mi historia clínica?",
            "¿Qué certificaciones de calidad posee la fundación?",
        ]
        for q in example_questions:
            st.markdown(f"- {q}")

# ---------------------------------------------------------------------------
# Tab 2: Resumen Ejecutivo
# ---------------------------------------------------------------------------

with tab_summary:
    st.subheader("Resumen Ejecutivo de la Institución")
    st.markdown(
        "Genera un resumen estructurado de la Fundación Valle del Lili "
        "a partir de todos los documentos indexados."
    )

    if st.button("Generar Resumen Ejecutivo", type="primary"):
        st.markdown("---")
        placeholder = st.empty()
        full_summary = ""
        try:
            for chunk in chains["summary"].stream({"context": context}):
                full_summary += chunk
                placeholder.markdown(full_summary + "▌")
            placeholder.markdown(full_summary or "_Sin respuesta — el modelo no generó texto._")
        except Exception as e:
            placeholder.error(f"Error del modelo: {e}")
        if full_summary:
            st.session_state["summary"] = full_summary

    elif "summary" in st.session_state:
        st.markdown("---")
        st.markdown(st.session_state["summary"])
        st.download_button(
            label="⬇️ Descargar resumen (.md)",
            data=st.session_state["summary"],
            file_name="resumen_ejecutivo_fvl.md",
            mime="text/markdown",
        )

# ---------------------------------------------------------------------------
# Tab 3: FAQ
# ---------------------------------------------------------------------------

with tab_faq:
    st.subheader("Preguntas Frecuentes — Generadas por IA")
    st.markdown(
        "Genera automáticamente las 20 preguntas más frecuentes que un paciente "
        "o visitante haría, con sus respuestas basadas en la base de conocimiento."
    )

    if st.button("Generar FAQ", type="primary"):
        st.markdown("---")
        placeholder = st.empty()
        full_faq = ""
        try:
            for chunk in chains["faq"].stream({"context": context}):
                full_faq += chunk
                placeholder.markdown(full_faq + "▌")
            placeholder.markdown(full_faq or "_Sin respuesta — el modelo no generó texto._")
        except Exception as e:
            placeholder.error(f"Error del modelo: {e}")
        if full_faq:
            st.session_state["faq"] = full_faq

    elif "faq" in st.session_state:
        st.markdown("---")
        st.markdown(st.session_state["faq"])
        st.download_button(
            label="⬇️ Descargar FAQ (.md)",
            data=st.session_state["faq"],
            file_name="faq_fvl.md",
            mime="text/markdown",
        )
