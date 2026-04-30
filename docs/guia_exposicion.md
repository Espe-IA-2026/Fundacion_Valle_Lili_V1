# Guía de Exposición — Asistente Virtual Fundación Valle del Lili
**Duración total:** 15 minutos · **Equipo:** 4 personas

---

## Distribución de tiempos y roles

| Segmento | Tema | Expositor | Tiempo |
|---|---|---|---|
| 1 | Cómo se construyó la capa semántica | Persona 1 | 4 min |
| 2 | Cómo se construyó el motor con LangChain | Persona 2 | 4 min |
| 3 | Cómo se creó la interfaz y cómo se comunica con el motor | Persona 3 | 3 min |
| 4 | Cómo se integra la base semántica en el prompt del agente orquestado | Persona 4 | 4 min |

> **Consejo:** Cada persona hace una transición verbal corta antes de ceder la palabra al siguiente (5 segundos).

---

## Segmento 1 — La capa semántica (4 minutos)
**Expositor: Persona 1**

### Guion de presentación

> "El proyecto parte de un problema concreto: la Fundación Valle del Lili tiene información dispersa en decenas de páginas web. Para que el chatbot pueda responder con precisión, necesitamos convertir ese contenido en documentos estructurados y normalizados. A eso lo llamamos **capa semántica**."

### Puntos clave a cubrir

**¿Qué es la capa semántica?**
- Es el conjunto de archivos Markdown generados a partir del sitio web de la FVL.
- Cada archivo representa un recurso (servicio, especialista, sede, noticia) con un frontmatter YAML de metadatos y un cuerpo Markdown de contenido limpio.
- La capa está organizada en categorías temáticas: `01_organizacion`, `02_servicios`, `03_talento_humano`, etc.

**Cómo se construyó — el pipeline de extracción:**

1. **Extractores** (`src/semantic_layer_fvl/extractors/`)
   - `WebCrawler`: descarga páginas usando selectores CSS específicos por dominio (`DomainConfig`) y las convierte a Markdown con la librería `markdownify`.
   - `YouTubeFeedExtractor` y `NewsFeedExtractor`: parsean feeds Atom/RSS para obtener noticias y videos institucionales.
   - `RobotsPolicy`: respeta el `robots.txt` del sitio antes de hacer cualquier petición.
   - `SitemapExtractor`: obtiene la lista de URLs directamente del `sitemap.xml` del dominio.

2. **Procesadores** (`src/semantic_layer_fvl/processors/`)
   - `TextCleaner`: elimina duplicados, líneas de navegación (menú, footer) y normaliza espacios.
   - `SemanticStructurer`: infiere la categoría del documento por reglas de ruta y palabras clave, genera el slug, extrae el resumen y estructura el Markdown final.

3. **Escritor** (`src/semantic_layer_fvl/writers/`)
   - `MarkdownWriter`: genera el archivo `.md` con frontmatter YAML completo (título, categoría, slug, URL de origen, fecha de extracción, estado de publicación).

4. **Orquestador** (`src/semantic_layer_fvl/orchestrator/`)
   - `SemanticPipeline`: conecta todos los pasos y soporta distintos modos: semillas, descubrimiento BFS, dominio por sitemap o feeds. Genera un `PipelineRunSummary` con los resultados.

**Resultado concreto:**
> "Al ejecutar `semantic-layer-fvl crawl-domain servicios --write`, el pipeline descarga, limpia y escribe automáticamente cientos de archivos Markdown listos para ser consumidos por el chatbot."

### Qué mostrar / señalar
- Estructura de carpetas `data/knowledge/` con las subcarpetas por categoría.
- Un archivo `.md` de ejemplo con su frontmatter y cuerpo.
- El comando CLI de ejemplo.

---

## Segmento 2 — El motor con LangChain (4 minutos)
**Expositor: Persona 2**

### Guion de presentación

> "Una vez que tenemos los documentos, necesitamos un motor inteligente que los use para responder preguntas, generar resúmenes y producir preguntas frecuentes. Aquí es donde entra LangChain como orquestador de las tres cadenas de inferencia."

### Puntos clave a cubrir

