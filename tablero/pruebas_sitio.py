"""
SIPA · Pruebas con Playwright del tablero publicado en GitHub Pages (stlite).

La versión en línea corre en el navegador con la copia de solo consulta: se
revisa que cargue, que cada sección se vea sin errores, que las reglas
rechacen lo inválido y que avise que no se guardan cambios.

Uso (desde la carpeta del proyecto):
    python -m http.server 8000 --directory docs          # sitio local
    python -m pytest tablero/pruebas_sitio.py -v
Contra el sitio publicado:
    set SIPA_URL=https://rebeca256.github.io/sipa-bacheo-inteligente/
    python -m pytest tablero/pruebas_sitio.py -v
"""
import os
import re
from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright

URL = os.environ.get("SIPA_URL", "http://localhost:8000/")
CAPTURAS = Path("tablero/capturas/sitio")
CAPTURAS.mkdir(parents=True, exist_ok=True)
CARGA = 240_000     # ms: la primera carga descarga Python en el navegador
ESPERA = 60_000


@pytest.fixture(scope="module")
def pagina():
    """Un solo navegador para todas las pruebas: cargar Pyodide es lo lento."""
    with sync_playwright() as p:
        navegador = p.chromium.launch()
        page = navegador.new_page(viewport={"width": 1500, "height": 1100})
        errores = []
        page.on("pageerror", lambda e: errores.append(str(e)))
        page.goto(URL)
        expect(page.get_by_test_id("stMetric").first).to_be_visible(timeout=CARGA)
        page.errores = errores
        yield page
        navegador.close()


def ir(page, seccion, titulo):
    page.get_by_test_id("stSidebar").get_by_text(seccion, exact=True).click()
    expect(page.get_by_role("heading", name=titulo).first).to_be_visible(timeout=ESPERA)
    quieto(page)
    sin_errores(page)


def quieto(page):
    page.wait_for_timeout(700)
    expect(page.get_by_test_id("stStatusWidget")).to_have_count(0, timeout=ESPERA)


def sin_errores(page):
    expect(page.get_by_test_id("stException")).to_have_count(0)
    expect(page.get_by_text("DeltaGenerator")).to_have_count(0)
    assert not page.errores, f"Errores de JavaScript: {page.errores}"


def elegir(page, etiqueta, opcion):
    page.get_by_role("combobox", name=etiqueta).click()
    page.get_by_role("option", name=opcion, exact=True).first.click()
    quieto(page)


def captura(page, nombre):
    quieto(page)
    page.wait_for_timeout(1500)
    page.screenshot(path=str(CAPTURAS / f"{nombre}.png"), full_page=True)


# ---------------------------------------------------------------------------

def test_carga_y_resumen(pagina):
    expect(pagina.get_by_test_id("stSidebar")).to_contain_text("Versión en línea de solo consulta")
    metricas = pagina.get_by_test_id("stMetric")
    expect(metricas).to_have_count(5)
    expect(metricas.nth(0)).to_contain_text("35,700")
    expect(metricas.nth(1)).to_contain_text("1,345")
    expect(metricas.nth(3)).to_contain_text("$4.61 M")
    expect(pagina.get_by_test_id("stDeckGlJsonChart").locator("canvas").first).to_be_visible(timeout=ESPERA)
    expect(pagina.get_by_test_id("stVegaLiteChart")).to_have_count(1)
    sin_errores(pagina)
    captura(pagina, "01_resumen")


def test_ciudadano(pagina):
    ir(pagina, "Modo ciudadano", "Modo ciudadano")
    pagina.get_by_role("button", name="Enviar reporte").click()
    expect(pagina.get_by_test_id("stAlertContentSuccess")).to_contain_text("no se guarda", timeout=ESPERA)
    quieto(pagina)
    campo = pagina.get_by_role("spinbutton", name="Folio")
    campo.fill("35698")
    campo.press("Enter")
    quieto(pagina)
    pagina.get_by_role("button", name="Consultar").click()
    quieto(pagina)
    expect(pagina.get_by_test_id("stDataFrame").first).to_be_visible(timeout=ESPERA)
    sin_errores(pagina)
    captura(pagina, "02_ciudadano")
    campo.fill("99999999")
    campo.press("Enter")
    quieto(pagina)
    pagina.get_by_role("button", name="Consultar").click()
    expect(pagina.get_by_test_id("stAlertContentWarning")).to_contain_text("No existe", timeout=ESPERA)


def test_recomendacion(pagina):
    ir(pagina, "Recomendación de SIPA", "Recomendación de SIPA")
    metricas = pagina.get_by_test_id("stMetric")
    expect(metricas.nth(0)).to_contain_text(re.compile(r"IPU\s*0\.\d{3}"), timeout=ESPERA)
    expect(pagina.get_by_test_id("stVegaLiteChart")).to_have_count(1)
    elegir(pagina, "Territorio", "COYOACAN")
    expect(metricas.nth(3)).to_contain_text("$")
    sin_errores(pagina)
    captura(pagina, "03_recomendacion")


def test_autoridad(pagina):
    ir(pagina, "Modo autoridad", "Modo autoridad")
    pagina.get_by_text("AJUSTAR", exact=True).click()
    pagina.get_by_role("button", name="Registrar decisión").click()
    expect(pagina.get_by_test_id("stAlertContentError")).to_contain_text("justificación", timeout=ESPERA)
    pagina.get_by_role("textbox", name=re.compile("^Justificación")).fill(
        "Frente a una primaria; riesgo para peatones en horario de entrada.")
    pagina.get_by_role("button", name="Registrar decisión").click()
    exito = pagina.get_by_test_id("stAlertContentSuccess")
    expect(exito).to_contain_text("Decisión registrada", timeout=ESPERA)
    expect(exito).to_contain_text("no se guarda")
    quieto(pagina)
    sin_errores(pagina)
    captura(pagina, "04_autoridad")


def test_indicadores(pagina):
    ir(pagina, "Indicadores", "Indicadores")
    expect(pagina.get_by_test_id("stDataFrame")).to_have_count(2, timeout=ESPERA)
    expect(pagina.get_by_test_id("stVegaLiteChart")).to_have_count(3, timeout=ESPERA)
    sin_errores(pagina)
    captura(pagina, "05_indicadores")
