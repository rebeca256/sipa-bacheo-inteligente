"""
SIPA - Exporta la copia de solo consulta que usa el tablero en línea (GitHub Pages).

El tablero en línea corre en el navegador con stlite y no puede conectarse a SQL
Server, así que lee estos CSV. Se generan desde la base SIPA ya construida
(bd/ejecutar_todo.ps1), con los mismos datos que los documentos.

Uso (desde la carpeta del proyecto):
    python scripts/exportar_datos_tablero.py
Salida:
    tablero/datos/*.csv
"""
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
    "tiempos": "SELECT * FROM ind.v_tiempo_respuesta_semaforo",
    "costo_pendiente": """SELECT territorio, baches_pendientes, costo_total, costo_rojos, costo_amarillos
                          FROM ind.v_costo_pendiente_territorio""",
    "reincidencia": """SELECT territorio, celdas, celdas_reincidentes, celdas_cronicas, pct_reportes_en_cronicas
                       FROM ind.v_reincidencia_territorio""",
    "causas": "SELECT causa_probable, COUNT(*) AS baches FROM ind.v_causa_probable_bache GROUP BY causa_probable",
    "cobertura": "SELECT territorio, pct_reparados FROM ind.v_cobertura_territorio",
    "resueltos": """SELECT anio, CAST(100.0 * SUM(resueltos) / SUM(reportes) AS DECIMAL(5,1)) AS pct_resueltos
                    FROM ind.v_cobertura_reportes_anual GROUP BY anio""",
}


def main():
    SALIDA.mkdir(parents=True, exist_ok=True)
    cx = pyodbc.connect("DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=SIPA;"
                        "Trusted_Connection=yes")
    for nombre, sql in CONSULTAS.items():
        cur = cx.cursor()
        cur.execute(sql)
        df = pd.DataFrame.from_records(cur.fetchall(), columns=[c[0] for c in cur.description])
        df.to_csv(SALIDA / f"{nombre}.csv", index=False, encoding="utf-8")
        print(f"{nombre:16} {len(df):>7,} filas")
    cx.close()


if __name__ == "__main__":
    main()
