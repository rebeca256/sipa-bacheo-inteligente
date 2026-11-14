# SIPA · Bitácora de avances

Las observaciones (docentes, equipo, datos) van en [`OBSERVACIONES.md`](OBSERVACIONES.md).

Registro de los cambios y avances del proyecto **SIPA (Sistema Inteligente de Priorización Asfáltica)**, problema prototípico «Bacheo inteligente y priorización urbana» · UNRC · LCDN 3er semestre · 2026-2.

**Próxima entrega (todas las materias):** a más tardar el **1 de noviembre de 2026**.

---

## Estado general por fase

Fases según la sección 11 de `SIPA_Propuesta_Arquitectura.docx`.

| Fase | Descripción | Estado |
|---|---|---|
| 0. Percepción inicial | Propuesta de intervenciones del equipo, fechada, **antes** de ver resultados | ⬜ Pendiente (urgente) |
| 1. Diseño | MER, modelo relacional, criterios del IPU | ✅ Hecho (pesos del IPU aún ilustrativos) |
| 2. Datos | Base en SQL Server, datos sintéticos, carga | ✅ Hecho |
| 3. Núcleo algorítmico | Lista enlazada, hash/AVL, heap, grafo, Dijkstra (Python) | ⬜ Pendiente (lo escribe el equipo, sin IA) |
| 4. Modelos | Poisson, degradación, IPU, NIF C-9, simulación FIFO vs. SIPA | 🟡 Degradación (Cálculo) e IPU hechos; faltan Poisson, NIF C-9 y simulación FIFO |
| 5. Integración | Tablero, Data Warehouse y datamarts | 🟡 DW y datamarts hechos; falta tablero |
| 6. Viabilidad | Contraste percepción vs. evidencia, costo-beneficio | ⬜ Pendiente |

## Estado por materia (2ª entrega)

| Materia | Qué piden | Estado |
|---|---|---|
| Fundamentos de Bases de Datos | Desarrollo del proyecto y que se vea plasmado en la planeación | ✅ Todo hecho (base, DW, datamarts, OLAP, fragmentación, replicación, documento); solo falta insertar las imágenes de los diagramas en el .docx |
| Estructuras de Datos | Prototipo funcional de la plataforma y plan de viabilidad (listas, árboles, búsqueda, ordenamiento) | 🟡 Prototipo y plan de viabilidad hechos (IA autorizada con crédito); falta la Fase 0 del equipo en la sección 2 del plan |
| Probabilidad | Incidente: «¿Qué vialidad debe atenderse primero?» Semáforo de prioridad y riesgo de siniestro a 72 h | 🟡 Modelo y documento hechos; falta que el equipo lo revise |
| Cálculo Integral | Incidente: degradación acumulada del asfalto (avances 20%) | 🟡 Documento y modelo hechos; confirmar con la docente qué formato pide |
| Contabilidad Financiera | Incidente: pasivos contingentes (NIF C-9), del mantenimiento reactivo a la inversión preventiva | 🟡 Modelo, libro contable y documento hechos; falta que el equipo lo revise |
| Pensamiento Complejo | Documento de estrategia de argumentación (PDF, 6-10 cuartillas, APA 7) más exposición | 🟡 Documento y PDF hechos; faltan matrículas, nombre de la persona docente y la exposición |

---

## Historial

### Septiembre 2026 · Primer avance
- `SIPA_Propuesta_Arquitectura.docx` (borrador 3): arquitectura completa del prototipo.
- `avance1_PP.docx` y `avance2_PP_incidente_ED.docx`: **ambos son el primer avance**, de materias distintas.
- `scripts/limpiar_base_maestra.py`: limpieza de la base maestra CDMX 2019-2022.
  - Salidas en `datos/limpios/`: 35,629 registros válidos, 114 excluidos, bitácora de limpieza y catálogo de estatus.

### 23 oct 2026 · Base de datos (Fundamentos de Bases de Datos)
Carpeta nueva `bd/`, probada en SQL Server 2025 (`localhost`):

| Archivo | Contenido |
|---|---|
| `01_crear_bd.sql` | 32 tablas (hoy 34) en 3FN, llaves primarias y foráneas, CHECK, UNIQUE, índices; esquema `priv` para datos personales |
| `02_catalogos.sql` | Catálogos, 8 criterios del IPU, usuarios y materiales de prueba |
| `03_carga_base_maestra.sql` | Carga de 35,629 reportes → 16 alcaldías, 1,642 colonias, 8,323 celdas; pesos iniciales del IPU |
| `04_datos_sinteticos.sql` | 1,627 baches (uno por celda, oct-dic 2022), 32 brigadas, 16 almacenes, inventario, presupuesto 2026 |
| `05_procedimientos_transacciones.sql` | `sp_registrar_reporte`, `sp_calcular_ipu`, `sp_registrar_decision`, `sp_asignar_orden`, `sp_cambiar_estado_orden` |
| `06_demo_y_consultas.sql` (hoy `07_…`) | Flujo completo, ROLLBACK provocado y 7 consultas de análisis |
| `MER_SIPA.md` | Diagrama entidad-relación (Mermaid) + justificación de 1FN, 2FN y 3FN |
| `ejecutar_todo.ps1` | Reconstruye la base desde cero |

**Decisiones de diseño**
- La **celda** de la cuadrícula es la unidad espacial (la base maestra no trae calle); `tramo` queda listo para datos viales futuros.
- **Bache ≠ reporte**: varios reportes del mismo daño se ligan a un solo bache.
- 3FN: `anio`, `mes` y `alcaldia` no se guardan en `reporte` (se derivan). Los reportes sin colonia van a "SIN COLONIA" de su alcaldía.
- Un supervisor debe aprobar toda prioridad; ajustar o rechazar exige justificación (CHECK).

**Hallazgos de las consultas** (datos reales)
- En temporada de lluvias hay ~1,147 reportes/mes contra ~603 en secas (casi el doble).
- Tláhuac (32%), Tlalpan (26%) y Álvaro Obregón (24%) son las alcaldías con más reportes turnados.

**Limitaciones a declarar**
- Severidad, costos, brigadas y presupuesto son **sintéticos**.
- En el IPU, los criterios de riesgo de accidente, personas afectadas, transporte, tránsito y vulnerabilidad usan **0.5 (valor neutro)** hasta cargar sus fuentes.

