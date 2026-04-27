# Informe — Módulo 1 (Fundación Valle del Lili)

## 1. Descripción del problema
Necesidad de un canal de comunicación automatizado y preciso para la Fundación Valle del Lili, capaz de responder preguntas frecuentes de primer contacto usando información pública y verificable.

## 2. Planteamiento de la solución
Creación de un sistema Q&A que responde basándose únicamente en un contexto consolidado (texto limpio extraído de fuentes públicas).  
**Nota:** En este módulo se evita RAG con base vectorial como mecanismo principal de recuperación; el contexto completo se consolida como “memoria” en el prompt del sistema.

## 3. Preparación de los datos
### 3.1 Scraping
- Fuentes: ver `docs/fuentes.md`
- Herramientas: (detallar requests/bs4/httpx/otros según corresponda)
- Consideraciones éticas: robots, rate limit, solo público, sin datos sensibles

### 3.2 Limpieza
- Eliminación de HTML/boilerplate
- Normalización
- Deduplicación

### 3.3 Segmentación (chunking)
- Estrategia de chunking (tamaño, solapamiento)
- Metadatos por chunk (`source_url`, `categoria`, `chunk_id`)

## 4. Modelado
### 4.1 Modelo (Módulo 2)
Indicar el LLM objetivo para el módulo 2 y la justificación (open-source vía Ollama o API privada).

### 4.2 Orquestación
Framework: LangChain o LlamaIndex (detallar cuál se usó y por qué).

### 4.3 Prompt engineering
- Prompt de sistema: reglas anti-alucinación, formato, tono
- Manejo explícito de “no encontrado en el contexto”

## 5. Resultados
### 5.1 Pruebas (20 preguntas)
Adjuntar tabla/resultados en `tests/qa_results.csv` (o equivalente).

### 5.2 Análisis de calidad
- Precisión
- Coherencia
- Cobertura

### 5.3 Limitaciones
- Dependencia de fuentes públicas
- Cambios del sitio / contenido dinámico
- Context window (recorte del contexto)

## Integrantes
- Nicolas
- Jhonatan
- Mateo
- Jorge

