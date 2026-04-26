"""
scraper/fvl_scraper.py — Fase 1

Extrae contenido de valledellili.org usando Selenium + BeautifulSoup + requests.
Salida: data/knowledge_base.json (lista de chunks con metadatos).

Uso:
    python scraper/fvl_scraper.py
    python scraper/fvl_scraper.py --max-pages 50
    python scraper/fvl_scraper.py --no-headless   # ver el browser en acción
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from pydantic import AnyHttpUrl, TypeAdapter
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# ── Configuración de rutas ───────────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))
load_dotenv(_ROOT / ".env")

import os

# Importaciones del proyecto (reutilización de Fase 0)
from semantic_layer_fvl.processors.chunker import TextChunker
from semantic_layer_fvl.processors.cleaner import TextCleaner
from semantic_layer_fvl.processors.structurer import SemanticStructurer
from semantic_layer_fvl.writers.markdown_writer import MarkdownWriter
from semantic_layer_fvl.schemas.documents import RawPage, ExtractionMetadata
from semantic_layer_fvl.config.settings import get_settings


# ── Configuración ────────────────────────────────────────────────────────────
BASE_URL: str = os.getenv("TARGET_BASE_URL", "https://valledellili.org")
OUTPUT_PATH: Path = Path(
    os.getenv("DATA_OUTPUT_PATH", str(_ROOT / "data" / "knowledge_base.json"))
)
REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "30"))
HEADLESS_DEFAULT: bool = os.getenv("HEADLESS", "true").lower() == "true"

RATE_LIMIT_SECONDS: float = 2.0  # pausa entre páginas (ser amigable con el servidor)
JS_WAIT_SECONDS: float = 2.5  # espera para que el JS renderice
MAX_PAGES_DEFAULT: int = 80  # cap de seguridad
MAX_RETRIES: int = 2

# ── Extensiones a ignorar ─────────────────────────────────────────────────────
_SKIP_EXTENSIONS = {
    ".pdf",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".svg",
    ".webp",
    ".mp4",
    ".mp3",
    ".avi",
    ".zip",
    ".rar",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
}

# ── Mapeo URL → categoría (espejo de structurer.py) ─────────────────────────
_PATH_RULES: list[tuple[str, str]] = [
    ("/nuestra-institucion/nuestras-sedes", "04_sedes_ubicaciones"),
    ("/nuestra-institucion/marco-legal", "06_normatividad"),
    ("/nuestra-institucion", "01_organizacion"),
    ("/especialidades", "02_servicios"),
    ("/servicios", "02_servicios"),
    ("/directorio-medico", "03_talento_humano"),
    ("/sedes", "04_sedes_ubicaciones"),
    ("/contactanos", "05_contacto"),
    ("/contacto", "05_contacto"),
    ("/normatividad", "06_normatividad"),
    ("/investigacion", "07_investigacion"),
    ("/educacion", "08_educacion"),
    ("/noticias-y-eventos", "09_noticias"),
    ("/noticias", "09_noticias"),
    ("/publicaciones", "09_noticias"),
    ("/blog", "09_noticias"),
    ("/videos", "10_multimedia"),
]

_KEYWORD_RULES: list[tuple[list[str], str]] = [
    (
        ["mision", "vision", "historia", "quienes-somos", "institucion"],
        "01_organizacion",
    ),
    (
        ["servicio", "especialidad", "consulta", "tratamiento", "programa"],
        "02_servicios",
    ),
    (
        ["doctor", "medico", "especialista", "directorio", "talento"],
        "03_talento_humano",
    ),
    (
        ["sede", "ubicacion", "direccion", "instalacion", "campus"],
        "04_sedes_ubicaciones",
    ),
    (["contacto", "telefono", "correo", "comunicacion", "pqrs"], "05_contacto"),
    (
        ["politica", "derechos", "normatividad", "ley", "legal", "marco"],
        "06_normatividad",
    ),
    (
        ["investigacion", "ensayo", "cientifico", "estudio", "clinico"],
        "07_investigacion",
    ),
    (["educacion", "curso", "formacion", "postgrado", "residencia"], "08_educacion"),
    (["noticia", "boletin", "evento", "actualidad", "novedad"], "09_noticias"),
    (["video", "youtube", "multimedia", "galeria", "foto"], "10_multimedia"),
]


def infer_category(url: str, title: str = "") -> str:
    """Infiere la categoría de una URL usando las mismas reglas que structurer.py."""
    path = urlparse(url).path.rstrip("/").lower()

    for prefix, category in _PATH_RULES:
        if path.startswith(prefix):
            return category

    combined = (path + " " + title).lower()
    for keywords, category in _KEYWORD_RULES:
        if any(kw in combined for kw in keywords):
            return category

    return "01_organizacion"


# ── Selenium ──────────────────────────────────────────────────────────────────
def build_driver(headless: bool = True) -> webdriver.Chrome:
    """Construye un Chrome driver con webdriver-manager."""
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--lang=es-CO")
    opts.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=opts)


# ── Extracción de contenido ───────────────────────────────────────────────────
def extract_content(html: str) -> tuple[str, str]:
    """Extrae (título, texto_principal) del HTML usando BeautifulSoup.

    Prioriza <main> y <article>; elimina nav/footer/scripts antes de extraer.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Título: prefiere og:title, luego <title>
    title = ""
    og = soup.find("meta", property="og:title")
    og_content_raw = og.get("content") if og else ""
    if isinstance(og_content_raw, str):
        og_content = og_content_raw.strip()
    elif isinstance(og_content_raw, list):
        og_content = " ".join(str(v) for v in og_content_raw).strip()
    else:
        og_content = ""
    if og_content:
        title = og_content
    elif soup.title and soup.title.string:
        title = soup.title.string.strip()
    # Limpia el sufijo del sitio (ej. "Servicios – Fundación Valle del Lili")
    if "–" in title:
        title = title.split("–")[0].strip()
    elif " - " in title:
        title = title.split(" - ")[0].strip()

    # Eliminar elementos de ruido antes de extraer texto
    for tag in soup(
        [
            "script",
            "style",
            "nav",
            "footer",
            "header",
            "aside",
            "form",
            "noscript",
            "iframe",
            "button",
            "svg",
            "figure",
        ]
    ):
        tag.decompose()

    # Extraer contenido principal en orden de preferencia
    content = (
        soup.find("main")
        or soup.find("article")
        or soup.find(id="content")
        or soup.find(id="main-content")
        or soup.find(class_=lambda c: bool(c and "content" in c.lower()))
        or soup.find("body")
    )

    text = content.get_text(separator="\n", strip=True) if content else ""
    return title, text


