"""
SIPA · Reporte de evidencia: el tablero trabaja en vivo sobre SQL Server.

Recorre el tablero local con Playwright y, en cada paso, consulta SQL Server
directamente para mostrar que lo que se ve y lo que se guarda está en la base:
  1. Datos del servidor (instancia, versión, base, tablas y procedimientos).
  2. La cifra de reportes del tablero = SELECT COUNT(*) FROM reporte.
  3. Un ciudadano envía un reporte desde el tablero -> la fila aparece en la base.
  4. La cifra del tablero sube en 1 al recargar.
  5. La base rechaza una decisión inválida (AJUSTAR sin justificación) y no
     se guarda ninguna fila.
Genera pdf/evidencia_sql_server.pdf con capturas y resultados de las consultas.

Uso (con el tablero corriendo: python -m streamlit run tablero/app.py --server.headless true):
    python scripts/evidencia_sql_server.py
ATENCIÓN: escribe un reporte en la base; después reconstruirla con bd/ejecutar_todo.ps1.
"""
import base64
import datetime as dt
import html
import re
import subprocess
import sys
from pathlib import Path

import pyodbc
from playwright.sync_api import sync_playwright, expect

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "tablero"))
from pruebas_e2e import (URL, AVISO, KPI, ESPERA, abrir, esperar_quieto, elegir,  # noqa: E402
                         bache_priorizado)

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
CONEXION = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=SIPA;Trusted_Connection=yes"
SALIDA = RAIZ / "pdf" / "evidencia_sql_server.pdf"
TEMP = RAIZ / "tablero" / "capturas" / "evidencia"
TEMP.mkdir(parents=True, exist_ok=True)

cx = pyodbc.connect(CONEXION, autocommit=True)


def sql(q, *p):
    cur = cx.cursor()
    cur.execute(q, p)
    cols = [c[0] for c in cur.description]
    return cols, [list(f) for f in cur.fetchall()]


def tabla(q, *p):
    cols, filas = sql(q, *p)
    cab = "".join(f"<th>{html.escape(c)}</th>" for c in cols)
    cuerpo = "".join("<tr>" + "".join(f"<td>{html.escape(str(v))}</td>" for v in f) + "</tr>" for f in filas)
    return f'<pre class="q">{html.escape(q.strip())}</pre><table><tr>{cab}</tr>{cuerpo}</table>'


def uno(q, *p):
    return sql(q, *p)[1][0][0]


def foto(page, nombre, locator=None):
    esperar_quieto(page)
    page.wait_for_timeout(1500)
    ruta = TEMP / f"{nombre}.png"
    (locator or page).screenshot(path=str(ruta), **({} if locator else {"full_page": False}))
    return f'<img src="data:image/png;base64,{base64.b64encode(ruta.read_bytes()).decode()}">'


secciones = []


def seccion(titulo, *partes):
    secciones.append(f"<section><h2>{titulo}</h2>{''.join(partes)}</section>")


def p(texto, clase=""):
    return f'<p class="{clase}">{texto}</p>'


# 1. Servidor ---------------------------------------------------------------
seccion("1. El servidor de base de datos",
        p("Consultas hechas directamente a SQL Server con pyodbc, el mismo controlador que usa el tablero:"),
        tabla("SELECT @@SERVERNAME AS servidor, DB_NAME() AS base, "
              "SERVERPROPERTY('ProductVersion') AS version, SERVERPROPERTY('Edition') AS edicion, "
              "SYSDATETIME() AS hora_servidor"),
        tabla("SELECT name AS procedimiento, create_date FROM sys.procedures "
              "WHERE name IN ('sp_registrar_reporte','sp_calcular_ipu','sp_registrar_decision',"
              "'sp_actualizar_estado_bache','sp_consultar_folio') ORDER BY name"),
        tabla("SELECT (SELECT COUNT(*) FROM reporte) AS reportes, (SELECT COUNT(*) FROM bache) AS baches, "
              "(SELECT COUNT(*) FROM calculo_prioridad) AS calculos_ipu, "
              "(SELECT COUNT(*) FROM decision_humana) AS decisiones"))

