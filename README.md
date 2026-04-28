# Chatbot FVL — Módulo 1: Capa Semántica

Pipeline de extracción y estructuración de conocimiento para la **Fundación Valle del Lili**. Lee el sitio web institucional, lo convierte en documentos Markdown enriquecidos con metadatos y los organiza en una base de conocimiento lista para alimentar un chatbot corporativo.

---

## Tabla de Contenidos

1. [Qué hace el proyecto](#qué-hace-el-proyecto)
2. [Arquitectura y flujo de datos](#arquitectura-y-flujo-de-datos)
3. [Cómo se comunican los módulos](#cómo-se-comunican-los-módulos)
4. [Stack tecnológico](#stack-tecnológico)
5. [Estructura del proyecto](#estructura-del-proyecto)
6. [Dominios configurados](#dominios-configurados)
7. [Configuración](#configuración)
8. [Comandos CLI](#comandos-cli)
9. [Taxonomía del knowledge base](#taxonomía-del-knowledge-base)
10. [Testing](#testing)
11. [Principios éticos y legales](#principios-éticos-y-legales)
12. [Troubleshooting](#troubleshooting)
13. [Lo que viene: completar Módulo 1 y Módulo 2](#lo-que-viene-completar-módulo-1-y-módulo-2)

---

## Qué hace el proyecto

El proyecto construye una **base de conocimiento en Markdown** a partir del contenido público de `valledellili.org`. El flujo completo es:

```
Sitios web / Sitemaps XML / Feeds YouTube & RSS
                │
                ▼
      Extractores (sitemap, HTTP, feeds)
                │
                ▼
      Procesadores (limpieza + estructuración semántica)
                │
                ▼
      Writer (Markdown + YAML frontmatter)
                │
                ▼
      knowledge/<dominio>/<slug>.md
```

**Entregables actuales:**

- Base de conocimiento en Markdown estructurado, organizada por dominio y categoría
- Pipeline CLI reproducible con soporte para crawl por dominio, BFS, semillas y feeds
- Resúmenes JSON de cada corrida (`runs/`)
- Suite de pruebas offline completa

---

## Arquitectura y flujo de datos

El sistema está dividido en cuatro capas que se comunican mediante contratos Pydantic:

```
Extractores  ──►  RawPage  ──►  Procesadores  ──►  ProcessedDocument  ──►  Writers
                                                                              │
                                                                              ▼
                                                                    knowledge/<dominio>/<slug>.md
```

### 1. Extractores

Obtienen contenido crudo de distintas fuentes y lo envuelven en un `RawPage`:

| Módulo | Fuente | Notas |
|--------|--------|-------|
| `sitemap_extractor.py` | Sitemaps XML del sitio | Usa cabeceras de Chrome para evitar bloqueos 403 |
| `web_crawler.py` | Páginas HTML individuales | `fetch()` para crawl BFS; `fetch_domain_page()` para extracción por dominio con selector CSS específico |
| `http_client.py` | Capa HTTP base | `httpx` con rate limiting integrado (máx. 0.5 req/s por defecto) |
| `robots.py` | `robots.txt` | Verifica permisos antes de cada URL en el crawl BFS |
| `site_map.py` | Mapa de semillas | Lista de URLs base de alta prioridad para iniciar el crawl |
| `youtube.py` | Feeds Atom de YouTube | Extrae metadata de videos sin API key |
| `news.py` | Feeds RSS/Atom de noticias | Lee artículos de feeds institucionales o externos |

### 2. Procesadores

Transforman `RawPage` → `ProcessedDocument`:

| Módulo | Responsabilidad |
|--------|-----------------|
| `cleaner.py` | Normalización de texto: espacios, caracteres unicode, longitudes mínimas |
| `structurer.py` | Asigna categoría, genera `document_id` y `slug`, detecta título, extrae headings |
| `chunker.py` | División de documentos largos en fragmentos (reservado para Módulo 2) |

### 3. Writer

`markdown_writer.py` toma un `ProcessedDocument` y lo escribe como archivo `.md` con YAML frontmatter completo:

```yaml
---
domain: "servicios"
title: "Cardiología Intervencionista"
document_id: "abc12345"
category: "02_servicios"
slug: "cardiologia-intervencionista"
source_url: "https://valledellili.org/servicios/cardiologia-intervencionista/"
source_name: "valledellili.org"
status: "draft"
extraction_date: "2026-04-28"
extracted_at: "2026-04-28T14:32:00+00:00"
extractor_name: "web_domain"
tags: []
warnings: []
---

# Cardiología Intervencionista
...contenido en Markdown...
```

Los campos extra de metadatos por dominio (como `categoria`, `especialidad`, `direccion`) se incluyen automáticamente al final del frontmatter.

### 4. Orquestador

`pipeline.py` coordina todo el flujo. Instancia un extractor, un procesador y un writer, los encadena y registra cada resultado en un `PipelineRunSummary`. Expone los métodos `run_domain()`, `run_seed_urls()`, `run_with_discovery()`, `run_all()` y `save_summary()`.

---

## Cómo se comunican los módulos

Los módulos nunca se llaman directamente entre sí a través de su lógica interna: se comunican exclusivamente a través de **contratos Pydantic** definidos en `schemas/`.

```
schemas/documents.py
  ├── RawPage              ← producido por todos los extractores
  ├── ProcessedDocument    ← producido por los procesadores, consumido por el writer
  ├── SourceDocument       ← embebido en ProcessedDocument
  ├── ExtractionMetadata   ← embebido en RawPage y SourceDocument
  └── DocumentCategory     ← enum StrEnum con las 10 categorías posibles

schemas/runs.py
  ├── PipelineRunSummary   ← resultado de cada corrida del orquestador
  └── PipelineItemResult   ← resultado individual por URL/feed procesado
```

**Flujo concreto para `crawl-domain servicios`:**

```
cli.py
  └─► handle_crawl_domain()
        └─► SemanticPipeline.run_domain("servicios")
              ├─► fetch_domain_urls(base_url, config)        # sitemap_extractor
              │     └─► requests.get(sitemap_url)            # browser headers
              │         └─► filtra por url_include_patterns
              │         └─► [lista de URLs]
              │
              └─► para cada URL:
                    ├─► WebCrawler.fetch_domain_page(url, config)
                    │     ├─► requests.get(url, headers=_BROWSER_HEADERS)
                    │     ├─► BeautifulSoup → elimina nav/footer/scripts
                    │     ├─► busca config.container_selector ("div.content-post")
                    │     ├─► markdownify → HTML a Markdown ATX
                    │     ├─► extrae extra_metadata_selectors del dominio
                    │     └─► retorna RawPage (con .markdown y .extra_metadata)
                    │
                    ├─► SemanticStructurer.build_document(raw_page, domain_name="servicios")
                    │     ├─► usa DomainConfig.category como DocumentCategory
                    │     ├─► genera document_id (hash) y slug (slugify del título)
                    │     └─► retorna ProcessedDocument
                    │
                    └─► MarkdownWriter.write(processed, domain_folder="servicios")
                          ├─► construye YAML frontmatter
                          ├─► une frontmatter + content_markdown
                          └─► escribe en knowledge/servicios/<slug>.md
```

---

## Stack tecnológico

| Librería | Uso |
|----------|-----|
| `beautifulsoup4` | Parsing HTML, eliminación de ruido (nav, footer, scripts), extracción de metadatos por selector CSS |
| `markdownify` | Conversión de HTML a Markdown ATX con soporte para encabezados, listas y tablas |
| `httpx` | Cliente HTTP base con rate limiting integrado para el crawl BFS |
| `requests` | Peticiones con cabeceras de navegador Chrome para sitemaps y páginas de dominio (evita bloqueos 403) |
| `pydantic v2` | Contratos de datos entre capas; validación y serialización de todos los schemas |
| `pydantic-settings` | Carga de configuración desde variables de entorno y archivo `.env` |
| `python-dotenv` | Soporte de archivo `.env` |
| `uv` | Gestión de dependencias y entorno virtual |
| `pytest` | Suite de pruebas offline |
| `ruff` | Linter y formateador (E, F, I, UP) |

---

## Estructura del proyecto

```text
Fundacion_Valle_Lili_V1/
├── .env.example                         ← Variables de entorno de referencia
├── pyproject.toml                       ← Dependencias y configuración de build
├── src/
│   └── semantic_layer_fvl/
│       ├── cli.py                       ← Punto de entrada de todos los comandos
│       ├── domains.py                   ← DomainConfig + DOMAIN_CONFIGS (4 dominios)
│       ├── config/
│       │   ├── settings.py              ← Configuración centralizada (pydantic-settings)
│       │   └── logging.py              ← Setup de logging estructurado
│       ├── schemas/
│       │   ├── documents.py             ← RawPage, ProcessedDocument, DocumentCategory, …
│       │   └── runs.py                 ← PipelineRunSummary, PipelineItemResult
│       ├── extractors/
│       │   ├── http_client.py           ← HttpClient (httpx) + RateLimiter
│       │   ├── robots.py               ← Parser y verificador de robots.txt
│       │   ├── web_crawler.py          ← Crawl BFS y extracción por dominio (BeautifulSoup)
│       │   ├── site_map.py             ← URLs semilla predefinidas de alta prioridad
│       │   ├── sitemap_extractor.py    ← Lectura de sitemaps XML con filtros por dominio
│       │   ├── youtube.py              ← Extractor de feeds Atom de YouTube
│       │   └── news.py                 ← Extractor de feeds RSS/Atom de noticias
│       ├── processors/
│       │   ├── cleaner.py              ← Normalización y limpieza de texto
│       │   ├── structurer.py           ← Categorización, slugs, document_id, headings
│       │   └── chunker.py             ← División en fragmentos (reservado para Módulo 2)
│       ├── writers/
│       │   └── markdown_writer.py      ← Renderiza ProcessedDocument a .md con frontmatter
│       └── orchestrator/
│           └── pipeline.py             ← SemanticPipeline: coordina todo el flujo
├── knowledge/                          ← Documentos .md generados (output del pipeline)
├── runs/                               ← Resúmenes JSON de cada corrida
├── tests/                              ← Suite de pruebas offline
└── docs/                               ← Documentación técnica complementaria
```

---

## Dominios configurados

Cada dominio tiene configuración propia en `domains.py` (`DomainConfig`):

| Dominio | Sitemap | Selector CSS | Carpeta de salida | Categoría |
|---------|---------|--------------|-------------------|-----------|
| `servicios` | `servicios-sitemap.xml` | `div.content-post` | `knowledge/servicios/` | `02_servicios` |
| `especialistas` | `especialistas-sitemap.xml` | `div.content-post` | `knowledge/especialistas/` | `03_talento_humano` |
| `sedes` | `sedes-sitemap.xml` | `div.content-post` | `knowledge/sedes/` | `04_sedes_ubicaciones` |
| `institucional` | `page-sitemap.xml` | `div.content-post` | `knowledge/institucional/` | `01_organizacion` |

Cada dominio también declara:
- `url_include_patterns` — sólo se procesan URLs que contengan uno de estos segmentos
- `url_exclude_patterns` — se descartan URLs que coincidan con algún patrón
- `extra_metadata_selectors` — selectores CSS adicionales que se extraen y agregan al frontmatter
- `fallback_urls` — se usan si el sitemap responde con error o está vacío

---

## Configuración

### 1. Crear el archivo de entorno

```bash
cp .env.example .env
```

### 2. Instalar dependencias

```bash
uv sync
```

### 3. Verificar configuración

```bash
uv run python -m semantic_layer_fvl.cli show-config
```

### Variables de entorno

| Variable | Default | Descripción |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Nivel de logging (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `OUTPUT_DIR` | `./knowledge` | Directorio de salida para documentos Markdown |
| `RUNS_DIR` | `./runs` | Directorio para resúmenes JSON de corridas |
| `REQUESTS_PER_SECOND` | `0.5` | Rate limiting del crawl BFS (req/s) |
| `REQUEST_TIMEOUT` | `30` | Timeout de requests en segundos |
| `TARGET_BASE_URL` | `https://valledellili.org` | URL base del sitio objetivo |
| `RESPECT_ROBOTS_TXT` | `true` | Respetar directivas de `robots.txt` en crawl BFS |
| `YOUTUBE_SEARCH_LIMIT` | `50` | Límite de items por feed de YouTube |
| `NEWS_FEED_LIMIT` | `50` | Límite de artículos por feed de noticias |

> **Nota Windows:** el comando `uv run semantic-layer-fvl` puede fallar con "program not found".
> Usar siempre: `uv run python -m semantic_layer_fvl.cli <comando>`

---

## Comandos CLI

### Diagnóstico

```bash
# Mostrar la configuración cargada desde .env
uv run python -m semantic_layer_fvl.cli show-config

# Listar las URLs semilla predefinidas
uv run python -m semantic_layer_fvl.cli list-seeds
```

### Crawl por dominio (flujo principal)

```bash
# Crawl completo de un dominio usando su sitemap XML
uv run python -m semantic_layer_fvl.cli crawl-domain servicios --max-urls 300 --write --save-summary
uv run python -m semantic_layer_fvl.cli crawl-domain especialistas --max-urls 300 --write --save-summary
uv run python -m semantic_layer_fvl.cli crawl-domain sedes --max-urls 300 --write --save-summary
uv run python -m semantic_layer_fvl.cli crawl-domain institucional --max-urls 300 --write --save-summary

# Prueba en seco (sin escribir archivos)
uv run python -m semantic_layer_fvl.cli crawl-domain servicios --max-urls 5
```

### Crawl general

```bash
# Procesar una sola URL (debug/validación)
uv run python -m semantic_layer_fvl.cli crawl-once https://valledellili.org/nuestra-institucion

# Procesar las URLs semilla
uv run python -m semantic_layer_fvl.cli crawl-seeds --limit 10 --write --save-summary

# Descubrimiento BFS: sigue enlaces internos desde las semillas
uv run python -m semantic_layer_fvl.cli crawl-discover --max-pages 50 --write --save-summary
```

### Fuentes complementarias

```bash
# Feed Atom de YouTube
uv run python -m semantic_layer_fvl.cli youtube-feed https://www.youtube.com/feeds/videos.xml?channel_id=XXX --write

# Feed RSS o Atom de noticias
uv run python -m semantic_layer_fvl.cli news-feed https://example.com/feed.xml --write
```

### Corrida compuesta

```bash
uv run python -m semantic_layer_fvl.cli run-all \
  --seed-limit 20 \
  --youtube-feed https://www.youtube.com/feeds/videos.xml?channel_id=XXX \
  --news-feed https://example.com/feed.xml \
  --write \
  --save-summary
```

### Interpretación del resumen de salida

```
processed=10      ← total de items intentados
success=9         ← procesados correctamente
failure=1         ← fallaron

ok  source="web_domain" input="https://..." title="..." output_path="knowledge/servicios/..."
error source="web_domain" input="https://..." error="empty content after extraction"
```

---

## Taxonomía del knowledge base

Los documentos se organizan automáticamente en subcarpetas según la categoría del dominio:

| Carpeta | Dominio / fuente |
|---------|------------------|
| `knowledge/01_organizacion/` | Dominio `institucional` (historia, misión, visión) |
| `knowledge/02_servicios/` | Dominio `servicios` |
| `knowledge/03_talento_humano/` | Dominio `especialistas` |
| `knowledge/04_sedes_ubicaciones/` | Dominio `sedes` |
| `knowledge/09_noticias/` | Feeds RSS de noticias |
| `knowledge/10_multimedia/` | Feeds Atom de YouTube |

---

## Testing

```bash
uv run pytest
```

O directamente con el Python del entorno virtual en Windows:

```powershell
& .\.venv\Scripts\python.exe -m pytest
```

La suite cubre exclusivamente pruebas **offline** (sin red):

- Configuración y settings
- Contratos Pydantic (schemas)
- Rate limiting y cliente HTTP
- Reglas de `robots.txt`
- Mapa de semillas
- Crawler web base
- Limpieza, estructuración y escritura Markdown
- Extractores de YouTube y noticias
- Ejecución del pipeline y resúmenes de corrida
- Despacho del CLI

---

## Principios éticos y legales

| Principio | Implementación |
|-----------|----------------|
| Solo información pública | Extrae únicamente contenido accesible sin autenticación |
| Respetar `robots.txt` | Verificado antes de cada URL en el crawl BFS (`respect_robots_txt=true`) |
| Rate limiting | Máximo 0.5 req/s por defecto, configurable vía `.env` |
| No datos sensibles | Cero información de pacientes o datos protegidos |
| Atribución | `source_url`, `extraction_date` y `extracted_at` incluidos en cada documento |

---

## Troubleshooting

### El sitemap retorna 403

El extractor usa cabeceras de Chrome para mitigar bloqueos de WAF. Si el sitio bloquea a nivel de IP, el pipeline cae automáticamente a las `fallback_urls` configuradas para ese dominio y lo indica en el log con `WARNING`.

### Documentos con `empty content after extraction`

El selector `div.content-post` no encontró contenido. Posibles causas: la página es una landing con botones/secciones, la URL redirige a otra estructura, o el sitio renderiza el contenido con JavaScript. Revisar el HTML con `crawl-once` sin `--write` y ajustar el `container_selector` en `domains.py`.

### `PermissionError` al escribir archivos

Validar que `OUTPUT_DIR` y `RUNS_DIR` apunten a rutas con permisos de escritura. Probar sin `--write` para aislar la extracción de la escritura.

### Crawl BFS muy lento

El `REQUESTS_PER_SECOND=0.5` introduce 2 segundos entre requests. Para pruebas locales aumentar a `2.0` en `.env`. Para producción mantener el valor conservador.

---

## Lo que viene: completar Módulo 1 y Módulo 2

### Estado actual del Módulo 1

El pipeline de extracción está completo y funcional. Lo que falta para cerrar el módulo es:

| Tarea | Descripción |
|-------|-------------|
| Poblar el knowledge base | Ejecutar `crawl-domain` en los 4 dominios contra `valledellili.org` y validar la calidad de los `.md` generados |
| Validar cobertura | Revisar que las categorías `01_organizacion` a `04_sedes_ubicaciones` tengan documentos suficientes y representativos |
| Afinar selectores | Ajustar `container_selector` y `extra_metadata_selectors` en `domains.py` para cualquier subdominio con estructura HTML diferente |
| Feeds complementarios | Identificar y configurar los feeds RSS/YouTube del canal institucional para poblar `09_noticias` y `10_multimedia` |
| Revisar calidad del Markdown | Asegurar que el frontmatter y el cuerpo sean consistentes entre documentos del mismo dominio |

### Módulo 2: Chatbot corporativo (Context Stuffing, sin RAG)

El diseño de Módulo 2 parte de la base de conocimiento generada por este pipeline. La arquitectura elegida es **Context Stuffing**: los documentos relevantes se inyectan directamente en el contexto del LLM en cada consulta, sin necesidad de búsqueda vectorial.

| Componente | Descripción |
|-----------|-------------|
| Interfaz de usuario | Streamlit — chat web ligero, sin infraestructura adicional |
| Motor de lenguaje | API de OpenAI (o compatible) vía LangChain |
| Estrategia de contexto | Selección de documentos por dominio/categoría + inyección en el prompt del sistema |
| `chunker.py` | Se activará para dividir documentos largos antes de inyectarlos si el contexto del modelo es limitado |
| Carga del knowledge base | Lector de archivos `.md` desde `knowledge/`, con filtrado por frontmatter |

**Flujo esperado de Módulo 2:**

```
Pregunta del usuario
      │
      ▼
Selección de documentos relevantes del knowledge base
      │
      ▼
Construcción del prompt (sistema + documentos + pregunta)
      │
      ▼
LLM (OpenAI / LangChain)
      │
      ▼
Respuesta fundamentada en fuentes institucionales
```

---

*Desarrollado por: Jhonatan, Nicolás, Mateo y Jorge — Abril 2026*
