/* =====================================================================
   SIPA · 05c_transporte_marginacion.sql
   Carga dos fuentes reales y las resume por celda para el IPU:
     - parada_transporte  : 10,961 paradas del GTFS CDMX (SEMOVI) con las
                            salidas por día que pasan por cada una
     - marginacion_colonia: índice de marginación urbana 2020 (CONAPO) de
                            2,243 colonias de la CDMX, con su polígono
     - contexto_celda     : por celda de la CDMX,
         v_transporte     = LOG(1 + salidas/día a <= 300 m) / LOG(1 + p95),
                            con tope 1 (0 si no pasa transporte público)
         v_vulnerabilidad = (IMN máx - IMN de la colonia) / (IMN máx - IMN mín)
                            (en CONAPO, IMN alto = menos marginación)
   Las celdas de Chalco no se calculan: el GTFS y el índice solo cubren la
   CDMX, así que ahí ambos criterios siguen en 0.5.

   Archivos de entrada: scripts/procesar_fuentes_ipu.py (ver FUENTE.md).
   ANTES DE EJECUTAR: ajusta @carpeta a la ruta del proyecto.
   ===================================================================== */
USE SIPA;
SET QUOTED_IDENTIFIER ON;
SET ANSI_NULLS ON;
GO
SET NOCOUNT ON;
SET XACT_ABORT ON;

DECLARE @carpeta NVARCHAR(400) = N'C:\Users\gerry\Documents\Rebeca_unrc\sistema_bacheo_3er_semestre\datos\';

/* 1. Tablas */
DROP TABLE IF EXISTS contexto_celda, parada_transporte, marginacion_colonia;

CREATE TABLE parada_transporte (
    stop_id      VARCHAR(40)  CONSTRAINT pk_parada PRIMARY KEY,
    nombre       VARCHAR(150) NOT NULL,
    modo         VARCHAR(15)  NOT NULL,
    ubicacion    GEOGRAPHY    NOT NULL,
    rutas        SMALLINT     NOT NULL CONSTRAINT ck_parada_rutas   CHECK (rutas >= 1),
    salidas_dia  INT          NOT NULL CONSTRAINT ck_parada_salidas CHECK (salidas_dia >= 0)
);

CREATE TABLE marginacion_colonia (
    id_col       INT          CONSTRAINT pk_marginacion PRIMARY KEY,
    colonia      VARCHAR(120) NOT NULL,
    alcaldia     VARCHAR(60)  NOT NULL,
    cp           VARCHAR(5)   NULL,
    im_2020      DECIMAL(9,4) NOT NULL,
    grado        VARCHAR(10)  NOT NULL
                 CONSTRAINT ck_marginacion_grado CHECK (grado IN ('Muy bajo','Bajo','Medio','Alto','Muy alto')),
    imn_2020     DECIMAL(9,6) NOT NULL CONSTRAINT ck_marginacion_imn CHECK (imn_2020 BETWEEN 0 AND 1),
    poligono     GEOGRAPHY    NOT NULL
);

CREATE TABLE contexto_celda (
    celda_id          VARCHAR(12)  CONSTRAINT pk_contexto_celda PRIMARY KEY
                                   CONSTRAINT fk_contexto_celda REFERENCES celda(celda_id),
    paradas_300m      INT          NOT NULL,
    salidas_dia_300m  INT          NOT NULL,
    v_transporte      DECIMAL(5,4) NOT NULL CONSTRAINT ck_contexto_vt CHECK (v_transporte BETWEEN 0 AND 1),
    id_col            INT          NULL CONSTRAINT fk_contexto_colonia REFERENCES marginacion_colonia(id_col),
    grado_marginacion VARCHAR(10)  NULL,
    v_vulnerabilidad  DECIMAL(5,4) NULL CONSTRAINT ck_contexto_vv CHECK (v_vulnerabilidad BETWEEN 0 AND 1)
);

/* 2. Carga de los CSV */
DROP TABLE IF EXISTS #p, #m;
CREATE TABLE #p (stop_id VARCHAR(40), nombre VARCHAR(150), modo VARCHAR(15), latitud VARCHAR(20),
                 longitud VARCHAR(20), rutas VARCHAR(10), salidas_dia VARCHAR(12));
CREATE TABLE #m (id_col VARCHAR(10), colonia VARCHAR(120), alcaldia VARCHAR(60), cp VARCHAR(10),
                 im_2020 VARCHAR(20), grado VARCHAR(10), imn_2020 VARCHAR(20), wkt VARCHAR(MAX));
DECLARE @sql NVARCHAR(MAX), @opc NVARCHAR(200) = N''' WITH (FORMAT = ''CSV'', FIRSTROW = 2, CODEPAGE = ''65001'');';
SET @sql = N'BULK INSERT #p FROM ''' + @carpeta + N'gtfs\limpios\paradas.csv' + @opc
         + N'BULK INSERT #m FROM ''' + @carpeta + N'marginacion\limpios\colonias_marginacion.csv' + @opc;
EXEC sp_executesql @sql;

