# Auditoría técnica de SIPA

Revisión del 17 de noviembre de 2026 sobre el commit `14c1fe4`. Alcance técnico: instalación, tablero local y publicación estática, SQL Server, estructuras de datos y dependencias entre modelos y entregables. Los criterios de abajo describen cómo comprobar cada corrección.

## Prioridad alta

### C01 · Proteger la base durante la instalación y las pruebas

**Evidencia.** El comando de instalación del [README](README.md) ejecuta un orquestador que comienza eliminando `SIPA`. Más adelante elimina `SIPA_DW` y `SIPA_REPLICA`. Si falla una carga posterior, la base anterior ya se perdió y la instalación puede quedar incompleta. Además, las pruebas del tablero modifican la base y sugieren reconstruirla al terminar.

**Trabajo para Claude.** Separar inicialización, migración y reconstrucción de demostración. Antes de cualquier escritura, comprobar servidor, bases de destino y archivos requeridos. Para las pruebas, usar una base desechable con datos de prueba.

**Criterio de cierre.** Una instalación normal sobre una base existente conserva sus registros. Un archivo faltante detiene la ejecución antes de modificar bases. Ejecutar las pruebas dos veces deja intactos los datos operativos.

**Referencias.** [Orquestador](bd/ejecutar_todo.ps1#L3), [base operativa](bd/01_crear_bd.sql#L21), [DW](bd/09_dw_crear.sql#L21), [réplica](bd/12_replicacion.sql#L103), [E2E](tablero/pruebas_e2e.py#L8).

### C02 · Vincular la identidad de autoridad con el territorio y la escritura

**Evidencia.** El tablero local usa una conexión integrada compartida y la pantalla de autoridad toma el `id_usuario` del selector «Entrar como». Los procedimientos de decisión y seguimiento comprueban que el identificador corresponde a una autoridad activa. La identidad del operador y el territorio autorizado quedan sin verificar en esos procedimientos. El recálculo de IPU también está disponible desde el ranking.

**Trabajo para Claude.** Si se conserva la selección libre para la demostración académica, limitarla a un entorno de datos de prueba e identificarla como simulación. Para datos operativos, obtener la identidad de la sesión y aplicar en el servidor permisos por territorio y acción con una cuenta SQL de privilegios mínimos.

**Criterio de cierre.** Sin identidad autorizada, una escritura de autoridad se rechaza. Una autoridad de un territorio carece de permisos para decidir o actualizar baches de otro, y cada decisión registra al actor autenticado.

**Referencias.** [Conexión y ranking](tablero/app.py#L215), [selector de autoridad](tablero/app.py#L872), [decisiones y estados](bd/05_procedimientos_transacciones.sql#L200), [roles SQL](bd/05_procedimientos_transacciones.sql#L309).

### C03 · Evitar que reportes de baches distintos se fusionen

**Evidencia.** `sp_registrar_reporte` busca la celda más cercana en toda la cuadrícula y liga la solicitud al bache abierto más antiguo de esa celda de 250 m. Falta comprobar la distancia al bache, la concordancia de colonia o territorio y la antigüedad del reporte anterior. El prototipo de estructuras trabaja con un vecindario de aproximadamente 11 m y una ventana de 30 días. La regla operacional actual puede mezclar folios, conteos y seguimiento de incidentes independientes.

**Trabajo para Claude.** Definir una política de vinculación con territorio, distancia física y antigüedad. Alinear la regla entre el formulario, SQL y los experimentos, o documentar qué hipótesis evalúa cada implementación. En casos ambiguos, conservar la posibilidad de revisión.

**Criterio de cierre.** Dos puntos separados dentro de una celda generan casos independientes. Un duplicado cercano válido conserva el bache existente incluso en el borde entre celdas. Coordenadas ajenas a la colonia reciben una validación explícita.

**Referencias.** [Alta SQL](bd/05_procedimientos_transacciones.sql#L26), [formulario](tablero/app.py#L760), [prototipo de estructuras](estructuras/sipa_ed.py#L74), [clasificación de reincidencia](bd/13_vistas_indicadores.sql#L63).

### C04 · Corregir la interpretación causal del riesgo y su propagación a costos

**Evidencia.** El `RR` se calcula comparando tasas medias de celdas con y sin reportes en 2019. El modelo multiplica por ese cociente una tasa base que ya recoge los accidentes observados en cada celda, incluidas las celdas con reportes. Hay riesgo de contabilizar dos veces la asociación. Luego publica `1 − 1/RR` como fracción atribuible al bache y Contabilidad usa ese valor para calcular reclamaciones esperadas. El diseño actual estima una asociación territorial sin aislar factores como el aforo o la propensión a reportar.

**Trabajo para Claude.** Revisar la aplicación de `RR` y calibrar el pronóstico con un corte temporal independiente. En los documentos, presentar la fracción como escenario hipotético sujeto a supuestos. Revisar en Contabilidad si sumar el riesgo por bache multiplica eventos cuando varios baches comparten una celda. Regenerar las tablas, gráficas y entregables que dependan de estas cifras.

**Criterio de cierre.** El documento identifica la unidad de riesgo, el horizonte, los supuestos y el periodo de validación. Un ejemplo con varios baches en una celda deja explícito cómo se asignan los accidentes esperados. Las conclusiones financieras incluyen sensibilidad ante escenarios alternativos, incluida atribución nula.

**Referencias.** [Modelo](probabilidad/riesgo_72h.py#L268), [generador de Probabilidad](scripts/generar_doc_probabilidad.py#L298), [costo esperado](contabilidad/provisiones.py#L91), [generador de Contabilidad](scripts/generar_doc_contabilidad.py#L185).

## Prioridad media

### C05 · Hacer reproducible la instalación en otro equipo

Seis scripts SQL tienen rutas absolutas del equipo original. El orquestador permite indicar `-Servidor`, mientras que el tablero, el exportador y algunos generadores apuntan a `localhost`. El orden que muestra el README carga en SQL un CSV de riesgo antes de regenerarlo. Parametrizar las rutas y la conexión. Documentar que `BULK INSERT` necesita rutas accesibles para el servicio de SQL Server. Indicar si se usan insumos versionados o se regeneran y, en ese caso, ejecutar la carga y el recálculo en el orden correcto. **Cierre:** un clon en otra ruta puede montar el entorno sin editar archivos SQL y el CSV de riesgo coincide con la tabla cargada. [Instalación](README.md), [ruta de riesgo](bd/05b_riesgo_72h.sql#L17), [tablero](tablero/app.py#L35), [exportación](scripts/exportar_datos_tablero.py#L72).

### C06 · Mantener el indicador de reincidencia sincronizado

`ind.sp_actualizar_reincidencia` reconstruye la tabla derivada y se llama al ejecutar el script de vistas. El alta de reportes no lanza ese proceso y el repositorio no incluye una programación para ejecutarlo periódicamente. Por eso la barra puede indicar conexión en vivo mientras se consulta un indicador calculado antes de las últimas altas. Definir frecuencia, fecha de corte visible y recuperación ante fallos. **Cierre:** un reporte nuevo aparece dentro del intervalo publicado y dos actualizaciones coincidentes no hacen retroceder el corte. [Proceso y ejecución inicial](bd/13_vistas_indicadores.sql#L63), [consulta del tablero](tablero/app.py#L369).

### C07 · Corregir el cálculo de tiempos de atención

La vista selecciona la última aprobación o ajuste y la última reparación mediante subconsultas independientes. Si hay una decisión fechada después de reparar, el tiempo puede resultar negativo y contar como cumplimiento. El flujo de la pantalla de autoridad filtra casos cerrados, pero el procedimiento de decisión no comprueba el estado del bache. El DW repite el patrón. Definir qué decisión rige la reparación, filtrar la secuencia por fecha y resolver los empates con un identificador estable. **Cierre:** una decisión posterior a la reparación no altera su plazo y los indicadores del tablero y del DW dan el mismo resultado para los casos de prueba. [Vista](bd/13_vistas_indicadores.sql#L138), [ETL](bd/10_dw_etl.sql#L133), [decisiones](bd/05_procedimientos_transacciones.sql#L200).

### C08 · Manejar caídas de SQL y territorios sin casos

Una excepción durante la primera conexión activa automáticamente el modo de copia y ese resultado se almacena con `st.cache_resource`. Si la conexión ya estaba abierta y falla después, las lecturas no tienen manejo equivalente. El ranking también presupone que hay baches abiertos con IPU en `CHALCO` y llama a `territorios.index("CHALCO")`, que falla si falta. Distinguir los modos de operación, permitir reconexión y manejar conjuntos vacíos. **Cierre:** al interrumpir y recuperar SQL, la app indica su estado y recupera la conexión. El ranking muestra un estado vacío cuando todos los baches están cerrados y funciona con cualquier territorio disponible. [Conexión](tablero/app.py#L215), [ranking](tablero/app.py#L845).

### C09 · Definir qué información se publica en la copia estática

El exportador incluye identificadores de reportes, coordenadas de baches, nombres de autoridades y comentarios de seguimiento. El generador copia esos CSV a `docs/datos/`. Los ejemplos revisados de autoridad y seguimiento son etiquetas genéricas y texto operativo de simulación. Si se sustituyen por datos reales, el exportador trasladaría esos campos tal cual. Definir un conjunto explícito de columnas y filas públicas, y usar comentarios ficticios en la demostración. **Cierre:** un comentario de prueba que contiene datos personales queda fuera del paquete público mientras los indicadores previstos siguen funcionando. [Consultas de exportación](scripts/exportar_datos_tablero.py#L22), [generador estático](scripts/construir_sitio.py#L65).

### C10 · Recuperar la réplica después de un fallo de restauración

`sp_replicar` crea un respaldo de log antes de restaurarlo. Si falla la restauración, registra el error, pero el siguiente intento crea otro respaldo y trata de aplicarlo directamente. La réplica puede quedar atrás si falta el tramo previo. Implementar el reintento de archivos pendientes en orden y serializar la ejecución. Separar el alta del reporte demostrativo del flujo de instalación. **Cierre:** después de un fallo inducido de restauración en una instancia de prueba, el siguiente ciclo recupera la secuencia sin insertar reportes demostrativos ni recrear la réplica. [Procedimiento](bd/12_replicacion.sql#L57), [demostración](bd/12_replicacion.sql#L130).

### C11 · Hacer explícitas las dependencias y el descubrimiento de pruebas

`pytest --collect-only` desde la raíz encontró cero pruebas con el patrón predeterminado. Al indicar los dos archivos de tablero, encontró 12 casos. La suite E2E depende del fixture `page` de `pytest-playwright`, que no figura en `requirements.txt`, aunque está disponible en el entorno auditado y permitió recolectar los casos. Declarar las dependencias de pruebas, la instalación de Chromium y los comandos de cada suite. **Cierre:** una instalación limpia puede recolectar y ejecutar las suites previstas con una instrucción documentada y bases aisladas. [Dependencias](requirements.txt), [E2E local](tablero/pruebas_e2e.py#L36), [pruebas estáticas](tablero/pruebas_sitio.py#L30), [estructuras](estructuras/pruebas.py).

## Verificación realizada

- `python -B estructuras/pruebas.py` pasó las 12 pruebas.
- `python -B -m pytest --collect-only -q -p no:cacheprovider tablero/pruebas_e2e.py tablero/pruebas_sitio.py` recolectó 12 casos. Quedó pendiente ejecutarlos con navegador y una base aislada para la suite local.
- Una consulta de solo lectura confirmó que existen `SIPA`, `SIPA_DW` y `SIPA_REPLICA`. Los hallazgos sobre procedimientos y vistas se sustentan en el código versionado. Quedó pendiente reproducirlos con datos controlados en SQL Server.
- `tablero/app.py` y `docs/app.py` tienen el mismo SHA-256. Se revisó la copia estática del repositorio. Quedó pendiente validar el sitio desplegado y las cifras de los PDF y Word de extremo a extremo.

Para el traspaso a Claude, atender primero C01 y C05 para disponer de un entorno reproducible de prueba. Luego corregir C02 y C03 antes de validar cambios en indicadores. C04 requiere acordar el alcance metodológico antes de regenerar las cifras y documentos. Registrar los resultados de las verificaciones junto a cada hallazgo.

---

## Atención de los hallazgos (Claude, 17 de noviembre de 2026)

Se atendieron los 11 hallazgos. Antes de cualquier cambio se respaldaron `SIPA`, `SIPA_DW` y `SIPA_REPLICA` (`*_antes_codex.bak`, copia COPY_ONLY en la carpeta de respaldos de la instancia). Después se reconstruyó todo desde cero con el instalador nuevo y se regeneraron modelos, documentos, PDF y sitio.

### C01 · Proteger la base · Atendido
- `bd/ejecutar_todo.ps1` revisa **antes de escribir** que existan `sqlcmd`, los 16 scripts y los archivos de datos, y que el servidor responda. Si `SIPA`, `SIPA_DW` o `SIPA_REPLICA` ya existen, **se detiene sin tocarlas**; reconstruir exige `-Reconstruir`.
- Pruebas E2E y de base: trabajan sobre copias desechables (`SIPA_PRUEBAS`, `SIPA_PRUEBAS_BD`) creadas con un respaldo COPY_ONLY (no rompe la cadena de logs de la réplica) y borradas al terminar. La E2E levanta su propio Streamlit (puerto 8599, `SIPA_BD=SIPA_PRUEBAS`).
- **Verificación:** sin `-Reconstruir` → «ALTO: ya existen… No se tocaron», exit 1. Con `-Raiz` inexistente → lista los 5 archivos faltantes, exit 1, ninguna base modificada. Con servidor inexistente → «no responde», exit 1. E2E ejecutada 3 veces: conteos de `SIPA` (reportes 35,699 · decisiones 301 · seguimientos 603 · cálculos 1,646 · baches 1,646) idénticos antes y después.

### C02 · Identidad y territorio · Atendido en el servidor; sesión declarada como simulación
- Nueva `dbo.fn_autoridad_puede(@usuario, @bache)`: una AUTORIDAD solo actúa sobre baches con reportes en su territorio (ADMIN sin restricción). `sp_registrar_decision` (error 50010) y `sp_actualizar_estado_bache` (50011) la aplican; la decisión guarda el `id_usuario` del actor.
- El selector «Entrar como» se mantiene para la demostración y la pantalla lo identifica como **simulación académica**. Fuera de alcance: autenticación real y una cuenta SQL por usuario.
- **Verificación (`bd/pruebas_bd.py`):** usuario nulo, inexistente o ANALISTA → rechazado; autoridad de otro territorio → rechazada al decidir y al actualizar; la decisión registrada lleva al actor correcto.

### C03 · Vinculación de reportes · Atendido
- `sp_registrar_reporte` ya no liga por celda. Política explícita (igual a `estructuras/sipa_ed.py`): bache abierto **a ≤ 15 m** (distancia física), del **mismo territorio** que la colonia y con último reporte **≤ 30 días**; gana el más cercano. Validaciones: punto a más de 3 km del centro de la colonia (50013) o fuera de la cuadrícula (50014) → rechazo explícito. La celda se sigue guardando para los indicadores.
- La carga histórica de `bd/04` (un bache por celda) quedó documentada como hipótesis de agregación de los datos 2022, distinta de la regla operativa.
- **Verificación:** dos puntos a 66 m en la misma celda → baches distintos; dos puntos a ≈ 8 m en celdas vecinas (borde) → mismo bache; coordenadas a 22 km de la colonia → rechazo «3 km»; punto fuera de la cuadrícula → rechazo. El demo de `bd/07` sigue detectando su duplicado (13 m).

### C04 · Riesgo y costos · Atendido
- **Doble conteo corregido:** `μ_c = λ_c · 3/365` (antes `λ_c · RR · 3/365`). λ_c (Bayes empírico) ya incluye los accidentes observados con los baches de la celda; el RR (1.38) queda solo como medida descriptiva de asociación.
- **Validación temporal:** λ ajustada solo con 2018 y evaluada contra 2019 (`probabilidad/resultados/t7_validacion_temporal.csv`): Spearman 0.57, deciles ordenados, celdas rojas con 4.3 % de P(72 h) observada contra 0.47 % en las verdes. El nivel se sobreestima 23 % porque 2019 registró menos accidentes; se documenta que hay que recalibrar cada año.
- **Fracción atribuible como escenario:** `1 − 1/RR = 27.4 %` se presenta como cota superior hipotética, junto con atribución media (13.7 %) y **nula (0 %)**.
- **Contabilidad:** P72 es por celda; si varios baches comparten celda, sus accidentes esperados se **reparten** (`/ n_celda`) en lugar de multiplicarse. Nueva tabla `t10_sensibilidad_atribucion.csv` y sección 4.3 en el documento. (Hoy ninguna celda tiene dos baches pendientes; la regla queda lista para cuando ocurra con la vinculación de C03.)
- **Efecto en cifras:** celdas en rojo 1,727 → 1,000; pendientes en rojo por riesgo 164 → 75; coincidencia con el IPU 55 % → 66 %. Ahorro del preventivo $7.57 M → $7.29 M; **con atribución nula el ahorro sigue siendo de $6.59 M**: la conclusión no depende del supuesto causal.
- Unidad (celda de 250 m), horizonte (72 h), supuestos y periodo de validación quedan escritos en el documento de Probabilidad (secciones 4, 7, 7.2, 7.3, 9 y 10) y en el entregable final.

### C05 · Instalación reproducible · Atendido
- Los 6 scripts con ruta absoluta usan ahora `$(RAIZ)` de `sqlcmd`; el orquestador la toma de la carpeta del repositorio (o de `-Raiz`). El servidor sale de `-Servidor` o de `SIPA_SERVIDOR`, que también leen el tablero, el exportador, los generadores, los modelos y las pruebas.
- README: orden correcto (riesgo → base → riesgo con base → cálculo → contabilidad), nota de que `BULK INSERT` usa la cuenta del servicio y aclaración de que el CSV versionado de riesgo equivale al generado.
- **Verificación:** instalación completa desde cero con el orquestador nuevo: exit 0, 16 scripts. Hallazgo durante la prueba: `sqlcmd -v RAIZ=C:\...` falla por el `:` de la ruta; se pasa como variable de entorno (sqlcmd las toma como variables de script).

### C06 · Reincidencia sincronizada · Atendido
- Nueva tabla `ind.corte_reincidencia` (corte visible: hasta qué reporte y a qué hora). `ind.sp_actualizar_reincidencia` se serializa con `sp_getapplock`, el corte **nunca retrocede** y, si falla, conserva la tabla y el corte anteriores y anota el error.
- Frecuencia publicada: el tablero la ejecuta al abrir Indicadores si hay reportes posteriores al corte (como máximo cada 5 min) y muestra la fecha de corte.
- **Verificación:** un reporte nuevo no aparece antes de actualizar y sí después; dos actualizaciones seguidas → el corte llega al reporte nuevo y no retrocede.

### C07 · Tiempos de atención · Atendido
- La vista y el ETL usan la misma regla: la reparación es el último seguimiento a REPARADO (empate por `id_seguimiento`) y la decisión que la rige es la última APROBAR/AJUSTAR **anterior** a la reparación (empate por `id_decision`). `sp_registrar_decision` rechaza baches reparados o descartados (50009).
- **Verificación:** el procedimiento rechaza la decisión posterior; una decisión insertada directamente 30 días después no cambia el plazo ni la fecha de decisión; 0 tiempos negativos; vista y DW coinciden en horas y cumplimiento en los 301 baches reparados.

### C08 · Caídas de SQL y territorios sin casos · Atendido
- Tres modos visibles: «En vivo · SQL Server», «Copia de solo consulta» (sitio) y «SQL Server no disponible · copia» (app local sin servidor; reintenta en cada recarga). La conexión guardada se comprueba con `SELECT 1` en cada ejecución y se reconecta si se cayó; un fallo a media consulta muestra un error claro en vez de una excepción.
- El ranking y el modo autoridad ya no dependen de `CHALCO`: si no existe usan el primer territorio, y si no hay baches abiertos con IPU muestran un estado vacío.
- **Verificación:** se cortaron con `KILL` las sesiones del tablero sobre SIPA; al recargar, la app volvió a «En vivo» sin excepciones y el ranking se mostró. No se probó apagar el servicio de SQL Server (requiere permisos de administrador).

### C09 · Copia estática · Atendido
- `scripts/exportar_datos_tablero.py` tiene una lista `PUBLICAS` de columnas por tabla; una columna no declarada **detiene la exportación**. Autoridades → «Autoridad de <territorio>»; comentarios de seguimiento → texto fijo según el estado; coordenadas de los baches redondeadas a 3 decimales (≈ 100 m); reportes sin descripción.
- **Verificación:** prueba con el comentario «Lo atendió Juan Pérez, tel. 55 1234 5678» → sale «Reparado.»; una columna `descripcion` no declarada detiene la exportación. Sitio regenerado; sus 5 pruebas pasan.

### C10 · Réplica · Atendido
- `sp_replicar` está serializado con `sp_getapplock`. Cada respaldo de log se anota PENDIENTE y se aplican **en orden** todos los PENDIENTE/ERROR posteriores al último respaldo completo; si uno falla se marca ERROR y se detiene, así el siguiente ciclo lo reintenta antes que los nuevos. El error 4326 (tramo ya aplicado) se marca OK.
- El reporte demostrativo salió de la instalación: `bd/12b_demo_replicacion.sql` (opcional, con instrucciones para inducir el fallo).
- **Verificación:** fallo inducido en la instancia: se generó un tramo de log y se registró como ERROR sin aplicarlo; el siguiente `sp_replicar` aplicó primero ese tramo (envío 3) y luego el nuevo (envío 4). La réplica siguió en STANDBY, sin recrearse y sin insertar reportes.

### C11 · Dependencias y pruebas · Atendido
- `pytest.ini` (testpaths `estructuras bd tablero`, archivos `pruebas*.py`); `requirements.txt` incluye `pytest-playwright`; el README explica cómo instalar Chromium y el comando de cada suite.
- **Verificación:** `python -m pytest --collect-only -q` desde la raíz recolecta 35 pruebas. Resultados: estructuras 12/12, bd 11/11, E2E 7/7, sitio 5/5.

### Pendiente (resuelto en la segunda ronda)
- `avance2_Probabilidad_semaforo72h.docx` estaba abierto en Word durante la regeneración; se regeneró en la segunda ronda.

---

## Reevaluación de Codex (17 nov 2026): 7.4/10, NO-GO

Cerrados C03, C07 y C11; parciales los otros ocho. Lo que pidió para el GO se atendió así:

## Segunda ronda (Claude, 18 de noviembre de 2026)

| Pedido de Codex | Cambio | Verificación |
|---|---|---|
| **C01** Prevalidar cada archivo de entrada | `ejecutar_todo.ps1` lista los 11 archivos que leen los scripts (no carpetas) y exige que cada uno sea un archivo (`-PathType Leaf`). | En una copia del proyecto se borró `datos\chalco\limpios\comunidades.csv`: «ALTO: faltan archivos… comunidades.csv», exit 1; la fecha de creación de `SIPA` no cambió. |
| **C01** Pruebas que borran bases con nombre fijo | `SIPA_PRUEBAS_<id único>` y `SIPA_PRUEBAS_BD_<id único>` por corrida; si el nombre ya existe la prueba se detiene y solo se borra la base que la propia corrida creó. | Tras bd y E2E no queda ninguna base `SIPA_PRUEBAS%`; conteos de `SIPA` iguales antes y después. |
| **C02** Identidad autenticada | `dbo.configuracion(modo)`: **DEMO** (lo que instala la demostración, con selector marcado como simulación) u **OPERATIVO**. Nueva `dbo.fn_actor`: en OPERATIVO el actor es el usuario cuyo `login_sql` = `ORIGINAL_LOGIN()` de la sesión; un `@id_usuario` distinto se rechaza. Los dos procedimientos de autoridad registran ese actor. El tablero en OPERATIVO quita el selector y muestra la sesión autenticada. | `test_modo_operativo_toma_la_identidad_de_la_sesion`: sin login asociado → rechazado aun con id válido; con login asociado → decide con `@id_usuario = NULL` y queda registrado el actor; pasar el id de otra autoridad → rechazado al decidir y al actualizar. |
| **C04** Regenerar Probabilidad y medir 72 h con ventanas reales | La validación parte 2019 en 122 ventanas consecutivas de 72 h y cuenta, por celda, la fracción de ventanas con al menos un accidente; se agregó el puntaje de Brier. Documento de Probabilidad y PDF regenerados (sección 7.3). | Rojo: P predicha 5.6 % → observada 4.3 %; amarillo 2.1 % → 1.6 %; verde 0.49 % → 0.47 %. Brier 0.01128 contra 0.01145 de referencia (mejora modesta, declarada en el documento: el valor está en separar las celdas rojas). |
| **C05** Instalación desde otra ruta y CSV = tabla | Se instaló desde una copia en `C:\Users\gerry\Documents\Rebeca_unrc\sipa_otra_ruta` sin editar ningún `.sql`; después se borró la copia. Nueva prueba que compara el CSV de riesgo con `riesgo_celda_72h`. | Instalación desde la otra ruta: exit 0 («Listo…»). `test_csv_de_riesgo_coincide_con_la_tabla`: mismas celdas, P(72 h) con diferencia < 1e-7, semáforo idéntico. |
| **C06** No depender de visitas | `ind.sp_reincidencia_reporte`: cada alta por `sp_registrar_reporte` clasifica su propio reporte y avanza el corte **dentro de la misma transacción** (candado compartido; la reconstrucción completa usa uno exclusivo). Frecuencia publicada: inmediata. | `test_reporte_nuevo_aparece_al_instante_y_el_corte_no_retrocede`: el reporte aparece clasificado sin ninguna actualización manual; dos reconstrucciones completas dan la misma clasificación y el corte no retrocede. |
| **C08** `fetchall()` fuera del manejo de errores | `consulta` lee las filas dentro del `try`. `ejecutar` distingue los SQLSTATE de conexión perdida (08S01, 08001, HYT00…) de una regla incumplida y en ese caso usa el aviso de caída. | E2E 7/7; la prueba de reconexión de la primera ronda sigue vigente. |
| **C09** `tiempos` con `SELECT *` | Consulta con columnas explícitas y lista pública obligatoria para **todas** las tablas (sin excepción `None`); una tabla no declarada también detiene la exportación. | bd 13/13 (incluye la prueba de datos personales); sitio 5/5. |
| **C10** Ventana entre `BACKUP LOG` y la anotación | El tramo se anota **PREPARADO antes** del respaldo y pasa a PENDIENTE después. Antes de restaurar se consulta `msdb.dbo.restorehistory` (ya aplicado → OK) y `xp_fileexist` + `msdb.backupmediafamily` (nunca escrito → ANULADO). Esto sustituye la lectura de `ERROR_NUMBER()`, que tras un RESTORE fallido devuelve el genérico 3013. | Fallo inducido: renglón PREPARADO con respaldo ya escrito (sesión cortada justo después) → aplicado en orden (envío 3); renglón PREPARADO sin archivo → ANULADO (envío 4); el envío nuevo (5) se aplicó; réplica en STANDBY y con los mismos 35,699 reportes. |

**Pruebas al cierre de la segunda ronda:** estructuras 12/12, bd 13/13, E2E 7/7, sitio 5/5 (37 en total; `python -m pytest --collect-only -q` las recolecta desde la raíz). Base reconstruida desde la otra ruta; modelos, documentos (incluido Probabilidad), PDF y sitio regenerados.

**Fuera de alcance (declarado):** inicio de sesión del tablero web propio; en modo OPERATIVO la autenticación es la de Windows/SQL Server de la conexión. No se probó apagar el servicio de SQL Server (requiere permisos de administrador).

---

## Reevaluación de Codex (18 nov 2026): 8.1/10, NO-GO

Cerrados C01, C03, C05, C07, C08, C09, C10 y C11. Parciales C02 (conexión compartida del tablero), C06 (altas concurrentes) y C04 (ventana incompleta y universo con datos de 2019). Además, `consulta()` trataba cualquier error ODBC como caída.

## Tercera ronda (Claude, 18 de noviembre de 2026)

**Alcance acordado con el equipo:** SIPA es un proyecto universitario de 3er semestre. Es un **prototipo académico con datos simulados**, no un sistema en operación. Por eso esta ronda corrige los errores técnicos reales y declara de forma explícita lo que corresponde a una puesta en producción.

| Pedido de Codex | Cambio | Verificación |
|---|---|---|
| **C04** Ventana incompleta | Solo ventanas completas: 121 (365 // 3); los días 364 y 365 se descartan. | `ventanas_72h = 121`. |
| **C04** Universo con datos de 2019 | Las celdas se fijan sin mirar los accidentes de 2019: las que tuvieron accidentes en 2018 o reportes de baches (exposición, no resultado). Se informan aparte los 554 accidentes de 2019 que caen fuera. Documento de Probabilidad y PDF regenerados con esta descripción. | 9,085 celdas; Spearman 0.62; rojo 5.6 % predicha → 4.3 % observada; amarillo 2.1 % → 1.6 %; verde 0.52 % → 0.43 %; Brier 0.01133 contra 0.01151. |
| **C06** Altas concurrentes | `ind.sp_reincidencia_reporte` toma el candado **exclusivo** hasta el COMMIT del alta, el mismo que la reconstrucción completa: las altas se clasifican una tras otra y cada una ve confirmadas las anteriores, así que el corte «hasta el reporte N» cubre todos los IDs menores. A la escala del proyecto la espera es nula. | Nueva `test_altas_simultaneas_clasifican_igual_que_la_reconstruccion`: 6 altas en hilos paralelos en el mismo punto → 1 NUEVO y 5 DUPLICADO, corte = ID máximo y la reconstrucción completa da exactamente la misma clasificación. |
| **Menor** Errores ODBC tratados como caída | `consulta()` solo trata como caída los SQLSTATE de conexión perdida; los errores de permisos o de consulta se muestran tal cual. | E2E 7/7. |
| **C02** Permisos de lectura | `rol_autoridad` recibe `SELECT` sobre el esquema `ind` (indicadores que lee el tablero). | Instalación completa, exit 0. |
| **C02** Identidad por persona | **Declarado fuera del alcance académico.** Lo que sí está y se prueba: en la base, cada decisión y avance se valida por territorio y registra al actor, y en modo OPERATIVO la identidad sale del login de la sesión (`fn_actor`), no del cliente. El tablero de la demostración usa una sola conexión y el selector «Entrar como», marcado en pantalla como simulación sobre datos simulados. Para una puesta en producción haría falta inicio de sesión en el tablero con una conexión por persona (p. ej. Streamlit con autenticación y `Trusted_Connection` por usuario). Se documenta como trabajo futuro. | `test_modo_operativo_toma_la_identidad_de_la_sesion` (bd). |

**Pruebas al cierre de la tercera ronda:** estructuras 12/12, bd 14/14, E2E 7/7, sitio 5/5 (38). Base reconstruida; modelos, documentos, PDF y sitio regenerados; no queda ninguna base `SIPA_PRUEBAS%`.

---

## Reevaluación de Codex (18 nov 2026): 8.6/10, NO-GO

C02 cerrado para el alcance académico acordado. Parciales: C06 (el candado se tomaba después de insertar el reporte) y C04 (el universo de validación usaba reportes de 2019-2022).

## Cuarta ronda (Claude, 18 de noviembre de 2026)

| Pedido de Codex | Cambio | Verificación |
|---|---|---|
| **C06** Candado antes de insertar | `sp_registrar_reporte` toma el candado exclusivo `ind.reincidencia` justo después de `BEGIN TRANSACTION`, **antes** de leer `bache` o insertar el reporte. Así el orden de los ID coincide con el orden de clasificación y una reconstrucción (mismo candado, sin tocar `bache`) no puede cruzarse con un alta a medias ni interbloquearse con ella. `ind.sp_reincidencia_reporte` vuelve a pedirlo (reentrante). | Nueva `test_altas_en_puntos_distintos_con_reconstruccion_simultanea`: 8 altas en puntos distintos y una reconstrucción completa en hilos paralelos → sin errores ni interbloqueos, corte = ID máximo, 0 reportes sin clasificar y misma clasificación que una reconstrucción posterior. Sigue pasando la prueba de 6 altas en el mismo punto. |
| **C04** Universo con información futura | El universo de validación usa **solo información disponible al cierre de 2018**: celdas con al menos un accidente en 2018 (ya no se usan los reportes de 2019-2022). El documento de Probabilidad lo describe así y explica por qué no aparecen celdas verdes en la muestra. Documento y PDF regenerados. | 5,113 celdas; 2,051 accidentes de 2019 quedan fuera; Spearman 0.61; rojas 4.9 % predicha → 3.7 % observada en ventanas reales; amarillas 1.7 % → 1.0 %; Brier 0.01777 contra 0.01797. |

**Pruebas al cierre de la cuarta ronda:** estructuras 12/12, bd 15/15, E2E 7/7, sitio 5/5 (39). Base reconstruida; modelos, documentos, PDF y sitio regenerados; no queda ninguna base `SIPA_PRUEBAS%`.

---

## Reevaluación final de Codex (18 nov 2026): 9.1/10, GO

C01 a C11 cerrados para el alcance acordado (prototipo académico con datos simulados). Limitaciones que Codex pide no perder de vista: la validación de C04 no evalúa celdas verdes (excluye celdas sin accidentes en 2018 y 2,051 accidentes de 2019) y la mejora de Brier es modesta; ambas están declaradas en el documento de Probabilidad.
