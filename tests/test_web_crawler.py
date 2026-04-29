from __future__ import annotations

import httpx
import requests
import pytest

from semantic_layer_fvl.config.settings import Settings
from semantic_layer_fvl.domains import DOMAIN_CONFIGS
from semantic_layer_fvl.extractors import (
    CrawlBlockedError,
    HttpClient,
    RobotsFetchResult,
    RobotsPolicy,
    WebCrawler,
)
from semantic_layer_fvl.extractors.web_crawler import extract_links, normalize_title


def test_web_crawler_returns_raw_page_with_title_and_text() -> None:
    html = """
    <html>
      <head><title>Quienes Somos</title></head>
      <body><h1>Fundacion Valle del Lili</h1><p>Informacion institucional.</p></body>
    </html>
    """

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text=html,
            headers={"content-type": "text/html; charset=utf-8"},
            request=request,
        )

    def robots_fetcher(robots_url: str) -> RobotsFetchResult:
        return RobotsFetchResult(
            url=robots_url, status_code=200, text="User-agent: *\nAllow: /\n"
        )

    settings = Settings(requests_per_second=10, respect_robots_txt=True)
    client = HttpClient(settings, transport=httpx.MockTransport(handler))
    crawler = WebCrawler(
        client,
        settings=settings,
        robots_policy=RobotsPolicy(settings.user_agent, fetcher=robots_fetcher),
    )

    page = crawler.fetch("https://valledellili.org/quienes-somos")
    client.close()

    assert page.title == "Quienes Somos"
    assert "Fundacion Valle del Lili" in (page.text_content or "")
    assert page.metadata.http_status == 200


def test_web_crawler_decodes_utf8_content_without_declared_charset() -> None:
    html = "<html><head><title>Fundación Valle del Lili</title></head><body><p>Información institucional.</p></body></html>"  # noqa: E501
    content = html.encode("utf-8")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=content,
            headers={"content-type": "text/html"},
            request=request,
        )

    def robots_fetcher(robots_url: str) -> RobotsFetchResult:
        return RobotsFetchResult(
            url=robots_url, status_code=200, text="User-agent: *\nAllow: /\n"
        )

    settings = Settings(requests_per_second=10, respect_robots_txt=True)
    client = HttpClient(settings, transport=httpx.MockTransport(handler))
    crawler = WebCrawler(
        client,
        settings=settings,
        robots_policy=RobotsPolicy(settings.user_agent, fetcher=robots_fetcher),
    )

    page = crawler.fetch("https://valledellili.org/quienes-somos")
    client.close()

    assert page.title == "Fundación Valle del Lili"
    assert "Información institucional." in (page.text_content or "")


def test_web_crawler_uses_meta_description_as_fallback_for_sparse_pages() -> None:
    html = """
    <html>
      <head>
        <title>Servicios</title>
        <meta name="description" content="Conozca nuestros servicios institucionales." />
      </head>
      <body><script>window.__APP__ = {};</script></body>
    </html>
    """

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text=html,
            headers={"content-type": "text/html; charset=utf-8"},
            request=request,
        )

    def robots_fetcher(robots_url: str) -> RobotsFetchResult:
        return RobotsFetchResult(
            url=robots_url, status_code=200, text="User-agent: *\nAllow: /\n"
        )

    settings = Settings(requests_per_second=10, respect_robots_txt=True)
    client = HttpClient(settings, transport=httpx.MockTransport(handler))
    crawler = WebCrawler(
        client,
        settings=settings,
        robots_policy=RobotsPolicy(settings.user_agent, fetcher=robots_fetcher),
    )

    page = crawler.fetch("https://valledellili.org/servicios")
    client.close()

    assert "Conozca nuestros servicios institucionales." in (page.text_content or "")


