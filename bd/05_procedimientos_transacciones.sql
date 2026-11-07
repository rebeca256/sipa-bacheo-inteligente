/* =====================================================================
   SIPA · 05_procedimientos_transacciones.sql
   Procedimientos almacenados del flujo de SIPA. Cada uno que modifica
   datos es una transacción: si cualquier paso falla, se revierte todo.

     Modo ciudadano
       sp_registrar_reporte        reporte nuevo + deduplicación por celda
       sp_consultar_folio          estado del reporte y su historial
     Asesoría (SIPA)
       sp_calcular_ipu             IPU, semáforo, intervención y costo estimado
     Modo autoridad
       sp_registrar_decision       aprueba, ajusta o rechaza la recomendación
       sp_actualizar_estado_bache  informa el avance; al reparar o descartar,
                                   notifica a todos los reportes del bache
   Al final se crean los roles rol_ciudadano y rol_autoridad.
   ===================================================================== */
USE SIPA;
SET QUOTED_IDENTIFIER ON;
SET ANSI_NULLS ON;
GO

/* ---------------------------------------------------------------------
   Registra un reporte. Si ya hay un bache abierto en la misma celda,
   el reporte se liga a él en lugar de crear uno nuevo (duplicado).
   --------------------------------------------------------------------- */
CREATE OR ALTER PROCEDURE sp_registrar_reporte
    @id_fuente   TINYINT,
    @id_colonia  INT,
    @latitud     DECIMAL(9,6),
    @longitud    DECIMAL(9,6),
    @descripcion VARCHAR(300) = NULL,
    @id_reporte  INT OUTPUT,
    @id_bache    INT OUTPUT
AS
BEGIN
    SET NOCOUNT ON; SET XACT_ABORT ON;

    -- Celda más cercana (cuadrícula de 250 m)
    DECLARE @celda VARCHAR(12) = (
        SELECT TOP 1 celda_id FROM celda
        ORDER BY SQUARE(latitud - @latitud) + SQUARE(longitud - @longitud));

    BEGIN TRANSACTION;

        SELECT TOP 1 @id_bache = id_bache
        FROM bache WITH (UPDLOCK, HOLDLOCK)
        WHERE celda_id = @celda AND id_estado_bache IN (1,2,3,4)
        ORDER BY fecha_deteccion;

        IF @id_bache IS NULL
        BEGIN
            INSERT INTO bache (celda_id, latitud, longitud, id_estado_bache, fecha_deteccion)
            VALUES (@celda, @latitud, @longitud, 1, CAST(GETDATE() AS DATE));
            SET @id_bache = SCOPE_IDENTITY();
        END

        INSERT INTO reporte (id_fuente, id_bache, id_colonia, celda_id, fecha_solicitud,
                             estatus_original, latitud, longitud, descripcion)
        VALUES (@id_fuente, @id_bache, @id_colonia, @celda, CAST(GETDATE() AS DATE),
                'RECIBIDO', @latitud, @longitud, @descripcion);
        SET @id_reporte = SCOPE_IDENTITY();

    COMMIT TRANSACTION;
END
GO

/* ---------------------------------------------------------------------
   Calcula el IPU de un bache con los pesos vigentes de su territorio.
   Criterios con datos disponibles hoy:
     DETERIORO        severidad / 5
     REPORTES         log(1 + n) / log(1 + 20), con tope en 1
     DETERIORO_MAYOR  reportes históricos de la celda / máximo de las celdas
                      del mismo territorio
     INUNDACION       1 si el bache está dentro de una zona inundable,
                      0.5 si está a menos de 200 m, 0 si está más lejos
     ACCESO_SERVICIOS (3·hospitales + 2·mercados + escuelas) a menos de
                      500 m, entre 10, con tope en 1
   Si un territorio no tiene cargada la fuente de un criterio (por ejemplo,
   la CDMX no tiene zonas inundables), ese criterio usa 0.5 = valor neutro.
   Aforo y personas afectadas siguen en 0.5 en todos lados.
   --------------------------------------------------------------------- */
CREATE OR ALTER PROCEDURE sp_calcular_ipu
    @id_bache   INT,
    @id_calculo INT OUTPUT
