"""Dashboard Streamlit — Asistente Virtual FVL (Módulo 2 · Agente RAG).

Funcionalidad principal:
- **🤖 Agente RAG**: recuperación semántica dinámica desde ChromaDB con
  memoria de sesión, streaming de respuestas y soporte de historial.
"""

from __future__ import annotations

import uuid
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

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
/* ── Variables — paleta oficial FVL ── */
:root {
    --fvl-primary:     #023739;   /* teal oscuro — color corporativo principal */
    --fvl-primary-mid: #034B4D;   /* teal medio (hover en primario) */
    --fvl-blue:        #007AFF;   /* azul FVL — elementos interactivos */
    --fvl-teal-bg:     #E8F2F2;   /* fondo claro derivado del primary */
    --fvl-green:       #95D31D;   /* verde lima FVL — éxito / acento */
    --fvl-border:      #C5D8D9;   /* borde derivado del teal */
    --fvl-bg:          #F5F7FA;
    --fvl-white:       #FFFFFF;
    --fvl-gray:        #5B6475;
    --fvl-gray-lt:     #F0F2F5;
    --radius:          10px;
    --shadow:          0 2px 8px rgba(0,0,0,0.08);
}

/* ── Layout principal ── */
.main .block-container {
    padding-top: 1.5rem;
    padding-bottom: 7rem;
    max-width: 1100px;
}
.stApp {
    background-color: var(--fvl-bg);
}

/* ── Headings ── */
h1 { color: var(--fvl-primary) !important; font-weight: 800 !important; letter-spacing: -0.02em; }
h2 { color: var(--fvl-primary) !important; font-weight: 700 !important; }
h3 { color: var(--fvl-blue) !important; font-weight: 600 !important; }

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
    color: var(--fvl-primary) !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
    color: var(--fvl-primary) !important;
    border-bottom: 3px solid var(--fvl-primary) !important;
    background: transparent !important;
}

