from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st

from app.engine import generate_faq, generate_summary, stream_answer
from app.retriever import Retriever, build_retriever

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
CHROMA_DIR = _ROOT / ".chroma"


@st.cache_resource(show_spinner="Indexando base de conocimiento…")
def get_retriever() -> Retriever:
    return build_retriever(KNOWLEDGE_DIR, CHROMA_DIR)


retriever = get_retriever()
stats = retriever.stats()

# ---------------------------------------------------------------------------
# Sidebar — estadísticas del knowledge base
# ---------------------------------------------------------------------------

with st.sidebar:
    st.image(
        "https://valledellili.org/wp-content/uploads/2021/05/logo-fvl.svg",
        width="stretch",
    )
    st.markdown("## 📚 Base de Conocimiento")
    st.metric("Documentos indexados", stats["total_documents"])
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
    st.caption("Modelo: llama3.2 (Ollama) · RAG semántico")

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
        ask = st.button("Consultar", type="primary", width="stretch")

    if ask and question.strip():
        with st.spinner("Buscando documentos relevantes…"):
            context = retriever.retrieve(question, k=5)
        st.markdown("---")
        st.markdown(f"**Pregunta:** {question}")
        st.markdown("**Respuesta:**")
        placeholder = st.empty()
        answer = ""
        try:
            for chunk in stream_answer(context, question):
                answer += chunk
                placeholder.markdown(answer + "▌")
            placeholder.markdown(answer)
        except Exception as e:
            st.error(f"Error al invocar el modelo: {e}")
        if answer:
            st.session_state["last_qa_question"] = question
            st.session_state["last_qa_answer"] = answer

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
        "a partir de los documentos más representativos indexados."
    )

    if st.button("Generar Resumen Ejecutivo", type="primary"):
        with st.spinner("Seleccionando documentos representativos…"):
            broad_context = retriever.retrieve_broad(k=20)
        with st.spinner("Redactando resumen… (puede tardar 1–2 min)"):
            try:
                summary = generate_summary(broad_context)
            except Exception as e:
                st.error(f"Error al invocar el modelo: {e}")
                summary = None
        if summary:
            st.session_state["summary"] = summary

    if "summary" in st.session_state:
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
        with st.spinner("Seleccionando documentos representativos…"):
            broad_context = retriever.retrieve_broad(k=20)
        with st.spinner("Generando preguntas frecuentes… (puede tardar 1–2 min)"):
            try:
                faq = generate_faq(broad_context)
            except Exception as e:
                st.error(f"Error al invocar el modelo: {e}")
                faq = None
        if faq:
            st.session_state["faq"] = faq

    if "faq" in st.session_state:
        st.markdown("---")
        st.markdown(st.session_state["faq"])
        st.download_button(
            label="⬇️ Descargar FAQ (.md)",
            data=st.session_state["faq"],
            file_name="faq_fvl.md",
            mime="text/markdown",
        )
