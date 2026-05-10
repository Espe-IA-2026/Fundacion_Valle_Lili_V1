# CLAUDE.md — Asistente Virtual FVL

Guía de referencia para asistentes de IA trabajando en este repositorio.

---

## Resumen del Proyecto

**Asistente Virtual para la Fundación Valle del Lili (FVL)** — hospital de alta complejidad en Cali, Colombia.

El repositorio tiene dos piezas integradas:

1. **`semantic_layer_fvl`** — pipeline ETL que extrae contenido público institucional y genera una base de conocimiento en Markdown.
2. **`app`** — dashboard Streamlit con tres funcionalidades LLM (Q&A, Resumen, FAQ) orquestadas con LangChain.

**Premisa clave (Módulo 1):** estrategia **NO-RAG** — todo el conocimiento se inyecta directamente en el prompt de sistema (context stuffing). No hay vectorstore ni retrieval semántico en esta fase.

**Módulo 2 (planificado):** evolución a RAG. El módulo `TextChunker` en `src/semantic_layer_fvl/processors/chunker.py` ya está scaffoldeado para esa fase.

---

## Stack Tecnológico

| Capa | Tecnología |
|---|---|
| Lenguaje | Python 3.11+ |
| Gestor de paquetes | **`uv`** (no usar pip ni poetry) |
| Modelos de datos | `pydantic` v2 + `pydantic-settings` |
| HTTP | `httpx` (con retry exponencial), `requests` |
| Scraping | `beautifulsoup4`, `markdownify` |
| YouTube | `yt-dlp` (sin descarga de video, solo metadatos y transcripciones) |
| LLM | `langchain` + `langchain-openai` (LCEL), OpenAI `gpt-4o-mini` |
| Dashboard | `streamlit` |
| Linting | `ruff` (line-length: 110) |
| Testing | `pytest` (88 tests, todos offline) |

---

## Setup de Desarrollo

```bash
# 1. Instalar dependencias desde uv.lock
uv sync

# 2. Crear y configurar .env
cp .env.example .env
# Editar .env y definir al menos:
#   OPENAI_API_KEY=<tu_key>
#   OPENAI_MODEL=gpt-4o-mini
#   KNOWLEDGE_DIR=data/knowledge

# 3. Verificar instalación
uv run semantic-layer-fvl show-config
uv run pytest -q
```

---

## Comandos de Desarrollo

```bash
# Tests
uv run pytest
uv run pytest -q            # salida compacta

# Linting y formato
uv run ruff check src/ tests/
uv run ruff format src/ tests/

# Crawling por dominio (genera archivos en data/knowledge/)
uv run semantic-layer-fvl crawl-domain servicios --write
uv run semantic-layer-fvl crawl-domain especialistas --write
uv run semantic-layer-fvl crawl-domain sedes --write
uv run semantic-layer-fvl crawl-domain institucional --write
uv run semantic-layer-fvl crawl-domain servicios --write --max-urls 50  # con límite

# Fuentes externas
uv run semantic-layer-fvl youtube-search "Fundacion Valle del Lili" --limit 20 --write
uv run semantic-layer-fvl news-curated --write

# Dashboard
uv run streamlit run src/app/main.py   # abre en http://localhost:8501

# Makefile (atajos)
make servicios
make especialistas
make sedes
make institucional
make app
```

---

## Estructura de Directorios

