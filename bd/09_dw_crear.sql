/* =====================================================================
   SIPA · 09_dw_crear.sql  ·  Data Warehouse (esquema en constelación)

   Base separada SIPA_DW, alimentada por ETL desde la base transaccional
   SIPA (10_dw_etl.sql). Así las consultas analíticas no cargan la base
   operativa.

   Dimensiones (compartidas):  dim_tiempo, dim_ubicacion, dim_celda,
                               dim_estatus, dim_fuente, dim_semaforo, dim_intervencion
   Hechos:                     fact_reporte       1 fila por reporte
                               fact_priorizacion  1 fila por cálculo del IPU
                               fact_atencion      1 fila por bache que la autoridad atendió
   Datamarts (vistas):         dm_priorizacion.*, dm_financiero.*

   Fragmentación horizontal: fact_reporte se particiona por año.

   ADVERTENCIA: borra y vuelve a crear SIPA_DW si ya existe.
   ===================================================================== */
USE master;
GO
IF DB_ID('SIPA_DW') IS NOT NULL
BEGIN
    ALTER DATABASE SIPA_DW SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
    DROP DATABASE SIPA_DW;
END
GO
CREATE DATABASE SIPA_DW;
GO
USE SIPA_DW;
SET QUOTED_IDENTIFIER ON;
SET ANSI_NULLS ON;
GO
CREATE SCHEMA dw;
GO
CREATE SCHEMA dm_priorizacion;
GO
CREATE SCHEMA dm_financiero;
GO

/* ---------------------------------------------------------------------
   DIMENSIONES
   Cada dimensión tiene una fila -1 «desconocido» para no perder hechos
   cuyo dato falta (p. ej. reportes sin colonia).
   --------------------------------------------------------------------- */

CREATE TABLE dw.dim_tiempo (
    id_tiempo       INT          CONSTRAINT pk_dim_tiempo PRIMARY KEY,   -- AAAAMMDD
    fecha           DATE         NOT NULL,
    anio            SMALLINT     NOT NULL,
    trimestre       TINYINT      NOT NULL,
    mes             TINYINT      NOT NULL,
    nombre_mes      VARCHAR(12)  NOT NULL,
    anio_mes        CHAR(7)      NOT NULL,
    dia_semana      TINYINT      NOT NULL,      -- 1 = lunes
    nombre_dia      VARCHAR(10)  NOT NULL,
    es_fin_semana   BIT          NOT NULL,
    temporada       VARCHAR(7)   NOT NULL       -- LLUVIAS (may-oct) / SECAS
);

CREATE TABLE dw.dim_ubicacion (
    id_ubicacion        INT IDENTITY(1,1) CONSTRAINT pk_dim_ubicacion PRIMARY KEY,
    id_colonia          INT          NULL,      -- llave natural en SIPA
    colonia             VARCHAR(80)  NOT NULL,
    tipo_asentamiento   VARCHAR(30)  NULL,
    territorio          VARCHAR(60)  NOT NULL,
    tipo_territorio     VARCHAR(10)  NOT NULL,
    entidad             VARCHAR(40)  NOT NULL
);

CREATE TABLE dw.dim_celda (
    id_celda                INT IDENTITY(1,1) CONSTRAINT pk_dim_celda PRIMARY KEY,
    celda_id                VARCHAR(12)  NOT NULL,
    latitud                 DECIMAL(9,6) NULL,
    longitud                DECIMAL(9,6) NULL,
    cerca_zona_inundable    BIT          NULL,  -- a 200 m o menos de una zona del atlas
    servicios_500m          INT          NULL   -- escuelas, hospitales y mercados cercanos
);

CREATE TABLE dw.dim_estatus (
    id_estatus          INT IDENTITY(1,1) CONSTRAINT pk_dim_estatus PRIMARY KEY,
    estatus_original    VARCHAR(15) NOT NULL,
    estatus_agrupado    VARCHAR(15) NOT NULL
);

