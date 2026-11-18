"""
SIPA · Pruebas de la base de datos (procedimientos, vistas y DW).

Comprueban los criterios de cierre de la auditoría (observaciones_codex.md):
C02 territorio y actor, C03 vinculación de reportes, C06 corte de reincidencia
y C07 tiempos de atención.

Base desechable: igual que las pruebas E2E, se copia SIPA a SIPA_PRUEBAS_BD_<id único>
(respaldo COPY_ONLY) y todas las escrituras van ahí; al final se borra. La
única prueba que lee SIPA y SIPA_DW reales es de solo lectura.

Uso (desde la carpeta del proyecto, con la base instalada):
    python -m pytest bd/pruebas_bd.py -v
"""
import os
import uuid

import pyodbc
import pytest

SERVIDOR = os.environ.get("SIPA_SERVIDOR", "localhost")
# Nombre único por corrida: las pruebas solo borran la base que ellas mismas crearon.
BD = f"SIPA_PRUEBAS_BD_{uuid.uuid4().hex[:8]}"


def conectar(base):
    return pyodbc.connect(f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVIDOR};DATABASE={base};"
                          "Trusted_Connection=yes", autocommit=True)


def ejecutar(cx, sql, *params):
    cur = cx.cursor()
    cur.execute(sql, params)
    while cur.description is None and cur.nextset():
        pass
    return cur


def borrar(cx):
    ejecutar(cx, f"IF DB_ID('{BD}') IS NOT NULL BEGIN ALTER DATABASE {BD} SET SINGLE_USER WITH ROLLBACK "
                 f"IMMEDIATE; DROP DATABASE {BD}; END")


@pytest.fixture(scope="module")
def cx():
    m = conectar("master")
    assert ejecutar(m, f"SELECT DB_ID('{BD}')").fetchone()[0] is None, f"ya existe {BD}; no se toca"
    ejecutar(m, f"""
        DECLARE @dir NVARCHAR(400) = CAST(SERVERPROPERTY('InstanceDefaultBackupPath') AS NVARCHAR(400)) + N'\\';
        DECLARE @datos NVARCHAR(400) = CAST(SERVERPROPERTY('InstanceDefaultDataPath') AS NVARCHAR(400));
        DECLARE @bak NVARCHAR(400) = @dir + N'{BD}.bak';
        DECLARE @d NVARCHAR(128), @l NVARCHAR(128);
        SELECT @d = name FROM SIPA.sys.database_files WHERE type_desc = 'ROWS';
        SELECT @l = name FROM SIPA.sys.database_files WHERE type_desc = 'LOG';
        BACKUP DATABASE SIPA TO DISK = @bak WITH COPY_ONLY, INIT, FORMAT;
        DECLARE @mdf NVARCHAR(400) = @datos + N'{BD}.mdf', @ldf NVARCHAR(400) = @datos + N'{BD}_log.ldf';
        RESTORE DATABASE {BD} FROM DISK = @bak WITH MOVE @d TO @mdf, MOVE @l TO @ldf, REPLACE, RECOVERY;
        ALTER DATABASE {BD} SET RECOVERY SIMPLE;""")
    c = conectar(BD)
    yield c
    c.close()
    borrar(m)
    m.close()


def reportar(cx, colonia, lat, lon):
    fila = ejecutar(cx, "SET NOCOUNT ON; DECLARE @r INT, @b INT; "
                        "EXEC sp_registrar_reporte 2, ?, ?, ?, 'prueba', @r OUTPUT, @b OUTPUT; "
                        "SELECT @r, @b, (SELECT celda_id FROM reporte WHERE id_reporte = @r);",
                    colonia, lat, lon).fetchone()
    return fila[0], fila[1], fila[2]


def colonia(cx, nombre):
    return ejecutar(cx, "SELECT TOP 1 id_colonia FROM colonia WHERE nombre LIKE ?", nombre + "%").fetchone()[0]


def error_sql(cx, sql, *params):
    with pytest.raises(pyodbc.Error) as e:
        ejecutar(cx, sql, *params)
    return str(e.value)


# --- C03 · Vinculación de reportes ---------------------------------------------

def test_dos_puntos_separados_en_una_celda_son_casos_distintos(cx):
    lv = colonia(cx, "LINDAVISTA I")
    cel = ejecutar(cx, """SELECT TOP 1 celda_id, latitud, longitud FROM celda
                          ORDER BY SQUARE(latitud - 19.4992) + SQUARE(longitud + 99.1308)""").fetchone()
    lat, lon = float(cel[1]), float(cel[2])
    _, b1, c1 = reportar(cx, lv, lat + 0.0003, lon)        # ≈ 33 m al norte del centro
    _, b2, c2 = reportar(cx, lv, lat - 0.0003, lon)        # ≈ 33 m al sur: 66 m entre ambos
    assert c1 == c2 == cel[0], "los dos puntos deben caer en la misma celda"
    assert b1 != b2, "dos baches a 66 m no deben fusionarse aunque compartan celda"