AS
BEGIN
    SET NOCOUNT ON; SET XACT_ABORT ON;

    DECLARE @celda VARCHAR(12), @severidad TINYINT, @territorio INT,
            @n_reportes INT, @hist INT, @max_hist INT,
            @punto GEOGRAPHY, @inundacion DECIMAL(5,4), @servicios DECIMAL(5,4),
            @riesgo72 DECIMAL(5,4), @transporte DECIMAL(5,4), @vulnerabilidad DECIMAL(5,4);

    SELECT @celda = celda_id, @severidad = ISNULL(severidad, 3),
           @punto = GEOGRAPHY::Point(latitud, longitud, 4326)
    FROM bache WHERE id_bache = @id_bache;
    IF @celda IS NULL THROW 50001, 'El bache no existe.', 1;

    -- territorio: el de la colonia más frecuente entre sus reportes
    SELECT TOP 1 @territorio = c.id_territorio
    FROM reporte r JOIN colonia c ON c.id_colonia = r.id_colonia
    WHERE r.celda_id = @celda
    GROUP BY c.id_territorio ORDER BY COUNT(*) DESC;

    SELECT @n_reportes = COUNT(*) FROM reporte WHERE id_bache = @id_bache;
    SELECT @hist = COUNT(*) FROM reporte WHERE celda_id = @celda;
    SELECT @max_hist = MAX(n) FROM (
        SELECT COUNT(*) n FROM reporte r JOIN colonia c ON c.id_colonia = r.id_colonia
        WHERE c.id_territorio = @territorio GROUP BY r.celda_id) x;

    -- Inundación: distancia a la zona inundable más cercana (0 = adentro)
    IF EXISTS (SELECT 1 FROM zona_inundable WHERE id_territorio = @territorio)
        SELECT @inundacion = CASE WHEN MIN(poligono.STDistance(@punto)) = 0   THEN 1.0
                                  WHEN MIN(poligono.STDistance(@punto)) <= 200 THEN 0.5
                                  ELSE 0 END
        FROM zona_inundable WHERE id_territorio = @territorio;
    ELSE SET @inundacion = 0.5;

    -- Servicios: equipamiento a menos de 500 m, ponderado por tipo
    IF EXISTS (SELECT 1 FROM equipamiento WHERE id_territorio = @territorio)
        SELECT @servicios = IIF(SUM(x.puntos) / 10.0 > 1, 1, ISNULL(SUM(x.puntos), 0) / 10.0)
        FROM (SELECT CASE tipo WHEN 'HOSPITAL' THEN 3 WHEN 'MERCADO' THEN 2 ELSE 1 END AS puntos
              FROM equipamiento
              WHERE id_territorio = @territorio AND ubicacion.STDistance(@punto) <= 500) x;
    ELSE SET @servicios = 0.5;

    -- Riesgo de accidente a 72 h del modelo de Probabilidad (05b); sin dato, 0.5 neutro
    SET @riesgo72 = 0.5;
    IF OBJECT_ID('riesgo_celda_72h') IS NOT NULL
        SELECT @riesgo72 = v_riesgo_72h FROM riesgo_celda_72h WHERE celda_id = @celda;

    -- Transporte público (GTFS) y marginación (CONAPO) por celda (05c); sin dato, 0.5 neutro
    SELECT @transporte = 0.5, @vulnerabilidad = 0.5;
    IF OBJECT_ID('contexto_celda') IS NOT NULL
        SELECT @transporte = v_transporte, @vulnerabilidad = ISNULL(v_vulnerabilidad, 0.5)
        FROM contexto_celda WHERE celda_id = @celda;

    DECLARE @valores TABLE (clave VARCHAR(20), valor DECIMAL(5,4));
    INSERT INTO @valores VALUES
        ('DETERIORO',       @severidad / 5.0),
        ('REPORTES',        IIF(LOG(1.0 + @n_reportes) / LOG(21.0) > 1, 1, LOG(1.0 + @n_reportes) / LOG(21.0))),
        ('DETERIORO_MAYOR', 1.0 * @hist / NULLIF(@max_hist, 0)),
        ('RIESGO_72H', @riesgo72), ('PERSONAS', 0.5), ('TRANSPORTE', @transporte),
        ('TRANSITO', 0.5), ('VULNERABILIDAD', @vulnerabilidad),
        ('INUNDACION',       @inundacion),
        ('ACCESO_SERVICIOS', @servicios);

    DECLARE @ipu DECIMAL(5,4) = (
        SELECT SUM(v.valor * p.peso)
        FROM @valores v
        JOIN criterio_ipu c   ON c.clave = v.clave
        JOIN peso_criterio p  ON p.id_criterio = c.id_criterio
                             AND p.id_territorio = @territorio
                             AND p.vigente_hasta IS NULL);

    -- Intervención recomendada y costo estimado con las tarifas del JSON (02):
    --   celda con muchos reportes históricos -> REENCARPETADO (el bacheo no basta)
    --   dentro o cerca de zona inundable     -> BACHEO_CON_SELLO
    --   severidad >= 4 o profundidad >= 10   -> BACHEO_PROFUNDO
    --   resto                                -> BACHEO_SUPERFICIAL
    DECLARE @tarifa VARCHAR(20), @costo DECIMAL(12,2);
    SELECT @tarifa = CASE
               WHEN 1.0 * @hist / NULLIF(@max_hist, 0) >= 0.8 AND @hist >= 10 THEN 'REENCARPETADO'
               WHEN @inundacion >= 0.5 AND EXISTS (SELECT 1 FROM zona_inundable WHERE id_territorio = @territorio)
                                                                    THEN 'BACHEO_CON_SELLO'
               WHEN b.severidad >= 4 OR b.profundidad_cm >= 10      THEN 'BACHEO_PROFUNDO'
               ELSE 'BACHEO_SUPERFICIAL' END
    FROM bache b WHERE b.id_bache = @id_bache;

    SELECT @costo = t.costo_fijo + t.costo_m2 * IIF(ISNULL(b.area_m2, 1) > t.area_minima_m2,
                                                    ISNULL(b.area_m2, 1), t.area_minima_m2)
    FROM bache b JOIN tarifa_reparacion t ON t.clave = @tarifa
    WHERE b.id_bache = @id_bache;

    BEGIN TRANSACTION;
        INSERT INTO calculo_prioridad (id_bache, ipu, semaforo, clave_tarifa, costo_estimado, version_modelo)
        VALUES (@id_bache, @ipu,
                CASE WHEN @ipu >= 0.60 THEN 'ROJO' WHEN @ipu >= 0.45 THEN 'AMARILLO' ELSE 'VERDE' END,
                @tarifa, @costo, 'v0.4');
        SET @id_calculo = SCOPE_IDENTITY();

        INSERT INTO detalle_calculo (id_calculo, id_criterio, valor_normalizado, peso_aplicado)
        SELECT @id_calculo, c.id_criterio, v.valor, p.peso
        FROM @valores v
        JOIN criterio_ipu c  ON c.clave = v.clave
        JOIN peso_criterio p ON p.id_criterio = c.id_criterio
                            AND p.id_territorio = @territorio AND p.vigente_hasta IS NULL;

        UPDATE bache SET id_estado_bache = 3 WHERE id_bache = @id_bache AND id_estado_bache < 3;
    COMMIT TRANSACTION;
