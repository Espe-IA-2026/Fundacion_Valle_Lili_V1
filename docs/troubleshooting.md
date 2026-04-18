# Troubleshooting

## `uv sync` falla por permisos de cache

Sintoma:

```text
Failed to initialize cache at C:\Users\USER\AppData\Local\uv\cache
```

Acciones:

- ejecutar `uv sync` con permisos suficientes en el entorno local
- revisar politicas de acceso al cache de `uv`

## `pytest` falla al crear temporales de Windows

Sintoma:

```text
PermissionError: ... AppData\\Local\\Temp\\pytest-of-USER
```

Estado actual:

- la suite del repo ya evita depender del directorio temporal por defecto
- si vuelve a aparecer, revisar tests nuevos que usen temporales del sistema

## Escritura de archivos bloqueada desde Python

Sintoma:

```text
PermissionError: [Errno 13] Permission denied
```

Acciones:

- validar que `OUTPUT_DIR` y `RUNS_DIR` apunten a rutas permitidas
- probar primero sin `--write` para aislar extraccion de persistencia

## `robots.txt` responde `403` o algun `4xx`

Comportamiento actual del proyecto:

- si `robots.txt` responde un `4xx` distinto de `429`, el crawler lo trata como no disponible y continua
- si responde `429` o `5xx`, el crawler conserva un comportamiento restrictivo y bloquea la extraccion

Si aun falla el crawl:

- revisar si la pagina objetivo tambien devuelve `403`
- revisar el `User-Agent` configurado
- validar si el sitio usa WAF o protecciones anti-bot

## Un feed no produce documentos

Checklist:

- confirmar que el feed sea RSS o Atom valido
- revisar que tenga `title` y `link` por item
- verificar limites como `YOUTUBE_SEARCH_LIMIT` o `NEWS_FEED_LIMIT`
