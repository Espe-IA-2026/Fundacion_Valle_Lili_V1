# Sistema de Preguntas y Respuestas Basado en Conocimiento Semántico para la Fundación Valle del Lili

**Jhonatan, Nicolas, Mateo, Jorge**  
*Universidad, Programa de Ingeniería*  
*Cali, Colombia*  
*Abril 2026*

---

## Resumen

Este artículo presenta el diseño e implementación de un sistema de Preguntas y Respuestas (Q&A) para la Fundación Valle del Lili, una de las instituciones médicas de mayor referencia en Colombia y Latinoamérica. El sistema extrae automáticamente información pública del sitio web institucional mediante técnicas de web scraping, la procesa y estructura en una base de conocimiento semántico de 97 documentos organizados en 9 categorías. Utilizando el modelo de lenguaje GPT-4o-mini (OpenAI) orquestado con LangChain, el sistema responde preguntas de usuarios basándose exclusivamente en el conocimiento extraído, logrando una precisión del 95% en una batería de 20 preguntas y eliminando completamente las alucinaciones mediante técnicas avanzadas de Prompt Engineering. La interfaz de usuario se implementó con Streamlit, ofreciendo tres funcionalidades principales: Q&A interactivo, generación de resumen ejecutivo y generación de FAQ.

**Palabras clave:** Procesamiento de Lenguaje Natural, Prompt Engineering, Web Scraping, Base de Conocimiento, LLM, Q&A, Chatbot, Fundación Valle del Lili.

---

## I. Introducción

### A. Descripción del Problema

La Fundación Valle del Lili (FVL) es una institución médica de alta complejidad ubicada en Cali, Valle del Cauca, con más de 43 años de experiencia, más de 800 especialistas y más de 8000 colaboradores. La institución cuenta con un sitio web extenso que alberga información sobre servicios, especialidades, procesos de atención, normatividad, investigación y contacto. Sin embargo, la navegación por este volumen de información puede resultar compleja para pacientes, familiares y visitantes que buscan respuestas rápidas y precisas.

La necesidad de un canal de comunicación automatizado y preciso que centralice la información institucional y la haga accesible a través de un lenguaje natural motiva el desarrollo de este proyecto. Un asistente virtual capaz de responder preguntas frecuentes reduciría la carga del personal de atención al cliente y mejoraría la experiencia del usuario.

### B. Planteamiento de la Solución

Se propone la creación de un sistema Q&A como núcleo para un futuro chatbot, basado en tres pilares:

1. **Extracción y estructuración automatizada** de información pública mediante web scraping ético.
2. **Base de conocimiento semántico** organizada por categorías institucionales.
3. **Motor de respuesta** basado en un LLM (Gemma 4) con Prompt Engineering avanzado que genera respuestas precisas y libres de alucinaciones.

El enfoque adoptado en este módulo es **contextual sin RAG**: todo el conocimiento extraído se consolida en el prompt del sistema como contexto directo, permitiendo que el LLM acceda a toda la información relevante en cada consulta.

---

## II. Trabajo Relacionado

Los sistemas Q&A sobre documentos institucionales han evolucionado significativamente con la aparición de los modelos de lenguaje grandes (LLMs). Las aproximaciones tradicionales basaban la búsqueda en coincidencia de palabras clave (TF-IDF, BM25), mientras que los enfoques modernos utilizan embeddings semánticos y modelos generativos [1].

La técnica de Retrieval-Augmented Generation (RAG) [2] combina la búsqueda vectorial con la generación de texto, permitiendo que los LLMs respondan basándose en documentos externos. Sin embargo, para bases de conocimiento de tamaño moderado (~450KB), la inyección directa del contexto en el prompt ofrece simplicidad y eliminación de la complejidad de retrieval.

El Prompt Engineering [3] ha demostrado ser una herramienta poderosa para controlar el comportamiento de los LLMs, incluyendo técnicas como zero-shot, few-shot, chain-of-thought y instrucciones de formato que mejoran significativamente la calidad de las respuestas.

---

## III. Preparación de los Datos

### A. Web Scraping

El proceso de extracción de datos se implementó mediante un pipeline automatizado en Python con las siguientes herramientas:

| Herramienta | Propósito |
|-------------|-----------|
| `httpx` | Cliente HTTP asíncrono con rate limiting |
| `BeautifulSoup4` | Parser HTML para extracción de texto |
| `feedparser` | Lectura de feeds RSS/Atom |
| `yt-dlp` | Metadatos de canal YouTube |

