/* =====================================================================
   SIPA · 11_dw_consultas_olap.sql  ·  Procesamiento OLAP sobre SIPA_DW

   Operaciones OLAP demostradas:
     O1  Roll-up        ROLLUP: reportes por territorio → año → total
     O2  Cubo           CUBE: todas las combinaciones temporada × estatus
     O3  Grouping sets  varios niveles de agregación en una sola consulta
     O4  Pivot          años como columnas
     O5  Drill-down     de territorio a colonia a celda
     O6  Slice / dice   rebanar el cubo por una o varias dimensiones
     O7  Funciones de ventana: tendencia y acumulados
   Y consultas a los datamarts de priorización (P) y financiero (F).
   ===================================================================== */
USE SIPA_DW;
GO
SET NOCOUNT ON;

/* O1. ROLL-UP: reportes por territorio y año, con subtotales y gran total */
SELECT IIF(GROUPING(u.territorio) = 1, '== TOTAL ==', u.territorio) AS territorio,
       IIF(GROUPING(t.anio) = 1, 'subtotal', CAST(t.anio AS VARCHAR)) AS anio,
       SUM(f.cantidad) AS reportes
FROM dw.fact_reporte f
JOIN dw.dim_ubicacion u ON u.id_ubicacion = f.id_ubicacion
JOIN dw.dim_tiempo t    ON t.id_tiempo = f.id_tiempo
WHERE u.territorio IN ('GUSTAVO A. MADERO', 'COYOACAN', 'CHALCO')
GROUP BY ROLLUP (u.territorio, t.anio)
ORDER BY GROUPING(u.territorio), u.territorio, GROUPING(t.anio), t.anio;

/* O2. CUBO: temporada × estatus agrupado, con todos los subtotales */
SELECT ISNULL(t.temporada, '(todas)')        AS temporada,
       ISNULL(e.estatus_agrupado, '(todos)') AS estatus,
       SUM(f.cantidad) AS reportes
FROM dw.fact_reporte f
JOIN dw.dim_tiempo t  ON t.id_tiempo = f.id_tiempo
JOIN dw.dim_estatus e ON e.id_estatus = f.id_estatus
GROUP BY CUBE (t.temporada, e.estatus_agrupado)
ORDER BY GROUPING(t.temporada), t.temporada, GROUPING(e.estatus_agrupado), e.estatus_agrupado;

/* O3. GROUPING SETS: por entidad, por trimestre y por día de la semana a la vez */
SELECT u.entidad, t.trimestre, t.nombre_dia, SUM(f.cantidad) AS reportes
FROM dw.fact_reporte f
JOIN dw.dim_ubicacion u ON u.id_ubicacion = f.id_ubicacion
JOIN dw.dim_tiempo t    ON t.id_tiempo = f.id_tiempo
GROUP BY GROUPING SETS ((u.entidad), (t.trimestre), (t.dia_semana, t.nombre_dia))
ORDER BY u.entidad, t.trimestre, MIN(t.dia_semana);

/* O4. PIVOT: reportes por alcaldía con un año por columna */
SELECT territorio, [2019], [2020], [2021], [2022], [2025], [2026]
FROM (SELECT u.territorio, t.anio, f.cantidad
      FROM dw.fact_reporte f
      JOIN dw.dim_ubicacion u ON u.id_ubicacion = f.id_ubicacion
      JOIN dw.dim_tiempo t    ON t.id_tiempo = f.id_tiempo) src
PIVOT (SUM(cantidad) FOR anio IN ([2019], [2020], [2021], [2022], [2025], [2026])) pv
ORDER BY territorio;

/* O5. DRILL-DOWN: territorio → colonia → celda (Chalco) */
-- nivel 1
SELECT u.territorio, SUM(f.cantidad) AS reportes
FROM dw.fact_reporte f JOIN dw.dim_ubicacion u ON u.id_ubicacion = f.id_ubicacion
WHERE u.territorio = 'CHALCO' GROUP BY u.territorio;
-- nivel 2
SELECT u.colonia, u.tipo_asentamiento, SUM(f.cantidad) AS reportes
FROM dw.fact_reporte f JOIN dw.dim_ubicacion u ON u.id_ubicacion = f.id_ubicacion
WHERE u.territorio = 'CHALCO' GROUP BY u.colonia, u.tipo_asentamiento ORDER BY reportes DESC;
-- nivel 3 (la colonia con más reportes)
SELECT c.celda_id, c.latitud, c.longitud, c.cerca_zona_inundable, c.servicios_500m, SUM(f.cantidad) AS reportes
FROM dw.fact_reporte f
JOIN dw.dim_ubicacion u ON u.id_ubicacion = f.id_ubicacion
JOIN dw.dim_celda c     ON c.id_celda = f.id_celda
WHERE u.territorio = 'CHALCO'
  AND u.colonia = (SELECT TOP 1 u2.colonia FROM dw.fact_reporte f2
                   JOIN dw.dim_ubicacion u2 ON u2.id_ubicacion = f2.id_ubicacion
                   WHERE u2.territorio = 'CHALCO' GROUP BY u2.colonia ORDER BY SUM(f2.cantidad) DESC)
GROUP BY c.celda_id, c.latitud, c.longitud, c.cerca_zona_inundable, c.servicios_500m;