**Problemas resueltos durante las pruebas**
- Conflicto de collation entre tablas temporales y la base → se usa la collation del servidor.
- `UNIQUE` en SQL Server solo admite un NULL → índice único filtrado para `folio_origen`.
- sqlcmd trae `QUOTED_IDENTIFIER OFF` → se activa al inicio de cada script.

### 23 oct 2026 · Documentos del docente de Pensamiento Complejo y datos de Chalco
**Revisión de 5 documentos propuestos por el docente** (PDF en la raíz del proyecto):
- *Priorización vial y conservación preventiva en Chalco*: muy útil. Propone un índice 0-100 con **inundación y drenaje** y **acceso a servicios**, criterios que nuestro IPU no tenía, además de reincidencia, causa probable e indicadores.
- *Drenaje pluvial* y *Suelo, subsuelo y pavimentación*: útiles como contexto (el agua y el subsuelo arcilloso explican la reincidencia).
- *Historia de la carretera México–Cuautla*: contexto y ejemplo para distinguir hecho, interpretación y dato no localizado.
- *Fosas sépticas en zonas inundables*: no aplica a SIPA.

**Portal de datos abiertos de Chalco** (datosabiertos.chalco.gob.mx) — funciona. Originales en `datos/chalco/originales/`:
- Reportes de bacheo 2025-2026: solo **75 reportes**, sin calle ni severidad.
- Atlas de Riesgo 2023 (KML): 23 zonas inundables, hospitales, mercados, escuelas, límite municipal. Capas de fracturas y accidentes **vacías**.
- Catálogo de escuelas (473, con alumnos) y comunidades del Bando 2026 (55).

**Integración de Chalco como segundo territorio**
- `scripts/procesar_chalco.py` → `datos/chalco/limpios/`: corrige codificación mixta (UTF-8/Windows-1252), normaliza comunidades contra el Bando 2026 (17 corregidas), excluye 6 sin coordenadas y 1 a más de 1 km del municipio, marca 6 como ubicación dudosa (cerca del límite), 6 posibles duplicados; misma cuadrícula de 250 m que la CDMX. Resultado: **68 reportes válidos**.
- Base de datos:
  - Nuevas tablas `zona_inundable` (polígonos `GEOGRAPHY`) y `equipamiento` (escuelas, hospitales, mercados); `colonia` gana `clave_oficial` y `tipo_asentamiento`.
  - Nuevos criterios del IPU: `INUNDACION` y `ACCESO_SERVICIOS`. Pesos **v2** (10 criterios) vigentes desde el 23 oct; los v1 se conservan para comparar.
  - `sp_calcular_ipu` v0.2: usa `STDistance` (dentro de zona inundable = 1, a menos de 200 m = 0.5) y equipamiento a menos de 500 m. Si el territorio no tiene la fuente, usa 0.5.
  - `06_carga_chalco.sql`: carga todo y calcula el IPU de los **18 baches abiertos** de Chalco. La demo pasó a `07_demo_y_consultas.sql`.
- Resultado: 6 de los 18 baches están a menos de 200 m de una zona inundable; ninguno queda dentro. 11 en amarillo y 9 en verde (incluye 2 de la demo de la CDMX).

### 23 oct 2026 · Data Warehouse (Fundamentos de Bases de Datos, unidad 4)
| Archivo | Contenido |
|---|---|
| `bd/08_simular_operacion.sql` | Historial operativo **simulado** con los procedimientos reales: IPU de los 1,645 baches, 300 aprobados (1 de cada 10 ajustado por el supervisor), asignados y cerrados; fechas repartidas en 2026 |
| `bd/09_dw_crear.sql` | Base `SIPA_DW`: 7 dimensiones, 3 hechos (reporte, priorización, orden), `fact_reporte` **particionada por año**, datamarts `dm_priorizacion` y `dm_financiero` (7 vistas) |
| `bd/10_dw_etl.sql` | `dw.sp_etl_cargar`: ETL completo en una transacción, con bitácora (~8 s) |
| `bd/11_dw_consultas_olap.sql` | ROLLUP, CUBE, GROUPING SETS, PIVOT, drill-down, slice/dice, ventanas y consultas a los datamarts |
| `bd/DW_SIPA.md` | Diagrama en estrella, ETL, datamarts, OLAP, fragmentación y propuesta de replicación |

- `sp_asignar_orden` ahora reparte la carga: elige la brigada disponible con menos órdenes.
- `ejecutar_todo.ps1` reconstruye todo (SIPA + SIPA_DW) en ~1 minuto.

**Hallazgos**
- Percepción vs. evidencia: varios baches entre los 50 con más reportes quedan después del lugar 1,000 por IPU (por ejemplo, en Coyoacán, Iztacalco y Tlalpan). Más reportes no siempre significa más prioridad: es un buen argumento para el plan de viabilidad.
- El supervisor cambió la recomendación del modelo en 31 de 301 casos (amarillo → rojo; incluye el de la demo), y queda registrado.

### 23 oct 2026 · Documento de entrega de Bases de Datos
- `avance2_BD_planeacion.docx` (6 páginas), generado con `scripts/generar_doc_planeacion_bd.py`: portada del equipo, mapa tema → producto → evidencia, cumplimiento **criterio por criterio** de las 3 rúbricas de la planeación, resultados, vinculación con el modelo educativo, limitaciones y anexo de archivos.
- Estado frente a las rúbricas: todo cumplido excepto **«Aplicación de replicación» (15% de la rúbrica 3)**, que solo está como propuesta.

### 23 oct 2026 · Replicación (cierra la rúbrica 3 de Bases de Datos)
- `bd/12_replicacion.sql`: réplica de solo lectura **`SIPA_REPLICA` por log shipping**. SIPA pasa a modelo FULL, se respalda y se restaura en STANDBY; `dbo.sp_replicar` envía y aplica el log; bitácora en `dbo.replicacion_bitacora`.
- Demostración comprobada: el reporte nuevo llega a la réplica solo tras `sp_replicar`; la réplica rechaza escrituras; `rol_tablero` lee `dbo` pero se le niega `priv` (datos personales).
- Actualizados `DW_SIPA.md`, `ejecutar_todo.ps1` (ahora crea SIPA, SIPA_DW y SIPA_REPLICA) y `avance2_BD_planeacion.docx`: **los 18 criterios de las 3 rúbricas quedan cumplidos**.