def test_web_crawler_prefers_og_title_and_main_content() -> None:
    html = """
    <html>
      <head>
        <title>Pagina con ruido | Fundacion Valle del Lili | Fundacion Valle del Lili</title>
        <meta property="og:title" content="Especialidades de la A a la Z | Fundacion Valle del Lili" />
      </head>
      <body>
        <nav>Menu principal</nav>
        <main>
          <h1>Especialidades</h1>
          <p>Contenido principal de especialidades.</p>
        </main>
        <footer>Pie de pagina</footer>
      </body>
    </html>
    """

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text=html,
            headers={"content-type": "text/html; charset=utf-8"},
            request=request,
        )

    def robots_fetcher(robots_url: str) -> RobotsFetchResult:
        return RobotsFetchResult(
            url=robots_url, status_code=200, text="User-agent: *\nAllow: /\n"
        )

    settings = Settings(requests_per_second=10, respect_robots_txt=True)
    client = HttpClient(settings, transport=httpx.MockTransport(handler))
    crawler = WebCrawler(
        client,
        settings=settings,
        robots_policy=RobotsPolicy(settings.user_agent, fetcher=robots_fetcher),
    )

    page = crawler.fetch("https://valledellili.org/especialidades")
    client.close()

    assert page.title == "Especialidades de la A a la Z"
    assert "Contenido principal de especialidades." in (page.text_content or "")
    assert "Menu principal" not in (page.text_content or "")


def test_web_crawler_cleans_sede_domain_markdown(monkeypatch) -> None:
    html = """
    <html>
      <head><title>Sede Alfaguara</title></head>
      <body>
        <main>
          <div>
            ### Encuentra lo que necesitas en la Fundación Valle del Lili
            [Preparación para exámenes y procedimientos](/preparacion-para-examenes-y-procedimientos/)
            [Hospital Padrino](/impacto-social/programa-hospital-padrino/)
            [Biblioteca](/educacion/biblioteca/)
            [FVL al día](/fvl-al-dia/)
            [Buscar especialidad](/servicios/)
            [Agenda tu cita](/solicitar-cita-medica/)
            [Especialistas](/directorio-medico/)
          </div>

          # Sede Alfaguara – Fundación Valle del Lili
          [Agenda una cita](/solicitar-cita-medica/)
          Scroll

          ## Excelencia médica más cerca de ti en Jamundí
          Texto base de la sede.

          ## Servicios destacados
          [Ver todos los servicios y especialidades](/servicios/?por_servicio=&by_tag=&sede=sede-alfaguara)
          ### Alergología
          Descripción de la especialidad.
          [Ver especialidad](https://valledellili.org/servicios/alergologia/)

          ## Horarios de atención
          Lunes a viernes: 7:00 a.m. – 6:00 p.m.

          ## Noticias y novedades
          Ruido que no debe quedar.

          ### Autorización datos personales
          Privacidad que no debe quedar.
        </main>
      </body>
    </html>
    """

    class ResponseStub:
        def __init__(self, url: str) -> None:
            self.status_code = 200
            self.text = html
            self.content = html.encode("utf-8")
            self.url = url
            self.headers = {"content-type": "text/html; charset=utf-8"}

        def raise_for_status(self) -> None:
            return None

    def handler(url: str, headers: dict[str, str], timeout: int) -> ResponseStub:
        return ResponseStub(url)

    def robots_fetcher(robots_url: str) -> RobotsFetchResult:
        return RobotsFetchResult(
            url=robots_url, status_code=200, text="User-agent: *\nAllow: /\n"
        )

    monkeypatch.setattr(requests, "get", handler)

    settings = Settings(requests_per_second=10, respect_robots_txt=True)
    client = HttpClient(
        settings,
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, request=request)
        ),
    )
    crawler = WebCrawler(
        client,
        settings=settings,
        robots_policy=RobotsPolicy(settings.user_agent, fetcher=robots_fetcher),
    )

    page = crawler.fetch_domain_page(
        "https://valledellili.org/sedes/sede-alfaguara/",
        DOMAIN_CONFIGS["sedes"],
    )
    client.close()

    markdown = page.text_content or ""

    assert "Encuentra lo que necesitas" not in markdown
    assert "Servicios para ti" not in markdown
    assert "Agenda una cita" not in markdown
    assert "Scroll" not in markdown
    assert "Ver todos los servicios y especialidades" not in markdown
    assert "Ver especialidad" not in markdown
    assert "Noticias y novedades" not in markdown
    assert "Autorización datos personales" not in markdown
    assert "# Sede Alfaguara – Fundación Valle del Lili" in markdown
    assert "## Excelencia médica más cerca de ti en Jamundí" in markdown
    assert "### Alergología" in markdown
    assert "\n\n\n" not in markdown
    assert (
        normalize_title("Directorio Medico | FVL | FVL duplicado")
        == "Directorio Medico"
    )


