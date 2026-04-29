"""Dashboard Streamlit con tres funcionalidades sobre el knowledge base de la FVL.

Pestañas disponibles:
- **💬 Q&A**: chatbot conversacional con historial de turnos.
- **📋 Resumen**: síntesis estructurada de un tema institucional.
- **❓ FAQ**: preguntas frecuentes generadas desde los documentos.
"""

import os

import streamlit as st
from dotenv import load_dotenv

from app.engine import (
    build_chain,
    build_faq_chain,
    build_summary_chain,
    get_faq,
    get_response,
    get_summary,
    load_knowledge_base,
)

load_dotenv()

st.set_page_config(
    page_title="Asistente Virtual — Fundación Valle del Lili",
    page_icon="🏥",
    layout="centered",
)


@st.cache_resource(show_spinner="Cargando base de conocimiento institucional…")
def load_resources() -> tuple:
    """Carga el knowledge base y construye las tres cadenas LangChain una sola vez.

    Usa ``@st.cache_resource`` para que el costoso proceso de lectura de archivos
    y construcción de cadenas ocurra una única vez por sesión del servidor.

    Returns:
        Tupla ``(qa_chain, summary_chain, faq_chain, context)``.
    """
    knowledge_dir = os.getenv("KNOWLEDGE_DIR", "./knowledge")
    context = load_knowledge_base(knowledge_dir)
    qa_chain = build_chain()
    summary_chain = build_summary_chain()
    faq_chain = build_faq_chain()
    return qa_chain, summary_chain, faq_chain, context


def _render_qa_tab(qa_chain, context: str) -> None:
    """Renderiza la pestaña de chat conversacional Q&A.

    Muestra el historial de la conversación actual y permite al usuario
    enviar nuevas preguntas. El historial se mantiene en ``st.session_state``.

    Args:
        qa_chain: Cadena LangChain Q&A construida por ``build_chain()``.
        context: Contexto compactado del knowledge base.
    """
    st.subheader("Pregunta sobre la Fundación Valle del Lili")
    st.caption(
        "Escribe tu consulta y el asistente responderá basándose únicamente "
        "en los documentos institucionales."
    )

    if "messages" not in st.session_state:
        st.session_state.messages: list[dict] = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    if user_input := st.chat_input("¿En qué te puedo ayudar?"):
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.write(user_input)

        history_for_prompt = st.session_state.messages[:-1]

        with st.chat_message("assistant"):
            with st.spinner("Consultando documentos institucionales…"):
                response = get_response(
                    qa_chain, context, user_input, history_for_prompt
                )
            st.write(response)

        st.session_state.messages.append({"role": "assistant", "content": response})

    if st.session_state.get("messages"):
        if st.button("🗑️ Limpiar conversación", key="clear_chat"):
            st.session_state.messages = []
            st.rerun()


def _render_summary_tab(summary_chain, context: str) -> None:
    """Renderiza la pestaña de generación de resúmenes estructurados.

    El usuario ingresa un tema y obtiene una síntesis en Markdown con secciones
    claras y referencias a los documentos fuente del knowledge base.

    Args:
        summary_chain: Cadena LangChain construida por ``build_summary_chain()``.
        context: Contexto compactado del knowledge base.
    """
    st.subheader("Resumen institucional sobre un tema")
    st.caption(
        "Ingresa un tema (servicio, sede, especialidad, programa, etc.) y el "
        "asistente generará un resumen estructurado basado en los documentos oficiales."
    )

    with st.form(key="summary_form"):
        topic = st.text_input(
            "Tema a resumir",
            placeholder="Ej: cardiología, sede norte, programa de trasplantes…",
        )
        submitted = st.form_submit_button("📋 Generar resumen")

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

    El usuario ingresa un tema y obtiene entre 5 y 8 preguntas frecuentes
    con sus respuestas, fundamentadas en los documentos del knowledge base.

    Args:
        faq_chain: Cadena LangChain construida por ``build_faq_chain()``.
        context: Contexto compactado del knowledge base.
    """
    st.subheader("Preguntas Frecuentes sobre un tema")
    st.caption(
        "Ingresa un tema y el asistente generará las preguntas más relevantes "
        "que haría un paciente o visitante, con respuestas basadas en documentos oficiales."
    )

    with st.form(key="faq_form"):
        topic = st.text_input(
            "Tema para el FAQ",
            placeholder="Ej: urgencias, trasplante de riñón, citas médicas, oncología…",
        )
        submitted = st.form_submit_button("❓ Generar FAQ")

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
        st.markdown(st.session_state["faq_result"])
        st.download_button(
            label="⬇️ Descargar FAQ (.md)",
            data=st.session_state["faq_result"],
            file_name=f"faq_{st.session_state['faq_topic'].replace(' ', '_')}.md",
            mime="text/markdown",
            key="download_faq",
        )


def main() -> None:
    """Punto de entrada del dashboard Streamlit de la FVL.

    Muestra el encabezado de la aplicación, carga los recursos (knowledge base y
    tres cadenas LangChain) y organiza las tres funcionalidades en pestañas
    independientes: Q&A conversacional, Resumen y FAQ.
    """
    st.title("🏥 Asistente Virtual FVL")
    st.caption(
        "Fundación Valle del Lili · Información institucional, servicios y especialidades"
    )

    try:
        qa_chain, summary_chain, faq_chain, context = load_resources()
    except (FileNotFoundError, ValueError) as e:
        st.error(f"Error al cargar la base de conocimiento: {e}")
        st.info(
            "Asegúrate de haber ejecutado el pipeline de scraping para poblar "
            "la carpeta `knowledge/`."
        )
        st.stop()

    tab_qa, tab_summary, tab_faq = st.tabs(
        ["💬 Q&A — Preguntas y Respuestas", "📋 Resumen", "❓ FAQ"]
    )

    with tab_qa:
        _render_qa_tab(qa_chain, context)

    with tab_summary:
        _render_summary_tab(summary_chain, context)

    with tab_faq:
        _render_faq_tab(faq_chain, context)


if __name__ == "__main__":
    main()
