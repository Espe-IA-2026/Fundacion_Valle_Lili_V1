# =============================================================================
#  Makefile  —  Asistente Virtual Fundación Valle del Lili
#  Gestor de paquetes: uv  |  Python 3.12  |  Plataforma: Windows (cmd)
# =============================================================================

.PHONY: help limpiar instalar config \
        servicios especialistas sedes institucional noticias multimedia full-etl \
        servtest espetest \
        build-index rebuild-index \
        app \
        test test-v lint formato

.DEFAULT_GOAL := help

# =============================================================================
#  AYUDA
# =============================================================================
help:
	@echo.
	@echo  ======================================================================
	@echo   Asistente Virtual  --  Fundacion Valle del Lili
	@echo   Gestor: uv  ^|  Python 3.12  ^|  Streamlit + LangChain + ChromaDB
	@echo  ======================================================================
	@echo.
	@echo  CONFIGURACION
	@echo  --------------
	@echo    make instalar       Instala / actualiza dependencias  (uv sync)
	@echo    make config         Muestra la configuracion activa del proyecto
	@echo.
	@echo  ETL / SCRAPING
	@echo  ---------------
	@echo    make servicios      Crawling dominio: servicios
	@echo    make especialistas  Crawling dominio: especialistas
	@echo    make sedes          Crawling dominio: sedes
	@echo    make institucional  Crawling dominio: institucional
	@echo    make noticias       Extraccion de noticias curadas (RSS/Atom)
	@echo    make multimedia     Busqueda y extraccion de YouTube
	@echo    make full-etl       Pipeline completo (todos los dominios + fuentes)
	@echo.
	@echo  MODOS DE PRUEBA  (ejecuciones limitadas)
	@echo  ------------------------------------------
	@echo    make servtest       Crawl servicios  (max 3 URLs)
	@echo    make espetest       Crawl especialistas  (max 50 URLs)
	@echo.
	@echo  RAG
	@echo  ----
	@echo    make build-index    Construye el indice vectorial ChromaDB
	@echo    make rebuild-index  Reconstruye el indice desde cero  (--force)
	@echo.
	@echo  APLICACION
	@echo  -----------
	@echo    make app            Lanza el dashboard Streamlit
	@echo.
	@echo  TESTS Y CALIDAD
	@echo  ----------------
	@echo    make test           Suite de tests offline  (modo silencioso)
	@echo    make test-v         Suite de tests offline  (modo verbose)
	@echo    make lint           Analisis estatico de codigo  (ruff check)
	@echo    make formato        Formato automatico de codigo  (ruff format)
	@echo.

# =============================================================================
#  UTILIDAD INTERNA
# =============================================================================
limpiar:
	@cls

# =============================================================================
#  CONFIGURACION
# =============================================================================
instalar:
	@echo [SETUP] Sincronizando dependencias con uv sync...
	@uv sync
	@echo [SETUP] Entorno virtual actualizado.

config:
	@echo [CONFIG] Configuracion activa del proyecto:
	@uv run semantic-layer-fvl show-config

# =============================================================================
#  ETL / SCRAPING
# =============================================================================
servicios: limpiar
	@echo [ETL] Crawling dominio servicios...
	@uv run semantic-layer-fvl crawl-domain servicios --write
	@echo [ETL] Dominio servicios completado.

especialistas: limpiar
	@echo [ETL] Crawling dominio especialistas...
	@uv run semantic-layer-fvl crawl-domain especialistas --write
	@echo [ETL] Dominio especialistas completado.

sedes: limpiar
	@echo [ETL] Crawling dominio sedes...
	@uv run semantic-layer-fvl crawl-domain sedes --write
	@echo [ETL] Dominio sedes completado.

institucional: limpiar
	@echo [ETL] Crawling dominio institucional...
	@uv run semantic-layer-fvl crawl-domain institucional --write
	@echo [ETL] Dominio institucional completado.

noticias: limpiar
	@echo [ETL] Extrayendo noticias curadas (RSS/Atom)...
	@uv run semantic-layer-fvl news-curated --write
	@echo [ETL] Noticias completadas.

multimedia: limpiar
	@echo [ETL] Buscando y extrayendo contenido de YouTube...
	@uv run semantic-layer-fvl youtube-search "Fundacion Valle del Lili" --write
	@echo [ETL] Multimedia completada.

full-etl: limpiar
	@echo [ETL] Iniciando pipeline ETL completo (6 etapas)...
	@echo.
	@echo [ETL] 1/6 Dominio: servicios
	@uv run semantic-layer-fvl crawl-domain servicios --write
	@echo [ETL] 2/6 Dominio: especialistas
	@uv run semantic-layer-fvl crawl-domain especialistas --write
	@echo [ETL] 3/6 Dominio: sedes
	@uv run semantic-layer-fvl crawl-domain sedes --write
	@echo [ETL] 4/6 Dominio: institucional
	@uv run semantic-layer-fvl crawl-domain institucional --write
	@echo [ETL] 5/6 Fuente: noticias curadas
	@uv run semantic-layer-fvl news-curated --write
	@echo [ETL] 6/6 Fuente: multimedia YouTube
	@uv run semantic-layer-fvl youtube-search "Fundacion Valle del Lili" --write
	@echo.
	@echo [ETL] Pipeline completo finalizado. Base de conocimiento actualizada.

# =============================================================================
#  MODOS DE PRUEBA
# =============================================================================
servtest: limpiar
	@echo [TEST-ETL] Crawl de prueba: servicios (max 3 URLs)
	@uv run semantic-layer-fvl crawl-domain servicios --write --max-urls 3
	@echo [TEST-ETL] Prueba de servicios completada.

espetest: limpiar
	@echo [TEST-ETL] Crawl de prueba: especialistas (max 50 URLs)
	@uv run semantic-layer-fvl crawl-domain especialistas --write --max-urls 50
	@echo [TEST-ETL] Prueba de especialistas completada.

# =============================================================================
#  RAG
# =============================================================================
build-index:
	@echo [RAG] Construyendo indice vectorial ChromaDB...
	@uv run semantic-layer-fvl build-index
	@echo [RAG] Indice construido correctamente.

rebuild-index:
	@echo [RAG] Reconstruyendo indice vectorial desde cero (--force)...
	@uv run semantic-layer-fvl build-index --force
	@echo [RAG] Indice reconstruido correctamente.

# =============================================================================
#  APLICACION
# =============================================================================
app: limpiar
	@echo [APP] Iniciando Asistente Virtual FVL en http://localhost:8501 ...
	@uv run python -m streamlit run src/app/main.py

# =============================================================================
#  TESTS Y CALIDAD DE CODIGO
# =============================================================================
test:
	@echo [TEST] Ejecutando suite de tests offline (modo silencioso)...
	@uv run pytest -q
	@echo [TEST] Suite completada.

test-v:
	@echo [TEST] Ejecutando suite de tests offline (modo verbose)...
	@uv run pytest -v

lint:
	@echo [CALIDAD] Analizando codigo con ruff check...
	@uv run ruff check src/ tests/
	@echo [CALIDAD] Analisis completado.

formato:
	@echo [CALIDAD] Aplicando formato con ruff format...
	@uv run ruff format src/ tests/
	@echo [CALIDAD] Formato aplicado.
