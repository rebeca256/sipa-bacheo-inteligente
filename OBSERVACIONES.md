# SIPA · Observaciones

Registro de observaciones del proyecto: comentarios de docentes, del equipo y observaciones técnicas o de los datos que conviene tener presentes.
Los avances y cambios van en [`AVANCES.md`](AVANCES.md).

**Cómo registrar:** una fila por observación, con fecha y origen. Al atenderla, cambia el estado y anota qué se hizo.

Estados: ⬜ Abierta · 🟡 En proceso · ✅ Atendida · ➖ Solo informativa

---

## 1. Observaciones de docentes

| # | Fecha | Materia | Observación | Estado | Cómo se atendió |
|---|---|---|---|---|---|
| D3 | 26 oct 2026 | Estructuras de Datos | La docente autorizó el uso de IA siempre que se dé crédito y se mencione que se usó como apoyo en el desarrollo. | ✅ | Declarado en cada archivo de `estructuras/` y en su README. Conviene guardar el permiso por escrito. |
| D2 | 23 oct 2026 | Pensamiento Complejo | El docente compartió 5 documentos de propuesta (priorización vial en Chalco, drenaje pluvial, suelo y pavimentación, historia México–Cuautla, fosas sépticas). | 🟡 | Revisados; se integraron los criterios de inundación y acceso a servicios y los datos abiertos de Chalco. Pendiente: reincidencia, causa probable, indicadores. Fosas sépticas no aplica. |
| D1 | 23 oct 2026 | Fundamentos de Bases de Datos | 2ª entrega: desarrollo del proyecto y «que se vea plasmado en la planeación». | 🟡 | Desarrollo hecho en `bd/`. Se interpretó «plasmado en la planeación» como relacionar el proyecto con los temas, productos y rúbricas de la planeación: `avance2_BD_planeacion.docx`. Conviene confirmarlo con la docente. |

## 2. Observaciones del equipo

| # | Fecha | Observación | Estado | Cómo se atendió |
|---|---|---|---|---|
| E1 | 23 oct 2026 | Todas las materias piden la 2ª entrega a más tardar el 1 de noviembre de 2026. | ➖ | |
| E2 | 23 oct 2026 | `avance1_PP.docx` y `avance2_PP_incidente_ED.docx` son ambos el primer avance, de materias distintas. | ➖ | |

## 3. Observaciones técnicas y de datos

