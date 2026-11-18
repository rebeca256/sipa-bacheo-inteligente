/* =====================================================================
   SIPA · 12_replicacion.sql  ·  Réplica de solo lectura (log shipping)

   Objetivo: mejorar la DISPONIBILIDAD. La base principal SIPA recibe las
   escrituras; SIPA_REPLICA es una copia de solo lectura que puede usar el
   tablero o el ETL sin cargar la principal, y que sigue disponible para
   consulta si la principal falla.

   Técnica: log shipping (envío del registro de transacciones)
     1. Respaldo completo de SIPA  ->  se restaura como SIPA_REPLICA en
        modo STANDBY (solo lectura, pero acepta más restauraciones).
     2. dbo.sp_replicar respalda el log de SIPA (los cambios desde el último
        envío) y lo aplica a SIPA_REPLICA.
   En producción el paso 2 lo programaría el Agente de SQL Server (p. ej.
   cada 15 minutos) y la réplica estaría en otro servidor; aquí se ejecuta
   a mano y en la misma instancia.

   Datos personales: el log copia la base completa, incluido el esquema
   priv. Por eso el acceso se controla con el rol rol_tablero, que puede
   leer dbo pero tiene DENY sobre priv; el rol se replica con la base.

   Requiere que SIPA esté en modelo de recuperación FULL (se configura aquí).
   ===================================================================== */
USE master;
SET QUOTED_IDENTIFIER ON;
SET ANSI_NULLS ON;
GO
SET NOCOUNT ON;

/* 0. Rol de solo lectura para el tablero (en la principal; viaja a la réplica) */
USE SIPA;
IF DATABASE_PRINCIPAL_ID('rol_tablero') IS NULL
    CREATE ROLE rol_tablero;
GRANT SELECT ON SCHEMA::dbo  TO rol_tablero;
DENY  SELECT ON SCHEMA::priv TO rol_tablero;
-- usuario de prueba sin inicio de sesión, solo para demostrar los permisos
IF DATABASE_PRINCIPAL_ID('usuario_tablero') IS NULL
    CREATE USER usuario_tablero WITHOUT LOGIN;
ALTER ROLE rol_tablero ADD MEMBER usuario_tablero;

-- Bitácora de cada envío de log
IF OBJECT_ID('dbo.replicacion_bitacora') IS NULL
    CREATE TABLE dbo.replicacion_bitacora (
        id_envio    INT IDENTITY(1,1) CONSTRAINT pk_replicacion_bitacora PRIMARY KEY,
        fecha       DATETIME2(0) NOT NULL CONSTRAINT df_replicacion_fecha DEFAULT SYSDATETIME(),
        tipo        VARCHAR(10)  NOT NULL CONSTRAINT ck_replicacion_tipo CHECK (tipo IN ('COMPLETO','LOG')),
        archivo     VARCHAR(400) NOT NULL,
        estado      VARCHAR(10)  NOT NULL,
        mensaje     VARCHAR(400) NULL
    );
GO

/* ---------------------------------------------------------------------
   Procedimiento de envío de log. Se puede ejecutar cuantas veces se quiera.

     1. Serializa: si otra ejecución está en curso, espera (sp_getapplock).
     2. Anota el archivo como PREPARADO ANTES de respaldar, respalda el log
        y lo pasa a PENDIENTE. Si la sesión se corta entre el respaldo y la
        anotación, el tramo ya está en la bitácora (PREPARADO) y el siguiente
        ciclo lo aplica; si el respaldo nunca llegó a escribirse (ni el
        archivo ni msdb lo conocen), ese renglón se marca ANULADO.
     3. Aplica EN ORDEN todos los archivos PENDIENTE o ERROR posteriores al
        último respaldo completo. Si uno falla, se marca ERROR y se detiene:
        el siguiente ciclo lo reintenta antes que los nuevos, así la cadena
        de logs nunca se salta un tramo.
     Si un archivo ya estaba aplicado (consta en msdb.dbo.restorehistory),
     se marca OK y se continúa con el siguiente.
   --------------------------------------------------------------------- */
