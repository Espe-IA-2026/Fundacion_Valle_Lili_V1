# Asistente Virtual FVL — Módulo 1 + Módulo 2

Pipeline de extracción y estructuración de conocimiento para la Fundación Valle del Lili + dashboard Streamlit con cuatro funcionalidades LLM: tres basadas en context stuffing (NO-RAG) y un agente conversacional con recuperación semántica dinámica (RAG).

---

## 1. Objetivo

Este repositorio integra dos módulos complementarios:

1. **`semantic_layer_fvl`**: capa semántica que extrae información pública institucional y genera una base de conocimiento en Markdown con frontmatter YAML extendido.
2. **`app`** (Módulo 1 — NO-RAG): motor y frontend que consumen esa base de conocimiento usando context stuffing — todo el conocimiento consolidado en el prompt de sistema — y exponen tres funcionalidades LLM.
3. **`app_agent`** (Módulo 2 — RAG): agente conversacional ReACT que recupera dinámicamente fragmentos relevantes desde un índice vectorial ChromaDB, mantiene memoria de sesión por checkpointer y responde únicamente con información institucional verificada.

Resultado final:

- Base de conocimiento limpia en `data/knowledge/` organizada por dominios institucionales.
- Índice vectorial ChromaDB en `data/chroma_db/` con embeddings sobre los documentos generados.
- Dashboard Streamlit con cuatro herramientas:
  - **💬 Q&A conversacional** (NO-RAG): chatbot con historial de turnos y context stuffing.
  - **📋 Resumen** (NO-RAG): síntesis estructurada en Markdown de cualquier tema institucional.
  - **❓ FAQ** (NO-RAG): 5–8 preguntas frecuentes con respuestas fundamentadas en documentos.
  - **🤖 Agente RAG**: agente ReACT con recuperación semántica dinámica y memoria de sesión.

---

## 2. Arquitectura End-to-End

```text
valledellili.org      YouTube (yt-dlp)      Feeds RSS curados
  + sitemaps           + transcripciones      + Google News RSS
      |                      |                      |
      v                      v                      v
 WebCrawler          YouTubeRichExtractor    NewsFeedExtractor
      |                      |                      |
      └──────────────────────┴──────────────────────┘
                             |
                             v
                    ContentDeduplicator
                    (URL canónica + SHA-256)
                             |
                             v
                      RawPage (Pydantic)
                             |
                             v
               processors (TextCleaner + structurer)
                  [presets: WEB_FVL / NEWS / YOUTUBE]
                             |
                             v
                   ProcessedDocument (Pydantic)
                             |
                             v
               writers (markdown + frontmatter YAML)
                  [source_type · external_id · published_at]
                             |
                             v
         data/knowledge/<dominio>/<slug>.md
                    ┌────────┴─────────────────────────────────┐
                    │ MÓDULO 1 (NO-RAG)                         │ MÓDULO 2 (RAG)
                    v                                           v
         app.engine → contexto consolidado         KnowledgeIndexer
                    + compactación                  (rag/indexer.py)
                    |                                    |
                    v                              OpenAI Embeddings
          LangChain LCEL + OpenAI              text-embedding-3-small
          ┌──────────┬──────────┐                    |
          v          v          v                    v
       Q&A chain  Summary   FAQ chain        ChromaDB (vectorstore)
       (streaming) chain                     data/chroma_db/
                                                    |
                                                    v
                                          KnowledgeRetriever
                                           (rag/retriever.py)
                                                    |
                                                    v
                                      @tool retrieve_fvl_knowledge
                                         (app_agent/tools.py)
                                                    |
                                                    v
                                    create_agent (LangChain) +
                                    InMemorySaver checkpointer
                                       (app_agent/agent.py)
                                                    |
                                          ciclo ReACT:
                                      razonar → tool call
                                      → razonar → responder
                                                    |
                                                    v
                                    stream_agent_response()
                                       thread_id UUID/sesión
                                       (app_agent/engine.py)
                                                    |
                    └───────────────────────────────┘
                                             |
                                             v
                              Streamlit dashboard (4 pestañas)
                         [wide layout · sidebar · CSS profesional]
```

---

## 3. Dominios Configurados

Definidos en `src/semantic_layer_fvl/domains.py`:

| Dominio | Carpeta destino | Comando |
|---|---|---|
| `servicios` | `data/knowledge/01_servicios/` | `crawl-domain servicios --write` |
| `especialistas` | `data/knowledge/02_especialistas/` | `crawl-domain especialistas --write` |
| `sedes` | `data/knowledge/03_sedes/` | `crawl-domain sedes --write` |
| `institucional` | `data/knowledge/04_institucional/` | `crawl-domain institucional --write` |

