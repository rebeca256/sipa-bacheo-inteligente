/* =====================================================================
   SIPA · 05_procedimientos_transacciones.sql
   Procedimientos almacenados del flujo de SIPA. Cada uno que modifica
   datos es una transacción: si cualquier paso falla, se revierte todo.

     Modo ciudadano
       sp_registrar_reporte        reporte nuevo + vinculación por distancia (15 m, 30 días, territorio)
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
   Registra un reporte con una POLÍTICA DE VINCULACIÓN explícita (la misma
   que usa el prototipo de estructuras/sipa_ed.py):

     Un reporte se liga a un bache existente solo si el bache
       a) sigue abierto (REPORTADO, VALIDADO, PRIORIZADO o EN_ATENCION),
       b) está a 15 m o menos (distancia física, no la celda de 250 m:
          dos baches separados dentro de una celda quedan como casos
          distintos y un duplicado junto al borde entre celdas sí se liga),
       c) pertenece al mismo territorio que la colonia del reporte, y
       d) recibió su último reporte hace 30 días o menos.
     Si varios cumplen, gana el más cercano (empate: el id menor).
     En otro caso se crea un bache nuevo.

   Validación de coordenadas: si la colonia ya tiene reportes, el punto
   debe quedar a 3 km o menos de su centro; y el punto debe caer dentro
   de la cuadrícula (celda a 300 m o menos). Lo demás se rechaza.
   La celda se sigue guardando para los indicadores territoriales.
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

    DECLARE @radio_m FLOAT = 15, @dias INT = 30;
    -- metros por grado (aproximación plana, válida a la escala de una calle)
    DECLARE @m_lat FLOAT = 110574,
            @m_lon FLOAT = 111320 * COS(RADIANS(CAST(@latitud AS FLOAT)));
    DECLARE @territorio INT = (SELECT id_territorio FROM colonia WHERE id_colonia = @id_colonia);
    IF @territorio IS NULL THROW 50012, 'La colonia del reporte no existe.', 1;

    -- Coordenadas congruentes con la colonia (si ya hay reportes de ella)
    DECLARE @c_lat FLOAT, @c_lon FLOAT;
    SELECT @c_lat = AVG(CAST(latitud AS FLOAT)), @c_lon = AVG(CAST(longitud AS FLOAT))
    FROM reporte WHERE id_colonia = @id_colonia AND latitud IS NOT NULL;
    IF @c_lat IS NOT NULL AND
       SQRT(SQUARE((@latitud - @c_lat) * @m_lat) + SQUARE((@longitud - @c_lon) * @m_lon)) > 3000
        THROW 50013, 'Las coordenadas quedan a más de 3 km de la colonia indicada; revise la colonia o el punto.', 1;

    -- Celda más cercana (cuadrícula de 250 m), solo para indicadores
    DECLARE @celda VARCHAR(12), @d_celda FLOAT;
    SELECT TOP 1 @celda = celda_id,
           @d_celda = SQRT(SQUARE((latitud - @latitud) * @m_lat) + SQUARE((longitud - @longitud) * @m_lon))
    FROM celda
    WHERE latitud BETWEEN @latitud - 0.01 AND @latitud + 0.01
      AND longitud BETWEEN @longitud - 0.01 AND @longitud + 0.01
    ORDER BY SQUARE((latitud - @latitud) * @m_lat) + SQUARE((longitud - @longitud) * @m_lon);
    IF @celda IS NULL OR @d_celda > 300
        THROW 50014, 'Las coordenadas quedan fuera de la zona cubierta por SIPA.', 1;

    DECLARE @dlat FLOAT = @radio_m / @m_lat, @dlon FLOAT = @radio_m / @m_lon;

    BEGIN TRANSACTION;
        -- Primero el candado de reincidencia (exclusivo, hasta el COMMIT), antes de leer o
        -- insertar nada: las altas obtienen su ID en el mismo orden en que se clasifican, y
        -- una reconstrucción completa (mismo candado) nunca queda cruzada con un alta a medias.
        DECLARE @lock INT;
        EXEC @lock = sp_getapplock @Resource = 'ind.reincidencia', @LockMode = 'Exclusive',
                                   @LockOwner = 'Transaction', @LockTimeout = 60000;
        IF @lock < 0 THROW 50020, 'Otra alta o reconstrucción de reincidencia sigue en curso.', 1;

        SELECT TOP 1 @id_bache = b.id_bache
        FROM bache b WITH (UPDLOCK, HOLDLOCK)
        WHERE b.id_estado_bache IN (1,2,3,4)
          AND b.latitud  BETWEEN @latitud  - @dlat AND @latitud  + @dlat
          AND b.longitud BETWEEN @longitud - @dlon AND @longitud + @dlon
          AND SQRT(SQUARE((b.latitud - @latitud) * @m_lat) + SQUARE((b.longitud - @longitud) * @m_lon)) <= @radio_m
          AND EXISTS (SELECT 1 FROM reporte r JOIN colonia c ON c.id_colonia = r.id_colonia
                      WHERE r.id_bache = b.id_bache AND c.id_territorio = @territorio)
          AND (SELECT MAX(r.fecha_solicitud) FROM reporte r WHERE r.id_bache = b.id_bache)
              >= DATEADD(DAY, -@dias, CAST(GETDATE() AS DATE))
        ORDER BY SQUARE((b.latitud - @latitud) * @m_lat) + SQUARE((b.longitud - @longitud) * @m_lon), b.id_bache;

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

        -- Reincidencia al instante (el esquema ind se crea en bd/13; antes de eso no aplica)
        IF OBJECT_ID('ind.sp_reincidencia_reporte') IS NOT NULL
            EXEC ind.sp_reincidencia_reporte @id_reporte;

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
   IDENTIDAD DEL ACTOR. La base tiene un modo de operación:
     DEMO       (lo que instala ejecutar_todo.ps1, con datos simulados):
                el cliente indica @id_usuario; es la simulación académica
                del selector «Entrar como» del tablero.
     OPERATIVO  la identidad la da la SESIÓN de SQL Server: el login
                autenticado (ORIGINAL_LOGIN()) debe estar asociado a un
                usuario activo en usuario.login_sql. El @id_usuario que
                mande el cliente se ignora si es NULL y se rechaza si no
                coincide: nadie puede hacerse pasar por otra autoridad.
   Pasar a operación real:
     UPDATE dbo.configuracion SET valor = 'OPERATIVO' WHERE clave = 'modo';
     UPDATE dbo.usuario SET login_sql = N'DOMINIO\persona' WHERE id_usuario = ...;
   y dar a cada login solo el rol rol_autoridad (EXECUTE de los procedimientos).
   --------------------------------------------------------------------- */
