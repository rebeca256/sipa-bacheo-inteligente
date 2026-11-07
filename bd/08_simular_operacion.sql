/* =====================================================================
   SIPA · 08_simular_operacion.sql
   Genera un historial SIMULADO para alimentar el Data Warehouse.
   Usa los mismos procedimientos del sistema (no inserta a mano):
     1. SIPA calcula el IPU de todos los baches validados.
     2. La autoridad de cada territorio decide sobre los 300 de mayor IPU
        (aprueba la mayoría y ajusta algunos).
     3. La autoridad informa que los repara (EN_ATENCION -> REPARADO) y
        reporta el costo real, que varía alrededor del estimado.
     4. Se reparten las fechas a lo largo de 2026 con tiempos de atención
        que dependen del semáforo, para analizar tiempos de respuesta.
   Todo el resultado es ILUSTRATIVO y reproducible: los valores «al azar»
   salen de un hash del bache (HASHBYTES), así que siempre son los mismos.
   ===================================================================== */
USE SIPA;
SET QUOTED_IDENTIFIER ON;
SET ANSI_NULLS ON;
GO
SET NOCOUNT ON;

/* 1. IPU de todos los baches validados que aún no tienen cálculo */
DECLARE @b INT, @calc INT, @dec INT, @n INT = 0;
DECLARE c1 CURSOR LOCAL FAST_FORWARD FOR
    SELECT id_bache FROM bache b
    WHERE id_estado_bache = 2
      AND NOT EXISTS (SELECT 1 FROM calculo_prioridad cp WHERE cp.id_bache = b.id_bache)
    ORDER BY id_bache;
OPEN c1; FETCH NEXT FROM c1 INTO @b;
WHILE @@FETCH_STATUS = 0
BEGIN
    EXEC sp_calcular_ipu @b, @calc OUTPUT;
    FETCH NEXT FROM c1 INTO @b;
END
CLOSE c1; DEALLOCATE c1;

/* 2 y 3. Decisión y avance informado por la autoridad de cada territorio */
DECLARE @autoridad INT, @costo DECIMAL(12,2);
DECLARE c2 CURSOR LOCAL FAST_FORWARD FOR
    SELECT TOP 300 cp.id_calculo, cp.id_bache, u.id_usuario, cp.costo_estimado
    FROM calculo_prioridad cp
    JOIN bache b ON b.id_bache = cp.id_bache
    CROSS APPLY (SELECT TOP 1 c.id_territorio FROM reporte r JOIN colonia c ON c.id_colonia = r.id_colonia
                 WHERE r.id_bache = b.id_bache GROUP BY c.id_territorio ORDER BY COUNT(*) DESC) ter
    JOIN usuario u ON u.id_territorio = ter.id_territorio AND u.rol = 'AUTORIDAD'
    WHERE b.id_estado_bache = 3
    ORDER BY cp.ipu DESC, cp.id_bache;
OPEN c2; FETCH NEXT FROM c2 INTO @calc, @b, @autoridad, @costo;
WHILE @@FETCH_STATUS = 0
BEGIN
    SET @n += 1;
    -- 1 de cada 10 decisiones la autoridad ajusta la recomendación
    IF @n % 10 = 0
        EXEC sp_registrar_decision @calc, @autoridad, 'AJUSTAR',
             @semaforo_ajustado = 'ROJO',
             @justificacion = 'Ajuste simulado: punto con alto flujo peatonal detectado en inspección.',
             @id_decision = @dec OUTPUT;
    ELSE
        EXEC sp_registrar_decision @calc, @autoridad, 'APROBAR', NULL, NULL, @dec OUTPUT;

    -- costo real: entre 85 % y 130 % del estimado
    SET @costo = ROUND(@costo * (0.85 + (CAST(SUBSTRING(HASHBYTES('MD5', CONCAT(@b, '|costo')), 1, 3) AS INT) % 46) / 100.0), 2);
    EXEC sp_actualizar_estado_bache @b, @autoridad, 4, 'Programado por la autoridad (simulado).';
    EXEC sp_actualizar_estado_bache @b, @autoridad, 5, 'Reparado (simulado).', @costo_reportado = @costo;

    FETCH NEXT FROM c2 INTO @calc, @b, @autoridad, @costo;