CREATE TABLE dw.dim_fuente (
    id_fuente   INT IDENTITY(1,1) CONSTRAINT pk_dim_fuente PRIMARY KEY,
    nombre      VARCHAR(30) NOT NULL
);

CREATE TABLE dw.dim_semaforo (
    id_semaforo         TINYINT     CONSTRAINT pk_dim_semaforo PRIMARY KEY,
    nombre              VARCHAR(12) NOT NULL,
    orden               TINYINT     NOT NULL,
    dias_objetivo       SMALLINT    NULL        -- sección 6.3 de la propuesta
);

-- Tipo de intervención recomendada, con su tarifa (del JSON de costos)
CREATE TABLE dw.dim_intervencion (
    id_intervencion INT IDENTITY(1,1) CONSTRAINT pk_dim_intervencion PRIMARY KEY,
    clave           VARCHAR(20)   NOT NULL,
    nombre          VARCHAR(80)   NOT NULL,
    costo_m2        DECIMAL(10,2) NULL,
    costo_fijo      DECIMAL(10,2) NULL
);

/* ---------------------------------------------------------------------
   FRAGMENTACIÓN HORIZONTAL de fact_reporte por año.
   En producción cada partición podría ir en un filegroup (disco) distinto
   o en otro servidor; en el prototipo todas van a PRIMARY.
   --------------------------------------------------------------------- */
CREATE PARTITION FUNCTION pf_anio (INT)
    AS RANGE RIGHT FOR VALUES (20200101, 20210101, 20220101, 20230101,
                               20240101, 20250101, 20260101, 20270101);
CREATE PARTITION SCHEME ps_anio AS PARTITION pf_anio ALL TO ([PRIMARY]);
GO

/* ---------------------------------------------------------------------
   HECHOS
   --------------------------------------------------------------------- */

CREATE TABLE dw.fact_reporte (
    id_tiempo           INT     NOT NULL CONSTRAINT fk_frep_tiempo    REFERENCES dw.dim_tiempo(id_tiempo),
    id_reporte          INT     NOT NULL,                       -- dimensión degenerada
    id_ubicacion        INT     NOT NULL CONSTRAINT fk_frep_ubicacion REFERENCES dw.dim_ubicacion(id_ubicacion),
    id_celda            INT     NOT NULL CONSTRAINT fk_frep_celda     REFERENCES dw.dim_celda(id_celda),
    id_estatus          INT     NOT NULL CONSTRAINT fk_frep_estatus   REFERENCES dw.dim_estatus(id_estatus),
    id_fuente           INT     NOT NULL CONSTRAINT fk_frep_fuente    REFERENCES dw.dim_fuente(id_fuente),
    cantidad            TINYINT NOT NULL CONSTRAINT df_frep_cantidad DEFAULT 1,
    posible_duplicado   BIT     NOT NULL,
    ubicacion_dudosa    BIT     NOT NULL,
    ligado_a_bache      BIT     NOT NULL,
    CONSTRAINT pk_fact_reporte PRIMARY KEY CLUSTERED (id_tiempo, id_reporte)
) ON ps_anio (id_tiempo);

CREATE TABLE dw.fact_priorizacion (
    id_calculo          INT          NOT NULL CONSTRAINT pk_fact_priorizacion PRIMARY KEY,
    id_bache            INT          NOT NULL,                  -- dimensión degenerada
    id_tiempo           INT          NOT NULL CONSTRAINT fk_fpri_tiempo    REFERENCES dw.dim_tiempo(id_tiempo),
    id_ubicacion        INT          NOT NULL CONSTRAINT fk_fpri_ubicacion REFERENCES dw.dim_ubicacion(id_ubicacion),
    id_celda            INT          NOT NULL CONSTRAINT fk_fpri_celda     REFERENCES dw.dim_celda(id_celda),
    id_semaforo_modelo  TINYINT      NOT NULL CONSTRAINT fk_fpri_sem_mod   REFERENCES dw.dim_semaforo(id_semaforo),
    id_semaforo_final   TINYINT      NOT NULL CONSTRAINT fk_fpri_sem_fin   REFERENCES dw.dim_semaforo(id_semaforo),
    decision            VARCHAR(12)  NOT NULL,                  -- APROBAR / AJUSTAR / RECHAZAR / PENDIENTE
    version_modelo      VARCHAR(20)  NOT NULL,
    ipu                 DECIMAL(5,4) NOT NULL,
    severidad           TINYINT      NULL,
    id_intervencion     INT          NOT NULL CONSTRAINT fk_fpri_intervencion REFERENCES dw.dim_intervencion(id_intervencion),
    costo_estimado      DECIMAL(12,2) NULL,
    -- valores normalizados de los criterios con datos (para analizar su efecto)
    v_deterioro         DECIMAL(5,4) NULL,
    v_deterioro_mayor   DECIMAL(5,4) NULL,
    v_reportes          DECIMAL(5,4) NULL,
    v_inundacion        DECIMAL(5,4) NULL,
    v_servicios         DECIMAL(5,4) NULL
);

