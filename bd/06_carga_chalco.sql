/* =====================================================================
   SIPA · 06_carga_chalco.sql
   Agrega Chalco (Estado de México) como segundo territorio, con datos
   abiertos reales del municipio (datosabiertos.chalco.gob.mx):
     - comunidades del Bando 2026
     - reportes de bacheo 2025-2026 (limpios con scripts/procesar_chalco.py)
     - zonas inundables y equipamiento del Atlas de Riesgo 2023
     - escuelas con número de alumnos
   La severidad de los baches es SINTÉTICA.

   ANTES DE EJECUTAR: ajusta @carpeta a la ruta de datos/chalco/limpios.
   ===================================================================== */
USE SIPA;
SET QUOTED_IDENTIFIER ON;
SET ANSI_NULLS ON;
GO
SET NOCOUNT ON;

DECLARE @carpeta NVARCHAR(400) =
    N'C:\Users\gerry\Documents\Rebeca_unrc\sistema_bacheo_3er_semestre\datos\chalco\limpios\';

/* 1. Tablas de paso */
DROP TABLE IF EXISTS #comunidades, #reportes, #zonas, #equipamiento;
CREATE TABLE #comunidades (clave_ut VARCHAR(10), nombre VARCHAR(80), tipo VARCHAR(30));
CREATE TABLE #reportes (
    id_folio VARCHAR(10), folio VARCHAR(20), fecha_solicitud VARCHAR(20), temporada_lluvias VARCHAR(5),
    comunidad VARCHAR(80), comunidad_original VARCHAR(100), comunidad_corregida VARCHAR(5),
    estatus VARCHAR(15), latitud VARCHAR(20), longitud VARCHAR(20), celda_id VARCHAR(12),
    celda_lat VARCHAR(20), celda_lon VARCHAR(20), ubicacion_dudosa VARCHAR(5),
    posible_duplicado VARCHAR(5), grupo_ubicacion VARCHAR(10));
CREATE TABLE #zonas (clave VARCHAR(20), wkt VARCHAR(MAX));
CREATE TABLE #equipamiento (tipo VARCHAR(10), nombre VARCHAR(150), latitud VARCHAR(20),
                            longitud VARCHAR(20), personas VARCHAR(10), fuente VARCHAR(40));

DECLARE @sql NVARCHAR(MAX), @opc NVARCHAR(200) =
    N''' WITH (FORMAT = ''CSV'', FIRSTROW = 2, CODEPAGE = ''65001'');';
SET @sql = N'BULK INSERT #comunidades  FROM ''' + @carpeta + N'comunidades.csv'      + @opc
         + N'BULK INSERT #reportes     FROM ''' + @carpeta + N'reportes_chalco.csv'  + @opc
         + N'BULK INSERT #zonas        FROM ''' + @carpeta + N'zonas_inundables.csv' + @opc
         + N'BULK INSERT #equipamiento FROM ''' + @carpeta + N'equipamiento.csv'     + @opc;
EXEC sp_executesql @sql;

