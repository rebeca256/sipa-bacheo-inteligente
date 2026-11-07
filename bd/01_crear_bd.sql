/* =====================================================================
   SIPA - Sistema Inteligente de Priorización Asfáltica
   01_crear_bd.sql  ·  Diseño físico de la base transaccional (SQL Server)

   Fundamentos de Bases de Datos · 3er semestre · 2026-2

   SIPA es un sistema de ASESORÍA: recomienda qué bache atender primero, por
   qué y cuánto costaría. La reparación (brigadas, material, presupuesto) la
   hace la autoridad; SIPA solo registra el estado que ella reporta.

   Crea la base SIPA con su modelo relacional normalizado a 3FN:
     - esquema dbo  : datos operativos del sistema
     - esquema priv : datos personales (acceso restringido, minimización)
   El Data Warehouse se crea aparte en SIPA_DW (09_dw_crear.sql).

   Ejecutar completo (F5 en SSMS o: sqlcmd -S localhost -E -i 01_crear_bd.sql)
   ADVERTENCIA: borra y vuelve a crear la base SIPA si ya existe.
   ===================================================================== */

USE master;
GO
IF DB_ID('SIPA') IS NOT NULL
BEGIN
    ALTER DATABASE SIPA SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
    DROP DATABASE SIPA;
END
GO
CREATE DATABASE SIPA;
GO
USE SIPA;
SET QUOTED_IDENTIFIER ON;
SET ANSI_NULLS ON;
GO
CREATE SCHEMA priv;
GO

/* ---------------------------------------------------------------------
   1. TERRITORIO Y UBICACIÓN
   --------------------------------------------------------------------- */

-- Municipio o alcaldía. Permite adaptar SIPA a cada lugar (pesos propios).
CREATE TABLE territorio (
    id_territorio   INT IDENTITY(1,1) CONSTRAINT pk_territorio PRIMARY KEY,
    nombre          VARCHAR(60)  NOT NULL,
    tipo            VARCHAR(10)  NOT NULL
                    CONSTRAINT ck_territorio_tipo CHECK (tipo IN ('ALCALDIA','MUNICIPIO')),
    entidad         VARCHAR(40)  NOT NULL,
    CONSTRAINT uq_territorio UNIQUE (nombre, entidad)
);

-- Colonia dentro de un territorio, con su vulnerabilidad.
CREATE TABLE colonia (
    id_colonia          INT IDENTITY(1,1) CONSTRAINT pk_colonia PRIMARY KEY,
    id_territorio       INT          NOT NULL
                        CONSTRAINT fk_colonia_territorio REFERENCES territorio(id_territorio),
    nombre              VARCHAR(80)  NOT NULL,
    clave_oficial       VARCHAR(10)  NULL,      -- p. ej. UT del Bando municipal de Chalco
    tipo_asentamiento   VARCHAR(30)  NULL,      -- colonia, pueblo, barrio, conjunto urbano...
    indice_marginacion  DECIMAL(6,3) NULL,      -- CONAPO (por cargar)
    poblacion           INT          NULL CONSTRAINT ck_colonia_poblacion CHECK (poblacion >= 0),
    CONSTRAINT uq_colonia UNIQUE (id_territorio, nombre)
);

-- Celda de la cuadrícula espacial (unidad de análisis del motor predictivo).
CREATE TABLE celda (
    celda_id    VARCHAR(12)  CONSTRAINT pk_celda PRIMARY KEY,   -- p. ej. F213_C132
    latitud     DECIMAL(9,6) NOT NULL CONSTRAINT ck_celda_lat CHECK (latitud  BETWEEN 14 AND 33),
    longitud    DECIMAL(9,6) NOT NULL CONSTRAINT ck_celda_lon CHECK (longitud BETWEEN -118 AND -86)
);

CREATE TABLE tipo_vialidad (
    id_tipo_vialidad    TINYINT IDENTITY(1,1) CONSTRAINT pk_tipo_vialidad PRIMARY KEY,
    nombre              VARCHAR(30) NOT NULL CONSTRAINT uq_tipo_vialidad UNIQUE,
    velocidad_kmh       SMALLINT    NOT NULL CONSTRAINT ck_tipo_vialidad_vel CHECK (velocidad_kmh > 0),
    aforo_referencia    INT         NOT NULL CONSTRAINT ck_tipo_vialidad_aforo CHECK (aforo_referencia >= 0)
);

