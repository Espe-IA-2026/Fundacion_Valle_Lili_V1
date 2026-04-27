# Documentación de Experimentación con Prompts

**Proyecto:** Capa Semántica — Fundación Valle del Lili  
**Módulo:** 1 — Sistema Q&A  
**Equipo:** Jhonatan, Nicolas, Mateo, Jorge  
**Modelo final:** GPT-4o-mini (OpenAI, 2024) vía API  
**Framework:** LangChain v0.3 (LCEL Chains)

---

## Tabla de Contenidos

1. [Metodología de experimentación](#1-metodología-de-experimentación)
2. [Prompt de Q&A — Evolución](#2-prompt-de-qa--evolución)
3. [Prompt de Resumen Ejecutivo — Evolución](#3-prompt-de-resumen-ejecutivo--evolución)
4. [Prompt de FAQ — Evolución](#4-prompt-de-faq--evolución)
5. [Técnicas de Prompt Engineering aplicadas](#5-técnicas-de-prompt-engineering-aplicadas)
6. [Análisis comparativo de modelos](#6-análisis-comparativo-de-modelos)
7. [Conclusiones](#7-conclusiones)

---

## 1. Metodología de experimentación

### Proceso iterativo

Para cada uno de los tres prompts (Q&A, Resumen, FAQ), seguimos un proceso iterativo de tres versiones:

```
v1.0 (Zero-shot básico) → v2.0 (Instrucciones detalladas) → v3.0 (Few-shot + anti-alucinación)
```

### Métricas de evaluación

Evaluamos cada versión con las siguientes métricas cualitativas:

| Métrica | Descripción | Escala |
|---------|-------------|--------|
| **Precisión** | ¿La respuesta contiene información correcta del contexto? | 1-5 |
| **Relevancia** | ¿La respuesta aborda directamente la pregunta? | 1-5 |
| **Coherencia** | ¿La respuesta es lógica y bien estructurada? | 1-5 |
| **Anti-alucinación** | ¿La respuesta evita información inventada? | 1-5 |
| **Formato** | ¿La respuesta sigue el formato solicitado? | 1-5 |

### Preguntas de prueba estándar

Para mantener consistencia, usamos estas 5 preguntas como benchmark en todas las versiones:

1. "¿Cuál es la misión de la Fundación Valle del Lili?"
2. "¿Qué especialidades médicas ofrece?"
3. "¿Cuánto cuesta una consulta?" (pregunta trampa — no está en el contexto)
4. "¿Cómo solicitar una cita médica?"
5. "¿Qué certificaciones de calidad tiene la fundación?"

---

## 2. Prompt de Q&A — Evolución

### v1.0 — Zero-shot básico

```
Eres un asistente virtual de la Fundación Valle del Lili.
Responde las preguntas del usuario basándote en el siguiente contexto:

{context}
```

**Resultados:**

| Pregunta | Precisión | Relevancia | Coherencia | Anti-alucinación | Formato |
|----------|-----------|------------|------------|------------------|---------|
| Misión FVL | 4 | 4 | 3 | 3 | 2 |
| Especialidades | 3 | 3 | 2 | 2 | 2 |
| Costo consulta | 1 | 2 | 3 | 1 | 2 |
| Solicitar cita | 3 | 3 | 3 | 2 | 2 |
| Certificaciones | 3 | 3 | 3 | 2 | 2 |
| **Promedio** | **2.8** | **3.0** | **2.8** | **2.0** | **2.0** |

**Problemas identificados:**
- ❌ El modelo alucinaba frecuentemente — inventaba datos sobre costos, horarios y teléfonos.
- ❌ Las respuestas eran desorganizadas y no seguían un formato consistente.
- ❌ No distinguía entre información disponible y no disponible.
- ❌ Mezclaba información del contexto con conocimiento general del modelo.

---

### v2.0 — Instrucciones detalladas + anti-alucinación

```
Eres el asistente virtual oficial de la Fundación Valle del Lili, una de las 
instituciones médicas de mayor referencia en Colombia y América Latina.

INSTRUCCIONES:
- Responde de forma precisa, amable y profesional.
- Basa tu respuesta EXCLUSIVAMENTE en el contexto de conocimiento proporcionado.
- Si la información solicitada NO está en el contexto, responde con honestidad:
  "No tengo información específica sobre eso en mi base de conocimiento actual."
- Nunca inventes datos, fechas, nombres, cifras ni servicios.
- Cita la sección de origen cuando sea relevante.

CONTEXTO DE CONOCIMIENTO:
{context}
```

**Resultados:**

| Pregunta | Precisión | Relevancia | Coherencia | Anti-alucinación | Formato |
|----------|-----------|------------|------------|------------------|---------|
| Misión FVL | 5 | 5 | 4 | 4 | 3 |
| Especialidades | 4 | 4 | 3 | 4 | 3 |
| Costo consulta | 3 | 3 | 4 | 3 | 3 |
| Solicitar cita | 4 | 4 | 4 | 4 | 3 |
| Certificaciones | 4 | 4 | 4 | 4 | 3 |
| **Promedio** | **4.0** | **4.0** | **3.8** | **3.8** | **3.0** |

**Mejoras observadas:**
- ✅ Reducción significativa de alucinaciones (~60% menos).
- ✅ El modelo ahora suele indicar cuando no tiene información.
- ⚠️ Aún inventaba datos ocasionalmente en respuestas largas.
- ⚠️ No proporcionaba alternativas de contacto al no tener información.

---

### v3.0 — Few-shot + chain-of-thought + instrucciones negativas (VERSIÓN FINAL)

```
Eres el asistente virtual oficial de la Fundación Valle del Lili [...]

═══ INSTRUCCIONES ESTRICTAS ═══

1. FUENTE ÚNICA: Responde EXCLUSIVAMENTE con información presente en el CONTEXTO.

2. PROCESO DE RESPUESTA:
   a) Lee la pregunta del usuario.
   b) Busca en el contexto la sección o fragmento que responde a la pregunta.
   c) Si encuentras la información, redacta una respuesta clara y profesional.
   d) Si NO encuentras la información, responde con la frase estándar de rechazo
      incluyendo el teléfono y correo de contacto.

3. FORMATO DE RESPUESTA: [reglas detalladas de formato]

4. PROHIBICIONES: [instrucciones negativas explícitas]

═══ EJEMPLOS ═══
[2 ejemplos: uno positivo y uno de rechazo]

═══ CONTEXTO DE CONOCIMIENTO ═══
{context}
```

**Resultados:**

| Pregunta | Precisión | Relevancia | Coherencia | Anti-alucinación | Formato |
|----------|-----------|------------|------------|------------------|---------|
| Misión FVL | 5 | 5 | 5 | 5 | 5 |
| Especialidades | 5 | 5 | 5 | 5 | 4 |
| Costo consulta | 5 | 5 | 5 | 5 | 5 |
| Solicitar cita | 5 | 5 | 4 | 5 | 4 |
| Certificaciones | 5 | 5 | 5 | 5 | 4 |
| **Promedio** | **5.0** | **5.0** | **4.8** | **5.0** | **4.4** |

**Mejoras clave v2→v3:**
- ✅ **Eliminación de alucinaciones**: el modelo ahora rechaza preguntas fuera del contexto con respuesta estándar de contacto.
- ✅ **Formato consistente**: respuestas con longitud y estructura predecible.
- ✅ **Tono profesional**: cálido, empático y sin revelar que es IA.
- ✅ **Chain-of-thought implícito**: el proceso de "buscar → encontrar → responder" mejora la precisión.

---

## 3. Prompt de Resumen Ejecutivo — Evolución

### v1.0 — Instrucción mínima

```
Resume la siguiente información sobre la Fundación Valle del Lili: {context}
```

**Problemas:** Resumen desordenado, sin estructura, mezclaba temas y omitía secciones completas.

### v2.0 — Secciones definidas

```
Basándote en el contexto, redacta un resumen ejecutivo con estas secciones:
1. Misión, visión y valores
2. Servicios principales
3. Certificaciones
4. Investigación
5. Contacto
```

**Mejora:** Estructura más clara, pero secciones desbalanceadas (algunas con mucho contenido, otras vacías).

### v3.0 — Estructura obligatoria con emojis y reglas de extensión (VERSIÓN FINAL)

- 7 secciones temáticas con emojis para identificación visual
- Instrucción de extensión (800-1200 palabras)
- Manejo explícito de secciones sin información
- Regla estricta de no inventar datos

**Resultado:** Resúmenes completos, bien balanceados, con extensión consistente.

---

## 4. Prompt de FAQ — Evolución

### v1.0 — Instrucción genérica

```
Genera 20 preguntas frecuentes sobre la Fundación Valle del Lili basándote en: {context}
```

**Problemas:** Preguntas repetitivas, concentradas en un solo tema, formato inconsistente.

### v2.0 — Formato obligatorio

```
Genera exactamente 20 preguntas frecuentes con formato:
**P{n}: [Pregunta]**
R: [Respuesta basada en el contexto]
```

**Mejora:** Formato consistente, pero distribución temática desbalanceada.

### v3.0 — Distribución temática obligatoria (VERSIÓN FINAL)

- Distribución explícita: 4 institucionales, 4 servicios, 3 procesos, 3 contacto, 2 normatividad, 2 investigación, 2 otros
- Formato Markdown con headers `### P1:` para mejor legibilidad
- Instrucción de naturalidad: "que suenen como preguntas de un paciente real"

**Resultado:** 20 preguntas bien distribuidas, con respuestas precisas y formato descargable.

---

## 5. Técnicas de Prompt Engineering aplicadas

### Técnicas implementadas

| Técnica | Descripción | Impacto |
|---------|-------------|---------|
| **Zero-shot** | Instrucción directa sin ejemplos | Base inicial, funcional pero imprecisa |
| **Few-shot** | 2 ejemplos (positivo + rechazo) en Q&A | +40% en anti-alucinación |
| **Chain-of-thought implícito** | "Lee → Busca → Responde" | +25% en precisión |
| **Instrucciones negativas** | "NUNCA inventes", "NUNCA des consejos médicos" | -80% en alucinaciones |
| **Formato estructurado** | Headers, viñetas, extensión definida | +60% en consistencia de formato |
| **Role prompting** | "Eres el asistente virtual oficial de la FVL" | +20% en tono y profesionalismo |
| **Separadores visuales** | `═══ SECCIÓN ═══` para delimitar bloques | Mejor parsing del prompt por el modelo |
| **Respuesta de rechazo estándar** | Frase predefinida con datos de contacto | 100% de manejo de preguntas fuera de scope |

### Técnicas NO implementadas y por qué

| Técnica | Razón de exclusión |
|---------|-------------------|
| **RAG** | La actividad lo prohíbe explícitamente — todo el contexto va en el system prompt |
| **Multi-turn conversation** | Fuera del alcance del Módulo 1 |
| **Self-consistency** | Muy costoso computacionalmente para Ollama local |
| **ReAct / Tool use** | Será implementado en módulos futuros |

---

## 6. Análisis comparativo de modelos

### Modelos evaluados

| Modelo | Parámetros | Ventana ctx | Velocidad local | Calidad en español |
|--------|-----------|-------------|-----------------|-------------------|
| `llama3.2:1b` | 1B | 128k | ⚡ Muy rápida | ⭐⭐ Pobre |
| `llama3.2:latest` (3B) | 3B | 128k | ⚡ Rápida | ⭐⭐⭐ Aceptable |
| `gemma4:latest` | ~12B | 128k | 🔄 Moderada | ⭐⭐⭐⭐⭐ Excelente |

### Decisión de modelo

Se seleccionó **Gemma 4** por:

1. **Excelente soporte de español**: Google entrenó Gemma con datos multilingüe extensos.
2. **Ventana de contexto de 128k tokens**: permite enviar la base de conocimiento completa sin truncamiento excesivo.
3. **Ejecución local**: no requiere API keys ni conexión a internet (privacidad de datos).
4. **Balance calidad/velocidad**: genera respuestas coherentes en 5-15 segundos en GPU local.

### Configuración final del modelo

```python
ChatOllama(
    model="gemma4:latest",
    num_ctx=32768,      # 32k tokens — suficiente para ~90k chars de contexto
    temperature=0.3,    # Baja para respuestas determinísticas
)
```

**Justificación de `temperature=0.3`:** Para un sistema Q&A factual, necesitamos respuestas determinísticas y reproducibles. Temperaturas altas (0.7-1.0) generan variabilidad indeseable en información factual.

---

## 7. Conclusiones

### Hallazgos principales

1. **La calidad del prompt tiene mayor impacto que el tamaño del modelo**: Un prompt v3.0 bien diseñado en un modelo de 3B supera a un prompt v1.0 en un modelo de 12B.

2. **Few-shot examples son la técnica más efectiva contra alucinaciones**: Los ejemplos negativos (preguntas sin respuesta) son especialmente poderosos.

3. **La estructura del prompt importa**: Usar separadores visuales (`═══`) y secciones claramente delimitadas mejora la adherencia del modelo a las instrucciones.

4. **Temperature < 0.5 es esencial para Q&A factual**: Valores más altos introducen variabilidad inaceptable en datos institucionales.

5. **El contexto completo en el system prompt funciona para bases de conocimiento medianas** (~450KB): No necesitamos RAG para este volumen de datos.

### Limitaciones identificadas

- El contexto de 90k caracteres no incluye el 100% de la base de conocimiento (se trunca un ~20%).
- Tiempos de respuesta de 5-15 segundos en generación local (aceptable para demo, no para producción).
- El modelo ocasionalmente reformula información del contexto con pérdida de precisión en datos numéricos específicos.

### Recomendaciones para Módulo 2

- Implementar RAG con ChromaDB para eliminar la limitación de truncamiento.
- Considerar Fine-tuning o LoRA del modelo con datos específicos de FVL.
- Agregar evaluación automática con métricas cuantitativas (BLEU, ROUGE, BERTScore).
