"""
Diagnóstico de selector HTML para páginas de directorio-medico.

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
    "div.content-post",
    "article",
    "main",
    "[role='main']",
    ".elementor-widget-theme-post-content",
    ".entry-content",
    ".post-content",
    ".site-main",
    "#content",
    "#main",
    ".page-content",
    ".single-content",
    ".doctor-profile",
    ".team-member",
    ".elementor-section",
]

TEST_URLS = [
    "https://valledellili.org/directorio-medico/adolfo-leon-de-la-hoz-alban/",
    "https://valledellili.org/directorio-medico/",
]


def _clean(soup: BeautifulSoup) -> BeautifulSoup:
    for tag in soup.select(NOISE_SELECTOR):
        tag.decompose()
    return soup


def _preview(text: str, chars: int = 200) -> str:
    collapsed = re.sub(r"\s+", " ", text).strip()
    return collapsed[:chars] + ("…" if len(collapsed) > chars else "")


def diagnose(url: str) -> None:
    print(f"\n{'=' * 70}")
    print(f"URL: {url}")
    print("=" * 70)

    try:
        r = requests.get(url, headers=BROWSER_HEADERS, timeout=30)
        r.raise_for_status()
    except Exception as exc:
        print(f"  ERROR al descargar: {exc}")
        return

    soup = BeautifulSoup(r.content, "html.parser")

    # ── 1. IDs disponibles ──────────────────────────────────────────────────
    ids = [(t.name, t["id"]) for t in soup.find_all(id=True)]
    print(f"\n[IDs en la página ({len(ids)} total)]")
    for name, id_ in ids[:30]:
        print(f"  <{name} id='{id_}'>")

    # ── 2. Clases únicas de contenedores ────────────────────────────────────
    kw = ["content", "main", "post", "article", "single", "doctor", "medico",
          "profile", "especialista", "entry", "page", "container", "wrapper",
          "team", "staff", "bio", "physician", "elementor"]
    seen: set[str] = set()
    matches: list[str] = []
    for tag in soup.find_all(["div", "article", "section", "main"], class_=True):
        cls = " ".join(tag.get("class", []))
        key = cls[:120]
        if key in seen:
            continue
        seen.add(key)
        if any(k in cls.lower() for k in kw):
            matches.append(f"  <{tag.name} class='{cls[:100]}'>")

    print(f"\n[Contenedores con clases relevantes ({len(matches)} únicos)]")
    for m in matches[:40]:
        print(m)

    # ── 3. Prueba de selectores candidatos ──────────────────────────────────
    print("\n[Prueba de selectores — texto capturado tras limpieza]")
    soup_clean = _clean(BeautifulSoup(r.content, "html.parser"))

    for sel in CANDIDATE_SELECTORS:
        node = soup_clean.select_one(sel)
        if node is None:
            print(f"  {sel:<45} → NO ENCONTRADO")
        else:
            txt = node.get_text(separator=" ", strip=True)
            words = len(re.findall(r"\w{3,}", txt))
            print(f"  {sel:<45} → {words:>4} palabras | {_preview(txt, 120)!r}")


if __name__ == "__main__":
    urls = sys.argv[1:] if len(sys.argv) > 1 else TEST_URLS
    for u in urls:
        diagnose(u)
    print("\nDiagnóstico completado.")
    print("Comparte este output para identificar el selector correcto.")