END
GO

/* ---------------------------------------------------------------------
   MODO AUTORIDAD. Decisión sobre la recomendación: APROBAR, AJUSTAR el
   semáforo o RECHAZAR. Las restricciones CHECK obligan a justificar los
   ajustes y rechazos. SIPA no crea órdenes de trabajo: la autoridad
   programa la reparación con sus propios recursos.
   --------------------------------------------------------------------- */
CREATE OR ALTER PROCEDURE sp_registrar_decision
    @id_calculo        INT,
    @id_usuario        INT,
    @decision          VARCHAR(10),
    @semaforo_ajustado VARCHAR(8)   = NULL,
    @justificacion     VARCHAR(500) = NULL,
    @id_decision       INT OUTPUT
AS
BEGIN
    SET NOCOUNT ON; SET XACT_ABORT ON;

    IF NOT EXISTS (SELECT 1 FROM usuario WHERE id_usuario = @id_usuario
                   AND rol IN ('AUTORIDAD','ADMIN') AND activo = 1)
        THROW 50002, 'Solo una autoridad activa puede decidir sobre una recomendación.', 1;

    BEGIN TRANSACTION;
        INSERT INTO decision_humana (id_calculo, id_usuario, decision, semaforo_ajustado, justificacion)
        VALUES (@id_calculo, @id_usuario, @decision, @semaforo_ajustado, @justificacion);
        SET @id_decision = SCOPE_IDENTITY();
    COMMIT TRANSACTION;
END
GO

/* ---------------------------------------------------------------------
   MODO AUTORIDAD. Informa el avance de un bache. Transiciones válidas:
     REPORTADO(1)  -> VALIDADO(2) o DESCARTADO(6)
     VALIDADO(2)   -> DESCARTADO(6)            (PRIORIZADO lo pone el IPU)
     PRIORIZADO(3) -> EN_ATENCION(4), REPARADO(5) o DESCARTADO(6)
     EN_ATENCION(4)-> REPARADO(5) o DESCARTADO(6)
   En una sola transacción: cambia el estado del bache, deja el registro
   en seguimiento_bache y, si se repara o descarta, notifica por folio a
   todos los reportes del bache. Si algo falla, no cambia nada.
   --------------------------------------------------------------------- */
CREATE OR ALTER PROCEDURE sp_actualizar_estado_bache
    @id_bache         INT,
    @id_usuario       INT,
    @nuevo            TINYINT,
    @comentario       VARCHAR(300)  = NULL,
    @costo_reportado  DECIMAL(12,2) = NULL,
    @id_seguimiento   INT = NULL OUTPUT
