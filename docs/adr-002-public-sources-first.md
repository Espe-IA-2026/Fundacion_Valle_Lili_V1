# ADR-002: Fuentes Publicas Primero y Respeto por Robots

## Estado

Aprobado

## Contexto

La capa semantica se alimenta de informacion institucional y debe respetar restricciones eticas y operativas del sitio objetivo.

## Decision

Se priorizan fuentes publicas y accesibles sin autenticacion.

Para extraccion web:

- se consulta `robots.txt`
- se aplica rate limiting
- se evita acceso a datos sensibles

Para fuentes complementarias:

- se prefieren feeds publicos antes que integraciones con claves o scraping ad hoc

## Consecuencias

Positivas:

- menor riesgo legal y operativo
- mejor trazabilidad de origen
- pruebas mas simples y repetibles

Negativas:

- algunas fuentes pueden ofrecer menos detalle que una integracion propietaria
- el proyecto depende de la estabilidad de feeds y contenido publico