### 23 oct 2026 · Cálculo Integral (incidente: degradación acumulada del asfalto)
- `calculo/degradacion.py`: modelo r(t,W) = a·(W/W₀)⁴·e^(kt) con a = k·V₀. Lee la base SIPA y genera en `calculo/resultados/` 5 gráficas, 5 tablas y `resumen.json`.
  - **k de lluvias calibrada con datos reales**: 1.80 veces la de secas (reportes/mes CDMX sin periodos atípicos). k secas = 0.08 (supuesto), k lluvias = 0.144.
  - Temas aplicados: ecuación diferencial dV/dt = kV, integral indefinida con cambio de variable, integral definida y TFC, sumas de Riemann (izq./der./punto medio), teorema del valor medio, aditividad (año por tramos), valor presente, optimización con A′(T) = 0, ley de la cuarta potencia.
- `avance2_Calculo_degradacion.docx` (9 páginas), generado con `scripts/generar_doc_calculo.py`.

**Resultados**
- Bache típico (1.71 m² × 9.8 cm): en 6 meses de lluvias pierde 0.185 m³; su reparación pasa de $1,055 a $2,499.
- 1,344 baches pendientes de SIPA: repararlos hoy cuesta $1.75 M; esperar 6 meses de lluvias cuesta **$2.40 M más**.
- Esperar no conviene ni con valor presente (k > δ). Intervalo preventivo óptimo ≈ 28 meses (k promedio anual).

### 26 oct 2026 · Probabilidad (incidente: semáforo de prioridad y riesgo a 72 h)
- `probabilidad/riesgo_72h.py`: cruza 30,654 accidentes de la SSC (2018-2019) con los reportes de baches en la cuadrícula de 250 m. Genera 6 gráficas, 7 tablas y `resumen.json` en `probabilidad/resultados/`. Se volvió a ejecutar y los resultados se reproducen idénticos.
  - Cubre las 4 unidades: condicional, chi cuadrada, probabilidad total, Bayes y conteo; variable aleatoria; Bernoulli, binomial, Poisson, binomial negativa, geométrica y aproximación de Poisson; exponencial, gamma, uniforme, normal, TLC y t de Student.
  - Modelo: N ~ Poisson(λ·RR·3/365) con λ por Bayes empírico gamma-Poisson (los datos tienen sobredispersión: Var/E ≈ 4) y RR = 1.38.
- `avance2_Probabilidad_semaforo72h.docx` (11 páginas), generado con `scripts/generar_doc_probabilidad.py`.

**Resultados**
- Semáforo: 1,727 celdas en rojo (P ≥ 3 %), 2,760 en amarillo y 5,025 en verde.
- Bache profundo en vía rápida: P(accidente en 72 h) mediana de 3.1 % (8.6 % en el percentil 90), P(accidente grave) muy baja y unas 36 ponchaduras esperadas (escenario).
- De los 1,344 baches pendientes, el semáforo a 72 h coincide con el del IPU solo en el 36 %, y 285 están en rojo por riesgo sin estar en rojo en el IPU. Esto pasa porque el criterio RIESGO_72H del IPU usa 0.5 neutro: el modelo puede llenarlo con `v_riesgo_72h`.

### 26 oct 2026 · Contabilidad Financiera (incidente: provisiones NIF C-9)
- `contabilidad/provisiones.py`: estima la provisión por reclamaciones de cada uno de los 1,344 baches pendientes, usando el riesgo a 72 h (Probabilidad) y los costos de reparar (Cálculo), y la clasifica según la NIF C-9 (probable, posible o remota). Compara el esquema preventivo (según el semáforo) con el reactivo (180 días).
  - Arma la contabilidad de un ejercicio de la Unidad de Bacheo: 10 asientos, esquemas de mayor, balanza, estado de resultados, balance general y flujo de efectivo (método indirecto). Verifica que todo cuadre cada vez que se ejecuta.
  - `contabilidad/resultados/libro_contable.xlsx` con todas las hojas.
- `avance2_Contabilidad_NIF_C9.docx` (11 páginas), generado con `scripts/generar_doc_contabilidad.py`: NIF C-9, cuadro comparativo NIF C-9 / NIC 37 / CONAC, aspectos fiscales (IVA no acreditable) y control interno.

**Resultados**
- Costo total para el erario: preventivo $1.91 M, reactivo $11.76 M; ahorro de $9.85 M. Sin contar ponchaduras, el ahorro sigue siendo de $3.91 M.
- Los 56 baches profundos en vía rápida son los únicos «probables» por sí solos; en el esquema reactivo aparecen además 82 pasivos contingentes.
- Con el esquema reactivo, la misma asignación de $6 M no alcanza: Bancos terminaría en −$2.95 M.
- Los porcentajes de reclamación y los montos son supuestos; hay que calibrarlos con expedientes reales de responsabilidad patrimonial.

### 26 oct 2026 · Pensamiento Complejo (estrategia de argumentación)
- `pensamiento/mapa_red.py`: mapa de red de 17 agentes (intercambios y conflictos) y diagrama de 3 ciclos de retroalimentación (reactivo, invisibilidad de zonas con pocos reportes, círculo virtuoso de SIPA).
- `avance2_PensamientoComplejo_argumentacion.docx` y `.pdf` (12 páginas con carátula y referencias, ~2,600 palabras, APA 7), generado con `scripts/generar_doc_pensamiento.py`. Cubre los 8 criterios de la planeación: síntesis, agentes, problemática de cada agente, mapa de red, estrategia de argumentación (Toulmin, lógico-formal, dialéctica con objeciones y réplicas), 10 habilidades blandas explicadas, estrategia de acuerdos en 5 fases (con pesos del IPU acordados por AHP) y reflexión metacognitiva.
- Pendiente del equipo: matrículas, nombre de la persona docente y la exposición oral.

### 26 oct 2026 · Estructuras de Datos (prototipo funcional)
- La docente autorizó el uso de IA con crédito y mención explícita. Cada archivo y el `README.md` lo declaran.
- `estructuras/`: implementa desde cero el diseño del avance: lista doblemente enlazada, tabla hash con rehash, árbol AVL, max-heap con actualización de prioridad, min-heap, cola FIFO, pila de decisiones (deshacer y rehacer), grafo con Dijkstra, DFS y vecino más cercano. 12 pruebas de correctitud pasan.
- `estructuras/experimentos.py` con los 34,945 reportes reales:
  - Búsqueda con todos los registros: lineal 754 µs (17,942 comparaciones), AVL 2.3 µs (14.5 comparaciones, altura 18), hash 2.9 µs (casi constante al crecer n).
  - Desduplicación completa en 1.4 s con 314,505 búsquedas, en lugar de 610 millones de comparaciones por pares: 1,064 duplicados y 2,152 reapariciones después de 30 días.
  - Simulación de julio de 2019 (15 reparaciones/día): con SIPA, el 100 % de los rojos se atiende en 3 días o menos (FIFO: 22 %), con la misma espera promedio total (7.7 días). Pero la brecha de espera entre alcaldías crece de 3.4 a 7.5 días (Cuajimalpa: 13 días); el envejecimiento β = 0.10 no alcanza en 30 días.
  - Rutas en Coyoacán: el vecino más cercano recorre 14.9 km contra 28.3 km en orden de prioridad (−47 %).

