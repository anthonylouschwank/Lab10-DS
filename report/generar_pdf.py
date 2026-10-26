"""Genera documento_diseno.pdf a partir de documento_diseno.html con Chromium (Playwright).

Uso:
    python report/generar_pdf.py

La portada se imprime sin pie de pagina; el resto del documento lleva la referencia al
repositorio y el numero de pagina. Si Playwright no tiene su navegador descargado:
`playwright install chromium`, o definir BROWSER_PATH con la ruta de un Chrome/Chromium.
"""

import io
import os
from pathlib import Path

from playwright.sync_api import sync_playwright
from pypdf import PdfReader, PdfWriter

AQUI = Path(__file__).resolve().parent
SALIDA = AQUI / "documento_diseno.pdf"

PIE = (
    '<div style="width:100%;font-family:sans-serif;font-size:7.5px;color:#6b6a66;'
    'padding:0 19mm;display:flex;justify-content:space-between">'
    "<span>Observatorio de Turismo Sostenible · Documento de diseño del tablero</span>"
    "<span>github.com/anthonylouschwank/Lab10-DS</span>"
    '<span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>'
)


def imprimir(pagina, con_pie: bool) -> bytes:
    return pagina.pdf(
        format="Letter",
        print_background=True,
        prefer_css_page_size=True,
        display_header_footer=con_pie,
        header_template="<span></span>",
        footer_template=PIE if con_pie else "<span></span>",
    )


with sync_playwright() as p:
    navegador = p.chromium.launch(executable_path=os.environ.get("BROWSER_PATH") or None)
    pagina = navegador.new_page()
    pagina.goto((AQUI / "documento_diseno.html").as_uri())
    pagina.wait_for_load_state("networkidle")
    pagina.evaluate("document.fonts.ready")
    sin_pie = PdfReader(io.BytesIO(imprimir(pagina, False)))
    con_pie = PdfReader(io.BytesIO(imprimir(pagina, True)))
    navegador.close()

documento = PdfWriter()
documento.add_page(sin_pie.pages[0])
for hoja in con_pie.pages[1:]:
    documento.add_page(hoja)
documento.add_metadata({"/Title": "Observatorio de Turismo Sostenible · Documento de diseño del tablero", "/Author": "Equipo Lab10-DS"})
with open(SALIDA, "wb") as f:
    documento.write(f)
print(SALIDA)