def test_duplicado_cercano_se_liga_aunque_cruce_el_borde_de_celda(cx):
    lv = colonia(cx, "LINDAVISTA I")
    a = ejecutar(cx, """SELECT TOP 1 celda_id, latitud, longitud FROM celda
                        ORDER BY SQUARE(latitud - 19.4950) + SQUARE(longitud + 99.1350)""").fetchone()
    b = ejecutar(cx, """SELECT TOP 1 celda_id, latitud, longitud FROM celda
                        WHERE latitud = ? AND longitud > ? ORDER BY longitud""", a[1], a[2]).fetchone()
    lat, medio = float(a[1]), (float(a[2]) + float(b[2])) / 2
    _, b1, c1 = reportar(cx, lv, lat, medio - 0.00004)     # ≈ 4 m a cada lado del borde
    _, b2, c2 = reportar(cx, lv, lat, medio + 0.00004)
    assert c1 != c2, "los puntos deben quedar en celdas distintas"
    assert b1 == b2, "un duplicado a ≈ 8 m debe conservar el bache existente"


def test_coordenadas_ajenas_a_la_colonia_se_rechazan(cx):
    lv = colonia(cx, "LINDAVISTA I")                        # norte de la CDMX
    msg = error_sql(cx, "DECLARE @r INT, @b INT; EXEC sp_registrar_reporte 2, ?, 19.30, -99.10, 'x', "
                        "@r OUTPUT, @b OUTPUT;", lv)       # ≈ 22 km al sur
    assert "3 km" in msg


def test_fuera_de_la_cuadricula_se_rechaza(cx):
    sin = ejecutar(cx, """SELECT TOP 1 c.id_colonia FROM colonia c
                          WHERE NOT EXISTS (SELECT 1 FROM reporte r WHERE r.id_colonia = c.id_colonia)""").fetchone()
    assert sin, "se necesita una colonia sin reportes"
    msg = error_sql(cx, "DECLARE @r INT, @b INT; EXEC sp_registrar_reporte 2, ?, 25.0, -100.0, 'x', "
                        "@r OUTPUT, @b OUTPUT;", sin[0])
    assert "fuera de la zona" in msg


# --- C02 · Identidad y territorio ------------------------------------------------

def bache_y_autoridades(cx):
    """Un bache PRIORIZADO con su cálculo, una autoridad de su territorio y otra de otro territorio."""
    f = ejecutar(cx, """
        SELECT TOP 1 b.id_bache, cp.id_calculo, u.id_usuario AS propia, o.id_usuario AS ajena
        FROM bache b
        CROSS APPLY (SELECT TOP 1 id_calculo FROM calculo_prioridad x WHERE x.id_bache = b.id_bache
                     ORDER BY id_calculo DESC) cp
        CROSS APPLY (SELECT TOP 1 u.id_usuario FROM usuario u WHERE u.rol = 'AUTORIDAD'
                     AND dbo.fn_autoridad_puede(u.id_usuario, b.id_bache) = 1) u
        CROSS APPLY (SELECT TOP 1 u.id_usuario FROM usuario u WHERE u.rol = 'AUTORIDAD'
                     AND dbo.fn_autoridad_puede(u.id_usuario, b.id_bache) = 0) o
        WHERE b.id_estado_bache = 3 ORDER BY b.id_bache""").fetchone()
    assert f
    return f


def test_sin_identidad_autorizada_se_rechaza(cx):
    _, calc, _, _ = bache_y_autoridades(cx)
    analista = ejecutar(cx, "SELECT TOP 1 id_usuario FROM usuario WHERE rol = 'ANALISTA'").fetchone()[0]
    for usuario in (None, -1, analista):
        msg = error_sql(cx, "DECLARE @d INT; EXEC sp_registrar_decision ?, ?, 'APROBAR', NULL, NULL, @d OUTPUT;",
                        calc, usuario)
        assert "autoridad activa" in msg