with sync_playwright() as pw:
    nav = pw.chromium.launch()
    page = nav.new_page(viewport={"width": 1400, "height": 900})

    # 2. Lectura -------------------------------------------------------------
    n0 = uno("SELECT COUNT(*) FROM reporte")
    abrir(page, 0, "Resumen ejecutivo")
    expect(page.get_by_text("En vivo · SQL Server").first).to_be_visible(timeout=ESPERA)
    kpi0 = page.locator(KPI).nth(0).inner_text()
    en_tablero = int(re.search(r"[\d,]{3,}", kpi0).group(0).replace(",", ""))
    seccion("2. El tablero lee de la base",
            p("La barra superior indica <b>«En vivo · SQL Server»</b>. La cifra «Reportes ciudadanos» del "
              "tablero es el resultado de <code>SELECT COUNT(*) FROM reporte</code>:"),
            foto(page, "01_resumen"),
            p(f"Tablero: <b>{en_tablero:,}</b> · SQL Server: <b>{n0:,}</b> → "
              f"{'<span class=ok>coinciden</span>' if en_tablero == n0 else '<span class=mal>NO coinciden</span>'}"))

    # 3. Escritura -------------------------------------------------------------
    marca = f"Evidencia SQL Server {dt.datetime.now():%Y-%m-%d %H:%M:%S}"
    abrir(page, 1, "Modo ciudadano")
    page.get_by_role("textbox", name="Descripción").fill(marca)
    page.get_by_role("button", name="Enviar reporte").click()
    aviso = page.locator(AVISO).first
    expect(aviso).to_contain_text("Su folio es", timeout=ESPERA)
    folio = int(re.search(r"folio es (\d+)", aviso.inner_text()).group(1))
    seccion("3. El tablero escribe en la base",
            p(f"Desde el modo ciudadano se envió un reporte con la descripción «{html.escape(marca)}». "
              f"El tablero llama al procedimiento <code>sp_registrar_reporte</code> y devuelve el folio {folio}:"),
            foto(page, "02_reporte"),
            p("La fila está en SQL Server, con el bache al que se asoció:"),
            tabla("SELECT r.id_reporte, r.fecha_solicitud, r.descripcion, r.id_bache, b.id_estado_bache "
                  "FROM reporte r LEFT JOIN bache b ON b.id_bache = r.id_bache WHERE r.id_reporte = ?", folio))

    # 4. Lectura después de escribir ---------------------------------------
    abrir(page, 0, "Resumen ejecutivo")
    kpi1 = int(re.search(r"[\d,]{3,}", page.locator(KPI).nth(0).inner_text()).group(0).replace(",", ""))
    n1 = uno("SELECT COUNT(*) FROM reporte")
    seccion("4. La cifra del tablero cambia con la base",
            p(f"Al recargar, «Reportes ciudadanos» pasó de <b>{en_tablero:,}</b> a <b>{kpi1:,}</b>; "
              f"SQL Server tiene <b>{n1:,}</b> → "
              f"{'<span class=ok>coinciden (+1)</span>' if kpi1 == n1 == en_tablero + 1 else '<span class=mal>revisar</span>'}"),
            foto(page, "03_resumen_despues", page.locator(KPI).nth(0)))

    # 5. Rechazo de la base ------------------------------------------------------
    d0 = uno("SELECT COUNT(*) FROM decision_humana")
    abrir(page, 3, "Modo autoridad")
    elegir(page, "Bache", bache_priorizado())
    page.get_by_text("AJUSTAR", exact=True).click()
    page.get_by_role("button", name="Registrar decisión").click()
    expect(page.locator(AVISO).first).to_contain_text("justificación", timeout=ESPERA)
    error = page.locator(AVISO).first.inner_text()
    d1 = uno("SELECT COUNT(*) FROM decision_humana")
    seccion("5. La base rechaza lo inválido",
            p("En el modo autoridad se intentó AJUSTAR la recomendación sin justificación. La regla vive en "
              "SQL Server (procedimiento <code>sp_registrar_decision</code> y restricción "
              "<code>ck_decision_justificacion</code>); el tablero solo muestra el mensaje de la base:"),
            foto(page, "04_rechazo"),
            p(f"Mensaje: <i>{html.escape(error)}</i>"),
            p(f"Decisiones en la base antes: <b>{d0:,}</b> · después: <b>{d1:,}</b> → "
              f"{'<span class=ok>no se guardó nada (transacción revertida)</span>' if d0 == d1 else '<span class=mal>revisar</span>'}"))
    nav.close()

ahora = dt.datetime.now()
doc = f"""<!DOCTYPE html><html lang="es"><head><meta charset="utf-8"><title>Evidencia SQL Server</title><style>
@page {{ size: Letter; margin: 16mm 15mm; }}
body {{ font-family: "Segoe UI", Arial, sans-serif; color: #1b1b1b; font-size: 11pt; }}
h1 {{ font-size: 20pt; margin: 0 0 4px; color: #0d366b; }} .sub {{ color: #555; margin: 0 0 14px; }}
h2 {{ font-size: 13.5pt; color: #0d366b; border-bottom: 2px solid #2a78d6; padding-bottom: 3px; margin-top: 18px; }}
section {{ break-inside: avoid-page; }} section:nth-of-type(4) img {{ width: 300px; }} img {{ width: 100%; border: 1px solid #ccc; margin: 6px 0; }}
table {{ border-collapse: collapse; width: 100%; font-size: 9pt; margin: 4px 0 10px; }}
th, td {{ border: 1px solid #ccc; padding: 3px 6px; text-align: left; }} th {{ background: #eef3fa; }}
pre.q {{ background: #f4f5f7; padding: 6px 8px; font-size: 8.5pt; white-space: pre-wrap; margin: 6px 0 2px; }}
.ok {{ color: #0a7a0a; font-weight: 700; }} .mal {{ color: #c00; font-weight: 700; }}
.caja {{ background: #eef3fa; border-left: 4px solid #2a78d6; padding: 8px 12px; }}
</style></head><body>
<h1>SIPA · Evidencia de conexión a SQL Server</h1>
<p class="sub">Generado automáticamente el {ahora:%d-%m-%Y a las %H:%M} con <code>scripts/evidencia_sql_server.py</code>
(Playwright + pyodbc) · Equipo: Sandra Luna Altos · Joshua David Aquino · Rebeca Jaimes Cruz · Ithan Felipe Santiago</p>
<div class="caja">La aplicación oficial (<code>tablero/app.py</code>) corre en local conectada en vivo a la base
<b>SIPA</b> de SQL Server. Este reporte recorre la aplicación en un navegador real y, en cada paso, consulta la base
directamente para comprobar que lo que se muestra y lo que se guarda está en SQL Server. El sitio de GitHub Pages es
solo una vista pública de consulta con una copia de los datos.</div>
{''.join(secciones)}
<p class="sub" style="margin-top:18px">Para repetirlo: <code>python -m streamlit run tablero/app.py</code> y
<code>python scripts/evidencia_sql_server.py</code>.</p>
</body></html>"""
html_path = TEMP / "evidencia.html"
html_path.write_text(doc, encoding="utf-8")
SALIDA.parent.mkdir(exist_ok=True)
subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                f"--print-to-pdf={SALIDA}", html_path.as_uri()], check=True, capture_output=True)
print("Listo:", SALIDA)
