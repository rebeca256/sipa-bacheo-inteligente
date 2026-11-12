"""
SIPA - Construye el sitio de GitHub Pages (carpeta docs/) con el tablero.

El tablero corre en el navegador con stlite (Streamlit sobre Pyodide), sin
servidor: GitHub Pages solo sirve archivos. Usa la copia de solo consulta de
tablero/datos/ (generarla antes con scripts/exportar_datos_tablero.py).

Uso (desde la carpeta del proyecto):
    python scripts/exportar_datos_tablero.py
    python scripts/construir_sitio.py
Probar en local:
    python -m http.server 8000 --directory docs     ->  http://localhost:8000
"""
import json
import shutil
from pathlib import Path

ORIGEN = Path("tablero")
SITIO = Path("docs")
STLITE = "1.12.1"

PAGINA = """<!doctype html>
<html lang="es">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no" />
    <title>SIPA · Sistema Inteligente de Priorización Asfáltica</title>
    <meta name="description" content="Prototipo funcional de SIPA: priorización de baches basada en evidencia. UNRC LCDN 2026-2." />
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@stlite/browser@__VERSION__/build/stlite.css" />
    <style>
      #carga { font-family: system-ui, sans-serif; max-width: 640px; margin: 15vh auto; text-align: center; color: #333; }
      #carga h1 { color: #1f3a5f; margin-bottom: .2em; }
      #carga p { line-height: 1.5; }
    </style>
  </head>
  <body>
    <div id="root">
      <div id="carga">
        <h1>SIPA</h1>
        <p>Sistema Inteligente de Priorización Asfáltica</p>
        <p>Cargando el tablero… La primera vez tarda entre 15 y 30 segundos, porque el navegador
           descarga Python. Las siguientes visitas son más rápidas.</p>
      </div>
    </div>
    <script type="module">
      import { mount } from "https://cdn.jsdelivr.net/npm/@stlite/browser@__VERSION__/build/stlite.js";
      const archivos = __ARCHIVOS__;
      const files = {};
      for (const ruta of archivos) files[ruta] = { url: "./" + ruta };
      mount(
        {
          requirements: ["pydeck"],
          entrypoint: "app.py",
          files,
          streamlitConfig: { "client.toolbarMode": "viewer", "theme.base": "light", "theme.primaryColor": "#2a78d6", "theme.backgroundColor": "#f4f5f7", "theme.secondaryBackgroundColor": "#eef0f3", "theme.textColor": "#0b0b0b" },
        },
        document.getElementById("root"),
      );
    </script>
  </body>
</html>
"""


def main():
    if SITIO.exists():
        shutil.rmtree(SITIO)
    (SITIO / "datos").mkdir(parents=True)
    shutil.copy(ORIGEN / "app.py", SITIO / "app.py")
    archivos = ["app.py"]
    for csv in sorted((ORIGEN / "datos").glob("*.csv")):
        shutil.copy(csv, SITIO / "datos" / csv.name)
        archivos.append(f"datos/{csv.name}")
    html = PAGINA.replace("__VERSION__", STLITE).replace("__ARCHIVOS__", json.dumps(archivos))
    (SITIO / "index.html").write_text(html, encoding="utf-8")
    (SITIO / ".nojekyll").write_text("", encoding="utf-8")   # GitHub Pages sirve los archivos tal cual
    print(f"Sitio en {SITIO}/: {len(archivos)} archivos montados con stlite {STLITE}")


if __name__ == "__main__":
    main()
