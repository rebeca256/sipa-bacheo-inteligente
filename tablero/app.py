"""
SIPA · Tablero del prototipo funcional (Streamlit).

Muestra el flujo completo con los dos modos de uso:
    Ciudadano   reporta un bache y consulta su folio
    SIPA        ranking, ficha de justificación del IPU, intervención y costo estimado
    Autoridad   aprueba, ajusta o rechaza la recomendación e informa el avance
    Indicadores reincidencia, tiempos, cobertura, causa probable y costo pendiente

Fuentes de datos:
    - Local: SQL Server (base SIPA). Las acciones pasan por los procedimientos
      almacenados (bd/05), con las mismas transacciones y restricciones.
    - En línea (GitHub Pages con stlite) o con SIPA_MODO=demo: la copia de solo
      consulta de tablero/datos/ (scripts/exportar_datos_tablero.py). Las
      acciones revisan las mismas reglas, pero no guardan nada.

Uso (desde la carpeta del proyecto):
    streamlit run tablero/app.py
"""
import os
from pathlib import Path

from decimal import Decimal

import altair as alt
import pandas as pd
import pydeck as pdk
import streamlit as st

try:                                   # en el navegador (stlite) no hay pyodbc ni SQL Server
    import pyodbc
except ImportError:
    pyodbc = None

CONEXION = ("DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=SIPA;"
            "Trusted_Connection=yes")
DATOS = Path(__file__).parent / "datos"
# --- Sistema visual (paleta validada para daltonismo; ver skill dataviz) -------
AZUL = "#2a78d6"          # dato principal de cada gráfica
MARINO = "#0d366b"        # banda superior
GRIS = "#c9c8c3"          # contexto: lo que no se destaca
TINTA, TINTA_2, TINTA_3 = "#0b0b0b", "#52514e", "#8a8984"
ESTADO = {"ROJO": "#d03b3b", "AMARILLO": "#fab219", "VERDE": "#0ca30c"}   # solo para el semáforo
CATEGORIAS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]       # orden fijo, nunca ciclado
COLOR = {k: [int(v[i:i + 2], 16) for i in (1, 3, 5)] for k, v in ESTADO.items()}   # para el mapa
ESTADOS = {1: "REPORTADO", 2: "VALIDADO", 3: "PRIORIZADO", 4: "EN_ATENCION", 5: "REPARADO", 6: "DESCARTADO"}
TRANSICIONES = {1: [2, 6], 2: [6], 3: [4, 5, 6], 4: [5, 6]}
# Restricciones de la base y su explicación para quien usa el tablero
REGLAS = {
    "ck_decision_justificacion": "para ajustar o rechazar hay que escribir una justificación de 20 caracteres o más.",
    "ck_decision_ajuste": "al ajustar hay que elegir el semáforo nuevo (y solo al ajustar).",
    "ck_seguimiento_descarte": "para descartar un bache hay que explicar el motivo (15 caracteres o más).",
    "ck_seguimiento_costo_rep": "el costo real solo se informa al marcar el bache como REPARADO.",
    "ck_seguimiento_costo": "el costo no puede ser negativo.",
}
AVISO_DEMO = ("(Versión en línea de solo consulta: las reglas se revisan igual que en la base, "
              "pero no se guarda ningún cambio.)")

st.set_page_config(page_title="SIPA · Portal ejecutivo", page_icon="🛣️", layout="wide",
                   initial_sidebar_state="expanded")

