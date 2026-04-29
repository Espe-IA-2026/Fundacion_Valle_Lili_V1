# Guía de Exposición — Chatbot Fundación Valle del Lili
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

> "Una vez que tenemos los documentos, necesitamos un motor inteligente que los use para responder preguntas. Aquí es donde entra LangChain como orquestador de la cadena de inferencia."

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

3. **`build_chain()`** — La cadena LangChain:
   ```
   ChatPromptTemplate | ChatOpenAI | StrOutputParser
   ```
   - El `ChatPromptTemplate` tiene tres partes:
     - **System**: contiene el `SYSTEM_TEMPLATE` con el contexto completo y las 7 instrucciones estrictas del asistente.
     - **MessagesPlaceholder("history_messages")**: inyecta el historial de conversación.
     - **Human**: recibe la pregunta actual del usuario.
   - El `ChatOpenAI` usa `gpt-4o-mini` con temperatura 0.1 (respuestas consistentes y poco creativas).
   - El `StrOutputParser` convierte la respuesta del modelo en una cadena simple.

4. **`get_response(chain, context, question, history)`:**
   - Invoca la cadena con el contexto, el historial procesado y la pregunta.
   - El historial se limita mediante `_history_to_messages()`: máximo 6 turnos, máximo 3500 caracteres acumulados, máximo 700 caracteres por mensaje.

### Qué mostrar / señalar
- El código de `build_chain()` en `engine.py` (líneas ~152-167).
- El `SYSTEM_TEMPLATE` con las instrucciones estrictas.
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
   - `load_resources()` llama a `load_knowledge_base()` y `build_chain()` una sola vez.
   - `@st.cache_resource` garantiza que aunque el usuario refresque la página, el conocimiento y la cadena no se recargan — esto es crítico por el costo computacional de leer cientos de archivos.

3. **Bucle de conversación:**
   - El historial se almacena en `st.session_state.messages` (lista de dicts `{role, content}`).
   - Al cargar la página, se renderizan todos los mensajes previos con `st.chat_message`.
   - Cuando el usuario escribe en `st.chat_input`, el mensaje se agrega al historial y se muestra inmediatamente.
   - Se llama a `get_response(chain, context, user_input, history_for_prompt)` dentro de un `st.spinner` para mostrar "Consultando documentos institucionales…" mientras el modelo responde.
   - La respuesta se agrega al historial y se muestra con `st.chat_message("assistant")`.

**Comunicación interfaz → motor:**

```
Usuario escribe pregunta
        ↓
main.py: get_response(chain, context, pregunta, historial)
        ↓
engine.py: chain.invoke({context, history_messages, question})
        ↓
LangChain: construye el prompt completo y lo envía a OpenAI API
        ↓
OpenAI devuelve la respuesta
        ↓
StrOutputParser convierte a string
        ↓
main.py: muestra respuesta en st.chat_message("assistant")
```

### Qué mostrar / señalar
- La interfaz en vivo en el navegador con una pregunta de ejemplo.
- El spinner de "Consultando documentos institucionales…".
- El código de `load_resources()` mostrando el decorador `@st.cache_resource`.

---

## Segmento 4 — Integración de la base semántica en el prompt del agente (4 minutos)
**Expositor: Persona 4**

### Guion de presentación

> "El punto más crítico del sistema es cómo el conocimiento extraído de la web —los archivos Markdown— termina convirtiéndose en la memoria del agente de LangChain. Aquí explicamos esa integración."

### Puntos clave a cubrir

**El flujo completo de integración:**

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
SYSTEM_TEMPLATE.format(context=context) → prompt del sistema
         ↓
ChatPromptTemplate.from_messages([system, history, human])
         ↓
ChatOpenAI (gpt-4o-mini) recibe el prompt completo
         ↓
Respuesta grounded en los documentos institucionales
```

**Por qué el frontmatter se elimina antes de inyectar:**
- El frontmatter YAML contiene metadatos de extracción (fecha, URL, estado) que son irrelevantes para el modelo y consumen tokens innecesarios.
- El contenido útil para el modelo es el cuerpo Markdown: encabezados, párrafos, listas de especialistas, horarios, etc.

**Cómo el SYSTEM_TEMPLATE amarra el conocimiento al agente:**
```
INSTRUCCIONES ESTRICTAS:
1. Responde ÚNICAMENTE con información contenida en la BASE DE CONOCIMIENTO.
2. Si la respuesta no está en el contexto, responde exactamente: 
   "No encontré esa información..."
3. NUNCA inventes datos como fechas, nombres, precios o teléfonos.
```
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
- El `SYSTEM_TEMPLATE` completo en `engine.py` (líneas ~18-44).
- Una demostración en vivo: pregunta al chatbot algo que esté en los documentos y algo que NO esté, para mostrar el comportamiento grounded vs. la respuesta de "no encontré".

---

## Cierre conjunto (30 segundos)

> **Cualquiera de los 4 expositores puede cerrar:**
>
> "En resumen: construimos un pipeline de extracción que convierte el sitio web de la FVL en una base de conocimiento Markdown, un motor LangChain que inyecta esa base directamente en el prompt del agente, y una interfaz Streamlit que conecta al usuario con ese motor de forma transparente. El resultado es un chatbot que solo responde con información institucional verificada, sin alucinaciones."

---

## Preguntas frecuentes anticipadas

| Pregunta posible | Respuesta sugerida |
|---|---|
| ¿Por qué no usaron RAG? | El corpus actual cabe en el contexto del modelo. RAG está preparado en `TextChunker` para la v2.0. |
| ¿Qué pasa si la información del sitio cambia? | Se re-ejecuta el pipeline de scraping para regenerar los `.md`. El chatbot siempre lee desde disco al iniciar. |
| ¿Qué modelo usan? | `gpt-4o-mini` por defecto, configurable con la variable de entorno `OPENAI_MODEL`. |
| ¿Cómo evitan alucinaciones? | Las instrucciones estrictas del `SYSTEM_TEMPLATE` prohíben al modelo inventar datos. Temperatura 0.1 para reducir creatividad. |
| ¿Cuántos documentos tiene la base? | Depende del crawl. El dominio `servicios` genera ~200 documentos, `especialistas` ~300. |
| ¿Cómo se actualiza la base? | Ejecutando `semantic-layer-fvl crawl-domain <dominio> --write` y reiniciando el servidor Streamlit. |