Cada dominio define sitemaps, patrones include/exclude de URL, selector principal de contenido, metadatos extra por selector y reglas de limpieza de markdown.

---

## 4. Fuentes Externas

Fuentes adicionales legalmente accesibles que amplían el corpus:

| Tipo | Comando CLI | Carpeta destino |
|---|---|---|
| YouTube enriquecido (yt-dlp) | `youtube-search` | `data/knowledge/10_multimedia/` |
| Noticias curadas (RSS) | `news-curated` | `data/knowledge/09_noticias/` |
| Google News RSS por keyword | incluido en `news-curated` | `data/knowledge/09_noticias/` |

**Redes sociales (LinkedIn, Instagram, Twitter/X)**: excluidas por restricciones de TOS. Si la FVL provee tokens oficiales, se pueden agregar sin refactor mayor.

---

## 5. Módulo 1 — Estrategia NO-RAG

Las tres primeras pestañas no usan vectorstore ni retrieval semántico. El conocimiento se consolida y se inyecta íntegro en el prompt de sistema de cada cadena.

### Cadenas LangChain disponibles (`src/app/engine.py`)

| Función | Cadena | Descripción |
|---|---|---|
| `build_chain()` | Q&A | Chat multi-turno con `MessagesPlaceholder`. Temperatura 0.1. |
| `build_summary_chain()` | Resumen | Síntesis estructurada en Markdown por tema. Temperatura 0.2. |
| `build_faq_chain()` | FAQ | 5–8 preguntas frecuentes con respuestas. Temperatura 0.2. |

### Optimizaciones de costo de inferencia

Para reducir tokens sin romper la premisa NO-RAG:

1. **Scope correcto de conocimiento**: `KNOWLEDGE_DIR=data/knowledge`.
2. **Compactación determinista de contexto**: normalización de saltos de línea, reemplazo de frases repetitivas por abreviaturas y compresión por léxico de líneas (`LEXICO_LINEAS`).
3. **Historial con presupuesto**: límite por turnos, por caracteres totales y por mensaje.
4. **Presupuestos de salida por tarea**: `RESPONSE_MAX_TOKENS`, `SUMMARY_MAX_TOKENS`, `FAQ_MAX_TOKENS`.
5. **Trazabilidad**: `data/debug_context_raw.txt` (consolidado original) y `data/debug_context.txt` (consolidado compacto).

---

## 6. Módulo 2 — Agente RAG

### Componentes

**`src/rag/indexer.py` — `KnowledgeIndexer`**

Lee todos los `.md` del knowledge base, extrae el frontmatter YAML como metadatos, divide el cuerpo con `TextChunker(max_chunk_size=1000, chunk_overlap=200)` y construye el índice ChromaDB con embeddings `text-embedding-3-small`. Incluye `_sanitize_metadata()` que convierte listas, fechas, `AnyHttpUrl` y `None` a tipos aceptados por ChromaDB (`str/int/float/bool`). El método `build_or_load(force=False)` detecta si el índice ya existe y lo carga sin re-indexar.

**`src/rag/retriever.py` — `KnowledgeRetriever`**

Envuelve ChromaDB y expone `search(query, k, score_threshold)` que filtra los resultados por similitud mínima usando `similarity_search_with_relevance_scores`.

**`src/app_agent/tools.py` — `retrieve_fvl_knowledge`**

Herramienta LangChain (`@tool`) que el agente invoca durante el ciclo ReACT. Usa un singleton `_retriever` con lazy initialization. Llama a `retriever.search(query, k=rag_top_k, score_threshold=rag_score_threshold)` y formatea la salida con headers `[Fragmento N — slug (category)]` separados por `---`. Si no hay resultados, devuelve un mensaje literal para que el agente lo comunique al usuario sin inventar datos.

**`src/app_agent/agent.py` — `build_rag_agent()`**

Construye el agente usando `create_agent` de `langchain.agents` con:
- Modelo `ChatOpenAI(temperature=0.1)` para respuestas deterministas.
- `tools=[retrieve_fvl_knowledge]`.
- `system_prompt` estricto que instruye al agente a siempre recuperar antes de responder, nunca inventar datos y citar fuentes con formato `DOC:<slug>`.
- `checkpointer=InMemorySaver()` de LangGraph para memoria de sesión diferenciada por `thread_id`.

**`src/app_agent/engine.py` — `get_rag_agent()` y `stream_agent_response()`**