IF OBJECT_ID('dbo.configuracion') IS NULL
    CREATE TABLE dbo.configuracion (
        clave  VARCHAR(30)  CONSTRAINT pk_configuracion PRIMARY KEY,
        valor  VARCHAR(100) NOT NULL,
        CONSTRAINT ck_configuracion_modo CHECK (clave <> 'modo' OR valor IN ('DEMO','OPERATIVO'))
    );
IF NOT EXISTS (SELECT 1 FROM dbo.configuracion WHERE clave = 'modo')
    INSERT INTO dbo.configuracion VALUES ('modo', 'DEMO');
IF COL_LENGTH('dbo.usuario', 'login_sql') IS NULL
    ALTER TABLE dbo.usuario ADD login_sql NVARCHAR(128) NULL;
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'uq_usuario_login')
    CREATE UNIQUE INDEX uq_usuario_login ON dbo.usuario(login_sql) WHERE login_sql IS NOT NULL;
GO

/* Devuelve el id del actor autorizado (AUTORIDAD o ADMIN activo) o NULL. */
CREATE OR ALTER FUNCTION dbo.fn_actor(@id_usuario INT)
RETURNS INT
AS
BEGIN
    DECLARE @modo VARCHAR(100) = ISNULL((SELECT valor FROM dbo.configuracion WHERE clave = 'modo'), 'OPERATIVO');
    DECLARE @sesion INT = (SELECT id_usuario FROM dbo.usuario
                           WHERE login_sql = ORIGINAL_LOGIN() AND activo = 1 AND rol IN ('AUTORIDAD','ADMIN'));
    IF @modo = 'OPERATIVO'
        RETURN IIF(@sesion IS NOT NULL AND (@id_usuario IS NULL OR @id_usuario = @sesion), @sesion, NULL);
    RETURN (SELECT id_usuario FROM dbo.usuario
            WHERE id_usuario = @id_usuario AND activo = 1 AND rol IN ('AUTORIDAD','ADMIN'));
