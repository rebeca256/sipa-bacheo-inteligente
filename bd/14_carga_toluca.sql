/* =====================================================================
   SIPA · 14_carga_toluca.sql
   Fuente externa: tablero público de bacheo de Toluca (DGOP),
   https://dgop.toluca.gob.mx/tablero_bacheo_filtros1.php
   74,319 baches reparados (2025-2026) y medidas reales de una muestra.
   Se guardan en un esquema aparte (ext) para no mezclarlos con la
   operación de SIPA: sirven para validar tamaños, costos y conteos.

   Requiere: python scripts/descargar_toluca.py y python scripts/limpiar_toluca.py
   ANTES DE EJECUTAR: ajusta @carpeta a la ruta de datos/limpios.
   ===================================================================== */
USE SIPA;
SET QUOTED_IDENTIFIER ON;
SET ANSI_NULLS ON;
GO
IF SCHEMA_ID('ext') IS NULL EXEC('CREATE SCHEMA ext');
GO
SET NOCOUNT ON;

DROP VIEW IF EXISTS ext.v_toluca_delegacion, ext.v_toluca_mes, ext.v_toluca_costo_tipo;
DROP TABLE IF EXISTS ext.toluca_medida, ext.toluca_bache;

CREATE TABLE ext.toluca_bache (
    folio       VARCHAR(30)  NOT NULL CONSTRAINT pk_toluca_bache PRIMARY KEY,
    tipo        VARCHAR(15)  NOT NULL CONSTRAINT ck_toluca_tipo CHECK (tipo IN ('PROFUNDO','SUPERFICIAL','SIN_CLASIFICAR')),
    calle       NVARCHAR(150) NULL,
    colonia     NVARCHAR(150) NULL,
    delegacion  NVARCHAR(100) NULL,
    estatus     VARCHAR(15)  NOT NULL,
    fecha       DATE         NOT NULL,
    latitud     DECIMAL(9,6) NULL,
    longitud    DECIMAL(9,6) NULL
);
CREATE TABLE ext.toluca_medida (
    folio          VARCHAR(30)  NOT NULL CONSTRAINT pk_toluca_medida PRIMARY KEY
                   CONSTRAINT fk_toluca_medida_bache REFERENCES ext.toluca_bache(folio),
    largo_m        DECIMAL(6,2) NOT NULL CHECK (largo_m > 0),
    ancho_m        DECIMAL(6,2) NOT NULL CHECK (ancho_m > 0),
    area_m2        AS CAST(largo_m * ancho_m AS DECIMAL(8,3)) PERSISTED,
    profundidad_cm DECIMAL(5,1) NULL CHECK (profundidad_cm > 0 AND profundidad_cm <= 40)
);
CREATE INDEX ix_toluca_bache_deleg ON ext.toluca_bache(delegacion, fecha);

DECLARE @carpeta NVARCHAR(400) =
    N'C:\Users\gerry\Documents\Rebeca_unrc\sistema_bacheo_3er_semestre\datos\limpios\';

DROP TABLE IF EXISTS #b, #m;
CREATE TABLE #b (folio VARCHAR(30), tipo VARCHAR(15), calle NVARCHAR(150), colonia NVARCHAR(150),
                 delegacion NVARCHAR(100), estatus VARCHAR(15), fecha VARCHAR(30), anio VARCHAR(6),
                 mes VARCHAR(10), lat VARCHAR(20), lng VARCHAR(20));
CREATE TABLE #m (folio VARCHAR(30), tipo VARCHAR(15), largo VARCHAR(20), ancho VARCHAR(20), area VARCHAR(20),
                 prof VARCHAR(20), vol VARCHAR(20), delegacion NVARCHAR(100), colonia NVARCHAR(150));

DECLARE @sql NVARCHAR(MAX), @opc NVARCHAR(200) =
    N''' WITH (FORMAT = ''CSV'', FIRSTROW = 2, CODEPAGE = ''65001'');';
SET @sql = N'BULK INSERT #b FROM ''' + @carpeta + N'toluca_baches.csv' + @opc
         + N'BULK INSERT #m FROM ''' + @carpeta + N'toluca_medidas.csv' + @opc;
EXEC (@sql);

BEGIN TRANSACTION;
INSERT INTO ext.toluca_bache (folio, tipo, calle, colonia, delegacion, estatus, fecha, latitud, longitud)
SELECT folio, tipo, NULLIF(calle,''), NULLIF(colonia,''), NULLIF(delegacion,''), estatus,
       CAST(LEFT(fecha,10) AS DATE), TRY_CAST(NULLIF(lat,'') AS DECIMAL(9,6)), TRY_CAST(NULLIF(lng,'') AS DECIMAL(9,6))
FROM #b;
INSERT INTO ext.toluca_medida (folio, largo_m, ancho_m, profundidad_cm)
SELECT m.folio, CAST(m.largo AS DECIMAL(6,2)), CAST(m.ancho AS DECIMAL(6,2)),
       TRY_CAST(NULLIF(m.prof,'') AS DECIMAL(5,1))
FROM #m m JOIN ext.toluca_bache b ON b.folio = m.folio;
COMMIT;
GO

/* Vistas */
CREATE VIEW ext.v_toluca_delegacion AS
SELECT delegacion,
       COUNT(*) AS baches,
       SUM(CASE WHEN tipo = 'PROFUNDO' THEN 1 ELSE 0 END) AS profundos,
       CAST(100.0 * SUM(CASE WHEN tipo = 'PROFUNDO' THEN 1 ELSE 0 END) / COUNT(*) AS DECIMAL(5,1)) AS pct_profundos,
       MIN(fecha) AS primera, MAX(fecha) AS ultima
FROM ext.toluca_bache
GROUP BY delegacion;
GO
CREATE VIEW ext.v_toluca_mes AS
SELECT YEAR(fecha) AS anio, MONTH(fecha) AS mes, tipo, COUNT(*) AS baches
FROM ext.toluca_bache
GROUP BY YEAR(fecha), MONTH(fecha), tipo;
GO
/* Costo con las mismas tarifas de SIPA (catálogo tarifa_reparacion si existe; si no, valores del JSON) */
CREATE VIEW ext.v_toluca_costo_tipo AS
SELECT b.tipo,
       COUNT(*) AS baches_medidos,
       CAST(AVG(m.area_m2) AS DECIMAL(8,2)) AS area_media_m2,
       CAST(AVG(m.profundidad_cm) AS DECIMAL(5,1)) AS profundidad_media_cm,
       CAST(AVG(CASE b.tipo WHEN 'PROFUNDO'
                    THEN 1500 + 720 * IIF(m.area_m2 > 1.0, m.area_m2, 1.0)
                    ELSE  900 + 380 * IIF(m.area_m2 > 0.5, m.area_m2, 0.5) END) AS DECIMAL(10,2)) AS costo_medio
FROM ext.toluca_medida m JOIN ext.toluca_bache b ON b.folio = m.folio
WHERE b.tipo <> 'SIN_CLASIFICAR'
GROUP BY b.tipo;
GO

/* Comprobación */
SELECT (SELECT COUNT(*) FROM ext.toluca_bache) AS baches, (SELECT COUNT(*) FROM ext.toluca_medida) AS medidas;
SELECT TOP 5 * FROM ext.v_toluca_delegacion ORDER BY baches DESC;
SELECT * FROM ext.v_toluca_costo_tipo;
