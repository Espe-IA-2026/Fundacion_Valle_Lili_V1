limpiar:
	cls
	cls
	cls

front:
	limpiar
	uv run streamlit run app/main.py

scrap:
	uv run scraper/fvl_scraper.py --max-pages 5 --no-headless