```
Fundacion_Valle_Lili_V1/
├── src/
│   ├── semantic_layer_fvl/       # Librería core del pipeline ETL
│   │   ├── cli.py                # Entry point CLI (semantic-layer-fvl)
│   │   ├── domains.py            # Config de los 4 dominios de crawling
│   │   ├── news_feeds.py         # Feeds RSS curados + queries Google News
│   │   ├── config/
│   │   │   ├── settings.py       # Pydantic Settings — singleton via get_settings()
│   │   │   └── logging.py
│   │   ├── extractors/
│   │   │   ├── web_crawler.py    # WebCrawler (CSS selectors + robots.txt)
│   │   │   ├── youtube_rich.py   # YouTubeRichExtractor (yt-dlp)
│   │   │   ├── news.py           # NewsFeedExtractor (RSS/Atom)
│   │   │   ├── google_news.py    # GoogleNewsFeedBuilder (RSS URLs)
│   │   │   ├── http_client.py    # HttpClient con retry exponencial
│   │   │   ├── robots.py         # RobotsPolicy (compliance robots.txt)
│   │   │   └── site_map.py       # Extracción de sitemaps
│   │   ├── processors/
│   │   │   ├── cleaner.py        # TextCleaner (presets WEB_FVL/NEWS/YOUTUBE)
│   │   │   ├── deduplicator.py   # ContentDeduplicator (URL canónica + SHA-256)
│   │   │   ├── structurer.py     # SemanticStructurer (categoría + slug)
│   │   │   ├── chunker.py        # TextChunker (reservado para Módulo 2/RAG)
│   │   │   └── noise_presets.py  # Constantes de ruido por tipo de fuente
│   │   ├── schemas/
│   │   │   ├── documents.py      # RawPage, SourceDocument, ProcessedDocument
│   │   │   └── runs.py           # PipelineRunSummary, PipelineItemResult
│   │   ├── writers/
│   │   │   └── markdown_writer.py # MarkdownWriter (frontmatter YAML)
│   │   └── orchestrator/
│   │       └── pipeline.py       # SemanticPipeline — coordinador principal
│   └── app/
│       ├── engine.py             # Cadenas LCEL + load_knowledge_base() + stream_response()
│       └── main.py               # Dashboard Streamlit (3 pestañas)
├── tests/                        # 88 tests unitarios offline
│   └── conftest.py               # Fixtures compartidos
├── data/
│   └── knowledge/                # Base de conocimiento generada (gitignored)
│       ├── 01_servicios/
│       ├── 02_especialistas/
│       ├── 03_sedes/
│       ├── 04_institucional/
│       ├── 09_noticias/
│       └── 10_multimedia/
├── reports/runs/                 # Resúmenes JSON de corridas del pipeline
├── docs/
│   └── guia_exposicion.md        # Guía de presentación del proyecto
├── pyproject.toml
├── .env.example
└── Makefile
```

---

## Módulos y Clases Clave

### Pipeline ETL (`src/semantic_layer_fvl/`)

| Clase / Función | Archivo | Descripción |
|---|---|---|
| `SemanticPipeline` | `orchestrator/pipeline.py` | Coordinador principal del pipeline. Métodos: `run_domain()`, `process_raw_page()`, `youtube_search()`, `news_curated()` |
| `WebCrawler` | `extractors/web_crawler.py` | Scraper por CSS selectors; respeta robots.txt; convierte HTML→Markdown |
| `YouTubeRichExtractor` | `extractors/youtube_rich.py` | Extrae metadatos y transcripciones VTT/json3 via yt-dlp (sin descarga) |
| `NewsFeedExtractor` | `extractors/news.py` | Parsea feeds RSS/Atom; soporte para fetch del artículo completo |
| `GoogleNewsFeedBuilder` | `extractors/google_news.py` | Construye URLs RSS de Google News por keyword |
| `HttpClient` | `extractors/http_client.py` | Wrapper httpx con retry exponencial (respeta `Retry-After`) |
| `RobotsPolicy` | `extractors/robots.py` | Compliance con robots.txt |
| `TextCleaner` | `processors/cleaner.py` | Limpieza configurable con presets `WEB_FVL_NOISE`, `NEWS_NOISE`, `YOUTUBE_NOISE` |
| `ContentDeduplicator` | `processors/deduplicator.py` | Deduplicación por URL canónica + checksum SHA-256 del contenido |
| `SemanticStructurer` | `processors/structurer.py` | Infiere categoría, genera slug, estructura el markdown final |
| `MarkdownWriter` | `writers/markdown_writer.py` | Serializa `ProcessedDocument` a `.md` con frontmatter YAML |
| `get_settings()` | `config/settings.py` | Singleton `@lru_cache` — única forma de acceder a la configuración |

### Dashboard LLM (`src/app/`)

