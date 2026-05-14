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

from app_agent.engine import stream_agent_events
from semantic_layer_fvl.config import get_settings

load_dotenv()

st.set_page_config(
    page_title="Asistente Virtual — Fundación Valle del Lili",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS clínico FVL — verde + blanco ───────────────────────────────────────────
_CSS = """
<style>
/* ── Variables — paleta clínica FVL verde + blanco ── */
:root {
    --fvl-primary:      #023739;   /* verde oscuro FVL — barra lateral y cabecera */
    --fvl-primary-mid:  #034B4D;   /* verde medio — hover en primario */
    --fvl-accent:       #6BAE23;   /* verde lima FVL — acento principal */
    --fvl-accent-lt:    #EEF7DA;   /* verde lima muy claro — fondo acento */
    --fvl-user-bg:      #E6F4EA;   /* burbuja usuario — verde suave */
    --fvl-user-border:  #A8D5B0;   /* borde burbuja usuario */
    --fvl-asst-border:  #B8D4C8;   /* borde burbuja asistente */
    --fvl-green-muted:  #2D6A4F;   /* verde medio para texto secundario */
    --fvl-border:       #D4E6DC;   /* borde general */
    --fvl-bg:           #F4FAF6;   /* fondo app — blanco con tinte verde */
    --fvl-white:        #FFFFFF;
    --fvl-gray:         #4A5568;
    --fvl-gray-lt:      #EDF2EE;
    --radius:           10px;
    --shadow:           0 2px 8px rgba(2,55,57,0.08);
    --shadow-md:        0 4px 16px rgba(2,55,57,0.12);
}

/* ── Reset / Layout ── */
* { box-sizing: border-box; }
.main .block-container {
    padding-top: 0;
    padding-bottom: 6rem;
    max-width: 980px;
}
.stApp {
    background-color: var(--fvl-bg) !important;
    color: #1A202C !important;
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif !important;
}

/* ── Sidebar — verde oscuro clínico ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #023739 0%, #034B4D 100%) !important;
    border-right: none !important;
    box-shadow: 2px 0 12px rgba(0,0,0,0.15) !important;
}
[data-testid="stSidebarContent"] {
    padding: 1.5rem 1.25rem !important;
}
/* Texto en sidebar — forzar blanco */
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] div,
[data-testid="stSidebar"] li {
    color: rgba(255,255,255,0.90) !important;
}
[data-testid="stSidebar"] hr {
    border-color: rgba(255,255,255,0.15) !important;
    margin: 1rem 0 !important;
}
/* Divider en sidebar */
[data-testid="stSidebar"] [data-testid="stDivider"] {
    border-color: rgba(255,255,255,0.15) !important;
}

/* ── Headings ── */
h1, h2 { color: var(--fvl-primary) !important; font-weight: 800 !important; }
h3 { color: var(--fvl-green-muted) !important; font-weight: 600 !important; }

/* ── Cabecera principal ── */
.fvl-header {
    background: linear-gradient(135deg, #023739 0%, #034B4D 60%, #045A5C 100%);
    border-radius: 14px;
    padding: 1.5rem 2rem;
    margin-bottom: 1.5rem;
    box-shadow: var(--shadow-md);
    position: relative;
    overflow: hidden;
}
.fvl-header::before {
    content: '';
    position: absolute;
    top: -40px; right: -40px;
    width: 160px; height: 160px;
    background: rgba(107,174,35,0.12);
    border-radius: 50%;
}
.fvl-header::after {
    content: '';
    position: absolute;
    bottom: -30px; left: 30%;
    width: 120px; height: 120px;
    background: rgba(107,174,35,0.08);
    border-radius: 50%;
}

/* ── Bienvenida ── */
.fvl-welcome {
    background: var(--fvl-white);
    border: 1px solid var(--fvl-border);
    border-left: 4px solid var(--fvl-accent);
    border-radius: var(--radius);
    padding: 1.1rem 1.4rem;
    margin-bottom: 1.25rem;
    box-shadow: var(--shadow);
}

/* ── Chat messages — usuario ── */
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
    background: var(--fvl-user-bg) !important;
    border: 1px solid var(--fvl-user-border) !important;
    border-radius: var(--radius) !important;
    margin-bottom: 0.6rem !important;
    box-shadow: none !important;
}
/* ── Chat messages — asistente ── */
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {
    background: var(--fvl-white) !important;
    border: 1px solid var(--fvl-asst-border) !important;
    border-left: 3px solid var(--fvl-accent) !important;
    border-radius: var(--radius) !important;
    margin-bottom: 0.6rem !important;
    box-shadow: var(--shadow) !important;
}
/* Texto en burbujas */
[data-testid="stChatMessage"] p,
[data-testid="stChatMessage"] li,
[data-testid="stChatMessage"] span {
    color: #1A202C !important;
}
/* Strong/bold dentro de chat */
[data-testid="stChatMessage"] strong {
    color: var(--fvl-primary) !important;
}

/* ── Indicador de pensamiento ── */
.fvl-thinking {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    color: var(--fvl-green-muted);
    font-style: italic;
    font-size: 0.9rem;
    padding: 0.4rem 0;
}

/* ── Chat input ── */
[data-testid="stChatInput"] > div {
    border-radius: 12px !important;
    border: 2px solid var(--fvl-border) !important;
    background: var(--fvl-white) !important;
    box-shadow: var(--shadow) !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
}
[data-testid="stChatInput"] > div:focus-within {
    border-color: var(--fvl-accent) !important;
    box-shadow: 0 0 0 3px rgba(107,174,35,0.15) !important;
}
[data-testid="stChatInput"] textarea,
[data-testid="stChatInput"] input {
    background: var(--fvl-white) !important;
    color: #1A202C !important;
    caret-color: var(--fvl-primary) !important;
    font-size: 0.96rem !important;
}
[data-testid="stChatInput"] textarea::placeholder,
[data-testid="stChatInput"] input::placeholder {
    color: #9CA3AF !important;
    opacity: 1 !important;
}
[data-testid="stChatInputSubmitButton"] {
    background-color: var(--fvl-accent) !important;
    border-radius: 8px !important;
    border: none !important;
    opacity: 1 !important;
}
[data-testid="stChatInputSubmitButton"]:hover {
    background-color: #5A9A1E !important;
}
[data-testid="stChatInputSubmitButton"] svg,
[data-testid="stChatInputSubmitButton"] svg path {
    fill: #FFFFFF !important;
    stroke: #FFFFFF !important;
}

/* ── Barra inferior ── */
[data-testid="stBottomBlockContainer"] {
    background: var(--fvl-bg) !important;
    border-top: 1px solid var(--fvl-border) !important;
    box-shadow: 0 -2px 12px rgba(2,55,57,0.07) !important;
}
section[data-testid="stChatInput"],
footer { background: var(--fvl-bg) !important; }

/* ── Botones de queries rápidas ── */
.stButton > button {
    border-radius: var(--radius) !important;
    border: 1.5px solid var(--fvl-border) !important;
    color: var(--fvl-primary) !important;
    background-color: var(--fvl-white) !important;
    font-weight: 500 !important;
    font-size: 0.83rem !important;
    transition: all 0.18s !important;
    padding: 0.4rem 0.8rem !important;
    text-align: left !important;
}
.stButton > button:hover {
    border-color: var(--fvl-accent) !important;
    color: var(--fvl-primary) !important;
    background-color: var(--fvl-accent-lt) !important;
    box-shadow: 0 2px 6px rgba(107,174,35,0.2) !important;
}

/* ── Botón limpiar ── */
.btn-clear button {
    border: 1.5px solid #FECACA !important;
    color: #991B1B !important;
    background-color: #FEF2F2 !important;
    font-weight: 600 !important;
    font-size: 0.8rem !important;
}
.btn-clear button:hover {
    background-color: #FEE2E2 !important;
    border-color: #F87171 !important;
}

/* ── Caption ── */
.stCaption {
    color: var(--fvl-gray) !important;
    font-size: 0.82rem !important;
}

/* ── Expanders ── */
details[data-testid="stExpander"] {
    border: 1px solid var(--fvl-border) !important;
    border-radius: var(--radius) !important;
    background: var(--fvl-white) !important;
    margin-bottom: 0.75rem !important;
}

/* ── Divider ── */
hr {
    border-color: var(--fvl-border) !important;
    margin: 1rem 0 !important;
}
</style>
"""

_EXAMPLE_QUERIES = [
    "¿Cuáles son los servicios de cardiología?",
    "¿Qué EPS tienen convenio con la FVL?",
    "¿Qué es el programa de trasplantes?",
    "¿Cuáles son los horarios de urgencias?",
    "¿Cómo agendar una cita médica?",
]

_TOOL_LABELS = {
    "retrieve_fvl_knowledge": "📚 Base de conocimiento",
    "get_fvl_structured_info": "🗂️ Datos institucionales",
}

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
    """Renderiza el panel lateral con branding FVL — fondo verde oscuro clínico."""
    settings = get_settings()
    model_name = settings.openai_model

    with st.sidebar:
        # ── Logo o bloque de marca ─────────────────────────────────────────
        if _LOGO_PATH.exists():
            st.image(str(_LOGO_PATH), use_container_width=True)
        else:
            st.markdown(
                """
                <div style="text-align:center; padding:1.5rem 0 1rem;">
                    <div style="
                        display:inline-flex; align-items:center; justify-content:center;
                        width:72px; height:72px; border-radius:16px;
                        background:rgba(107,174,35,0.18); border:2px solid rgba(107,174,35,0.5);
                        color:#FFFFFF; font-size:1.5rem; font-weight:900;
                    ">FVL</div>
                    <div style="color:#FFFFFF; font-size:1.05rem; font-weight:800;
                                line-height:1.4; margin-top:0.75rem;">
                        Fundación Valle del Lili
                    </div>
                    <div style="color:rgba(255,255,255,0.6); font-size:0.72rem;
                                letter-spacing:0.1em; text-transform:uppercase; margin-top:0.3rem;">
                        Asistente Virtual Clínico
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown(
            "<hr style='border-color:rgba(255,255,255,0.15);margin:0.5rem 0 1.2rem;'>",
            unsafe_allow_html=True,
        )

        # ── Estado del sistema ────────────────────────────────────────────
        st.markdown(
            "<p style='font-size:0.72rem;font-weight:700;color:rgba(255,255,255,0.5);"
            "text-transform:uppercase;letter-spacing:0.1em;margin:0 0 0.75rem;'>Estado del sistema</p>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"""
            <div style="background:rgba(255,255,255,0.07);border-radius:8px;
                        padding:0.75rem 1rem;margin-bottom:0.6rem;">
                <div style="color:rgba(255,255,255,0.55);font-size:0.72rem;margin-bottom:0.2rem;">MODELO LLM</div>
                <div style="color:#FFFFFF;font-size:0.88rem;font-weight:600;">{model_name}</div>
            </div>
            <div style="background:rgba(255,255,255,0.07);border-radius:8px;
                        padding:0.75rem 1rem;margin-bottom:0.6rem;">
                <div style="color:rgba(255,255,255,0.55);font-size:0.72rem;margin-bottom:0.2rem;">BASE VECTORIAL</div>
                <div style="color:#FFFFFF;font-size:0.88rem;font-weight:600;">ChromaDB · RAG</div>
            </div>
            <div style="background:rgba(255,255,255,0.07);border-radius:8px;
                        padding:0.75rem 1rem;">
                <div style="color:rgba(255,255,255,0.55);font-size:0.72rem;margin-bottom:0.2rem;">EMBEDDINGS</div>
                <div style="color:#FFFFFF;font-size:0.88rem;font-weight:600;">text-embedding-3-small</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            "<hr style='border-color:rgba(255,255,255,0.15);margin:1.2rem 0;'>",
            unsafe_allow_html=True,
        )

        # ── Guía de uso ───────────────────────────────────────────────────
        st.markdown(
            "<p style='font-size:0.72rem;font-weight:700;color:rgba(255,255,255,0.5);"
            "text-transform:uppercase;letter-spacing:0.1em;margin:0 0 0.75rem;'>Capacidades</p>",
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            <div style="display:flex;flex-direction:column;gap:0.5rem;">
                <div style="display:flex;align-items:flex-start;gap:0.6rem;">
                    <span style="font-size:1rem;margin-top:0.05rem;">📚</span>
                    <div>
                        <div style="color:#FFFFFF;font-size:0.84rem;font-weight:600;margin-bottom:0.1rem;">Base de conocimiento</div>
                        <div style="color:rgba(255,255,255,0.6);font-size:0.78rem;line-height:1.4;">Servicios, especialistas, historia institucional</div>
                    </div>
                </div>
                <div style="display:flex;align-items:flex-start;gap:0.6rem;">
                    <span style="font-size:1rem;margin-top:0.05rem;">🗂️</span>
                    <div>
                        <div style="color:#FFFFFF;font-size:0.84rem;font-weight:600;margin-bottom:0.1rem;">Datos estructurados</div>
                        <div style="color:rgba(255,255,255,0.6);font-size:0.78rem;line-height:1.4;">EPS, horarios, contactos, sedes</div>
                    </div>
                </div>
                <div style="display:flex;align-items:flex-start;gap:0.6rem;">
                    <span style="font-size:1rem;margin-top:0.05rem;">🧠</span>
                    <div>
                        <div style="color:#FFFFFF;font-size:0.84rem;font-weight:600;margin-bottom:0.1rem;">Memoria de sesión</div>
                        <div style="color:rgba(255,255,255,0.6);font-size:0.78rem;line-height:1.4;">Recuerda el contexto de la conversación</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            "<hr style='border-color:rgba(255,255,255,0.15);margin:1.2rem 0 0.75rem;'>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<p style='font-size:0.72rem;color:rgba(255,255,255,0.4);margin:0;text-align:center;'>"
            "Fundación Valle del Lili · 2026<br>Asistente Clínico RAG</p>",
            unsafe_allow_html=True,
        )


def _render_rag_tab() -> None:
    """Renderiza el agente RAG con memoria de sesión y streaming.

    El placeholder de respuesta siempre muestra un indicador de estado
    durante el procesamiento para evitar el "mensaje fantasma" vacío
    que aparecía cuando el usuario enviaba una segunda pregunta.
    """
    if "rag_thread_id" not in st.session_state:
        st.session_state.rag_thread_id = str(uuid.uuid4())
    if "rag_messages" not in st.session_state:
        st.session_state.rag_messages: list[dict] = []
    # Sanear mensajes vacíos de errores previos
    st.session_state.rag_messages = [
        m for m in st.session_state.rag_messages if m.get("content")
    ]

    # ── Fila título + botón limpiar ────────────────────────────────────────
    col_title, col_btn = st.columns([8, 1])
    with col_title:
        st.markdown(
            "<p style='color:var(--fvl-gray);font-size:0.88rem;margin:0 0 1rem;'>"
            "El agente selecciona automáticamente la fuente más precisa para cada consulta."
            "</p>",
            unsafe_allow_html=True,
        )
    with col_btn:
        if st.session_state.get("rag_messages"):
            st.markdown('<div class="btn-clear">', unsafe_allow_html=True)
            if st.button("🗑️", key="clear_rag", help="Borrar conversación y reiniciar sesión"):
                st.session_state.rag_messages = []
                st.session_state.rag_thread_id = str(uuid.uuid4())
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    # ── Panel de bienvenida ────────────────────────────────────────────────
    if not st.session_state.rag_messages:
        st.markdown(
            """
            <div class="fvl-welcome">
                <p style="margin:0 0 0.5rem; font-weight:700; color:var(--fvl-primary); font-size:0.96rem;">
                    👋 Bienvenido al Asistente Clínico de la Fundación Valle del Lili
                </p>
                <p style="margin:0; color:var(--fvl-gray); font-size:0.86rem; line-height:1.55;">
                    Puedo responder preguntas sobre servicios médicos, especialistas, EPS en convenio,
                    horarios de atención, sedes y más. Toda la información proviene directamente
                    de los documentos oficiales de la institución.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            "<p style='font-size:0.8rem;color:var(--fvl-gray);margin:0 0 0.5rem;'>Consultas frecuentes:</p>",
            unsafe_allow_html=True,
        )
        cols = st.columns(len(_EXAMPLE_QUERIES))
        for col, query in zip(cols, _EXAMPLE_QUERIES):
            with col:
                if st.button(query, key=f"rag_ex_{hash(query)}", use_container_width=True):
                    st.session_state["_rag_pending"] = query
                    st.rerun()
        st.markdown("")

    # ── Historial de mensajes ──────────────────────────────────────────────
    for msg in st.session_state.rag_messages:
        if not msg.get("content"):
            continue
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            # Mostrar herramientas usadas en mensajes del asistente guardados
            if msg["role"] == "assistant" and msg.get("tools_used"):
                labels = " · ".join(
                    _TOOL_LABELS.get(t, f"🔧 {t}") for t in msg["tools_used"]
                )
                st.caption(f"Fuente: {labels}")

    _scroll_to_bottom()

    # ── Input ──────────────────────────────────────────────────────────────
    user_input = st.chat_input("Escribe tu consulta aquí…", key="rag_input")
    if "_rag_pending" in st.session_state:
        user_input = st.session_state.pop("_rag_pending")

    if user_input:
        st.session_state.rag_messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        tools_used: list[str] = []
        response = ""

        with st.chat_message("assistant"):
            # FIX: placeholder siempre tiene contenido visible para evitar
            # el "mensaje fantasma" vacío durante el ciclo de pensamiento.
            placeholder = st.empty()
            placeholder.markdown(
                "<div class='fvl-thinking'>⏳ Consultando documentos institucionales…</div>",
                unsafe_allow_html=True,
            )

            for event in stream_agent_events(user_input, st.session_state.rag_thread_id):
                if event["type"] == "thought":
                    tools_used.append(event["tool"])
                    tool_label = _TOOL_LABELS.get(event["tool"], event["tool"])
                    placeholder.markdown(
                        f"<div class='fvl-thinking'>🔍 Buscando en {tool_label}…</div>",
                        unsafe_allow_html=True,
                    )
                elif event["type"] in ("answer", "error"):
                    response = event["text"]
                    placeholder.markdown(response)

            if tools_used:
                labels = " · ".join(_TOOL_LABELS.get(t, f"🔧 {t}") for t in tools_used)
                st.caption(f"Fuente: {labels}")

        if response:
            st.session_state.rag_messages.append({
                "role": "assistant",
                "content": response,
                "tools_used": tools_used,
            })


def main() -> None:
    """Punto de entrada del Asistente Virtual FVL — Módulo 2 (Agente RAG)."""
    _inject_css()
    _render_sidebar()

    # ── Cabecera principal verde FVL ───────────────────────────────────────
    st.markdown(
        """
        <div class="fvl-header">
            <div style="position:relative;z-index:1;">
                <div style="display:flex;align-items:center;gap:0.75rem;margin-bottom:0.4rem;">
                    <span style="font-size:1.8rem;">🏥</span>
                    <h1 style="margin:0;font-size:1.7rem;color:#FFFFFF;font-weight:800;
                               letter-spacing:-0.02em;line-height:1.2;">
                        Asistente Virtual
                    </h1>
                </div>
                <p style="margin:0;color:rgba(255,255,255,0.80);font-size:0.95rem;
                           font-weight:400;letter-spacing:0.01em;">
                    Fundación Valle del Lili &nbsp;·&nbsp; Información institucional verificada
                </p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _render_rag_tab()


if __name__ == "__main__":
    main()
