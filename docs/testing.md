# Testing

## Suite actual

La suite cubre:

- configuracion y settings
- contratos Pydantic
- rate limiting y cliente HTTP
- reglas de `robots.txt`
- mapeo de semillas
- crawler web base
- limpieza, estructuracion y escritura Markdown
- extractores de YouTube y noticias
- ejecucion del pipeline y resumenes de corrida
- despacho basico del CLI

## Ejecutar pruebas

```powershell
& .\.venv\Scripts\python.exe -m pytest
```

## Criterio actual

- las pruebas deben ser offline
- las integraciones externas se simulan con `httpx.MockTransport` o stubs
- los tests deben evitar dependencias de directorios temporales del sistema cuando el entorno tenga restricciones

## Siguiente mejora recomendada

- agregar pruebas de integracion con ejemplos reales de HTML y feeds guardados como fixtures
- validar formato del frontmatter generado contra un parser YAML
