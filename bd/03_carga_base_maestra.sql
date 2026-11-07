/* =====================================================================
   SIPA · 03_carga_base_maestra.sql
   Carga la base maestra limpia (datos/limpios/base_maestra_limpia.csv)
   y la reparte en las tablas normalizadas:
       staging  ->  territorio, colonia, celda, reporte
   Al final asigna los pesos iniciales del IPU a cada territorio.

   ANTES DE EJECUTAR: cambia @archivo a la ruta del CSV en tu equipo.
   El servicio de SQL Server debe poder leer esa carpeta; si marca
   "Access is denied", copia el CSV a C:\SIPA\ y usa esa ruta.
   ===================================================================== */
USE SIPA;
SET QUOTED_IDENTIFIER ON;
SET ANSI_NULLS ON;
GO
SET NOCOUNT ON;

DECLARE @archivo NVARCHAR(400) =
    N'C:\Users\gerry\Documents\Rebeca_unrc\sistema_bacheo_3er_semestre\datos\limpios\base_maestra_limpia.csv';

/* 1. Tabla temporal de paso con la misma forma que el CSV (todo como texto) */
DROP TABLE IF EXISTS #staging;
CREATE TABLE #staging (
    id_folio VARCHAR(20), fecha_solicitud VARCHAR(20), anio VARCHAR(10), mes VARCHAR(10),
    anio_mes VARCHAR(10), temporada_lluvias VARCHAR(10), periodo_atipico VARCHAR(10),
    conjunto VARCHAR(20), alcaldia VARCHAR(60), alcaldia_inferida VARCHAR(10),
    colonia_datos VARCHAR(100), colonia_inferida VARCHAR(10), estatus VARCHAR(20),
    estatus_original VARCHAR(20), latitud VARCHAR(30), longitud VARCHAR(30),
    celda_id VARCHAR(20), celda_lat VARCHAR(30), celda_lon VARCHAR(30),
    ubicacion_dudosa VARCHAR(10), posible_duplicado VARCHAR(10),
    grupo_ubicacion VARCHAR(20), fila_original VARCHAR(20)
);

DECLARE @sql NVARCHAR(MAX) = N'
BULK INSERT #staging FROM ''' + REPLACE(@archivo, '''', '''''') + N'''
WITH (FORMAT = ''CSV'', FIRSTROW = 2, CODEPAGE = ''65001'', TABLOCK);';
EXEC sp_executesql @sql;
PRINT 'Filas leídas del CSV: ' + CAST(@@ROWCOUNT AS VARCHAR);

