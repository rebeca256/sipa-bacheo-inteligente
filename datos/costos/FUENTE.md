# Tarifas de reparación (`tarifas_reparacion.json`)

SIPA no maneja la logística de reparación (brigadas, almacenes, material, presupuesto): eso lo hace la autoridad. Para que la recomendación diga **cuánto costaría** atender cada bache, la base lee este archivo JSON con costos unitarios por tipo de intervención.

- Se carga en la tabla `tarifa_reparacion` con `OPENJSON` (`bd/02_catalogos.sql`).
- `sp_calcular_ipu` elige la intervención según el bache y calcula `costo = costo_fijo + costo_m2 × MAX(área, área mínima)`.
- Los valores son **ILUSTRATIVOS** (estimación del equipo). Cada autoridad puede reemplazar el archivo por su tabulador y volver a cargarlo sin tocar la base.