-- Tramo de vialidad: la unidad que se prioriza.
CREATE TABLE tramo (
    id_tramo            INT IDENTITY(1,1) CONSTRAINT pk_tramo PRIMARY KEY,
    nombre_vialidad     VARCHAR(100) NOT NULL,
    id_tipo_vialidad    TINYINT      NOT NULL
                        CONSTRAINT fk_tramo_tipo REFERENCES tipo_vialidad(id_tipo_vialidad),
    id_colonia          INT          NOT NULL
                        CONSTRAINT fk_tramo_colonia REFERENCES colonia(id_colonia),
    celda_id            VARCHAR(12)  NULL
                        CONSTRAINT fk_tramo_celda REFERENCES celda(celda_id),
    longitud_m          DECIMAL(8,1) NOT NULL CONSTRAINT ck_tramo_longitud CHECK (longitud_m > 0)
);

/* ---------------------------------------------------------------------
   2. CATÁLOGOS
   --------------------------------------------------------------------- */

CREATE TABLE cat_estatus_reporte (
    estatus_original    VARCHAR(15) CONSTRAINT pk_cat_estatus_reporte PRIMARY KEY,
    estatus_agrupado    VARCHAR(15) NOT NULL
                        CONSTRAINT ck_estatus_agrupado CHECK (estatus_agrupado IN ('RESUELTO','TURNADO','PENDIENTE')),
    descripcion         VARCHAR(100) NOT NULL
);

CREATE TABLE cat_fuente_reporte (
    id_fuente   TINYINT IDENTITY(1,1) CONSTRAINT pk_cat_fuente PRIMARY KEY,
    nombre      VARCHAR(30) NOT NULL CONSTRAINT uq_cat_fuente UNIQUE
);

CREATE TABLE cat_estado_bache (
    id_estado_bache TINYINT     CONSTRAINT pk_cat_estado_bache PRIMARY KEY,
    nombre          VARCHAR(20) NOT NULL CONSTRAINT uq_cat_estado_bache UNIQUE
);

/* ---------------------------------------------------------------------
   3. BACHES Y REPORTES
   --------------------------------------------------------------------- */

-- Daño físico identificado. Varios reportes pueden referirse al mismo bache.
CREATE TABLE bache (
    id_bache            INT IDENTITY(1,1) CONSTRAINT pk_bache PRIMARY KEY,
    id_tramo            INT          NULL CONSTRAINT fk_bache_tramo REFERENCES tramo(id_tramo),
    celda_id            VARCHAR(12)  NOT NULL CONSTRAINT fk_bache_celda REFERENCES celda(celda_id),
    latitud             DECIMAL(9,6) NOT NULL,
    longitud            DECIMAL(9,6) NOT NULL,
    severidad           TINYINT      NULL CONSTRAINT ck_bache_severidad CHECK (severidad BETWEEN 1 AND 5),
    profundidad_cm      DECIMAL(5,1) NULL CONSTRAINT ck_bache_profundidad CHECK (profundidad_cm > 0),
    area_m2             DECIMAL(6,2) NULL CONSTRAINT ck_bache_area CHECK (area_m2 > 0),
    id_estado_bache     TINYINT      NOT NULL CONSTRAINT df_bache_estado DEFAULT 1
                        CONSTRAINT fk_bache_estado REFERENCES cat_estado_bache(id_estado_bache),
    fecha_deteccion     DATE         NOT NULL
);

