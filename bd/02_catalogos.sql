/* =====================================================================
   SIPA · 02_catalogos.sql
   Catálogos y parámetros iniciales. Los valores numéricos (pesos, costos)
   son ILUSTRATIVOS y se ajustarán durante el desarrollo.
   Las tarifas de reparación se leen del archivo JSON
   datos/costos/tarifas_reparacion.json.
   ANTES DE EJECUTAR: ajusta @json a la ruta del proyecto.
   ===================================================================== */
USE SIPA;
SET QUOTED_IDENTIFIER ON;
SET ANSI_NULLS ON;
GO

INSERT INTO cat_estatus_reporte (estatus_original, estatus_agrupado, descripcion) VALUES
 ('ATENDIDO', 'RESUELTO',  'Solicitud atendida (nombre usado en 2019-2021)'),
 ('CERRADO',  'RESUELTO',  'Solicitud cerrada (nombre usado en 2022)'),
 ('TURNADO',  'TURNADO',   'Enviada a otra área o dependencia'),
 ('RECIBIDO', 'PENDIENTE', 'Recibida sin atención registrada'),
 -- estatus de los datos abiertos de Chalco
 ('FINALIZADO', 'RESUELTO',  'Reporte finalizado (Chalco)'),
 ('NUEVO',      'PENDIENTE', 'Reporte nuevo sin atender (Chalco)'),
 ('EN PROCESO', 'PENDIENTE', 'Reporte en atención (Chalco)');

INSERT INTO cat_fuente_reporte (nombre) VALUES
 ('BASE_MAESTRA_CDMX'), ('CIUDADANO'), ('INSPECCION'), ('CHALCO_DATOS_ABIERTOS');

INSERT INTO cat_estado_bache (id_estado_bache, nombre) VALUES
 (1,'REPORTADO'), (2,'VALIDADO'), (3,'PRIORIZADO'), (4,'EN_ATENCION'), (5,'REPARADO'), (6,'DESCARTADO');

INSERT INTO tipo_vialidad (nombre, velocidad_kmh, aforo_referencia) VALUES
 ('PRIMARIA', 60, 40000), ('SECUNDARIA', 40, 12000), ('LOCAL', 30, 2500);

-- Criterios del Índice de Prioridad Urbana (sección 5.5 de la propuesta)
INSERT INTO criterio_ipu (clave, nombre, descripcion) VALUES
 ('DETERIORO',     'Nivel de deterioro actual',          'Profundidad, área y severidad del bache'),
 ('RIESGO_72H',    'Riesgo de accidente a 72 h',         'Motor predictivo de siniestralidad'),
 ('PERSONAS',      'Personas afectadas',                 'Aforo × ocupación + pasajeros de transporte público'),
 ('TRANSPORTE',    'Relevancia para transporte público', 'Número e importancia de rutas en el tramo'),
 ('TRANSITO',      'Intensidad del tránsito',            'Aforo vehicular y porcentaje de carga pesada'),
 ('VULNERABILIDAD','Vulnerabilidad territorial',         'Índice de marginación de la zona'),
 ('DETERIORO_MAYOR','Riesgo de deterioro mayor',         'Probabilidad de baches nuevos y degradación'),
 ('REPORTES',      'Reportes ciudadanos (acotado)',      'Escala logarítmica con tope para evitar sesgo digital'),
 -- agregados a partir de la propuesta del docente de Pensamiento Complejo
 ('INUNDACION',    'Inundación y drenaje',               'Bache dentro o cerca de una zona inundable del Atlas de Riesgo'),
 ('ACCESO_SERVICIOS','Acceso a servicios',               'Escuelas, hospitales y mercados a menos de 500 m');

-- Usuarios de prueba. Las autoridades se crean junto con su territorio (03 y 06).
INSERT INTO usuario (nombre, rol) VALUES
 ('Analista SIPA de prueba', 'ANALISTA');

-- Tarifas de reparación desde el archivo JSON
DECLARE @json NVARCHAR(400) =
    N'C:\Users\gerry\Documents\Rebeca_unrc\sistema_bacheo_3er_semestre\datos\costos\tarifas_reparacion.json';
-- BULK INSERT lee el archivo completo como un solo renglón (los separadores
-- 0x00 y 0x01 no aparecen en el JSON). OPENROWSET(BULK) usaría la cuenta del
-- servicio de SQL Server, que no tiene acceso a la carpeta del proyecto.
DROP TABLE IF EXISTS #json;
CREATE TABLE #json (texto NVARCHAR(MAX));
DECLARE @texto NVARCHAR(MAX), @sql NVARCHAR(MAX) =
    N'BULK INSERT #json FROM ''' + @json + N''' WITH (CODEPAGE = ''65001'', ROWTERMINATOR = ''0x00'', FIELDTERMINATOR = ''0x01'');';
EXEC sp_executesql @sql;
SELECT @texto = texto FROM #json;
IF ISJSON(@texto) = 0 THROW 50010, 'El archivo de tarifas no es un JSON válido.', 1;

INSERT INTO tarifa_reparacion (clave, nombre, costo_m2, costo_fijo, area_minima_m2, version, fuente)
SELECT t.clave, t.nombre, t.costo_m2, t.costo_fijo, t.area_minima_m2,
       JSON_VALUE(@texto, '$.version'), JSON_VALUE(@texto, '$.fuente')
FROM OPENJSON(@texto, '$.tarifas')
     WITH (clave VARCHAR(20), nombre NVARCHAR(80), costo_m2 DECIMAL(10,2),
           costo_fijo DECIMAL(10,2), area_minima_m2 DECIMAL(8,2)) t;
PRINT 'Tarifas cargadas del JSON: ' + CAST(@@ROWCOUNT AS VARCHAR);
GO
PRINT 'Catálogos cargados.';
