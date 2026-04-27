# Capa Semántica — Fundación Valle del Lili

Pipeline automatizado que extrae, estructura y almacena información pública de la **Fundación Valle del Lili** en una base de conocimiento Markdown enriquecido. Esta base de conocimiento está diseñada para alimentar un sistema agéntico y un chatbot especializado en servicios, especialidades y noticias de la institución.

---

## Tabla de Contenidos

1. [Qué hace el proyecto](#qué-hace-el-proyecto)
2. [Principios éticos y legales](#principios-éticos-y-legales)
3. [Arquitectura](#arquitectura)
4. [Stack tecnológico](#stack-tecnológico)
5. [Estructura del proyecto](#estructura-del-proyecto)
6. [Configuración](#configuración)
7. [Comandos CLI](#comandos-cli)
8. [API REST](#api-rest)
9. [Búsqueda semántica](#búsqueda-semántica)
10. [Taxonomía del knowledge base](#taxonomía-del-knowledge-base)
11. [Fuentes de datos](#fuentes-de-datos)
12. [Testing](#testing)
13. [Runbook operativo](#runbook-operativo)
14. [Troubleshooting](#troubleshooting)
15. [Decisiones de arquitectura (ADRs)](#decisiones-de-arquitectura-adrs)
16. [Métricas de éxito](#métricas-de-éxito)
17. [Riesgos y mitigaciones](#riesgos-y-mitigaciones)

---

## Qué hace el proyecto

El proyecto construye una **capa semántica** a partir de contenido público de la Fundación Valle del Lili. El flujo completo es:

```
Sitio web / YouTube / RSS
         │
         ▼
   Extractores (crawl BFS, feeds)
         │
         ▼
   Procesadores (limpieza + estructuración semántica)
         │
         ▼
   Writers (Markdown con YAML frontmatter + ChromaDB)
         │
         ▼
   knowledge/   ←  base de conocimiento lista para agentes
   vectorstore/ ←  índice vectorial para búsqueda semántica
```

**Entregables concretos:**

- Base de conocimiento en Markdown estructurado (97 documentos organizados en 9 categorías)
- Pipeline de extracción automatizado y reproducible
- Búsqueda semántica con embeddings multilingüe (ChromaDB + `paraphrase-multilingual-MiniLM-L12-v2`)
- Sistema Q&A con Gemma 4 (Ollama) + LangChain — tres funcionalidades: Q&A, Resumen Ejecutivo, FAQ
- Dashboard interactivo con Streamlit
- API REST con FastAPI para consultar el knowledge base desde otros sistemas
- Suite de pruebas offline completa
- Documentación extensiva de experimentación con prompts y batería de 20 preguntas

---

## Principios éticos y legales

El proyecto opera exclusivamente sobre información pública y cumple los siguientes principios:

| Principio | Implementación |
|-----------|----------------|
| Solo información pública | Extrae únicamente contenido accesible sin autenticación |
| Respetar `robots.txt` | Verifica y cumple directivas del sitio antes de cada crawl |
| Rate limiting | Máximo 0.5 requests/segundo (configurable) |
| No datos sensibles | Cero información de pacientes o datos protegidos |
| Atribución | Documenta fuente y fecha de extracción en cada documento |

**Datos que el pipeline evita activamente:**

- Información de pacientes
- Datos de contacto personal de empleados no publicados
- Documentos internos o confidenciales
- Contenido detrás de login o autenticación

---

## Arquitectura

El sistema sigue principios de **bajo acoplamiento y alta cohesión**, con capas que se comunican mediante contratos Pydantic:

```
extractores  →  RawPage  →  procesadores  →  ProcessedDocument  →  writers
```

- **Extractores** producen `RawPage` a partir de web, YouTube o feeds RSS/Atom
- **Procesadores** limpian el texto y estructuran la información semánticamente
- **Writers** persisten `ProcessedDocument` como Markdown o en ChromaDB
- **Orquestador** coordina las corridas, registra resúmenes y expone el CLI
- **API REST** expone búsqueda y estadísticas del knowledge base sobre HTTP

### Principios de diseño

- **Bajo acoplamiento:** cada módulo es independiente y se comunica vía contratos Pydantic
- **Alta cohesión:** cada módulo tiene una sola responsabilidad
- **Contratos explícitos:** schemas Pydantic definen la estructura entre capas
- **Configuración externa:** variables de entorno para URLs, modelos y directorios

---

## Stack tecnológico

### Extracción

| Herramienta | Propósito |
|-------------|-----------|
| `httpx` | Cliente HTTP async con rate limiting |
| `BeautifulSoup4` | Parser HTML para extracción estructurada |
| `feedparser` | Lectura de feeds RSS y Atom |
| `yt-dlp` | Metadata de YouTube sin API key |

### Procesamiento y estructuración

| Herramienta | Propósito |
|-------------|-----------|
| `Pydantic v2` | Contratos de datos y validación de schemas |
| `pyyaml` | Manejo de metadatos YAML en frontmatter Markdown |

### Búsqueda semántica

| Herramienta | Propósito |
|-------------|-----------|
| `ChromaDB` | Base de datos vectorial persistente |
| `sentence-transformers` | Modelo de embeddings multilingüe |
| `paraphrase-multilingual-MiniLM-L12-v2` | Modelo concreto (~120 MB, descarga automática) |

### API y CLI

| Herramienta | Propósito |
|-------------|-----------|
| `FastAPI` | API REST con documentación interactiva automática |
| `uvicorn` | Servidor ASGI para producción local |

### Dev y testing

| Herramienta | Propósito |
|-------------|-----------|
| `uv` | Gestión de dependencias y entornos virtuales |
| `pytest` | Suite de pruebas offline |
| `ruff` | Linter y formateador |

---

## Estructura del proyecto

```text
plan_capa_semantica/
├── .env.example                    ← Variables de entorno de referencia
├── pyproject.toml                  ← Configuración UV y dependencias
├── src/
│   └── semantic_layer_fvl/
│       ├── api/                    ← API REST (FastAPI)
│       │   ├── app.py
│       │   └── routes.py
│       ├── cli.py                  ← Punto de entrada de todos los comandos
│       ├── config/
│       │   ├── settings.py         ← Configuración centralizada (pydantic-settings)
│       │   └── logging.py          ← Logging estructurado
│       ├── schemas/
│       │   ├── documents.py        ← RawPage, ProcessedDocument, Chunk
│       │   └── runs.py             ← RunSummary
│       ├── extractors/
│       │   ├── http_client.py      ← Cliente HTTP con rate limiting
│       │   ├── robots.py           ← Parser y verificador de robots.txt
│       │   ├── web_crawler.py      ← Crawler BFS con respeto a robots.txt
│       │   ├── site_map.py         ← Mapa de URLs semilla
│       │   ├── youtube.py          ← Extractor de feeds YouTube
│       │   └── news.py             ← Extractor de feeds RSS/Atom
│       ├── processors/
│       │   ├── cleaner.py          ← Limpieza y normalización de texto
│       │   ├── structurer.py       ← Clasificación y estructuración semántica
│       │   └── chunker.py          ← División inteligente de documentos largos
│       ├── writers/
│       │   ├── base.py             ← Interfaz base de escritores
│       │   ├── markdown_writer.py  ← Escribe Markdown con YAML frontmatter
│       │   └── vectorstore_writer.py ← Indexa documentos en ChromaDB
│       ├── vectorstore/
│       │   ├── embeddings.py       ← Carga y gestión del modelo de embeddings
│       │   └── store.py            ← Operaciones sobre ChromaDB
│       └── orchestrator/
│           └── pipeline.py         ← Orquestación de corridas y resúmenes
├── knowledge/                      ← Documentos Markdown generados (output)
├── vectorstore/                    ← Base de datos vectorial persistente (output)
├── tests/                          ← Suite de pruebas
└── docs/                           ← Documentación técnica
```

---

## Configuración

### 1. Crear el archivo de variables de entorno

```bash
cp .env.example .env
```

### 2. Instalar dependencias

```bash
uv sync
```

### 3. Validar configuración

```bash
uv run semantic-layer-fvl show-config
```

### Variables de entorno disponibles

| Variable | Default | Descripción |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Nivel de logging (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `OUTPUT_DIR` | `./knowledge` | Directorio de salida para documentos Markdown |
| `RUNS_DIR` | `./runs` | Directorio para guardar resúmenes JSON de corridas |
| `REQUESTS_PER_SECOND` | `0.5` | Rate limiting para crawl (req/seg) |
| `REQUEST_TIMEOUT` | `30` | Timeout de requests en segundos |
| `TARGET_BASE_URL` | `https://valledellili.org` | URL base del sitio objetivo |
| `RESPECT_ROBOTS_TXT` | `true` | Activar/desactivar respeto a robots.txt |
| `CHROMA_PERSIST_DIR` | `./vectorstore` | Directorio de persistencia de ChromaDB |
| `EMBEDDING_MODEL` | `paraphrase-multilingual-MiniLM-L12-v2` | Modelo de embeddings |
| `SEARCH_RESULTS_LIMIT` | `5` | Límite por defecto de resultados de búsqueda |
| `YOUTUBE_SEARCH_LIMIT` | `50` | Límite de videos a extraer por feed YouTube |
| `NEWS_FEED_LIMIT` | `100` | Límite de artículos a extraer por feed de noticias |

---

## Comandos CLI

Todos los comandos se ejecutan con `uv run semantic-layer-fvl <comando>`.

### Diagnóstico

```bash
# Ver configuración actual cargada desde .env
uv run semantic-layer-fvl show-config

# Listar URLs semilla configuradas
uv run semantic-layer-fvl list-seeds
```

### Crawling web

```bash
# Procesar una sola URL (útil para depurar extracción y clasificación)
uv run semantic-layer-fvl crawl-once https://valledellili.org/nuestra-institucion

# Procesar las URLs semilla configuradas
uv run semantic-layer-fvl crawl-seeds --limit 5 --write --save-summary

# Descubrimiento BFS: sigue enlaces internos a partir de las semillas
uv run semantic-layer-fvl crawl-discover --max-pages 100 --write --save-summary
```

### Fuentes complementarias

```bash
# Extraer feed de YouTube (canal o búsqueda)
uv run semantic-layer-fvl youtube-feed https://www.youtube.com/feeds/videos.xml?channel_id=XXX

# Extraer feed RSS o Atom de noticias
uv run semantic-layer-fvl news-feed https://example.com/feed.xml
```

### Corrida compuesta (todas las fuentes)

```bash
uv run semantic-layer-fvl run-all \
  --seed-limit 5 \
  --youtube-feed https://www.youtube.com/feeds/videos.xml?channel_id=XXX \
  --news-feed https://example.com/feed.xml \
  --save-summary
```

### Búsqueda semántica

```bash
# Indexar todos los documentos del knowledge base
uv run semantic-layer-fvl index-knowledge

# Buscar por significado (no por palabras exactas)
uv run semantic-layer-fvl search "cardiología"
uv run semantic-layer-fvl search "horarios de atención" --limit 10
```

### API REST

```bash
# Levantar el servidor en el puerto 8000
uv run semantic-layer-fvl serve --port 8000
```

---

## API REST

Al ejecutar `serve`, la API queda disponible con documentación interactiva en `http://localhost:8000/docs`.

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/search?q=...&limit=5` | `GET` | Búsqueda semántica sobre el knowledge base |
| `/api/stats` | `GET` | Estadísticas del knowledge base (documentos, chunks, categorías) |
| `/api/index` | `POST` | Re-indexar todos los documentos del directorio `knowledge/` |

---

## Búsqueda semántica

El sistema usa **embeddings multilingüe** para buscar por significado, no por coincidencia de palabras exactas. Esto permite encontrar documentos relevantes aunque la consulta use vocabulario diferente al del documento.

**Modelo:** `paraphrase-multilingual-MiniLM-L12-v2` (~120 MB, se descarga automáticamente la primera vez).

**Flujo de indexación:**

1. Lee todos los archivos `.md` del directorio `knowledge/`
2. Aplica **chunking inteligente** para dividir documentos largos en fragmentos con solapamiento
3. Genera embeddings de cada chunk con el modelo de sentence-transformers
4. Persiste los vectores en ChromaDB (directorio `vectorstore/`)

**Flujo de búsqueda:**

1. Genera el embedding de la consulta
2. Busca los chunks más cercanos en el espacio vectorial
3. Retorna resultados ordenados por distancia coseno (menor = más relevante)

---

## Taxonomía del knowledge base

Los documentos Markdown generados se organizan automáticamente en categorías:

| Carpeta | Contenido | Prioridad |
|---------|-----------|-----------|
| `01_organizacion/` | Historia, misión, visión, certificaciones | Alta |
| `02_servicios/` | Especialidades médicas, programas | Alta |
| `03_talento_humano/` | Directivos, especialistas | Alta |
| `04_sedes_ubicaciones/` | Sede principal, centros médicos | Alta |
| `05_contacto/` | Canales de atención, horarios | Alta |
| `06_normatividad/` | Derechos de pacientes, políticas | Media |
| `07_investigacion/` | Centro de investigaciones | Media |
| `08_educacion/` | Programas de formación | Media |
| `09_noticias/` | Noticias institucionales | Media |
| `10_multimedia/` | YouTube, redes sociales | Media |

Cada documento incluye YAML frontmatter con metadatos:

```yaml
---
title: "Nombre del documento"
category: "02_servicios"
source: "https://valledellili.org/servicios"
extracted_at: "2026-04-18T10:00:00"
---
```

---

## Fuentes de datos

### Sitio web principal (`valledellili.org`)

| URL | Contenido | Prioridad |
|-----|-----------|-----------|
| `/` | Página principal, overview | Alta |
| `/quienes-somos` | Historia, misión, visión | Alta |
| `/servicios` | Lista de servicios médicos | Alta |
| `/especialidades` | Especialidades médicas | Alta |
| `/directorio-medico` | Información de especialistas | Alta |
| `/sedes` | Ubicaciones y contacto | Alta |
| `/normatividad` | Políticas, derechos pacientes | Media |
| `/investigacion` | Centro de investigaciones | Media |
| `/noticias` | Noticias institucionales | Media |

### Fuentes complementarias

- **YouTube:** Feed público del canal institucional de la Fundación Valle del Lili
- **Noticias:** Feeds RSS de El País (Cali), El Tiempo, Google News, Portafolio

---

## Testing

### Ejecutar la suite

```bash
uv run pytest
```

O con el ejecutable del entorno virtual directamente:

```powershell
& .\.venv\Scripts\python.exe -m pytest
```

### Cobertura actual

La suite cubre:

- Configuración y settings
- Contratos Pydantic (schemas)
- Rate limiting y cliente HTTP
- Reglas de `robots.txt`
- Mapeo de semillas
- Crawler web base
- Limpieza, estructuración y escritura Markdown
- Extractores de YouTube y noticias
- Ejecución del pipeline y resúmenes de corrida
- Despacho básico del CLI

### Criterios de testing

- Las pruebas deben ser **offline** — sin dependencias de red en tiempo de test
- Las integraciones externas se simulan con `httpx.MockTransport` o stubs
- Los tests evitan dependencias de directorios temporales del sistema

### Próximas mejoras recomendadas

- Agregar pruebas de integración con ejemplos reales de HTML y feeds guardados como fixtures
- Validar el formato del frontmatter generado contra un parser YAML

---

## Documentación del Módulo 1

| Documento | Descripción |
|-----------|-------------|
| [`docs/prompt_experiments.md`](docs/prompt_experiments.md) | Documentación completa de la experimentación iterativa con prompts (3 versiones × 3 prompts) |
| [`docs/qa_test_results.md`](docs/qa_test_results.md) | Batería de 20 preguntas con resultados, análisis de calidad y comparación de modelos |
| [`docs/informe_ieee.md`](docs/informe_ieee.md) | Informe técnico en formato IEEE con todas las secciones requeridas |

### Dashboard Streamlit (Módulo 1 — App Q&A)

```bash
# Instalar dependencias del app
uv sync --group app

# Ejecutar el dashboard
uv run streamlit run app/main.py
```

**Modelo:** Gemma 4 (Google, 2026) vía Ollama — 32k tokens de contexto, temperature 0.3  
**Framework:** LangChain v0.3 con LCEL Chains  
**Funcionalidades:**
- 💬 Preguntas y Respuestas con streaming y historial de sesión
- 📋 Resumen Ejecutivo de la institución (7 secciones temáticas)
- ❓ Generación de 20 FAQ con distribución temática obligatoria

---

## Runbook operativo

### Preparación inicial

1. Crear `.env` a partir de `.env.example`
2. Instalar dependencias: `uv sync`
3. Validar configuración: `uv run semantic-layer-fvl show-config`

### Flujo típico de extracción

```bash
# 1. Probar con una sola URL para validar extracción
uv run semantic-layer-fvl crawl-once https://valledellili.org/quienes-somos

# 2. Extraer URLs semilla
uv run semantic-layer-fvl crawl-seeds --limit 5 --write --save-summary

# 3. Descubrimiento BFS para mayor cobertura
uv run semantic-layer-fvl crawl-discover --max-pages 50 --write --save-summary

# 4. Indexar el knowledge base para búsqueda semántica
uv run semantic-layer-fvl index-knowledge

# 5. Verificar con una búsqueda de prueba
uv run semantic-layer-fvl search "cardiología" --limit 5
```

### Artefactos de salida

- `knowledge/`: documentos Markdown organizados por categoría
- `runs/`: resúmenes JSON de las corridas cuando se usa `--save-summary`
- `vectorstore/`: base de datos vectorial persistente de ChromaDB

### Lectura del resumen de corrida

Los comandos por lote imprimen un resumen con:

- `processed`: cantidad total de items intentados
- `success`: cantidad de items procesados correctamente
- `failure`: cantidad de items que fallaron

Cuando hay errores, cada item fallido incluye el `source`, el `input` y el mensaje de error.

---

## Troubleshooting

### `uv sync` falla por permisos de caché

**Síntoma:**
```text
Failed to initialize cache at C:\Users\USER\AppData\Local\uv\cache
```

**Acciones:**
- Ejecutar `uv sync` con permisos suficientes en el entorno local
- Revisar políticas de acceso al caché de `uv`

---

### `pytest` falla al crear temporales de Windows

**Síntoma:**
```text
PermissionError: ... AppData\Local\Temp\pytest-of-USER
```

**Estado:** la suite del repo ya evita depender del directorio temporal por defecto. Si vuelve a aparecer, revisar si algún test nuevo usa temporales del sistema.

---

### Escritura de archivos bloqueada desde Python

**Síntoma:**
```text
PermissionError: [Errno 13] Permission denied
```

**Acciones:**
- Validar que `OUTPUT_DIR` y `RUNS_DIR` apunten a rutas con permisos de escritura
- Probar primero sin `--write` para aislar extracción de persistencia

---

### `robots.txt` responde `403` u otro `4xx`

El crawler trata los `4xx` (distinto de `429`) como "no disponible" y continúa. Si responde `429` o `5xx`, el crawler adopta un comportamiento restrictivo y bloquea la extracción.

**Si el crawl aún falla:**
- Revisar si la página objetivo también devuelve `403`
- Revisar el `User-Agent` configurado
- Validar si el sitio usa WAF o protecciones anti-bot

---

### Un feed no produce documentos

**Checklist:**
- Confirmar que el feed sea RSS o Atom válido
- Revisar que tenga `title` y `link` por item
- Verificar los límites `YOUTUBE_SEARCH_LIMIT` o `NEWS_FEED_LIMIT` en `.env`

---

## Decisiones de arquitectura (ADRs)

### ADR-001: Pipeline modular y contratos explícitos

**Estado:** Aprobado

**Contexto:** El proyecto necesita combinar varias fuentes de información y transformarlas a un formato Markdown consistente sin acoplar cada extractor a la salida final.

**Decisión:** Se adopta una arquitectura modular con capas separadas: extractores → procesadores → writers → orquestador. Los contratos entre capas se modelan con Pydantic.

**Consecuencias:**
- ✅ Facilita pruebas offline
- ✅ Permite agregar nuevas fuentes sin reescribir el pipeline
- ✅ Mantiene separación clara de responsabilidades
- ⚠️ Más clases y modelos que en un script lineal
- ⚠️ Algunas transformaciones requieren mapeos intermedios adicionales

---

### ADR-002: Fuentes públicas primero y respeto por `robots.txt`

**Estado:** Aprobado

**Contexto:** La capa semántica se alimenta de información institucional y debe respetar restricciones éticas y operativas del sitio objetivo.

**Decisión:** Se priorizan fuentes públicas y accesibles sin autenticación. Para extracción web: se consulta `robots.txt`, se aplica rate limiting y se evita acceso a datos sensibles. Para fuentes complementarias: se prefieren feeds públicos antes que integraciones con claves o scraping ad hoc.

**Consecuencias:**
- ✅ Menor riesgo legal y operativo
- ✅ Mejor trazabilidad de origen
- ✅ Pruebas más simples y repetibles
- ⚠️ Algunas fuentes pueden ofrecer menos detalle que una integración propietaria
- ⚠️ El proyecto depende de la estabilidad de los feeds y el contenido público

---

## Métricas de éxito

| Métrica | Objetivo | Cómo medir |
|---------|----------|------------|
| Cobertura de contenido | >80% secciones del sitio | Checklist de URLs |
| Calidad del Markdown | Formato consistente | Validación automática |
| Rate limiting | 0 errores 429 | Logs del extractor |
| Tiempo de extracción | <30 min sitio completo | Métricas del pipeline |
| Tests passing | 100% | `pytest` en CI |
| Documentación | README + ADRs completos | Revisión manual |

---

## Riesgos y mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|------------|
| El sitio bloquea scraping | Media | Alto | Respetar `robots.txt`, rate limiting |
| Estructura HTML cambia | Alta | Medio | Selectores genéricos, logging detallado |
| Contenido dinámico JS | Media | Medio | Parseo HTML directo con fallbacks |
| Datos incompletos | Media | Medio | Validación con schemas Pydantic |
| Dependencias rotas | Baja | Alto | Lockfile `uv.lock`, versiones pinneadas |

---
Realizado por: Jhonatan, Nicolas, Mateo y Jorge
*Versión: 1.0 — Abril 2026*