-- Atención informada por la autoridad: desde su decisión hasta que reporta
-- el bache como reparado o descartado. SIPA no ejecuta la reparación.
CREATE TABLE dw.fact_atencion (
    id_bache            INT           NOT NULL CONSTRAINT pk_fact_atencion PRIMARY KEY,
    id_tiempo_decision  INT           NOT NULL CONSTRAINT fk_fate_t_dec    REFERENCES dw.dim_tiempo(id_tiempo),
    id_tiempo_cierre    INT           NULL     CONSTRAINT fk_fate_t_cierre REFERENCES dw.dim_tiempo(id_tiempo),
    id_ubicacion        INT           NOT NULL CONSTRAINT fk_fate_ubicacion REFERENCES dw.dim_ubicacion(id_ubicacion),
    id_celda            INT           NOT NULL CONSTRAINT fk_fate_celda     REFERENCES dw.dim_celda(id_celda),
    id_intervencion     INT           NOT NULL CONSTRAINT fk_fate_intervencion REFERENCES dw.dim_intervencion(id_intervencion),
    id_semaforo_final   TINYINT       NOT NULL CONSTRAINT fk_fate_semaforo  REFERENCES dw.dim_semaforo(id_semaforo),
    estado              VARCHAR(20)   NOT NULL,
    costo_estimado      DECIMAL(12,2) NULL,
    costo_reportado     DECIMAL(12,2) NULL,
    horas_resolucion    INT           NULL,
    dias_objetivo       SMALLINT      NULL,
    cumplio_meta        BIT           NULL      -- reparado dentro del plazo del semáforo
);

-- Índices para las consultas más comunes del tablero
CREATE INDEX ix_frep_ubicacion ON dw.fact_reporte(id_ubicacion) INCLUDE (cantidad);
CREATE INDEX ix_fpri_ubicacion ON dw.fact_priorizacion(id_ubicacion) INCLUDE (ipu, id_semaforo_final);
CREATE INDEX ix_fate_ubicacion ON dw.fact_atencion(id_ubicacion) INCLUDE (costo_reportado, horas_resolucion);

/* Bitácora del proceso ETL */
CREATE TABLE dw.etl_bitacora (
    id_ejecucion    INT IDENTITY(1,1) CONSTRAINT pk_etl_bitacora PRIMARY KEY,
    inicio          DATETIME2(0) NOT NULL,
    fin             DATETIME2(0) NULL,
    paso            VARCHAR(40)  NOT NULL,
    filas           INT          NULL,
    estado          VARCHAR(10)  NOT NULL,
    mensaje         VARCHAR(400) NULL
);
GO

/* ---------------------------------------------------------------------
   Dimensión de tiempo: un día por fila, 2019-2027
   --------------------------------------------------------------------- */