#### Principios éticos del scraping:

- **Solo información pública**: Se extrae únicamente contenido accesible sin autenticación.
- **Respeto a `robots.txt`**: Verificación automática antes de cada request.
- **Rate limiting**: Máximo 0.5 requests/segundo para no sobrecargar el servidor.
- **Atribución**: Cada documento incluye URL de origen y fecha de extracción.

#### Estrategia de crawling:

Se implementó un crawler BFS (Breadth-First Search) que parte de URLs semilla predefinidas del sitio `valledellili.org` y sigue enlaces internos descubiertos:

```
URLs semilla → BFS Crawler → RawPage (HTML + metadata) → Procesadores → Markdown
```

Se definieron 9 URLs semilla correspondientes a las secciones principales del sitio, resultando en el descubrimiento y extracción de 97 páginas únicas.

### B. Limpieza y Preprocesamiento

El texto extraído del HTML se procesó mediante el módulo `TextCleaner`:

1. **Eliminación de etiquetas HTML**: Se remueven todas las etiquetas y atributos.
2. **Normalización de espacios**: Se colapsan múltiples espacios en blanco y saltos de línea.
3. **Eliminación de contenido no informativo**: Menús de navegación, footers, scripts, estilos CSS.
4. **Preservación de estructura**: Se mantienen encabezados, listas y párrafos semánticos.

### C. Segmentación (Chunking)

Se implementó un `TextChunker` con las siguientes características:

| Parámetro | Valor | Justificación |
|-----------|-------|---------------|
| `max_chunk_size` | 500 caracteres | Balance entre granularidad y completitud |
| `chunk_overlap` | 50 caracteres | Preserva continuidad entre chunks adyacentes |
| `min_chunk_size` | 100 caracteres | Evita fragmentos demasiado pequeños |

El algoritmo respeta límites de párrafo, dividiendo por oraciones cuando un párrafo excede el tamaño máximo. Esto mantiene la coherencia semántica de cada fragmento.

### D. Estructuración Semántica

Cada documento procesado se guarda como Markdown con YAML frontmatter:

```yaml
---
title: "Cardiología"
document_id: "02_servicios-cardiologia"
category: "02_servicios"
slug: "cardiologia"
source_url: "https://valledellili.org/cardiologia/"
extracted_at: "2026-04-12T20:35:02Z"
---
# Cardiología
[contenido limpio del documento]
```

#### Taxonomía de categorías:

| Categoría | Documentos | Contenido |
|-----------|-----------|-----------|
| `01_organizacion` | 17 | Historia, misión, certificaciones, RSE |
| `02_servicios` | 69 | Especialidades, laboratorios, procesos |
| `03_talento_humano` | 1 | Directorio médico |
| `04_sedes_ubicaciones` | 1 | Sedes y ubicaciones |
| `05_contacto` | 1 | Canales de contacto |
| `06_normatividad` | 2 | Marco legal, datos personales |
| `07_investigacion` | 1 | Comité de ética |
| `08_educacion` | 2 | Educación y docencia |
| `09_noticias` | 3 | Noticias institucionales |
| **Total** | **97** | |

---

## IV. Modelado

### A. Selección del Modelo de Lenguaje

Se evaluaron modelos locales y de API:

| Modelo | Tipo | Ventana ctx | Calidad español | Seleccionado |
|--------|------|-------------|-----------------|-------------|
| Llama 3.2 (1B) vía Ollama | Local | 128k | Pobre | ❌ |
| Llama 3.2 (3B) vía Ollama | Local | 128k | Aceptable | ❌ |
| **GPT-4o-mini (OpenAI)** | API | 128k | **Excelente** | ✅ |

Se seleccionó **GPT-4o-mini** (OpenAI, 2024) por su superior calidad de respuesta en español, amplia ventana de contexto (128k tokens) y su bajo costo operativo por token. Su arquitectura optimizada permite respuestas en streaming con latencia reducida, lo cual mejora la experiencia del usuario en la interfaz Streamlit.

#### Configuración del modelo:

```python
ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,      # Determinístico para Q&A factual
    streaming=True,     # Streaming de tokens para UX fluida
)
```

### B. Modelo de Embeddings (para Módulo 2)

Para la búsqueda semántica (implementada pero no utilizada en el flujo Q&A de este módulo), se seleccionó:

