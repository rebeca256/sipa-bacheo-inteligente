"""
SIPA · Pruebas de extremo a extremo del tablero con Playwright.

Abren el tablero en un navegador real (Chromium sin ventana), recorren las
cinco secciones, usan los formularios del modo ciudadano y del modo autoridad
y revisan que la base acepte lo válido y rechace lo inválido.

ATENCIÓN: escriben en la base SIPA (un reporte, decisiones y cambios de
estado). Al terminar, reconstruir la base con bd/ejecutar_todo.ps1.

Uso (desde la carpeta del proyecto, con el tablero corriendo):
    streamlit run tablero/app.py --server.headless true
    python -m pytest tablero/pruebas_e2e.py -v
Las capturas quedan en tablero/capturas/pruebas/.
"""
import re
from pathlib import Path

import pyodbc
import pytest
from playwright.sync_api import Page, expect

URL = "http://localhost:8501"
# El nombre de la gráfica Altair cambia según la versión de Streamlit
GRAFICA = "[data-testid=stVegaLiteChart], [data-testid=stArrowVegaLiteChart]"
CAPTURAS = Path("tablero/capturas/pruebas")
CAPTURAS.mkdir(parents=True, exist_ok=True)
ESPERA = 120_000  # ms: la primera carga tras reiniciar o cambiar el código puede tardar


@pytest.fixture
def pagina(page: Page):
    page.set_viewport_size({"width": 1500, "height": 1100})
    errores = []
    page.on("pageerror", lambda e: errores.append(str(e)))
    yield page
    assert not errores, f"Errores de JavaScript en el navegador: {errores}"


def abrir(page, seccion, titulo):
    page.goto(f"{URL}/?p={seccion}")
    expect(page.get_by_role("heading", name=titulo).first).to_be_visible(timeout=ESPERA)
    esperar_quieto(page)
    sin_errores(page)


def esperar_quieto(page):
    """Espera a que Streamlit termine de ejecutar el script (desaparece el indicador «Running»)."""
    page.wait_for_timeout(500)
    expect(page.get_by_test_id("stStatusWidget")).to_have_count(0, timeout=ESPERA)


def sin_errores(page):
    expect(page.get_by_test_id("stException")).to_have_count(0)
    # texto técnico que Streamlit muestra si una expresión suelta se escribe en pantalla
    expect(page.get_by_text("DeltaGenerator")).to_have_count(0)
    expect(page.get_by_test_id("stMain").get_by_text("None", exact=True)).to_have_count(0)


def elegir(page, etiqueta, opcion):
    """Elige una opción en un selectbox de Streamlit."""
    # La lista desplegable se redibuja y a veces suelta el clic: se reintenta y se comprueba
    for _ in range(5):
        caja = page.get_by_role("combobox", name=etiqueta).last   # al redibujar puede haber una copia vieja
        caja.click()
        try:
            page.get_by_role("option", name=opcion, exact=True).first.click(timeout=5000)
        except Exception:
            page.keyboard.press("Escape")
            continue
        esperar_quieto(page)
        if page.get_by_role("combobox", name=re.compile(rf"Selected {re.escape(opcion)}\.")).count() > 0:
            break
    expect(page.get_by_role("combobox", name=re.compile(rf"Selected {re.escape(opcion)}\.")).last).to_be_visible()
    esperar_quieto(page)


def bache_priorizado(territorio="CHALCO"):
    """Un bache del territorio que siga en PRIORIZADO (las pruebas no dependen de corridas anteriores)."""
    cx = pyodbc.connect("DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=SIPA;"
                        "Trusted_Connection=yes")
    fila = cx.execute("""SELECT TOP 1 b.id_bache FROM bache b
                         JOIN ind.v_celda_territorio ct ON ct.celda_id = b.celda_id
                         WHERE ct.territorio = ? AND b.id_estado_bache = 3
                         ORDER BY b.id_bache DESC""", territorio).fetchone()
    cx.close()
    assert fila, f"No quedan baches priorizados en {territorio}: reconstruir la base"
    return str(fila[0])


def captura(page, nombre):
    esperar_quieto(page)
    page.wait_for_timeout(1500)      # deja terminar la animación de los elementos que se redibujan
    page.screenshot(path=str(CAPTURAS / f"{nombre}.png"), full_page=True)


# ---------------------------------------------------------------------------

def test_resumen_y_mapa(pagina):
    abrir(pagina, 0, "SIPA · Sistema Inteligente de Priorización Asfáltica")
    metricas = pagina.get_by_test_id("stMetric")
    expect(metricas).to_have_count(5)
    expect(metricas.nth(1)).to_contain_text(re.compile(r"Baches abiertos\s*1,\d{3}"))
    expect(metricas.nth(3)).to_contain_text(re.compile(r"\$\d+\.\d{2} M"))
    # mapa (pydeck dibuja en un canvas) y gráfica de costo pendiente
    expect(pagina.get_by_test_id("stDeckGlJsonChart").locator("canvas").first).to_be_visible(timeout=ESPERA)
    expect(pagina.locator(GRAFICA)).to_have_count(1)
    elegir(pagina, "Territorio", "CHALCO")
    sin_errores(pagina)
    captura(pagina, "01_resumen")


