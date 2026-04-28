limpiar:
	cls
	cls
	cls

front:
	make limpiar
	uv run streamlit run app/main.py

scrap:
	uv run scraper/fvl_scraper.py --max-pages 50 --no-headless
