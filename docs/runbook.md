# Runbook

## Objetivo

Esta guia resume como ejecutar el proyecto en modo local y como interpretar sus salidas principales.

## Preparacion

1. Crear `.env` a partir de `.env.example`.
2. Instalar dependencias con `uv sync`.
3. Validar configuracion con `uv run semantic-layer-fvl show-config`.

## Comandos operativos

### Procesar una sola URL

```powershell
uv run semantic-layer-fvl crawl-once https://valledellili.org/quienes-somos
```

Usar este comando para depurar extracción, limpieza y clasificación sobre una sola página.

### Procesar semillas del sitio

```powershell
uv run semantic-layer-fvl crawl-seeds --limit 5 --save-summary
```

Este comando toma las URLs semilla definidas en el proyecto y devuelve un resumen con conteos de éxito y fallo.

### Procesar feeds complementarios

```powershell
uv run semantic-layer-fvl youtube-feed https://www.youtube.com/feeds/videos.xml?channel_id=...
uv run semantic-layer-fvl news-feed https://example.com/feed.xml
```

### Descubrimiento BFS

```powershell
uv run semantic-layer-fvl crawl-discover --max-pages 50 --write --save-summary
```

Arranca desde las URLs semilla y sigue los enlaces internos en anchura (BFS) hasta alcanzar `--max-pages`.
Las URLs bloqueadas por `robots.txt` se omiten silenciosamente; los demas errores quedan registrados en el resumen.

### Corrida compuesta

```powershell
uv run semantic-layer-fvl run-all --seed-limit 5 --youtube-feed https://... --news-feed https://... --save-summary
```

## Artefactos de salida

- `knowledge/`: documentos Markdown organizados por categoria.
- `runs/`: resúmenes JSON de las corridas cuando se usa `--save-summary`.

## Lectura del resumen

Los comandos por lote imprimen:

- `processed`: cantidad total de items intentados.
- `success`: cantidad de items procesados correctamente.
- `failure`: cantidad de items que fallaron.

Cuando hay errores, cada item fallido incluye el `source`, el `input` y el mensaje de error.

## Vectorstore (busqueda semantica)

### Indexar knowledge existente

```powershell
uv run semantic-layer-fvl index-knowledge
```

Lee todos los archivos `.md` del directorio `knowledge/` y los indexa en ChromaDB (persiste en `vectorstore/`). La primera vez descargará el modelo de embeddings (~120 MB).

### Busqueda semantica

```powershell
uv run semantic-layer-fvl search "cardiología"
uv run semantic-layer-fvl search "horarios de atencion" --limit 10
```

Busca por significado, no por palabras exactas. Los resultados se muestran con su score de distancia (menor = mas relevante).