/* 2. Reparto a tablas normalizadas, todo o nada */
BEGIN TRY
    BEGIN TRANSACTION;

    -- Territorios (alcaldías)
    INSERT INTO territorio (nombre, tipo, entidad)
    SELECT DISTINCT alcaldia, 'ALCALDIA', 'CIUDAD DE MEXICO'
    FROM #staging WHERE NULLIF(alcaldia,'') IS NOT NULL;

    -- Una cuenta de autoridad (de prueba) por alcaldía: decide y reporta el estado
    INSERT INTO usuario (nombre, rol, id_territorio)
    SELECT CONCAT('Autoridad ', nombre), 'AUTORIDAD', id_territorio FROM territorio;

    -- Colonias; los reportes sin colonia se agrupan en "SIN COLONIA" de su alcaldía
    INSERT INTO colonia (id_territorio, nombre)
    SELECT DISTINCT t.id_territorio, COALESCE(NULLIF(s.colonia_datos,''), 'SIN COLONIA')
    FROM #staging s
    JOIN territorio t ON t.nombre = s.alcaldia;

    -- Celdas de la cuadrícula
    INSERT INTO celda (celda_id, latitud, longitud)
    SELECT celda_id, MIN(CAST(celda_lat AS DECIMAL(9,6))), MIN(CAST(celda_lon AS DECIMAL(9,6)))
    FROM #staging WHERE NULLIF(celda_id,'') IS NOT NULL
    GROUP BY celda_id;

    -- Reportes históricos
    DECLARE @fuente TINYINT = (SELECT id_fuente FROM cat_fuente_reporte WHERE nombre = 'BASE_MAESTRA_CDMX');

    INSERT INTO reporte (folio_origen, id_fuente, id_colonia, celda_id, fecha_solicitud,
                         estatus_original, latitud, longitud, conjunto, temporada_lluvias,
                         periodo_atipico, alcaldia_inferida, colonia_inferida,
                         ubicacion_dudosa, posible_duplicado, grupo_ubicacion)
    SELECT CAST(s.id_folio AS INT),
           @fuente,
           c.id_colonia,
           NULLIF(s.celda_id,''),
           CAST(s.fecha_solicitud AS DATE),
           s.estatus_original,
           CAST(NULLIF(s.latitud,'')  AS DECIMAL(9,6)),
           CAST(NULLIF(s.longitud,'') AS DECIMAL(9,6)),
           s.conjunto,
           IIF(s.temporada_lluvias = 'True', 1, 0),
           IIF(s.periodo_atipico   = 'True', 1, 0),
           IIF(s.alcaldia_inferida = 'True', 1, 0),
           IIF(s.colonia_inferida  = 'True', 1, 0),
           IIF(s.ubicacion_dudosa  = 'True', 1, 0),
           IIF(s.posible_duplicado = 'True', 1, 0),
           CAST(CAST(NULLIF(s.grupo_ubicacion,'') AS DECIMAL(12,1)) AS INT)
    FROM #staging s
    LEFT JOIN territorio t ON t.nombre = s.alcaldia
    LEFT JOIN colonia c    ON c.id_territorio = t.id_territorio
                          AND c.nombre = COALESCE(NULLIF(s.colonia_datos,''), 'SIN COLONIA')
    ORDER BY CAST(s.id_folio AS INT);   -- orden fijo de id_reporte

    -- Pesos del IPU (iguales para todos los territorios; suman 1).
    -- v1 (ene 2026): 8 criterios de la propuesta de arquitectura.
    -- v2 (oct 2026): se agregan INUNDACION y ACCESO_SERVICIOS, retomando el
    --   índice 0-100 propuesto por el docente de Pensamiento Complejo.
    -- Se conservan ambas versiones para poder comparar (vigente_hasta).
    INSERT INTO peso_criterio (id_territorio, id_criterio, vigente_desde, vigente_hasta, peso)
    SELECT t.id_territorio, c.id_criterio, p.desde, p.hasta, p.peso
    FROM territorio t
    CROSS JOIN (VALUES
        ('DETERIORO',      '2026-01-01','2026-10-23',0.20), ('DETERIORO',       '2026-10-23',NULL,0.15),
        ('RIESGO_72H',     '2026-01-01','2026-10-23',0.20), ('RIESGO_72H',      '2026-10-23',NULL,0.15),
        ('PERSONAS',       '2026-01-01','2026-10-23',0.15), ('PERSONAS',        '2026-10-23',NULL,0.10),
        ('TRANSPORTE',     '2026-01-01','2026-10-23',0.10), ('TRANSPORTE',      '2026-10-23',NULL,0.05),
        ('TRANSITO',       '2026-01-01','2026-10-23',0.10), ('TRANSITO',        '2026-10-23',NULL,0.10),
        ('VULNERABILIDAD', '2026-01-01','2026-10-23',0.10), ('VULNERABILIDAD',  '2026-10-23',NULL,0.10),
        ('DETERIORO_MAYOR','2026-01-01','2026-10-23',0.10), ('DETERIORO_MAYOR', '2026-10-23',NULL,0.05),
        ('REPORTES',       '2026-01-01','2026-10-23',0.05), ('REPORTES',        '2026-10-23',NULL,0.05),
        ('INUNDACION',     '2026-10-23',NULL,0.15),
        ('ACCESO_SERVICIOS','2026-10-23',NULL,0.10)
    ) p(clave, desde, hasta, peso)
    JOIN criterio_ipu c ON c.clave = p.clave;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
    PRINT 'ERROR en la carga, no se guardó nada: ' + ERROR_MESSAGE();
    THROW;
END CATCH;

/* 3. Verificación */
SELECT 'territorio' AS tabla, COUNT(*) AS filas FROM territorio
UNION ALL SELECT 'colonia', COUNT(*) FROM colonia
UNION ALL SELECT 'celda',   COUNT(*) FROM celda
UNION ALL SELECT 'reporte', COUNT(*) FROM reporte
UNION ALL SELECT 'peso_criterio', COUNT(*) FROM peso_criterio;

-- Los pesos de cada territorio deben sumar exactamente 1
SELECT id_territorio, SUM(peso) AS suma_pesos
FROM peso_criterio WHERE vigente_hasta IS NULL
GROUP BY id_territorio HAVING SUM(peso) <> 1;   -- debe salir vacío
GO