**Arquitectura NO-RAG (context stuffing):**
- A diferencia de los sistemas RAG (Retrieval-Augmented Generation) que usan bases vectoriales, este proyecto utiliza **context stuffing**: todos los documentos se concatenan en un único contexto y se inyectan directamente en el prompt del sistema.
- Ventaja: no hay latencia de búsqueda vectorial y el modelo siempre tiene todo el conocimiento disponible.
- Desafío: optimización del número de tokens para no superar el límite del modelo.

**Cómo se construyó el motor (`src/app/engine.py`):**

1. **`load_knowledge_base(knowledge_dir)`**
   - Lee recursivamente todos los `.md` de la carpeta de conocimiento.
   - Elimina el frontmatter YAML de cada archivo.
   - Separa cada documento con el marcador `====== DOCUMENTO: {slug} ======`.
   - Aplica `_compact_context()` para reducir tokens.

2. **Compactación del contexto (`_compact_context`):**
   - Normaliza saltos de línea.
   - Reemplaza texto repetido por abreviaturas: `"Fundación Valle del Lili"` → `FVL`, `"## Especialistas que pueden atenderte"` → `## ESP`.
   - Activa la compresión por léxico de líneas (`_compress_repeated_lines`) para tokens adicionales: líneas que aparecen ≥5 veces y tienen ≥24 caracteres se reemplazan por tokens `L001`, `L002`, etc.

3. **Tres cadenas LangChain independientes** — misma estructura, distinto propósito:
   ```
   ChatPromptTemplate | ChatOpenAI | StrOutputParser
   ```

   | Función | Template | Historial | Temperatura | Tokens máx. |
   |---|---|---|---|---|
   | `build_chain()` | `SYSTEM_TEMPLATE` | Sí (`MessagesPlaceholder`) | 0.1 | 500 |
   | `build_summary_chain()` | `SUMMARY_SYSTEM_TEMPLATE` | No (single-turn) | 0.2 | 900 |
   | `build_faq_chain()` | `FAQ_SYSTEM_TEMPLATE` | No (single-turn) | 0.2 | 1 200 |

   - Q&A usa temperatura 0.1 (máxima consistencia) e historial multi-turno.
   - Resumen y FAQ usan temperatura 0.2 (algo de fluidez) y son single-turn: cada invocación es independiente.

4. **Funciones de invocación:**
   - `get_response(chain, context, question, history)` — inyecta contexto + historial acotado + pregunta.
   - `get_summary(chain, context, topic)` — inyecta contexto + tema; devuelve Markdown estructurado.
   - `get_faq(chain, context, topic)` — inyecta contexto + tema; devuelve 5-8 pares pregunta/respuesta.
   - El historial de Q&A se limita con `_history_to_messages()`: máximo 6 turnos, 3 500 caracteres, 700 por mensaje.

### Qué mostrar / señalar
- Las tres funciones `build_*` en `engine.py` para notar la simetría de diseño.
- Los tres templates con sus instrucciones estrictas (grounding, fallback, formato).
- Los archivos de debug: `data/debug_context.txt` (compactado) vs `data/debug_context_raw.txt` (crudo) para mostrar el ahorro de tokens.

---

## Segmento 3 — La interfaz y su comunicación con el motor (3 minutos)
**Expositor: Persona 3**

### Guion de presentación

> "Con el motor listo, necesitábamos una interfaz que cualquier persona pudiera usar sin conocimientos técnicos. Elegimos Streamlit porque permite construir aplicaciones web interactivas en pocas líneas de Python."

### Puntos clave a cubrir

**Tecnología elegida: Streamlit**
- Framework de Python que convierte scripts en aplicaciones web con componentes de chat nativos.
- No requiere HTML, CSS ni JavaScript por parte del desarrollador.
- Ejecutar con: `streamlit run src/app/main.py`

**Cómo se construyó la interfaz (`src/app/main.py`):**

1. **Configuración de página** (`st.set_page_config`):
   - Título: "Asistente Virtual — Fundación Valle del Lili"
   - Ícono: 🏥
   - Layout centrado.

