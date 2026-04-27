from __future__ import annotations

import csv
import io
import os
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# ── Cargar .env ANTES de cualquier import que lo necesite ──
_ENV_FILE = _ROOT / ".env"
if _ENV_FILE.exists():
    for _line in _ENV_FILE.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())

import streamlit as st  # noqa: E402

from app.engine import build_chains  # noqa: E402
from app.knowledge_loader import load_knowledge_base  # noqa: E402
from app.retriever import build_retriever  # noqa: E402

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
# Custom CSS — tema claro forzado + paleta institucional FVL
# ---------------------------------------------------------------------------

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    /* ── Fondo degradado claro ── */
    .stApp { background: linear-gradient(135deg, #f0f4f8 0%, #e8eef5 100%); }

    /* ── Header azul institucional ── */
    .main-header {
        background: linear-gradient(135deg, #1a5276 0%, #2e86c1 50%, #3498db 100%);
        padding: 2rem 2.5rem; border-radius: 16px; margin-bottom: 1.5rem;
        box-shadow: 0 8px 32px rgba(26, 82, 118, 0.25);
    }
    .main-header h1, .main-header p { color: #ffffff !important; }
    .main-header h1 { margin: 0; font-size: 2rem; font-weight: 700; }
    .main-header p  { margin: 0.5rem 0 0 0; opacity: 0.9; font-weight: 300; }

    /* ── Tarjetas métricas ── */
    .metric-card {
        background: #ffffff; border-radius: 12px; padding: 1.2rem;
        box-shadow: 0 2px 12px rgba(0,0,0,0.08); border-left: 4px solid #2e86c1;
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .metric-card:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,0.12); }
    .metric-card .label { font-size: 0.8rem; color: #555555 !important; font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em; }
    .metric-card .value { font-size: 1.8rem; font-weight: 700; color: #1a5276 !important; margin-top: 0.2rem; }

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; background: #ffffff; padding: 8px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.04); }
    .stTabs [data-baseweb="tab"] { border-radius: 8px; padding: 10px 20px; font-weight: 500; color: #1a5276 !important; }
    .stTabs [aria-selected="true"] { background: linear-gradient(135deg, #1a5276, #2e86c1) !important; color: #ffffff !important; }

    /* ── Input ── */
    .stTextInput > div > div > input { border-radius: 10px; border: 2px solid #ccc; padding: 12px 16px; font-size: 1rem; }
    .stTextInput > div > div > input:focus { border-color: #2e86c1; box-shadow: 0 0 0 3px rgba(46,134,193,0.15); }

    /* ── Botón primario ── */
    .stButton > button[kind="primary"] { background: linear-gradient(135deg, #1a5276, #2e86c1) !important; color: #ffffff !important; border: none; border-radius: 10px; padding: 10px 24px; font-weight: 600; }
    .stButton > button[kind="primary"]:hover { transform: translateY(-1px); box-shadow: 0 4px 15px rgba(26,82,118,0.3); }

    /* ── Caja de respuesta ── */
    .response-box { background: #ffffff; border-radius: 12px; padding: 1.5rem; box-shadow: 0 2px 12px rgba(0,0,0,0.08); border-left: 4px solid #27ae60; margin-top: 1rem; }
    .response-box, .response-box * { color: #1a1a2e !important; }

    /* ── Sidebar oscuro ── */
    section[data-testid="stSidebar"] { background: linear-gradient(180deg, #1a2332 0%, #1a3a5c 100%) !important; }
    section[data-testid="stSidebar"] * { color: #e8eef5 !important; }
    section[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.15) !important; }

    /* ── Badges ── */
    .model-badge { display: inline-block; background: linear-gradient(135deg, #27ae60, #2ecc71); color: #ffffff !important; padding: 4px 12px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; }
    .timer-badge { display: inline-block; background: rgba(46,134,193,0.15); color: #1a5276 !important; padding: 4px 12px; border-radius: 20px; font-size: 0.8rem; font-weight: 600; }

    /* ── Expanders ── */
    details summary span { color: #1a5276 !important; font-weight: 500; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Cached resources
# ---------------------------------------------------------------------------

KNOWLEDGE_DIR = _ROOT / "knowledge"
VECTORSTORE_DIR = _ROOT / "vectorstore"


@st.cache_resource(show_spinner="Cargando base de conocimiento…")
def get_knowledge() -> tuple[str, dict]:
    return load_knowledge_base(KNOWLEDGE_DIR)


@st.cache_resource(show_spinner="Conectando al vector store…")
def get_retriever(_cache_buster=2):
    return build_retriever(KNOWLEDGE_DIR, VECTORSTORE_DIR)


@st.cache_resource(show_spinner="Inicializando GPT-4o-mini…")
def get_chains() -> dict:
    return build_chains()


# GPT-4o-mini soporta 128k tokens de contexto.
# Usamos hasta 90k chars (~25k tokens) para dejar espacio al prompt y la respuesta.
_MAX_CONTEXT_CHARS = 90_000

context_full, stats = get_knowledge()
context_broad = context_full[:_MAX_CONTEXT_CHARS]
retriever = get_retriever()
chains = get_chains()

# Update stats with actual indexed count from vector store
stats["total_documents"] = retriever.count

# ---------------------------------------------------------------------------
# Session state init
# ---------------------------------------------------------------------------

if "qa_history" not in st.session_state:
    st.session_state["qa_history"] = []

# ---------------------------------------------------------------------------
# Sidebar — estadísticas del knowledge base
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown(
        """
        <div style="text-align:center; padding: 1rem 0;">
            <div style="font-size: 2rem; font-weight: 700; color: #ffffff;">🏥</div>
            <div style="font-size: 1.1rem; font-weight: 600; color: #ffffff; letter-spacing: 0.05em;">
                Fundación<br>Valle del Lili
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("---")

    st.markdown("### 📊 Base de Conocimiento")
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        st.metric("Documentos", stats["total_documents"])
    with col_m2:
        st.metric("Categorías", len(stats["categories"]))

    st.metric("Chunks indexados", f"{retriever.count:,}")

    st.markdown("---")

    st.markdown("### 📂 Categorías")
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

    st.markdown("---")

    st.markdown(
        '<span class="model-badge">GPT-4o-mini · OpenAI · 128k ctx</span>',
        unsafe_allow_html=True,
    )
    st.caption("Módulo 1 — Capa Semántica FVL")
    st.caption("Equipo: Jhonatan, Nicolas, Mateo, Jorge")

# ---------------------------------------------------------------------------
# Main area — Header
# ---------------------------------------------------------------------------

st.markdown(
    """
    <div class="main-header">
        <h1>🏥 Sistema Q&A — Fundación Valle del Lili</h1>
        <p>Base de conocimiento semántico extraída del sitio oficial · 97 documentos · 9 categorías</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Metrics row
# ---------------------------------------------------------------------------

mc1, mc2, mc3, mc4 = st.columns(4)
with mc1:
    st.markdown(
        '<div class="metric-card"><div class="label">Documentos Indexados</div>'
        f'<div class="value">{stats["total_documents"]}</div></div>',
        unsafe_allow_html=True,
    )
with mc2:
    st.markdown(
        '<div class="metric-card"><div class="label">Categorías</div>'
        f'<div class="value">{len(stats["categories"])}</div></div>',
        unsafe_allow_html=True,
    )
with mc3:
    st.markdown(
        '<div class="metric-card"><div class="label">Modelo LLM</div>'
        '<div class="value" style="font-size:1.1rem">GPT-4o-mini</div></div>',
        unsafe_allow_html=True,
    )
with mc4:
    st.markdown(
        '<div class="metric-card"><div class="label">Framework</div>'
        '<div class="value" style="font-size:1.2rem">LangChain</div></div>',
        unsafe_allow_html=True,
    )

st.markdown("")

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------

tab_qa, tab_summary, tab_faq = st.tabs(
    ["💬 Preguntas y Respuestas", "📋 Resumen Ejecutivo", "❓ FAQ Generadas"]
)

# ---------------------------------------------------------------------------
# Tab 1: Q&A
# ---------------------------------------------------------------------------

with tab_qa:
    st.subheader("Hazle una pregunta al asistente")
    st.markdown(
        "Escribe cualquier pregunta sobre la Fundación Valle del Lili. "
        "El asistente responderá **exclusivamente** con información de la base de conocimiento."
    )

    question = st.text_input(
        "Tu pregunta:",
        placeholder="Ej: ¿Cuáles son las especialidades médicas disponibles?",
        key="qa_input",
    )

    col_btn, col_space = st.columns([1, 5])
    with col_btn:
        ask = st.button("🔍 Consultar", type="primary", use_container_width=True)

    if ask and question.strip():
        st.markdown("---")
        st.markdown(f"**🧑 Pregunta:** {question}")

        start_time = time.time()
        placeholder = st.empty()
        full_answer = ""
        try:
            qa_context = retriever.retrieve(question, k=20)
            for chunk in chains["qa"].stream({"context": qa_context, "question": question}):
                full_answer += chunk
                placeholder.markdown(
                    f'<div class="response-box">🤖 **Respuesta:**\n\n{full_answer}▌</div>',
                    unsafe_allow_html=True,
                )
            elapsed = time.time() - start_time
            placeholder.markdown(
                f'<div class="response-box">🤖 **Respuesta:**\n\n'
                f'{full_answer or "_Sin respuesta — el modelo no generó texto._"}</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<span class="timer-badge">⏱️ {elapsed:.1f}s</span>',
                unsafe_allow_html=True,
            )
            with st.expander("🔍 Debug: Contexto recuperado del vector store"):
                st.text(f"Longitud del contexto: {len(qa_context)} caracteres")
                st.code(qa_context[:3000], language="markdown")
        except Exception as e:
            placeholder.error(f"Error del modelo: {e}")

        if full_answer:
            st.session_state["qa_history"].append(
                {"question": question, "answer": full_answer, "time": f"{elapsed:.1f}s"}
            )

    if "last_qa_answer" in st.session_state:
        st.divider()
        st.subheader("Registro de pruebas (para las 20 preguntas)")

        if "qa_log" not in st.session_state:
            st.session_state["qa_log"] = []

        col_a, col_b, col_c = st.columns([2, 2, 3])
        with col_a:
            add_to_log = st.button("Agregar a resultados", use_container_width=True)
        with col_b:
            clear_log = st.button("Limpiar resultados", use_container_width=True)

        if add_to_log:
            st.session_state["qa_log"].append(
                {
                    "question": st.session_state["last_qa_question"],
                    "answer": st.session_state["last_qa_answer"],
                }
            )

        if clear_log:
            st.session_state["qa_log"] = []

        csv_buffer = io.StringIO()
        writer = csv.DictWriter(csv_buffer, fieldnames=["question", "answer"])
        writer.writeheader()
        writer.writerows(st.session_state["qa_log"])

        with col_c:
            st.download_button(
                label=f"Descargar CSV ({len(st.session_state['qa_log'])})",
                data=csv_buffer.getvalue(),
                file_name="qa_results.csv",
                mime="text/csv",
                use_container_width=True,
            )
        st.caption("Sugerencia: guardar el archivo final como `tests/qa_results.csv` para el informe.")

    elif ask and not question.strip():
        st.warning("Por favor escribe una pregunta antes de consultar.")

    # Historial de preguntas
    if st.session_state["qa_history"]:
        st.markdown("---")
        st.markdown("### 📜 Historial de esta sesión")
        for i, entry in enumerate(reversed(st.session_state["qa_history"]), 1):
            with st.expander(f"Q{i}: {entry['question']} ({entry['time']})"):
                st.markdown(f"**Respuesta:** {entry['answer']}")

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
    st.subheader("📋 Resumen Ejecutivo de la Institución")
    st.markdown(
        "Genera un resumen estructurado de la Fundación Valle del Lili "
        "a partir de todos los documentos indexados."
    )

    if st.button("Generar Resumen Ejecutivo", type="primary", key="btn_summary"):
        st.markdown("---")
        start_time = time.time()
        placeholder = st.empty()
        full_summary = ""
        try:
            for chunk in chains["summary"].stream({"context": context_broad}):
                full_summary += chunk
                placeholder.markdown(full_summary + "▌")
            elapsed = time.time() - start_time
            placeholder.markdown(full_summary or "_Sin respuesta — el modelo no generó texto._")
            st.markdown(
                f'<span class="timer-badge">⏱️ {elapsed:.1f}s</span>',
                unsafe_allow_html=True,
            )
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
    st.subheader("❓ Preguntas Frecuentes — Generadas por IA")
    st.markdown(
        "Genera automáticamente las 20 preguntas más frecuentes que un paciente "
        "o visitante haría, con sus respuestas basadas en la base de conocimiento."
    )

    if st.button("Generar FAQ", type="primary", key="btn_faq"):
        st.markdown("---")
        start_time = time.time()
        placeholder = st.empty()
        full_faq = ""
        try:
            for chunk in chains["faq"].stream({"context": context_broad}):
                full_faq += chunk
                placeholder.markdown(full_faq + "▌")
            elapsed = time.time() - start_time
            placeholder.markdown(full_faq or "_Sin respuesta — el modelo no generó texto._")
            st.markdown(
                f'<span class="timer-badge">⏱️ {elapsed:.1f}s</span>',
                unsafe_allow_html=True,
            )
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