### 3 nov 2026 · Estructuras de Datos (plan de viabilidad, 2º producto)
- `estructuras/viabilidad.py`: simulación de 90 días (julio a septiembre de 2019) con 4 políticas (FIFO, SIPA β = 0.10, β = 0.30 y SIPA con cupo de antigüedad: un segundo max-heap con eliminación perezosa), barrido de capacidad, llegadas por temporada y catálogo de celdas con reincidencia. Salidas `v1`-`v5` y `viabilidad.json` en `estructuras/resultados/`.
- `avance2_ED_plan_viabilidad.docx` (8 páginas), generado con `scripts/generar_doc_viabilidad_ED.py`: contraste percepción vs. evidencia, análisis de riesgo y recursos, gestión de datos, viabilidad financiera, equidad, catálogo de 9 intervenciones, implementación, limitaciones y anexo con 15 celdas para reencarpetado.

**Resultados**
- Llegan 37.3 baches nuevos/día en lluvias y 22.5 en secas. Con 15 reparaciones/día la cola crece con cualquier política (unos 1,360 pendientes en 90 días); con 35/día quedan 32.
- La brecha entre alcaldías es sobre todo un problema de capacidad: con 15/día pasa de 6.8 días (FIFO) a 19.8 (SIPA); el cupo la baja a 16.5 y β = 0.30 casi no ayuda; con 35/día baja a 2.6. Los rojos se atienden al 100 % en todas las variantes de SIPA.
- 143 celdas con 3 o más reapariciones concentran 2,255 baches (6.7 %): candidatas a reencarpetado.
- Pendiente del equipo: transcribir la Fase 0 en la sección 2 y poner la fecha de entrega en la portada.

### 3 nov 2026 · Base de datos (riesgo a 72 h en el IPU, v0.3)
- `bd/05b_riesgo_72h.sql`: tabla `riesgo_celda_72h` cargada desde `probabilidad/resultados/t4_riesgo_72h_por_celda.csv` (8,301 celdas; se descartan 1,211 con accidentes pero sin reportes de bache). Se ejecuta después de `05` en `ejecutar_todo.ps1`.
- `sp_calcular_ipu` usa `v_riesgo_72h` de la celda en el criterio RIESGO_72H (si no hay dato, como en Chalco, se queda en 0.5). Versión del modelo: `v0.3`.

**Resultados** (1,646 cálculos de la demo y la simulación)
- Los 1,627 baches de CDMX tienen dato de riesgo. El riesgo promedio es 0.09-0.37 según la alcaldía (Cuauhtémoc el más alto), muy por debajo del 0.5 neutro, así que el IPU promedio baja unos 0.05 puntos.
- El semáforo cambia en 602 cálculos (37 %): los rojos pasan de 1 a 15 y los amarillos de 1,296 a 734. El IPU ahora distingue los baches en celdas con accidentes, en lugar de dejar casi todo en amarillo.
- Chalco no cambia (no hay datos de accidentes).

### 3 nov 2026 · Base de datos (vistas de indicadores)
- `bd/13_vistas_indicadores.sql` (esquema `ind`, se ejecuta al final de `ejecutar_todo.ps1`):
  - **Reincidencia:** `ind.sp_actualizar_reincidencia` clasifica cada reporte como NUEVO, DUPLICADO (< 30 días en el mismo punto de ≈ 11 m o sus 8 vecinos) o REAPARICION (≥ 30 días), con la misma regla que `estructuras/sipa_ed.py`, y lo guarda en `ind.reporte_reaparicion`. Vistas `v_reincidencia_celda` (UNICA, REINCIDENTE, CRONICA con ≥ 3 reapariciones) y `v_reincidencia_territorio`. Se guarda en tabla porque como vista tardaba más de 5 minutos; así tarda 3.5 s.
  - **Tiempo de respuesta:** `v_tiempo_respuesta_orden`, `_semaforo` y `_territorio` (días de atención y % dentro de la meta de 3, 15 o 60 días).
  - **Cobertura:** `v_cobertura_territorio` (baches priorizados, con orden y reparados, y antigüedad de los pendientes) y `v_cobertura_reportes_anual` (% de reportes ciudadanos resueltos por año).

**Resultados**
- Reincidencia: 1,134 duplicados y 2,271 reapariciones; 161 celdas crónicas (en ED fueron 1,064, 2,152 y 143: la base incluye Chalco y los reportes sintéticos). Azcapotzalco concentra el 21.7 % de sus reportes en celdas crónicas.
- Tiempo de respuesta (simulado): rojos 3.3 días en promedio, 51 % en meta; amarillos 14.1 días, 60 % en meta.
- Cobertura: Cuauhtémoc tiene el 41 % de sus baches reparados y Tláhuac el 2 %. Los reportes resueltos bajan de 97.5 % (2019) a 67.9 % (2022).

### 4 nov 2026 · Base de datos (causa probable del daño)
- En `bd/13_vistas_indicadores.sql`, vistas `ind.v_causa_probable_bache` y `ind.v_causa_probable_territorio` (propuesta del docente). La base no registra la causa, así que se infiere con tres indicios:
  - **Agua:** a 200 m o menos de una zona inundable (solo Chalco tiene atlas), o al menos 80 % de los reportes de la celda en temporada de lluvias (promedio 68.5 %) con 5 reportes o más.
  - **Carga:** la celda está sobre una vía rápida (`riesgo_celda_72h`).
  - **Estructural:** celda crónica (3 reapariciones o más).
- Cada causa trae una intervención sugerida (reencarpetado, sello y revisión del drenaje, mezcla de alto desempeño o bacheo convencional con inspección). Es una hipótesis para orientar la inspección, no un diagnóstico.

