"""Motor lógico del chatbot: carga la base de conocimiento y gestiona la cadena LangChain."""

import os
import re
from collections import Counter
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

load_dotenv()

SYSTEM_TEMPLATE = """\
Eres el asistente virtual oficial de la Fundación Valle del Lili, \
un hospital universitario de alta complejidad ubicado en Cali, Colombia.

INSTRUCCIONES ESTRICTAS (no negociables):
1. Responde ÚNICAMENTE con información contenida en la BASE DE CONOCIMIENTO que se te proporciona abajo.
2. Si la respuesta no está en el contexto, responde exactamente: \
"No encontré esa información en los documentos institucionales disponibles."
3. NUNCA inventes datos como fechas, nombres de médicos, precios, horarios o teléfonos \
que no estén explícitamente en el contexto.
4. Responde en español, con tono profesional, amable y conciso.
5. Si el usuario saluda o hace preguntas ajenas a la institución, responde con cortesía \
pero redirige la conversación hacia tu función institucional.
6. Cuando sea relevante, indica de qué documento proviene la información \
usando el marcador DOC:<nombre>.
7. El contexto usa abreviaturas para ahorrar tokens. Interprétalas así:
    - FVL: Fundación Valle del Lili
    - DOC: delimitador de documento (formato: DOC:<slug>)
    - ESP: sección de especialistas
    - PROC: sección de procedimientos
    - TRAT: sección de tratamiento
    - CONTACTO: sección de contacto
    - L###: línea comprimida; resuélvela consultando la sección LEXICO_LINEAS

BASE DE CONOCIMIENTO DE LA FUNDACIÓN VALLE DEL LILI:
{context}
"""

_FRONTMATTER_RE = re.compile(r"^---[\s\S]*?---\s*\n", re.MULTILINE)
_MULTI_NEWLINE_RE = re.compile(r"\n{3,}")
_DOC_SEPARATOR_RE = re.compile(r"\n\n====== DOCUMENTO: ([^=\n]+) ======\n\n")

_CONTEXT_REPLACEMENTS = (
    (r"Fundaci[oó]n\s+Valle\s+del\s+Lili", "FVL"),
    (r"##\s+Especialistas\s+que\s+pueden\s+atenderte", "## ESP"),
    (r"##\s+Procedimientos\s+y\s+tratamientos", "## PROC"),
    (r"##\s+Tratamiento", "## TRAT"),
    (r"##\s+Contacto", "## CONTACTO"),
)

_HISTORY_MAX_TURNS = int(os.getenv("HISTORY_MAX_TURNS", "6"))
_HISTORY_MAX_CHARS = int(os.getenv("HISTORY_MAX_CHARS", "3500"))
_HISTORY_ITEM_MAX_CHARS = int(os.getenv("HISTORY_ITEM_MAX_CHARS", "700"))
_RESPONSE_MAX_TOKENS = int(os.getenv("RESPONSE_MAX_TOKENS", "500"))
_LINE_LEXICON_ENABLED = os.getenv("LINE_LEXICON_ENABLED", "true").lower() == "true"
_LINE_LEXICON_MIN_COUNT = int(os.getenv("LINE_LEXICON_MIN_COUNT", "5"))
_LINE_LEXICON_MIN_LEN = int(os.getenv("LINE_LEXICON_MIN_LEN", "24"))
_LINE_LEXICON_MAX_ENTRIES = int(os.getenv("LINE_LEXICON_MAX_ENTRIES", "350"))
_OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


