# SIPA · Sistema Inteligente de Priorización Asfáltica

Problema prototípico **«Bacheo inteligente y priorización urbana»** · Universidad Nacional Rosario Castellanos · Licenciatura en Ciencia de Datos para Negocios · 3er semestre · 2026-2.

SIPA es un sistema de **asesoría**: reúne los reportes ciudadanos de baches con información del entorno (riesgo de accidente, transporte público, marginación, zonas inundables, escuelas y hospitales cercanos) y calcula para cada bache un **Índice de Prioridad Urbana (IPU)**, un semáforo, la intervención recomendada y su costo estimado. La autoridad decide y repara; SIPA registra su decisión y el avance que informa.

## La aplicación oficial trabaja sobre SQL Server

La aplicación del proyecto es el tablero de `tablero/app.py`, que corre en local (`python -m streamlit run tablero/app.py`) **conectado en vivo a SQL Server** (base `SIPA`) con `pyodbc`:

- Lee los datos con consultas y vistas (esquema `ind`).
- Toda escritura pasa por los **procedimientos almacenados** de `bd/05` (`sp_registrar_reporte`, `sp_calcular_ipu`, `sp_registrar_decision`, `sp_actualizar_estado_bache`), con sus transacciones y restricciones: lo inválido lo rechaza la base y la transacción se revierte.
- La barra superior del tablero indica **«En vivo · SQL Server»**.
- Las pruebas `tablero/pruebas_e2e.py` (Playwright) recorren la app y escriben en una copia desechable de la base (`SIPA_PRUEBAS`), no en `SIPA`.
- **Evidencia:** [evidencia_sql_server.pdf](pdf/evidencia_sql_server.pdf) muestra la app en un navegador y, en cada paso, la consulta directa a SQL Server: lee lo mismo, escribe un reporte (la fila aparece en la base y la cifra sube en 1) y la base rechaza una decisión inválida. Se genera con `python scripts/evidencia_sql_server.py`.

El sitio de abajo es solo una **vista pública de consulta**: un sitio estático no puede conectarse a un SQL Server local, por eso usa una copia exportada.

## Tablero en línea (vista pública de solo consulta)

**https://rebeca256.github.io/sipa-bacheo-inteligente/**