-- Aviso ciudadano, de inspección o histórico (base maestra CDMX).
-- anio, mes y alcaldía NO se guardan: se derivan de fecha_solicitud y de la colonia (3FN).
CREATE TABLE reporte (
    id_reporte          INT IDENTITY(1,1) CONSTRAINT pk_reporte PRIMARY KEY,
    folio_origen        INT          NULL,      -- id_folio de la base maestra
    id_fuente           TINYINT      NOT NULL CONSTRAINT fk_reporte_fuente REFERENCES cat_fuente_reporte(id_fuente),
    id_bache            INT          NULL CONSTRAINT fk_reporte_bache REFERENCES bache(id_bache),
    id_colonia          INT          NULL CONSTRAINT fk_reporte_colonia REFERENCES colonia(id_colonia),
    celda_id            VARCHAR(12)  NULL CONSTRAINT fk_reporte_celda REFERENCES celda(celda_id),
    fecha_solicitud     DATE         NOT NULL,
    estatus_original    VARCHAR(15)  NOT NULL CONSTRAINT fk_reporte_estatus REFERENCES cat_estatus_reporte(estatus_original),
    latitud             DECIMAL(9,6) NULL,
    longitud            DECIMAL(9,6) NULL,
    descripcion         VARCHAR(300) NULL,
    -- columnas de control heredadas de la limpieza
    conjunto            VARCHAR(13)  NULL CONSTRAINT ck_reporte_conjunto CHECK (conjunto IN ('ENTRENAMIENTO','PRUEBA')),
    temporada_lluvias   BIT          NOT NULL CONSTRAINT df_reporte_lluvias DEFAULT 0,
    periodo_atipico     BIT          NOT NULL CONSTRAINT df_reporte_atipico DEFAULT 0,
    alcaldia_inferida   BIT          NOT NULL CONSTRAINT df_reporte_alc_inf DEFAULT 0,
    colonia_inferida    BIT          NOT NULL CONSTRAINT df_reporte_col_inf DEFAULT 0,
    ubicacion_dudosa    BIT          NOT NULL CONSTRAINT df_reporte_dudosa DEFAULT 0,
    posible_duplicado   BIT          NOT NULL CONSTRAINT df_reporte_dup DEFAULT 0,
    grupo_ubicacion     INT          NULL,
    fecha_registro      DATETIME2(0) NOT NULL CONSTRAINT df_reporte_registro DEFAULT SYSDATETIME(),
    CONSTRAINT ck_reporte_coords CHECK (
        (latitud IS NULL AND longitud IS NULL)
        OR (latitud BETWEEN 14 AND 33 AND longitud BETWEEN -118 AND -86))
);
-- UNIQUE filtrado: el folio se repite solo si es NULL (reportes nuevos sin folio externo)
CREATE UNIQUE INDEX uq_reporte_folio ON reporte(id_fuente, folio_origen) WHERE folio_origen IS NOT NULL;
CREATE INDEX ix_reporte_fecha   ON reporte(fecha_solicitud);
CREATE INDEX ix_reporte_celda   ON reporte(celda_id);
CREATE INDEX ix_reporte_colonia ON reporte(id_colonia);

-- Datos personales separados, opcionales y con consentimiento (LGPDPPSO).
CREATE TABLE priv.contacto_ciudadano (
    id_contacto         INT IDENTITY(1,1) CONSTRAINT pk_contacto PRIMARY KEY,
    id_reporte          INT          NOT NULL CONSTRAINT uq_contacto_reporte UNIQUE
                        CONSTRAINT fk_contacto_reporte REFERENCES dbo.reporte(id_reporte),
    medio               VARCHAR(10)  NOT NULL CONSTRAINT ck_contacto_medio CHECK (medio IN ('CORREO','TELEFONO')),
    dato_contacto       VARCHAR(100) NOT NULL,
    consentimiento      BIT          NOT NULL CONSTRAINT ck_contacto_consent CHECK (consentimiento = 1),
    fecha_consentimiento DATETIME2(0) NOT NULL CONSTRAINT df_contacto_fecha DEFAULT SYSDATETIME()
);

/* ---------------------------------------------------------------------
   4. CONTEXTO: TRÁNSITO, TRANSPORTE Y SINIESTRALIDAD
   --------------------------------------------------------------------- */

CREATE TABLE aforo (
    id_aforo            INT IDENTITY(1,1) CONSTRAINT pk_aforo PRIMARY KEY,
    id_tramo            INT          NOT NULL CONSTRAINT fk_aforo_tramo REFERENCES tramo(id_tramo),
    fecha_medicion      DATE         NOT NULL,
    vehiculos_dia       INT          NOT NULL CONSTRAINT ck_aforo_veh CHECK (vehiculos_dia >= 0),
    pct_carga_pesada    DECIMAL(5,2) NOT NULL CONSTRAINT ck_aforo_pct CHECK (pct_carga_pesada BETWEEN 0 AND 100),
    CONSTRAINT uq_aforo UNIQUE (id_tramo, fecha_medicion)
);

CREATE TABLE ruta_transporte (
    id_ruta         INT IDENTITY(1,1) CONSTRAINT pk_ruta PRIMARY KEY,
    nombre          VARCHAR(80) NOT NULL,
    tipo            VARCHAR(20) NOT NULL
                    CONSTRAINT ck_ruta_tipo CHECK (tipo IN ('METROBUS','TROLEBUS','RTP','CONCESIONADO','OTRO')),
    pasajeros_dia   INT         NULL CONSTRAINT ck_ruta_pasajeros CHECK (pasajeros_dia >= 0)
);

