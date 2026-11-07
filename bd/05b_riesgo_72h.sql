/* =====================================================================
   SIPA · 05b_riesgo_72h.sql
   Carga el riesgo de accidente a 72 h por celda que calcula el modelo de
   Probabilidad (probabilidad/resultados/t4_riesgo_72h_por_celda.csv) y lo
   deja disponible para el criterio RIESGO_72H del IPU (sp_calcular_ipu).
   Solo cubre CDMX; las celdas sin dato (p. ej. Chalco) siguen en 0.5.

   ANTES DE EJECUTAR: ajusta @archivo a la ruta del CSV.
   ===================================================================== */
USE SIPA;
SET QUOTED_IDENTIFIER ON;
SET ANSI_NULLS ON;
GO
SET NOCOUNT ON;

DECLARE @archivo NVARCHAR(400) =
    N'C:\Users\gerry\Documents\Rebeca_unrc\sistema_bacheo_3er_semestre\probabilidad\resultados\t4_riesgo_72h_por_celda.csv';

IF OBJECT_ID('riesgo_celda_72h') IS NULL
CREATE TABLE riesgo_celda_72h (
    celda_id       VARCHAR(12)  CONSTRAINT pk_riesgo_celda PRIMARY KEY
                                CONSTRAINT fk_riesgo_celda REFERENCES celda(celda_id),
    acc_total      INT          NOT NULL,
    graves_total   INT          NOT NULL,
    via_rapida     BIT          NOT NULL,
    lambda_anual   DECIMAL(10,6) NOT NULL,
    p72_accidente  DECIMAL(9,8) NOT NULL CONSTRAINT ck_riesgo_p72  CHECK (p72_accidente BETWEEN 0 AND 1),
    p72_grave      DECIMAL(11,10) NOT NULL CONSTRAINT ck_riesgo_p72g CHECK (p72_grave BETWEEN 0 AND 1),
    semaforo_72h   VARCHAR(8)   NOT NULL CONSTRAINT ck_riesgo_sem  CHECK (semaforo_72h IN ('ROJO','AMARILLO','VERDE')),
    v_riesgo_72h   DECIMAL(5,4) NOT NULL CONSTRAINT ck_riesgo_v    CHECK (v_riesgo_72h BETWEEN 0 AND 1),
    fecha_carga    DATETIME2(0) NOT NULL DEFAULT SYSDATETIME()
);

DROP TABLE IF EXISTS #r;
CREATE TABLE #r (celda_id VARCHAR(20), acc_total VARCHAR(10), graves_total VARCHAR(10),
                 via_rapida VARCHAR(10), lambda_anual VARCHAR(30), p72_accidente VARCHAR(30),
                 p72_grave VARCHAR(30), semaforo_72h VARCHAR(10), v_riesgo_72h VARCHAR(10));

DECLARE @sql NVARCHAR(MAX) = N'BULK INSERT #r FROM ''' + REPLACE(@archivo, '''', '''''') + N'''
WITH (FORMAT = ''CSV'', FIRSTROW = 2, CODEPAGE = ''65001'');';
EXEC sp_executesql @sql;
PRINT 'Filas leídas del CSV: ' + CAST(@@ROWCOUNT AS VARCHAR);

BEGIN TRANSACTION;
    DELETE FROM riesgo_celda_72h;
    INSERT INTO riesgo_celda_72h (celda_id, acc_total, graves_total, via_rapida, lambda_anual,
                                  p72_accidente, p72_grave, semaforo_72h, v_riesgo_72h)
    SELECT r.celda_id, CAST(r.acc_total AS INT), CAST(r.graves_total AS INT),
           IIF(r.via_rapida = 'True', 1, 0),
           CAST(CAST(r.lambda_anual  AS FLOAT) AS DECIMAL(10,6)),
           CAST(CAST(r.p72_accidente AS FLOAT) AS DECIMAL(9,8)),
           CAST(CAST(r.p72_grave     AS FLOAT) AS DECIMAL(11,10)),
           r.semaforo_72h, CAST(r.v_riesgo_72h AS DECIMAL(5,4))
    FROM #r r
    JOIN celda c ON c.celda_id = r.celda_id;   -- solo celdas que existen en la base
COMMIT TRANSACTION;

DECLARE @cargadas INT, @leidas INT, @con INT, @total INT;
SELECT @cargadas = COUNT(*) FROM riesgo_celda_72h;
SELECT @leidas = COUNT(*) FROM #r;
SELECT @con = COUNT(*) FROM bache b JOIN riesgo_celda_72h r ON r.celda_id = b.celda_id;
SELECT @total = COUNT(*) FROM bache;
PRINT 'Celdas con riesgo 72 h cargadas: ' + CAST(@cargadas AS VARCHAR)
    + ' (descartadas por no existir en celda: ' + CAST(@leidas - @cargadas AS VARCHAR) + ')';
PRINT 'Baches con riesgo 72 h disponible: ' + CAST(@con AS VARCHAR) + ' de ' + CAST(@total AS VARCHAR);
GO
