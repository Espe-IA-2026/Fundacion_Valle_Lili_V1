# Asistente Virtual FVL - Modulo 1

Pipeline de extraccion y estructuracion de conocimiento para la Fundacion Valle del Lili + dashboard Streamlit con tres funcionalidades de LLM orquestadas con LangChain.

Premisa del proyecto en esta fase: **NO es un RAG**. Las tres tareas responden usando contexto consolidado inyectado en el prompt de sistema.

---

## 1. Objetivo

Este repositorio tiene dos piezas integradas:

1. `semantic_layer_fvl`: capa semantica que extrae informacion publica y genera una base de conocimiento en Markdown.
2. `app`: motor y frontend que consumen esa base de conocimiento con estrategia de context stuffing (sin retrieval vectorial) y exponen tres funcionalidades de LLM.

Resultado esperado:

- Salida limpia en `data/knowledge/` por dominios institucionales.
- Dashboard con tres herramientas que responden usando solo contexto institucional consolidado:
  - **Q&A conversacional**: chatbot con historial de turnos.
  - **Resumen**: sintesis estructurada en Markdown de cualquier tema institucional.
  - **FAQ**: entre 5 y 8 preguntas frecuentes con respuestas fundamentadas en los documentos.

---

## 2. Arquitectura End-to-End

```text
valledellili.org + sitemaps + feeds
            |
            v
extractors (sitemap, crawler, feeds)
            |
            v
RawPage (Pydantic)
            |
            v
processors (cleaner + structurer)
            |
            v
ProcessedDocument (Pydantic)
            |
            v
writers (markdown + frontmatter)
            |
            v
data/knowledge/<dominio>/<slug>.md
            |
            v
app.engine -> contexto consolidado + compactacion
            |
            v
LangChain + OpenAI (NO-RAG)
   ┌────────┼────────────┐
   v        v            v
Q&A chain  Summary chain FAQ chain
            |
            v
Streamlit dashboard (3 pestañas)
```

Capas principales:

- `src/semantic_layer_fvl/extractors`: scraping y fuentes.
- `src/semantic_layer_fvl/processors`: limpieza y estructuracion.
- `src/semantic_layer_fvl/writers`: persistencia a Markdown.
- `src/semantic_layer_fvl/orchestrator/pipeline.py`: coordinacion del flujo.
- `src/app/engine.py`: motor del chatbot con contexto consolidado.
- `src/app/main.py`: frontend Streamlit.

---

## 3. Dominios Configurados

Definidos en `src/semantic_layer_fvl/domains.py`:

- `servicios`
- `especialistas`
- `sedes`
- `institucional`

Cada dominio define:

- sitemaps
- patrones include/exclude de URL
- selector principal de contenido
- metadatos extra por selector
- reglas de corte y limpieza de markdown

---

## 4. Flujo de Ejecucion

Comando principal por dominio:

```powershell
uv run semantic-layer-fvl crawl-domain servicios --write
```

Secuencia:

1. CLI parsea comando (`src/semantic_layer_fvl/cli.py`).
2. `SemanticPipeline.run_domain()` obtiene URLs del sitemap.
3. `WebCrawler.fetch_domain_page()` descarga HTML, limpia ruido y convierte a markdown.
4. Estructuracion semantica (`structurer.py`) y armado de documento.
5. Writer guarda `.md` y, opcionalmente, resumen de corrida.

---

## 5. Estrategia del Asistente (NO-RAG)

Las tres funcionalidades **no usan vectorstore ni retrieval semantico** en esta fase.

Flujo compartido:

1. Carga recursiva de `.md` desde `KNOWLEDGE_DIR`.
2. Consolidacion de todos los documentos en un solo contexto compactado.
3. Inyeccion de ese contexto en el prompt de sistema de cada cadena.

Las tres cadenas LangChain disponibles en `src/app/engine.py`:

| Funcion | Cadena | Descripcion |
|---|---|---|
| `build_chain()` | Q&A | Chat multi-turno con `MessagesPlaceholder`. Temperatura 0.1. |
| `build_summary_chain()` | Resumen | Genera sintesis estructurada en Markdown por tema. Temperatura 0.2. |
| `build_faq_chain()` | FAQ | Genera 5-8 preguntas frecuentes con respuestas. Temperatura 0.2. |

Funciones de invocacion:

- `get_response(chain, context, question, history)` — Q&A bloqueante (resultado completo).
- `stream_response(chain, context, question, history)` — Q&A en streaming; devuelve un generador de chunks que `st.write_stream()` consume token a token.
- `get_summary(chain, context, topic)` — Resumen de un tema.
- `get_faq(chain, context, topic)` — FAQ sobre un tema.

