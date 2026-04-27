# Registro de cambios y organización del repo — Módulo 1 (FVL)

Fecha: 2026-04-25  
Proyecto: Capa Semántica — Fundación Valle del Lili (FVL)  
Equipo: Nicolas, Jhonatan, Mateo, Jorge

Este documento resume **qué se creó/ajustó en el repositorio**, **cómo se organizó el trabajo (issues/milestones/ramas)** y **por qué** se tomó cada decisión, con el objetivo de facilitar la ejecución del Módulo 1 y la colaboración del equipo.

---

## 1) Estructura de colaboración (ramas)

### Qué se definió
Se estableció un flujo de ramas simple y escalable para un equipo de 4:

- Ramas personales (trabajo diario): `Nicolas`, `Jhonatan`, `Mateo`, `Jorge`
- Rama de integración: `Development`
- Rama estable: `main`
- Rama de despliegue (opcional): `Production`

### Por qué
- Permite **trabajo paralelo** sin bloquearse.
- La rama `Development` concentra integración y revisión (PRs) antes de tocar `main`.
- `main` queda como “estado demostrable” (demo + pruebas) para entregar.
- `Production` queda lista para “lo que mostraríamos como versión final”, si la necesitan.

### Documento guía
- `docs/workflow_git.md`

---

## 2) Organización por Milestones + Issues (para repartir carga)

### Qué se creó
Se agregaron plantillas de issues y un backlog sugerido por milestones.

Milestones recomendados para Módulo 1:
- `M1-0 Setup`
- `M1-1 Investigación + Alcance (FVL)`
- `M1-2 Scraping + Dataset crudo`
- `M1-3 Limpieza + Chunking + KB final`
- `M1-4 Q&A (NO-RAG) + Prompt`
- `M1-5 Streamlit Demo + Pruebas + Informe`

Backlog con asignación sugerida (editable según el equipo):
- `docs/milestones_backlog.md`

### Por qué
- Hace el avance **medible** y facilita dividir el trabajo por especialidad (scraping/datos/prompt/ui/docs).
- Cada issue tiene **Definition of Done (DoD)** para evitar ambigüedad.
- Facilita que los PRs sean pequeños y revisables (1 PR ≈ 1 tema).

---

## 3) Plantillas de GitHub (Issues + PR)

### Qué se agregó
Carpeta `.github/` con:

- Template de PR:
  - `.github/pull_request_template.md`
- Templates de issues (formularios):
  - `.github/ISSUE_TEMPLATE/01-investigacion.yml`
  - `.github/ISSUE_TEMPLATE/02-scraping.yml`
  - `.github/ISSUE_TEMPLATE/03-kb-datos.yml`
  - `.github/ISSUE_TEMPLATE/04-qa-prompt.yml`
  - `.github/ISSUE_TEMPLATE/05-streamlit.yml`
  - `.github/ISSUE_TEMPLATE/06-documentacion.yml`

### Por qué
- Estandariza qué información debe traer cada issue (responsable, URLs, riesgos, decisiones).
- El PR template fuerza checklist mínimo: ética, pruebas, demo, docs.
- Acelera la creación de issues y reduce la fricción de coordinación.

---

## 4) Documentación base (para el informe y para ejecutar)

### Qué se agregó
Se agregaron docs “plantilla” para llenar con el contenido real del grupo:

- `docs/fuentes.md`: inventario de fuentes públicas (URLs por sección).
- `docs/alcance.md`: qué responde / qué no responde (reglas de seguridad).
- `docs/informe.md`: plantilla con la estructura exigida por el enunciado.
- `docs/kb_stats.md`: placeholder para estadísticas y evidencias de la KB.
- `docs/resultados_ejemplos.md`: evidencia de 5+ ejemplos (calidad/limitaciones).
- `docs/milestones_backlog.md`: backlog/milestones sugeridos.
- `docs/workflow_git.md`: reglas del flujo de ramas y PRs.

### Por qué
- El enunciado exige trazabilidad del proceso (scraping, limpieza, chunking, resultados).
- Tener la estructura desde el inicio reduce “deuda” de documentación al final.
- Permite que cada integrante complete partes concretas sin pisarse.

---

## 5) Plantillas para pruebas (20 preguntas)

### Qué se agregó
En `tests/`:
- `tests/qa_questions.md`: banco de 30 preguntas objetivo (para elegir las 20 finales).
- `tests/qa_results.csv`: plantilla de salida para registrar preguntas/respuestas.

### Por qué
- El enunciado pide **mínimo 20 preguntas** y análisis de calidad.
- Estandarizar el formato (CSV) facilita:
  - anexarlo al informe,
  - comparar respuestas,
  - detectar huecos de la KB (“no está en contexto”).

---

## 6) Streamlit: export de resultados de Q&A

### Qué se ajustó
En `app/main.py` se añadió una sección de “Registro de pruebas”:
- Guarda en memoria (sesión) pares `{question, answer}`.
- Permite descargar un `qa_results.csv` desde la UI.
- Recomendación: guardar el CSV final como `tests/qa_results.csv` para el informe.

### Por qué
- Acelera el ciclo de evaluación (hacer 20 preguntas y guardar evidencia).
- Evita que el equipo “copie/pegue” manualmente respuestas y pierda tiempo.

---

## 7) Referencias en README

### Qué se ajustó
Se añadió en `README.md` una sección de “Gestión del proyecto (Issues/Milestones)” apuntando a:
- `docs/milestones_backlog.md`
- `docs/workflow_git.md`
- `docs/fuentes.md`, `docs/alcance.md`, `docs/informe.md`
- `tests/qa_questions.md`, `tests/qa_results.csv`

### Por qué
- Para que cualquier persona que abra el repo entienda rápido “cómo se trabaja” y “qué entregar”.

---

## 8) Sincronización de ramas

### Qué se hizo
Los cambios de organización/documentación se propagaron para que todas las ramas del equipo queden alineadas:
- `Jorge` (origen de los cambios)
- `Nicolas`
- `Mateo`
- `Jhonatan`
- `Development`
- `main`
- `Production`

### Por qué
- Evita que cada integrante tenga un “repo distinto” en su rama base.
- Reduce conflictos al momento de abrir PRs hacia `Development`.

---

## 9) Cómo usar esto (paso a paso recomendado)

1. Crear milestones en GitHub según `docs/milestones_backlog.md`.
2. Crear issues usando los templates de `.github/ISSUE_TEMPLATE/`.
3. Cada integrante trabaja en su rama (`Nicolas`, `Mateo`, `Jhonatan`, `Jorge`) y abre PR a `Development`.
4. Cuando `Development` esté estable (demo + pruebas), abrir PR a `main`.
5. Completar `docs/informe.md` y adjuntar `tests/qa_results.csv` como evidencia.