/* O6. SLICE (una dimensión fija) y DICE (varias): */
-- slice: solo temporada de lluvias
SELECT t.anio, SUM(f.cantidad) AS reportes_en_lluvias
FROM dw.fact_reporte f JOIN dw.dim_tiempo t ON t.id_tiempo = f.id_tiempo
WHERE t.temporada = 'LLUVIAS' GROUP BY t.anio ORDER BY t.anio;
-- dice: CDMX × 2021-2022 × reportes turnados × lluvias
SELECT u.territorio, t.anio, SUM(f.cantidad) AS turnados_en_lluvias
FROM dw.fact_reporte f
JOIN dw.dim_ubicacion u ON u.id_ubicacion = f.id_ubicacion
JOIN dw.dim_tiempo t    ON t.id_tiempo = f.id_tiempo
JOIN dw.dim_estatus e   ON e.id_estatus = f.id_estatus
WHERE u.entidad = 'CIUDAD DE MEXICO' AND t.anio IN (2021, 2022)
  AND e.estatus_agrupado = 'TURNADO' AND t.temporada = 'LLUVIAS'
GROUP BY u.territorio, t.anio ORDER BY turnados_en_lluvias DESC;

/* O7. VENTANAS: reportes mensuales, promedio móvil de 3 meses y acumulado anual (CDMX) */
SELECT t.anio_mes, SUM(f.cantidad) AS reportes,
       AVG(SUM(f.cantidad)) OVER (ORDER BY t.anio_mes ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) AS promedio_movil_3m,
       SUM(SUM(f.cantidad)) OVER (PARTITION BY t.anio ORDER BY t.anio_mes) AS acumulado_anual
FROM dw.fact_reporte f
JOIN dw.dim_tiempo t    ON t.id_tiempo = f.id_tiempo
JOIN dw.dim_ubicacion u ON u.id_ubicacion = f.id_ubicacion
WHERE u.entidad = 'CIUDAD DE MEXICO'
GROUP BY t.anio, t.anio_mes ORDER BY t.anio_mes;

/* ===================== DATAMART DE PRIORIZACIÓN ===================== */

-- P1. Top 10 de Chalco
SELECT TOP 10 lugar_en_territorio AS lugar, colonia, ipu, semaforo_modelo, severidad, v_inundacion, v_servicios
FROM dm_priorizacion.v_ranking_baches WHERE territorio = 'CHALCO' ORDER BY lugar_en_territorio;

-- P2. Semáforo por territorio
SELECT * FROM dm_priorizacion.v_semaforo_territorio ORDER BY ipu_promedio DESC;

-- P3. Celdas críticas para un programa preventivo (reportes en 3 o más años)
SELECT TOP 15 * FROM dm_priorizacion.v_celdas_criticas
WHERE anios_con_reportes >= 3 ORDER BY reportes DESC;

-- P4. Percepción vs. evidencia: baches con muchos reportes que NO quedan arriba por IPU
SELECT TOP 10 territorio, colonia, lugar_por_reportes, lugar_por_ipu, ipu, semaforo_modelo
FROM dm_priorizacion.v_reportes_vs_ipu
WHERE lugar_por_reportes <= 50 ORDER BY lugar_por_ipu DESC;

-- P5. Decisiones humanas: ¿cuántas veces se cambió lo que recomendó el modelo?
SELECT sm.nombre AS recomendado, sf.nombre AS decidido, COUNT(*) AS casos
FROM dw.fact_priorizacion f
JOIN dw.dim_semaforo sm ON sm.id_semaforo = f.id_semaforo_modelo
JOIN dw.dim_semaforo sf ON sf.id_semaforo = f.id_semaforo_final
WHERE f.decision <> 'PENDIENTE'
GROUP BY sm.nombre, sf.nombre ORDER BY casos DESC;

/* ===================== DATAMART FINANCIERO ===================== */

-- F1. Cumplimiento de tiempos objetivo por semáforo
SELECT * FROM dm_financiero.v_cumplimiento_semaforo;

-- F2. Costo estimado vs. reportado por territorio, con total (ROLLUP)
SELECT ISNULL(territorio, '== TOTAL ==') AS territorio,
       SUM(baches_reparados) AS baches_reparados,
       SUM(costo_estimado) AS costo_estimado, SUM(costo_reportado) AS costo_reportado,
       CAST(100.0 * (SUM(costo_reportado) - SUM(costo_estimado)) / SUM(costo_estimado) AS DECIMAL(6,1)) AS desviacion_pct
FROM dm_financiero.v_costo_mensual
GROUP BY ROLLUP (territorio)
ORDER BY GROUPING(territorio), costo_reportado DESC;

-- F3. Gasto mensual 2026 informado por las autoridades
SELECT anio_mes, SUM(baches_reparados) AS baches_reparados, SUM(costo_reportado) AS costo_reportado
FROM dm_financiero.v_costo_mensual WHERE anio = 2026
GROUP BY anio_mes ORDER BY anio_mes;

-- F4. ¿Cuánto costaría atender lo recomendado, por tipo de intervención?
SELECT * FROM dm_financiero.v_intervenciones ORDER BY costo_estimado_total DESC;
GO