Corre en el navegador con [stlite](https://github.com/whitphx/stlite) (Streamlit sobre Pyodide). La primera carga tarda entre 15 y 30 segundos. Es una **versión de solo consulta**: usa una copia de los datos (`tablero/datos/`); los formularios revisan las mismas reglas que la base, pero no guardan cambios. La versión completa, que guarda reportes y decisiones, corre en local con SQL Server.

## Contenido

| Carpeta | Qué hay |
|---|---|
| `bd/` | Base de datos en SQL Server: modelo entidad-relación, scripts 01 a 13, Data Warehouse, réplica, indicadores (`ejecutar_todo.ps1` reconstruye todo) |
| `tablero/` | Tablero en Streamlit (`app.py`), pruebas con Playwright y copia de solo consulta de los datos |
| `docs/` | Sitio de GitHub Pages (lo genera `scripts/construir_sitio.py`) |
| `estructuras/` | Estructuras de datos: lista enlazada, tabla hash, AVL, max-heap, pila, grafo y Dijkstra; simulaciones |
| `probabilidad/` | Riesgo de accidente a 72 h (Poisson) y semáforo de riesgo |
| `calculo/` | Degradación del asfalto (integral definida) y costo de esperar |
| `contabilidad/` | Provisiones NIF C-9 y registro contable |
| `pensamiento/` | Mapa de red de agentes |
| `pesos/` | Plantilla AHP para definir los pesos del IPU |
| `datos/` | Datos abiertos usados (cada carpeta tiene su `FUENTE.md`) y tarifas de reparación (`datos/costos/`) |
| `scripts/` | Limpieza de datos y generadores de los documentos de entrega |
| `*.docx` | Entregables: `entregable_final_SIPA.docx` (evidencia integradora) y uno por asignatura |

## Entregables en PDF

Para leerlos directo en GitHub (los originales en Word están en la raíz del repositorio):

| Documento | PDF |
|---|---|
| Evidencia integradora (entregable final) | [entregable_final_SIPA.pdf](pdf/entregable_final_SIPA.pdf) |
| Fundamentos de Bases de Datos | [avance2_BD_entrega.pdf](pdf/avance2_BD_entrega.pdf) |
| Estructuras de Datos: plan de viabilidad | [avance2_ED_plan_viabilidad.pdf](pdf/avance2_ED_plan_viabilidad.pdf) |
| Probabilidad: semáforo de riesgo a 72 h | [avance2_Probabilidad_semaforo72h.pdf](pdf/avance2_Probabilidad_semaforo72h.pdf) |
| Cálculo Integral: degradación del asfalto | [avance2_Calculo_degradacion.pdf](pdf/avance2_Calculo_degradacion.pdf) |
| Contabilidad Financiera: provisiones NIF C-9 | [avance2_Contabilidad_NIF_C9.pdf](pdf/avance2_Contabilidad_NIF_C9.pdf) |
| Pensamiento Complejo: estrategia de argumentación | [avance2_PensamientoComplejo_argumentacion.pdf](pdf/avance2_PensamientoComplejo_argumentacion.pdf) |
| Primer avance e incidente de Estructuras de Datos | [avance1_PP.pdf](pdf/avance1_PP.pdf) · [avance2_PP_incidente_ED.pdf](pdf/avance2_PP_incidente_ED.pdf) |
| Control interno de la entrega de BD (rúbricas) | [avance2_BD_planeacion.pdf](pdf/avance2_BD_planeacion.pdf) |

Se generan con `python scripts/exportar_pdf.py` (sin Word: mammoth y Chrome), así que el formato es más sencillo que el del .docx.

## Cómo ejecutar en local

Requisitos: Python 3.11+, SQL Server (probado con 2025 Developer) con ODBC Driver 17, `sqlcmd` y PowerShell.

```
pip install -r requirements.txt
python -m playwright install chromium                     # navegador para las pruebas

python probabilidad/riesgo_72h.py                         # 1. genera t4_riesgo_72h_por_celda.csv (lo carga la base)
powershell -ExecutionPolicy Bypass -File bd\ejecutar_todo.ps1    # 2. base, DW y réplica (instalación nueva)
python probabilidad/riesgo_72h.py                         # 3. con la base: riesgo de los baches pendientes
python calculo/degradacion.py
python contabilidad/provisiones.py
python estructuras/viabilidad.py
python -m streamlit run tablero/app.py                    # tablero completo (Streamlit 1.67)
```

El paso 1 puede omitirse si se usa el CSV versionado en `probabilidad/resultados/`: es el mismo que genera el script.

**Instalación protegida.** `ejecutar_todo.ps1` revisa antes de escribir que existan `sqlcmd`, todos los scripts y los archivos de datos, y que el servidor responda. Si ya existen `SIPA`, `SIPA_DW` o `SIPA_REPLICA`, se detiene sin tocarlas; para borrarlas y reconstruir la demostración hay que pedirlo explícitamente con `-Reconstruir`.

**Otro equipo u otra carpeta.** No hay que editar los `.sql`: usan la variable `$(RAIZ)` de `sqlcmd`, que el orquestador toma de la carpeta del repositorio (o de `-Raiz`). El servidor se indica con `-Servidor` o con la variable de entorno `SIPA_SERVIDOR`, que también leen el tablero, el exportador y los generadores (por omisión, `localhost`). `BULK INSERT` lee los archivos con la cuenta del servicio de SQL Server, así que la carpeta del proyecto debe ser accesible para ese servicio (en una instancia local lo es; en un servidor remoto use una ruta UNC).

```
$env:SIPA_SERVIDOR = ".\SQLEXPRESS"
powershell -ExecutionPolicy Bypass -File bd\ejecutar_todo.ps1 -Reconstruir
```

**Identidad de las autoridades.** La instalación deja la base en modo `DEMO` (datos simulados): el tablero muestra el selector «Entrar como», marcado como simulación. En modo `OPERATIVO` la base toma la identidad del login de SQL Server de la sesión (`usuario.login_sql`), el selector desaparece y nadie puede actuar en nombre de otra autoridad ni fuera de su territorio. Pasos en el encabezado de `dbo.fn_actor` (`bd/05`).

Para actualizar el sitio en línea después de cambiar la base:

```
python scripts/exportar_datos_tablero.py      # solo columnas públicas (ver la política en el script)
python scripts/construir_sitio.py
```

## Pruebas

`pytest.ini` declara las suites (los archivos se llaman `pruebas*.py`). Ninguna modifica la base operativa `SIPA`: las de base de datos y las del tablero local copian `SIPA` a una base desechable con nombre único por corrida, trabajan sobre ella y borran solo esa base al terminar (nunca una que ya existiera).

```
python -m pytest estructuras -v                  # estructuras de datos (12 pruebas, sin requisitos)
python -m pytest bd -v                           # procedimientos, vistas, DW y copia pública (15 pruebas)
python -m pytest tablero/pruebas_e2e.py -v       # tablero local: levanta su propio Streamlit en el puerto 8599
python -m pytest tablero/pruebas_sitio.py -v     # sitio estático: antes, python -m http.server 8000 --directory docs
```

La demostración de la réplica que inserta un reporte de prueba quedó fuera de la instalación: `sqlcmd -S localhost -E -f 65001 -i bd\12b_demo_replicacion.sql`.

## Datos

Reales: solicitudes de bacheo de la CDMX 2019-2022, datos abiertos de Chalco (reportes, comunidades, Atlas de Riesgo, equipamiento), hechos de tránsito de la SSC, GTFS de SEMOVI e índice de marginación urbana 2020 de CONAPO. Simulados y declarados como tales: severidad y medidas de los baches, decisiones y reparaciones de la autoridad. Las tarifas de reparación son una estimación del equipo.

**Dos territorios.** El nivel operativo de SIPA (qué bache atender primero) se probó en la CDMX, donde hay baches georreferenciados. El nivel financiero (incidente de Contabilidad «Contingencias por daños viales») se estimó para el **Estado de México** con datos del INEGI (ATUS 2010-2023: accidentes por mala condición del camino; vehículos registrados 2023 por municipio) y la Ley de Responsabilidad Patrimonial del Edomex: `python contabilidad/contingencias_edomex.py`. El ZIP completo del ATUS (126 MB) no se sube; se descarga de https://www.inegi.org.mx/contenidos/programas/accidentes/datosabiertos/atus_anual_csv.zip y se guarda en `datos/edomex/raw/`.

## Equipo

Sandra Luna Altos · Joshua David Aquino · Rebeca Jaimes Cruz · Ithan Felipe Santiago

## Uso de IA

El código y los documentos se elaboraron con apoyo de IA generativa (Claude, de Anthropic), con autorización de las y los docentes. El equipo revisó, ejecutó y verificó los resultados.
