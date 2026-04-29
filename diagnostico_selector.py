"""
Diagnóstico de selector HTML para páginas del sitio valledellili.org.

Ejecutar desde la raíz del proyecto:
    python diagnostico_selector.py

Imprime los contenedores candidatos y una vista previa del texto
que capturaría cada selector alternativo.
"""
from __future__ import annotations

import re
import sys

import requests
from bs4 import BeautifulSoup

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache",
}

NOISE_SELECTOR = (
    "nav, footer, header, aside, script, style, noscript, iframe, hr, "
    "figure, svg, img, "
    ".cnt_breadcrumbs, .social-share, "
    ".elementor-location-header, .elementor-location-footer"
)

CANDIDATE_SELECTORS = [
    "main",
    "article",
    "[role='main']",
    "#content",
    "#main",
    "#primary",
    ".site-content",
    ".site-main",
    ".entry-content",
    ".post-content",
    ".page-content",
    ".content-block",
    ".content-post",
    ".ma-content",
    ".ml-main-container",
    "section.personal-sfaff-lite",
    ".elementor-widget-theme-post-content",
    ".wp-block-group",
    "div.content-block",
]

TEST_URLS = {
    "especialistas_perfil": "https://valledellili.org/directorio-medico/adolfo-leon-de-la-hoz-alban/",
    "especialistas_listado": "https://valledellili.org/directorio-medico/",
    "institucional_principal": "https://valledellili.org/nuestra-institucion/",
    "institucional_quienes": "https://valledellili.org/nuestra-institucion/quienes-somos/",
    "institucional_historia": "https://valledellili.org/nuestra-institucion/historia/",
}


def _clean(soup: BeautifulSoup) -> BeautifulSoup:
    for tag in soup.select(NOISE_SELECTOR):
        tag.decompose()
    return soup


def _preview(text: str, chars: int = 150) -> str:
    collapsed = re.sub(r"\s+", " ", text).strip()
    return collapsed[:chars] + ("…" if len(collapsed) > chars else "")


def diagnose(label: str, url: str) -> None:
    print(f"\n{'=' * 70}")
    print(f"[{label}]  {url}")
    print("=" * 70)

    try:
        r = requests.get(url, headers=BROWSER_HEADERS, timeout=30)
        r.raise_for_status()
    except Exception as exc:
        print(f"  ERROR al descargar: {exc}")
        return

    soup_raw = BeautifulSoup(r.content, "html.parser")

    # ── Título real de la página ────────────────────────────────────────────
    h1 = soup_raw.find("h1")
    title_tag = soup_raw.find("title")
    print(f"\n  <h1>  : {h1.get_text(strip=True)[:100] if h1 else '(none)'}")
    print(f"  <title>: {title_tag.get_text(strip=True)[:100] if title_tag else '(none)'}")

    # ── Clases únicas de contenedores relevantes ────────────────────────────
    kw = ["content", "main", "post", "article", "single", "doctor", "medico",
          "profile", "especialista", "entry", "page", "container", "wrapper",
          "team", "staff", "bio", "elementor", "ml-", "ma-"]
    seen: set[str] = set()
    matches: list[str] = []
    for tag in soup_raw.find_all(["div", "article", "section", "main"], class_=True):
        cls = " ".join(tag.get("class", []))
        key = cls[:120]
        if key in seen:
            continue
        seen.add(key)
        if any(k in cls.lower() for k in kw):
            matches.append(f"  <{tag.name} class='{cls[:100]}'>")

    print(f"\n  Contenedores candidatos ({len(matches)} únicos):")
    for m in matches[:30]:
        print(m)

    # ── Prueba de selectores ────────────────────────────────────────────────
    print("\n  Selectores → palabras capturadas (tras limpieza):")
    soup_clean = _clean(BeautifulSoup(r.content, "html.parser"))

    best = ("—", 0, "")
    for sel in CANDIDATE_SELECTORS:
        node = soup_clean.select_one(sel)
        if node is None:
            print(f"    {sel:<50} → NO ENCONTRADO")
        else:
            txt = node.get_text(separator=" ", strip=True)
            words = len(re.findall(r"\w{3,}", txt))
            preview = _preview(txt)
            print(f"    {sel:<50} → {words:>4} palabras | {preview!r}")
            if words > best[1]:
                best = (sel, words, preview)

    print(f"\n  *** MEJOR SELECTOR: '{best[0]}' con {best[1]} palabras ***")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        for u in sys.argv[1:]:
            diagnose("custom", u)
    else:
        for label, url in TEST_URLS.items():
            diagnose(label, url)
    print("\n\nDiagnóstico completado.")
