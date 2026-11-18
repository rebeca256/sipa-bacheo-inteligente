/* =====================================================================
   SIPA · 12b_demo_replicacion.sql  ·  Demostración de la réplica (opcional)

   NO forma parte de la instalación (bd/ejecutar_todo.ps1 no lo ejecuta):
   inserta un reporte de prueba en SIPA y lo replica. Úsese solo en una
   base de demostración:
       sqlcmd -S localhost -E -f 65001 -i bd\12b_demo_replicacion.sql

   Prueba de recuperación (fallo inducido de restauración):
       1. Poner la réplica en uso exclusivo desde otra sesión o mover el
          archivo .trn más reciente: sp_replicar falla y lo marca ERROR.
       2. Volver a ejecutar dbo.sp_replicar: reintenta primero el tramo
          con ERROR y luego el nuevo, en orden; la réplica se pone al día
          sin recrearse.
   ===================================================================== */
USE SIPA;
SET QUOTED_IDENTIFIER ON;
SET ANSI_NULLS ON;
GO
SET NOCOUNT ON;

SELECT 'antes' AS momento,
       (SELECT COUNT(*) FROM SIPA.dbo.reporte)         AS reportes_principal,
       (SELECT COUNT(*) FROM SIPA_REPLICA.dbo.reporte) AS reportes_replica;

-- b) Llega un reporte nuevo a la principal
DECLARE @rep INT, @bache INT;
DECLARE @colonia INT = (SELECT TOP 1 c.id_colonia FROM colonia c JOIN territorio t
                        ON t.id_territorio = c.id_territorio WHERE t.nombre = 'CHALCO' AND c.nombre = 'CENTRO');
EXEC sp_registrar_reporte @id_fuente = 2, @id_colonia = @colonia,
     @latitud = 19.260100, @longitud = -98.897700,
     @descripcion = 'Prueba de replicación: bache frente al mercado',
     @id_reporte = @rep OUTPUT, @id_bache = @bache OUTPUT;

SELECT 'después del reporte, sin replicar' AS momento,
       (SELECT COUNT(*) FROM SIPA.dbo.reporte)         AS reportes_principal,
       (SELECT COUNT(*) FROM SIPA_REPLICA.dbo.reporte) AS reportes_replica;

-- c) Se envía el log: la réplica se pone al día
EXEC dbo.sp_replicar;

SELECT 'después de replicar' AS momento,
       (SELECT COUNT(*) FROM SIPA.dbo.reporte)         AS reportes_principal,
       (SELECT COUNT(*) FROM SIPA_REPLICA.dbo.reporte) AS reportes_replica;
SELECT id_reporte, descripcion FROM SIPA_REPLICA.dbo.reporte WHERE id_reporte = @rep;
GO


SELECT id_envio, fecha, tipo, estado, mensaje FROM SIPA.dbo.replicacion_bitacora ORDER BY id_envio;
GO
