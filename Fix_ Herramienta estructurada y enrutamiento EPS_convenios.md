# Fix: Herramienta estructurada y enrutamiento EPS/convenios
## Estado actual
El proyecto tiene tres capas: RAG (ChromaDB), herramienta estructurada (JSON), y un agente LangChain que enruta entre ambas. El agente usa `langchain.agents.create_agent` (wrapper válido de LangGraph en langchain 1.2.18) con `InMemorySaver` para memoria de sesión. La app Streamlit muestra el historial y el razonamiento del agente correctamente.
## Bugs identificados (con certeza)
### Bug 1 — Mismatch de claves JSON (crítico, afecta TODA la herramienta estructurada)
`_format_structured_data` en `tools.py` lee claves planas (`razon_social`, `nit`, `contactos`, `horarios`, `sedes`, …) que **no existen** en el JSON real. El JSON real tiene estructura anidada:
* `informacion_corporativa.nombre_legal`, `.nit`, `.naturaleza_juridica`, `.pagina_web`, `.acreditaciones`
* `contactos_clave` (no `contactos`)
* `horarios_atencion` (no `horarios`)
* `sedes_y_ubicaciones` (no `sedes`; sin campo `telefono`, usa `ciudad` + `servicios_principales`)
Resultado: **todo devuelve 'N/A' o vacío** en producción, aunque los tests pasan porque usan datos mock con la estructura plana antigua.
### Bug 2 — Sección `convenios_eps_y_aseguradoras` nunca se lee (crítico, causa directa del problema reportado)
`_format_structured_data` no tiene ningún bloque para la clave `convenios_eps_y_aseguradoras` que contiene `eps_regimen_contributivo`, `medicina_prepagada`, `aseguradoras_y_otros` y `nota_importante`. Esta es la causa exacta de que las preguntas sobre EPS no obtengan respuesta.
### Bug 3 — Enrutamiento no menciona EPS/convenios
Ni el docstring `@tool` de `get_fvl_structured_info` ni `_AGENT_SYSTEM_PROMPT` listan EPS/convenios como categoría de esta herramienta. El agente no sabe enrutar esas preguntas al JSON.
### Bug 4 — Tests dan falsos positivos
`test_structured_tool.py._sample_data()` usa la estructura plana antigua → los tests pasan aunque el código falla con el JSON real.
## Cambios propuestos
### 1. `src/app_agent/tools.py` — Reescribir `_format_structured_data`
Leer las claves reales del JSON:
* `informacion_corporativa` → razón social, NIT, naturaleza jurídica, web, ranking, acreditaciones
* `contactos_clave` → bloque CONTACTOS
* `horarios_atencion` → bloque HORARIOS
* `sedes_y_ubicaciones` → bloque SEDES (adaptar formato: mostrar `ciudad` y `servicios_principales` en vez de `telefono`)
* `convenios_eps_y_aseguradoras` → nuevo bloque CONVENIOS Y EPS (eps contributivo, prepagada, aseguradoras, nota)
* `servicios_destacados` → ya funciona (clave correcta)
* `servicios_de_apoyo` → nuevo bloque SERVICIOS DE APOYO
* `servicios_digitales` → nuevo bloque SERVICIOS DIGITALES
También actualizar el docstring `@tool` de `get_fvl_structured_info` para incluir EPS/convenios, medicina prepagada y aseguradoras.
### 2. `src/app_agent/agent.py` — Actualizar `_AGENT_SYSTEM_PROMPT`
Añadir en la sección de `get_fvl_structured_info`:
* EPS en convenio y régimen contributivo
* Medicina prepagada y aseguradoras
* SOAT, ARL y seguros internacionales
Añadir instrucción de que preguntas sobre "¿mi EPS tiene convenio?" o "¿atienden con X EPS?" deben usar la herramienta estructurada.
### 3. `tests/test_structured_tool.py` — Actualizar datos mock y añadir test de EPS
Actualizar `_sample_data()` para usar la estructura anidada real del JSON (`informacion_corporativa`, `contactos_clave`, `horarios_atencion`, `sedes_y_ubicaciones`, `convenios_eps_y_aseguradoras`). Adaptar las assertions existentes. Añadir test `test_get_fvl_structured_info_incluye_eps` que verifica que el resultado contiene nombres de EPS.