**Resultados** (1,646 baches)
- Estructural 73, agua 277, agua y carga 36, carga 121; sin indicios 1,139 (69 %).
- Cuauhtémoc (44.5 %) y Miguel Hidalgo (43.6 %) tienen más baches con causa identificada; Azcapotzalco tiene la mayor cantidad de causa estructural (16).
- Para mejorar: registrar la causa en la inspección de campo y cargar el atlas de riesgo de inundación de la CDMX.

### 4 nov 2026 · Base de datos (imágenes del MER y del DW)
- `bd/img/MER_SIPA.png` y `bd/img/DW_SIPA.png`, generadas con mermaid-cli desde los bloques de `bd/MER_SIPA.md` y `bd/DW_SIPA.md` (ya incluyen `riesgo_celda_72h`). Se regeneran con `bd/img/generar_imagenes.ps1`.
- Insertadas en `avance2_BD_planeacion.docx` como figuras 1 (MER, en la rúbrica 3.1) y 2 (DW, en la rúbrica 3.3).

### 4 nov 2026 · Pesos del IPU (plantilla de AHP)
- `pesos/AHP_pesos_IPU.xlsx`, generado con `scripts/generar_matriz_ahp.py`: plantilla de AHP de Saaty para los 10 criterios del IPU.
  - Cada integrante llena una hoja `Evaluador_1` a `_4`: 45 comparaciones por pares (cuál importa más y cuánto, de 1 a 9). La matriz recíproca, los pesos (media geométrica) y la razón de consistencia (RC ≤ 10 %, RI = 1.49) se calculan solos.
  - `Consolidado`: combina a los evaluadores incluidos con la media geométrica de cada comparación (AIJ), compara con v1 y v2 y arma las líneas SQL para `peso_criterio`.
  - `Ejemplo`: llenado a partir de los pesos v2 (RC 0.4 %). Muestra que la escala entera de Saaty comprime las diferencias: v2 da 15 % / 10 % / 5 %; el ejemplo, 13 % / 11.5 % / 5.1 %.
- Verificado en Excel: 0 errores de fórmula; con un solo evaluador incluido, el consolidado da los mismos pesos que su hoja.
- Pendiente del equipo: llenar las hojas, discutir las diferencias con v2 y cargar los pesos.

### 5 nov 2026 · Fuentes reales descargadas (GTFS y marginación)
- `datos/gtfs/originales/gtfs.zip`: GTFS de la CDMX (SEMOVI, Datos Abiertos CDMX, edición de oct 2021), con rutas, paradas, recorridos y frecuencias de Metro, Metrobús, Trolebús, RTP, Tren Ligero, Cablebús, Suburbano y concesionados. Para el criterio TRANSPORTE.
- `datos/marginacion/originales/im_colonia_cdmx.geojson`: índice de marginación urbana 2020 de CONAPO para 2,243 colonias de la CDMX, con polígono (capa `im_colonia` del SIEG CDMX). Para el criterio VULNERABILIDAD. Grados: 453 muy bajo, 1,092 bajo, 558 medio, 93 alto y 47 muy alto.
- Cada carpeta tiene un `FUENTE.md` con la URL, la fecha de descarga, los campos y las limitaciones.
- No se descargó ATUS: Probabilidad ya usa los hechos de tránsito de la SSC, que traen coordenadas (ATUS solo llega a nivel municipio).
- Falta: integrarlos a la base y al IPU, y conseguir los datos equivalentes para Chalco.

### 6 nov 2026 · IPU v0.4 (transporte público y marginación reales)
- `scripts/procesar_fuentes_ipu.py`: convierte el GTFS en `datos/gtfs/limpios/paradas.csv` (10,961 paradas con rutas y salidas por día, calculadas con `frequencies.txt`) y el GeoJSON de CONAPO en `datos/marginacion/limpios/colonias_marginacion.csv` (2,243 polígonos en WKT).
- `bd/05c_transporte_marginacion.sql` (corre después de `05b`): tablas `parada_transporte`, `marginacion_colonia` (con índices espaciales) y `contexto_celda`, para las 8,280 celdas de la CDMX:
  - `v_transporte` = LOG(1 + salidas/día de las paradas a 300 m o menos) / LOG(1 + p95); el p95 es 11,415 salidas/día. Vale 0 donde no pasa transporte público.
  - `v_vulnerabilidad` = (IMN máx − IMN) / (IMN máx − IMN mín) de la colonia que contiene el centro de la celda (o la más cercana a 250 m o menos).
- `sp_calcular_ipu` usa ambos valores (sin dato, como en Chalco, siguen en 0.5). Versión del modelo: `v0.4`.

**Resultados**
- 6,170 celdas tienen transporte a 300 m o menos; 8,264 quedan asignadas a una colonia de CONAPO (16 sin colonia).
- Promedios en los 1,646 cálculos: transporte 0.60 y vulnerabilidad 0.24. El IPU promedio baja de 0.444 a 0.424, porque la mayoría de las colonias tienen marginación baja o muy baja.
- Contra v0.3 recalculado con los mismos baches: rojos 12 → 10, amarillos 743 → 511; cambia el semáforo en 246 cálculos (15 %).
- Advertencia para la discusión de pesos: el índice de CONAPO tiene un rango muy estrecho en la CDMX (0.868 a 0.995) y el reescalado con mínimo y máximo concentra casi todas las colonias abajo; solo 9 celdas tienen grado «Muy alto».
- Faltan: PERSONAS y TRANSITO (no hay aforos abiertos por tramo) y las fuentes equivalentes para Chalco.

---

## Pendientes

- [ ] **Fase 0:** el equipo escribe y fecha su percepción inicial (antes de ver resultados).
- [x] BD: Data Warehouse (esquema estrella) y datamarts de priorización y financiero.
- [x] BD: fragmentación horizontal implementada (por año) y propuesta de replicación y fragmentación por territorio (en `bd/DW_SIPA.md`).
- [x] BD: documento que relacione el proyecto con la planeación didáctica (`avance2_BD_planeacion.docx`).
- [x] BD: aplicar replicación (`bd/12_replicacion.sql`).
- [x] BD: insertar en el .docx las imágenes del MER y del DW (`bd/img/`).
- [ ] Confirmar qué pide cada una de las demás materias para la 2ª entrega.
- [x] Cargar fuentes reales: GTFS y marginación CONAPO integradas al IPU v0.4 (`bd/05c`); accidentes, los de la SSC. Faltan aforos (PERSONAS, TRANSITO) y Chalco.
- [ ] Definir los pesos definitivos del IPU: plantilla de AHP lista (`pesos/AHP_pesos_IPU.xlsx`); falta que el equipo la llene y comparar con v1, v2 y el índice del docente.
- [x] Agregar reincidencia y causa probable del daño (propuesta del docente). Falta el atlas de inundación de la CDMX.
- [x] Cargar `v_riesgo_72h` (de `probabilidad/resultados/t4_riesgo_72h_por_celda.csv`) al criterio RIESGO_72H del IPU en la base SIPA.
- [x] Estructuras de Datos: plan de viabilidad y propuesta de intervenciones (`avance2_ED_plan_viabilidad.docx`). Falta transcribir la Fase 0.
- [x] Estructuras de Datos: cupo de antigüedad probado; la brecha se resuelve sobre todo con capacidad (ver `estructuras/viabilidad.py`).
- [x] Vistas de indicadores: reincidencia, tiempo de respuesta, cobertura (`bd/13_vistas_indicadores.sql`).

