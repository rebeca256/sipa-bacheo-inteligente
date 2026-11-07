/* =====================================================================
   SIPA · 07_demo_y_consultas.sql
   Parte A: recorrido de un reporte de principio a fin, con los dos modos
            (ciudadano y autoridad).
   Parte B: transacción que falla a propósito para demostrar ROLLBACK.
   Parte C: consultas de análisis para la priorización.
   ===================================================================== */
USE SIPA;
SET QUOTED_IDENTIFIER ON;
SET ANSI_NULLS ON;
GO
SET NOCOUNT ON;

/* ===================== PARTE A: flujo completo ===================== */
DECLARE @rep INT, @bache INT, @calc INT, @dec INT, @seg INT, @rep2 INT, @bache2 INT;
DECLARE @colonia INT = (SELECT TOP 1 id_colonia FROM colonia WHERE nombre LIKE 'LINDAVISTA%');
DECLARE @autoridad INT = (SELECT u.id_usuario FROM usuario u JOIN colonia c ON c.id_territorio = u.id_territorio
                          WHERE c.id_colonia = @colonia AND u.rol = 'AUTORIDAD');

-- 1. [Ciudadano] Llega un reporte
EXEC sp_registrar_reporte @id_fuente = 2, @id_colonia = @colonia,
     @latitud = 19.499211, @longitud = -99.130782,
     @descripcion = 'Bache profundo frente a la escuela',
     @id_reporte = @rep OUTPUT, @id_bache = @bache OUTPUT;

-- 2. [Ciudadano] Otro reporte del mismo lugar: se liga al mismo bache (duplicado)
EXEC sp_registrar_reporte @id_fuente = 2, @id_colonia = @colonia,
     @latitud = 19.499300, @longitud = -99.130700,
     @id_reporte = @rep2 OUTPUT, @id_bache = @bache2 OUTPUT;
SELECT @rep AS reporte_1, @rep2 AS reporte_2, @bache AS bache_1, @bache2 AS bache_2,
       IIF(@bache = @bache2, 'Duplicado detectado', 'Baches distintos') AS resultado;

-- 3. [Autoridad] Inspecciona, registra las medidas y valida el bache
UPDATE bache SET severidad = 5, profundidad_cm = 12, area_m2 = 1.5 WHERE id_bache = @bache;
EXEC sp_actualizar_estado_bache @bache, @autoridad, 2, 'Validado en inspección.';

-- 4. [SIPA] Calcula el IPU, recomienda la intervención y estima el costo
EXEC sp_calcular_ipu @id_bache = @bache, @id_calculo = @calc OUTPUT;

-- Ficha de justificación: cuánto aporta cada criterio
SELECT c.nombre AS criterio, d.valor_normalizado, d.peso_aplicado,
       CAST(d.valor_normalizado * d.peso_aplicado AS DECIMAL(5,4)) AS aporte
FROM detalle_calculo d JOIN criterio_ipu c ON c.id_criterio = d.id_criterio
WHERE d.id_calculo = @calc ORDER BY aporte DESC;
SELECT cp.ipu, cp.semaforo, t.nombre AS intervencion_recomendada, cp.costo_estimado
FROM calculo_prioridad cp JOIN tarifa_reparacion t ON t.clave = cp.clave_tarifa
WHERE cp.id_calculo = @calc;

-- 5. [Autoridad] Decide: ajusta a ROJO con justificación
EXEC sp_registrar_decision @id_calculo = @calc, @id_usuario = @autoridad, @decision = 'AJUSTAR',
     @semaforo_ajustado = 'ROJO',
     @justificacion = 'Está frente a una escuela primaria; riesgo para peatones en horario de entrada.',
     @id_decision = @dec OUTPUT;

-- 6. [Autoridad] Repara con sus propios recursos e informa el avance y el costo real
EXEC sp_actualizar_estado_bache @bache, @autoridad, 4, 'Programado para el turno nocturno.';
EXEC sp_actualizar_estado_bache @bache, @autoridad, 5, 'Reparado.', @costo_reportado = 2950.00;

-- 7. [Ciudadano] Consulta su folio y ve el avance; ambos reportes fueron notificados
EXEC sp_consultar_folio @rep2;
SELECT COUNT(*) AS reportes_notificados FROM notificacion n
JOIN reporte r ON r.id_reporte = n.id_reporte WHERE r.id_bache = @bache;
GO

/* ===== PARTE B: ROLLBACK al descartar un bache sin explicar por qué ===== */
-- El procedimiento primero cambia el estado del bache y después intenta
-- registrar el seguimiento. Sin motivo, el CHECK ck_seguimiento_descarte
-- falla y la transacción completa se revierte: el bache conserva su estado.
DECLARE @bache INT = (SELECT TOP 1 id_bache FROM bache WHERE id_estado_bache = 2 ORDER BY id_bache);
DECLARE @autoridad INT = (SELECT MIN(id_usuario) FROM usuario WHERE rol = 'AUTORIDAD');
DECLARE @antes TINYINT = (SELECT id_estado_bache FROM bache WHERE id_bache = @bache),
        @seg_antes INT = (SELECT COUNT(*) FROM seguimiento_bache), @despues TINYINT, @seg_despues INT;