La carga de recursos usa `@st.cache_resource` para que el conocimiento y las tres cadenas se inicialicen una sola vez por sesion del servidor.

---

## 6. Optimizaciones de Costo de Inferencia (Implementadas)

Para reducir tokens sin romper la premisa NO-RAG:

1. **Scope correcto de conocimiento**
- `KNOWLEDGE_DIR=data/knowledge`
- Evita cargar todo `data/`.

2. **Compactacion deterministica de contexto**
- normaliza saltos de linea
- reemplaza encabezados/frases repetitivas por abreviaturas
- agrega compresion por lexico de lineas repetidas (`LEXICO_LINEAS`)

3. **Historial con presupuesto**
- limite por turnos
- limite por caracteres totales
- limite por mensaje

4. **Presupuestos de salida por tarea**
- `RESPONSE_MAX_TOKENS` para Q&A (default 500)
- `SUMMARY_MAX_TOKENS` para Resumen (default 900)
- `FAQ_MAX_TOKENS` para FAQ (default 1200)

5. **Trazabilidad de contexto**
- `data/debug_context_raw.txt` (consolidado original)
- `data/debug_context.txt` (consolidado compacto)

Variables de control (`.env`):

- `RESPONSE_MAX_TOKENS` — tokens maximos en respuesta Q&A (default 500)
- `SUMMARY_MAX_TOKENS` — tokens maximos en respuesta de Resumen (default 900)
- `FAQ_MAX_TOKENS` — tokens maximos en respuesta de FAQ (default 1200)
- `HISTORY_MAX_TURNS`
- `HISTORY_MAX_CHARS`
- `HISTORY_ITEM_MAX_CHARS`
- `LINE_LEXICON_ENABLED`
- `LINE_LEXICON_MIN_COUNT`
- `LINE_LEXICON_MIN_LEN`
- `LINE_LEXICON_MAX_ENTRIES`

---

## 7. Estructura del Proyecto

```text
.
├── Makefile
├── pyproject.toml
├── .env.example
├── data/
│   ├── knowledge/
│   ├── debug_context.txt
│   └── debug_context_raw.txt
├── reports/
│   └── runs/
├── src/
│   ├── semantic_layer_fvl/
│   │   ├── cli.py
│   │   ├── domains.py
│   │   ├── config/
│   │   ├── extractors/
│   │   ├── processors/
│   │   ├── schemas/
│   │   ├── writers/
│   │   └── orchestrator/
│   └── app/
│       ├── engine.py
│       └── main.py
└── tests/
```

---

## 8. Requisitos

- Python 3.11+
- `uv` instalado
- OpenAI API key para la app

Opcional:

- GNU make (en Windows puedes usar los comandos `uv run ...` directos)

---

## 9. Configuracion

### 9.1 Crear entorno local

```powershell
uv sync
```

### 9.2 Configurar variables

```powershell
Copy-Item .env.example .env
```

Editar `.env` y definir al menos:

- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `KNOWLEDGE_DIR=data/knowledge`

### 9.3 Verificar CLI

```powershell
uv run semantic-layer-fvl show-config
```

---

## 10. Comandos Operativos

### 10.1 Crawling por dominio

```powershell
uv run semantic-layer-fvl crawl-domain servicios --write
uv run semantic-layer-fvl crawl-domain especialistas --write
uv run semantic-layer-fvl crawl-domain sedes --write
uv run semantic-layer-fvl crawl-domain institucional --write
```

Con limite:

```powershell
uv run semantic-layer-fvl crawl-domain servicios --write --max-urls 50
```

### 10.2 Otros comandos CLI

```powershell
uv run semantic-layer-fvl crawl-once https://valledellili.org/quienes-somos --write
uv run semantic-layer-fvl crawl-seeds --limit 10 --write --save-summary
uv run semantic-layer-fvl crawl-discover --max-pages 50 --write --save-summary
uv run semantic-layer-fvl youtube-feed <feed_url> --write
uv run semantic-layer-fvl news-feed <feed_url> --write
```

### 10.3 Dashboard Streamlit

```powershell
uv run streamlit run src/app/main.py
```

La aplicacion abre en `http://localhost:8501` con layout wide y sidebar lateral.

**Sidebar**
- Branding de la FVL, estado de carga del knowledge base, guia de uso y modelo activo.

**Pestanas**

