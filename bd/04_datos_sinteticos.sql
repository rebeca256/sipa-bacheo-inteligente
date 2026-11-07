/* =====================================================================
   SIPA · 04_datos_sinteticos.sql
   Genera datos SINTÉTICOS para lo que la base maestra no trae
   (sección 9.5 de la propuesta): baches con severidad, profundidad y área.
   Todo valor aquí es ilustrativo. Los valores salen de un hash de la celda
   (HASHBYTES), no de NEWID(): cada reconstrucción genera los mismos baches. Brigadas, material y presupuesto NO
   están en SIPA: son de la autoridad.

   Los baches se forman agrupando los reportes de oct-dic 2022 por celda:
   un bache por celda, y sus reportes quedan ligados a él (deduplicación).
   ===================================================================== */
USE SIPA;
SET QUOTED_IDENTIFIER ON;
SET ANSI_NULLS ON;
GO
SET NOCOUNT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    /* 1. Baches: uno por celda con reportes en el último trimestre de 2022 */
    INSERT INTO bache (celda_id, latitud, longitud, severidad, profundidad_cm, area_m2,
                       id_estado_bache, fecha_deteccion)
    SELECT r.celda_id,
           AVG(r.latitud), AVG(r.longitud),
           1 + CAST(SUBSTRING(HASHBYTES('MD5', CONCAT(r.celda_id, '|severidad')), 1, 3) AS INT) % 5,                          -- severidad 1-5
           CAST(2 + CAST(SUBSTRING(HASHBYTES('MD5', CONCAT(r.celda_id, '|profundidad')), 1, 3) AS INT) % 150 / 10.0 AS DECIMAL(5,1)),  -- 2 a 17 cm
           CAST(0.2 + CAST(SUBSTRING(HASHBYTES('MD5', CONCAT(r.celda_id, '|area')), 1, 3) AS INT) % 300 / 100.0 AS DECIMAL(6,2)),-- 0.2 a 3.2 m2
           2,                                                        -- VALIDADO
           MIN(r.fecha_solicitud)
    FROM reporte r
    WHERE r.fecha_solicitud >= '2022-10-01'
      AND r.celda_id IS NOT NULL AND r.ubicacion_dudosa = 0
    GROUP BY r.celda_id
    ORDER BY r.celda_id;   -- orden fijo: los id_bache salen iguales en cada reconstrucción

    UPDATE r SET id_bache = b.id_bache
    FROM reporte r
    JOIN bache b ON b.celda_id = r.celda_id
    WHERE r.fecha_solicitud >= '2022-10-01' AND r.ubicacion_dudosa = 0;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;

SELECT 'bache' AS tabla, COUNT(*) AS filas FROM bache
UNION ALL SELECT 'reportes ligados a bache', COUNT(*) FROM reporte WHERE id_bache IS NOT NULL;
GO
