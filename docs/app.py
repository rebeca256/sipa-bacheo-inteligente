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
COLOR = {"ROJO": [211, 47, 47], "AMARILLO": [249, 168, 37], "VERDE": [56, 142, 60]}
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

st.set_page_config(page_title="SIPA · Tablero", page_icon="🛣️", layout="wide")


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


def estilo(g):
    """Estilo común: letra legible, cuadrícula suave y sin borde."""
    return (g.configure_axis(labelFontSize=12, titleFontSize=12, gridColor="#EEEEEE", domain=False,
                             tickColor="#DDDDDD", labelColor="#444444", titleColor="#666666")
             .configure_view(strokeWidth=0))


def barras(df, valor, etiqueta, titulo, color="#1565C0", formato=",.0f", maximo=None, orden="-x"):
    """Barras horizontales delgadas, de mayor a menor, con el valor escrito al final.
    La altura depende del número de barras (24 px cada una)."""
    df = df.copy()
    df[valor] = df[valor].astype(float)
    df = df.sort_values(valor, ascending=False)
    if maximo:
        df = df.head(maximo)
    base = alt.Chart(df).encode(
        y=alt.Y(f"{etiqueta}:N", sort=list(df[etiqueta]) if orden == "-x" else orden, title=None, axis=alt.Axis(labelLimit=200, ticks=False, labelOverlap=False)),
        x=alt.X(f"{valor}:Q", title=titulo, scale=alt.Scale(domainMax=float(df[valor].max()) * 1.18 or 1), axis=alt.Axis(tickCount=4, format="~s" if "$" in formato else formato)),
        tooltip=[alt.Tooltip(f"{etiqueta}:N", title=" "),
                 alt.Tooltip(f"{valor}:Q", format=formato, title=titulo)])
    g = base.mark_bar(color=color, size=14, cornerRadiusEnd=3) + base.mark_text(
        align="left", dx=4, fontSize=11, color="#555555").encode(text=alt.Text(f"{valor}:Q", format=formato))
    return estilo(g.properties(height=alt.Step(26)))


def ver_barras(df, valor, etiqueta, titulo, top=10, **kw):
    """Muestra las 10 primeras barras y deja ver el resto con un interruptor."""
    todos = len(df) > top and st.toggle(f"Ver los {len(df)}", key=f"todos_{etiqueta}_{valor}")
    st.altair_chart(barras(df, valor, etiqueta, titulo, maximo=None if todos else top, **kw),
                    use_container_width=True)


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
    st.title("SIPA · Sistema Inteligente de Priorización Asfáltica")
    st.caption("SIPA asesora: recomienda qué bache atender primero, por qué y cuánto costaría. "
               "La reparación la hace la autoridad.")
    df = baches()
    abiertos = df[df["estado"].isin(["VALIDADO", "PRIORIZADO", "EN_ATENCION"])]
    tr = tiempos()
    rojos_meta = tr.loc[tr["semaforo_final"] == "ROJO", "pct_en_meta"]
    c = st.columns(5)
    c[0].metric("Reportes en la base", f"{total_reportes():,}")
    c[1].metric("Baches abiertos", f"{len(abiertos):,}")
    n = abiertos["semaforo"].value_counts()
    c[2].metric("Rojo · amarillo", f"{n.get('ROJO', 0)} · {n.get('AMARILLO', 0)}",
                help=f"Baches abiertos por semáforo ({n.get('VERDE', 0):,} más en verde). Si no hay rojos es porque todos los rojos ya "
                     "pasaron a reparación (decisiones simuladas en bd/08).")
    c[3].metric("Costo pendiente", f"${abiertos['costo_estimado'].astype(float).sum() / 1e6:,.2f} M",
                help="Costo estimado para atender todos los baches abiertos.")
    c[4].metric("Rojos reparados en ≤ 3 días", f"{float(rojos_meta.iloc[0]):.0f} %" if len(rojos_meta) else "—")

    izq, der = st.columns([3, 2])
    with izq:
        st.subheader("Mapa de prioridades (baches abiertos)")
        territorio = st.selectbox("Territorio", ["Todos"] + sorted(abiertos["territorio"].dropna().unique()))
        vista = abiertos if territorio == "Todos" else abiertos[abiertos["territorio"] == territorio]
        mapa(vista)
        st.caption("Rojo: atender en 3 días · Amarillo: en 15 · Verde: programar en 60. "
                   "El tamaño del punto crece con el IPU.")
    with der:
        st.subheader("Costo pendiente por territorio")
        cp = costo_pendiente().copy()
        cp["costo_total"] = cp["costo_total"].astype(float)
        ver_barras(cp, "costo_total", "territorio", "Costo estimado", color="#EF6C00", formato="$,.0f")