def test_ciudadano_reporta_y_consulta_folio(pagina):
    abrir(pagina, 1, "Modo ciudadano")
    pagina.get_by_role("textbox", name="Descripción").fill("Prueba Playwright: bache frente a la escuela")
    pagina.get_by_role("button", name="Enviar reporte").click()
    exito = pagina.get_by_role("alert").first
    expect(exito).to_contain_text("Su folio es", timeout=ESPERA)
    folio = re.search(r"folio es (\d+)", exito.inner_text()).group(1)
    captura(pagina, "02_ciudadano_reporte")

    pagina.get_by_role("spinbutton", name="Folio").fill(folio)
    pagina.get_by_role("spinbutton", name="Folio").press("Enter")
    esperar_quieto(pagina)
    pagina.get_by_role("button", name="Consultar").click()
    esperar_quieto(pagina)
    tabla = pagina.get_by_test_id("stDataFrame").first
    expect(tabla).to_be_visible(timeout=ESPERA)
    expect(pagina.get_by_role("alert").first).to_contain_text("Aún sin avances")
    sin_errores(pagina)
    captura(pagina, "03_ciudadano_folio")


def test_folio_inexistente(pagina):
    abrir(pagina, 1, "Modo ciudadano")
    pagina.get_by_role("spinbutton", name="Folio").fill("99999999")
    pagina.get_by_role("spinbutton", name="Folio").press("Enter")
    esperar_quieto(pagina)
    pagina.get_by_role("button", name="Consultar").click()
    expect(pagina.get_by_role("alert").first).to_contain_text("No existe", timeout=ESPERA)


def test_recomendacion_y_ficha(pagina):
    abrir(pagina, 2, "Recomendación de SIPA")
    expect(pagina.get_by_test_id("stDataFrame").first).to_be_visible(timeout=ESPERA)
    metricas = pagina.get_by_test_id("stMetric")
    expect(metricas).to_have_count(4)
    expect(metricas.nth(0)).to_contain_text(re.compile(r"IPU\s*0\.\d{3}"))
    expect(metricas.nth(3)).to_contain_text("$")
    expect(pagina.locator(GRAFICA)).to_have_count(1)
    elegir(pagina, "Territorio", "COYOACAN")
    expect(metricas.nth(0)).to_contain_text("IPU")
    sin_errores(pagina)
    captura(pagina, "04_recomendacion")
    pagina.get_by_role("button", name="Recalcular el IPU de este bache").click()
    expect(pagina.get_by_role("alert").first).to_contain_text("recalculado", timeout=ESPERA)


def test_autoridad_reglas_y_avance(pagina):
    abrir(pagina, 3, "Modo autoridad")
    expect(pagina.get_by_test_id("stDataFrame").first).to_be_visible(timeout=ESPERA)
    elegir(pagina, "Bache", bache_priorizado())

    # 1. Ajustar sin justificación: la base lo rechaza
    pagina.get_by_text("AJUSTAR", exact=True).click()
    pagina.get_by_role("button", name="Registrar decisión").click()
    error = pagina.get_by_role("alert").first
    expect(error).to_contain_text("justificación", timeout=ESPERA)
    captura(pagina, "05_autoridad_rechazo")

    # 2. Ajustar con justificación: se registra
    pagina.get_by_text("AJUSTAR", exact=True).click()
    pagina.get_by_role("textbox", name=re.compile("^Justificación")).fill(
        "Frente a una primaria; riesgo para peatones en horario de entrada.")
    pagina.get_by_role("button", name="Registrar decisión").click()
    expect(pagina.get_by_role("alert").first).to_contain_text("Decisión registrada", timeout=ESPERA)

    # 3. Descartar sin motivo: la transacción se revierte
    elegir(pagina, re.compile(r"(^|. )De PRIORIZADO a"), "DESCARTADO")
    pagina.get_by_role("button", name="Actualizar estado").click()
    expect(pagina.get_by_role("alert").first).to_contain_text("motivo", timeout=ESPERA)

    # 4. Pasar a EN_ATENCION y después a REPARADO con costo
    elegir(pagina, re.compile(r"(^|. )De PRIORIZADO a"), "EN_ATENCION")
    pagina.get_by_role("button", name="Actualizar estado").click()
    expect(pagina.get_by_role("alert").first).to_contain_text("EN_ATENCION", timeout=ESPERA)
    esperar_quieto(pagina)
    expect(pagina.get_by_role("combobox", name=re.compile(r"(^|. )De EN_ATENCION a"))).to_be_visible(timeout=ESPERA)
    elegir(pagina, re.compile(r"(^|. )De EN_ATENCION a"), "REPARADO")
    pagina.get_by_role("spinbutton", name=re.compile("^Costo real")).fill("1850")
    pagina.get_by_role("button", name="Actualizar estado").click()
    expect(pagina.get_by_role("alert").first).to_contain_text("notificó", timeout=ESPERA)
    sin_errores(pagina)
    captura(pagina, "06_autoridad_reparado")


def test_indicadores(pagina):
    abrir(pagina, 4, "Indicadores")
    expect(pagina.get_by_test_id("stDataFrame")).to_have_count(2, timeout=ESPERA)
    expect(pagina.locator(GRAFICA)).to_have_count(3, timeout=ESPERA)
    captura(pagina, "07_indicadores")


def test_navegacion_lateral(pagina):
    abrir(pagina, 0, "SIPA · Sistema Inteligente de Priorización Asfáltica")
    for etiqueta, titulo in [("Modo ciudadano", "Modo ciudadano"), ("Recomendación de SIPA", "Recomendación de SIPA"),
                             ("Modo autoridad", "Modo autoridad"), ("Indicadores", "Indicadores")]:
        pagina.get_by_test_id("stSidebar").get_by_text(etiqueta, exact=True).click()
        expect(pagina.get_by_role("heading", name=titulo).first).to_be_visible(timeout=ESPERA)
        esperar_quieto(pagina)
        sin_errores(pagina)
