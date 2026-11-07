/* =====================================================================
   SIPA · 10_dw_etl.sql  ·  Proceso ETL: SIPA (transaccional) -> SIPA_DW

   Extrae de SIPA, transforma (llaves sustitutas, fila «desconocido»,
   criterios del IPU en columnas, tiempos de atención, cumplimiento de meta)
   y carga en SIPA_DW. Es una CARGA COMPLETA: vacía y vuelve a llenar.
   Todo ocurre en una transacción y cada paso queda en dw.etl_bitacora.

   Uso:  EXEC SIPA_DW.dw.sp_etl_cargar;
   ===================================================================== */
USE SIPA_DW;
SET QUOTED_IDENTIFIER ON;
SET ANSI_NULLS ON;
GO

CREATE OR ALTER PROCEDURE dw.sp_etl_cargar
AS
BEGIN
    SET NOCOUNT ON; SET XACT_ABORT ON;
    DECLARE @inicio DATETIME2(0) = SYSDATETIME(), @t DATETIME2(0), @filas INT;

    BEGIN TRY
        BEGIN TRANSACTION;

        /* --- 0. Limpieza (hechos primero por las llaves foráneas) --- */
        TRUNCATE TABLE dw.fact_reporte;
        TRUNCATE TABLE dw.fact_priorizacion;
        TRUNCATE TABLE dw.fact_atencion;
        DELETE dw.dim_ubicacion; DBCC CHECKIDENT ('dw.dim_ubicacion', RESEED, 0) WITH NO_INFOMSGS;
        DELETE dw.dim_celda;     DBCC CHECKIDENT ('dw.dim_celda',     RESEED, 0) WITH NO_INFOMSGS;
        DELETE dw.dim_estatus;   DBCC CHECKIDENT ('dw.dim_estatus',   RESEED, 0) WITH NO_INFOMSGS;
        DELETE dw.dim_fuente;    DBCC CHECKIDENT ('dw.dim_fuente',    RESEED, 0) WITH NO_INFOMSGS;
        DELETE dw.dim_intervencion; DBCC CHECKIDENT ('dw.dim_intervencion', RESEED, 0) WITH NO_INFOMSGS;

        /* --- 1. Dimensiones --- */
        SET @t = SYSDATETIME();
        SET IDENTITY_INSERT dw.dim_ubicacion ON;
        INSERT INTO dw.dim_ubicacion (id_ubicacion, id_colonia, colonia, territorio, tipo_territorio, entidad)
        VALUES (-1, NULL, 'DESCONOCIDA', 'DESCONOCIDO', 'N/A', 'N/A');
        SET IDENTITY_INSERT dw.dim_ubicacion OFF;
        INSERT INTO dw.dim_ubicacion (id_colonia, colonia, tipo_asentamiento, territorio, tipo_territorio, entidad)
        SELECT c.id_colonia, c.nombre, c.tipo_asentamiento, t.nombre, t.tipo, t.entidad
        FROM SIPA.dbo.colonia c JOIN SIPA.dbo.territorio t ON t.id_territorio = c.id_territorio;
        SET @filas = @@ROWCOUNT;
        INSERT INTO dw.etl_bitacora VALUES (@t, SYSDATETIME(), 'dim_ubicacion', @filas, 'OK', NULL);

        -- Celdas: se precalcula cercanía a zonas inundables y servicios.
        -- El filtro por diferencia de coordenadas evita medir distancias inútiles.
        SET @t = SYSDATETIME();
        SET IDENTITY_INSERT dw.dim_celda ON;
        INSERT INTO dw.dim_celda (id_celda, celda_id) VALUES (-1, 'DESCONOCIDA');
        SET IDENTITY_INSERT dw.dim_celda OFF;
        INSERT INTO dw.dim_celda (celda_id, latitud, longitud, cerca_zona_inundable, servicios_500m)
        SELECT c.celda_id, c.latitud, c.longitud,
               IIF(EXISTS (SELECT 1 FROM SIPA.dbo.zona_inundable z
                           WHERE z.poligono.STDistance(GEOGRAPHY::Point(c.latitud, c.longitud, 4326)) <= 200), 1, 0),
               (SELECT COUNT(*) FROM SIPA.dbo.equipamiento e
                WHERE ABS(e.latitud - c.latitud) < 0.006 AND ABS(e.longitud - c.longitud) < 0.006
                  AND e.ubicacion.STDistance(GEOGRAPHY::Point(c.latitud, c.longitud, 4326)) <= 500)
        FROM SIPA.dbo.celda c;
        SET @filas = @@ROWCOUNT;
        INSERT INTO dw.etl_bitacora VALUES (@t, SYSDATETIME(), 'dim_celda', @filas, 'OK', NULL);

        SET IDENTITY_INSERT dw.dim_intervencion ON;
        INSERT INTO dw.dim_intervencion (id_intervencion, clave, nombre) VALUES (-1, 'SIN_DATO', 'Sin intervención calculada');
        SET IDENTITY_INSERT dw.dim_intervencion OFF;
        INSERT INTO dw.dim_intervencion (clave, nombre, costo_m2, costo_fijo)
        SELECT clave, nombre, costo_m2, costo_fijo FROM SIPA.dbo.tarifa_reparacion;

        INSERT INTO dw.dim_estatus (estatus_original, estatus_agrupado)
        SELECT estatus_original, estatus_agrupado FROM SIPA.dbo.cat_estatus_reporte;

        INSERT INTO dw.dim_fuente (nombre) SELECT nombre FROM SIPA.dbo.cat_fuente_reporte;

        /* --- 2. Hechos de reportes --- */
        SET @t = SYSDATETIME();
        INSERT INTO dw.fact_reporte (id_tiempo, id_reporte, id_ubicacion, id_celda, id_estatus, id_fuente,
                                     posible_duplicado, ubicacion_dudosa, ligado_a_bache)
        SELECT CONVERT(INT, FORMAT(r.fecha_solicitud, 'yyyyMMdd')), r.id_reporte,
               ISNULL(u.id_ubicacion, -1), ISNULL(c.id_celda, -1), e.id_estatus, f.id_fuente,
               r.posible_duplicado, r.ubicacion_dudosa, IIF(r.id_bache IS NULL, 0, 1)
        FROM SIPA.dbo.reporte r
        JOIN SIPA.dbo.cat_fuente_reporte fr ON fr.id_fuente = r.id_fuente
        JOIN dw.dim_fuente f   ON f.nombre = fr.nombre
        JOIN dw.dim_estatus e  ON e.estatus_original = r.estatus_original
        LEFT JOIN dw.dim_ubicacion u ON u.id_colonia = r.id_colonia
        LEFT JOIN dw.dim_celda c     ON c.celda_id = r.celda_id;
        SET @filas = @@ROWCOUNT;
        INSERT INTO dw.etl_bitacora VALUES (@t, SYSDATETIME(), 'fact_reporte', @filas, 'OK', NULL);

        /* --- 3. Hechos de priorización --- */
        SET @t = SYSDATETIME();
        INSERT INTO dw.fact_priorizacion
        SELECT cp.id_calculo, cp.id_bache,
               CONVERT(INT, FORMAT(cp.fecha_calculo, 'yyyyMMdd')),
               ISNULL(u.id_ubicacion, -1), ISNULL(dc.id_celda, -1),
               sm.id_semaforo,
               ISNULL(sf.id_semaforo, 0),
               ISNULL(d.decision, 'PENDIENTE'),
               cp.version_modelo, cp.ipu, b.severidad, ISNULL(di.id_intervencion, -1), cp.costo_estimado,
               cr.v_deterioro, cr.v_deterioro_mayor, cr.v_reportes, cr.v_inundacion, cr.v_servicios
        FROM SIPA.dbo.calculo_prioridad cp
        JOIN SIPA.dbo.bache b ON b.id_bache = cp.id_bache
        LEFT JOIN dw.dim_celda dc ON dc.celda_id = b.celda_id
        LEFT JOIN dw.dim_intervencion di ON di.clave = cp.clave_tarifa
        -- ubicación del bache: la colonia más frecuente entre sus reportes
        OUTER APPLY (SELECT TOP 1 r.id_colonia FROM SIPA.dbo.reporte r
                     WHERE r.id_bache = b.id_bache AND r.id_colonia IS NOT NULL
                     GROUP BY r.id_colonia ORDER BY COUNT(*) DESC) col
        LEFT JOIN dw.dim_ubicacion u ON u.id_colonia = col.id_colonia
        OUTER APPLY (SELECT TOP 1 decision, semaforo_ajustado FROM SIPA.dbo.decision_humana dh
                     WHERE dh.id_calculo = cp.id_calculo ORDER BY dh.fecha DESC) d
        JOIN dw.dim_semaforo sm ON sm.nombre = cp.semaforo
        LEFT JOIN dw.dim_semaforo sf ON d.decision IS NOT NULL
                                    AND sf.nombre = COALESCE(d.semaforo_ajustado, cp.semaforo)
        -- criterios del IPU de filas a columnas (PIVOT)
        OUTER APPLY (
            SELECT MAX(IIF(c.clave = 'DETERIORO',        dt.valor_normalizado, NULL)) AS v_deterioro,
                   MAX(IIF(c.clave = 'DETERIORO_MAYOR',  dt.valor_normalizado, NULL)) AS v_deterioro_mayor,
                   MAX(IIF(c.clave = 'REPORTES',         dt.valor_normalizado, NULL)) AS v_reportes,
                   MAX(IIF(c.clave = 'INUNDACION',       dt.valor_normalizado, NULL)) AS v_inundacion,
                   MAX(IIF(c.clave = 'ACCESO_SERVICIOS', dt.valor_normalizado, NULL)) AS v_servicios
            FROM SIPA.dbo.detalle_calculo dt JOIN SIPA.dbo.criterio_ipu c ON c.id_criterio = dt.id_criterio
            WHERE dt.id_calculo = cp.id_calculo) cr;
        SET @filas = @@ROWCOUNT;
        INSERT INTO dw.etl_bitacora VALUES (@t, SYSDATETIME(), 'fact_priorizacion', @filas, 'OK', NULL);

        /* --- 4. Hechos de atención (lo que informa la autoridad) --- */
        -- Un renglón por bache con decisión APROBAR/AJUSTAR: desde la última
        -- decisión hasta el seguimiento que lo marcó REPARADO o DESCARTADO.
        SET @t = SYSDATETIME();
        INSERT INTO dw.fact_atencion
        SELECT b.id_bache,
               CONVERT(INT, FORMAT(d.fecha, 'yyyyMMdd')),
               CONVERT(INT, FORMAT(fin.fecha, 'yyyyMMdd')),
               ISNULL(u.id_ubicacion, -1), ISNULL(dc.id_celda, -1), ISNULL(di.id_intervencion, -1),
               sf.id_semaforo, e.nombre, d.costo_estimado, fin.costo_reportado,
               DATEDIFF(HOUR, d.fecha, fin.fecha),
               sf.dias_objetivo,
               CASE WHEN fin.fecha IS NULL OR fin.id_estado_nuevo <> 5 THEN NULL
                    WHEN DATEDIFF(HOUR, d.fecha, fin.fecha) <= 24 * sf.dias_objetivo THEN 1 ELSE 0 END
        FROM SIPA.dbo.bache b
        JOIN SIPA.dbo.cat_estado_bache e ON e.id_estado_bache = b.id_estado_bache
        CROSS APPLY (SELECT TOP 1 dh.fecha, cp.costo_estimado, cp.clave_tarifa,
                            COALESCE(dh.semaforo_ajustado, cp.semaforo) AS semaforo_final
                     FROM SIPA.dbo.decision_humana dh
                     JOIN SIPA.dbo.calculo_prioridad cp ON cp.id_calculo = dh.id_calculo
                     WHERE cp.id_bache = b.id_bache AND dh.decision IN ('APROBAR','AJUSTAR')
                     ORDER BY dh.fecha DESC) d
        OUTER APPLY (SELECT TOP 1 s.fecha, s.id_estado_nuevo, s.costo_reportado
                     FROM SIPA.dbo.seguimiento_bache s
                     WHERE s.id_bache = b.id_bache AND s.id_estado_nuevo IN (5, 6)
                     ORDER BY s.fecha DESC) fin
        JOIN dw.dim_semaforo sf          ON sf.nombre = d.semaforo_final
        LEFT JOIN dw.dim_celda dc        ON dc.celda_id = b.celda_id
        LEFT JOIN dw.dim_intervencion di ON di.clave = d.clave_tarifa
        OUTER APPLY (SELECT TOP 1 r.id_colonia FROM SIPA.dbo.reporte r
                     WHERE r.id_bache = b.id_bache AND r.id_colonia IS NOT NULL
                     GROUP BY r.id_colonia ORDER BY COUNT(*) DESC) col
        LEFT JOIN dw.dim_ubicacion u ON u.id_colonia = col.id_colonia;
        SET @filas = @@ROWCOUNT;
        INSERT INTO dw.etl_bitacora VALUES (@t, SYSDATETIME(), 'fact_atencion', @filas, 'OK', NULL);

        INSERT INTO dw.etl_bitacora VALUES (@inicio, SYSDATETIME(), 'CARGA COMPLETA', NULL, 'OK', NULL);
        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        INSERT INTO dw.etl_bitacora VALUES (@inicio, SYSDATETIME(), 'CARGA COMPLETA', NULL, 'ERROR', LEFT(ERROR_MESSAGE(), 400));
        THROW;
    END CATCH
END
GO

EXEC dw.sp_etl_cargar;

-- Pasos de la última ejecución
SELECT paso, filas, DATEDIFF(SECOND, inicio, fin) AS segundos, estado
FROM (SELECT TOP 6 * FROM dw.etl_bitacora ORDER BY id_ejecucion DESC) x
ORDER BY id_ejecucion;

-- Fragmentación: cuántos reportes quedaron en cada partición (año)
SELECT p.partition_number AS particion,
       CASE WHEN prv.value IS NULL THEN 'antes de 2020' ELSE CONCAT('desde ', LEFT(CAST(prv.value AS VARCHAR), 4)) END AS rango,
       p.rows AS filas
FROM sys.partitions p
JOIN sys.indexes i ON i.object_id = p.object_id AND i.index_id = p.index_id
LEFT JOIN sys.partition_range_values prv
       ON prv.function_id = (SELECT function_id FROM sys.partition_functions WHERE name = 'pf_anio')
      AND prv.boundary_id = p.partition_number - 1
WHERE p.object_id = OBJECT_ID('dw.fact_reporte') AND i.index_id = 1
ORDER BY p.partition_number;
GO