def pagina_ciudadano():
    st.title("Modo ciudadano")
    st.caption("No necesita cuenta. El reporte se liga al bache que ya exista en la misma celda de 250 m.")
    izq, der = st.columns(2)
    with izq:
        st.subheader("Reportar un bache")
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
    with der:
        st.subheader("Consultar mi folio")
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


def ficha(id_bache):
    b = baches().set_index("id_bache").loc[id_bache]
    c = st.columns(4)
    c[0].metric("IPU", f"{float(b.ipu):.3f}" if pd.notna(b.ipu) else "—")
    c[1].metric("Semáforo", b.semaforo if pd.notna(b.semaforo) else "—")
    c[2].metric("Intervención", CORTO.get(b.intervencion, b.intervencion if pd.notna(b.intervencion) else "—"),
                help=b.intervencion if pd.notna(b.intervencion) else None)
    c[3].metric("Costo estimado", dinero(float(b.costo_estimado)) if pd.notna(b.costo_estimado) else "—")
    if pd.notna(b.id_calculo):
        det = detalle(int(b.id_calculo))
        st.write("**Ficha de justificación:** cuánto aporta cada criterio al IPU. Un valor de 0.5 indica "
                 "que no hay dato para ese criterio (neutral).")
        st.altair_chart(barras(det, "aporte", "criterio", "Aporte al IPU (valor × peso)", formato=".3f"),
                        use_container_width=True)
        with st.expander("Ver los valores y pesos de cada criterio"):
            st.dataframe(det, hide_index=True)
    st.caption(f"{b.territorio} · celda {b.celda_id} · severidad {b.severidad} · {b.profundidad_cm} cm · "
               f"{b.area_m2} m² · {b.reportes} reportes · estado {b.estado}")


def pagina_ranking():
    st.title("Recomendación de SIPA")
    df = baches()
    abiertos = df[df["estado"].isin(["VALIDADO", "PRIORIZADO", "EN_ATENCION"]) & df["ipu"].notna()].copy()
    territorios = sorted(abiertos["territorio"].dropna().unique())
    territorio = st.selectbox("Territorio", territorios, index=territorios.index("CHALCO"))
    rank = abiertos[abiertos["territorio"] == territorio].sort_values("ipu", ascending=False)
    rank.insert(0, "lugar", range(1, len(rank) + 1))
    st.dataframe(miles(rank[["lugar", "id_bache", "ipu", "semaforo", "intervencion", "costo_estimado",
                             "reportes", "estado"]]), hide_index=True, height=280, column_config=COLUMNAS)
    st.caption("Fíjese en la columna de reportes: más reportes no significa más prioridad.")
    id_bache = st.selectbox("Ver la ficha del bache", rank["id_bache"])
    ficha(id_bache)
    if st.button("Recalcular el IPU de este bache"):
        ok, msg, _ = recalcular_ipu(id_bache)
        if ok:
            aviso_y_recargar(f"IPU del bache {id_bache} recalculado (queda como un cálculo nuevo; "
                             "el anterior se conserva).")
        st.error(msg)