def test_normalize_title_preserves_title_without_pipe() -> None:
    assert (
        normalize_title("Inicio - Fundacion Valle del Lili")
        == "Inicio - Fundacion Valle del Lili"
    )


def test_normalize_title_inserts_space_between_concatenated_words() -> None:
    # Regex splits at lowercase→uppercase boundary: "LiliFundacion" → "Lili Fundacion"
    assert normalize_title("LiliFundacion") == "Lili Fundacion"


def test_extract_links_returns_same_domain_links() -> None:
    html = """
    <html><body>
      <a href="/quienes-somos">Quienes somos</a>
      <a href="/servicios/hospitalizacion">Hospitalizacion</a>
      <a href="https://valledellili.org/contacto">Contacto absoluto</a>
      <a href="https://otro-sitio.org/pagina">Externo</a>
    </body></html>
    """
    links = extract_links(html, "https://valledellili.org")
    assert "https://valledellili.org/quienes-somos" in links
    assert "https://valledellili.org/servicios/hospitalizacion" in links
    assert "https://valledellili.org/contacto" in links
    assert not any("otro-sitio" in link for link in links)


def test_extract_links_skips_fragments_mailto_and_non_html() -> None:
    html = """
    <html><body>
      <a href="#seccion">Ancla</a>
      <a href="mailto:info@fvl.org.co">Correo</a>
      <a href="/documento.pdf">PDF</a>
      <a href="/imagen.jpg">Imagen</a>
      <a href="/pagina-valida">Pagina valida</a>
    </body></html>
    """
    links = extract_links(html, "https://valledellili.org")
    assert links == ["https://valledellili.org/pagina-valida"]


def test_extract_links_deduplicates_normalized_urls() -> None:
    html = """
    <html><body>
      <a href="/pagina">Primera</a>
      <a href="/pagina">Duplicada</a>
      <a href="/pagina/">Con trailing slash</a>
    </body></html>
    """
    links = extract_links(html, "https://valledellili.org")
    assert links.count("https://valledellili.org/pagina") == 1


def test_extract_links_strips_query_and_fragment() -> None:
    html = """
    <html><body>
      <a href="/buscar?q=cardiologia">Busqueda</a>
      <a href="/pagina#seccion2">Con ancla</a>
    </body></html>
    """
    links = extract_links(html, "https://valledellili.org")
    assert "https://valledellili.org/buscar" in links
    assert "https://valledellili.org/pagina" in links
    assert not any("q=cardiologia" in link for link in links)
    assert not any("#" in link for link in links)


def test_web_crawler_respects_robots_policy() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html></html>", request=request)

    def robots_fetcher(robots_url: str) -> RobotsFetchResult:
        return RobotsFetchResult(
            url=robots_url,
            status_code=200,
            text="User-agent: *\nDisallow: /privado\n",
        )

    settings = Settings(requests_per_second=10, respect_robots_txt=True)
    client = HttpClient(settings, transport=httpx.MockTransport(handler))
    crawler = WebCrawler(
        client,
        settings=settings,
        robots_policy=RobotsPolicy(settings.user_agent, fetcher=robots_fetcher),
    )

    with pytest.raises(CrawlBlockedError):
        crawler.fetch("https://valledellili.org/privado")

    client.close()