2. **Carga de recursos con caché** (`@st.cache_resource`):
   - `load_resources()` llama a `load_knowledge_base()` y construye las **tres cadenas** (`build_chain`, `build_summary_chain`, `build_faq_chain`) una sola vez.
   - Devuelve una tupla de cuatro elementos: `(qa_chain, summary_chain, faq_chain, context)`.
   - `@st.cache_resource` garantiza que aunque el usuario refresque la página, el conocimiento y las cadenas no se recargan.

3. **Tres pestañas, tres funciones de renderizado:**
   - `_render_qa_tab(qa_chain, context)` — chat multi-turno con `st.chat_input` y botón "Limpiar conversación".
   - `_render_summary_tab(summary_chain, context)` — formulario con `st.form`, resultado en `st.session_state["summary_result"]`, botón de descarga `.md`.
   - `_render_faq_tab(faq_chain, context)` — formulario con `st.form`, resultado en `st.session_state["faq_result"]`, botón de descarga `.md`.
   - Los resultados de Resumen y FAQ persisten en `st.session_state` para no perderse en reruns de Streamlit.

**Comunicación interfaz → motor (flujo unificado para las tres tareas):**

```
Usuario interactúa en una pestaña
        ↓
main.py: llama a get_response / get_summary / get_faq
        ↓
engine.py: chain.invoke({context, [historial/topic]})
        ↓
LangChain: construye el prompt y lo envía a OpenAI API
        ↓
OpenAI devuelve la respuesta
        ↓
StrOutputParser convierte a string
        ↓
main.py: muestra resultado (chat / markdown / descarga .md)
```

### Qué mostrar / señalar
- La interfaz en vivo con las tres pestañas visibles.
- Demostrar Q&A con una pregunta, luego Resumen con un tema (p.ej. "cardiología") y FAQ con otro.
- El código de `load_resources()` mostrando el decorador `@st.cache_resource` y la tupla de cuatro elementos.

---

## Segmento 4 — Integración de la base semántica en el prompt del agente (4 minutos)
**Expositor: Persona 4**

### Guion de presentación

> "El punto más crítico del sistema es cómo el conocimiento extraído de la web —los archivos Markdown— termina convirtiéndose en la memoria del agente de LangChain. Aquí explicamos esa integración."

### Puntos clave a cubrir

**El flujo completo de integración (compartido por las tres tareas):**

```
Archivos .md en data/knowledge/
         ↓
load_knowledge_base() lee y elimina frontmatter YAML
         ↓
Concatenación con marcadores DOC:{slug}
         ↓
_compact_context(): abreviaturas + compresión de líneas
         ↓
Contexto compacto → variable "context"
         ↓
         ┌────────────────────┬─────────────────────┐
         ▼                    ▼                     ▼
 SYSTEM_TEMPLATE        SUMMARY_SYSTEM_      FAQ_SYSTEM_
 (Q&A multi-turno)      TEMPLATE (Resumen)   TEMPLATE (FAQ)
         └────────────────────┴─────────────────────┘
                              ↓
            ChatOpenAI (gpt-4o-mini) recibe el prompt completo
                              ↓
              Respuesta grounded en los documentos institucionales
```

**Por qué el frontmatter se elimina antes de inyectar:**
- El frontmatter YAML contiene metadatos de extracción (fecha, URL, estado) que son irrelevantes para el modelo y consumen tokens innecesarios.
- El contenido útil para el modelo es el cuerpo Markdown: encabezados, párrafos, listas de especialistas, horarios, etc.

**Cómo los tres templates amarran el conocimiento al agente:**

Los tres comparten el mismo principio de grounding:
```
INSTRUCCIONES ESTRICTAS:
1. Responde/genera ÚNICAMENTE con información de la BASE DE CONOCIMIENTO.
2. Si el tema no está en el contexto, responde exactamente:
   "No encontré esa información..."
3. NUNCA inventes datos como fechas, nombres, precios o teléfonos.
```

Cada template añade además instrucciones de **formato específico por tarea**:
- Q&A: respuesta conversacional con referencia `DOC:<slug>`.
- Resumen: estructura Markdown con secciones (`## Descripción`, `## Servicios`, `## Fuentes consultadas`).
- FAQ: entre 5 y 8 pares `**¿Pregunta?** / Respuesta` numerados.