def _compress_repeated_lines(text: str) -> str:
    if not _LINE_LEXICON_ENABLED:
        return text

    lines = text.split("\n")
    stripped_lines = [line.strip() for line in lines]
    counts = Counter(
        line for line in stripped_lines if line and len(line) >= _LINE_LEXICON_MIN_LEN
    )

    candidates = [
        line for line, count in counts.items() if count >= _LINE_LEXICON_MIN_COUNT
    ]
    if not candidates:
        return text

    candidates.sort(key=lambda line: (counts[line] - 1) * len(line), reverse=True)
    selected = candidates[:_LINE_LEXICON_MAX_ENTRIES]

    line_to_token = {
        line: f"L{index:03d}" for index, line in enumerate(selected, start=1)
    }

    compressed_lines: list[str] = []
    for raw_line in lines:
        token = line_to_token.get(raw_line.strip())
        compressed_lines.append(token if token is not None else raw_line)

    lexicon_lines = ["LEXICO_LINEAS"]
    for line, token in line_to_token.items():
        lexicon_lines.append(f"{token}={line}")
    lexicon_lines.append("FIN_LEXICO_LINEAS")

    return "\n".join(lexicon_lines) + "\n\n" + "\n".join(compressed_lines)


def _compact_context(text: str) -> str:
    compacted = text.replace("\r\n", "\n").replace("\r", "\n")
    compacted = _DOC_SEPARATOR_RE.sub(
        lambda m: f"\nDOC:{m.group(1).strip()}\n", compacted
    )

    for pattern, replacement in _CONTEXT_REPLACEMENTS:
        compacted = re.sub(pattern, replacement, compacted, flags=re.IGNORECASE)

    compacted = _MULTI_NEWLINE_RE.sub("\n\n", compacted)
    compacted = _compress_repeated_lines(compacted)
    return compacted.strip()


def load_knowledge_base(knowledge_dir: str) -> str:
    """Lee recursivamente todos los .md de knowledge_dir y los consolida en un solo string."""
    base = Path(knowledge_dir)
    if not base.exists():
        raise FileNotFoundError(
            f"La carpeta de conocimiento no existe: {knowledge_dir}"
        )

    docs: list[str] = []
    for md_file in sorted(base.rglob("*.md")):
        raw = md_file.read_text(encoding="utf-8")
        content = _FRONTMATTER_RE.sub("", raw).strip()
        if not content:
            continue
        slug = md_file.stem
        docs.append(f"\n\n====== DOCUMENTO: {slug} ======\n\n{content}")

    if not docs:
        raise ValueError(f"No se encontraron archivos .md en: {knowledge_dir}")

    full_context = "".join(docs)
    compact_context = _compact_context(full_context)

    debug_path = Path("data/debug_context.txt")
    debug_path.parent.mkdir(parents=True, exist_ok=True)
    debug_path.write_text(compact_context, encoding="utf-8")

    raw_debug_path = Path("data/debug_context_raw.txt")
    raw_debug_path.write_text(full_context, encoding="utf-8")

    return compact_context


def build_chain() -> Runnable:
    """Construye la cadena LangChain: PromptTemplate | ChatOpenAI | StrOutputParser."""
    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0.1,
        max_completion_tokens=_RESPONSE_MAX_TOKENS,
        api_key=SecretStr(_OPENAI_API_KEY) if _OPENAI_API_KEY else None,
    )
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_TEMPLATE),
            MessagesPlaceholder("history_messages"),
            ("human", "{question}"),
        ]
    )
    return prompt | llm | StrOutputParser()


def get_response(
    chain: Runnable, context: str, question: str, history: list[dict]
) -> str:
    """Invoca la cadena con contexto completo, historial recortado y pregunta."""
    return chain.invoke(
        {
            "context": context,
            "history_messages": _history_to_messages(history),
            "question": question,
        }
    )


def _history_to_messages(history: list[dict]) -> list[HumanMessage | AIMessage]:
    """Convierte historial a mensajes LangChain con presupuesto de tokens."""
    selected = history[-_HISTORY_MAX_TURNS:]
    messages: list[HumanMessage | AIMessage] = []
    chars_used = 0

    for msg in selected:
        content = str(msg["content"]).strip()
        if len(content) > _HISTORY_ITEM_MAX_CHARS:
            content = content[: _HISTORY_ITEM_MAX_CHARS - 1].rstrip() + "..."
        projected = chars_used + len(content)
        if projected > _HISTORY_MAX_CHARS:
            break

        if msg.get("role") == "assistant":
            messages.append(AIMessage(content=content))
        else:
            messages.append(HumanMessage(content=content))
        chars_used = projected

    return messages