CREATE OR ALTER PROCEDURE dbo.sp_replicar
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @dir NVARCHAR(400) = CAST(SERVERPROPERTY('InstanceDefaultBackupPath') AS NVARCHAR(400)) + N'\';
    DECLARE @archivo NVARCHAR(400) = @dir + N'SIPA_log_' + FORMAT(SYSDATETIME(), 'yyyyMMdd_HHmmss_fff') + N'.trn';
    DECLARE @undo NVARCHAR(400) = @dir + N'SIPA_REPLICA_undo.tuf';
    DECLARE @sql NVARCHAR(MAX), @lock INT, @id INT, @pend NVARCHAR(400), @desde INT;

    EXEC @lock = sp_getapplock @Resource = 'SIPA.replicacion', @LockMode = 'Exclusive',
                               @LockOwner = 'Session', @LockTimeout = 120000;
    IF @lock < 0 THROW 50030, 'Otra replicación sigue en curso.', 1;

    BEGIN TRY
        -- 2. Nuevo tramo del log: primero se anota, después se respalda
        DECLARE @nuevo INT;
        INSERT INTO SIPA.dbo.replicacion_bitacora (tipo, archivo, estado) VALUES ('LOG', @archivo, 'PREPARADO');
        SET @nuevo = SCOPE_IDENTITY();
        BACKUP LOG SIPA TO DISK = @archivo WITH INIT;
        UPDATE SIPA.dbo.replicacion_bitacora SET estado = 'PENDIENTE' WHERE id_envio = @nuevo;

        -- la réplica no debe tener conexiones abiertas mientras se restaura
        DECLARE @sesion INT;
        DECLARE sesiones CURSOR LOCAL FAST_FORWARD FOR
            SELECT session_id FROM sys.dm_exec_sessions
            WHERE database_id = DB_ID('SIPA_REPLICA') AND session_id <> @@SPID;
        OPEN sesiones; FETCH NEXT FROM sesiones INTO @sesion;
        WHILE @@FETCH_STATUS = 0
        BEGIN
            SET @sql = N'KILL ' + CAST(@sesion AS NVARCHAR(10));
            EXEC (@sql);
            FETCH NEXT FROM sesiones INTO @sesion;
        END
        CLOSE sesiones; DEALLOCATE sesiones;

        -- 3. Aplicar en orden lo pendiente desde el último respaldo completo
        SET @desde = ISNULL((SELECT MAX(id_envio) FROM SIPA.dbo.replicacion_bitacora
                             WHERE tipo = 'COMPLETO' AND estado = 'OK'), 0);
        WHILE 1 = 1
        BEGIN
            SELECT TOP 1 @id = id_envio, @pend = archivo FROM SIPA.dbo.replicacion_bitacora
            WHERE tipo = 'LOG' AND estado IN ('PREPARADO', 'PENDIENTE', 'ERROR') AND id_envio > @desde
            ORDER BY id_envio;
            IF @@ROWCOUNT = 0 BREAK;

            -- ¿Ya se aplicó? (msdb registra cada restauración y el archivo de origen)
            IF EXISTS (SELECT 1 FROM msdb.dbo.restorehistory rh
                       JOIN msdb.dbo.backupset bs ON bs.backup_set_id = rh.backup_set_id
                       JOIN msdb.dbo.backupmediafamily mf ON mf.media_set_id = bs.media_set_id
                       WHERE rh.destination_database_name = 'SIPA_REPLICA' AND mf.physical_device_name = @pend)
            BEGIN
                UPDATE SIPA.dbo.replicacion_bitacora SET estado = 'OK', mensaje = 'Ya estaba aplicado.'
                WHERE id_envio = @id;
                CONTINUE;
            END

            -- ¿Existe el archivo? Si se anotó pero el respaldo nunca se escribió, no hay tramo que aplicar.
            DECLARE @existe INT = 0;
            EXEC master.dbo.xp_fileexist @pend, @existe OUTPUT;
            IF @existe = 0 AND NOT EXISTS (SELECT 1 FROM msdb.dbo.backupmediafamily WHERE physical_device_name = @pend)
            BEGIN
                UPDATE SIPA.dbo.replicacion_bitacora SET estado = 'ANULADO',
                       mensaje = 'El respaldo no llegó a escribirse.' WHERE id_envio = @id;
                CONTINUE;
            END

            BEGIN TRY
                RESTORE LOG SIPA_REPLICA FROM DISK = @pend WITH STANDBY = @undo;
                UPDATE SIPA.dbo.replicacion_bitacora SET estado = 'OK', mensaje = NULL WHERE id_envio = @id;
            END TRY
            BEGIN CATCH
                UPDATE SIPA.dbo.replicacion_bitacora
                SET estado = 'ERROR', mensaje = LEFT(ERROR_MESSAGE(), 400) WHERE id_envio = @id;
                THROW;
            END CATCH
        END
        EXEC sp_releaseapplock @Resource = 'SIPA.replicacion', @LockOwner = 'Session';
    END TRY
    BEGIN CATCH
        EXEC sp_releaseapplock @Resource = 'SIPA.replicacion', @LockOwner = 'Session';
        THROW;
    END CATCH