`get_rag_agent(force_rebuild=False)` es un singleton con lazy initialization. `force_rebuild=True` es útil tras re-indexar con `build-index --force`.

`stream_agent_response(question, thread_id)` envía únicamente el mensaje actual al agente; el checkpointer recupera el historial del hilo automáticamente. Filtra el stream para emitir solo el `AIMessage` final, descartando `ToolMessage` intermedios y `AIMessage` con `tool_calls` pendientes.

### Memoria de sesión

El `thread_id` es un UUID generado en Streamlit una vez por sesión (`st.session_state.rag_thread_id`). Al limpiar el chat se regenera el UUID, iniciando un nuevo hilo aislado en el checkpointer. La UI mantiene `st.session_state.rag_messages` exclusivamente para renderizado — **no se pasa historial al backend**.

### Comando CLI para indexar

```powershell
# Construir índice desde cero (primera vez o tras actualizar el knowledge base)
uv run semantic-layer-fvl build-index

# Forzar reconstrucción completa (descarta índice existente)
uv run semantic-layer-fvl build-index --force
```

Salida esperada: `index_ready=True`, `chunks=N`, `chroma_dir=<ruta>`.

---

## 7. Estructura del Proyecto

```text
.
├── Makefile
├── pyproject.toml               ← requires-python = ">=3.11,<3.14"
├── .python-version              ← 3.12 (pinned con uv)
├── .env.example
├── data/
│   ├── knowledge/               ← generado por el pipeline ETL (gitignored)
│   │   ├── 01_servicios/
│   │   ├── 02_especialistas/
│   │   ├── 03_sedes/
│   │   ├── 04_institucional/
│   │   ├── 09_noticias/
│   │   └── 10_multimedia/
│   ├── chroma_db/               ← índice vectorial ChromaDB (gitignored)
│   ├── debug_context.txt
│   └── debug_context_raw.txt
├── reports/
│   └── runs/
├── src/
│   ├── semantic_layer_fvl/      ← pipeline ETL (Módulo 1 + 2)
│   │   ├── cli.py               ← entry point CLI (incluye build-index)
│   │   ├── domains.py
│   │   ├── news_feeds.py
│   │   ├── config/
│   │   │   └── settings.py      ← Settings pydantic (RAG + LLM + HTTP)
│   │   ├── extractors/
│   │   │   ├── web_crawler.py
│   │   │   ├── youtube_rich.py
│   │   │   ├── news.py
│   │   │   ├── google_news.py
│   │   │   ├── http_client.py
│   │   │   └── ...
│   │   ├── processors/
│   │   │   ├── chunker.py       ← TextChunker usado por KnowledgeIndexer
│   │   │   ├── cleaner.py
│   │   │   ├── deduplicator.py
│   │   │   └── ...
│   │   ├── schemas/
│   │   ├── writers/
│   │   └── orchestrator/
│   ├── rag/                     ← capa vectorial (Módulo 2)
│   │   ├── indexer.py           ← KnowledgeIndexer + _sanitize_metadata()
│   │   └── retriever.py         ← KnowledgeRetriever
│   ├── app_agent/               ← agente RAG (Módulo 2)
│   │   ├── tools.py             ← @tool retrieve_fvl_knowledge
│   │   ├── agent.py             ← build_rag_agent() con checkpointer
│   │   ├── engine.py            ← singleton + stream_agent_response()
│   │   └── __init__.py
│   └── app/                     ← dashboard Streamlit (Módulo 1 + 2)
│       ├── engine.py            ← cadenas LCEL + stream_response()
│       └── main.py              ← 4 pestañas (Q&A, Resumen, FAQ, Agente RAG)
└── tests/                       ← ~105 tests (todos offline)
    ├── test_rag_indexer.py      ← 9 tests KnowledgeIndexer
    ├── test_rag_retriever.py    ← 6 tests KnowledgeRetriever
    ├── test_rag_tools.py        ← 6 tests retrieve_fvl_knowledge
    ├── test_rag_agent.py        ← 4 tests build_rag_agent
    ├── test_rag_engine.py       ← 7 tests get_rag_agent + stream_agent_response
    └── ...                      ← 88 tests existentes de Módulo 1
```

---

## 8. Stack Tecnológico

