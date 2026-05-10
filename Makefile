limpiar:
	cls
	cls
	cls

especialistas:
	make limpiar
	uv run semantic-layer-fvl crawl-domain especialistas --write

sedes:
	make limpiar 
	uv run semantic-layer-fvl crawl-domain sedes --write
institucional:
	make limpiar 
	uv run semantic-layer-fvl crawl-domain institucional --write
servicios:
	make limpiar 
	uv run semantic-layer-fvl crawl-domain servicios --write

servtest:
	make limpiar 
	uv run semantic-layer-fvl crawl-domain servicios --write --max-urls 3

espetest:
	make limpiar 
	uv run semantic-layer-fvl crawl-domain especialistas --write --max-urls 50

app:
	make limpiar
	uv run streamlit run src/app/main.py
