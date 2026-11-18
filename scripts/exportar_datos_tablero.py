"""
SIPA - Exporta la copia de solo consulta que usa el tablero en línea (GitHub Pages).

El tablero en línea corre en el navegador con stlite y no puede conectarse a SQL
Server, así que lee estos CSV. Se generan desde la base SIPA ya construida
(bd/ejecutar_todo.ps1), con los mismos datos que los documentos.

Política de publicación (la copia es pública en GitHub Pages):
  - Solo salen las columnas de PUBLICAS; una columna nueva en una consulta
    detiene la exportación hasta que se declare aquí a propósito.
  - Autoridades: etiqueta genérica «Autoridad de <territorio>», nunca nombres.
  - Seguimiento: no se publica el comentario libre (podría traer datos
    personales); se sustituye por un texto fijo según el cambio de estado.
  - Baches: coordenadas redondeadas a 3 decimales (≈ 100 m).
  - Reportes: folio, fecha y bache; sin descripción ni coordenadas exactas.

Uso (desde la carpeta del proyecto):
    python scripts/exportar_datos_tablero.py
Salida:
    tablero/datos/*.csv
"""
import os
from pathlib import Path

import pandas as pd
import pyodbc

SALIDA = Path("tablero/datos")

CONSULTAS = {
    "baches": """
        SELECT b.id_bache, ct.territorio, b.celda_id, b.latitud, b.longitud, b.severidad, b.profundidad_cm,
               b.area_m2, e.nombre AS estado, cp.id_calculo, cp.ipu, cp.semaforo,
               t.nombre AS intervencion, cp.costo_estimado,
               (SELECT COUNT(*) FROM reporte r WHERE r.id_bache = b.id_bache) AS reportes
        FROM bache b
        JOIN cat_estado_bache e ON e.id_estado_bache = b.id_estado_bache
        LEFT JOIN ind.v_celda_territorio ct ON ct.celda_id = b.celda_id
        OUTER APPLY (SELECT TOP 1 * FROM calculo_prioridad x WHERE x.id_bache = b.id_bache
                     ORDER BY x.id_calculo DESC) cp
        LEFT JOIN tarifa_reparacion t ON t.clave = cp.clave_tarifa""",
    # desglose del último cálculo de cada bache
    "detalle": """
        SELECT d.id_calculo, c.nombre AS criterio, d.valor_normalizado AS valor, d.peso_aplicado AS peso,
               CAST(d.valor_normalizado * d.peso_aplicado AS DECIMAL(5,4)) AS aporte
        FROM detalle_calculo d JOIN criterio_ipu c ON c.id_criterio = d.id_criterio
        WHERE d.id_calculo IN (SELECT MAX(id_calculo) FROM calculo_prioridad GROUP BY id_bache)""",
    "colonias": """
        SELECT c.id_colonia, CONCAT(c.nombre, ' · ', t.nombre) AS nombre
        FROM colonia c JOIN territorio t ON t.id_territorio = c.id_territorio ORDER BY 2""",
    "autoridades": """
        SELECT u.id_usuario, u.nombre, t.nombre AS territorio FROM usuario u
        JOIN territorio t ON t.id_territorio = u.id_territorio
        WHERE u.rol = 'AUTORIDAD' ORDER BY t.nombre""",
    "reportes": "SELECT id_reporte, fecha_solicitud, id_bache FROM reporte",
    # semáforo decidido por la autoridad (última decisión sobre el último cálculo)
    "decisiones": """
        SELECT cp.id_bache, COALESCE(d.semaforo_ajustado, cp.semaforo) AS prioridad_decidida
        FROM calculo_prioridad cp
        CROSS APPLY (SELECT TOP 1 semaforo_ajustado FROM decision_humana dh
                     WHERE dh.id_calculo = cp.id_calculo ORDER BY dh.fecha DESC) d
        WHERE cp.id_calculo IN (SELECT MAX(id_calculo) FROM calculo_prioridad GROUP BY id_bache)""",
    "seguimiento": """
        SELECT s.id_bache, s.fecha, ea.nombre AS de_estado, en.nombre AS a_estado, s.comentario
        FROM seguimiento_bache s
        JOIN cat_estado_bache ea ON ea.id_estado_bache = s.id_estado_anterior
        JOIN cat_estado_bache en ON en.id_estado_bache = s.id_estado_nuevo""",
    "tiempos": """SELECT semaforo_final, baches, dias_promedio, dias_min, dias_max, meta_dias, pct_en_meta
                  FROM ind.v_tiempo_respuesta_semaforo""",
    "costo_pendiente": """SELECT territorio, baches_pendientes, costo_total, costo_rojos, costo_amarillos
                          FROM ind.v_costo_pendiente_territorio""",
    "reincidencia": """SELECT territorio, celdas, celdas_reincidentes, celdas_cronicas, pct_reportes_en_cronicas
                       FROM ind.v_reincidencia_territorio""",
    "causas": "SELECT causa_probable, COUNT(*) AS baches FROM ind.v_causa_probable_bache GROUP BY causa_probable",
    "cobertura": "SELECT territorio, pct_reparados FROM ind.v_cobertura_territorio",
    "resueltos": """SELECT anio, SUM(reportes) AS reportes, CAST(100.0 * SUM(resueltos) / SUM(reportes) AS DECIMAL(5,1)) AS pct_resueltos
                    FROM ind.v_cobertura_reportes_anual GROUP BY anio""",
}