def is_internal(url: str) -> bool:
    """Verifica que la URL pertenece al dominio objetivo."""
    host = urlparse(url).netloc
    base_host = urlparse(BASE_URL).netloc
    return host == base_host or host == ""


def should_skip_url(url: str) -> bool:
    """True si la URL apunta a un archivo binario o debe ignorarse."""
    path = urlparse(url).path.lower()
    return any(path.endswith(ext) for ext in _SKIP_EXTENSIONS)


def discover_links(html: str, current_url: str) -> list[str]:
    """Extrae y normaliza todos los links internos del HTML."""
    soup = BeautifulSoup(html, "html.parser")
    links: list[str] = []
    for a in soup.find_all("a", href=True):
        href_raw = a.get("href", "")
        if isinstance(href_raw, str):
            href = href_raw.strip()
        elif isinstance(href_raw, list):
            href = " ".join(str(v) for v in href_raw).strip()
        else:
            href = str(href_raw).strip()

        if not href:
            continue
        if any(href.startswith(p) for p in ("#", "mailto:", "tel:", "javascript:")):
            continue
        full = urljoin(current_url, href).split("#")[0].split("?")[0]
        if is_internal(full) and not should_skip_url(full):
            links.append(full)
    return list(dict.fromkeys(links))  # deduplicar preservando orden


