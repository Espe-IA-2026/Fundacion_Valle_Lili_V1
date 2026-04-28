from __future__ import annotations

from urllib.parse import urljoin

from pydantic import AnyHttpUrl, TypeAdapter

from semantic_layer_fvl.schemas import DocumentCategory, UrlRecord

DEFAULT_SEED_PATHS: tuple[tuple[str, DocumentCategory, int, str], ...] = (
    ("/", DocumentCategory.ORGANIZACION, 10, "Pagina principal y panorama general."),
    (
        "/nuestra-institucion",
        DocumentCategory.ORGANIZACION,
        20,
        "Historia, mision, vision y valores institucionales.",
    ),  # noqa: E501
    (
        "/servicios",
        DocumentCategory.SERVICIOS,
        30,
        "Servicios medicos institucionales.",
    ),
    ("/especialidades", DocumentCategory.SERVICIOS, 40, "Especialidades medicas."),
    (
        "/directorio-medico",
        DocumentCategory.TALENTO_HUMANO,
        50,
        "Directorio de especialistas.",
    ),
    (
        "/nuestra-institucion/nuestras-sedes",
        DocumentCategory.SEDES_UBICACIONES,
        60,
        "Ubicaciones y puntos de atencion.",
    ),  # noqa: E501
    (
        "/contactanos",
        DocumentCategory.CONTACTO,
        70,
        "Canales de contacto institucionales.",
    ),
    (
        "/nuestra-institucion/marco-legal",
        DocumentCategory.NORMATIVIDAD,
        80,
        "Marco legal, politicas y derechos.",
    ),  # noqa: E501
    (
        "/investigacion",
        DocumentCategory.INVESTIGACION,
        90,
        "Centro de investigacion clinica.",
    ),
    (
        "/educacion",
        DocumentCategory.EDUCACION,
        100,
        "Programas de formacion y docencia.",
    ),
    (
        "/noticias-y-eventos",
        DocumentCategory.NOTICIAS,
        110,
        "Noticias y eventos institucionales.",
    ),
)

_HTTP_URL_ADAPTER = TypeAdapter(AnyHttpUrl)


def build_seed_urls(base_url: str | AnyHttpUrl) -> list[UrlRecord]:
    normalized_base_url = str(base_url)
    records = [
        UrlRecord(
            url=_HTTP_URL_ADAPTER.validate_python(urljoin(normalized_base_url, path)),
            category=category,
            priority=priority,
            notes=notes,
        )
        for path, category, priority, notes in DEFAULT_SEED_PATHS
    ]
    return sorted(records, key=lambda record: (record.priority, str(record.url)))