- Estas instrucciones hacen que el modelo actúe como un agente **grounded**: solo puede responder con lo que está en los documentos, no con su conocimiento preentrenado.

**El rol de los marcadores de documento:**
- Cada documento se separa con `====== DOCUMENTO: {slug} ======`.
- Durante la compactación se convierten a `DOC:{slug}` (menos tokens).
- Las instrucciones del sistema le dicen al modelo: "cuando cites información, indica el `DOC:<nombre>` de origen."
- Esto da trazabilidad: el usuario puede saber de qué documento proviene cada respuesta.

**Decisión de diseño: ¿por qué NO usar RAG (vectores)?**
- RAG requiere una base de datos vectorial (FAISS, Pinecone, Chroma), un modelo de embeddings y un paso de recuperación.
- Para el tamaño actual del corpus (~500 documentos), el contexto compactado cabe dentro de la ventana del modelo.
- La solución sin RAG es más simple, más predecible y eliminan los falsos negativos por recuperación incorrecta.
- El módulo `TextChunker` está implementado en `processors/chunker.py` y **reservado para la versión 2.0** cuando el corpus crezca y requiera RAG.

**Resultado observable:**
> "Si preguntas '¿Cuáles son los horarios de atención del servicio de cardiología?', el modelo busca en el contexto el documento con slug `cardiologia`, encuentra la sección de contacto y responde con los datos exactos del archivo, indicando `DOC:cardiologia` como fuente."

### Qué mostrar / señalar
- El archivo `data/debug_context.txt` para mostrar cómo queda el contexto comprimido.
- Los tres templates en `engine.py`: señalar la sección `INSTRUCCIONES ESTRICTAS` idéntica en los tres y la sección de formato diferente en cada uno.
- Una demostración en vivo: pregunta al chatbot algo que esté en los documentos y algo que NO esté (pestaña Q&A), luego solicita un resumen de "cardiología" (pestaña Resumen) y un FAQ de "urgencias" (pestaña FAQ), para mostrar los tres modos de salida y el comportamiento grounded en cada uno.

---

## Cierre conjunto (30 segundos)

> **Cualquiera de los 4 expositores puede cerrar:**
>
> "En resumen: construimos un pipeline de extracción que convierte el sitio web de la FVL en una base de conocimiento Markdown, un motor LangChain con tres cadenas independientes que inyectan esa base en el prompt de cada tarea, y un dashboard Streamlit con tres pestañas que expone Q&A conversacional, generación de resúmenes y generación de preguntas frecuentes. El resultado es un asistente que responde únicamente con información institucional verificada, sin alucinaciones, en tres formatos distintos según la necesidad del usuario."

---

## Preguntas frecuentes anticipadas

| Pregunta posible | Respuesta sugerida |
|---|---|
| ¿Por qué no usaron RAG? | El corpus actual cabe en el contexto del modelo. RAG está preparado en `TextChunker` para la v2.0. |
| ¿Qué pasa si la información del sitio cambia? | Se re-ejecuta el pipeline de scraping para regenerar los `.md`. El asistente siempre lee desde disco al iniciar. |
| ¿Qué modelo usan? | `gpt-4o-mini` por defecto, configurable con la variable de entorno `OPENAI_MODEL`. |
| ¿Cómo evitan alucinaciones? | Los tres templates tienen instrucciones estrictas que prohíben inventar datos. Q&A usa temperatura 0.1; Resumen y FAQ usan 0.2 para mayor fluidez sin creatividad excesiva. |
| ¿Cuántos documentos tiene la base? | Depende del crawl. El dominio `servicios` genera ~200 documentos, `especialistas` ~300. |
| ¿Cómo se actualiza la base? | Ejecutando `semantic-layer-fvl crawl-domain <dominio> --write` y reiniciando el servidor Streamlit. |
| ¿Por qué tres cadenas y no una? | Cada tarea tiene instrucciones de formato diferentes (chat, Markdown estructurado, pares FAQ), temperatura distinta y presupuesto de tokens propio. Separar las cadenas hace el código más claro y cada prompt más preciso. |
| ¿Se puede descargar la salida? | Sí. Las pestañas Resumen y FAQ incluyen un botón "Descargar (.md)" que guarda el resultado como archivo Markdown. |
