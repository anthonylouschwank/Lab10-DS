"""Genera Informe_Lab11.pdf a partir de informe_lab11.html con Chromium (Playwright).

Uso:
    python report/lab11/capturas.py tablero estimaciones_vigente   # capturas (servicios levantados)
    python report/lab11/capturas.py mlflow
    python report/lab11/generar_informe.py

Igual que report/generar_pdf.py: la portada sin pie de pagina y el resto con el numero de pagina.
Si Playwright no tiene su navegador: `playwright install chromium`, o BROWSER_PATH con un Chrome.
"""

import io
import os
from pathlib import Path

from playwright.sync_api import sync_playwright
from pypdf import PdfReader, PdfWriter

AQUI = Path(__file__).resolve().parent
SALIDA = AQUI / "Informe_Lab11.pdf"

PIE = (
    '<div style="width:100%;font-family:IBM Plex Sans,sans-serif;font-size:7.5px;color:#6f6f6f;'
    'padding:0 18mm;display:flex;justify-content:space-between">'
    "<span>Laboratorio 11 - MLOps aplicado al observatorio</span>"
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
    pagina.goto((AQUI / "informe_lab11.html").as_uri())
    pagina.wait_for_load_state("networkidle")
    pagina.evaluate("document.fonts.ready")
    sin_pie = PdfReader(io.BytesIO(imprimir(pagina, False)))
    con_pie = PdfReader(io.BytesIO(imprimir(pagina, True)))
    navegador.close()

documento = PdfWriter()
documento.add_page(sin_pie.pages[0])
for hoja in con_pie.pages[1:]:
    documento.add_page(hoja)
documento.add_metadata({"/Title": "Laboratorio 11 - MLOps aplicado al observatorio", "/Author": "Equipo Lab10-DS, grupo 3"})
with open(SALIDA, "wb") as f:
    documento.write(f)
print(SALIDA)
