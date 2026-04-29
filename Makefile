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

	