| Capa | Tecnología |
|---|---|
| Lenguaje | Python **3.12** (pinned; incompatible con 3.14 por pydantic + langchain legacy) |
| Gestor de paquetes | `uv` |
| LLM | `langchain 0.3` + `langchain-openai` + OpenAI `gpt-4o-mini` |
| Embeddings | `text-embedding-3-small` via `langchain-openai` |
| Agente | `create_agent` de `langchain.agents` |
| Grafo / Memoria | `langgraph 1.0` — `InMemorySaver` checkpointer |
| Vectorstore | `chromadb` + `langchain-chroma` |
| Modelos de datos | `pydantic v2` + `pydantic-settings` |
| HTTP | `httpx` con retry exponencial |
| Scraping | `beautifulsoup4`, `markdownify` |
| YouTube | `yt-dlp` (sin descarga de video) |
| Dashboard | `streamlit` |
| Linting | `ruff` (line-length: 110) |
| Testing | `pytest` (~105 tests, todos offline) |

---

## 9. Requisitos

- Python 3.12 (no compatible con 3.14)
- `uv` instalado
- OpenAI API key

---

## 10. Configuración

### 10.1 Crear entorno local

```powershell
uv sync
```

> Si Python 3.12 no está instalado: `uv python install 3.12` antes de `uv sync`.

### 10.2 Configurar variables

```powershell
Copy-Item .env.example .env
```

Variables mínimas requeridas:

```dotenv
# LLM
OPENAI_API_KEY=<tu_api_key>
OPENAI_MODEL=gpt-4o-mini

# Rutas
KNOWLEDGE_DIR=data/knowledge
CHROMA_PERSIST_DIR=./data/chroma_db

# RAG
EMBEDDING_MODEL=text-embedding-3-small
RAG_TOP_K=5
RAG_SCORE_THRESHOLD=0.3
AGENT_MAX_ITERATIONS=6

# Presupuestos de inferencia (NO-RAG)
RESPONSE_MAX_TOKENS=500
SUMMARY_MAX_TOKENS=900
FAQ_MAX_TOKENS=1200
HISTORY_MAX_TURNS=6
HISTORY_MAX_CHARS=3500
HISTORY_ITEM_MAX_CHARS=700
```

### 10.3 Verificar instalación

```powershell
uv run semantic-layer-fvl show-config
uv run pytest -q
```

---

## 11. Comandos Operativos

### 11.1 Generar base de conocimiento (ETL)

```powershell
# Dominios institucionales (obligatorio)
uv run semantic-layer-fvl crawl-domain servicios --write
uv run semantic-layer-fvl crawl-domain especialistas --write
uv run semantic-layer-fvl crawl-domain sedes --write
uv run semantic-layer-fvl crawl-domain institucional --write

# Con límite de URLs
uv run semantic-layer-fvl crawl-domain servicios --write --max-urls 50

# Fuentes externas (opcional)
uv run semantic-layer-fvl youtube-search "Fundacion Valle del Lili" --limit 20 --write
uv run semantic-layer-fvl news-curated --write
```

### 11.2 Construir índice vectorial (Módulo 2)

```powershell
# Primera vez o tras actualizar el knowledge base
uv run semantic-layer-fvl build-index

# Reconstruir desde cero (descarta índice existente)
uv run semantic-layer-fvl build-index --force
```

### 11.3 Iniciar dashboard

```powershell
uv run streamlit run src/app/main.py
```

Abre en `http://localhost:8501`. La primera consulta a la pestaña **🤖 Agente RAG** inicializa el agente y carga ChromaDB (puede tomar unos segundos).

### 11.4 Atajos Makefile

```powershell
make servicios
make especialistas
make sedes
make institucional
make app
```

---

## 12. Replicar en Otro Equipo

### Paso 1. Clonar el repositorio

```powershell
git clone <URL_DEL_REPO>
cd Fundacion_Valle_Lili_V1
```

### Paso 2. Instalar dependencias

```powershell
uv python install 3.12   # si no está instalado
uv sync
```

### Paso 3. Crear y ajustar `.env`

```powershell
Copy-Item .env.example .env
# Editar y completar OPENAI_API_KEY y demás variables
```

### Paso 4. Generar base de conocimiento

```powershell
uv run semantic-layer-fvl crawl-domain servicios --write
uv run semantic-layer-fvl crawl-domain especialistas --write
uv run semantic-layer-fvl crawl-domain sedes --write
uv run semantic-layer-fvl crawl-domain institucional --write

# Opcional
uv run semantic-layer-fvl youtube-search "Fundacion Valle del Lili" --limit 20 --write
uv run semantic-layer-fvl news-curated --write
```

### Paso 5. Construir el índice vectorial

```powershell
uv run semantic-layer-fvl build-index
```

### Paso 6. Verificar e iniciar

```powershell
uv run pytest -q
uv run streamlit run src/app/main.py
```

---

## 13. Testing

Suite completa (~105 tests, todos offline):