## 6 nov 2026 · Documento de entrega de BD para la docente
- Nuevo `scripts/generar_doc_entrega_bd.py` → `avance2_BD_entrega.docx`: versión en prosa para entregar (introducción, datos, MER, modelo relacional y 3FN, implementación física, transacciones, DW y datamarts, fragmentación y replicación, resultados, conclusiones). Sin tablas de rúbricas.
- `avance2_BD_planeacion.docx` queda como control interno del equipo (cumplimiento por rúbrica).

## 6 nov 2026 · Cambio de alcance: SIPA como sistema de asesoría (propuesta del equipo)
- SIPA recomienda qué atender, por qué y cuánto costaría; la reparación es de la autoridad.
- Se quitaron de la base brigada, almacen, material, inventario, presupuesto, orden_trabajo, historial_orden, consumo_material, evidencia_reparacion y cat_estado_orden (respaldo de la versión anterior en `respaldo_alcance_v1/`).
- Nuevo: `datos/costos/tarifas_reparacion.json` → `tarifa_reparacion` (OPENJSON); `sp_calcular_ipu` elige intervención (superficial, profundo, con sello, reencarpetado) y estima costo.
- Nuevo: `seguimiento_bache` (avance que informa la autoridad), `sp_actualizar_estado_bache`, `sp_consultar_folio`; dos modos como roles `rol_ciudadano` y `rol_autoridad`; usuarios AUTORIDAD por territorio.
- Bug corregido: los CHECK de justificación aceptaban NULL (resultado desconocido); se agregó IS NOT NULL.
- DW: `fact_orden`/`dim_brigada` → `fact_atencion`/`dim_intervencion`; datamart financiero: costo estimado vs. reportado, `v_intervenciones`. Indicadores: tiempo de respuesta por bache y `ind.v_costo_pendiente_territorio` (1,345 baches abiertos ≈ $5.3 M).
- Base: 32 tablas, 39 FK, 56 CHECK. Reconstrucción completa sin errores. MER y DW regenerados.
- `avance2_BD_entrega.docx` reescrito al nuevo alcance (pendiente regenerar: el archivo estaba abierto en Word).
- Pendiente: los documentos de otras materias (Contabilidad, planeación BD interna) todavía mencionan brigadas/órdenes.

## 6 nov 2026 · Documentos de las otras materias alineados al alcance de asesoría
- Contabilidad: SIPA ya no guarda órdenes/consumos; control interno por costo reportado vs. estimado y seguimiento; la Unidad de Bacheo repara con sus brigadas y contrata la asesoría de SIPA.
- Pensamiento Complejo, Probabilidad, ED: "supervisor" → autoridad; brigadas como recomendación a la autoridad. Cálculo: costo de mezcla marcado como supuesto.
- Documento interno de BD (rúbricas): cifras y ejemplos actualizados (32 tablas, 39 FK, 56 CHECK, 32 PK, 16 DEFAULT, 9 UNIQUE).
- Regenerados los 6 .docx; avance2_BD_entrega.docx ya estaba al día.

## 6 nov 2026 · Costos unificados con las tarifas JSON
- `calculo/degradacion.py` usa `datos/costos/tarifas_reparacion.json`: C(T) = F + c_m2 · MAX((V0+P(T))/d, área mín.), con la tarifa que SIPA recomienda a cada bache. En T=0 coincide al centavo con `costo_estimado` de la base (diferencia máx. $0.00).
- Bache típico: $2,511 hoy, $3,895 tras 6 meses de lluvias. 1,345 baches abiertos: $5.32 M hoy, +$1.81 M si esperan 6 meses de lluvias.
- Se volvió a correr Probabilidad (su lista de pendientes era de una base anterior), Contabilidad (preventivo $5.45 M vs. reactivo $12.67 M; ahorro $7.22 M, mínimo $2.76 M sin ponchaduras) y ED (lee el costo del bache de Cálculo en lugar de constantes fijas).
- Regenerados los documentos de Cálculo, Contabilidad, Probabilidad, Pensamiento Complejo, ED y BD interno.

## 6 nov 2026 · Datos sintéticos reproducibles
- 04, 06 y 08 ya no usan NEWID(): severidad, profundidad, área, costo reportado y fechas salen de HASHBYTES('MD5') de la celda o del bache; los INSERT llevan ORDER BY para fijar los id. Dos reconstrucciones seguidas dan resultados idénticos.
- Con los datos fijos: 1,345 baches abiertos cuestan $4.61 M hoy (+$1.81 M si esperan 6 meses de lluvias); Contabilidad preventivo $4.74 M vs. reactivo $12.31 M (ahorro $7.57 M, mínimo $2.79 M); rojos 2.7 días (60 % en meta), amarillos 14.6 (52 %).
- Modelos (Probabilidad, Cálculo, Contabilidad, ED) y documentos regenerados con cifras actualizadas. avance2_BD_entrega.docx pendiente de regenerar (abierto en Word).

## 6 nov 2026 · Tablero del prototipo funcional (Streamlit)
- `tablero/app.py`: resumen y mapa, modo ciudadano (reportar, consultar folio), recomendación de SIPA (ranking, ficha del IPU, intervención y costo), modo autoridad (decidir e informar avance) e indicadores. Usa los procedimientos de la base; los errores de las restricciones se explican en español.
- Probado: las 5 páginas cargan sin errores; reportar, aprobar y reparar funcionan; ajustar sin justificación y descartar sin motivo se rechazan. Base restaurada después de las pruebas.
- Ejecutar: `streamlit run tablero/app.py`.