END
GO

/* ---------------------------------------------------------------------
   1. Configuración inicial: modelo FULL, respaldo completo y restauración
      de la réplica en modo STANDBY.
   --------------------------------------------------------------------- */
USE master;
ALTER DATABASE SIPA SET RECOVERY FULL;

IF DB_ID('SIPA_REPLICA') IS NOT NULL
BEGIN
    -- una base en STANDBY se quita de en medio sin SINGLE_USER
    DROP DATABASE SIPA_REPLICA;
END

DECLARE @dir   NVARCHAR(400) = CAST(SERVERPROPERTY('InstanceDefaultBackupPath') AS NVARCHAR(400)) + N'\';
DECLARE @datos NVARCHAR(400) = CAST(SERVERPROPERTY('InstanceDefaultDataPath')   AS NVARCHAR(400));
DECLARE @full  NVARCHAR(400) = @dir + N'SIPA_full.bak';
DECLARE @undo  NVARCHAR(400) = @dir + N'SIPA_REPLICA_undo.tuf';
DECLARE @mdf   NVARCHAR(400) = @datos + N'SIPA_REPLICA.mdf';
DECLARE @ldf   NVARCHAR(400) = @datos + N'SIPA_REPLICA_log.ldf';
DECLARE @dato_logico NVARCHAR(128), @log_logico NVARCHAR(128);

SELECT @dato_logico = name FROM SIPA.sys.database_files WHERE type_desc = 'ROWS';
SELECT @log_logico  = name FROM SIPA.sys.database_files WHERE type_desc = 'LOG';

BACKUP DATABASE SIPA TO DISK = @full WITH INIT, FORMAT;

RESTORE DATABASE SIPA_REPLICA FROM DISK = @full
WITH MOVE @dato_logico TO @mdf,
     MOVE @log_logico  TO @ldf,
     STANDBY = @undo, REPLACE;

INSERT INTO SIPA.dbo.replicacion_bitacora (tipo, archivo, estado) VALUES ('COMPLETO', @full, 'OK');
PRINT 'Réplica SIPA_REPLICA creada en modo de solo lectura.';
GO

/* ---------------------------------------------------------------------
   2. DEMOSTRACIÓN
   --------------------------------------------------------------------- */
USE SIPA;
GO
SET NOCOUNT ON;

-- a) Estado inicial: ambas bases tienen los mismos reportes
SELECT 'antes' AS momento,
       (SELECT COUNT(*) FROM SIPA.dbo.reporte)         AS reportes_principal,
       (SELECT COUNT(*) FROM SIPA_REPLICA.dbo.reporte) AS reportes_replica;

-- b) y c) El reporte de prueba y el envío de log están en 12b_demo_replicacion.sql,
--    fuera de la instalación, para no insertar datos de demostración.
EXEC dbo.sp_replicar;   -- primer envío: deja la réplica al día con la instalación
GO

-- d) La réplica es de solo lectura: cualquier escritura se rechaza
BEGIN TRY
    UPDATE SIPA_REPLICA.dbo.bache SET severidad = 5 WHERE id_bache = 1;
    PRINT 'ERROR: la réplica aceptó una escritura';
END TRY
BEGIN CATCH
    SELECT 'Escritura rechazada en la réplica' AS resultado, ERROR_MESSAGE() AS mensaje;
END CATCH;

-- e) En la réplica, el tablero lee reportes pero NO datos personales
USE SIPA_REPLICA;
EXECUTE AS USER = 'usuario_tablero';
SELECT 'tablero lee dbo.reporte' AS prueba, COUNT(*) AS filas FROM dbo.reporte;
BEGIN TRY
    SELECT COUNT(*) AS filas FROM priv.contacto_ciudadano;
    PRINT 'ERROR: el tablero pudo leer datos personales';
END TRY
BEGIN CATCH
    SELECT 'tablero intenta leer priv.contacto_ciudadano' AS prueba, ERROR_MESSAGE() AS resultado;
END CATCH;
REVERT;
USE SIPA;
GO

-- f) Estado de las bases y bitácora de envíos
SELECT name AS base, state_desc AS estado, is_read_only AS solo_lectura,
       is_in_standby AS en_standby, recovery_model_desc AS modelo_recuperacion
FROM sys.databases WHERE name IN ('SIPA', 'SIPA_REPLICA');

SELECT id_envio, fecha, tipo, estado FROM SIPA.dbo.replicacion_bitacora ORDER BY id_envio;
GO
