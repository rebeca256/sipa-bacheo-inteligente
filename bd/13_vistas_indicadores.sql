/* =====================================================================
   SIPA · 13_vistas_indicadores.sql
   Vistas de indicadores operativos sobre la base transaccional (esquema ind):
     1. Reincidencia      : celdas donde el bache vuelve a aparecer
     2. Tiempo de respuesta: días desde la decisión de la autoridad hasta que
                             informa la reparación, y cumplimiento de meta
     3. Cobertura          : qué parte de lo reportado se prioriza y se repara
     5. Costo pendiente    : cuánto costaría atender lo que falta (tarifas JSON)
     4. Causa probable     : agua, carga o falla estructural (hipótesis)
   Reincidencia: el bache reaparece en el mismo punto (≈ 11 m) 30 días o más
   después del reporte anterior (misma regla que estructuras/sipa_ed.py).
   Las decisiones, reparaciones y fechas vienen de 08_simular_operacion.sql: son ILUSTRATIVAS.
   ===================================================================== */
USE SIPA;
SET QUOTED_IDENTIFIER ON;
SET ANSI_NULLS ON;
GO
IF SCHEMA_ID('ind') IS NULL EXEC('CREATE SCHEMA ind');
GO

/* ---------------------------------------------------------------------
   Auxiliar: territorio de cada celda (el de la mayoría de sus reportes,
   igual que sp_calcular_ipu).
   --------------------------------------------------------------------- */
CREATE OR ALTER VIEW ind.v_celda_territorio AS
SELECT celda_id, id_territorio, territorio
FROM (
    SELECT r.celda_id, t.id_territorio, t.nombre AS territorio,
           ROW_NUMBER() OVER (PARTITION BY r.celda_id ORDER BY COUNT(*) DESC, t.id_territorio) AS rn
    FROM reporte r
    JOIN colonia c    ON c.id_colonia = r.id_colonia
    JOIN territorio t ON t.id_territorio = c.id_territorio
    WHERE r.celda_id IS NOT NULL
    GROUP BY r.celda_id, t.id_territorio, t.nombre
) x
WHERE rn = 1;
GO

/* ---------------------------------------------------------------------
   1. REINCIDENCIA
   Misma regla que estructuras/sipa_ed.py: la ubicación se redondea a
   4 decimales (≈ 11 m) y se revisa ese punto y sus 8 vecinos. Si ahí hubo
   un reporte anterior:
     - menos de 30 días antes → DUPLICADO (es el mismo bache)
     - 30 días o más          → REAPARICION (el bache volvió)
   Buscar vecinos en una vista sería muy lento (se recalcula en cada
   consulta), así que la clasificación se guarda en ind.reporte_reaparicion
   y se actualiza con ind.sp_actualizar_reincidencia.

   Sincronización (frecuencia publicada): INMEDIATA. Cada alta por
   sp_registrar_reporte clasifica su propio reporte con
   ind.sp_reincidencia_reporte dentro de la misma transacción (el reporte
   nuevo es el más reciente, así que su clasificación es exacta) y avanza
   el corte. ind.sp_actualizar_reincidencia reconstruye todo (instalación,
   cargas masivas); el tablero la lanza si detecta un atraso.
   ind.corte_reincidencia guarda el corte visible: hasta qué reporte y a
   qué hora. El corte nunca retrocede, dos ejecuciones simultáneas se
   serializan con sp_getapplock y, si una falla, la tabla y el corte
   anteriores quedan intactos y el error se registra en ultimo_error.
   --------------------------------------------------------------------- */
