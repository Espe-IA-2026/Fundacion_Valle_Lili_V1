from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DomainConfig:
    name: str
    sitemap_paths: list[str]
    container_selector: str
    output_folder: str
    category: str
    url_include_patterns: list[str]
    url_exclude_patterns: list[str]
    extra_metadata_selectors: dict[str, str]
    fallback_urls: list[str]


DOMAIN_CONFIGS: dict[str, DomainConfig] = {
    "servicios": DomainConfig(
        name="servicios",
        sitemap_paths=["servicios-sitemap.xml"],
        container_selector="main",
        output_folder="servicios",
        category="02_servicios",
        url_include_patterns=["/servicios/", "/servicio/"],
        url_exclude_patterns=[],
        extra_metadata_selectors={
            "categoria": ".breadcrumb > *:last-child, .categoria",
        },
        fallback_urls=["https://valledellili.org/servicios/"],
    ),
    "especialistas": DomainConfig(
        name="especialistas",
        sitemap_paths=["especialistas-sitemap.xml"],
        container_selector="main",
        output_folder="especialistas",
        category="03_talento_humano",
        url_include_patterns=["/especialistas/", "/medicos/", "/directorio-medico/"],
        url_exclude_patterns=[],
        extra_metadata_selectors={},
        fallback_urls=["https://valledellili.org/directorio-medico/"],
    ),
    "sedes": DomainConfig(
        name="sedes",
        sitemap_paths=["sedes-sitemap.xml"],
        container_selector="main",
        output_folder="sedes",
        category="04_sedes_ubicaciones",
        url_include_patterns=["/sedes/", "/sede/", "/ubicaciones/"],
        url_exclude_patterns=[],
        extra_metadata_selectors={
            "direccion": ".direccion, [class*='address'], table td:first-child",
            "horarios": ".horarios, [class*='schedule'], table",
        },
        fallback_urls=["https://valledellili.org/nuestra-institucion/nuestras-sedes/"],
    ),
    "institucional": DomainConfig(
        name="institucional",
        sitemap_paths=["page-sitemap.xml", "wp-sitemap-posts-page-1.xml"],
        container_selector=".ma-content",
        output_folder="institucional",
        category="01_organizacion",
        url_include_patterns=[
            "/nuestra-fundacion/",
            "/historia/",
            "/mision-y-vision/",
            "/quienes-somos/",
            "/nuestra-institucion/",
        ],
        url_exclude_patterns=["/servicios/", "/especialistas/", "/sedes/"],
        extra_metadata_selectors={},
        fallback_urls=[
            "https://valledellili.org/nuestra-institucion/",
        ],
    ),
}