-- Relación N:M: una ruta recorre muchos tramos y un tramo lo usan muchas rutas.
CREATE TABLE ruta_tramo (
    id_ruta     INT NOT NULL CONSTRAINT fk_ruta_tramo_ruta  REFERENCES ruta_transporte(id_ruta),
    id_tramo    INT NOT NULL CONSTRAINT fk_ruta_tramo_tramo REFERENCES tramo(id_tramo),
    CONSTRAINT pk_ruta_tramo PRIMARY KEY (id_ruta, id_tramo)
);

CREATE TABLE accidente (
    id_accidente    INT IDENTITY(1,1) CONSTRAINT pk_accidente PRIMARY KEY,
    id_tramo        INT          NULL CONSTRAINT fk_accidente_tramo REFERENCES tramo(id_tramo),
    celda_id        VARCHAR(12)  NULL CONSTRAINT fk_accidente_celda REFERENCES celda(celda_id),
    fecha           DATE         NOT NULL,
    tipo            VARCHAR(30)  NOT NULL,
    gravedad        VARCHAR(10)  NOT NULL
                    CONSTRAINT ck_accidente_gravedad CHECK (gravedad IN ('DANOS','HERIDOS','FATAL')),
    CONSTRAINT ck_accidente_ubicacion CHECK (id_tramo IS NOT NULL OR celda_id IS NOT NULL)
);

-- Zonas de inundación del Atlas de Riesgo (polígonos geográficos).
CREATE TABLE zona_inundable (
    id_zona         INT IDENTITY(1,1) CONSTRAINT pk_zona_inundable PRIMARY KEY,
    id_territorio   INT          NOT NULL CONSTRAINT fk_zona_territorio REFERENCES territorio(id_territorio),
    clave           VARCHAR(20)  NOT NULL,
    poligono        GEOGRAPHY    NOT NULL,
    fuente          VARCHAR(40)  NOT NULL,
    CONSTRAINT uq_zona_inundable UNIQUE (id_territorio, clave)
);

-- Equipamiento urbano que eleva la prioridad de los baches cercanos.
CREATE TABLE equipamiento (
    id_equipamiento INT IDENTITY(1,1) CONSTRAINT pk_equipamiento PRIMARY KEY,
    id_territorio   INT          NOT NULL CONSTRAINT fk_equip_territorio REFERENCES territorio(id_territorio),
    tipo            VARCHAR(10)  NOT NULL
                    CONSTRAINT ck_equip_tipo CHECK (tipo IN ('ESCUELA','HOSPITAL','MERCADO')),
    nombre          VARCHAR(150) NOT NULL,
    latitud         DECIMAL(9,6) NOT NULL,
    longitud        DECIMAL(9,6) NOT NULL,
    personas        INT          NULL CONSTRAINT ck_equip_personas CHECK (personas >= 0),  -- p. ej. alumnos
    fuente          VARCHAR(40)  NOT NULL,
    ubicacion       AS GEOGRAPHY::Point(latitud, longitud, 4326)
);

/* ---------------------------------------------------------------------
   5. PRIORIZACIÓN (IPU) Y SUPERVISIÓN HUMANA
   --------------------------------------------------------------------- */

CREATE TABLE criterio_ipu (
    id_criterio     TINYINT IDENTITY(1,1) CONSTRAINT pk_criterio PRIMARY KEY,
    clave           VARCHAR(20)  NOT NULL CONSTRAINT uq_criterio UNIQUE,
    nombre          VARCHAR(60)  NOT NULL,
    descripcion     VARCHAR(200) NOT NULL
);

-- Pesos configurables por territorio y con vigencia (no fijos en el código).
CREATE TABLE peso_criterio (
    id_territorio   INT          NOT NULL CONSTRAINT fk_peso_territorio REFERENCES territorio(id_territorio),
    id_criterio     TINYINT      NOT NULL CONSTRAINT fk_peso_criterio REFERENCES criterio_ipu(id_criterio),
    vigente_desde   DATE         NOT NULL,
    vigente_hasta   DATE         NULL,
    peso            DECIMAL(4,3) NOT NULL CONSTRAINT ck_peso_rango CHECK (peso BETWEEN 0 AND 1),
    CONSTRAINT pk_peso_criterio PRIMARY KEY (id_territorio, id_criterio, vigente_desde),
    CONSTRAINT ck_peso_vigencia CHECK (vigente_hasta IS NULL OR vigente_hasta > vigente_desde)
);