/* ── Botón de formulario (submit) ── */
.stFormSubmitButton > button {
    width: 100%;
    background-color: var(--fvl-primary) !important;
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
    background-color: var(--fvl-primary-mid) !important;
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
    border-color: var(--fvl-blue) !important;
    color: var(--fvl-blue) !important;
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

/* ── Chat input (inner div) ── */
[data-testid="stChatInput"] > div {
    border-radius: var(--radius) !important;
    border: 1.5px solid var(--fvl-border) !important;
    background: var(--fvl-white) !important;
    box-shadow: var(--shadow) !important;
}
[data-testid="stChatInput"] > div:focus-within {
    border-color: var(--fvl-blue) !important;
    box-shadow: 0 0 0 3px rgba(0,122,255,0.12) !important;
}

/* ── Chat input fijo en la parte inferior ── */
section[data-testid="stChatInput"] {
    position: fixed !important;
    bottom: 0 !important;
    left: 244px !important;
    right: 0 !important;
    z-index: 999 !important;
    background: var(--fvl-bg) !important;
    padding: 0.75rem 1.5rem 1rem !important;
    border-top: 1px solid var(--fvl-border) !important;
    box-shadow: 0 -2px 12px rgba(0,0,0,0.06) !important;
}
/* Sidebar colapsado */
[data-testid="stSidebar"][aria-expanded="false"] ~ .main section[data-testid="stChatInput"] {
    left: 0 !important;
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
    border-color: var(--fvl-blue) !important;
    box-shadow: 0 0 0 3px rgba(0,122,255,0.12) !important;
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
    color: var(--fvl-primary) !important;
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

_LOGO_PATH = Path(__file__).parent / "assets" / "logo.png"


def _inject_css() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def _scroll_to_bottom() -> None:
    """Desplaza la vista al último mensaje del chat usando JavaScript.

    Inyecta un fragmento HTML/JS con ``st.components.v1.html`` que localiza
    el último mensaje renderizado y llama a ``scrollIntoView``. La altura fija
    de 0 evita que el componente ocupe espacio visual en la página.
    """
    import streamlit.components.v1 as components

    components.html(
        """
        <script>
        (function () {
            const msgs = window.parent.document.querySelectorAll(
                '[data-testid="stChatMessage"]'
            );
            if (msgs.length > 0) {
                msgs[msgs.length - 1].scrollIntoView({
                    behavior: "smooth",
                    block: "end"
                });
            }
        })();
        </script>
        """,
        height=0,
    )


def _render_sidebar() -> None:
    """Renderiza el panel lateral con branding FVL y guía de uso del agente RAG."""
    with st.sidebar:
        # ── Logo institucional o fallback con iniciales FVL ───────────────
        if _LOGO_PATH.exists():
            st.image(str(_LOGO_PATH), use_container_width=True)
        else:
            st.markdown(
                """
                <div style="text-align:center; padding:1.25rem 0 0.75rem;">
                    <div style="
                        display:inline-flex; align-items:center; justify-content:center;
                        width:64px; height:64px; border-radius:14px;
                        background:var(--fvl-primary); color:#FFFFFF;
                        font-size:1.4rem; font-weight:900; letter-spacing:0.02em;
                    ">FVL</div>
                    <div style="font-size:1.05rem; font-weight:800; color:var(--fvl-primary);
                                line-height:1.3; margin-top:0.6rem;">
                        Fundación<br>Valle del Lili
                    </div>
                    <div style="font-size:0.74rem; color:#5B6475; margin-top:0.3rem;
                                letter-spacing:0.04em; text-transform:uppercase;">
                        Asistente Virtual · Módulo RAG
                    </div>
                </div>
                <hr style="border-color:var(--fvl-border); margin:0.5rem 0 1rem;">
                """,
                unsafe_allow_html=True,
            )

        # ── Guía de uso ───────────────────────────────────────────────────
        st.markdown(
            "<p style='font-size:0.82rem;font-weight:700;color:var(--fvl-primary);"
            "text-transform:uppercase;letter-spacing:0.06em;margin:1.25rem 0 0.5rem;'>Cómo usar</p>",
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            **🤖 Agente RAG — Recuperación semántica**
            Consulta el índice vectorial ChromaDB para responder con fragmentos
            exactos de los documentos institucionales de la FVL.
            Mantiene memoria de la sesión activa.
            """,
        )

        st.markdown(
            "<p style='font-size:0.82rem;font-weight:700;color:var(--fvl-primary);"
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
        st.caption("Módulo 2 — Agente RAG · ChromaDB")
        st.caption("GPT-4o-mini · Fundación Valle del Lili · 2024–2025")


def _render_rag_tab() -> None:
    """Renderiza el agente RAG con memoria de sesión y streaming.

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
                background: linear-gradient(135deg, var(--fvl-teal-bg) 0%, #F0F7FF 100%);
                border: 1px solid var(--fvl-border);
                border-left: 4px solid var(--fvl-blue);
                border-radius: 10px;
                padding: 1rem 1.25rem 0.75rem;
                margin: 0.5rem 0 1rem;
            ">
                <p style="margin:0 0 0.4rem; font-weight:700; color:var(--fvl-primary); font-size:0.95rem;">
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

    _scroll_to_bottom()

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
    """Punto de entrada del Asistente Virtual FVL — Módulo 2 (Agente RAG).

    Inyecta el CSS de marca institucional, renderiza el sidebar y lanza
    directamente el agente RAG con recuperación semántica desde ChromaDB.
    El agente usa lazy-loading y gestiona sus propios errores internamente.
    """
    _inject_css()
    _render_sidebar()

    # ── Cabecera principal ─────────────────────────────────────────────────
    st.markdown(
        """
        <div style="padding:0.25rem 0 1.5rem;">
            <h1 style="margin:0; font-size:1.85rem; color:var(--fvl-primary); font-weight:800;">
                Asistente Virtual — Fundación Valle del Lili
            </h1>
            <p style="margin:0.3rem 0 0; color:#5B6475; font-size:0.9rem;">
                Agente RAG · Recuperación semántica · ChromaDB
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _render_rag_tab()


if __name__ == "__main__":
    main()