- **💬 Q&A — Preguntas y Respuestas**: respuestas en streaming token a token via `chain.stream()`. Incluye panel de bienvenida con 5 preguntas de ejemplo clicables y boton para limpiar historial.
- **📋 Resumen**: expander de temas sugeridos, formulario de tema libre, resultado con banner de identificacion y descarga en `.md`.
- **❓ FAQ**: misma estructura que Resumen; genera 5-8 preguntas con respuestas fundamentadas en documentos.

El CSS profesional aplica una paleta hospitalaria (azul `#002D72` / teal `#0077B5`) a tabs, botones, inputs y mensajes de chat.

### 10.4 Atajos Makefile

```powershell
make servicios
make especialistas
make sedes
make institucional
make app
```

---

## 11. Replicar en Otro Equipo

Esta seccion esta pensada para levantar el proyecto desde cero en una maquina nueva.

### Paso 1. Clonar el repositorio

```powershell
git clone <URL_DEL_REPO>
cd Fundacion_Valle_Lili_V1
```

### Paso 2. Instalar dependencias

```powershell
uv sync
```

### Paso 3. Crear y ajustar `.env`

```powershell
Copy-Item .env.example .env
```

Valores minimos recomendados:

```dotenv
OPENAI_API_KEY=<tu_api_key>
OPENAI_MODEL=gpt-4o-mini
KNOWLEDGE_DIR=data/knowledge
RESPONSE_MAX_TOKENS=500
SUMMARY_MAX_TOKENS=900
FAQ_MAX_TOKENS=1200
HISTORY_MAX_TURNS=6
HISTORY_MAX_CHARS=3500
HISTORY_ITEM_MAX_CHARS=700
LINE_LEXICON_ENABLED=true
LINE_LEXICON_MIN_COUNT=5
LINE_LEXICON_MIN_LEN=24
LINE_LEXICON_MAX_ENTRIES=350
```

### Paso 4. Verificar instalacion

```powershell
uv run semantic-layer-fvl show-config
uv run pytest -q
```

### Paso 5. Generar base de conocimiento

```powershell
uv run semantic-layer-fvl crawl-domain servicios --write
uv run semantic-layer-fvl crawl-domain especialistas --write
uv run semantic-layer-fvl crawl-domain sedes --write
uv run semantic-layer-fvl crawl-domain institucional --write
```

### Paso 6. Iniciar app

```powershell
uv run streamlit run src/app/main.py
```

### Paso 7. Validar contexto cargado

Al iniciar la app, revisar que se generen:

- `data/debug_context_raw.txt`
- `data/debug_context.txt`

Puedes medir compactacion:

```powershell
uv run python -c "import pathlib; raw=pathlib.Path('data/debug_context_raw.txt').stat().st_size; comp=pathlib.Path('data/debug_context.txt').stat().st_size; print(round(((raw-comp)/raw)*100,2))"
```

---

## 12. Testing

Ejecutar toda la suite:

```powershell
uv run pytest
```

La suite es offline y cubre, entre otros:

- settings/config
- schemas Pydantic
- crawler y reglas de limpieza
- pipeline
- CLI

---

## 13. Troubleshooting Rapido

1. `program not found: semantic-layer-fvl`
- Ejecuta `uv sync`.
- Usa `uv run semantic-layer-fvl ...` dentro de la raiz del repo.

2. La app responde lento o caro en tokens
- Baja `RESPONSE_MAX_TOKENS` (Q&A), `SUMMARY_MAX_TOKENS` (Resumen) o `FAQ_MAX_TOKENS` (FAQ).
- Ajusta `HISTORY_MAX_*` para reducir tokens del historial en Q&A.
- Mantiene `KNOWLEDGE_DIR=data/knowledge`.

3. Error por API key
- Verifica `OPENAI_API_KEY` en `.env`.
- Reinicia proceso de Streamlit despues de cambiar variables.

4. No aparecen documentos en salida
- Ejecuta `crawl-domain ... --write`.
- Verifica permisos de escritura en `data/knowledge`.

---

## 14. Seguridad y Buenas Practicas

- No subir `.env` al repositorio.
- No exponer llaves API en capturas o logs.
- Mantener scraping solo sobre contenido publico institucional.

---

## 15. Estado del Modulo

Estado actual: funcional para construccion de base semantica + dashboard NO-RAG con tres funcionalidades LLM (Q&A, Resumen, FAQ) y optimizaciones de costo de inferencia.

Siguiente paso natural (si el curso lo permite): evolucionar a recuperacion selectiva por documentos/chunks (RAG) — el modulo `TextChunker` en `processors/chunker.py` ya esta implementado y reservado para esa fase.