-- Tarifas de reparación para estimar el costo. Se cargan desde un archivo
-- JSON (datos/costos/tarifas_reparacion.json) que la autoridad puede
-- actualizar sin tocar la base. costo = costo_fijo + costo_m2 × MAX(área, área mínima)
CREATE TABLE tarifa_reparacion (
    clave           VARCHAR(20)   CONSTRAINT pk_tarifa PRIMARY KEY,
    nombre          VARCHAR(80)   NOT NULL,
    costo_m2        DECIMAL(10,2) NOT NULL CONSTRAINT ck_tarifa_m2    CHECK (costo_m2 > 0),
    costo_fijo      DECIMAL(10,2) NOT NULL CONSTRAINT ck_tarifa_fijo  CHECK (costo_fijo >= 0),
    area_minima_m2  DECIMAL(8,2)  NOT NULL CONSTRAINT ck_tarifa_area  CHECK (area_minima_m2 > 0),
    version         VARCHAR(10)   NOT NULL,
    fuente          VARCHAR(200)  NOT NULL
);

-- Cada cálculo del IPU se conserva para auditoría.
CREATE TABLE calculo_prioridad (
    id_calculo      INT IDENTITY(1,1) CONSTRAINT pk_calculo PRIMARY KEY,
    id_bache        INT           NOT NULL CONSTRAINT fk_calculo_bache REFERENCES bache(id_bache),
    fecha_calculo   DATETIME2(0)  NOT NULL CONSTRAINT df_calculo_fecha DEFAULT SYSDATETIME(),
    ipu             DECIMAL(5,4)  NOT NULL CONSTRAINT ck_calculo_ipu CHECK (ipu BETWEEN 0 AND 1),
    semaforo        VARCHAR(8)    NOT NULL CONSTRAINT ck_calculo_semaforo CHECK (semaforo IN ('ROJO','AMARILLO','VERDE')),
    clave_tarifa    VARCHAR(20)   NULL CONSTRAINT fk_calculo_tarifa REFERENCES tarifa_reparacion(clave),
    costo_estimado  DECIMAL(12,2) NULL CONSTRAINT ck_calculo_costo CHECK (costo_estimado >= 0),
    version_modelo  VARCHAR(20)   NOT NULL
);

-- Desglose del IPU por criterio: base de la ficha de justificación.
CREATE TABLE detalle_calculo (
    id_calculo          INT          NOT NULL CONSTRAINT fk_detalle_calculo REFERENCES calculo_prioridad(id_calculo),
    id_criterio         TINYINT      NOT NULL CONSTRAINT fk_detalle_criterio REFERENCES criterio_ipu(id_criterio),
    valor_normalizado   DECIMAL(5,4) NOT NULL CONSTRAINT ck_detalle_valor CHECK (valor_normalizado BETWEEN 0 AND 1),
    peso_aplicado       DECIMAL(4,3) NOT NULL CONSTRAINT ck_detalle_peso CHECK (peso_aplicado BETWEEN 0 AND 1),
    CONSTRAINT pk_detalle_calculo PRIMARY KEY (id_calculo, id_criterio)
);

-- Usuarios con cuenta. El ciudadano NO necesita cuenta: reporta y consulta
-- por folio (rol de base de datos rol_ciudadano, ver 05). La AUTORIDAD
-- decide sobre la recomendación y reporta el estado de cada bache.
CREATE TABLE usuario (
    id_usuario      INT IDENTITY(1,1) CONSTRAINT pk_usuario PRIMARY KEY,
    nombre          VARCHAR(80) NOT NULL,
    rol             VARCHAR(10) NOT NULL
                    CONSTRAINT ck_usuario_rol CHECK (rol IN ('AUTORIDAD','ANALISTA','ADMIN')),
    id_territorio   INT         NULL CONSTRAINT fk_usuario_territorio REFERENCES territorio(id_territorio),
    activo          BIT         NOT NULL CONSTRAINT df_usuario_activo DEFAULT 1,
    CONSTRAINT ck_usuario_autoridad CHECK (rol <> 'AUTORIDAD' OR id_territorio IS NOT NULL)
);