CSS = """
<style>
/* Estilo inspirado en AdminLTE 3 (plantilla MIT): menú lateral oscuro, small boxes, tarjetas con borde superior */
@import url('https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@300;400;600;700&display=swap');
@import url('https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css');
html, body, .stApp { font-family: 'Source Sans 3', 'Source Sans Pro', system-ui, sans-serif; }
.stApp { background: #f4f6f9; }
[data-testid="stDecoration"], [data-testid="stToolbarActions"], [data-testid="stMainMenu"], .stDeployButton,
#MainMenu, footer { display: none !important; }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stMainBlockContainer"], .block-container { padding-top: 1.2rem !important; max-width: 1400px; }

/* ---- Menú lateral oscuro ---- */
[data-testid="stSidebar"] { background: #343a40; }
[data-testid="stSidebar"] > div { background: #343a40; }
[data-testid="stSidebar"] * { color: #c2c7d0; }
[data-testid="stSidebarUserContent"] { padding-top: 0 !important; }
.sb-marca { display: flex; align-items: center; gap: 10px; padding: 14px 6px 14px; border-bottom: 1px solid #4b545c;
  margin: 0 -6px 10px; }
.sb-logo { width: 34px; height: 34px; border-radius: 50%; background: #007bff; color: #fff !important;
  display: inline-flex; align-items: center; justify-content: center; font-weight: 700; font-size: 13px;
  box-shadow: 0 3px 6px rgba(0,0,0,.16); }
.sb-nombre { font-size: 20px; font-weight: 300; color: #fff !important; }
.sb-nombre b { font-weight: 700; color: #fff !important; }
.sb-usuario { display: flex; align-items: center; gap: 10px; padding: 4px 6px 12px; border-bottom: 1px solid #4b545c;
  margin: 0 -6px 12px; font-size: 14px; }
.sb-usuario i { font-size: 26px; color: #adb5bd !important; }
.sb-seccion { font-size: 11px; text-transform: uppercase; letter-spacing: .6px; color: #8a939b !important;
  margin: 4px 0 6px 8px; }
.sb-pie { font-size: 11.5px; color: #8a939b !important; margin-top: 24px; line-height: 1.5; }
[data-testid="stSidebar"] .st-key-nav [data-testid="stWidgetLabel"] { display: none; }
[data-testid="stSidebar"] .st-key-nav [role="radiogroup"] { gap: 3px; flex-direction: column; }
[data-testid="stSidebar"] .st-key-nav [data-testid="stRadioOption"] { width: 100%; }
[data-testid="stSidebar"] .st-key-nav [role="radiogroup"] > * { width: 100%; margin: 0; padding: 9px 12px;
  border-radius: 4px; cursor: pointer; transition: background .15s; }
[data-testid="stSidebar"] .st-key-nav [role="radiogroup"] > *:hover { background: rgba(255,255,255,.1); }
[data-testid="stSidebar"] .st-key-nav [role="radiogroup"] > label > div:first-child:not([data-testid]),
[data-testid="stSidebar"] .st-key-nav [data-testid="stRadioOption"] > div > div:not([data-testid]) { display: none; }
[data-testid="stSidebar"] .st-key-nav [role="radiogroup"] > * p { font-size: 15.5px; color: #c2c7d0; }
[data-testid="stSidebar"] .st-key-nav [role="radiogroup"] > * p::before { font-family: 'bootstrap-icons';
  margin-right: 10px; font-size: 15px; display: inline-block; width: 18px; }
[data-testid="stSidebar"] .st-key-nav [role="radiogroup"] > *:has(input:checked),
[data-testid="stSidebar"] .st-key-nav [data-testid="stRadioOption"][data-selected="true"] {
  background: #007bff; box-shadow: 0 1px 3px rgba(0,0,0,.12), 0 1px 2px rgba(0,0,0,.24); }
[data-testid="stSidebar"] .st-key-nav [role="radiogroup"] > *:has(input:checked) p,
[data-testid="stSidebar"] .st-key-nav [data-testid="stRadioOption"][data-selected="true"] p { color: #fff; }
[data-testid="stSidebar"] .st-key-nav [role="radiogroup"] > *:nth-child(1) p::before { content: "\\f422"; }
[data-testid="stSidebar"] .st-key-nav [role="radiogroup"] > *:nth-child(2) p::before { content: "\\f4da"; }
[data-testid="stSidebar"] .st-key-nav [role="radiogroup"] > *:nth-child(3) p::before { content: "\\f586"; }
[data-testid="stSidebar"] .st-key-nav [role="radiogroup"] > *:nth-child(4) p::before { content: "\\f531"; }
[data-testid="stSidebar"] .st-key-nav [role="radiogroup"] > *:nth-child(5) p::before { content: "\\f17a"; }

/* ---- Barra superior y encabezado de página ---- */
.topbar { background: #fff; border-bottom: 1px solid #dee2e6; margin: -1.2rem 0 0; padding: 10px 16px;
  display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap;
  box-shadow: 0 0 0 100vmax #fff; clip-path: inset(0 -100vmax); }
.topbar .ruta { color: #6c757d; font-size: 14px; }
.topbar .ruta b { color: #212529; font-weight: 600; }
.topbar .modo { font-size: 12px; background: #e9ecef; color: #495057; border-radius: 4px; padding: 3px 8px; }
.topbar .modo.vivo { background: #d4edda; color: #155724; }
h1 { font-size: 1.8rem !important; font-weight: 400 !important; color: #212529; padding: 18px 0 0 !important; }
.subtitulo { color: #6c757d; font-size: 14.5px; margin: 0 0 14px; }

/* ---- Small boxes (cifras clave) ---- */
.kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin: 6px 0 16px; }
.kpi { position: relative; border-radius: 4px; overflow: hidden; color: #fff;
  box-shadow: 0 0 1px rgba(0,0,0,.125), 0 1px 3px rgba(0,0,0,.2); display: flex; flex-direction: column; }
.kpi .k-in { padding: 12px 14px 10px; position: relative; z-index: 1; flex: 1; }
.kpi .k-val { font-size: 2.1rem; font-weight: 700; line-height: 1.15; margin: 0 0 4px; white-space: nowrap;
  word-break: keep-all; }
.kpi .k-et { font-size: 15px; }
.kpi .k-ico { position: absolute; right: 14px; top: 10px; font-size: 64px; line-height: 1; color: rgba(0,0,0,.15);
  z-index: 0; transition: transform .3s; }
.kpi:hover .k-ico { transform: scale(1.1); }
.kpi .k-pie { background: rgba(0,0,0,.1); color: rgba(255,255,255,.85); font-size: 13px; text-align: center;
  padding: 4px 8px; position: relative; z-index: 1; }
.kpi.info { background: #17a2b8; } .kpi.primary { background: #007bff; } .kpi.success { background: #28a745; }
.kpi.danger { background: #dc3545; } .kpi.secondary { background: #6c757d; }
.kpi.warning { background: #ffc107; color: #1f2d3d; } .kpi.warning .k-pie { color: rgba(31,45,61,.85); }

/* ---- Tarjetas (card-outline) ---- */
[class*="st-key-card_"] { background: #fff; border-top: 3px solid #007bff; border-radius: 4px;
  box-shadow: 0 0 1px rgba(0,0,0,.125), 0 1px 3px rgba(0,0,0,.2); padding: 0 20px 14px; }
.t-cab { margin: 0 -20px 12px; padding: 11px 20px; border-bottom: 1px solid rgba(0,0,0,.125); }
.t-tit { font-weight: 400; font-size: 1.1rem; color: #212529; }
.t-tit::before { font-family: 'bootstrap-icons'; content: "\\f28c"; margin-right: 8px; color: #6c757d; font-size: 15px; }
.t-nota { color: #6c757d; font-size: 13px; margin-top: 2px; }

/* ---- Badges y callout ---- */
.chip { display: inline-block; font-size: 12px; font-weight: 700; border-radius: 4px; padding: 3px 7px; }
.chip.ok { background: #28a745; color: #fff; } .chip.alerta { background: #dc3545; color: #fff; }
.chip.medio { background: #ffc107; color: #1f2d3d; } .chip.neutro { background: #6c757d; color: #fff; }
.hallazgo { background: #fff; border-left: 5px solid #117a8b; border-radius: 4px; padding: 14px 18px;
  box-shadow: 0 1px 3px rgba(0,0,0,.12), 0 1px 2px rgba(0,0,0,.24); color: #212529; font-size: 15px;
  margin: 2px 0 16px; }

/* ---- Expediente y pasos ---- */
.exp-cab { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; flex-wrap: wrap;
  padding-top: 14px; }
.exp-tit { font-size: 1.4rem; font-weight: 600; color: #212529; }
.exp-sub { color: #6c757d; font-size: 13.5px; margin-top: 2px; }
.exp-chips { display: flex; gap: 6px; flex-wrap: wrap; }
.datos { display: grid; grid-template-columns: repeat(auto-fit, minmax(110px, 1fr)); gap: 10px;
  margin: 6px 0 4px; padding: 12px 0 0; border-top: 1px solid #e9ecef; }
.datos div { font-size: 12.5px; color: #6c757d; }
.datos b { display: block; font-size: 16px; color: #212529; font-weight: 600; margin-top: 2px; }
.porque { font-size: 14.5px; color: #212529; line-height: 1.55; }
.porque ol { padding-left: 18px; margin: 6px 0 0; }
.paso { display: flex; align-items: center; justify-content: space-between; gap: 8px; flex-wrap: wrap;
  margin: 0 -20px 12px; padding: 11px 20px; border-bottom: 1px solid rgba(0,0,0,.125); }
.paso .num { display: inline-flex; width: 26px; height: 26px; border-radius: 50%; background: #007bff; color: #fff;
  align-items: center; justify-content: center; font-weight: 700; font-size: 13px; margin-right: 8px; }
.paso .t { font-weight: 400; font-size: 1.1rem; color: #212529; display: inline-flex; align-items: center; }

/* ---- Leyenda del semáforo ---- */
.leyenda { display: flex; gap: 16px; flex-wrap: wrap; font-size: 13px; color: #495057; margin: 2px 0 8px; }
.leyenda span { display: inline-flex; align-items: center; gap: 6px; }
.leyenda i { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
.leyenda b { color: #212529; }

[data-testid="stElementContainer"]:has(style), .element-container:has(style) { display: none; }
@media (max-width: 640px) { .kpi .k-val { font-size: 1.6rem; } .kpi .k-ico { font-size: 48px; } }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def tema_altair():
    """Tema común de Altair: tinta neutra, cuadrícula casi invisible, sin bordes."""
    return {"config": {
        "font": "Inter, system-ui, sans-serif",
        "background": "transparent",
        "view": {"stroke": None},
        "axis": {"labelColor": TINTA_2, "titleColor": TINTA_3, "labelFontSize": 12, "titleFontSize": 11.5,
                 "titleFontWeight": 500, "gridColor": "#efefec", "domain": False, "ticks": False,
                 "labelPadding": 6},
        "legend": {"labelColor": TINTA_2, "labelFontSize": 12, "titleColor": TINTA_3, "titleFontSize": 11.5,
                   "orient": "top", "symbolType": "circle"},
        "text": {"color": TINTA_2, "fontSize": 11.5},
    }}


try:
    alt.themes.register("sipa", tema_altair)
    alt.themes.enable("sipa")
except AttributeError:              # Altair 5.5+ / 6
    alt.theme.register("sipa", enable=True)(tema_altair)


# ---------------------------------------------------------------------------
# Fuente de datos: SQL Server (versión local) o copia de solo consulta (en línea)
# ---------------------------------------------------------------------------

@st.cache_resource
def conexion():
    """Conexión a SQL Server, o None si no hay (entonces se usa la copia de solo consulta)."""
    if pyodbc is None or os.environ.get("SIPA_MODO") == "demo":
        return None
    try:
        return pyodbc.connect(CONEXION, autocommit=True, timeout=3)   # cada procedimiento maneja su transacción
    except pyodbc.Error:
        return None


EN_LINEA = conexion() is None


def consulta(sql, *params):
    cur = conexion().cursor()
    cur.execute(sql, params)
    columnas = [c[0] for c in cur.description]
    df = pd.DataFrame.from_records(cur.fetchall(), columns=columnas)
    # SQL Server devuelve DECIMAL como decimal.Decimal: se pasa a float para tablas, gráficas y mapa
    for c in df.columns:
        if df[c].dtype == object and df[c].map(lambda v: isinstance(v, Decimal)).any():
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


@st.cache_data
def copia(nombre):
    return pd.read_csv(DATOS / f"{nombre}.csv")


def ejecutar(sql, *params):
    """Ejecuta un procedimiento; devuelve (ok, mensaje, filas del primer resultado o None)."""
    cur = conexion().cursor()
    try:
        cur.execute("SET NOCOUNT ON; " + sql, params)
        filas = None
        while True:
            if cur.description:
                filas = cur.fetchall()
                break
            if not cur.nextset():
                break
        return True, "", filas
    except pyodbc.Error as e:
        texto = str(e.args[1]) if len(e.args) > 1 else str(e)
        texto = texto.split("[SQL Server]")[-1].split("(")[0].strip()
        for nombre, explicacion in REGLAS.items():
            if f'"{nombre}"' in texto:
                texto = f"{explicacion} (restricción {nombre})"
        return False, texto, None


def regla(nombre):
    """Resultado de una regla incumplida, igual al que da la base."""
    return False, f"{REGLAS[nombre]} (restricción {nombre})", None


# --- Lecturas ---------------------------------------------------------------

ULTIMO_CALCULO = """
    SELECT b.id_bache, ct.territorio, b.celda_id, b.latitud, b.longitud, b.severidad, b.profundidad_cm,
           b.area_m2, e.nombre AS estado, cp.id_calculo, cp.ipu, cp.semaforo,
           t.nombre AS intervencion, cp.costo_estimado,
           (SELECT COUNT(*) FROM reporte r WHERE r.id_bache = b.id_bache) AS reportes
    FROM bache b
    JOIN cat_estado_bache e ON e.id_estado_bache = b.id_estado_bache
    LEFT JOIN ind.v_celda_territorio ct ON ct.celda_id = b.celda_id
    OUTER APPLY (SELECT TOP 1 * FROM calculo_prioridad x WHERE x.id_bache = b.id_bache
                 ORDER BY x.id_calculo DESC) cp
    LEFT JOIN tarifa_reparacion t ON t.clave = cp.clave_tarifa