| Función | Archivo | Descripción |
|---|---|---|
| `build_chain()` | `engine.py` | Cadena Q&A conversacional con historial (`MessagesPlaceholder`), temperatura 0.1 |
| `build_summary_chain()` | `engine.py` | Cadena de resumen estructurado en Markdown, temperatura 0.2 |
| `build_faq_chain()` | `engine.py` | Genera 5–8 preguntas frecuentes con respuestas, temperatura 0.2 |
| `load_knowledge_base()` | `engine.py` | Carga y concatena todos los `.md` de `KNOWLEDGE_DIR` |
| `stream_response()` | `engine.py` | Generador de chunks para streaming en Streamlit (`st.write_stream()`) |

### Schemas Pydantic (`src/semantic_layer_fvl/schemas/`)

```python
RawPage            # Página descargada (url, html, text_content, metadata)
SourceDocument     # Documento fuente (document_id, title, slug, category, source_url)
ProcessedDocument  # Documento procesado (document + content_markdown + headings)
DocumentCategory   # StrEnum con prefijos numéricos: "01_servicios", "02_especialistas"...
PipelineRunSummary # Estadísticas de corrida (total, success, failures, duration)
```

---

## Convenciones de Código

### Lenguaje
- Docstrings y mensajes de commit en **español**
- Nombres de variables, funciones y clases en inglés (Python estándar)

### Nomenclatura
- Archivos y módulos: `snake_case` (`web_crawler.py`, `noise_presets.py`)
- Clases: `PascalCase` (`WebCrawler`, `SemanticPipeline`)
- Funciones y variables: `snake_case`
- Métodos privados: prefijo `_` (`_is_noise()`, `_normalize_line()`)
- Booleanos: prefijo `is_` o `has_` (`is_duplicate()`, `has_content`)
- Builders: prefijo `build_` (`build_chain()`, `build_document()`)
- Handlers CLI: prefijo `handle_` (`handle_crawl_domain()`)

### Estilo
- Line length: **110 caracteres** (ruff)
- `from __future__ import annotations` en todos los módulos con anotaciones de tipo
- API pública declarada con `__all__` en cada `__init__.py`
- Nunca instanciar `Settings()` directamente — usar siempre `get_settings()`
- Sin base de datos tradicional — el conocimiento es file-based (Markdown + YAML frontmatter)

### Imports
```python
from __future__ import annotations

# Stdlib primero, luego third-party, luego internos
import logging
from pathlib import Path

import httpx
from pydantic import BaseModel

from semantic_layer_fvl.config import get_settings
from semantic_layer_fvl.schemas import ProcessedDocument
```

### Manejo de errores
- Errores capturados con `try/except` específicos, registrados con `logger.exception()`
- Resultados de pipeline rastreados en `PipelineRunSummary` (no re-lanzar excepciones)
- Validación solo en límites del sistema (input de usuario, APIs externas)

---

## Dominios Configurados

Definidos en `src/semantic_layer_fvl/domains.py`. Cada dominio tiene: sitemaps, patrones include/exclude de URL, selector CSS principal, metadatos extra y reglas de limpieza.

| Dominio | Carpeta destino | Comando |
|---|---|---|
| `servicios` | `data/knowledge/01_servicios/` | `crawl-domain servicios --write` |
| `especialistas` | `data/knowledge/02_especialistas/` | `crawl-domain especialistas --write` |
| `sedes` | `data/knowledge/03_sedes/` | `crawl-domain sedes --write` |
| `institucional` | `data/knowledge/04_institucional/` | `crawl-domain institucional --write` |
| *(externas)* | `data/knowledge/09_noticias/` | `news-curated --write` |
| *(externas)* | `data/knowledge/10_multimedia/` | `youtube-search "..." --write` |

---

## Variables de Entorno

Ver `.env.example` para todos los valores. Los mínimos requeridos:

```dotenv
# Requeridos para la app
OPENAI_API_KEY=<tu_key>
OPENAI_MODEL=gpt-4o-mini
KNOWLEDGE_DIR=data/knowledge

# Presupuestos de inferencia (tokens de salida por tarea)
RESPONSE_MAX_TOKENS=500    # Q&A
SUMMARY_MAX_TOKENS=900     # Resumen
FAQ_MAX_TOKENS=1200        # FAQ

# Historial Q&A
HISTORY_MAX_TURNS=6
HISTORY_MAX_CHARS=3500
HISTORY_ITEM_MAX_CHARS=700

# Compactación de contexto (reduce tokens del knowledge base)
LINE_LEXICON_ENABLED=true
LINE_LEXICON_MIN_COUNT=5
LINE_LEXICON_MIN_LEN=24
LINE_LEXICON_MAX_ENTRIES=350

# HTTP
MAX_RETRIES=2
REQUEST_TIMEOUT=30

# YouTube (opcional)
YOUTUBE_SEARCH_LIMIT=20
YOUTUBE_TRANSCRIPT_LANGUAGES=["es","es-419","en"]

# Noticias (opcional)
NEWS_CURATED_ENABLED=true
NEWS_FETCH_FULL_ARTICLE=false
NEWS_FEED_LIMIT=50
```