## 6 nov 2026 · Evidencia integradora (entregable final)
- `scripts/generar_entregable_final.py` → `entregable_final_SIPA.docx`: problema y alcance de asesoría; producto 1 (prototipo: 4 capas y capturas del tablero); producto 2 (plan de viabilidad, incisos a–e); catálogo de 9 intervenciones con evidencia técnica, financiera y social; integración interdisciplinaria; respuesta a los 6 dilemas; limitaciones; referencias; anexo de ejecución. Todas las cifras se leen de la base y de los resultados de los modelos.
- Capturas del tablero en `tablero/capturas/` (el tablero acepta `?p=0..4` para abrir cada sección). Corregidos el mapa (coordenadas Decimal) y el orden de las barras.
- Corregido el promedio de reportes en secas: 639/mes (base maestra, sin periodos atípicos), no 603; coincide con el factor de lluvias 1.80 de Cálculo. Actualizados BD entrega, BD interno y Pensamiento Complejo.
- Pendiente del equipo: sección 3.1 (percepción inicial, Fase 0) y el párrafo de conclusión del contraste; matrículas y fecha en la portada. Regenerar el PDF de Pensamiento Complejo.

## 6 nov 2026 · Pruebas de extremo a extremo del tablero (Playwright)
- `tablero/pruebas_e2e.py`: 7 pruebas en Chromium (resumen y mapa, reporte y folio, folio inexistente, recomendación y ficha, reglas y avance de la autoridad, indicadores, navegación). 7/7 pasan. Capturas en `tablero/capturas/pruebas/`.
- Errores encontrados y corregidos: la pantalla no se actualizaba después de guardar; texto técnico de Streamlit visible al consultar un folio; "None" en lugar de "Sin calcular"; formularios que conservaban datos al cambiar de bache; costos sin formato; gráficas en orden alfabético.
- Base reconstruida después de las pruebas. Pendiente menor: la métrica «Intervención» se corta en pantallas angostas.
- La métrica «Intervención» usa el nombre corto (el completo en la ayuda). Capturas del documento final retomadas con Playwright y entregable_final_SIPA.docx regenerado; pruebas 7/7; base restaurada.

## 7 nov 2026 · Proyecto en GitHub y tablero en GitHub Pages
- Repositorio público: https://github.com/rebeca256/sipa-bacheo-inteligente (sin los documentos de los docentes; ver `.gitignore`).
- Tablero en línea: https://rebeca256.github.io/sipa-bacheo-inteligente/ — corre en el navegador con stlite 1.12.1 (sin servidor). Usa la copia de solo consulta `tablero/datos/` (`scripts/exportar_datos_tablero.py`); el sitio se arma con `scripts/construir_sitio.py` en `docs/`.
- `tablero/app.py` detecta la fuente: SQL Server en local (todo se guarda) o la copia en línea (las reglas se revisan igual, nada se guarda).
- Pruebas: `tablero/pruebas_sitio.py` 5/5 contra el sitio publicado; `tablero/pruebas_e2e.py` 7/7 en local. Primera carga del sitio: unos 27 s.
- Corregido en `bd/08`: la validación simulada ahora queda antes de la decisión (antes salía después de la reparación).
- Para actualizar el sitio: reconstruir la base, `python scripts/exportar_datos_tablero.py`, `python scripts/construir_sitio.py`, commit y push.

## 7 nov 2026 · Entregables en PDF
- `pdf/`: los 10 entregables en PDF (`scripts/exportar_pdf.py`, mammoth + Chrome; la automatización de Word se bloquea en esta computadora). README con enlaces. Corregida la referencia a la sección 3.1 del entregable final. Se quitó del repositorio el PDF viejo de Pensamiento Complejo.

## 7 nov 2026 · Segundo avance de Estructuras de Datos, rehecho
- `avance2_ED_plan_viabilidad.docx` ahora es «Prototipo funcional y plan de viabilidad» y gira alrededor de las estructuras (lo que evalúa la UCA): el problema del FIFO, diagrama de clases (`estructuras/img/clases.png`), una sección por estructura con su código real (extraído del archivo con `ast`), complejidad y medición; decisión hash contra AVL con datos (el AVL resultó más rápido en µs y se explica por qué igual se elige la hash para duplicados); las 12 pruebas; resultados FIFO contra cola de prioridad; plan de viabilidad, contraste percepción-evidencia (pendiente del equipo) e intervenciones ligadas a cada estructura.
- Quitadas las partes viejas: cargar riesgo 72 h y GTFS (ya hechos), cifras escritas a mano, nombres sin acentos y la referencia dudosa.
- Los bloques de código usan el estilo «Codigo»; `scripts/exportar_pdf.py` los convierte en `<pre>` para que el PDF conserve la sangría (también en el documento de BD).

## 10 nov 2026 · Contabilidad: incidente «Contingencias por daños viales» (Estado de México)
- La docente pide datos del **Edomex** (PDF `tablero/AVANCES INCIDENTE CRITICO.pdf`; paso 1 se entrega el 19-11-2026).
- Datos descargados en `datos/edomex/`: INEGI ATUS 1997-2023 (se extrae el Edomex 2010-2023: 963 accidentes por «mala condición del camino»; 206 en 2023, con 10 fatales), INEGI vehículos registrados 2023 por municipio y la Ley de Responsabilidad Patrimonial del Edomex (art. 18: lesiones y muerte con la LFT).
- Parámetros con fuente: Metepec (200 reportes, 37 procedentes, hasta $10,000), rango de la docente ($3k-$40k), AMIS, TRIJAEM (81 % de sentencias favorables en 2021). Supuesto: % que reclama en accidentes graves.
- `contabilidad/contingencias_edomex.py`: valor esperado + Monte Carlo + reparto por municipio + asiento NIF C-9 al 31/12/2026. Resultados en `contabilidad/resultados_edomex/`.
- Resultado: ≈ 2,066 casos viables al año; provisión (valor esperado) $58.7 M; IC 90 % $45.9-$75.4 M; se revela como pasivo contingente $16.7 M (P95 − VE).
- `avance_Contabilidad_contingencias_Edomex.docx`, generado con `scripts/generar_doc_contingencias_edomex.py`.
- Pendiente: pedir por SAIMEX el registro de indemnizaciones (art. 9 de la ley) a Junta de Caminos y ayuntamientos para sustituir supuestos.