;WITH dias AS (
    SELECT CAST('2019-01-01' AS DATE) AS f
    UNION ALL SELECT DATEADD(DAY, 1, f) FROM dias WHERE f < '2027-12-31'
), d AS (
    -- día de la semana 1 = lunes, sin depender de la configuración del servidor
    SELECT f, (DATEDIFF(DAY, '19000101', f) % 7) + 1 AS dia FROM dias
)
INSERT INTO dw.dim_tiempo
SELECT CONVERT(INT, FORMAT(f, 'yyyyMMdd')), f, YEAR(f), DATEPART(QUARTER, f), MONTH(f),
       CHOOSE(MONTH(f), 'ENERO','FEBRERO','MARZO','ABRIL','MAYO','JUNIO','JULIO',
                        'AGOSTO','SEPTIEMBRE','OCTUBRE','NOVIEMBRE','DICIEMBRE'),
       FORMAT(f, 'yyyy-MM'), dia,
       CHOOSE(dia, 'LUNES','MARTES','MIERCOLES','JUEVES','VIERNES','SABADO','DOMINGO'),
       IIF(dia >= 6, 1, 0),
       IIF(MONTH(f) BETWEEN 5 AND 10, 'LLUVIAS', 'SECAS')
FROM d
OPTION (MAXRECURSION 0);

INSERT INTO dw.dim_semaforo (id_semaforo, nombre, orden, dias_objetivo) VALUES
    (0, 'SIN DECISION', 0, NULL), (1, 'ROJO', 1, 3), (2, 'AMARILLO', 2, 15), (3, 'VERDE', 3, 60);
GO

/* ---------------------------------------------------------------------
   DATAMART DE PRIORIZACIÓN
   --------------------------------------------------------------------- */

-- Último IPU de cada bache, con su ubicación y criterios
CREATE VIEW dm_priorizacion.v_ranking_baches AS
SELECT f.id_bache, u.territorio, u.colonia, c.celda_id, c.latitud, c.longitud,
       f.ipu, sm.nombre AS semaforo_modelo, sf.nombre AS semaforo_final, f.decision,
       f.severidad, f.v_inundacion, f.v_servicios, f.version_modelo,
       RANK() OVER (PARTITION BY u.territorio ORDER BY f.ipu DESC) AS lugar_en_territorio
FROM dw.fact_priorizacion f
JOIN dw.dim_ubicacion u ON u.id_ubicacion = f.id_ubicacion
JOIN dw.dim_celda c     ON c.id_celda = f.id_celda
JOIN dw.dim_semaforo sm ON sm.id_semaforo = f.id_semaforo_modelo
JOIN dw.dim_semaforo sf ON sf.id_semaforo = f.id_semaforo_final
WHERE f.id_calculo = (SELECT MAX(id_calculo) FROM dw.fact_priorizacion x WHERE x.id_bache = f.id_bache);
GO

-- Semáforo por territorio: cuántos baches hay en cada color
CREATE VIEW dm_priorizacion.v_semaforo_territorio AS
SELECT territorio,
       SUM(IIF(semaforo_modelo = 'ROJO', 1, 0))     AS rojos,
       SUM(IIF(semaforo_modelo = 'AMARILLO', 1, 0)) AS amarillos,
       SUM(IIF(semaforo_modelo = 'VERDE', 1, 0))    AS verdes,
       CAST(AVG(ipu) AS DECIMAL(5,4))               AS ipu_promedio
FROM dm_priorizacion.v_ranking_baches
GROUP BY territorio;
GO

-- Celdas críticas: muchos reportes históricos (insumo del programa preventivo)
CREATE VIEW dm_priorizacion.v_celdas_criticas AS
SELECT u.territorio, c.celda_id, c.latitud, c.longitud, c.cerca_zona_inundable, c.servicios_500m,
       SUM(f.cantidad) AS reportes,
       SUM(IIF(t.temporada = 'LLUVIAS', f.cantidad, 0)) AS reportes_lluvias,
       COUNT(DISTINCT t.anio) AS anios_con_reportes
FROM dw.fact_reporte f
JOIN dw.dim_celda c     ON c.id_celda = f.id_celda
JOIN dw.dim_ubicacion u ON u.id_ubicacion = f.id_ubicacion
JOIN dw.dim_tiempo t    ON t.id_tiempo = f.id_tiempo
WHERE c.celda_id <> 'DESCONOCIDA'
GROUP BY u.territorio, c.celda_id, c.latitud, c.longitud, c.cerca_zona_inundable, c.servicios_500m;
GO