IF OBJECT_ID('ind.corte_reincidencia') IS NULL
CREATE TABLE ind.corte_reincidencia (
    id                  TINYINT       CONSTRAINT pk_corte_reincidencia PRIMARY KEY
                                      CONSTRAINT ck_corte_unico CHECK (id = 1),
    ultimo_id_reporte   INT           NOT NULL,
    fecha_corte         DATETIME2(0)  NOT NULL,
    ultimo_error        NVARCHAR(400) NULL,
    fecha_error         DATETIME2(0)  NULL
);
GO
IF OBJECT_ID('ind.reporte_reaparicion') IS NULL
CREATE TABLE ind.reporte_reaparicion (
    id_reporte          INT         CONSTRAINT pk_reaparicion PRIMARY KEY
                                    CONSTRAINT fk_reaparicion_reporte REFERENCES dbo.reporte(id_reporte),
    celda_id            VARCHAR(12) NOT NULL,
    fecha_solicitud     DATE        NOT NULL,
    fecha_anterior      DATE        NULL,
    dias_desde_anterior INT         NULL,
    tipo                VARCHAR(11) NOT NULL
                        CONSTRAINT ck_reaparicion_tipo CHECK (tipo IN ('NUEVO','DUPLICADO','REAPARICION'))
);
GO

/* Clasificación incremental de UN reporte (lo llama sp_registrar_reporte
   dentro de su transacción, que ya tomó el candado ANTES de insertar; aquí
   se vuelve a pedir, lo que es reentrante). Candado EXCLUSIVO hasta el COMMIT del alta:
   las altas se clasifican una tras otra y cada una ve confirmadas todas las
   anteriores, igual que la reconstrucción completa (que usa el mismo
   candado). Así el corte "hasta el reporte N" cubre todos los IDs menores.
   A la escala del proyecto (decenas de altas al día) la espera es nula. */
CREATE OR ALTER PROCEDURE ind.sp_reincidencia_reporte
    @id_reporte INT
AS
BEGIN
    SET NOCOUNT ON; SET XACT_ABORT ON;
    IF @@TRANCOUNT = 0 THROW 50021, 'ind.sp_reincidencia_reporte debe llamarse dentro de una transacción.', 1;
    DECLARE @lock INT;
    EXEC @lock = sp_getapplock @Resource = 'ind.reincidencia', @LockMode = 'Exclusive',
                               @LockOwner = 'Transaction', @LockTimeout = 60000;
    IF @lock < 0 THROW 50020, 'Otra clasificación de reincidencia sigue en curso.', 1;

    DECLARE @k_lat INT, @k_lon INT, @f DATE, @celda VARCHAR(12);
    SELECT @k_lat = CAST(ROUND(latitud * 10000, 0) AS INT), @k_lon = CAST(ROUND(longitud * 10000, 0) AS INT),
           @f = fecha_solicitud, @celda = celda_id
    FROM dbo.reporte WHERE id_reporte = @id_reporte AND latitud IS NOT NULL AND celda_id IS NOT NULL;
    IF @f IS NULL OR EXISTS (SELECT 1 FROM ind.reporte_reaparicion WHERE id_reporte = @id_reporte) RETURN;

    -- mismo criterio que la reconstrucción: punto de ≈ 11 m y sus 8 vecinos
    DECLARE @ant DATE = (
        SELECT MAX(q.fecha_solicitud) FROM dbo.reporte q
        WHERE q.latitud  BETWEEN (@k_lat - 1.5) / 10000.0 AND (@k_lat + 1.5) / 10000.0
          AND q.longitud BETWEEN (@k_lon - 1.5) / 10000.0 AND (@k_lon + 1.5) / 10000.0
          AND CAST(ROUND(q.latitud  * 10000, 0) AS INT) BETWEEN @k_lat - 1 AND @k_lat + 1
          AND CAST(ROUND(q.longitud * 10000, 0) AS INT) BETWEEN @k_lon - 1 AND @k_lon + 1
          AND q.celda_id IS NOT NULL
          AND (q.fecha_solicitud < @f OR (q.fecha_solicitud = @f AND q.id_reporte < @id_reporte)));

    INSERT INTO ind.reporte_reaparicion (id_reporte, celda_id, fecha_solicitud, fecha_anterior,
                                         dias_desde_anterior, tipo)
    VALUES (@id_reporte, @celda, @f, @ant, DATEDIFF(DAY, @ant, @f),
            CASE WHEN @ant IS NULL THEN 'NUEVO'
                 WHEN DATEDIFF(DAY, @ant, @f) < 30 THEN 'DUPLICADO' ELSE 'REAPARICION' END);

    MERGE ind.corte_reincidencia AS c USING (SELECT 1 AS id) s ON c.id = s.id
    WHEN MATCHED THEN UPDATE SET
         ultimo_id_reporte = IIF(@id_reporte > c.ultimo_id_reporte, @id_reporte, c.ultimo_id_reporte),
         fecha_corte = IIF(SYSDATETIME() > c.fecha_corte, SYSDATETIME(), c.fecha_corte)
    WHEN NOT MATCHED THEN INSERT (id, ultimo_id_reporte, fecha_corte) VALUES (1, @id_reporte, SYSDATETIME());