```powershell
uv run pytest
uv run pytest -q    # salida compacta
```

| Archivo de test | Qué cubre |
|---|---|
| `test_rag_indexer.py` | `KnowledgeIndexer`: frontmatter, sanitización de metadatos, carga de documentos, `build_or_load`, `_drop_collection` |
| `test_rag_retriever.py` | `KnowledgeRetriever`: filtro por threshold, parámetro k, casos vacíos, boundary exacto |
| `test_rag_tools.py` | `retrieve_fvl_knowledge`: metadata tool, sin resultados, formato headers con/sin categoría, separador, parámetros de settings |
| `test_rag_agent.py` | `build_rag_agent`: retorno del agente, tool correcta, `InMemorySaver` presente, temperatura 0.1 |
| `test_rag_engine.py` | `get_rag_agent` singleton + `force_rebuild`; `stream_agent_response`: filtro de mensajes, `thread_id` en config, manejo de excepciones |
| `test_settings.py` | Config y variables de entorno |
| `test_schemas.py` | Modelos Pydantic |
| `test_web_crawler.py` | WebCrawler, selectors CSS, conversión HTML→MD |
| `test_pipeline.py` | `SemanticPipeline` end-to-end |
| `test_cli.py` | Comandos CLI y argumentos |
| `test_http_retry.py` | Retry exponencial (503, 429, timeout) |
| `test_deduplicator.py` | Deduplicación por URL canónica y SHA-256 |
| `test_youtube_rich.py` | `YouTubeRichExtractor` con mock de yt-dlp |
| `test_google_news.py` | Construcción de URLs RSS Google News |
| `test_cleaner_presets.py` | Presets WEB_FVL, NEWS, YOUTUBE |

---

## 14. Troubleshooting

**`program not found: semantic-layer-fvl`**
Ejecuta `uv sync` en la raíz del repo.

**La app RAG responde lento en la primera consulta**
Normal: la primera llamada inicializa el agente y carga ChromaDB. Las siguientes son instantáneas.

**`index_ready=False` o `chunks=0`**
Ejecuta `uv run semantic-layer-fvl build-index --force`. Verifica que `data/knowledge/` tenga archivos `.md` (ejecutar primero el pipeline ETL).

**`OPENAI_API_KEY` no encontrada en runtime**
La librería OpenAI lee `os.environ`, no el objeto `Settings`. La API key debe estar en `.env` y es leída por pydantic-settings. No funciona si se define solo como variable de entorno del sistema operativo sin `.env`.

**El agente responde sin recuperar documentos**
Aumentar `RAG_SCORE_THRESHOLD` (default 0.3) o bajar `RAG_TOP_K` para ser más selectivo. Revisar que el índice tenga chunks con `uv run semantic-layer-fvl build-index`.

**El Módulo 1 (Q&A/Resumen/FAQ) responde lento o es costoso**
Bajar `RESPONSE_MAX_TOKENS`, `SUMMARY_MAX_TOKENS` o `FAQ_MAX_TOKENS`. Ajustar `HISTORY_MAX_*` para reducir tokens del historial.

**`TypeError: 'function' object is not subscriptable` en tests**
El proyecto usa Python 3.12 obligatoriamente. Python 3.14 es incompatible con `langchain.agents` + pydantic. Ejecutar `uv python pin 3.12` y `uv sync`.

---

## 15. Seguridad y Buenas Prácticas

- No subir `.env`, `data/` ni `reports/` al repositorio (todos en `.gitignore`).
- No exponer API keys en capturas o logs.
- Mantener scraping solo sobre contenido público institucional.
- `InMemorySaver` almacena el historial en memoria del proceso — se pierde al reiniciar la app. Para persistencia entre reinicios, reemplazar por `SqliteSaver` o `PostgresSaver` de LangGraph.

---

## 16. Estado del Módulo

| Iteración | Estado | Contenido |
|---|---|---|
| Iteración 1 | ✅ Completa | Pipeline web (4 dominios) + dashboard NO-RAG (Q&A, Resumen, FAQ) + context stuffing con compactación de contexto |
| Iteración 2 | ✅ Completa | YouTubeRichExtractor, noticias curadas, deduplicación, retry HTTP, presets de ruido, streaming LCEL, CSS profesional |
| Módulo 2 — RAG | ✅ Completa | `KnowledgeIndexer`, `KnowledgeRetriever`, `@tool retrieve_fvl_knowledge`, agente ReACT con `InMemorySaver`, pestaña Agente RAG en Streamlit, suite de tests offline, comando CLI `build-index` |