# ── Pipeline principal ────────────────────────────────────────────────────────
def run_scraper(driver: webdriver.Chrome, max_pages: int) -> int:
    """Ejecuta el scraping y escribe archivos .md enriquecidos. Devuelve el nº de docs escritos."""
    settings = get_settings()
    cleaner = TextCleaner()
    structurer = SemanticStructurer()
    writer = MarkdownWriter(settings)
    # Ya no necesitamos TextChunker aquí — SemanticStructurer estructura el contenido

    seed_urls = [
        f"{BASE_URL}/",
        f"{BASE_URL}/nuestra-institucion",
        f"{BASE_URL}/servicios",
        f"{BASE_URL}/especialidades",
        f"{BASE_URL}/directorio-medico",
        f"{BASE_URL}/nuestra-institucion/nuestras-sedes",
        f"{BASE_URL}/contactanos",
        f"{BASE_URL}/nuestra-institucion/marco-legal",
        f"{BASE_URL}/investigacion",
        f"{BASE_URL}/educacion",
        f"{BASE_URL}/noticias-y-eventos",
    ]

    queue: deque[str] = deque(seed_urls)
    visited: set[str] = set(seed_urls)
    docs_written = 0
    page_count = 0

    while queue and page_count < max_pages:
        url = queue.popleft()
        page_count += 1
        logging.info("[%d/%d] %s", page_count, max_pages, url)

        html: str | None = None

        # 1. Selenium (JS rendering)
        for attempt in range(MAX_RETRIES + 1):
            try:
                driver.get(url)
                time.sleep(JS_WAIT_SECONDS)
                html = driver.page_source
                break
            except Exception as exc:
                logging.warning("  Selenium intento %d falló: %s", attempt + 1, exc)
                if attempt < MAX_RETRIES:
                    time.sleep(2**attempt)

        # 2. Fallback requests
        if not html:
            try:
                resp = requests.get(
                    url,
                    timeout=REQUEST_TIMEOUT,
                    headers={
                        "User-Agent": "Mozilla/5.0 (compatible; FVL-Scraper/1.0)",
                        "Accept-Language": "es-CO,es;q=0.9",
                    },
                )
                resp.raise_for_status()
                html = resp.text
            except Exception as exc:
                logging.warning("  requests falló: %s — omitiendo", exc)
                time.sleep(RATE_LIMIT_SECONDS)
                continue

        # 3. Extraer contenido
        page_title, raw_text = extract_content(html)
        cleaned = cleaner.clean(raw_text)

        if not cleaned:
            time.sleep(RATE_LIMIT_SECONDS)
            continue

        # 4. Construir RawPage → ProcessedDocument → escribir .md
        validated_source_url = TypeAdapter(AnyHttpUrl).validate_python(url)
        raw_page = RawPage(
            url=validated_source_url,
            title=page_title or url,
            html=html,
            text_content=cleaned,
            metadata=ExtractionMetadata(
                source_url=validated_source_url,
                source_name="Fundacion Valle del Lili",
                extractor_name="fvl_selenium_scraper",
            ),
        )

        processed = structurer.build_document(raw_page, cleaned)
        output_path = writer.write(processed)
        docs_written += 1

        logging.info(
            "  ✓ '%s' → %s [%s]",
            processed.document.title[:60],
            output_path.name,
            processed.document.category.value,
        )

        # 5. Descubrir links (BFS)
        for link in discover_links(html, url):
            if link not in visited:
                visited.add(link)
                queue.append(link)

        time.sleep(RATE_LIMIT_SECONDS)

    return docs_written


# ── Punto de entrada ──────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description="Scraper FVL — Fase 1")
    parser.add_argument(
        "--max-pages",
        type=int,
        default=MAX_PAGES_DEFAULT,
        help=f"Máximo de páginas a scrapear (default: {MAX_PAGES_DEFAULT})",
    )
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Abrir el browser visible (útil para depuración)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(_ROOT / "data" / "scraper.log", encoding="utf-8"),
        ],
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    headless = HEADLESS_DEFAULT and not args.no_headless
    logging.info("Modo headless: %s", headless)

    driver = build_driver(headless=headless)
    try:
        docs_written = run_scraper(driver, max_pages=args.max_pages)
        logging.info("Scraping finalizado: %d documentos escritos", docs_written)
        results = run_scraper(driver, max_pages=args.max_pages)
    finally:
        driver.quit()

    # ── Resumen final ────────────────────────────────────────────
    knowledge_dir = _ROOT / "knowledge"
    md_files = list(knowledge_dir.rglob("*.md")) if knowledge_dir.exists() else []
    cats: dict[str, int] = {}
    for f in md_files:
        if f.name != ".gitkeep":
            cats[f.parent.name] = cats.get(f.parent.name, 0) + 1

    logging.info("=" * 60)
    logging.info("SCRAPING COMPLETADO")
    logging.info("Documentos escritos: %d", docs_written)
    logging.info("Archivos .md en knowledge/: %d", len(md_files))
    logging.info("Distribución por categoría:")
    for cat, count in sorted(cats.items()):
        logging.info("  %-35s %d docs", cat, count)


if __name__ == "__main__":
    main()