END
CLOSE c2; DEALLOCATE c2;

/* 4. Reparto de fechas a lo largo de 2026 (solo datos simulados). */
BEGIN TRANSACTION;

    ;WITH d AS (
        SELECT d.id_decision, c.id_bache, COALESCE(d.semaforo_ajustado, c.semaforo) AS final,
               DATEADD(MINUTE, CAST(SUBSTRING(HASHBYTES('MD5', CONCAT(c.id_bache, '|minuto')), 1, 3) AS INT) % 1440,
                       DATEADD(DAY, CAST(SUBSTRING(HASHBYTES('MD5', CONCAT(c.id_bache, '|dia')), 1, 3) AS INT) % 270, CAST('2026-01-05' AS DATETIME2(0)))) AS decidida
        FROM decision_humana d
        JOIN calculo_prioridad c ON c.id_calculo = d.id_calculo
        WHERE EXISTS (SELECT 1 FROM seguimiento_bache s WHERE s.id_bache = c.id_bache AND s.id_estado_nuevo = 5)
    ), t AS (
        -- horas hasta la reparación: rojo 1-5 días, amarillo 5-24, verde 20-79 (algunos fuera de meta)
        SELECT *, DATEADD(HOUR, CASE final WHEN 'ROJO'     THEN 24  + CAST(SUBSTRING(HASHBYTES('MD5', CONCAT(id_bache, '|rojo')), 1, 3) AS INT) % 96
                                           WHEN 'AMARILLO' THEN 120 + CAST(SUBSTRING(HASHBYTES('MD5', CONCAT(id_bache, '|amarillo')), 1, 3) AS INT) % 456
                                           ELSE                 480 + CAST(SUBSTRING(HASHBYTES('MD5', CONCAT(id_bache, '|verde')), 1, 3) AS INT) % 1440 END, decidida) AS reparada
        FROM d
    )
    SELECT * INTO #fechas FROM t;

    UPDATE dh SET fecha = f.decidida
    FROM decision_humana dh JOIN #fechas f ON f.id_decision = dh.id_decision;

    UPDATE c SET fecha_calculo = DATEADD(HOUR, -2, f.decidida)
    FROM calculo_prioridad c JOIN decision_humana dh ON dh.id_calculo = c.id_calculo
    JOIN #fechas f ON f.id_decision = dh.id_decision;

    -- EN_ATENCION a la mitad del camino; REPARADO en la fecha simulada
    UPDATE s SET fecha = IIF(s.id_estado_nuevo = 5, f.reparada,
                             DATEADD(SECOND, DATEDIFF(SECOND, f.decidida, f.reparada) / 2, f.decidida))
    FROM seguimiento_bache s JOIN #fechas f ON f.id_bache = s.id_bache
    WHERE s.id_estado_nuevo IN (4, 5);

    -- la validación (si la hubo) ocurre antes del cálculo y de la decisión
    UPDATE s SET fecha = DATEADD(HOUR, -6, f.decidida)
    FROM seguimiento_bache s JOIN #fechas f ON f.id_bache = s.id_bache
    WHERE s.id_estado_nuevo = 2;

    UPDATE n SET fecha = s.fecha
    FROM notificacion n JOIN seguimiento_bache s ON s.id_seguimiento = n.id_seguimiento
    JOIN #fechas f ON f.id_bache = s.id_bache;

COMMIT TRANSACTION;

SELECT COUNT(*) AS baches_reparados,
       AVG(DATEDIFF(HOUR, f.decidida, f.reparada) / 24.0) AS dias_promedio,
       SUM(s.costo_reportado) AS costo_reportado_total
FROM #fechas f JOIN seguimiento_bache s ON s.id_bache = f.id_bache AND s.id_estado_nuevo = 5;
GO