def pagina_autoridad():
    st.title("Modo autoridad")
    st.caption("La autoridad decide sobre la recomendación y repara con sus propios recursos; "
               "en SIPA solo informa el avance.")
    usuarios = autoridades()
    nombre = st.selectbox("Entrar como", usuarios["nombre"],
                          index=int((usuarios["territorio"] == "CHALCO").idxmax()))
    u = usuarios[usuarios["nombre"] == nombre].iloc[0]
    df = baches()
    mios = df[(df["territorio"] == u.territorio) & df["estado"].isin(["REPORTADO", "VALIDADO", "PRIORIZADO",
                                                                      "EN_ATENCION"])]
    mios = mios.sort_values("ipu", ascending=False)
    st.dataframe(miles(mios[["id_bache", "ipu", "semaforo", "intervencion", "costo_estimado", "estado"]]),
                 hide_index=True, height=240, column_config=COLUMNAS)
    if mios.empty:
        st.info("No hay baches abiertos en este territorio.")
        return
    id_bache = st.selectbox("Bache", mios["id_bache"], key=f"bache_autoridad_{u.id_usuario}")
    b = mios.set_index("id_bache").loc[id_bache]
    izq, der = st.columns(2)
    with izq:
        st.subheader("1. Decidir sobre la recomendación")
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
    with der:
        st.subheader("2. Informar el avance")
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
    st.title("Indicadores")
    st.caption("Las decisiones, reparaciones y tiempos son simulados (bd/08); reincidencia y reportes "
               "resueltos salen de datos reales.")
    a, b = st.columns(2)
    with a:
        st.subheader("Reincidencia: celdas donde el bache vuelve a salir")
        st.dataframe(reincidencia()[["territorio", "celdas", "celdas_reincidentes", "celdas_cronicas",
                                     "pct_reportes_en_cronicas"]], hide_index=True, column_config=COLUMNAS)
        st.subheader("Causa probable del daño (hipótesis)")
        ver_barras(causas(), "baches", "causa_probable", "Baches", color="#6D4C41")
    with b:
        st.subheader("Tiempo de respuesta por semáforo")
        st.dataframe(tiempos()[["semaforo_final", "baches", "dias_promedio", "meta_dias", "pct_en_meta"]],
                     hide_index=True, column_config=COLUMNAS)
        st.subheader("Cobertura: baches reparados por territorio")
        ver_barras(cobertura(), "pct_reparados", "territorio", "% de baches reparados", color="#2E7D32",
                   formato=".0f")
        st.subheader("Reportes ciudadanos resueltos por año")
        res = resueltos()
        if "reportes" in res.columns:
            res = res[res["reportes"].astype(float) >= 500]
        st.altair_chart(barras(res.rename(columns={"anio": "Año"}), "pct_resueltos", "Año", "% resueltos",
                               formato=".1f", orden="ascending"), use_container_width=True)
        st.caption("Solo años con 500 reportes o más (CDMX 2019–2022). 2025–2026 son pocos reportes de "
                   "Chalco aún en curso y no son comparables.")


PAGINAS = {"Resumen y mapa": pagina_resumen, "Modo ciudadano": pagina_ciudadano,
           "Recomendación de SIPA": pagina_ranking, "Modo autoridad": pagina_autoridad,
           "Indicadores": pagina_indicadores}
with st.sidebar:
    st.header("SIPA")
    # ?p=2 abre directamente la tercera sección (útil para capturas y para la exposición)
    inicial = int(st.query_params.get("p", 0)) if str(st.query_params.get("p", 0)).isdigit() else 0
    pagina = st.radio("Sección", list(PAGINAS), index=min(inicial, len(PAGINAS) - 1))
    st.divider()
    if EN_LINEA:
        st.info("Versión en línea de solo consulta (copia de los datos). Las acciones revisan las reglas, "
                "pero no guardan cambios.")
    st.caption("Prototipo funcional · Bacheo inteligente y priorización urbana · UNRC LCDN 2026-2")
mostrar_aviso()
PAGINAS[pagina]()
