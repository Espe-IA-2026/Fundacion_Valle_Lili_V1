# ADR-001: Pipeline Modular y Contratos Explicitos

## Estado

Aprobado

## Contexto

El proyecto necesita combinar varias fuentes de informacion y transformarlas a un formato Markdown consistente sin acoplar cada extractor a la salida final.

## Decision

Se adopta una arquitectura modular con estas capas:

- extractores que producen `RawPage`
- procesadores que limpian y estructuran
- writers que persisten `ProcessedDocument`
- orquestacion que coordina corridas y resumenes

Los contratos entre capas se modelan con Pydantic.

## Consecuencias

Positivas:

- facilita pruebas offline
- permite agregar nuevas fuentes sin reescribir la pipeline
- mantiene separacion clara de responsabilidades

Negativas:

- hay mas clases y modelos base que en un script lineal
- algunas transformaciones requieren mapeos intermedios adicionales