- **Modelo:** `paraphrase-multilingual-MiniLM-L12-v2` (sentence-transformers)
- **Tamaño:** ~120 MB
- **Dimensionalidad:** 384 dimensiones
- **Justificación:** Modelo multilingüe optimizado para semántica en español.

### C. Base de Datos Vectorial (para Módulo 2)

- **Motor:** ChromaDB v1.0
- **Persistencia:** Directorio local `./vectorstore`
- **Será utilizado en Módulo 2** para implementar RAG completo.

### D. Diseño del Prompt

El diseño del prompt fue un proceso iterativo documentado en detalle (ver `docs/prompt_experiments.md`). Se desarrollaron tres versiones para cada uno de los tres prompts:

#### Técnicas de Prompt Engineering implementadas:

1. **Role prompting**: Definición clara del rol ("asistente virtual oficial de la FVL").
2. **Instrucciones negativas**: Reglas explícitas de lo que NO debe hacer el modelo.
3. **Few-shot examples**: Dos ejemplos incluidos (respuesta positiva + rechazo).
4. **Chain-of-thought implícito**: Proceso secuencial Lee → Busca → Responde.
5. **Formato estructurado**: Reglas de extensión, viñetas e indicadores de fuente.
6. **Respuesta de rechazo estándar**: Frase predefinida con datos de contacto para preguntas fuera del scope.

#### Framework de orquestación:

Se utiliza **LangChain v0.3** con LCEL (LangChain Expression Language) para construir las chains:

```python
chain = PromptTemplate | ChatOpenAI | StrOutputParser
```

Tres chains independientes:
- **Q&A Chain**: Responde preguntas individuales del usuario.
- **Summary Chain**: Genera un resumen ejecutivo de la institución.
- **FAQ Chain**: Genera 20 preguntas frecuentes con distribución temática.

---

## V. Implementación

### A. Arquitectura del Sistema

```
┌─────────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Web Scraping      │────▶│  Procesamiento   │────▶│  Knowledge Base │
│  (httpx + BS4)      │     │  (clean + chunk) │     │  (97 Markdown)  │
└─────────────────────┘     └──────────────────┘     └────────┬────────┘
                                                              │
                             ┌────────────────────────────────▼────────┐
                             │         Streamlit Dashboard             │
                             │  ┌──────┐  ┌─────────┐  ┌──────┐      │
                             │  │ Q&A  │  │ Resumen │  │ FAQ  │      │
                             │  └──┬───┘  └────┬────┘  └──┬───┘      │
                             └─────┼───────────┼─────────┼────────────┘
                                   │           │         │
                             ┌─────▼───────────▼─────────▼────────────┐
                             │    LangChain LCEL Chains                │
                             │  PromptTemplate → GPT-4o-mini → Parser │
                             └────────────────────────────────────────┘
```

### B. Stack Tecnológico

| Capa | Herramientas |
|------|-------------|
| Extracción | httpx, BeautifulSoup4, feedparser, yt-dlp |
| Procesamiento | Pydantic v2, PyYAML, TextCleaner, TextChunker |
| LLM | GPT-4o-mini (OpenAI), LangChain v0.3, LCEL |
| Búsqueda semántica | ChromaDB, sentence-transformers |
| Interfaz | Streamlit 1.56 |
| API | FastAPI, uvicorn |
| Dev/Test | uv, pytest, ruff |

### C. Interfaz de Usuario

El dashboard Streamlit presenta tres funcionalidades:

1. **Tab Q&A**: Campo de texto para preguntas con streaming de respuesta, historial de sesión, y preguntas de ejemplo.
2. **Tab Resumen**: Generación de resumen ejecutivo con 7 secciones temáticas y descarga en Markdown.
3. **Tab FAQ**: Generación de 20 FAQ con distribución temática obligatoria y descarga.

Características de UI:
- Diseño premium con colores institucionales FVL (azul naval a azul cielo)
- Tarjetas de métricas con animaciones de hover
- Sidebar oscuro con estadísticas y directorio de categorías
- Indicador de modelo y tiempo de respuesta
- CSS personalizado con Google Fonts (Inter)

---

## VI. Resultados

### A. Batería de Pruebas

Se evaluó el sistema con una batería de 20 preguntas distribuidas en 7 categorías temáticas (ver `docs/qa_test_results.md`):

| Resultado | Cantidad | Porcentaje |
|-----------|----------|------------|
| ✅ Precisa | 16 | 80% |
| ⚠️ Parcial | 1 | 5% |
| ❌ Incorrecta | 0 | 0% |
| 🚫 Rechazo correcto | 2 | 10% |
| **Total exitoso** | **19/20** | **95%** |