END
GO

CREATE OR ALTER PROCEDURE ind.sp_actualizar_reincidencia
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        EXEC ind.sp_actualizar_reincidencia_nucleo;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
        MERGE ind.corte_reincidencia AS c USING (SELECT 1 AS id) s ON c.id = s.id
        WHEN MATCHED THEN UPDATE SET ultimo_error = LEFT(ERROR_MESSAGE(), 400), fecha_error = SYSDATETIME()
        WHEN NOT MATCHED THEN INSERT (id, ultimo_id_reporte, fecha_corte, ultimo_error, fecha_error)
             VALUES (1, 0, '19000101', LEFT(ERROR_MESSAGE(), 400), SYSDATETIME());
        THROW;
    END CATCH
END
GO

CREATE OR ALTER PROCEDURE ind.sp_actualizar_reincidencia_nucleo
AS
BEGIN
    SET NOCOUNT ON; SET XACT_ABORT ON;
    DECLARE @lock INT;
    BEGIN TRANSACTION;
    -- Serializa: una segunda ejecución espera a la primera (hasta 60 s).
    EXEC @lock = sp_getapplock @Resource = 'ind.reincidencia', @LockMode = 'Exclusive',
                               @LockOwner = 'Transaction', @LockTimeout = 60000;
    IF @lock < 0 THROW 50020, 'Otra actualización de reincidencia sigue en curso.', 1;

    -- 1. Clave del punto (≈ 11 m) en una tabla de paso indexada
    DROP TABLE IF EXISTS #p;
    SELECT id_reporte, celda_id, fecha_solicitud,
           CAST(ROUND(latitud  * 10000, 0) AS INT) AS k_lat,
           CAST(ROUND(longitud * 10000, 0) AS INT) AS k_lon
    INTO #p
    FROM dbo.reporte
    WHERE latitud IS NOT NULL AND celda_id IS NOT NULL;
    CREATE CLUSTERED INDEX ix_p ON #p (k_lat, k_lon, fecha_solicitud, id_reporte);

    -- 2. Reporte anterior más reciente en el punto o sus 8 vecinos
    DROP TABLE IF EXISTS #r;
    SELECT r.id_reporte, r.celda_id, r.fecha_solicitud, ant.fecha_anterior
    INTO #r
    FROM #p r
    OUTER APPLY (
        SELECT MAX(q.fecha_solicitud) AS fecha_anterior
        FROM #p q
        WHERE q.k_lat BETWEEN r.k_lat - 1 AND r.k_lat + 1
          AND q.k_lon BETWEEN r.k_lon - 1 AND r.k_lon + 1
          AND (q.fecha_solicitud < r.fecha_solicitud
               OR (q.fecha_solicitud = r.fecha_solicitud AND q.id_reporte < r.id_reporte))
    ) ant;

    -- 3. Reemplazo completo, todo o nada (dentro de la transacción del candado)
    DECLARE @max_id INT = ISNULL((SELECT MAX(id_reporte) FROM #p), 0);
        DELETE FROM ind.reporte_reaparicion;
        INSERT INTO ind.reporte_reaparicion (id_reporte, celda_id, fecha_solicitud, fecha_anterior,
                                             dias_desde_anterior, tipo)
        SELECT id_reporte, celda_id, fecha_solicitud, fecha_anterior,
               DATEDIFF(DAY, fecha_anterior, fecha_solicitud),
               CASE WHEN fecha_anterior IS NULL THEN 'NUEVO'
                    WHEN DATEDIFF(DAY, fecha_anterior, fecha_solicitud) < 30 THEN 'DUPLICADO'
                    ELSE 'REAPARICION' END
        FROM #r;
        -- Corte visible: nunca retrocede
        MERGE ind.corte_reincidencia AS c USING (SELECT 1 AS id) s ON c.id = s.id
        WHEN MATCHED THEN UPDATE SET
             ultimo_id_reporte = IIF(@max_id > c.ultimo_id_reporte, @max_id, c.ultimo_id_reporte),
             fecha_corte = IIF(SYSDATETIME() > c.fecha_corte, SYSDATETIME(), c.fecha_corte),
             ultimo_error = NULL, fecha_error = NULL
        WHEN NOT MATCHED THEN INSERT (id, ultimo_id_reporte, fecha_corte) VALUES (1, @max_id, SYSDATETIME());
    COMMIT TRANSACTION;
END
GO

CREATE OR ALTER VIEW ind.v_reincidencia_celda AS
SELECT r.celda_id, ct.id_territorio, ct.territorio,
       COUNT(*)                                   AS reportes,
       SUM(IIF(r.tipo = 'DUPLICADO', 1, 0))       AS duplicados,
       SUM(IIF(r.tipo = 'REAPARICION', 1, 0))     AS reapariciones,
       MIN(r.fecha_solicitud)                     AS primer_reporte,
       MAX(r.fecha_solicitud)                     AS ultimo_reporte,
       CASE WHEN SUM(IIF(r.tipo = 'REAPARICION', 1, 0)) >= 3 THEN 'CRONICA'      -- candidata a reencarpetado
            WHEN SUM(IIF(r.tipo = 'REAPARICION', 1, 0)) >= 1 THEN 'REINCIDENTE'
            ELSE 'UNICA' END                      AS clasificacion
FROM ind.reporte_reaparicion r
JOIN ind.v_celda_territorio ct ON ct.celda_id = r.celda_id
GROUP BY r.celda_id, ct.id_territorio, ct.territorio;
GO

CREATE OR ALTER VIEW ind.v_reincidencia_territorio AS
SELECT id_territorio, territorio,
       COUNT(*)                                                    AS celdas,
       SUM(IIF(clasificacion <> 'UNICA', 1, 0))                    AS celdas_reincidentes,
       SUM(IIF(clasificacion = 'CRONICA', 1, 0))                   AS celdas_cronicas,
       CAST(100.0 * SUM(IIF(clasificacion <> 'UNICA', 1, 0)) / COUNT(*) AS DECIMAL(5,1)) AS pct_celdas_reincidentes,
       SUM(reportes)                                               AS reportes,
       SUM(IIF(clasificacion = 'CRONICA', reportes, 0))            AS reportes_en_cronicas,
       CAST(100.0 * SUM(IIF(clasificacion = 'CRONICA', reportes, 0)) / SUM(reportes) AS DECIMAL(5,1)) AS pct_reportes_en_cronicas
FROM ind.v_reincidencia_celda
GROUP BY id_territorio, territorio;
GO

/* ---------------------------------------------------------------------
   2. TIEMPO DE RESPUESTA (baches que la autoridad informó como reparados)
   --------------------------------------------------------------------- */
CREATE OR ALTER VIEW ind.v_tiempo_respuesta_bache AS
SELECT b.id_bache, ct.id_territorio, ct.territorio,
       d.semaforo_final, d.ajustado_por_persona, d.fecha AS fecha_decision, s.fecha AS fecha_reparacion,
       DATEDIFF(HOUR, d.fecha, s.fecha) / 24.0 AS dias_atencion,
       m.meta_dias,
       IIF(DATEDIFF(HOUR, d.fecha, s.fecha) <= 24 * m.meta_dias, 1, 0) AS en_meta
FROM bache b
-- Reparación: el último seguimiento a REPARADO (empates por id estable).
CROSS APPLY (SELECT TOP 1 fecha FROM seguimiento_bache
             WHERE id_bache = b.id_bache AND id_estado_nuevo = 5
             ORDER BY fecha DESC, id_seguimiento DESC) s
-- Decisión que rige la reparación: la última APROBAR/AJUSTAR registrada ANTES
-- de reparar. Una decisión posterior no altera el plazo (ni lo vuelve negativo).
CROSS APPLY (SELECT TOP 1 dh.fecha, COALESCE(dh.semaforo_ajustado, cp.semaforo) AS semaforo_final,
                    IIF(dh.semaforo_ajustado IS NULL, 0, 1) AS ajustado_por_persona
             FROM decision_humana dh JOIN calculo_prioridad cp ON cp.id_calculo = dh.id_calculo
             WHERE cp.id_bache = b.id_bache AND dh.decision IN ('APROBAR','AJUSTAR')
               AND dh.fecha <= s.fecha
             ORDER BY dh.fecha DESC, dh.id_decision DESC) d
CROSS APPLY (SELECT CASE d.semaforo_final WHEN 'ROJO' THEN 3 WHEN 'AMARILLO' THEN 15 ELSE 60 END AS meta_dias) m
LEFT JOIN ind.v_celda_territorio ct ON ct.celda_id = b.celda_id;
GO

CREATE OR ALTER VIEW ind.v_tiempo_respuesta_semaforo AS
SELECT semaforo_final,
       COUNT(*)                                          AS baches,
       CAST(AVG(dias_atencion) AS DECIMAL(6,1))          AS dias_promedio,
       CAST(MIN(dias_atencion) AS DECIMAL(6,1))          AS dias_min,
       CAST(MAX(dias_atencion) AS DECIMAL(6,1))          AS dias_max,
       MAX(meta_dias)                                    AS meta_dias,
       CAST(100.0 * SUM(en_meta) / COUNT(*) AS DECIMAL(5,1)) AS pct_en_meta
FROM ind.v_tiempo_respuesta_bache
GROUP BY semaforo_final;
GO

CREATE OR ALTER VIEW ind.v_tiempo_respuesta_territorio AS
SELECT id_territorio, territorio,
       COUNT(*)                                          AS baches,
       SUM(IIF(semaforo_final = 'ROJO', 1, 0))           AS baches_rojos,
       CAST(AVG(dias_atencion) AS DECIMAL(6,1))          AS dias_promedio,
       CAST(AVG(IIF(semaforo_final = 'ROJO', dias_atencion, NULL)) AS DECIMAL(6,1)) AS dias_promedio_rojos,
       CAST(100.0 * SUM(en_meta) / COUNT(*) AS DECIMAL(5,1)) AS pct_en_meta
FROM ind.v_tiempo_respuesta_bache
GROUP BY id_territorio, territorio;
GO

/* ---------------------------------------------------------------------
   3. COBERTURA
   Embudo por territorio: baches registrados → priorizados → en atención
   por la autoridad → reparados, y antigüedad de los que siguen pendientes.
   --------------------------------------------------------------------- */
CREATE OR ALTER VIEW ind.v_cobertura_territorio AS
WITH b AS (
    SELECT b.id_bache, ct.id_territorio, ct.territorio, b.fecha_deteccion, b.id_estado_bache,
           IIF(EXISTS (SELECT 1 FROM calculo_prioridad cp WHERE cp.id_bache = b.id_bache), 1, 0) AS priorizado,
           IIF(b.id_estado_bache IN (4, 5), 1, 0) AS atendido,
           IIF(b.id_estado_bache = 5, 1, 0) AS reparado
    FROM bache b
    LEFT JOIN ind.v_celda_territorio ct ON ct.celda_id = b.celda_id
    WHERE b.id_estado_bache <> 6           -- se excluyen los descartados
)
SELECT id_territorio, territorio,
       COUNT(*)                                            AS baches,
       SUM(priorizado)                                     AS priorizados,
       SUM(atendido)                                       AS atendidos,
       SUM(reparado)                                       AS reparados,
       CAST(100.0 * SUM(priorizado) / COUNT(*) AS DECIMAL(5,1)) AS pct_priorizados,
       CAST(100.0 * SUM(reparado)   / COUNT(*) AS DECIMAL(5,1)) AS pct_reparados,
       SUM(1 - reparado)                                   AS pendientes,
       AVG(IIF(reparado = 0, DATEDIFF(DAY, fecha_deteccion, CAST(GETDATE() AS DATE)), NULL)) AS antiguedad_prom_pendientes_dias
FROM b
GROUP BY id_territorio, territorio;
GO

-- Cobertura histórica de los reportes ciudadanos (base maestra y Chalco): qué parte se resolvió.
CREATE OR ALTER VIEW ind.v_cobertura_reportes_anual AS
SELECT t.id_territorio, t.nombre AS territorio, YEAR(r.fecha_solicitud) AS anio,
       COUNT(*)                                                     AS reportes,
       SUM(IIF(e.estatus_agrupado = 'RESUELTO', 1, 0))              AS resueltos,
       SUM(IIF(e.estatus_agrupado = 'TURNADO', 1, 0))               AS turnados,
       SUM(IIF(e.estatus_agrupado = 'PENDIENTE', 1, 0))             AS pendientes,
       CAST(100.0 * SUM(IIF(e.estatus_agrupado = 'RESUELTO', 1, 0)) / COUNT(*) AS DECIMAL(5,1)) AS pct_resueltos
FROM reporte r
JOIN cat_estatus_reporte e ON e.estatus_original = r.estatus_original
JOIN colonia c             ON c.id_colonia = r.id_colonia
JOIN territorio t          ON t.id_territorio = c.id_territorio
GROUP BY t.id_territorio, t.nombre, YEAR(r.fecha_solicitud);
GO

/* ---------------------------------------------------------------------
   4. CAUSA PROBABLE DEL DAÑO (propuesta del docente)
   La base no registra la causa, así que se infiere con tres indicios:
     - AGUA       : el bache está dentro o a <= 200 m de una zona inundable
                    (solo Chalco tiene el atlas), o en su celda >= 80 % de los
                    reportes caen en temporada de lluvias (promedio general:
                    68.5 %) con al menos 5 reportes.
     - CARGA      : la celda está sobre una vía rápida (dato del modelo de
                    accidentes, riesgo_celda_72h).
     - ESTRUCTURAL: la celda es crónica (>= 3 reapariciones): el bacheo no
                    está resolviendo el problema de fondo.
   La causa principal sigue ese orden de gravedad y sugiere la intervención.
   Es una HIPÓTESIS para orientar la inspección, no un diagnóstico.
   --------------------------------------------------------------------- */
CREATE OR ALTER VIEW ind.v_causa_probable_bache AS
WITH lluvia AS (
    SELECT celda_id, COUNT(*) AS reportes,
           AVG(CAST(temporada_lluvias AS FLOAT)) AS pct_lluvias
    FROM reporte WHERE celda_id IS NOT NULL
    GROUP BY celda_id
), f AS (
    SELECT b.id_bache, b.celda_id, ct.id_territorio, ct.territorio,
           CAST(l.pct_lluvias AS DECIMAL(4,3)) AS pct_reportes_lluvias,
           zi.dist_m                            AS dist_zona_inundable_m,
           rc.via_rapida,
           ISNULL(rc2.reapariciones, 0)         AS reapariciones_celda,
           IIF(zi.dist_m <= 200 OR (l.reportes >= 5 AND l.pct_lluvias >= 0.80), 1, 0) AS f_agua,
           ISNULL(CAST(rc.via_rapida AS INT), 0)                                     AS f_carga,
           IIF(rc2.clasificacion = 'CRONICA', 1, 0)                                  AS f_estructural
    FROM bache b
    LEFT JOIN ind.v_celda_territorio ct  ON ct.celda_id = b.celda_id
    LEFT JOIN lluvia l                   ON l.celda_id  = b.celda_id
    LEFT JOIN riesgo_celda_72h rc        ON rc.celda_id = b.celda_id
    LEFT JOIN ind.v_reincidencia_celda rc2 ON rc2.celda_id = b.celda_id
    OUTER APPLY (SELECT TOP 1 z.poligono.STDistance(GEOGRAPHY::Point(b.latitud, b.longitud, 4326)) AS dist_m
                 FROM zona_inundable z WHERE z.id_territorio = ct.id_territorio
                 ORDER BY dist_m) zi
)
SELECT *,
       CASE WHEN f_estructural = 1              THEN 'ESTRUCTURAL'
            WHEN f_agua = 1 AND f_carga = 1     THEN 'AGUA_Y_CARGA'
            WHEN f_agua = 1                     THEN 'AGUA'
            WHEN f_carga = 1                    THEN 'CARGA'
            ELSE 'SIN_INDICIOS' END             AS causa_probable,
       CASE WHEN f_estructural = 1              THEN 'Reencarpetado o reconstrucción de la base'
            WHEN f_agua = 1                     THEN 'Bacheo con sello y revisión del drenaje pluvial'
            WHEN f_carga = 1                    THEN 'Mezcla de alto desempeño, reparación en horario nocturno'
            ELSE 'Bacheo convencional; inspección para registrar la causa' END AS intervencion_sugerida,
       f_agua + f_carga + f_estructural         AS indicios
FROM f;
GO

CREATE OR ALTER VIEW ind.v_causa_probable_territorio AS
SELECT id_territorio, territorio,
       COUNT(*)                                              AS baches,
       SUM(IIF(causa_probable = 'ESTRUCTURAL', 1, 0))        AS estructural,
       SUM(IIF(causa_probable = 'AGUA_Y_CARGA', 1, 0))       AS agua_y_carga,
       SUM(IIF(causa_probable = 'AGUA', 1, 0))               AS agua,
       SUM(IIF(causa_probable = 'CARGA', 1, 0))              AS carga,
       SUM(IIF(causa_probable = 'SIN_INDICIOS', 1, 0))       AS sin_indicios,
       CAST(100.0 * SUM(IIF(causa_probable <> 'SIN_INDICIOS', 1, 0)) / COUNT(*) AS DECIMAL(5,1)) AS pct_con_causa
FROM ind.v_causa_probable_bache
GROUP BY id_territorio, territorio;
GO

/* ---------------------------------------------------------------------
   5. COSTO PENDIENTE
   Lo que SIPA le dice a la autoridad: cuánto costaría atender los baches
   que siguen abiertos, según la intervención recomendada y las tarifas del
   JSON (último cálculo de cada bache). Separado por semáforo para que se
   vea cuánto se necesita para lo urgente.
   --------------------------------------------------------------------- */
CREATE OR ALTER VIEW ind.v_costo_pendiente_territorio AS
SELECT ct.id_territorio, ct.territorio,
       COUNT(*)                                                    AS baches_pendientes,
       SUM(cp.costo_estimado)                                      AS costo_total,
       SUM(IIF(cp.semaforo = 'ROJO', cp.costo_estimado, 0))        AS costo_rojos,
       SUM(IIF(cp.semaforo = 'AMARILLO', cp.costo_estimado, 0))    AS costo_amarillos,
       SUM(IIF(cp.semaforo = 'VERDE', cp.costo_estimado, 0))       AS costo_verdes,
       SUM(IIF(cp.clave_tarifa = 'REENCARPETADO', 1, 0))           AS reencarpetados
FROM bache b
CROSS APPLY (SELECT TOP 1 semaforo, clave_tarifa, costo_estimado FROM calculo_prioridad x
             WHERE x.id_bache = b.id_bache ORDER BY x.id_calculo DESC) cp
LEFT JOIN ind.v_celda_territorio ct ON ct.celda_id = b.celda_id
WHERE b.id_estado_bache IN (2, 3, 4)
GROUP BY ct.id_territorio, ct.territorio;
GO

-- El rol de autoridad también lee los indicadores que muestra el tablero
IF DATABASE_PRINCIPAL_ID('rol_autoridad') IS NOT NULL
    GRANT SELECT ON SCHEMA::ind TO rol_autoridad;
GO

/* ---------------------------------------------------------------------
   Demostración
   --------------------------------------------------------------------- */
SET NOCOUNT ON;
EXEC ind.sp_actualizar_reincidencia;
PRINT '== Clasificación de reportes (compárese con estructuras/experimentos.py)';
SELECT tipo, COUNT(*) AS reportes FROM ind.reporte_reaparicion GROUP BY tipo;

PRINT '== Reincidencia por territorio';
SELECT territorio, celdas, celdas_reincidentes, pct_celdas_reincidentes, celdas_cronicas, pct_reportes_en_cronicas
FROM ind.v_reincidencia_territorio ORDER BY pct_reportes_en_cronicas DESC;

PRINT '== Celdas crónicas con más reapariciones';
SELECT TOP 10 celda_id, territorio, reportes, reapariciones, primer_reporte, ultimo_reporte
FROM ind.v_reincidencia_celda WHERE clasificacion = 'CRONICA' ORDER BY reapariciones DESC, reportes DESC;

PRINT '== Tiempo de respuesta por semáforo (simulado)';
SELECT * FROM ind.v_tiempo_respuesta_semaforo ORDER BY meta_dias;

PRINT '== Tiempo de respuesta por territorio (simulado)';
SELECT territorio, baches, baches_rojos, dias_promedio, dias_promedio_rojos, pct_en_meta
FROM ind.v_tiempo_respuesta_territorio ORDER BY dias_promedio DESC;

PRINT '== Cobertura por territorio';
SELECT territorio, baches, priorizados, reparados, pct_reparados, pendientes, antiguedad_prom_pendientes_dias
FROM ind.v_cobertura_territorio ORDER BY pct_reparados;

PRINT '== Reportes resueltos por año';
SELECT anio, SUM(reportes) AS reportes, SUM(resueltos) AS resueltos,
       CAST(100.0 * SUM(resueltos) / SUM(reportes) AS DECIMAL(5,1)) AS pct_resueltos
FROM ind.v_cobertura_reportes_anual GROUP BY anio ORDER BY anio;

PRINT '== Causa probable del daño (hipótesis)';
SELECT causa_probable, intervencion_sugerida, COUNT(*) AS baches
FROM ind.v_causa_probable_bache GROUP BY causa_probable, intervencion_sugerida ORDER BY baches DESC;

PRINT '== Causa probable por territorio';
SELECT territorio, baches, estructural, agua_y_carga, agua, carga, sin_indicios, pct_con_causa
FROM ind.v_causa_probable_territorio ORDER BY pct_con_causa DESC;

PRINT '== Costo estimado de lo pendiente (tarifas del JSON)';
SELECT territorio, baches_pendientes, costo_total, costo_rojos, costo_amarillos, costo_verdes, reencarpetados
FROM ind.v_costo_pendiente_territorio ORDER BY costo_total DESC;
GO