def test_autoridad_de_otro_territorio_no_decide_ni_actualiza(cx):
    bache, calc, _, ajena = bache_y_autoridades(cx)
    msg = error_sql(cx, "DECLARE @d INT; EXEC sp_registrar_decision ?, ?, 'APROBAR', NULL, NULL, @d OUTPUT;",
                    calc, ajena)
    assert "de su territorio" in msg
    msg = error_sql(cx, "EXEC sp_actualizar_estado_bache ?, ?, 4, 'x';", bache, ajena)
    assert "de su territorio" in msg


def test_la_decision_registra_al_actor(cx):
    _, calc, propia, _ = bache_y_autoridades(cx)
    d = ejecutar(cx, "SET NOCOUNT ON; DECLARE @d INT; EXEC sp_registrar_decision ?, ?, 'APROBAR', NULL, NULL, "
                     "@d OUTPUT; SELECT id_usuario FROM decision_humana WHERE id_decision = @d;",
                 calc, propia).fetchone()
    assert d[0] == propia


# --- C07 · Tiempos de atención ---------------------------------------------------

def test_decision_posterior_a_la_reparacion(cx):
    fila = ejecutar(cx, """SELECT TOP 1 v.id_bache, v.dias_atencion, v.fecha_decision, cp.id_calculo, d.id_usuario
                           FROM ind.v_tiempo_respuesta_bache v
                           CROSS APPLY (SELECT TOP 1 id_calculo FROM calculo_prioridad x
                                        WHERE x.id_bache = v.id_bache ORDER BY id_calculo DESC) cp
                           CROSS APPLY (SELECT TOP 1 dh.id_usuario FROM decision_humana dh
                                        JOIN calculo_prioridad c ON c.id_calculo = dh.id_calculo
                                        WHERE c.id_bache = v.id_bache) d
                           ORDER BY v.id_bache""").fetchone()
    bache, dias, fecha_dec, calc, autoridad = fila
    # El procedimiento ya no acepta decisiones sobre un bache reparado...
    msg = error_sql(cx, "DECLARE @d INT; EXEC sp_registrar_decision ?, ?, 'APROBAR', NULL, NULL, @d OUTPUT;",
                    calc, autoridad)
    assert "cerrado" in msg
    # ...y aunque se cuele una (p. ej. carga directa), el plazo no cambia ni se vuelve negativo.
    ejecutar(cx, "INSERT INTO decision_humana (id_calculo, id_usuario, decision, fecha) "
                 "VALUES (?, ?, 'APROBAR', DATEADD(DAY, 30, SYSDATETIME()))", calc, autoridad)
    despues = ejecutar(cx, "SELECT dias_atencion, fecha_decision FROM ind.v_tiempo_respuesta_bache "
                           "WHERE id_bache = ?", bache).fetchone()
    assert float(despues[0]) == float(dias) and despues[1] == fecha_dec
    assert ejecutar(cx, "SELECT COUNT(*) FROM ind.v_tiempo_respuesta_bache WHERE dias_atencion < 0").fetchone()[0] == 0


def test_tablero_y_dw_dan_el_mismo_tiempo():
    """Solo lectura sobre SIPA y SIPA_DW reales: misma regla en la vista y en el ETL."""
    c = conectar("SIPA")
    dif = ejecutar(c, """
        SELECT COUNT(*) FROM ind.v_tiempo_respuesta_bache v
        JOIN SIPA_DW.dw.fact_atencion f ON f.id_bache = v.id_bache
        WHERE f.estado = 'REPARADO'
          AND (ABS(f.horas_resolucion / 24.0 - v.dias_atencion) > 0.001 OR f.cumplio_meta <> v.en_meta)""").fetchone()[0]
    n = ejecutar(c, "SELECT COUNT(*) FROM SIPA_DW.dw.fact_atencion WHERE estado = 'REPARADO'").fetchone()[0]
    c.close()
    assert n > 0 and dif == 0


# --- C06 · Corte de reincidencia -------------------------------------------------

def test_reporte_nuevo_aparece_al_instante_y_el_corte_no_retrocede(cx):
    ejecutar(cx, "EXEC ind.sp_actualizar_reincidencia")
    antes = ejecutar(cx, "SELECT ultimo_id_reporte, fecha_corte FROM ind.corte_reincidencia").fetchone()
    r, _, _ = reportar(cx, colonia(cx, "LINDAVISTA I"), 19.4981, -99.1322)
    # sin ninguna actualización manual: el alta ya lo clasificó y movió el corte
    assert ejecutar(cx, "SELECT COUNT(*) FROM ind.reporte_reaparicion WHERE id_reporte = ?", r).fetchone()[0] == 1
    tras_alta = ejecutar(cx, "SELECT ultimo_id_reporte, fecha_corte FROM ind.corte_reincidencia").fetchone()
    assert tras_alta[0] == r > antes[0] and tras_alta[1] >= antes[1]
    tipo_incremental = ejecutar(cx, "SELECT tipo FROM ind.reporte_reaparicion WHERE id_reporte = ?", r).fetchone()[0]
    # dos reconstrucciones completas seguidas: misma clasificación y el corte no retrocede
    ejecutar(cx, "EXEC ind.sp_actualizar_reincidencia")
    ejecutar(cx, "EXEC ind.sp_actualizar_reincidencia")
    final = ejecutar(cx, "SELECT ultimo_id_reporte, fecha_corte FROM ind.corte_reincidencia").fetchone()
    assert final[0] == r and final[1] >= tras_alta[1]
    assert ejecutar(cx, "SELECT tipo FROM ind.reporte_reaparicion WHERE id_reporte = ?", r).fetchone()[0] \
        == tipo_incremental