---

## Testing

- **88 tests unitarios**, todos **offline** (sin llamadas reales a OpenAI, YouTube ni Google News)
- Mocks implementados con `httpx` y parches de `yt-dlp`
- Fixtures compartidos en `tests/conftest.py`

```bash
uv run pytest -q    # ejecutar toda la suite
uv run pytest tests/test_pipeline.py -v   # un archivo específico
```

**Convención al agregar código nuevo:** cada extractor o procesador nuevo debe tener un archivo `tests/test_<módulo>.py` correspondiente con tests offline.

| Archivo de test | Qué cubre |
|---|---|
| `test_settings.py` | Carga de config desde `.env` |
| `test_schemas.py` | Validación de modelos Pydantic |
| `test_web_crawler.py` | WebCrawler, selectors CSS, conversión HTML→MD |
| `test_pipeline.py` | SemanticPipeline end-to-end |
| `test_cli.py` | Comandos CLI y argumentos |
| `test_http_retry.py` | Retry exponencial (503, 429, timeout) |
| `test_deduplicator.py` | Dedup por URL canónica y SHA-256 |
| `test_youtube_rich.py` | YouTubeRichExtractor con mock de yt-dlp |
| `test_google_news.py` | Construcción de URLs RSS Google News |
| `test_cleaner_presets.py` | Presets WEB_FVL, NEWS, YOUTUBE |

---

## Decisiones de Arquitectura

### NO-RAG (Módulo 1)
Todo el knowledge base se concatena y se inyecta en el prompt de sistema. Simple, determinista, sin infraestructura de vectores. El costo es proporcional al tamaño del corpus. La compactación de contexto (`LINE_LEXICON`) mitiga este costo.

### Compactación de contexto
Antes de inyectar el conocimiento, `engine.py` aplica: normalización de saltos de línea, reemplazo de frases repetitivas por abreviaturas, y compresión por léxico de líneas (`LEXICO_LINEAS`). Los archivos de debug (`data/debug_context_raw.txt` y `data/debug_context.txt`) permiten medir la tasa de compresión.

### yt-dlp sobre YouTube Data API
No requiere autenticación, maneja transcripciones VTT/json3 nativamente y soporta búsqueda por keyword sin cuota. Solo se extraen metadatos (sin descarga de video).

### Redes sociales excluidas
LinkedIn, Instagram y Twitter/X excluidos por restricciones de TOS y riesgo de bloqueo. Si la FVL provee tokens oficiales, se pueden agregar sin refactor mayor.

### Frontmatter YAML extendido
Cada `.md` generado incluye: `title`, `category`, `slug`, `source_url`, `published_at`, `source_type` (`web` | `youtube` | `news`), `external_id`. Esto facilita la transición futura a RAG con metadatos de filtrado.

---

## Convenciones Git

- Mensajes de commit en **español**, descriptivos del "qué" y el "por qué"
- Ramas de features: `claude/<descripcion>` o `<feature>-v<N>`
- **Nunca** commitear `.env` ni archivos bajo `data/` (ambos en `.gitignore`)
- Los resúmenes de corrida en `reports/runs/` también están en `.gitignore`

---

## Estado del Módulo

| Iteración | Estado | Contenido |
|---|---|---|
| Iteración 1 | Completa | Pipeline web (4 dominios) + dashboard NO-RAG (Q&A, Resumen, FAQ) |
| Iteración 2 | Completa | YouTubeRichExtractor, noticias curadas, deduplicación, retry HTTP, presets de ruido, streaming LCEL |
| Módulo 2 | Planificado | RAG con vectorstore — `TextChunker` ya scaffoldeado en `processors/chunker.py` |
