"""Dashboard Streamlit profesional — Asistente Virtual FVL.

Pestañas disponibles:
- **💬 Q&A**: chatbot conversacional con historial y streaming de respuestas.
- **📋 Resumen**: síntesis estructurada de un tema institucional.
- **❓ FAQ**: preguntas frecuentes generadas desde los documentos.
"""

import os
import uuid

import streamlit as st
from dotenv import load_dotenv

from app.engine import (
    build_chain,
    build_faq_chain,
    build_summary_chain,
    get_faq,
    get_summary,
    load_knowledge_base,
    stream_response,
)
from app_agent.engine import stream_agent_response

load_dotenv()

st.set_page_config(
    page_title="Asistente Virtual — Fundación Valle del Lili",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS profesional ────────────────────────────────────────────────────────────
_CSS = """
<style>
/* ── Variables ── */
:root {
    --fvl-blue:      #002D72;
    --fvl-blue-mid:  #003D9A;
    --fvl-teal:      #0077B5;
    --fvl-teal-bg:   #EBF5FB;
    --fvl-green:     #047857;
    --fvl-border:    #D1D9E0;
    --fvl-bg:        #F5F7FA;
    --fvl-white:     #FFFFFF;
    --fvl-gray:      #5B6475;
    --fvl-gray-lt:   #F0F2F5;
    --radius:        10px;
    --shadow:        0 2px 8px rgba(0,0,0,0.08);
}

/* ── Layout principal ── */
.main .block-container {
    padding-top: 1.5rem;
    padding-bottom: 3rem;
    max-width: 1100px;
}
.stApp {
    background-color: var(--fvl-bg);
}

/* ── Headings ── */
h1 { color: var(--fvl-blue) !important; font-weight: 800 !important; letter-spacing: -0.02em; }
h2 { color: var(--fvl-blue) !important; font-weight: 700 !important; }
h3 { color: var(--fvl-teal) !important; font-weight: 600 !important; }

/* ── Pestañas ── */
button[data-baseweb="tab"] {
    font-weight: 600 !important;
    font-size: 0.92rem !important;
    padding: 10px 22px !important;
    border-radius: 8px 8px 0 0 !important;
    color: var(--fvl-gray) !important;
    transition: color 0.2s !important;
}
button[data-baseweb="tab"]:hover {
    color: var(--fvl-blue) !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
    color: var(--fvl-blue) !important;
    border-bottom: 3px solid var(--fvl-blue) !important;
    background: transparent !important;
}

/* ── Botón de formulario (submit) ── */
.stFormSubmitButton > button {
    width: 100%;
    background-color: var(--fvl-blue) !important;
    color: white !important;
    border: none !important;
    border-radius: var(--radius) !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
    padding: 0.65rem 1.5rem !important;
    transition: background 0.2s !important;
    letter-spacing: 0.01em !important;
}
.stFormSubmitButton > button:hover {
    background-color: var(--fvl-blue-mid) !important;
}

/* ── Botones normales ── */
.stButton > button {
    border-radius: var(--radius) !important;
    border: 1.5px solid var(--fvl-border) !important;
    color: var(--fvl-gray) !important;
    background: var(--fvl-white) !important;
    font-weight: 500 !important;
    font-size: 0.82rem !important;
    transition: all 0.2s !important;
    padding: 0.35rem 0.75rem !important;
}
.stButton > button:hover {
    border-color: var(--fvl-teal) !important;
    color: var(--fvl-teal) !important;
    background: var(--fvl-teal-bg) !important;
}

/* ── Botón de descarga ── */
.stDownloadButton > button {
    background-color: var(--fvl-green) !important;
    color: white !important;
    border: none !important;
    border-radius: var(--radius) !important;
    font-weight: 600 !important;
    transition: opacity 0.2s !important;
}
.stDownloadButton > button:hover {
    opacity: 0.88 !important;
}

/* ── Chat messages ── */
[data-testid="stChatMessage"] {
    border-radius: var(--radius) !important;
    border: 1px solid var(--fvl-border) !important;
    background: var(--fvl-white) !important;
    margin-bottom: 0.5rem !important;
    box-shadow: var(--shadow) !important;
}

/* ── Chat input ── */
[data-testid="stChatInput"] > div {
    border-radius: var(--radius) !important;
    border: 1.5px solid var(--fvl-border) !important;
    background: var(--fvl-white) !important;
    box-shadow: var(--shadow) !important;
}
[data-testid="stChatInput"] > div:focus-within {
    border-color: var(--fvl-teal) !important;
    box-shadow: 0 0 0 3px rgba(0,119,181,0.12) !important;
}

/* ── Text inputs ── */
.stTextInput > div > div > input {
    border-radius: var(--radius) !important;
    border: 1.5px solid var(--fvl-border) !important;
    background: var(--fvl-white) !important;
    padding: 0.6rem 0.9rem !important;
    font-size: 0.95rem !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
}
.stTextInput > div > div > input:focus {
    border-color: var(--fvl-teal) !important;
    box-shadow: 0 0 0 3px rgba(0,119,181,0.12) !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background-color: var(--fvl-white) !important;
    border-right: 1px solid var(--fvl-border) !important;
}
[data-testid="stSidebarContent"] {
    padding: 1.25rem 1rem !important;
}

/* ── Expanders ── */
.streamlit-expanderHeader {
    font-weight: 600 !important;
    color: var(--fvl-blue) !important;
    font-size: 0.9rem !important;
}
details[data-testid="stExpander"] {
    border: 1px solid var(--fvl-border) !important;
    border-radius: var(--radius) !important;
    background: var(--fvl-white) !important;
    margin-bottom: 0.75rem !important;
}

/* ── Alertas / Info ── */
[data-testid="stAlert"] {
    border-radius: var(--radius) !important;
}

/* ── Divider ── */
hr {
    border-color: var(--fvl-border) !important;
    margin: 1.2rem 0 !important;
}

/* ── Metrics en sidebar ── */
[data-testid="stMetric"] {
    background: var(--fvl-gray-lt);
    border-radius: var(--radius);
    padding: 0.75rem 1rem;
    border: 1px solid var(--fvl-border);
}

/* ── Caption / pequeño texto ── */
.stCaption {
    color: var(--fvl-gray) !important;
    font-size: 0.84rem !important;
}
</style>
"""

_EXAMPLE_QUERIES = [
    "¿Cuáles son los servicios de cardiología?",
    "¿Dónde está ubicada la sede norte?",
    "¿Qué es el programa de trasplantes?",
    "¿Cómo solicito una cita médica?",
    "¿Cuáles son los horarios de urgencias?",
]

_EXAMPLE_TOPICS = [
    "Cardiología",
    "Trasplante de órganos",
    "Urgencias",
    "Oncología",
    "Atención al paciente",
]


@st.cache_resource(show_spinner="Cargando base de conocimiento institucional…")
def load_resources() -> tuple:
    """Carga el knowledge base y construye las tres cadenas LangChain una sola vez.

    Returns:
        Tupla ``(qa_chain, summary_chain, faq_chain, context)``.
    """
    knowledge_dir = os.getenv("KNOWLEDGE_DIR", "./knowledge")
    context = load_knowledge_base(knowledge_dir)
    qa_chain = build_chain()
    summary_chain = build_summary_chain()
    faq_chain = build_faq_chain()
    return qa_chain, summary_chain, faq_chain, context


def _inject_css() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def _render_sidebar(knowledge_loaded: bool = True) -> None:
    """Renderiza el panel lateral con branding y guía de uso."""
    with st.sidebar:
        st.markdown(
            """
            <div style="text-align:center; padding:1.25rem 0 0.75rem;">
                <div style="font-size:3.2rem; line-height:1;">🏥</div>
                <div style="font-size:1.05rem; font-weight:800; color:#002D72;
                            line-height:1.3; margin-top:0.5rem;">
                    Fundación<br>Valle del Lili
                </div>
                <div style="font-size:0.74rem; color:#5B6475; margin-top:0.3rem;
                            letter-spacing:0.04em; text-transform:uppercase;">
                    Asistente Virtual · Módulo 1+2
                </div>
            </div>
            <hr style="border-color:#D1D9E0; margin:0.5rem 0 1rem;">
            """,
            unsafe_allow_html=True,
        )

        if knowledge_loaded:
            st.success("Base de conocimiento cargada", icon="✅")
        else:
            st.error("Knowledge base no disponible", icon="❌")

        st.markdown(
            "<p style='font-size:0.82rem;font-weight:700;color:#002D72;"
            "text-transform:uppercase;letter-spacing:0.06em;margin:1.25rem 0 0.5rem;'>Cómo usar</p>",
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            **💬 Q&A — Preguntas y Respuestas**
            Consulta sobre servicios, sedes, especialidades y procedimientos. El asistente
            responde en tiempo real.

            **📋 Resumen**
            Obtén una síntesis estructurada con secciones claras y referencias a los
            documentos fuente.

            **❓ FAQ**
            Genera las preguntas más frecuentes sobre un tema, con respuestas basadas
            en los documentos oficiales.

            **🤖 Agente RAG**
            Agente con recuperación semántica dinámica. Consulta el índice vectorial
            para responder con fragmentos exactos de los documentos institucionales.
            Mantiene memoria de la sesión activa.
            """,
            help=None,
        )

        st.markdown(
            "<p style='font-size:0.82rem;font-weight:700;color:#002D72;"
            "text-transform:uppercase;letter-spacing:0.06em;margin:1.25rem 0 0.5rem;'>Acerca de</p>",
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            Las respuestas se generan **exclusivamente** a partir de los documentos
            institucionales. No se inventa ni extrapola información.
            """,
        )

        st.divider()
        st.caption("Módulo 1 — Context Stuffing · Módulo 2 — RAG")
        st.caption("GPT-4o-mini · Fundación Valle del Lili · 2024–2025")


def _render_qa_tab(qa_chain, context: str) -> None:
    """Renderiza la pestaña de chat conversacional Q&A con streaming.

    Args:
        qa_chain: Cadena LangChain Q&A construida por ``build_chain()``.
        context: Contexto compactado del knowledge base.
    """
    if "messages" not in st.session_state:
        st.session_state.messages: list[dict] = []

    col_title, col_btn = st.columns([7, 1])
    with col_title:
        st.subheader("Consulta al asistente institucional")
        st.caption(
            "Respuestas en tiempo real basadas exclusivamente en los documentos oficiales de la FVL."
        )
    with col_btn:
        st.markdown("<div style='margin-top:1.4rem;'></div>", unsafe_allow_html=True)
        if st.session_state.get("messages"):
            if st.button("🗑️ Limpiar", key="clear_chat", help="Borrar historial de conversación"):
                st.session_state.messages = []
                st.rerun()

    # Panel de bienvenida y ejemplos cuando el chat está vacío
    if not st.session_state.messages:
        st.markdown(
            """
            <div style="
                background: linear-gradient(135deg, #EBF5FB 0%, #F0F7FF 100%);
                border: 1px solid #C5D9EC;
                border-left: 4px solid #0077B5;
                border-radius: 10px;
                padding: 1rem 1.25rem 0.75rem;
                margin: 0.5rem 0 1rem;
            ">
                <p style="margin:0 0 0.4rem; font-weight:700; color:#002D72; font-size:0.95rem;">
                    ¿En qué te puedo ayudar?
                </p>
                <p style="margin:0; color:#5B6475; font-size:0.85rem;">
                    Puedes preguntar sobre servicios, sedes, especialidades, procedimientos o cualquier
                    información institucional de la Fundación Valle del Lili. Prueba uno de estos ejemplos:
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        cols = st.columns(len(_EXAMPLE_QUERIES))
        for col, query in zip(cols, _EXAMPLE_QUERIES):
            with col:
                if st.button(query, key=f"ex_{hash(query)}", use_container_width=True):
                    st.session_state["_qa_pending"] = query
                    st.rerun()

        st.markdown("")

    # Renderizar historial
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Input: mensaje del usuario o ejemplo pendiente
    user_input = st.chat_input("¿En qué te puedo ayudar hoy?")
    if "_qa_pending" in st.session_state:
        user_input = st.session_state.pop("_qa_pending")

    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        history_for_prompt = st.session_state.messages[:-1]

        with st.chat_message("assistant"):
            response = st.write_stream(
                stream_response(qa_chain, context, user_input, history_for_prompt)
            )

        st.session_state.messages.append({"role": "assistant", "content": response})


def _render_summary_tab(summary_chain, context: str) -> None:
    """Renderiza la pestaña de generación de resúmenes estructurados.

    Args:
        summary_chain: Cadena LangChain construida por ``build_summary_chain()``.
        context: Contexto compactado del knowledge base.
    """
    st.subheader("Resumen estructurado")
    st.caption(
        "Genera una síntesis con secciones claras y referencias a los documentos fuente de la FVL."
    )

    with st.expander("📌 Temas sugeridos", expanded=False):
        cols = st.columns(len(_EXAMPLE_TOPICS))
        for col, topic in zip(cols, _EXAMPLE_TOPICS):
            with col:
                if st.button(topic, key=f"stopic_{topic}", use_container_width=True):
                    st.session_state["_summary_prefill"] = topic

    with st.form(key="summary_form"):
        topic_val = st.session_state.pop("_summary_prefill", "")
        topic = st.text_input(
            "Tema a resumir",
            value=topic_val,
            placeholder="Ej: cardiología, sede norte, programa de trasplantes…",
        )
        submitted = st.form_submit_button("📋 Generar resumen", use_container_width=True)

    if submitted:
        if not topic.strip():
            st.warning("Por favor ingresa un tema antes de generar el resumen.")
        else:
            with st.spinner(f'Generando resumen sobre "{topic}"…'):
                result = get_summary(summary_chain, context, topic.strip())
            st.session_state["summary_result"] = result
            st.session_state["summary_topic"] = topic.strip()

    if "summary_result" in st.session_state:
        st.divider()
        st.markdown(
            f"""
            <div style="
                background: #EBF5FB;
                border: 1px solid #C5D9EC;
                border-left: 4px solid #002D72;
                border-radius: 10px;
                padding: 0.6rem 1rem;
                margin-bottom: 0.75rem;
                font-size: 0.84rem;
                color: #002D72;
                font-weight: 600;
            ">
                📄 Resumen generado para: <em>{st.session_state['summary_topic']}</em>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.container():
            st.markdown(st.session_state["summary_result"])
        st.download_button(
            label="⬇️ Descargar resumen (.md)",
            data=st.session_state["summary_result"],
            file_name=f"resumen_{st.session_state['summary_topic'].replace(' ', '_')}.md",
            mime="text/markdown",
            key="download_summary",
        )


def _render_faq_tab(faq_chain, context: str) -> None:
    """Renderiza la pestaña de generación de preguntas frecuentes (FAQ).

    Args:
        faq_chain: Cadena LangChain construida por ``build_faq_chain()``.
        context: Contexto compactado del knowledge base.
    """
    st.subheader("Preguntas frecuentes")
    st.caption(
        "Entre 5 y 8 preguntas que haría un paciente o visitante, con respuestas "
        "basadas exclusivamente en documentos oficiales."
    )

    with st.expander("📌 Temas sugeridos", expanded=False):
        cols = st.columns(len(_EXAMPLE_TOPICS))
        for col, topic in zip(cols, _EXAMPLE_TOPICS):
            with col:
                if st.button(topic, key=f"ftopic_{topic}", use_container_width=True):
                    st.session_state["_faq_prefill"] = topic

    with st.form(key="faq_form"):
        topic_val = st.session_state.pop("_faq_prefill", "")
        topic = st.text_input(
            "Tema para el FAQ",
            value=topic_val,
            placeholder="Ej: urgencias, trasplante de riñón, citas médicas, oncología…",
        )
        submitted = st.form_submit_button("❓ Generar FAQ", use_container_width=True)

    if submitted:
        if not topic.strip():
            st.warning("Por favor ingresa un tema antes de generar el FAQ.")
        else:
            with st.spinner(f'Generando preguntas frecuentes sobre "{topic}"…'):
                result = get_faq(faq_chain, context, topic.strip())
            st.session_state["faq_result"] = result
            st.session_state["faq_topic"] = topic.strip()

    if "faq_result" in st.session_state:
        st.divider()
        st.markdown(
            f"""
            <div style="
                background: #EBF5FB;
                border: 1px solid #C5D9EC;
                border-left: 4px solid #002D72;
                border-radius: 10px;
                padding: 0.6rem 1rem;
                margin-bottom: 0.75rem;
                font-size: 0.84rem;
                color: #002D72;
                font-weight: 600;
            ">
                ❓ FAQ generado para: <em>{st.session_state['faq_topic']}</em>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(st.session_state["faq_result"])
        st.download_button(
            label="⬇️ Descargar FAQ (.md)",
            data=st.session_state["faq_result"],
            file_name=f"faq_{st.session_state['faq_topic'].replace(' ', '_')}.md",
            mime="text/markdown",
            key="download_faq",
        )


def _render_rag_tab() -> None:
    """Renderiza la pestaña del agente RAG con memoria de sesión y streaming.

    Genera un UUID de sesión al inicio y lo persiste en ``st.session_state``
    como ``rag_thread_id``. Los mensajes para visualización se guardan en
    ``rag_messages`` (presentación pura). El agente gestiona su propia memoria
    internamente mediante el checkpointer — no se pasa historial al backend.

    Al limpiar la conversación se regenera el UUID, iniciando un nuevo hilo
    aislado en el checkpointer sin afectar sesiones anteriores.
    """
    if "rag_thread_id" not in st.session_state:
        st.session_state.rag_thread_id = str(uuid.uuid4())
    if "rag_messages" not in st.session_state:
        st.session_state.rag_messages: list[dict] = []

    col_title, col_btn = st.columns([7, 1])
    with col_title:
        st.subheader("Agente RAG — Recuperación semántica")
        st.caption(
            "Recuperación dinámica desde el índice vectorial ChromaDB · "
            "El agente decide qué fragmentos usar en cada respuesta."
        )
    with col_btn:
        st.markdown("<div style='margin-top:1.4rem;'></div>", unsafe_allow_html=True)
        if st.session_state.get("rag_messages"):
            if st.button("🗑️ Limpiar", key="clear_rag", help="Borrar conversación y reiniciar sesión"):
                st.session_state.rag_messages = []
                st.session_state.rag_thread_id = str(uuid.uuid4())
                st.rerun()

    # Panel de bienvenida con ejemplos cuando el chat está vacío
    if not st.session_state.rag_messages:
        st.markdown(
            """
            <div style="
                background: linear-gradient(135deg, #EBF5FB 0%, #F0F7FF 100%);
                border: 1px solid #C5D9EC;
                border-left: 4px solid #0077B5;
                border-radius: 10px;
                padding: 1rem 1.25rem 0.75rem;
                margin: 0.5rem 0 1rem;
            ">
                <p style="margin:0 0 0.4rem; font-weight:700; color:#002D72; font-size:0.95rem;">
                    🤖 Agente con recuperación semántica activa
                </p>
                <p style="margin:0; color:#5B6475; font-size:0.85rem;">
                    Este agente consulta dinámicamente el índice vectorial para responder con
                    fragmentos exactos de los documentos oficiales. Prueba una de estas consultas:
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        cols = st.columns(len(_EXAMPLE_QUERIES))
        for col, query in zip(cols, _EXAMPLE_QUERIES):
            with col:
                if st.button(query, key=f"rag_ex_{hash(query)}", use_container_width=True):
                    st.session_state["_rag_pending"] = query
                    st.rerun()

        st.markdown("")

    # Renderizar historial de visualización
    for msg in st.session_state.rag_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Input: mensaje del usuario o ejemplo pendiente
    user_input = st.chat_input("Consulta al agente RAG…", key="rag_input")
    if "_rag_pending" in st.session_state:
        user_input = st.session_state.pop("_rag_pending")

    if user_input:
        st.session_state.rag_messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            response = st.write_stream(
                stream_agent_response(user_input, st.session_state.rag_thread_id)
            )

        st.session_state.rag_messages.append({"role": "assistant", "content": response})


def main() -> None:
    """Punto de entrada del dashboard Streamlit de la FVL.

    Inyecta el CSS profesional, renderiza el sidebar, carga los recursos y
    organiza las tres funcionalidades en pestañas independientes.
    """
    _inject_css()

    try:
        qa_chain, summary_chain, faq_chain, context = load_resources()
        knowledge_loaded = True
    except (FileNotFoundError, ValueError) as e:
        _render_sidebar(knowledge_loaded=False)
        st.error(f"Error al cargar la base de conocimiento: {e}")
        st.info(
            "Asegúrate de haber ejecutado el pipeline de scraping para poblar "
            "la carpeta `knowledge/`."
        )
        st.stop()

    _render_sidebar(knowledge_loaded=True)

    # Cabecera principal
    st.markdown(
        """
        <div style="padding:0.25rem 0 1.5rem;">
            <h1 style="margin:0; font-size:1.85rem; color:#002D72; font-weight:800;">
                Asistente Virtual — Fundación Valle del Lili
            </h1>
            <p style="margin:0.3rem 0 0; color:#5B6475; font-size:0.9rem;">
                Información institucional · Servicios · Especialidades · Sedes
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab_qa, tab_summary, tab_faq, tab_rag = st.tabs(
        ["💬  Q&A — Preguntas y Respuestas", "📋  Resumen", "❓  FAQ", "🤖  Agente RAG"]
    )

    with tab_qa:
        _render_qa_tab(qa_chain, context)

    with tab_summary:
        _render_summary_tab(summary_chain, context)

    with tab_faq:
        _render_faq_tab(faq_chain, context)

    with tab_rag:
        _render_rag_tab()


if __name__ == "__main__":
    main()
