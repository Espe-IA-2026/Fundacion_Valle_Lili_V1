# Flujo de trabajo Git (equipo de 4)

## Branches
- Ramas personales (trabajo diario): `Nicolas`, `Jhonatan`, `Mateo`, `Jorge`
- Integración: `Development`
- Estable: `main`

## Reglas de integración
1. Cada integrante trabaja en su rama y hace commits pequeños.
2. Se abre PR desde la rama personal hacia `Development`.
3. Solo cuando `Development` está estable (demo + pruebas), se abre PR hacia `main`.

## Comandos típicos
Actualizar tu rama con lo último de `Development`:
```bash
git fetch origin
git switch Nicolas  # o tu rama
git merge origin/Development
```

Subir cambios:
```bash
git push -u origin Nicolas  # o tu rama
```

## Convenciones
- 1 PR = 1 tema (scraping / KB / UI / docs).
- Incluir evidencia en el PR (logs, links internos, capturas).
- No subir datos sensibles.