### B. Análisis Comparativo de Modelos

| Métrica | Llama 3.2 (1B) | GPT-4o-mini |
|---------|---------------|-------------|
| Tasa de éxito | 55% | 95% |
| Alucinaciones | 6/20 | 0/20 |
| Rechazos correctos | 0/2 | 2/2 |
| Calidad media (1-5) | 2.5 | 4.7 |

### C. Impacto del Prompt Engineering

| Versión del prompt | Técnica | Calidad media |
|-------------------|---------|---------------|
| v1.0 | Zero-shot básico | 2.0/5.0 |
| v2.0 | Instrucciones + anti-alucinación | 3.8/5.0 |
| v3.0 | Few-shot + CoT + negativas | 4.8/5.0 |

La evolución de prompts demostró que **la calidad del prompt tiene mayor impacto que el tamaño del modelo**: un prompt v3.0 en un modelo de 3B puede superar a un prompt v1.0 en un modelo de 12B.

### D. Ejemplos de Respuestas

**Pregunta:** ¿Cuál es la misión de la Fundación Valle del Lili?

**Respuesta del sistema:** La misión de la Fundación Valle del Lili es satisfacer las necesidades de salud de alta complejidad de sus pacientes, integrando la práctica clínica, la educación y la investigación, en una permanente búsqueda de la excelencia para beneficio de la comunidad.

---

**Pregunta:** ¿Cuánto cuesta una consulta de cardiología?

**Respuesta del sistema:** No dispongo de esa información en mi base de conocimiento actual. Te recomiendo contactar directamente a la Fundación Valle del Lili al (+57) 602 331 9090 o al correo siau@fvl.org.co.

---

### E. Limitaciones Identificadas

1. **Truncamiento de contexto**: La base de conocimiento (~450KB) excede la capacidad práctica del prompt (~90KB), requiriendo truncamiento del 20%.
2. **Latencia**: Tiempos de respuesta de 5-15 segundos en ejecución local.
3. **Sin memoria conversacional**: Cada pregunta es independiente.
4. **Cobertura parcial**: Algunos documentos del sitio no fueron extraídos por restricciones de `robots.txt` o contenido dinámico JavaScript.
5. **Dependencia de Ollama**: Requiere instalación local del servidor de modelos.

---

## VII. Conclusiones y Trabajo Futuro

### A. Conclusiones

Se logró construir un sistema Q&A funcional para la Fundación Valle del Lili que:

- Extrae y estructura automáticamente 97 documentos de la web institucional.
- Responde preguntas con 95% de precisión y cero alucinaciones.
- Opera completamente de forma local sin dependencia de APIs externas.
- Demuestra la efectividad del Prompt Engineering iterativo para controlar LLMs.

El enfoque de inyección directa de contexto (sin RAG) demostró ser viable para bases de conocimiento medianas, simplificando la arquitectura del sistema.

### B. Trabajo Futuro (Módulo 2)

1. **Implementación de RAG**: Utilizar ChromaDB y embeddings para recuperación dinámica de contexto, eliminando la limitación de truncamiento.
2. **Memoria conversacional**: Agregar historial de conversación para preguntas de seguimiento.
3. **Fine-tuning**: Optimizar el modelo con datos específicos de la FVL.
4. **Evaluación cuantitativa**: Implementar métricas automáticas (BLEU, ROUGE, BERTScore).
5. **Despliegue en producción**: Contenerización con Docker y despliegue en nube.

---

## Referencias

[1] T. Brown et al., "Language Models are Few-Shot Learners," in *Proceedings of NeurIPS*, 2020.

[2] P. Lewis et al., "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks," in *Proceedings of NeurIPS*, 2020.

[3] J. Wei et al., "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models," in *Proceedings of NeurIPS*, 2022.

[4] H. Chase, "LangChain: Building applications with LLMs through composability," GitHub, 2023. [Online]. Available: https://github.com/langchain-ai/langchain

[5] Fundación Valle del Lili, "Sitio Web Oficial," 2026. [Online]. Available: https://valledellili.org

[6] Google DeepMind, "Gemma: Open Models Based on Gemini Research and Technology," 2024. [Online]. Available: https://ai.google.dev/gemma

[7] Ollama, "Run Large Language Models Locally," 2024. [Online]. Available: https://ollama.com
