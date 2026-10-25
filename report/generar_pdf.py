"""Genera documento_diseno.pdf a partir de documento_diseno.html con Chromium (Playwright).

Uso:
    python report/generar_pdf.py
Si Playwright no tiene su navegador descargado: `playwright install chromium`, o definir
BROWSER_PATH con la ruta de un Chrome/Chromium instalado.
"""

import os
from pathlib import Path

from playwright.sync_api import sync_playwright

AQUI = Path(__file__).resolve().parent

with sync_playwright() as p:
    navegador = p.chromium.launch(executable_path=os.environ.get("BROWSER_PATH") or None)
    pagina = navegador.new_page()
    pagina.goto((AQUI / "documento_diseno.html").as_uri())
    pagina.wait_for_load_state("networkidle")
    pagina.pdf(
        path=str(AQUI / "documento_diseno.pdf"),
        format="Letter",
        print_background=True,
        prefer_css_page_size=True,
        display_header_footer=True,
        header_template="<span></span>",
        footer_template='<div style="font-size:8px;color:#898781;width:100%;text-align:center">'
        'Laboratorio 10 · Documento de diseño · <span class="pageNumber"></span>/<span class="totalPages"></span></div>',
    )
    navegador.close()
print(AQUI / "documento_diseno.pdf")
