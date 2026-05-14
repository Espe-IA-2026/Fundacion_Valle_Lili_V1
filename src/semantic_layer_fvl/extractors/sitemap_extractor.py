"""Extractor de URLs desde archivos sitemap XML de dominios configurados.

Si los sitemaps no existen o no devuelven URLs válidas, el extractor cae en un
mecanismo de descubrimiento que descarga las páginas de fallback y extrae todos
los enlaces internos que cumplan los filtros del dominio. Esto garantiza que el
pipeline siempre rastrea páginas individuales (e.g. ``/servicios/cardiologia/``)
en lugar de quedarse solo en la página de listado.
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from typing import TYPE_CHECKING
from urllib.parse import urljoin, urlsplit

import requests
from bs4 import BeautifulSoup

if TYPE_CHECKING:
    from semantic_layer_fvl.domains import DomainConfig

logger = logging.getLogger(__name__)

_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
}

_SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def fetch_domain_urls(base_url: str, config: DomainConfig) -> list[str]:
    """Devuelve las URLs filtradas del sitemap XML de un dominio configurado.

    Orden de prioridad:
    1. Sitemap XML configurado en ``config.sitemap_paths``.
    2. Descubrimiento de enlaces desde las páginas de fallback (BFS de nivel 1).
    3. Las propias ``config.fallback_urls`` como último recurso.

    Args:
        base_url: URL base del sitio (sin barra final).
        config: Configuración del dominio con rutas de sitemap y filtros de URL.

    Returns:
        Lista de URLs absolutas que superaron los filtros de inclusión/exclusión.
    """
    base = base_url.rstrip("/")
    for path in config.sitemap_paths:
        urls = _parse_sitemap(f"{base}/{path}")
        if not urls:
            logger.debug("[sitemap] %s/%s returned no URLs", base, path)
            continue
        filtered = _apply_filters(urls, config)
        logger.info("[sitemap] %s → %d URLs after filtering", path, len(filtered))
        if filtered:
            return filtered
        logger.debug("[sitemap] %s → all %d URLs excluded by filters", path, len(urls))

    # Sitemap no disponible — intentar descubrimiento desde las páginas de fallback
    discovered = _discover_urls_from_pages(config.fallback_urls, base_url, config)
    if discovered:
        logger.info(
            "[sitemap] Descubiertas %d URLs desde páginas de fallback para dominio '%s'",
            len(discovered),
            config.name,
        )
        return discovered

    # Último recurso: devolver las fallback_urls tal cual
    logger.warning(
        "[sitemap] Sitemap y descubrimiento fallaron para '%s' — usando %d fallback URL(s)",
        config.name,
        len(config.fallback_urls),
    )
    return list(config.fallback_urls)


def _discover_urls_from_pages(
    seed_urls: list[str],
    base_url: str,
    config: DomainConfig,
) -> list[str]:
    """Descarga las seed_urls y extrae todos los enlaces internos que cumplan los filtros.

    Realiza un BFS de nivel 1: solo sigue los enlaces directos de las seeds,
    sin profundizar más. Excluye las propias seeds del resultado para evitar
    re-rastrear páginas de listado como si fueran contenido.

    Args:
        seed_urls: URLs de las páginas de listado a analizar.
        base_url: URL base del sitio para validar que los enlaces sean internos.
        config: Configuración del dominio con filtros de inclusión/exclusión.

    Returns:
        Lista de URLs individuales filtradas, sin duplicados, listas para rastrear.
    """
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    base_netloc = urlsplit(base_url).netloc.lower()
    discovered: set[str] = set()

    for seed in seed_urls:
        try:
            resp = requests.get(
                seed,
                headers=_BROWSER_HEADERS,
                timeout=20,
                verify=False,  # Algunos servidores tienen certificados autofirmados
            )
            if resp.status_code != 200:
                logger.debug("[sitemap] discover: %s → HTTP %d", seed, resp.status_code)
                continue

            soup = BeautifulSoup(resp.content, "html.parser")
            for a_tag in soup.find_all("a", href=True):
                href = str(a_tag["href"]).strip()
                if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
                    continue

                full_url = urljoin(seed, href).split("?")[0].split("#")[0].rstrip("/")
                parsed = urlsplit(full_url)

                if parsed.scheme not in {"http", "https"}:
                    continue
                if parsed.netloc.lower() != base_netloc:
                    continue
                if not parsed.path or parsed.path == "/":
                    continue

                discovered.add(full_url)

            logger.debug(
                "[sitemap] discover: %d enlaces encontrados en '%s'",
                len(discovered),
                seed,
            )

        except Exception as exc:  # noqa: BLE001
            logger.debug("[sitemap] discover: error al procesar '%s': %s", seed, exc)

    # Aplicar filtros del dominio y excluir las seeds para no re-rastrear listados
    filtered = _apply_filters(list(discovered), config)
    seeds_normalized = {u.rstrip("/") for u in seed_urls}
    result = [u for u in filtered if u.rstrip("/") not in seeds_normalized]
    return result


def _parse_sitemap(url: str) -> list[str]:
    """Descarga y parsea un sitemap XML, devolviendo la lista de ``<loc>`` encontradas.

    Usa ``verify=False`` para evitar fallos silenciosos en servidores con
    certificados auto-firmados o cadenas SSL incompletas (misma estrategia que
    ``WebCrawler.fetch_domain_page``). Las advertencias de urllib3 se suprimen
    para mantener la salida del pipeline limpia.
    """
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    try:
        resp = requests.get(url, headers=_BROWSER_HEADERS, timeout=20, verify=False)
        if resp.status_code != 200:
            logger.debug("[sitemap] %s → HTTP %d", url, resp.status_code)
            return []
        root = ET.fromstring(resp.content)
        locs = root.findall(".//sm:url/sm:loc", _SITEMAP_NS)
        urls = [loc.text.strip() for loc in locs if loc.text]
        logger.debug("[sitemap] %s → %d URLs en el sitemap", url, len(urls))
        return urls
    except requests.RequestException as exc:
        logger.debug("[sitemap] Network error for %s: %s", url, exc)
        return []
    except ET.ParseError as exc:
        logger.debug("[sitemap] XML parse error for %s: %s", url, exc)
        return []


def _apply_filters(urls: list[str], config: DomainConfig) -> list[str]:
    """Aplica los filtros de inclusión y exclusión del dominio a la lista de URLs."""
    result: list[str] = []
    for url in urls:
        if config.url_include_patterns and not any(
            p in url for p in config.url_include_patterns
        ):
            continue
        if any(p in url for p in config.url_exclude_patterns):
            continue
        result.append(url)
    return result