-- "SIPA recomienda, la autoridad decide": toda decisión queda registrada.
CREATE TABLE decision_humana (
    id_decision         INT IDENTITY(1,1) CONSTRAINT pk_decision PRIMARY KEY,
    id_calculo          INT           NOT NULL CONSTRAINT fk_decision_calculo REFERENCES calculo_prioridad(id_calculo),
    id_usuario          INT           NOT NULL CONSTRAINT fk_decision_usuario REFERENCES usuario(id_usuario),
    decision            VARCHAR(10)   NOT NULL
                        CONSTRAINT ck_decision_tipo CHECK (decision IN ('APROBAR','AJUSTAR','RECHAZAR')),
    semaforo_ajustado   VARCHAR(8)    NULL
                        CONSTRAINT ck_decision_semaforo CHECK (semaforo_ajustado IN ('ROJO','AMARILLO','VERDE')),
    justificacion       VARCHAR(500)  NULL,
    fecha               DATETIME2(0)  NOT NULL CONSTRAINT df_decision_fecha DEFAULT SYSDATETIME(),
    -- si se ajusta o rechaza, el motivo es obligatorio (IS NOT NULL: un CHECK
    -- con resultado desconocido, por NULL, se considera cumplido)
    CONSTRAINT ck_decision_justificacion CHECK (
        decision = 'APROBAR' OR (justificacion IS NOT NULL AND LEN(LTRIM(RTRIM(justificacion))) >= 20)),
    CONSTRAINT ck_decision_ajuste CHECK (
        (decision = 'AJUSTAR' AND semaforo_ajustado IS NOT NULL)
        OR (decision <> 'AJUSTAR' AND semaforo_ajustado IS NULL))
);

/* ---------------------------------------------------------------------
   6. SEGUIMIENTO QUE REPORTA LA AUTORIDAD
   SIPA no programa brigadas ni maneja material o presupuesto: la autoridad
   repara y solo informa el avance. Cada cambio de estado del bache queda en
   esta bitácora, que nunca se sobrescribe.
   --------------------------------------------------------------------- */

CREATE TABLE seguimiento_bache (
    id_seguimiento      INT IDENTITY(1,1) CONSTRAINT pk_seguimiento PRIMARY KEY,
    id_bache            INT           NOT NULL CONSTRAINT fk_seguimiento_bache REFERENCES bache(id_bache),
    id_estado_anterior  TINYINT       NOT NULL CONSTRAINT fk_seguimiento_ant REFERENCES cat_estado_bache(id_estado_bache),
    id_estado_nuevo     TINYINT       NOT NULL CONSTRAINT fk_seguimiento_nvo REFERENCES cat_estado_bache(id_estado_bache),
    id_usuario          INT           NOT NULL CONSTRAINT fk_seguimiento_usuario REFERENCES usuario(id_usuario),
    fecha               DATETIME2(0)  NOT NULL CONSTRAINT df_seguimiento_fecha DEFAULT SYSDATETIME(),
    comentario          VARCHAR(300)  NULL,
    costo_reportado     DECIMAL(12,2) NULL CONSTRAINT ck_seguimiento_costo CHECK (costo_reportado >= 0),
    CONSTRAINT ck_seguimiento_cambio  CHECK (id_estado_nuevo <> id_estado_anterior),
    -- descartar un bache exige explicar por qué
    CONSTRAINT ck_seguimiento_descarte CHECK (id_estado_nuevo <> 6 OR (comentario IS NOT NULL AND LEN(LTRIM(RTRIM(comentario))) >= 15)),
    -- el costo real solo lo informa la autoridad al marcar REPARADO
    CONSTRAINT ck_seguimiento_costo_rep CHECK (costo_reportado IS NULL OR id_estado_nuevo = 5)
);
CREATE INDEX ix_seguimiento_bache ON seguimiento_bache(id_bache, fecha);

-- Aviso al ciudadano por folio cuando su bache se repara o se descarta
-- (no requiere datos personales).
CREATE TABLE notificacion (
    id_notificacion INT IDENTITY(1,1) CONSTRAINT pk_notificacion PRIMARY KEY,
    id_reporte      INT          NOT NULL CONSTRAINT fk_notificacion_reporte REFERENCES reporte(id_reporte),
    id_seguimiento  INT          NOT NULL CONSTRAINT fk_notificacion_seguimiento REFERENCES seguimiento_bache(id_seguimiento),
    fecha           DATETIME2(0) NOT NULL CONSTRAINT df_notificacion_fecha DEFAULT SYSDATETIME(),
    medio           VARCHAR(10)  NOT NULL CONSTRAINT ck_notificacion_medio CHECK (medio IN ('FOLIO','CORREO','SMS'))
);
GO

DECLARE @n INT = (SELECT COUNT(*) FROM sys.tables);
PRINT 'Base SIPA creada: ' + CAST(@n AS VARCHAR) + ' tablas.';
