"""
SIPA - Exporta los entregables .docx a PDF para leerlos directo en GitHub.

No usa Word (su automatización se bloquea en esta computadora): convierte cada
.docx a HTML con mammoth (con imágenes y tablas) y Chrome sin ventana lo imprime
a PDF. El formato es más sencillo que el de Word, pero el contenido es el mismo;
para entregar, usar el .docx.

Uso (desde la carpeta del proyecto):
    python scripts/exportar_pdf.py
Salida:
    pdf/*.pdf
"""
import subprocess
import tempfile
from pathlib import Path

import mammoth

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
SALIDA = Path("pdf")

# Los bloques de código (estilo «Codigo» en los .docx) pasan a <pre> para conservar la sangría
MAPA = "p[style-name='Codigo'] => pre:separator('\\n')"

ESTILO = """
<style>
  @page { size: Letter; margin: 2cm 2.2cm; }
  body { font-family: Calibri, "Segoe UI", Arial, sans-serif; font-size: 11pt; line-height: 1.4; color: #222; }
  h1, h2, h3 { color: #1f3a5f; page-break-after: avoid; }
  h1 { font-size: 17pt; margin-top: 1.2em; } h2 { font-size: 14pt; } h3 { font-size: 12pt; }
  table { border-collapse: collapse; width: 100%; margin: .6em 0 1em; font-size: 9.5pt; page-break-inside: auto; }
  td, th { border: 1px solid #999; padding: 3px 5px; vertical-align: top; }
  tr { page-break-inside: avoid; }
  tr:first-child td { background: #d9e2ec; font-weight: bold; }
  img { max-width: 100%; height: auto; display: block; margin: .5em auto; }
  p { margin: .35em 0; }
  pre { font-family: Consolas, monospace; font-size: 8pt; background: #f5f7fa; border: 1px solid #dde3ea;
        padding: 6px 8px; white-space: pre-wrap; page-break-inside: auto; }
</style>
"""


def main():
    SALIDA.mkdir(exist_ok=True)
    docs = sorted(p for p in Path(".").glob("*.docx")
                  if p.name.startswith(("avance", "entregable")) and not p.name.startswith("~$"))
    with tempfile.TemporaryDirectory() as tmp:
        for d in docs:
            with d.open("rb") as f:
                html = mammoth.convert_to_html(f, style_map=MAPA).value
            pagina = Path(tmp) / f"{d.stem}.html"
            pagina.write_text(f"<!doctype html><html lang='es'><head><meta charset='utf-8'>"
                              f"<title>{d.stem}</title>{ESTILO}</head><body>{html}</body></html>",
                              encoding="utf-8")
            pdf = (SALIDA / f"{d.stem}.pdf").resolve()
            subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                            f"--print-to-pdf={pdf}", pagina.resolve().as_uri()],
                           check=True, capture_output=True, timeout=120)
            print(f"{d.name:50} -> {pdf.stat().st_size / 1024:,.0f} KB")


if __name__ == "__main__":
    main()