END
GO

/* ---------------------------------------------------------------------
   Territorio del bache: el de la colonia de sus reportes. Una autoridad
   (rol AUTORIDAD) solo puede decidir o informar avances de baches con al
   menos un reporte en su territorio; ADMIN no tiene esa restricción.
   --------------------------------------------------------------------- */
CREATE OR ALTER FUNCTION dbo.fn_autoridad_puede(@id_usuario INT, @id_bache INT)
RETURNS BIT
AS
BEGIN
    IF EXISTS (SELECT 1 FROM usuario WHERE id_usuario = @id_usuario AND rol = 'ADMIN' AND activo = 1)
        RETURN 1;
    IF EXISTS (SELECT 1 FROM usuario u
               JOIN colonia c ON c.id_territorio = u.id_territorio
               JOIN reporte r ON r.id_colonia = c.id_colonia
               WHERE u.id_usuario = @id_usuario AND u.rol = 'AUTORIDAD' AND u.activo = 1
                 AND r.id_bache = @id_bache)
        RETURN 1;
    RETURN 0;
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
    @id_usuario        INT = NULL,       -- en modo OPERATIVO lo da la sesión
    @decision          VARCHAR(10),
    @semaforo_ajustado VARCHAR(8)   = NULL,
    @justificacion     VARCHAR(500) = NULL,
    @id_decision       INT OUTPUT
AS
BEGIN
    SET NOCOUNT ON; SET XACT_ABORT ON;

    DECLARE @actor INT = dbo.fn_actor(@id_usuario);
    IF @actor IS NULL
        THROW 50002, 'Solo una autoridad activa y autenticada puede decidir sobre una recomendación.', 1;

    DECLARE @bache_dec INT, @estado_dec TINYINT;
    SELECT @bache_dec = cp.id_bache, @estado_dec = b.id_estado_bache
    FROM calculo_prioridad cp JOIN bache b ON b.id_bache = cp.id_bache
    WHERE cp.id_calculo = @id_calculo;
    IF @bache_dec IS NULL THROW 50008, 'El cálculo de prioridad no existe.', 1;
    IF dbo.fn_autoridad_puede(@actor, @bache_dec) = 0
        THROW 50010, 'La autoridad solo puede decidir sobre baches de su territorio.', 1;
    -- Un bache reparado o descartado ya no admite decisiones (evita tiempos de atención negativos).
    IF @estado_dec IN (5, 6)
        THROW 50009, 'El bache ya está cerrado: reparado o descartado; no admite nuevas decisiones.', 1;

    BEGIN TRANSACTION;
        INSERT INTO decision_humana (id_calculo, id_usuario, decision, semaforo_ajustado, justificacion)
        VALUES (@id_calculo, @actor, @decision, @semaforo_ajustado, @justificacion);
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
    @id_usuario       INT,              -- en modo OPERATIVO puede ir NULL: lo da la sesión
    @nuevo            TINYINT,
    @comentario       VARCHAR(300)  = NULL,
    @costo_reportado  DECIMAL(12,2) = NULL,
    @id_seguimiento   INT = NULL OUTPUT
AS
BEGIN
    SET NOCOUNT ON; SET XACT_ABORT ON;
    DECLARE @actual TINYINT;

    DECLARE @actor INT = dbo.fn_actor(@id_usuario);
    IF @actor IS NULL
        THROW 50003, 'Solo una autoridad activa y autenticada puede actualizar el estado de un bache.', 1;
    IF dbo.fn_autoridad_puede(@actor, @id_bache) = 0
        THROW 50011, 'La autoridad solo puede actualizar baches de su territorio.', 1;

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
        VALUES (@id_bache, @actual, @nuevo, @actor, @comentario, @costo_reportado);
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
