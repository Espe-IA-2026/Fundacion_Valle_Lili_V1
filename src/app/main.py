"""Interfaz de chat Streamlit para el chatbot de la Fundación Valle del Lili."""

import os

import streamlit as st
from dotenv import load_dotenv

from app.engine import build_chain, get_response, load_knowledge_base

load_dotenv()

st.set_page_config(
    page_title="Asistente Virtual — Fundación Valle del Lili",
    page_icon="🏥",
    layout="centered",
)


@st.cache_resource(show_spinner="Cargando base de conocimiento institucional…")
def load_resources():
    """Carga el knowledge base y construye la cadena LangChain una sola vez."""
    knowledge_dir = os.getenv("KNOWLEDGE_DIR", "./knowledge")
    context = load_knowledge_base(knowledge_dir)
    chain = build_chain()
    return chain, context


def main() -> None:
    st.title("Asistente Virtual")
    st.caption("Fundación Valle del Lili · Información institucional, servicios y especialidades")

    try:
        chain, context = load_resources()
    except (FileNotFoundError, ValueError) as e:
        st.error(f"Error al cargar la base de conocimiento: {e}")
        st.info("Asegúrate de haber ejecutado el pipeline de scraping para poblar la carpeta `knowledge/`.")
        st.stop()

    if "messages" not in st.session_state:
        st.session_state.messages: list[dict] = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    if user_input := st.chat_input("¿En qué te puedo ayudar?"):
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.write(user_input)

        # Pasar el historial sin el mensaje actual (ya fue agregado)
        history_for_prompt = st.session_state.messages[:-1]

        with st.chat_message("assistant"):
            with st.spinner("Consultando documentos institucionales…"):
                response = get_response(chain, context, user_input, history_for_prompt)
            st.write(response)

        st.session_state.messages.append({"role": "assistant", "content": response})


if __name__ == "__main__":
    main()