/* 2. Reparto a las tablas normalizadas, todo o nada */
BEGIN TRY
    BEGIN TRANSACTION;

    INSERT INTO territorio (nombre, tipo, entidad) VALUES ('CHALCO', 'MUNICIPIO', 'ESTADO DE MEXICO');
    DECLARE @chalco INT = SCOPE_IDENTITY();

    INSERT INTO colonia (id_territorio, nombre, clave_oficial, tipo_asentamiento)
    SELECT @chalco, nombre, clave_ut, tipo FROM #comunidades;

    INSERT INTO celda (celda_id, latitud, longitud)
    SELECT celda_id, MIN(CAST(celda_lat AS DECIMAL(9,6))), MIN(CAST(celda_lon AS DECIMAL(9,6)))
    FROM #reportes r
    WHERE NOT EXISTS (SELECT 1 FROM celda c WHERE c.celda_id = r.celda_id)
    GROUP BY celda_id;

    DECLARE @fuente TINYINT = (SELECT id_fuente FROM cat_fuente_reporte WHERE nombre = 'CHALCO_DATOS_ABIERTOS');

    INSERT INTO reporte (folio_origen, id_fuente, id_colonia, celda_id, fecha_solicitud,
                         estatus_original, latitud, longitud, descripcion, temporada_lluvias,
                         ubicacion_dudosa, posible_duplicado, grupo_ubicacion)
    SELECT CAST(r.id_folio AS INT), @fuente, c.id_colonia, r.celda_id,
           CAST(r.fecha_solicitud AS DATE), r.estatus,
           CAST(r.latitud AS DECIMAL(9,6)), CAST(r.longitud AS DECIMAL(9,6)),
           CONCAT('Folio ', r.folio,
                  IIF(r.comunidad_corregida = 'True', ' · comunidad original: ' + r.comunidad_original, '')),
           IIF(r.temporada_lluvias = 'True', 1, 0),
           IIF(r.ubicacion_dudosa  = 'True', 1, 0),
           IIF(r.posible_duplicado = 'True', 1, 0),
           CAST(CAST(NULLIF(r.grupo_ubicacion, '') AS DECIMAL(12,1)) AS INT)
    FROM #reportes r
    JOIN colonia c ON c.id_territorio = @chalco AND c.nombre = r.comunidad;

    -- Zonas inundables: se valida el polígono con GEOMETRY y se convierte a
    -- GEOGRAPHY. Si el anillo quedó en sentido contrario (abarcaría casi todo
    -- el planeta), ReorientObject lo corrige.
    INSERT INTO zona_inundable (id_territorio, clave, poligono, fuente)
    SELECT @chalco, z.clave,
           IIF(g.poligono.EnvelopeAngle() > 90, g.poligono.ReorientObject(), g.poligono),
           'ATLAS_RIESGO_2023'
    FROM #zonas z
    CROSS APPLY (SELECT GEOGRAPHY::STGeomFromText(
                     GEOMETRY::STGeomFromText(z.wkt, 4326).MakeValid().STAsText(), 4326) AS poligono) g;

    INSERT INTO equipamiento (id_territorio, tipo, nombre, latitud, longitud, personas, fuente)
    SELECT @chalco, tipo, nombre, CAST(latitud AS DECIMAL(9,6)), CAST(longitud AS DECIMAL(9,6)),
           CAST(NULLIF(personas, '') AS INT), fuente
    FROM #equipamiento;

    -- Baches: uno por celda con reportes abiertos (NUEVO o EN PROCESO)
    INSERT INTO bache (celda_id, latitud, longitud, severidad, profundidad_cm, area_m2,
                       id_estado_bache, fecha_deteccion)
    SELECT r.celda_id, AVG(r.latitud), AVG(r.longitud),
           1 + CAST(SUBSTRING(HASHBYTES('MD5', CONCAT(r.celda_id, '|severidad')), 1, 3) AS INT) % 5,
           CAST(2 + CAST(SUBSTRING(HASHBYTES('MD5', CONCAT(r.celda_id, '|profundidad')), 1, 3) AS INT) % 150 / 10.0 AS DECIMAL(5,1)),
           CAST(0.2 + CAST(SUBSTRING(HASHBYTES('MD5', CONCAT(r.celda_id, '|area')), 1, 3) AS INT) % 300 / 100.0 AS DECIMAL(6,2)),
           2, MIN(r.fecha_solicitud)
    FROM reporte r
    WHERE r.id_fuente = @fuente AND r.estatus_original IN ('NUEVO','EN PROCESO')
    GROUP BY r.celda_id
    ORDER BY r.celda_id;   -- orden fijo: los id_bache salen iguales en cada reconstrucción

    UPDATE r SET id_bache = b.id_bache
    FROM reporte r
    JOIN bache b ON b.celda_id = r.celda_id
    WHERE r.id_fuente = @fuente AND r.estatus_original IN ('NUEVO','EN PROCESO');

    -- Cuenta de autoridad (de prueba) del municipio
    INSERT INTO usuario (nombre, rol, id_territorio) VALUES ('Autoridad Chalco', 'AUTORIDAD', @chalco);

    -- Pesos del IPU vigentes (v2), copiados de la configuración general
    INSERT INTO peso_criterio (id_territorio, id_criterio, vigente_desde, peso)
    SELECT DISTINCT @chalco, id_criterio, vigente_desde, peso
    FROM peso_criterio
    WHERE vigente_hasta IS NULL
      AND id_territorio = (SELECT MIN(id_territorio) FROM territorio);

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
    PRINT 'ERROR en la carga de Chalco, no se guardó nada: ' + ERROR_MESSAGE();
    THROW;
END CATCH;

/* 3. Cálculo del IPU para todos los baches abiertos de Chalco */
DECLARE @b INT, @calc INT;
DECLARE baches CURSOR LOCAL FAST_FORWARD FOR
    SELECT DISTINCT b.id_bache
    FROM bache b
    JOIN reporte r ON r.id_bache = b.id_bache
    JOIN colonia c ON c.id_colonia = r.id_colonia
    JOIN territorio t ON t.id_territorio = c.id_territorio
    WHERE t.nombre = 'CHALCO';
OPEN baches;
FETCH NEXT FROM baches INTO @b;
WHILE @@FETCH_STATUS = 0
BEGIN
    EXEC sp_calcular_ipu @b, @calc OUTPUT;
    FETCH NEXT FROM baches INTO @b;
END
CLOSE baches; DEALLOCATE baches;

/* 4. Verificación */
SELECT 'colonias Chalco' AS dato, COUNT(*) AS n FROM colonia c JOIN territorio t ON t.id_territorio = c.id_territorio WHERE t.nombre = 'CHALCO'
UNION ALL SELECT 'reportes Chalco', COUNT(*) FROM reporte r JOIN cat_fuente_reporte f ON f.id_fuente = r.id_fuente WHERE f.nombre = 'CHALCO_DATOS_ABIERTOS'
UNION ALL SELECT 'zonas inundables', COUNT(*) FROM zona_inundable
UNION ALL SELECT 'equipamiento', COUNT(*) FROM equipamiento
UNION ALL SELECT 'baches abiertos Chalco', COUNT(DISTINCT id_bache) FROM reporte r JOIN cat_fuente_reporte f ON f.id_fuente = r.id_fuente WHERE f.nombre = 'CHALCO_DATOS_ABIERTOS' AND r.id_bache IS NOT NULL;
GO