## 11 nov 2026 · Datos reales de Toluca en todas las materias
- Fuente: tablero público de bacheo de la DGOP de Toluca (https://dgop.toluca.gob.mx/tablero_bacheo_filtros1.php). Servicios: `ajax/buscar_tablero_bacheo.php` (tabla paginada), `ws/ListadoMarkers.php` (coordenadas), `ws/obtenerMarker.php?folio=` (largo, ancho, profundidad, fotos).
- `scripts/descargar_toluca.py`: 74,319 baches reparados (ene 2025 – nov 2026) y medidas de una muestra aleatoria de 1,500. `scripts/limpiar_toluca.py` → `datos/limpios/toluca_*.csv` (1,491 medidas válidas; mediana 3.6 m² y 7 cm; 39 % profundos).
- Contabilidad: costo real de reparar en Toluca 2025 ≈ $172 M (tarifas SIPA) frente a $3.1 M de provisión (sección 4.4).
- Probabilidad (`probabilidad/toluca.py`, sección 8.1): binomial de profundos, lognormal del área, t de Welch, Poisson vs binomial negativa (dispersión 128), IC del área media.
- Cálculo (`calculo/toluca.py`, sección 4.1): bache real vs simulado, P(6) exacta y Riemann, costo esperado como integral con densidad lognormal, mezcla de un año (≈ 39,900 t).
- BD: `bd/14_carga_toluca.sql` (esquema `ext`, 2 tablas y 3 vistas), agregado a `ejecutar_todo.ps1`; sección 9.1.
- ED (`estructuras/toluca_ed.py`, sección 6.1): prueba de escala con 74,319 baches (hash 767× más rápida que lista; AVL altura 19). Se conservaron los cambios manuales del equipo (fecha 13-11-2026 y declaración de IA).
- Pensamiento Complejo y entregable final: Toluca como evidencia de transparencia y siguiente piloto.
- Todas las entregas con fecha 13 de noviembre de 2026.

## 11 nov 2026 · Revisión visual del tablero
- Errores corregidos en `tablero/app.py`: el mapa del resumen no cargaba (`height` de pydeck y valores `Decimal` de SQL Server) y el costo estimado salía con ⚠.
- Gráficas: barras delgadas con el valor al final, altura según el número de barras, top 10 con interruptor "Ver todos" y un estilo común (`estilo()`, `barras()`, `ver_barras()`).
- "Reportes resueltos por año": barras solo de años con 500 reportes o más (2019–2022); se quitó la línea engañosa que caía a 0 en 2026.
- Tablas con nombres en español, costos con separador de miles y barras de porcentaje; métricas con títulos cortos y ayuda ("Rojo · amarillo", "Costo pendiente").
- Ficha de justificación: la tabla de criterios quedó en un desplegable para no repetir la gráfica.
- `pruebas_e2e.py` ajustado a Streamlit 1.67 (nombres de gráficas y avisos, selectores con reintento): 7/7 pasan. `pruebas_sitio.py`: 5/5. Sitio `docs/` reconstruido.

## 11 nov 2026 · Rediseño del tablero como portal ejecutivo (fases 1–3)
- Identidad: tema propio (`.streamlit/config.toml` y el mismo tema en el sitio stlite), banda superior azul marino con la marca SIPA, pestañas arriba en lugar de la barra lateral, tarjetas blancas para cada bloque y tipografía Inter.
- Cifras clave: tarjetas de KPI con contexto y estado ("Debajo de la meta"), y un hallazgo principal en Resumen e Indicadores.
- Gráficas: un solo azul para el dato principal, gris como contexto (el territorio elegido se destaca), colores del semáforo solo para el semáforo y etiquetas solo en las 3 barras principales. Tiempo de respuesta como barra contra la meta, reincidencia como gráfica (con la tabla en un desplegable) y causas como barra segmentada de 100 %. La paleta pasó el validador de daltonismo; el % va escrito en la leyenda por el aviso de contraste.
- El tablero local debe correrse con `python -m streamlit` (1.67): el comando `streamlit` de Anaconda es 1.32.
- Pruebas compatibles con Streamlit 1.32 y 1.67: e2e 7/7 y sitio 5/5. Base reconstruida y `docs/` regenerado.

## 11 nov 2026 · Rediseño del tablero, fase 4 (pulido por pantalla)
- Recomendación: filtros en una fila, semáforo con ícono y nombre en el ranking, ficha del bache como expediente (cabecera con lugar en el ranking, chips de semáforo y estado, cifras, datos del bache) y tarjeta "Por qué ocupa este lugar" con los tres criterios que más pesan.
- Autoridad: filtros en una fila, cifras del territorio, pasos 1 y 2 numerados con su estado.
- Tablas con el alto justo para ver todas las filas; cifras de las tarjetas sin cortar palabras en celular.
- Pruebas: e2e 7/7 y sitio 5/5; base reconstruida y `docs/` regenerado.

## 11 nov 2026 · Componentes shadcn/ui en el tablero local
- `streamlit-shadcn-ui` 1.5 (en `requirements.txt`): tarjetas de cifras (`ui.metric_card`) y pestañas de navegación (`ui.tabs`).
- Respaldo: si la librería no está (sitio en línea con stlite), se usan las tarjetas HTML y las pestañas propias; el sitio no cambia.
- Pruebas: e2e 7/7 (reconocen ambos tipos de tarjeta) y sitio 5/5. Base reconstruida y `docs/` regenerado.

## 12 nov 2026 · Tablero con estilo AdminLTE
- Se quitó streamlit-shadcn-ui. Estilo inspirado en AdminLTE 3 (plantilla MIT), hecho con CSS sobre Streamlit: menú lateral oscuro con íconos de Bootstrap Icons, barra superior con la ruta y el modo ("En vivo · SQL Server"), cifras en "small boxes" de color con ícono, tarjetas con borde superior y callout para el hallazgo.
- No se usó streamlit-option-menu: dibuja en un iframe y rompería las pruebas y el sitio stlite.
- Pruebas: e2e 7/7 y sitio 5/5; base reconstruida y `docs/` regenerado.

## 13 nov 2026 · Reporte de evidencia de conexión a SQL Server
- `scripts/evidencia_sql_server.py` genera `pdf/evidencia_sql_server.pdf` (5 páginas): datos del servidor (SQL Server 17, base SIPA, procedimientos), el tablero muestra el mismo conteo que `SELECT COUNT(*) FROM reporte`, un reporte enviado desde el tablero aparece como fila en la base y la cifra sube en 1, y la base rechaza AJUSTAR sin justificación sin guardar nada.
- Base reconstruida después de generarlo.