| # | Fecha | Tema | Observación | Estado | Cómo se atendió |
|---|---|---|---|---|---|
| T1 | 23 oct 2026 | Normas de IA | La planeación de **Estructuras de Datos prohíbe la IA generativa** (motivo de cancelación). Actualización 26 oct: la docente lo autorizó con crédito (ver D3). Las demás materias permiten IA como apoyo documentado. | ➖ | |
| T2 | 23 oct 2026 | Fase 0 | La percepción inicial debe escribirse y fecharse **antes** de ver resultados del modelo; si no, el contraste percepción vs. evidencia pierde validez. | ⬜ | |
| T3 | 23 oct 2026 | Datos | La base maestra no trae calle, severidad ni fecha de cierre. Se usa la celda de cuadrícula como unidad espacial y la severidad es sintética. | 🟡 | Declarado como limitación; pendiente cargar red vial (OSM / INEGI). |
| T4 | 23 oct 2026 | Datos | El nombre de la base dice 2019-2024 pero solo contiene 2019-2022. | ⬜ | Confirmar si existen datos de 2023-2024. |
| T5 | 23 oct 2026 | IPU | Cinco criterios (riesgo de accidente, personas afectadas, transporte, tránsito, vulnerabilidad) usan 0.5 neutro por falta de fuentes. Así el IPU depende sobre todo de la severidad, que es sintética. | ⬜ | Cargar ATUS, GTFS, CONAPO y aforos de referencia. |
| T6 | 23 oct 2026 | IPU | Los pesos (0.20, 0.20, 0.15…) son ilustrativos; falta justificarlos. | ⬜ | Decidir método: consenso del equipo o AHP. |
| T7 | 23 oct 2026 | Hallazgo | En temporada de lluvias hay casi el doble de reportes por mes (~1,147) que en secas (~603). Útil para Probabilidad (tasa Poisson por temporada) y para planear brigadas. | ➖ | |
| T8 | 23 oct 2026 | Hallazgo | Tláhuac (32%), Tlalpan (26%) y Álvaro Obregón (24%) turnan más reportes a otras áreas. Posible cuello de botella; útil para el plan de viabilidad. | ➖ | |
| T9 | 23 oct 2026 | Hallazgo | Milpa Alta tiene solo 133 reportes en 4 años. Puede ser poca participación digital, no pocos baches: justifica el peso acotado de los reportes en el IPU (sesgo). | ➖ | |
| T10 | 23 oct 2026 | SQL Server | Si se ejecutan los scripts con sqlcmd, `QUOTED_IDENTIFIER` debe estar activo (ya está incluido en cada script). En SSMS viene activo por defecto. | ✅ | Agregado al inicio de los scripts. |
| T11 | 23 oct 2026 | SQL Server | El script de carga usa una ruta absoluta al CSV. En otra computadora hay que cambiar `@archivo` en `03_carga_base_maestra.sql` y `@carpeta` en `06_carga_chalco.sql`; si marca «Access is denied», copiar el CSV a `C:\SIPA\`. | ➖ | |
| T12 | 23 oct 2026 | Datos Chalco | Solo 75 reportes de bacheo en 17 meses: no alcanza para calibrar modelos. El modelo se calibra con CDMX y Chalco es caso piloto. Que haya tan pocos reportes es en sí un argumento: los reportes no reflejan todos los baches. | ➖ | |
| T13 | 23 oct 2026 | Datos Chalco | El CSV mezcla codificaciones (UTF-8 y Windows-1252) y nombres de comunidad que no coinciden con el Bando 2026. | ✅ | Corregido en `procesar_chalco.py` (17 comunidades). |
| T14 | 23 oct 2026 | Datos Chalco | El polígono municipal del atlas es aproximado: 5 reportes de San Marcos Huixtoco caían fuera aunque sí son de Chalco. | ✅ | Tolerancia de 1 km; se conservan como `ubicacion_dudosa`. |
| T15 | 23 oct 2026 | Datos Chalco | En el Atlas de Riesgo 2023, las capas de fracturas, deslizamientos y accidentes carreteros están vacías. | ➖ | Buscar en el Atlas de Riesgos 2025 (PDF) o en ATUS. |
| T16 | 23 oct 2026 | IPU | Ningún bache abierto de Chalco cae dentro de una zona inundable; 6 están a menos de 200 m. Las zonas suman solo 1.3 km², podrían estar subestimadas. | ⬜ | Contrastar con el Atlas de Inundaciones CAEM 2025. |
| T17 | 23 oct 2026 | DW | Las 300 órdenes de trabajo del DW son simuladas (fechas, tiempos y cumplimiento de meta ilustrativos). Hay que declararlo en la entrega. | ➖ | |
| T18 | 23 oct 2026 | SQL Server | `sp_asignar_orden` tomaba siempre la primera brigada libre, así que las nocturnas nunca trabajaban. | ✅ | Ahora elige la brigada disponible con menos órdenes. |
| T19 | 23 oct 2026 | Hallazgo | Baches entre los 50 con más reportes quedan después del lugar 1,000 por IPU. Evidencia de que reportes ≠ prioridad (útil para Pensamiento Complejo y el plan de viabilidad). | ➖ | Consulta P4 en `11_dw_consultas_olap.sql`. |
| T20 | 23 oct 2026 | Rúbrica BD | La rúbrica 3 pide «aplicación de replicación» (15%), no solo una propuesta. | ✅ | `bd/12_replicacion.sql`: réplica de solo lectura por log shipping, probada. |
| T21 | 23 oct 2026 | Replicación | El log shipping copia toda la base, incluidos los datos personales (`priv`). | ✅ | Protegido por permisos: `rol_tablero` con DENY sobre `priv`, comprobado en la réplica. |
| T22 | 23 oct 2026 | Replicación | Cada ejecución de `12_replicacion.sql` agrega un reporte de prueba en Chalco Centro a la base principal. | ➖ | No afecta si se reconstruye todo con `ejecutar_todo.ps1`. |
| T23 | 23 oct 2026 | Cálculo | El factor de lluvias correcto es 1.80 (CDMX sin periodos atípicos), no 1.90 como se dijo antes con todos los datos. | ✅ | Se usa 1.80 en el modelo. |
| T24 | 23 oct 2026 | Cálculo | El crecimiento exponencial solo es válido a corto plazo (meses): un bache no crece sin límite. | ➖ | Declarado; mejora posible con modelo logístico (también es ecuación diferencial). |
| T25 | 23 oct 2026 | Cálculo | La planeación solo trae la síntesis del incidente; no tenemos el documento con sus preguntas específicas. | ⬜ | Si la docente dio preguntas guía, revisarlas contra el documento. |
| T26 | 23 oct 2026 | Hallazgo | Esperar 6 meses de lluvias para reparar los 1,344 baches pendientes cuesta $2.4 M más que hacerlo hoy. Argumento financiero para el enfoque preventivo (útil en Contabilidad y el plan de viabilidad). | ➖ | |
| T27 | 26 oct 2026 | Datos de accidentes | Los accidentes de la SSC casi se duplican a partir de julio de 2019 y siguen altos en noviembre y diciembre (secas): parece un cambio en el registro, no un efecto de la lluvia. | ➖ | Declarado en el documento de Probabilidad; no se usa para medir la temporada. |
| T28 | 26 oct 2026 | Probabilidad | El riesgo relativo de 1.38 (celdas con baches contra sin baches) es asociación, no causalidad: el tránsito puede explicar parte. | ➖ | Declarado como limitación; se separaría con datos de aforo. |
| T29 | 26 oct 2026 | Contabilidad | La provisión del esquema reactivo depende sobre todo del supuesto de ponchaduras (79 % del total). | ➖ | Se agregó sensibilidad: aun sin ponchaduras, el preventivo ahorra $3.9 M. |