# --- C09 · Copia pública ---------------------------------------------------------

def test_copia_publica_excluye_datos_personales():
    """Un comentario con datos personales no sale en el paquete público; los indicadores siguen."""
    import sys
    from pathlib import Path
    import pandas as pd
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
    from exportar_datos_tablero import hacer_publico

    seg = pd.DataFrame({"id_bache": [1], "fecha": ["2026-01-01"], "de_estado": ["PRIORIZADO"],
                        "a_estado": ["REPARADO"], "comentario": ["Lo atendió Juan Pérez, tel. 55 1234 5678"]})
    pub = hacer_publico("seguimiento", seg)
    assert "Juan" not in pub.to_csv() and "5678" not in pub.to_csv()
    assert pub["comentario"].iloc[0] == "Reparado."
    aut = hacer_publico("autoridades", pd.DataFrame({"id_usuario": [1], "nombre": ["Lic. María López"],
                                                     "territorio": ["CHALCO"]}))
    assert aut["nombre"].iloc[0] == "Autoridad de Chalco"
    with pytest.raises(SystemExit):                       # una columna no declarada detiene la exportación
        hacer_publico("reportes", pd.DataFrame({"id_reporte": [1], "fecha_solicitud": ["x"], "id_bache": [1],
                                                "descripcion": ["dato privado"]}))


# --- C02 · Modo OPERATIVO: identidad de la sesión ---------------------------------

def test_modo_operativo_toma_la_identidad_de_la_sesion(cx):
    bache, calc, propia, ajena = bache_y_autoridades(cx)
    decidir = "SET NOCOUNT ON; DECLARE @d INT; EXEC sp_registrar_decision ?, ?, 'APROBAR', NULL, NULL, @d OUTPUT; " \
              "SELECT id_usuario FROM decision_humana WHERE id_decision = @d;"
    login = ejecutar(cx, "SELECT ORIGINAL_LOGIN()").fetchone()[0]
    try:
        ejecutar(cx, "UPDATE configuracion SET valor = 'OPERATIVO' WHERE clave = 'modo'")
        # 1. La sesión no está asociada a ninguna autoridad: ni con un id válido se puede escribir
        assert "autenticada" in error_sql(cx, decidir, calc, propia)
        # 2. Se asocia el login de la sesión a la autoridad del territorio
        ejecutar(cx, "UPDATE usuario SET login_sql = ? WHERE id_usuario = ?", login, propia)
        assert ejecutar(cx, decidir, calc, None).fetchone()[0] == propia      # sin id: lo pone la sesión
        # 3. Hacerse pasar por otra autoridad se rechaza
        assert "autenticada" in error_sql(cx, decidir, calc, ajena)
        assert "autenticada" in error_sql(cx, "EXEC sp_actualizar_estado_bache ?, ?, 4, 'x';", bache, ajena)
    finally:
        ejecutar(cx, "UPDATE usuario SET login_sql = NULL WHERE login_sql = ?", login)
        ejecutar(cx, "UPDATE configuracion SET valor = 'DEMO' WHERE clave = 'modo'")


# --- C05 · El CSV de riesgo coincide con la tabla cargada --------------------------