"""


@st.cache_data(ttl=30)
def baches():
    return copia("baches") if EN_LINEA else consulta(ULTIMO_CALCULO)


def total_reportes():
    if EN_LINEA:
        return len(copia("reportes"))
    return int(consulta("SELECT COUNT(*) n FROM reporte")["n"][0])


def tiempos():
    df = copia("tiempos") if EN_LINEA else consulta("SELECT * FROM ind.v_tiempo_respuesta_semaforo")
    return df.sort_values("meta_dias")


def costo_pendiente():
    if EN_LINEA:
        return copia("costo_pendiente")
    return consulta("SELECT territorio, baches_pendientes, costo_total, costo_rojos, costo_amarillos "
                    "FROM ind.v_costo_pendiente_territorio")


def colonias():
    if EN_LINEA:
        return copia("colonias")
    return consulta("SELECT c.id_colonia, CONCAT(c.nombre, ' · ', t.nombre) AS nombre "
                    "FROM colonia c JOIN territorio t ON t.id_territorio = c.id_territorio ORDER BY 2")


def detalle(id_calculo):
    if EN_LINEA:
        det = copia("detalle")
        det = det[det["id_calculo"] == id_calculo].drop(columns="id_calculo")
    else:
        det = consulta("""SELECT c.nombre AS criterio, d.valor_normalizado AS valor, d.peso_aplicado AS peso,
                                 CAST(d.valor_normalizado * d.peso_aplicado AS DECIMAL(5,4)) AS aporte
                          FROM detalle_calculo d JOIN criterio_ipu c ON c.id_criterio = d.id_criterio
                          WHERE d.id_calculo = ?""", int(id_calculo))
    det = det.copy()
    det[["valor", "peso", "aporte"]] = det[["valor", "peso", "aporte"]].astype(float)
    return det.sort_values("aporte", ascending=False).reset_index(drop=True)


def autoridades():
    if EN_LINEA:
        return copia("autoridades")
    return consulta("""SELECT u.id_usuario, u.nombre, t.nombre AS territorio FROM usuario u
                       JOIN territorio t ON t.id_territorio = u.id_territorio
                       WHERE u.rol = 'AUTORIDAD' ORDER BY t.nombre""")


def folio(id_reporte):
    """Encabezado del folio y avance informado por la autoridad."""
    if not EN_LINEA:
        cab = consulta("EXEC sp_consultar_folio ?", id_reporte)
        hist = consulta("""SELECT s.fecha, ea.nombre AS de_estado, en.nombre AS a_estado, s.comentario
                           FROM reporte r JOIN seguimiento_bache s ON s.id_bache = r.id_bache
                           JOIN cat_estado_bache ea ON ea.id_estado_bache = s.id_estado_anterior
                           JOIN cat_estado_bache en ON en.id_estado_bache = s.id_estado_nuevo
                           WHERE r.id_reporte = ? ORDER BY s.fecha""", id_reporte)
        return cab, hist
    rep = copia("reportes")
    rep = rep[rep["id_reporte"] == id_reporte]
    seg = copia("seguimiento")
    if rep.empty:
        return rep, seg.iloc[0:0]
    r = rep.iloc[0]
    b = baches().set_index("id_bache")
    dec = copia("decisiones").set_index("id_bache")["prioridad_decidida"]
    id_b = int(r.id_bache) if pd.notna(r.id_bache) and int(r.id_bache) in b.index else None
    cab = pd.DataFrame([{
        "folio": int(r.id_reporte), "fecha_solicitud": r.fecha_solicitud,
        "estado_bache": b.loc[id_b, "estado"] if id_b else None,
        "prioridad_recomendada": b.loc[id_b, "semaforo"] if id_b else None,
        "prioridad_decidida": dec.get(id_b) if id_b else None}])
    hist = seg[seg["id_bache"] == id_b].drop(columns="id_bache").sort_values("fecha")
    return cab, hist


def reincidencia():
    df = copia("reincidencia") if EN_LINEA else consulta(
        """SELECT territorio, celdas, celdas_reincidentes, celdas_cronicas, pct_reportes_en_cronicas
           FROM ind.v_reincidencia_territorio""")
    return df.sort_values("pct_reportes_en_cronicas", ascending=False)


def causas():
    if EN_LINEA:
        return copia("causas")
    return consulta("SELECT causa_probable, COUNT(*) AS baches FROM ind.v_causa_probable_bache "
                    "GROUP BY causa_probable")


def cobertura():
    df = copia("cobertura") if EN_LINEA else consulta(
        "SELECT territorio, pct_reparados FROM ind.v_cobertura_territorio")
    df = df.copy()
    df["pct_reparados"] = df["pct_reparados"].astype(float)
    return df


def resueltos():
    df = copia("resueltos") if EN_LINEA else consulta(
        """SELECT anio, SUM(reportes) AS reportes,
                  CAST(100.0 * SUM(resueltos) / SUM(reportes) AS DECIMAL(5,1)) AS pct_resueltos
           FROM ind.v_cobertura_reportes_anual GROUP BY anio""")
    df = df.copy()
    df["anio"] = df["anio"].astype(int).astype(str)
    df["pct_resueltos"] = df["pct_resueltos"].astype(float)
    return df.sort_values("anio")


# --- Acciones: en línea se revisan las mismas reglas, pero no se guarda nada --

def registrar_reporte(id_col, lat, lon, desc):
    if EN_LINEA:
        return True, "", None
    return ejecutar("DECLARE @r INT, @b INT; EXEC sp_registrar_reporte 2, ?, ?, ?, ?, @r OUTPUT, @b OUTPUT; "
                    "SELECT @r, @b;", id_col, lat, lon, desc)


def recalcular_ipu(id_bache):
    if EN_LINEA:
        return True, "", None
    return ejecutar("DECLARE @c INT; EXEC sp_calcular_ipu ?, @c OUTPUT;", int(id_bache))


def registrar_decision(id_calculo, id_usuario, decision, ajustado, justificacion):
    if EN_LINEA:
        if decision != "APROBAR" and len((justificacion or "").strip()) < 20:
            return regla("ck_decision_justificacion")
        return True, "", None
    return ejecutar("DECLARE @d INT; EXEC sp_registrar_decision ?, ?, ?, ?, ?, @d OUTPUT;",
                    int(id_calculo), int(id_usuario), decision, ajustado, justificacion)


def actualizar_estado(id_bache, id_usuario, nuevo, comentario, costo):
    if EN_LINEA:
        if nuevo == 6 and len((comentario or "").strip()) < 15:
            return regla("ck_seguimiento_descarte")
        return True, "", None
    return ejecutar("EXEC sp_actualizar_estado_bache ?, ?, ?, ?, ?;",
                    int(id_bache), int(id_usuario), nuevo, comentario, costo)


# ---------------------------------------------------------------------------
# Utilidades de la interfaz
# ---------------------------------------------------------------------------

def refrescar():
    st.cache_data.clear()


def aviso_y_recargar(texto):
    """Guarda el aviso de éxito y vuelve a dibujar la página con los datos nuevos."""
    if EN_LINEA:
        texto += " " + AVISO_DEMO
    else:
        refrescar()
    st.session_state["aviso"] = texto
    st.rerun()


def mostrar_aviso():
    if "aviso" in st.session_state:
        st.success(st.session_state.pop("aviso"))


def barras(df, valor, etiqueta, titulo, formato=",.0f", maximo=None, orden="-x", destacar=None,
           etiquetas=3):
    """Barras horizontales delgadas en un solo azul (una sola serie).
    - destacar: si se da, esa barra va en azul y las demás en gris (contexto).
    - etiquetas: cuántas barras llevan su valor escrito (las primeras); el resto, en el tooltip."""
    df = df.copy()
    df[valor] = df[valor].astype(float)
    df = df.sort_values(valor, ascending=False)
    if maximo:
        df = df.head(maximo)
    df["_rango"] = range(len(df))
    if destacar is not None:
        df["_color"] = [AZUL if v == destacar else GRIS for v in df[etiqueta]]
        df["_rotulo"] = df[etiqueta] == destacar
    else:
        df["_color"] = AZUL
        df["_rotulo"] = df["_rango"] < etiquetas
    base = alt.Chart(df).encode(
        y=alt.Y(f"{etiqueta}:N", sort=list(df[etiqueta]) if orden == "-x" else orden, title=None,
                axis=alt.Axis(labelLimit=190, labelOverlap=False)),
        x=alt.X(f"{valor}:Q", title=titulo, scale=alt.Scale(domainMax=float(df[valor].max()) * (1.32 if "$" in formato else 1.2) or 1),
                axis=alt.Axis(tickCount=4, format="$~s" if "$" in formato else formato)),
        tooltip=[alt.Tooltip(f"{etiqueta}:N", title=" "),
                 alt.Tooltip(f"{valor}:Q", format=formato, title=titulo)])
    g = base.mark_bar(size=12, cornerRadiusEnd=4).encode(color=alt.Color("_color:N", scale=None)) + \
        base.transform_filter("datum._rotulo").mark_text(align="left", dx=6, fontWeight=600, color=TINTA) \
            .encode(text=alt.Text(f"{valor}:Q", format=formato))
    return g.properties(height=alt.Step(26))


def ver_barras(df, valor, etiqueta, titulo, top=10, **kw):
    """Muestra las 10 primeras barras y deja ver el resto con un interruptor."""
    todos = len(df) > top and st.toggle(f"Ver los {len(df)}", key=f"todos_{etiqueta}_{valor}")
    st.altair_chart(barras(df, valor, etiqueta, titulo, maximo=None if todos else top, **kw),
                    use_container_width=True)


def barra_contra_meta(df):
    """Tiempo de respuesta: barra de días promedio (color del semáforo) y una marca en la meta."""
    df = df.copy()
    for c in ("dias_promedio", "meta_dias", "pct_en_meta"):
        df[c] = df[c].astype(float)
    df["color"] = df["semaforo_final"].map(ESTADO)
    df["texto"] = df.apply(lambda f: f"{f.dias_promedio:.1f} días · meta {f.meta_dias:.0f} · "
                                     f"{f.pct_en_meta:.0f} % en meta", axis=1)
    y = alt.Y("semaforo_final:N", title=None, sort=list(df["semaforo_final"]))
    tip = [alt.Tooltip("semaforo_final:N", title="Semáforo"), alt.Tooltip("baches:Q", title="Baches"),
           alt.Tooltip("dias_promedio:Q", title="Días promedio", format=".1f"),
           alt.Tooltip("meta_dias:Q", title="Meta (días)"), alt.Tooltip("pct_en_meta:Q", title="% en meta",
                                                                         format=".0f")]
    tope = float(max(df["dias_promedio"].max(), df["meta_dias"].max())) * 1.9
    barra = alt.Chart(df).mark_bar(size=14, cornerRadiusEnd=4).encode(
        y=y, x=alt.X("dias_promedio:Q", title="Días para reparar (promedio)", scale=alt.Scale(domain=[0, tope])),
        color=alt.Color("color:N", scale=None), tooltip=tip)
    meta = alt.Chart(df).mark_tick(color=TINTA, thickness=2, size=26).encode(y=y, x="meta_dias:Q", tooltip=tip)
    texto = alt.Chart(df).mark_text(align="left", dx=8, color=TINTA_2).encode(
        y=y, x=alt.X("max_x:Q"), text="texto:N").transform_calculate(
        max_x="max(datum.dias_promedio, datum.meta_dias)")
    return (barra + meta + texto).properties(height=alt.Step(40))


def barra_segmentada(df, valor, etiqueta):
    """Un todo partido en partes (100 %), con los colores categóricos en orden fijo."""
    df = df.copy()
    df[valor] = df[valor].astype(float)
    df = df.sort_values(valor, ascending=False)
    df["pct"] = df[valor] / df[valor].sum()
    # el % va en la leyenda: tres colores tienen poco contraste y no deben cargar solos el dato
    df[etiqueta] = [f"{n.replace('_', ' ').capitalize()} · {p:.0%}" for n, p in zip(df[etiqueta], df["pct"])]
    orden = list(df[etiqueta])
    df["fin"] = df["pct"].cumsum()
    df["inicio"] = df["fin"] - df["pct"]
    colores = alt.Scale(domain=orden, range=CATEGORIAS[:len(orden)])
    return alt.Chart(df).mark_bar(height=30, stroke="#ffffff", strokeWidth=2, cornerRadius=3).encode(
        x=alt.X("inicio:Q", title=None, scale=alt.Scale(domain=[0, 1]), axis=None),
        x2="fin:Q",
        color=alt.Color(f"{etiqueta}:N", scale=colores, sort=orden, title=None,
                        legend=None),
        tooltip=[alt.Tooltip(f"{etiqueta}:N", title="Causa"), alt.Tooltip(f"{valor}:Q", title="Baches")],
    ).properties(height=34)


def leyenda_segmentada(df, valor, etiqueta):
    """Leyenda en HTML con el % escrito (Streamlit recorta la leyenda de Vega en gráficas bajas)."""
    df = df.copy()
    df[valor] = df[valor].astype(float)
    df = df.sort_values(valor, ascending=False)
    total = df[valor].sum()
    items = "".join(
        f'<span><i style="background:{CATEGORIAS[k]}"></i>{n.replace("_", " ").capitalize()} · '
        f'<b>{v / total:.0%}</b> ({v:,.0f})</span>'
        for k, (n, v) in enumerate(zip(df[etiqueta], df[valor])))
    st.markdown(f'<div class="leyenda">{items}</div>', unsafe_allow_html=True)


# --- Piezas de la interfaz -----------------------------------------------------

def barra_superior(pagina):
    modo = ('<span class="modo">Copia de solo consulta</span>' if EN_LINEA
            else '<span class="modo vivo">● En vivo · SQL Server</span>')
    st.markdown(f'<div class="topbar"><span class="ruta">Inicio / <b>{pagina}</b></span>{modo}</div>',
                unsafe_allow_html=True)
    if EN_LINEA:
        st.caption("Versión en línea de solo consulta (copia de los datos). Las acciones revisan las reglas, "
                   "pero no guardan cambios.")


def menu_lateral(inicial):
    with st.sidebar:
        st.markdown('<div class="sb-marca"><span class="sb-logo">SIPA</span>'
                    '<span class="sb-nombre"><b>SIPA</b> Portal</span></div>'
                    '<div class="sb-usuario"><i class="bi bi-person-circle"></i>'
                    '<span>Panel ejecutivo<br><small>Piloto CDMX y Chalco</small></span></div>'
                    '<div class="sb-seccion">Navegación</div>', unsafe_allow_html=True)
        with st.container(key="nav"):
            pagina = st.radio("Sección", list(PAGINAS), index=min(inicial, len(PAGINAS) - 1))
        st.markdown('<div class="sb-pie">Sistema Inteligente de Priorización Asfáltica<br>'
                    'Bacheo inteligente · UNRC LCDN 2026-2</div>', unsafe_allow_html=True)
    return pagina


def encabezado(titulo, subtitulo=None):
    st.title(titulo, anchor=False)
    if subtitulo:
        st.markdown(f'<div class="subtitulo">{subtitulo}</div>', unsafe_allow_html=True)


# Color e ícono de cada small box (por etiqueta); un estado (chip) manda sobre el color
ESTILO_KPI = [("Reportes", "info", "megaphone-fill"), ("Baches abiertos", "primary", "cone-striped"),
              ("Costo", "warning", "cash-stack"), ("Rojos", "success", "stopwatch-fill"),
              ("IPU", "info", "speedometer2"), ("Intervención", "primary", "cone-striped"),
              ("Por semáforo", "secondary", "bar-chart-fill")]
COLOR_CHIP = {"ok": "success", "alerta": "danger", "medio": "warning"}
COLOR_SEMAFORO = {"Rojo": "danger", "Amarillo": "warning", "Verde": "success"}


def kpis(items):
    """Small boxes al estilo AdminLTE. items: (etiqueta, valor, contexto, (tipo, texto) o None, ayuda)."""
    html = ""
    for i, (et, val, ctx, chip, ayuda) in enumerate(items):
        color, icono = next(((c, ic) for pref, c, ic in ESTILO_KPI if et.startswith(pref)),
                            (["info", "success", "warning", "danger"][i % 4], "clipboard-data"))
        if et == "Semáforo":
            color, icono = COLOR_SEMAFORO.get(val, "secondary"), "circle-fill"
        if chip:
            color = COLOR_CHIP.get(chip[0], color)
        pie = ctx + (f" · {chip[1]}" if chip else "")
        html += (f'<div class="kpi {color}" title="{ayuda or ""}"><div class="k-in"><div class="k-val">{val}</div>'
                 f'<div class="k-et">{et}</div></div><i class="bi bi-{icono} k-ico"></i>'
                 f'<div class="k-pie">{pie} <i class="bi bi-arrow-right-circle"></i></div></div>')
    st.markdown(f'<div class="kpis">{html}</div>', unsafe_allow_html=True)


def hallazgo(texto):
    st.markdown(f'<div class="hallazgo">{texto}</div>', unsafe_allow_html=True)


def tarjeta(clave, titulo=None, nota=None):
    """Contenedor blanco con borde (el estilo sale de la clase st-key-card_…)."""
    c = st.container(key=f"card_{clave}")
    if titulo:
        c.markdown(f'<div class="t-cab"><div class="t-tit">{titulo}</div>'
                   + (f'<div class="t-nota">{nota}</div>' if nota else "") + '</div>', unsafe_allow_html=True)
    return c


LEYENDA = ('<div class="leyenda">' + "".join(
    f'<span><i style="background:{ESTADO[k]}"></i>{k.capitalize()} · {t}</span>'
    for k, t in [("ROJO", "atender en 3 días"), ("AMARILLO", "en 15"), ("VERDE", "programar en 60")])
    + "<span>· El tamaño del punto crece con el IPU</span></div>")


# Formato de las columnas en las tablas
COLUMNAS = {
    "ipu": st.column_config.NumberColumn("IPU", format="%.3f"),
    "costo_estimado": st.column_config.TextColumn("Costo estimado"),   # ya viene como "$12,345"
    "id_bache": st.column_config.NumberColumn("Bache", format="%d"),
    "semaforo": "Semáforo", "intervencion": "Intervención recomendada", "reportes": "Reportes",
    "estado": "Estado", "lugar": "Lugar",
    # Indicadores
    "territorio": "Territorio", "celdas": "Celdas", "celdas_reincidentes": "Reincidentes",
    "celdas_cronicas": "Crónicas",
    "pct_reportes_en_cronicas": st.column_config.ProgressColumn(
        "% reportes en celdas crónicas", format="%.1f %%", min_value=0, max_value=100),
    "semaforo_final": "Semáforo", "baches": "Baches",
    "dias_promedio": st.column_config.NumberColumn("Días promedio", format="%.1f"),
    "meta_dias": st.column_config.NumberColumn("Meta (días)", format="%d"),
    "pct_en_meta": st.column_config.ProgressColumn("% dentro de la meta", format="%.0f %%",
                                                   min_value=0, max_value=100),
    "folio": "Folio", "fecha_solicitud": "Fecha de solicitud", "estado_bache": "Estado del bache",
    "prioridad_recomendada": "Prioridad recomendada", "prioridad_decidida": "Prioridad decidida",
}

# Nombre corto de cada tarifa para que quepa en la métrica (el completo va en la ayuda)
CORTO = {"Bacheo superficial con mezcla en frío": "Superficial",
         "Bacheo profundo: corte, caja y mezcla en caliente": "Profundo",
         "Bacheo con sello impermeable y revisión de drenaje pluvial": "Con sello",
         "Reencarpetado del tramo (unos 100 m de un carril)": "Reencarpetado"}


def dinero(x):
    return f"${x:,.0f}" if pd.notna(x) else "—"


ICONO = {"ROJO": "🔴 Rojo", "AMARILLO": "🟡 Amarillo", "VERDE": "🟢 Verde"}
CHIP = {"ROJO": ("alerta", "● Rojo · 3 días"), "AMARILLO": ("medio", "● Amarillo · 15 días"),
        "VERDE": ("ok", "● Verde · 60 días")}


def con_icono(df, col="semaforo"):
    """Semáforo con ícono y nombre (el color nunca va solo)."""
    df = df.copy()
    df[col] = df[col].map(lambda v: ICONO.get(v, v))
    return df


def alto_tabla(filas, maximo=420):
    """Alto justo para ver todas las filas (35 px cada una), con tope."""
    return min(35 * (filas + 1) + 3, maximo)


def chip_html(tipo, texto):
    return f'<span class="chip {tipo}">{texto}</span>'


def miles(df, col="costo_estimado"):
    """Costo como texto con separador de miles ($12,345) para las tablas."""
    df = df.copy()
    df[col] = df[col].astype(float).map(dinero)
    return df


# ---------------------------------------------------------------------------
# Páginas
# ---------------------------------------------------------------------------

def mapa(df, alto=430):
    df = df.dropna(subset=["semaforo"]).copy()
    for c in ("latitud", "longitud", "ipu", "costo_estimado"):
        df[c] = df[c].astype(float)          # SQL devuelve Decimal; pydeck necesita float
    df["color"] = df["semaforo"].map(COLOR)
    df["radio"] = 40 + df["ipu"] * 160
    df["costo_txt"] = df["costo_estimado"].map(dinero)
    # pydeck serializa a JSON: solo columnas simples (sin fechas ni Decimal)
    df = df[["id_bache", "territorio", "ipu", "semaforo", "intervencion", "costo_txt",
             "latitud", "longitud", "color", "radio"]].copy()
    df["id_bache"] = df["id_bache"].astype(int)
    capa = pdk.Layer("ScatterplotLayer", df, get_position=["longitud", "latitud"],
                     get_fill_color="color", get_radius="radio", pickable=True, opacity=0.75)
    vista = pdk.ViewState(latitude=float(df["latitud"].mean()), longitude=float(df["longitud"].mean()), zoom=10)
    st.pydeck_chart(pdk.Deck(layers=[capa], initial_view_state=vista, map_style="light", height=alto,
                             tooltip={"text": "Bache {id_bache} · {territorio}\nIPU {ipu} · {semaforo}\n"
                                              "{intervencion}\nCosto estimado {costo_txt}"}),
                    use_container_width=True)


def pagina_resumen():
    encabezado("Resumen ejecutivo", "SIPA recomienda qué bache atender primero, por qué y cuánto costaría. "
                                    "La reparación la decide y la hace la autoridad.")
    df = baches()
    abiertos = df[df["estado"].isin(["VALIDADO", "PRIORIZADO", "EN_ATENCION"])]
    tr = tiempos()
    rojos_meta = tr.loc[tr["semaforo_final"] == "ROJO", "pct_en_meta"]
    pct_rojos = float(rojos_meta.iloc[0]) if len(rojos_meta) else None
    n = abiertos["semaforo"].value_counts()
    costo = abiertos["costo_estimado"].astype(float).sum()
    cp = costo_pendiente().copy()
    cp["costo_total"] = cp["costo_total"].astype(float)
    cp = cp.sort_values("costo_total", ascending=False)
    top4 = cp.head(4)["costo_total"].sum() / cp["costo_total"].sum() * 100

    kpis([
        ("Reportes ciudadanos", f"{total_reportes():,}", "CDMX 2019–2022 y Chalco 2025–2026", None, None),
        ("Baches abiertos", f"{len(abiertos):,}", f"{n.get('ROJO', 0)} rojos · {n.get('AMARILLO', 0)} amarillos · "
                                                  f"{n.get('VERDE', 0):,} verdes", None,
         "Si no hay rojos abiertos es porque ya pasaron a reparación (decisiones simuladas en bd/08)."),
        ("Costo pendiente", f"${costo / 1e6:,.2f} M", "estimado para atender lo abierto", None,
         "Suma del costo estimado de todos los baches abiertos."),
        ("Rojos reparados en ≤ 3 días", f"{pct_rojos:.0f} %" if pct_rojos is not None else "—", "meta: 100 %",
         (("ok", "✓ En meta") if pct_rojos and pct_rojos >= 90 else ("alerta", "! Debajo de la meta"))
         if pct_rojos is not None else None, None),
    ])
    hallazgo(f"<b>Hallazgo:</b> el costo pendiente es <b>${costo / 1e6:,.2f} M</b> y el "
             f"<b>{top4:.0f} %</b> se concentra en 4 territorios ({', '.join(cp.head(4)['territorio'].str.title())}). "
             f"El {pct_rojos:.0f} % de los rojos se reparó dentro de los 3 días de la meta." if pct_rojos is not None
             else f"<b>Hallazgo:</b> el costo pendiente es <b>${costo / 1e6:,.2f} M</b>.")

    izq, der = st.columns([3, 2], gap="medium")
    with izq:
        with tarjeta("mapa", "Mapa de prioridades", "Baches abiertos, coloreados por semáforo"):
            territorio = st.selectbox("Territorio", ["Todos"] + sorted(abiertos["territorio"].dropna().unique()))
            st.markdown(LEYENDA, unsafe_allow_html=True)
            vista = abiertos if territorio == "Todos" else abiertos[abiertos["territorio"] == territorio]
            mapa(vista)
    with der:
        nota = ("Territorio elegido en azul" if territorio != "Todos"
                else "Los 10 territorios con más costo; el resto con el interruptor")
        with tarjeta("costo", "Costo pendiente por territorio", nota):
            ver_barras(cp, "costo_total", "territorio", "Costo estimado", formato="$,.0f",
                       destacar=territorio if territorio != "Todos" else None)


def pagina_ciudadano():
    encabezado("Modo ciudadano", "No necesita cuenta. El reporte se liga al bache que ya exista en la misma "
                                 "celda de 250 m.")
    izq, der = st.columns(2, gap="medium")
    with izq, tarjeta("reportar", "Reportar un bache", "Ubicación y una descripción breve"):
        cols = colonias()
        with st.form("reporte"):
            col = st.selectbox("Colonia", cols["nombre"],
                               index=int(cols["nombre"].str.startswith("LINDAVISTA").idxmax()))
            lat = st.number_input("Latitud", value=19.499211, format="%.6f")
            lon = st.number_input("Longitud", value=-99.130782, format="%.6f")
            desc = st.text_input("Descripción", "Bache profundo frente a la escuela")
            if st.form_submit_button("Enviar reporte"):
                id_col = int(cols.loc[cols["nombre"] == col, "id_colonia"].iloc[0])
                ok, msg, filas = registrar_reporte(id_col, lat, lon, desc)
                if ok and EN_LINEA:
                    aviso_y_recargar("Reporte revisado. En la versión local se guardaría y recibiría su folio.")
                elif ok:
                    num, bache = filas[0]
                    aviso_y_recargar(f"Reporte recibido. Su folio es **{num}** (bache {bache}).")
                else:
                    st.error(msg)
    with der, tarjeta("folio", "Consultar mi folio", "El avance lo informa la autoridad"):
        num = st.number_input("Folio", min_value=1, value=35698, step=1)
        if st.button("Consultar"):
            cab, hist = folio(int(num))
            if cab.empty:
                st.warning("No existe ese folio.")
            else:
                st.dataframe(cab.fillna("Sin calcular"), hide_index=True, column_config=COLUMNAS)
                st.write("Avance informado por la autoridad:")
                if hist.empty:
                    st.info("Aún sin avances.")
                else:
                    st.dataframe(hist, hide_index=True)


def ficha(id_bache, lugar=None, total=None):
    """Expediente del bache: cabecera, cifras, datos del bache y por qué ocupa su lugar."""
    b = baches().set_index("id_bache").loc[id_bache]
    sem = b.semaforo if pd.notna(b.semaforo) else None
    chips = (chip_html(*CHIP[sem]) if sem in CHIP else "") + chip_html("neutro", f"Estado: {b.estado}")
    lugar_txt = f"Lugar {lugar} de {total} en {str(b.territorio).title()}" if lugar else str(b.territorio).title()
    with tarjeta("expediente"):
        st.markdown(f"""<div class="exp-cab"><div><div class="exp-tit">Bache {id_bache}</div>
            <div class="exp-sub">{lugar_txt} · celda {b.celda_id}</div></div>
            <div class="exp-chips">{chips}</div></div>""", unsafe_allow_html=True)
        kpis([
            ("IPU", f"{float(b.ipu):.3f}" if pd.notna(b.ipu) else "—", "índice de prioridad (0 a 1)", None, None),
            ("Semáforo", sem.capitalize() if sem else "—", "prioridad recomendada", None, None),
            ("Intervención", CORTO.get(b.intervencion, b.intervencion if pd.notna(b.intervencion) else "—"),
             b.intervencion if pd.notna(b.intervencion) else "", None, None),
            ("Costo estimado", dinero(float(b.costo_estimado)) if pd.notna(b.costo_estimado) else "—",
             "tarifa SIPA por m²", None, None),
        ])
        num = lambda v, f: f.format(float(v)) if pd.notna(v) else "—"
        st.markdown(f"""<div class="datos">
            <div>Severidad<b>{num(b.severidad, "{:.1f}")}</b></div>
            <div>Profundidad<b>{num(b.profundidad_cm, "{:.1f} cm")}</b></div>
            <div>Área<b>{num(b.area_m2, "{:.2f} m²")}</b></div>
            <div>Reportes<b>{int(b.reportes) if pd.notna(b.reportes) else "—"}</b></div>
            <div>Territorio<b>{str(b.territorio).title()}</b></div></div>""", unsafe_allow_html=True)
    if pd.notna(b.id_calculo):
        det = detalle(int(b.id_calculo))
        izq, der = st.columns([3, 2], gap="medium")
        with izq, tarjeta("justificacion", "Ficha de justificación",
                          "Cuánto aporta cada criterio al IPU (valor × peso). Un valor de 0.5 indica que no "
                          "hay dato para ese criterio (neutral)."):
            st.altair_chart(barras(det, "aporte", "criterio", "Aporte al IPU", formato=".3f"),
                            use_container_width=True)
            with st.expander("Ver los valores y pesos de cada criterio"):
                st.dataframe(det, hide_index=True)
        with der, tarjeta("porque", "Por qué ocupa este lugar"):
            top = det.assign(aporte=det["aporte"].astype(float)).sort_values("aporte", ascending=False).head(3)
            total_ipu = float(b.ipu) if pd.notna(b.ipu) else top["aporte"].sum()
            items = "".join(f"<li><b>{c}</b>: {a:.3f} ({a / total_ipu:.0%} del IPU)</li>"
                            for c, a in zip(top["criterio"], top["aporte"]))
            st.markdown(f'<div class="porque">Los tres criterios que más pesan:<ol>{items}</ol></div>',
                        unsafe_allow_html=True)
            st.markdown('<div class="porque" style="margin-top:10px">El número de reportes está acotado: '
                        'un bache muy reportado no sube solo por eso.</div>', unsafe_allow_html=True)
            return True
    return False


def pagina_ranking():
    encabezado("Recomendación de SIPA", "Ranking por IPU de los baches abiertos de un territorio y la ficha que "
                                        "justifica cada lugar.")
    df = baches()
    abiertos = df[df["estado"].isin(["VALIDADO", "PRIORIZADO", "EN_ATENCION"]) & df["ipu"].notna()].copy()
    territorios = sorted(abiertos["territorio"].dropna().unique())
    f1, f2 = st.columns(2)
    territorio = f1.selectbox("Territorio", territorios, index=territorios.index("CHALCO"))
    rank = abiertos[abiertos["territorio"] == territorio].sort_values("ipu", ascending=False)
    rank.insert(0, "lugar", range(1, len(rank) + 1))
    id_bache = f2.selectbox("Ver la ficha del bache", rank["id_bache"],
                            format_func=lambda x: f"{x}")
    with tarjeta("ranking", f"Ranking de {territorio.title()}",
                 "Fíjese en la columna de reportes: más reportes no significa más prioridad."):
        st.dataframe(con_icono(miles(rank[["lugar", "id_bache", "ipu", "semaforo", "intervencion",
                                           "costo_estimado", "reportes", "estado"]])),
                     hide_index=True, height=alto_tabla(len(rank)), column_config=COLUMNAS)
    lugar = int(rank.loc[rank["id_bache"] == id_bache, "lugar"].iloc[0])
    ficha(id_bache, lugar, len(rank))
    if st.button("Recalcular el IPU de este bache"):
        ok, msg, _ = recalcular_ipu(id_bache)
        if ok:
            aviso_y_recargar(f"IPU del bache {id_bache} recalculado (queda como un cálculo nuevo; "
                             "el anterior se conserva).")
        st.error(msg)


def pagina_autoridad():
    encabezado("Modo autoridad", "La autoridad decide sobre la recomendación y repara con sus propios "
                                 "recursos; en SIPA solo informa el avance.")
    usuarios = autoridades()
    f1, f2 = st.columns(2)
    nombre = f1.selectbox("Entrar como", usuarios["nombre"],
                          index=int((usuarios["territorio"] == "CHALCO").idxmax()))
    u = usuarios[usuarios["nombre"] == nombre].iloc[0]
    df = baches()
    mios = df[(df["territorio"] == u.territorio) & df["estado"].isin(["REPORTADO", "VALIDADO", "PRIORIZADO",
                                                                      "EN_ATENCION"])]
    mios = mios.sort_values("ipu", ascending=False)
    if mios.empty:
        with tarjeta("pendientes", f"Baches abiertos de {u.territorio.title()}"):
            st.info("No hay baches abiertos en este territorio.")
        return
    id_bache = f2.selectbox("Bache", mios["id_bache"], key=f"bache_autoridad_{u.id_usuario}")
    b = mios.set_index("id_bache").loc[id_bache]
    n = mios["semaforo"].value_counts()
    kpis([
        ("Baches abiertos", f"{len(mios):,}", f"en {u.territorio.title()}", None, None),
        ("Por semáforo", f"{n.get('ROJO', 0)} · {n.get('AMARILLO', 0)} · {n.get('VERDE', 0)}",
         "rojo · amarillo · verde", None, None),
        ("Costo estimado", f"${mios['costo_estimado'].astype(float).sum():,.0f}", "para atender todo lo abierto",
         None, None),
    ])
    with tarjeta("pendientes", f"Baches abiertos de {u.territorio.title()}", "Ordenados por IPU"):
        st.dataframe(con_icono(miles(mios[["id_bache", "ipu", "semaforo", "intervencion", "costo_estimado",
                                           "estado"]])),
                     hide_index=True, height=alto_tabla(len(mios)), column_config=COLUMNAS)
    sem = b.semaforo if pd.notna(b.semaforo) else None
    izq, der = st.columns(2, gap="medium")
    with izq, tarjeta("decidir"):
        st.markdown(f'<div class="paso"><span class="t"><span class="num">1</span>Decidir sobre la recomendación'
                    f'</span>{chip_html(*CHIP[sem]) if sem in CHIP else chip_html("neutro", "Sin IPU")}</div>',
                    unsafe_allow_html=True)
        if pd.isna(b.id_calculo):
            st.info("El bache aún no tiene IPU calculado.")
        else:
            st.write(f"SIPA recomienda **{b.semaforo}** (IPU {float(b.ipu):.3f}), {b.intervencion.lower()}, "
                     f"costo estimado {dinero(float(b.costo_estimado))}.")
            with st.form(f"decision_{id_bache}"):
                decision = st.radio("Decisión", ["APROBAR", "AJUSTAR", "RECHAZAR"], horizontal=True)
                ajustado = st.selectbox("Semáforo ajustado (solo si ajusta)", ["ROJO", "AMARILLO", "VERDE"])
                just = st.text_area("Justificación (obligatoria si ajusta o rechaza, 20 caracteres o más)")
                if st.form_submit_button("Registrar decisión"):
                    ok, msg, _ = registrar_decision(b.id_calculo, u.id_usuario, decision,
                                                    ajustado if decision == "AJUSTAR" else None, just or None)
                    if ok:
                        aviso_y_recargar(f"Decisión registrada para el bache {id_bache}: {decision}.")
                    st.error(f"No se registró: {msg}")
    with der, tarjeta("avance"):
        st.markdown(f'<div class="paso"><span class="t"><span class="num">2</span>Informar el avance</span>'
                    f'{chip_html("neutro", "Estado: " + b.estado)}</div>', unsafe_allow_html=True)
        actual = {v: k for k, v in ESTADOS.items()}[b.estado]
        opciones = [ESTADOS[x] for x in TRANSICIONES.get(actual, [])]
        with st.form(f"estado_{id_bache}_{b.estado}"):
            nuevo = st.selectbox(f"De {b.estado} a", opciones)
            coment = st.text_input("Comentario (obligatorio al descartar, 15 caracteres o más)")
            costo = st.number_input("Costo real de la reparación (solo al marcar REPARADO)", min_value=0.0,
                                    value=0.0, step=100.0)
            if st.form_submit_button("Actualizar estado"):
                id_nuevo = {v: k for k, v in ESTADOS.items()}[nuevo]
                ok, msg, _ = actualizar_estado(id_bache, u.id_usuario, id_nuevo, coment or None,
                                               costo if id_nuevo == 5 and costo > 0 else None)
                if ok:
                    aviso_y_recargar(f"Bache {id_bache}: estado actualizado a {nuevo}."
                                     + (" Se notificó por folio a los ciudadanos que lo reportaron."
                                        if id_nuevo in (5, 6) else ""))
                else:
                    st.error(f"La transacción se revirtió, no cambió nada: {msg}")


def pagina_indicadores():
    encabezado("Indicadores", "Reincidencia, causas y reportes resueltos salen de datos reales; decisiones, "
                              "reparaciones y tiempos son simulados (bd/08).")
    rein = reincidencia()
    tr = tiempos()
    cau = causas()
    res = resueltos()
    if "reportes" in res.columns:
        res = res[res["reportes"].astype(float) >= 500]
    peor = rein.iloc[0]
    sin = cau.set_index("causa_probable")["baches"].astype(float)
    pct_sin = sin.get("SIN_INDICIOS", 0) / sin.sum() * 100
    hallazgo(f"<b>Hallazgo:</b> en <b>{peor.territorio.title()}</b> el {float(peor.pct_reportes_en_cronicas):.0f} % "
             f"de los reportes cae en celdas crónicas (el bache vuelve a salir). En el {pct_sin:.0f} % de los "
             f"baches no hay indicios de causa: ahí la reparación superficial basta.")

    a, b = st.columns(2, gap="medium")
    with a:
        with tarjeta("reincidencia", "Reincidencia por territorio",
                     "% de reportes que caen en celdas crónicas (el bache vuelve a salir)"):
            ver_barras(rein, "pct_reportes_en_cronicas", "territorio", "% de reportes en celdas crónicas",
                       formato=".1f")
            with st.expander("Ver la tabla completa"):
                st.dataframe(rein[["territorio", "celdas", "celdas_reincidentes", "celdas_cronicas",
                                   "pct_reportes_en_cronicas"]], hide_index=True, column_config=COLUMNAS)
        with tarjeta("causas", "Causa probable del daño", "Hipótesis por cruce con lluvia, drenaje y tránsito"):
            st.altair_chart(barra_segmentada(cau, "baches", "causa_probable"), use_container_width=True)
            leyenda_segmentada(cau, "baches", "causa_probable")
    with b:
        with tarjeta("tiempos", "Tiempo de respuesta contra la meta",
                     "Barra: días promedio para reparar · marca negra: meta del semáforo"):
            st.altair_chart(barra_contra_meta(tr), use_container_width=True)
            with st.expander("Ver la tabla"):
                st.dataframe(tr[["semaforo_final", "baches", "dias_promedio", "meta_dias", "pct_en_meta"]],
                             hide_index=True, column_config=COLUMNAS)
        with tarjeta("cobertura", "Cobertura: baches reparados por territorio", "% del total de cada territorio"):
            ver_barras(cobertura(), "pct_reparados", "territorio", "% de baches reparados", formato=".0f")
        with tarjeta("resueltos", "Reportes ciudadanos resueltos por año",
                     "Solo años con 500 reportes o más (CDMX 2019–2022); 2025–2026 son pocos reportes de "
                     "Chalco aún en curso"):
            st.altair_chart(barras(res.rename(columns={"anio": "Año"}), "pct_resueltos", "Año", "% resueltos",
                                   formato=".1f", orden="ascending", etiquetas=4), use_container_width=True)


PAGINAS = {"Resumen": pagina_resumen, "Modo ciudadano": pagina_ciudadano,
           "Recomendación de SIPA": pagina_ranking, "Modo autoridad": pagina_autoridad,
           "Indicadores": pagina_indicadores}
# ?p=2 abre directamente la tercera sección (útil para capturas y para la exposición)
inicial = int(st.query_params.get("p", 0)) if str(st.query_params.get("p", 0)).isdigit() else 0
pagina = menu_lateral(inicial)
barra_superior(pagina)
mostrar_aviso()
PAGINAS[pagina]()
