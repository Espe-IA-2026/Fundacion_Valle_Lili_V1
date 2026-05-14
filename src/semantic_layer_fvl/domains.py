"""Configuración de dominios de scraping para el sitio de la Fundación Valle del Lili.

Define la estructura ``DomainConfig`` y el diccionario ``DOMAIN_CONFIGS`` con los
parámetros de extracción para cada sección del sitio (servicios, especialistas,
sedes e institucional).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DomainConfig:
    """Parámetros de extracción para un dominio específico del sitio web.

    Attributes:
        name: Identificador corto del dominio (p.ej. ``"servicios"``).
        sitemap_paths: Rutas relativas del sitemap XML a consultar.
        container_selector: Selector CSS del contenedor principal de contenido.
        output_folder: Subcarpeta de salida dentro del directorio de conocimiento.
        category: Valor de ``DocumentCategory`` asignado a los documentos del dominio.
        url_include_patterns: Patrones que debe contener la URL para ser procesada.
        url_exclude_patterns: Patrones que excluyen una URL del procesamiento.
        extra_metadata_selectors: Mapa ``{campo: selector_css}`` para metadatos extra.
        fallback_urls: URLs de respaldo si el sitemap no devuelve resultados válidos.
        trim_before_first_h1: Si es ``True``, elimina el contenido previo al primer H1.
        markdown_cutoff_headings: Encabezados a partir de los cuales se trunca el Markdown.
        specialists_section_heading: Encabezado de la sección de especialistas a reformatear.
    """

    name: str
    sitemap_paths: list[str]
    container_selector: str
    output_folder: str
    category: str
    url_include_patterns: list[str]
    url_exclude_patterns: list[str]
    extra_metadata_selectors: dict[str, str]
    fallback_urls: list[str]
    trim_before_first_h1: bool = False
    markdown_cutoff_headings: list[str] = field(default_factory=list)
    specialists_section_heading: str | None = None


DOMAIN_CONFIGS: dict[str, DomainConfig] = {  # Configuraciones registradas por nombre de dominio
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
        trim_before_first_h1=True,
        markdown_cutoff_headings=[
            "### Otros servicios y especialidades",
            "### Contenidos relacionados",
        ],
        specialists_section_heading="## Especialistas que pueden atenderte",
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
        trim_before_first_h1=True,
        markdown_cutoff_headings=[
            "### Otros servicios y especialidades",
            "### Contenidos relacionados",
        ],
    ),
    "sedes": DomainConfig(
        name="sedes",
        sitemap_paths=["sedes-sitemap.xml"],
        container_selector="main",
        output_folder="sedes",
        category="04_sedes_ubicaciones",
        # Incluye rutas de sedes individuales y la página de listado de sedes
        url_include_patterns=[
            "/sedes/", "/sede/", "/ubicaciones/",
            "/nuestras-sedes/",
            "/nuestra-institucion/nuestras-sedes",
        ],
        url_exclude_patterns=[],
        extra_metadata_selectors={
            "direccion": ".direccion, [class*='address'], table td:first-child",
            "horarios": ".horarios, [class*='schedule'], table",
        },
        # Dos seeds: la página oficial de sedes y la de nuestra institución para
        # descubrir enlaces a sedes individuales si el sitemap no existe.
        fallback_urls=[
            "https://valledellili.org/nuestra-institucion/nuestras-sedes/",
            "https://valledellili.org/nuestra-institucion/",
        ],
        trim_before_first_h1=True,
        markdown_cutoff_headings=[
            "# Nuestra Historia",
            "## Noticias y novedades",
            "## Conoce otras sedes",
            "## ¿En qué tema de salud te podemos orientar hoy?",
            "### Conozca más de la Fundación Valle del Lili",
            "### Autorización datos personales",
            "### Otros servicios y especialidades",
            "### Contenidos relacionados",
        ],
    ),
    "institucional": DomainConfig(
        name="institucional",
        sitemap_paths=["page-sitemap.xml", "pages-sitemap.xml"],
        container_selector="main",
        output_folder="institucional",
        category="01_organizacion",
        # Patrones amplios para capturar historia, misión, calidad, investigación, etc.
        url_include_patterns=[
            "/nuestra-institucion/",
            "/mision",
            "/historia",
            "/valores",
            "/gestion-de-calidad",
            "/investigacion",
            "/impacto-social",
            "/hospital-universitario",
            "/sostenibilidad",
        ],
        url_exclude_patterns=[
            "/servicios/", "/directorio-medico/", "/nuestras-sedes/",
        ],
        extra_metadata_selectors={},
        fallback_urls=[
            "https://valledellili.org/nuestra-institucion/",
        ],
        trim_before_first_h1=True,
        markdown_cutoff_headings=[
            "### Conozca más de la Fundación Valle del Lili",
            "### Autorización datos personales",
            "### Otros servicios y especialidades",
            "### Contenidos relacionados",
        ],
    ),
}