-- Percepción vs. evidencia: ¿los baches con más reportes son los de mayor IPU?
CREATE VIEW dm_priorizacion.v_reportes_vs_ipu AS
SELECT r.id_bache, r.territorio, r.colonia, r.ipu, r.semaforo_modelo,
       f.v_reportes,
       RANK() OVER (ORDER BY f.v_reportes DESC) AS lugar_por_reportes,
       RANK() OVER (ORDER BY r.ipu DESC)        AS lugar_por_ipu
FROM dm_priorizacion.v_ranking_baches r
JOIN dw.fact_priorizacion f ON f.id_bache = r.id_bache
WHERE f.id_calculo = (SELECT MAX(id_calculo) FROM dw.fact_priorizacion x WHERE x.id_bache = r.id_bache);
GO

/* ---------------------------------------------------------------------
   DATAMART FINANCIERO
   --------------------------------------------------------------------- */

-- Costo estimado por SIPA vs. costo que reporta la autoridad, por territorio y mes
CREATE VIEW dm_financiero.v_costo_mensual AS
SELECT u.territorio, t.anio, t.mes, t.anio_mes,
       COUNT(*)                         AS baches_reparados,
       SUM(f.costo_estimado)            AS costo_estimado,
       SUM(f.costo_reportado)           AS costo_reportado,
       CAST(100.0 * (SUM(f.costo_reportado) - SUM(f.costo_estimado)) / NULLIF(SUM(f.costo_estimado), 0)
            AS DECIMAL(6,1))            AS desviacion_pct
FROM dw.fact_atencion f
JOIN dw.dim_ubicacion u ON u.id_ubicacion = f.id_ubicacion
JOIN dw.dim_tiempo t    ON t.id_tiempo = f.id_tiempo_cierre
WHERE f.estado = 'REPARADO'
GROUP BY u.territorio, t.anio, t.mes, t.anio_mes;
GO

-- Cumplimiento de tiempos objetivo por semáforo (indicador de la sección 6.5)
CREATE VIEW dm_financiero.v_cumplimiento_semaforo AS
SELECT s.nombre AS semaforo, s.dias_objetivo,
       COUNT(*) AS baches_reparados,
       CAST(AVG(f.horas_resolucion / 24.0) AS DECIMAL(6,1)) AS dias_promedio,
       CAST(100.0 * SUM(CAST(f.cumplio_meta AS INT)) / COUNT(*) AS DECIMAL(5,1)) AS pct_en_meta,
       SUM(f.costo_reportado) AS costo_reportado
FROM dw.fact_atencion f
JOIN dw.dim_semaforo s ON s.id_semaforo = f.id_semaforo_final
WHERE f.estado = 'REPARADO'
GROUP BY s.nombre, s.dias_objetivo, s.orden;
GO

-- Necesidad de inversión por tipo de intervención: lo recomendado (último
-- cálculo de cada bache) y lo que ya se reparó
CREATE VIEW dm_financiero.v_intervenciones AS
SELECT i.clave, i.nombre,
       COUNT(*)                     AS baches_recomendados,
       SUM(p.costo_estimado)        AS costo_estimado_total,
       COUNT(a.id_bache)            AS baches_reparados,
       SUM(a.costo_reportado)       AS costo_reportado_total
FROM dw.fact_priorizacion p
JOIN dw.dim_intervencion i ON i.id_intervencion = p.id_intervencion
LEFT JOIN dw.fact_atencion a ON a.id_bache = p.id_bache AND a.estado = 'REPARADO'
WHERE p.id_calculo = (SELECT MAX(id_calculo) FROM dw.fact_priorizacion x WHERE x.id_bache = p.id_bache)
GROUP BY i.clave, i.nombre;
GO

PRINT 'SIPA_DW creado.';
