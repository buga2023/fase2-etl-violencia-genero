# -*- coding: utf-8 -*-
"""
build.py - monta o relatorio da Fase 3 em um unico PDF.

O que faz, em ordem:
  1. copia as figuras geradas em figuras/ para esta pasta, para que o HTML as encontre;
  2. injeta a base.css e o caminho das fontes no portrait.html;
  3. renderiza o HTML com o Chromium headless, uma pagina por secao;
  4. junta as paginas com o pypdf no PDF final.

Uso:
    python relatorio/build.py                 # usa relatorio/manifest.json
    python relatorio/build.py outro_manifest.json

Dependencias: playwright com chromium, pypdf. Veja requirements.txt.
Se o Chromium nao estiver no caminho padrao, aponte a variavel CHROMIUM_BIN.
"""
import json, re, sys, os, shutil
from pathlib import Path
from playwright.sync_api import sync_playwright
from pypdf import PdfReader, PdfWriter

AQUI = Path(__file__).resolve().parent
FONTS_DIR = AQUI.parent / "relatorio" / "fonts"
BASE_CSS = AQUI / "base.css"
FIGURAS = AQUI.parent.parent / "figuras"


def copiar_figuras(destino):
    if FIGURAS.exists():
        for png in FIGURAS.glob("*.png"):
            shutil.copy(png, destino / png.name)


def resolve(html, base_css):
    if "/*__BASE__*/" in html:
        html = html.replace("/*__BASE__*/", base_css)
    html = html.replace("__FONTS__", FONTS_DIR.as_uri())
    return html


def main(manifest_path):
    mpath = Path(manifest_path).resolve()
    root = mpath.parent
    m = json.loads(mpath.read_text(encoding="utf-8"))
    copiar_figuras(root)

    base_css = BASE_CSS.read_text(encoding="utf-8").replace("__FONTS__", FONTS_DIR.as_uri())
    sources = m["sources"]
    rendered = {}
    chrome = os.environ.get("CHROMIUM_BIN", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
    with sync_playwright() as p:
        b = (p.chromium.launch(executable_path=chrome) if Path(chrome).exists()
             else p.chromium.launch())
        pg = b.new_page()
        for key, rel in sources.items():
            html = resolve((root / rel).read_text(encoding="utf-8"), base_css)
            final = root / f"_{key}_final.html"
            final.write_text(html, encoding="utf-8")
            out = root / f"_{key}.pdf"
            pg.goto(final.as_uri()); pg.wait_for_timeout(400)
            pg.pdf(path=str(out), prefer_css_page_size=True, print_background=True)
            rendered[key] = PdfReader(str(out))
        b.close()

    for k, r in rendered.items():
        print(f"  {k}: {len(r.pages)} pagina(s)")

    order = m.get("order") or [[k, i] for k in sources for i in range(len(rendered[k].pages))]
    w = PdfWriter()
    for key, idx in order:
        w.add_page(rendered[key].pages[idx])
    w.add_metadata({f"/{k.capitalize()}": v for k, v in m.get("metadata", {}).items()})
    out_path = root / m["output"]
    with open(out_path, "wb") as f:
        w.write(f)
    print(f"PDF final -> {out_path}  ({len(w.pages)} paginas)")
    return str(out_path)


if __name__ == "__main__":
    mani = sys.argv[1] if len(sys.argv) > 1 else str(AQUI / "manifest.json")
    main(mani)