PUBLICAS = {
    "baches": ["id_bache", "territorio", "celda_id", "latitud", "longitud", "severidad", "profundidad_cm",
               "area_m2", "estado", "id_calculo", "ipu", "semaforo", "intervencion", "costo_estimado", "reportes"],
    "detalle": ["id_calculo", "criterio", "valor", "peso", "aporte"],
    "colonias": ["id_colonia", "nombre"],
    "autoridades": ["id_usuario", "nombre", "territorio"],
    "reportes": ["id_reporte", "fecha_solicitud", "id_bache"],
    "decisiones": ["id_bache", "prioridad_decidida"],
    "seguimiento": ["id_bache", "fecha", "de_estado", "a_estado", "comentario"],
    "tiempos": ["semaforo_final", "baches", "dias_promedio", "dias_min", "dias_max", "meta_dias", "pct_en_meta"],
    "costo_pendiente": ["territorio", "baches_pendientes", "costo_total", "costo_rojos", "costo_amarillos"],
    "reincidencia": ["territorio", "celdas", "celdas_reincidentes", "celdas_cronicas", "pct_reportes_en_cronicas"],
    "causas": ["causa_probable", "baches"],
    "cobertura": ["territorio", "pct_reparados"],
    "resueltos": ["anio", "reportes", "pct_resueltos"],
}

TEXTO_SEGUIMIENTO = {
    "VALIDADO": "Validado en inspección.", "EN_ATENCION": "Programado por la autoridad.",
    "REPARADO": "Reparado.", "DESCARTADO": "Descartado por la autoridad.",
}


def hacer_publico(nombre, df):
    """Aplica la política de publicación a una tabla exportada."""
    if nombre not in PUBLICAS:
        raise SystemExit(f"{nombre}: tabla no declarada como pública")
    permitidas = PUBLICAS[nombre]                 # todas las tablas tienen lista explícita, sin excepciones
    extra = set(df.columns) - set(permitidas)
    if extra:
        raise SystemExit(f"{nombre}: columnas no declaradas como públicas: {sorted(extra)}")
    df = df[permitidas].copy()
    if nombre == "autoridades":
        df["nombre"] = "Autoridad de " + df["territorio"].str.title()
    if nombre == "seguimiento":
        df["comentario"] = df["a_estado"].map(TEXTO_SEGUIMIENTO).fillna("Cambio de estado.")
    if nombre == "baches":
        df["latitud"] = pd.to_numeric(df["latitud"]).round(3)
        df["longitud"] = pd.to_numeric(df["longitud"]).round(3)
    return df


def main():
    SALIDA.mkdir(parents=True, exist_ok=True)
    cx = pyodbc.connect("DRIVER={ODBC Driver 17 for SQL Server};SERVER=" + os.environ.get("SIPA_SERVIDOR", "localhost") + ";DATABASE=SIPA;"
                        "Trusted_Connection=yes")
    for nombre, sql in CONSULTAS.items():
        cur = cx.cursor()
        cur.execute(sql)
        df = pd.DataFrame.from_records(cur.fetchall(), columns=[c[0] for c in cur.description])
        df = hacer_publico(nombre, df)
        df.to_csv(SALIDA / f"{nombre}.csv", index=False, encoding="utf-8")
        print(f"{nombre:16} {len(df):>7,} filas")
    cx.close()


if __name__ == "__main__":
    main()