BEGIN TRY
    EXEC sp_actualizar_estado_bache @bache, @autoridad, 6, @comentario = NULL;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    PRINT 'Transacción revertida: ' + ERROR_MESSAGE();
END CATCH;
SELECT @despues = id_estado_bache FROM bache WHERE id_bache = @bache;
SELECT @seg_despues = COUNT(*) FROM seguimiento_bache;

SELECT @antes AS estado_antes, @despues AS estado_despues,
       @seg_antes AS seguimientos_antes, @seg_despues AS seguimientos_despues,
       IIF(@antes = @despues AND @seg_antes = @seg_despues,
           'Nada cambió: ROLLBACK correcto', 'ERROR') AS resultado;
GO

/* ===================== PARTE C: consultas de análisis ===================== */

-- C1. Reportes por alcaldía y año (anio se deriva de la fecha, no se guarda)
SELECT t.nombre AS alcaldia, YEAR(r.fecha_solicitud) AS anio, COUNT(*) AS reportes
FROM reporte r
JOIN colonia c    ON c.id_colonia = r.id_colonia
JOIN territorio t ON t.id_territorio = c.id_territorio
GROUP BY t.nombre, YEAR(r.fecha_solicitud)
ORDER BY t.nombre, anio;

-- C2. Efecto de la temporada de lluvias: promedio mensual de reportes
SELECT IIF(temporada_lluvias = 1, 'Lluvias (jun-oct)', 'Secas') AS temporada,
       COUNT(*) * 1.0 / COUNT(DISTINCT FORMAT(fecha_solicitud, 'yyyy-MM')) AS reportes_por_mes
FROM reporte WHERE periodo_atipico = 0
GROUP BY temporada_lluvias;

-- C3. Las 10 celdas con más reportes históricos (candidatas a programa preventivo)
SELECT TOP 10 r.celda_id, ce.latitud, ce.longitud, COUNT(*) AS reportes,
       MIN(r.fecha_solicitud) AS primero, MAX(r.fecha_solicitud) AS ultimo
FROM reporte r JOIN celda ce ON ce.celda_id = r.celda_id
GROUP BY r.celda_id, ce.latitud, ce.longitud
ORDER BY reportes DESC;

-- C4. Proporción de reportes turnados por alcaldía (posible cuello de botella)
SELECT t.nombre AS alcaldia,
       COUNT(*) AS total,
       SUM(IIF(e.estatus_agrupado = 'TURNADO', 1, 0)) AS turnados,
       CAST(100.0 * SUM(IIF(e.estatus_agrupado = 'TURNADO', 1, 0)) / COUNT(*) AS DECIMAL(5,1)) AS pct_turnados
FROM reporte r
JOIN cat_estatus_reporte e ON e.estatus_original = r.estatus_original
JOIN colonia c    ON c.id_colonia = r.id_colonia
JOIN territorio t ON t.id_territorio = c.id_territorio
GROUP BY t.nombre ORDER BY pct_turnados DESC;

-- C5. Calidad de los datos: cuántos registros traen cada marca de control
SELECT SUM(CAST(ubicacion_dudosa  AS INT)) AS ubicacion_dudosa,
       SUM(CAST(posible_duplicado AS INT)) AS posible_duplicado,
       SUM(CAST(alcaldia_inferida AS INT)) AS alcaldia_inferida,
       SUM(CAST(colonia_inferida  AS INT)) AS colonia_inferida,
       SUM(CAST(periodo_atipico   AS INT)) AS periodo_atipico
FROM reporte;

-- C6. ¿Cuánto costaría atender lo pendiente? Costo estimado (tarifas del JSON)
--     del último cálculo de cada bache aún no reparado, por territorio y semáforo
SELECT t.nombre AS territorio, cp.semaforo, COUNT(*) AS baches,
       SUM(cp.costo_estimado) AS costo_estimado
FROM bache b
CROSS APPLY (SELECT TOP 1 * FROM calculo_prioridad x WHERE x.id_bache = b.id_bache
             ORDER BY x.id_calculo DESC) cp
CROSS APPLY (SELECT TOP 1 c.id_territorio FROM reporte r JOIN colonia c ON c.id_colonia = r.id_colonia
             WHERE r.id_bache = b.id_bache GROUP BY c.id_territorio ORDER BY COUNT(*) DESC) ter
JOIN territorio t ON t.id_territorio = ter.id_territorio
WHERE b.id_estado_bache IN (2,3,4)
GROUP BY t.nombre, cp.semaforo
ORDER BY t.nombre, cp.semaforo;

-- C7. Decisiones humanas que cambiaron la recomendación del algoritmo
SELECT d.fecha, u.nombre AS autoridad, cp.semaforo AS recomendado,
       d.semaforo_ajustado AS decidido, d.justificacion
FROM decision_humana d
JOIN calculo_prioridad cp ON cp.id_calculo = d.id_calculo
JOIN usuario u            ON u.id_usuario = d.id_usuario
WHERE d.decision = 'AJUSTAR';
GO