def test_csv_de_riesgo_coincide_con_la_tabla():
    """Solo lectura sobre SIPA: lo cargado por 05b es el CSV versionado de Probabilidad."""
    from pathlib import Path
    import pandas as pd
    csv = pd.read_csv(Path(__file__).resolve().parent.parent / "probabilidad/resultados/t4_riesgo_72h_por_celda.csv")
    c = conectar("SIPA")
    cur = ejecutar(c, "SELECT celda_id, p72_accidente, semaforo_72h, v_riesgo_72h FROM riesgo_celda_72h")
    tabla = pd.DataFrame.from_records(cur.fetchall(), columns=[d[0] for d in cur.description])
    celdas = {r[0] for r in ejecutar(c, "SELECT celda_id FROM celda").fetchall()}
    c.close()
    esperado = csv[csv["celda_id"].isin(celdas)]
    assert len(tabla) == len(esperado) > 0
    u = esperado.merge(tabla, on="celda_id", suffixes=("_csv", "_bd"))
    assert len(u) == len(tabla)
    assert (u["p72_accidente_csv"] - u["p72_accidente_bd"].astype(float)).abs().max() < 1e-7
    assert (u["semaforo_72h_csv"] == u["semaforo_72h_bd"]).all()
    assert (u["v_riesgo_72h_csv"] - u["v_riesgo_72h_bd"].astype(float)).abs().max() < 1e-4


def test_altas_simultaneas_clasifican_igual_que_la_reconstruccion(cx):
    """Varias altas en paralelo en el mismo punto: la clasificación incremental coincide con la completa."""
    import threading
    lv = colonia(cx, "LINDAVISTA I")
    ids, errores = [], []

    def alta():
        try:
            c = conectar(BD)
            ids.append(reportar(c, lv, 19.4930, -99.1290)[0])
            c.close()
        except Exception as e:          # noqa: BLE001
            errores.append(e)

    hilos = [threading.Thread(target=alta) for _ in range(6)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    assert not errores and len(ids) == 6
    marcas = ",".join(str(i) for i in ids)
    antes = dict(ejecutar(cx, f"SELECT id_reporte, tipo FROM ind.reporte_reaparicion WHERE id_reporte IN ({marcas})")
                 .fetchall())
    assert sorted(antes.values()).count("NUEVO") == 1 and len(antes) == 6   # una abre, las demás son duplicado
    corte = ejecutar(cx, "SELECT ultimo_id_reporte FROM ind.corte_reincidencia").fetchone()[0]
    assert corte == max(ids)
    ejecutar(cx, "EXEC ind.sp_actualizar_reincidencia")
    despues = dict(ejecutar(cx, f"SELECT id_reporte, tipo FROM ind.reporte_reaparicion WHERE id_reporte IN ({marcas})")
                   .fetchall())
    assert antes == despues



def test_altas_en_puntos_distintos_con_reconstruccion_simultanea(cx):
    """Altas en puntos distintos mientras corre una reconstrucción completa: sin interbloqueos,
    sin huecos en el corte y misma clasificación que una reconstrucción posterior."""
    import threading
    lv = colonia(cx, "LINDAVISTA I")
    puntos = [(19.4900 + 0.0004 * i, -99.1250 - 0.0004 * (i % 3)) for i in range(8)]
    ids, errores = [], []

    def alta(lat, lon):
        try:
            c = conectar(BD)
            ids.append(reportar(c, lv, lat, lon)[0])
            c.close()
        except Exception as e:          # noqa: BLE001
            errores.append(e)

    def reconstruir():
        try:
            c = conectar(BD)
            ejecutar(c, "EXEC ind.sp_actualizar_reincidencia")
            c.close()
        except Exception as e:          # noqa: BLE001
            errores.append(e)

    hilos = [threading.Thread(target=alta, args=pt) for pt in puntos[:4]] + [threading.Thread(target=reconstruir)] \
        + [threading.Thread(target=alta, args=pt) for pt in puntos[4:]]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    assert not errores, errores
    corte = ejecutar(cx, "SELECT ultimo_id_reporte FROM ind.corte_reincidencia").fetchone()[0]
    assert corte == ejecutar(cx, "SELECT MAX(id_reporte) FROM reporte").fetchone()[0]
    sin_clasificar = ejecutar(cx, "SELECT COUNT(*) FROM reporte r WHERE r.latitud IS NOT NULL AND r.celda_id IS NOT "
                                  "NULL AND NOT EXISTS (SELECT 1 FROM ind.reporte_reaparicion x "
                                  "WHERE x.id_reporte = r.id_reporte)").fetchone()[0]
    assert sin_clasificar == 0
    marcas = ",".join(str(i) for i in ids)
    antes = dict(ejecutar(cx, f"SELECT id_reporte, tipo FROM ind.reporte_reaparicion WHERE id_reporte IN ({marcas})")
                 .fetchall())
    ejecutar(cx, "EXEC ind.sp_actualizar_reincidencia")
    despues = dict(ejecutar(cx, f"SELECT id_reporte, tipo FROM ind.reporte_reaparicion WHERE id_reporte IN ({marcas})")
                   .fetchall())
    assert antes == despues and len(antes) == 8