BEGIN TRANSACTION;
    INSERT INTO parada_transporte (stop_id, nombre, modo, ubicacion, rutas, salidas_dia)
    SELECT stop_id, nombre, modo,
           GEOGRAPHY::Point(CAST(latitud AS FLOAT), CAST(longitud AS FLOAT), 4326),
           CAST(rutas AS SMALLINT), CAST(salidas_dia AS INT)
    FROM #p;

    -- Igual que las zonas inundables (06): se valida como GEOMETRY (y otra vez
    -- como GEOGRAPHY, porque algunos polígonos se autointersectan) y, si el
    -- anillo quedó al revés (abarcaría casi todo el planeta), se reorienta.
    INSERT INTO marginacion_colonia (id_col, colonia, alcaldia, cp, im_2020, grado, imn_2020, poligono)
    SELECT CAST(m.id_col AS INT), m.colonia, m.alcaldia, RIGHT('0' + m.cp, 5),
           CAST(m.im_2020 AS DECIMAL(9,4)), m.grado, CAST(m.imn_2020 AS DECIMAL(9,6)),
           IIF(g.poligono.EnvelopeAngle() > 90, g.poligono.ReorientObject(), g.poligono)
    FROM #m m
    CROSS APPLY (SELECT GEOGRAPHY::STGeomFromText(
                     GEOMETRY::STGeomFromText(m.wkt, 4326).MakeValid().STAsText(), 4326).MakeValid() AS poligono) g;
COMMIT TRANSACTION;

CREATE SPATIAL INDEX six_parada_ubicacion   ON parada_transporte(ubicacion);
CREATE SPATIAL INDEX six_marginacion_poligono ON marginacion_colonia(poligono);

/* 3. Resumen por celda de la CDMX */
DROP TABLE IF EXISTS #celdas;
SELECT c.celda_id, GEOGRAPHY::Point(c.latitud, c.longitud, 4326) AS punto
INTO #celdas
FROM celda c
WHERE EXISTS (SELECT 1 FROM reporte r
              JOIN colonia co   ON co.id_colonia = r.id_colonia
              JOIN territorio t ON t.id_territorio = co.id_territorio
              WHERE r.celda_id = c.celda_id AND t.entidad = 'CIUDAD DE MEXICO');

DROP TABLE IF EXISTS #t;
SELECT c.celda_id, COUNT(p.stop_id) AS paradas, ISNULL(SUM(p.salidas_dia), 0) AS salidas
INTO #t
FROM #celdas c
LEFT JOIN parada_transporte p WITH (INDEX(six_parada_ubicacion))
       ON p.ubicacion.STDistance(c.punto) <= 300
GROUP BY c.celda_id;

DECLARE @p95 FLOAT = (SELECT TOP 1 PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY salidas) OVER ()
                      FROM #t WHERE salidas > 0);
DECLARE @imn_min FLOAT = (SELECT MIN(imn_2020) FROM marginacion_colonia),
        @imn_max FLOAT = (SELECT MAX(imn_2020) FROM marginacion_colonia);

-- Colonia de cada celda: la que contiene su centro; si cae en un hueco
-- (camellón, parque), la más cercana a <= 250 m.
DROP TABLE IF EXISTS #col;
SELECT c.celda_id, x.id_col
INTO #col
FROM #celdas c
OUTER APPLY (SELECT TOP 1 m.id_col FROM marginacion_colonia m WITH (INDEX(six_marginacion_poligono))
             WHERE m.poligono.STIntersects(c.punto) = 1) dentro
OUTER APPLY (SELECT TOP 1 m.id_col FROM marginacion_colonia m WITH (INDEX(six_marginacion_poligono))
             WHERE dentro.id_col IS NULL AND m.poligono.STDistance(c.punto) <= 250
             ORDER BY m.poligono.STDistance(c.punto)) cerca
CROSS APPLY (SELECT COALESCE(dentro.id_col, cerca.id_col) AS id_col) x;

INSERT INTO contexto_celda (celda_id, paradas_300m, salidas_dia_300m, v_transporte,
                            id_col, grado_marginacion, v_vulnerabilidad)
SELECT t.celda_id, t.paradas, t.salidas,
       CAST(IIF(t.salidas = 0, 0, IIF(LOG(1 + t.salidas) / LOG(1 + @p95) > 1, 1,
                                      LOG(1 + t.salidas) / LOG(1 + @p95))) AS DECIMAL(5,4)),
       m.id_col, m.grado,
       CAST((@imn_max - m.imn_2020) / (@imn_max - @imn_min) AS DECIMAL(5,4))
FROM #t t
JOIN #col c ON c.celda_id = t.celda_id
LEFT JOIN marginacion_colonia m ON m.id_col = c.id_col;

/* 4. Resumen */
DECLARE @par INT, @col INT, @cel INT, @con_tr INT, @con_col INT;
SELECT @par = COUNT(*) FROM parada_transporte;
SELECT @col = COUNT(*) FROM marginacion_colonia;
SELECT @cel = COUNT(*), @con_tr = SUM(IIF(paradas_300m > 0, 1, 0)), @con_col = COUNT(id_col) FROM contexto_celda;
PRINT 'Paradas: ' + CAST(@par AS VARCHAR) + ' · colonias con marginación: ' + CAST(@col AS VARCHAR);
PRINT 'Celdas CDMX: ' + CAST(@cel AS VARCHAR) + ' · con transporte a 300 m: ' + CAST(@con_tr AS VARCHAR)
    + ' · con colonia CONAPO: ' + CAST(@con_col AS VARCHAR) + ' · p95 salidas/día: ' + CAST(CAST(@p95 AS INT) AS VARCHAR);
GO