AS
BEGIN
    SET NOCOUNT ON; SET XACT_ABORT ON;
    DECLARE @actual TINYINT;

    IF NOT EXISTS (SELECT 1 FROM usuario WHERE id_usuario = @id_usuario
                   AND rol IN ('AUTORIDAD','ADMIN') AND activo = 1)
        THROW 50003, 'Solo una autoridad activa puede actualizar el estado de un bache.', 1;

    BEGIN TRANSACTION;
        SELECT @actual = id_estado_bache FROM bache WITH (UPDLOCK) WHERE id_bache = @id_bache;
        IF @actual IS NULL THROW 50006, 'El bache no existe.', 1;

        IF NOT EXISTS (SELECT 1 FROM (VALUES (1,2),(1,6),(2,6),(3,4),(3,5),(3,6),(4,5),(4,6)) t(de, a)
                       WHERE t.de = @actual AND t.a = @nuevo)
            THROW 50007, 'Transición de estado no permitida.', 1;

        UPDATE bache SET id_estado_bache = @nuevo WHERE id_bache = @id_bache;

        -- Las restricciones CHECK de seguimiento_bache (motivo obligatorio al
        -- descartar, costo solo al reparar) hacen fallar toda la transacción.
        INSERT INTO seguimiento_bache (id_bache, id_estado_anterior, id_estado_nuevo, id_usuario,
                                       comentario, costo_reportado)
        VALUES (@id_bache, @actual, @nuevo, @id_usuario, @comentario, @costo_reportado);
        SET @id_seguimiento = SCOPE_IDENTITY();

        IF @nuevo IN (5, 6)
            INSERT INTO notificacion (id_reporte, id_seguimiento, medio)
            SELECT id_reporte, @id_seguimiento, 'FOLIO' FROM reporte WHERE id_bache = @id_bache;
    COMMIT TRANSACTION;
END
GO

/* ---------------------------------------------------------------------
   MODO CIUDADANO. Consulta por folio: estado del bache, prioridad
   asignada e historial de avances. No expone datos personales.
   --------------------------------------------------------------------- */
CREATE OR ALTER PROCEDURE sp_consultar_folio
    @id_reporte INT
AS
BEGIN
    SET NOCOUNT ON;
    SELECT r.id_reporte AS folio, r.fecha_solicitud, e.nombre AS estado_bache,
           cp.semaforo AS prioridad_recomendada,
           COALESCE(d.semaforo_ajustado, cp.semaforo) AS prioridad_decidida
    FROM reporte r
    LEFT JOIN bache b            ON b.id_bache = r.id_bache
    LEFT JOIN cat_estado_bache e ON e.id_estado_bache = b.id_estado_bache
    OUTER APPLY (SELECT TOP 1 id_calculo, semaforo FROM calculo_prioridad
                 WHERE id_bache = b.id_bache ORDER BY id_calculo DESC) cp
    OUTER APPLY (SELECT TOP 1 semaforo_ajustado FROM decision_humana
                 WHERE id_calculo = cp.id_calculo ORDER BY fecha DESC) d
    WHERE r.id_reporte = @id_reporte;

    SELECT s.fecha, ea.nombre AS de_estado, en.nombre AS a_estado, s.comentario
    FROM reporte r
    JOIN seguimiento_bache s     ON s.id_bache = r.id_bache
    JOIN cat_estado_bache ea     ON ea.id_estado_bache = s.id_estado_anterior
    JOIN cat_estado_bache en     ON en.id_estado_bache = s.id_estado_nuevo
    WHERE r.id_reporte = @id_reporte
    ORDER BY s.fecha, s.id_seguimiento;
END
GO

/* ---------------------------------------------------------------------
   Los dos modos de uso como roles de la base de datos:
     rol_ciudadano: solo reporta y consulta su folio (no lee tablas).
     rol_autoridad: consulta la recomendación, decide y reporta el estado.
   Ninguno puede leer los datos personales del esquema priv.
   --------------------------------------------------------------------- */
IF DATABASE_PRINCIPAL_ID('rol_ciudadano') IS NULL CREATE ROLE rol_ciudadano;
IF DATABASE_PRINCIPAL_ID('rol_autoridad') IS NULL CREATE ROLE rol_autoridad;
GRANT EXECUTE ON dbo.sp_registrar_reporte       TO rol_ciudadano;
GRANT EXECUTE ON dbo.sp_consultar_folio         TO rol_ciudadano;
GRANT SELECT  ON SCHEMA::dbo                    TO rol_autoridad;
GRANT EXECUTE ON dbo.sp_registrar_decision      TO rol_autoridad;
GRANT EXECUTE ON dbo.sp_actualizar_estado_bache TO rol_autoridad;
GRANT EXECUTE ON dbo.sp_consultar_folio         TO rol_autoridad;
DENY  SELECT  ON SCHEMA::priv                   TO rol_ciudadano, rol_autoridad;
GO
PRINT 'Procedimientos y roles creados.';
