"""
SIPA - Evidencia integradora del problema prototípico «Bacheo inteligente y
priorización urbana»: (1) prototipo funcional y (2) plan de viabilidad con la
propuesta de intervenciones públicas priorizadas.

Lee los resultados de todos los modelos y la base SIPA, así que las cifras son
las mismas que en los documentos de cada materia. Ejecutar antes:
    bd/ejecutar_todo.ps1, probabilidad/riesgo_72h.py, calculo/degradacion.py,
    contabilidad/provisiones.py, estructuras/experimentos.py, estructuras/viabilidad.py
y tomar las capturas del tablero (tablero/capturas/, ver tablero/README.md).

Uso (desde la carpeta del proyecto):
    python scripts/generar_entregable_final.py
Salida:
    entregable_final_SIPA.docx
"""
import json
import sys
from pathlib import Path

import pyodbc
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt

sys.path.insert(0, str(Path(__file__).parent))
from generar_doc_planeacion_bd import AZUL, parrafo, tabla, titulo, vinetas  # noqa: E402

SALIDA = "entregable_final_SIPA.docx"
CAPTURAS = Path("tablero/capturas")


def leer(ruta):
    return json.loads(Path(ruta).read_text(encoding="utf-8"))


def m(x, dec=0):
    return f"${x:,.{dec}f}"


def mm(x):
    return f"${x / 1e6:,.2f} M"


ACENTOS = {"Juarez": "Juárez", "Coyoacan": "Coyoacán", "Union": "Unión", "Tlahuac": "Tláhuac",
           "Alvaro": "Álvaro", "Obregon": "Obregón", "Mexico": "México", "Cuauhtemoc": "Cuauhtémoc",
           "Ii": "II", "De": "de", "Del": "del", "La": "la"}


def nombre(texto):
    """BENITO JUAREZ -> Benito Juárez (las bases traen los nombres en mayúsculas y sin acentos)."""
    palabras = [ACENTOS.get(w, w) for w in texto.title().split()]
    palabras[0] = palabras[0][:1].upper() + palabras[0][1:]
    return " ".join(palabras)


def pct(x):
    return f"{100 * x:.0f} %"


def figura(doc, ruta, pie, ancho=16):
    doc.add_picture(str(ruta), width=Cm(ancho))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(pie)
    r.italic = True
    r.font.size = Pt(9)


# ---------------------------------------------------------------------------
# Datos
# ---------------------------------------------------------------------------

def datos_base():
    cx = pyodbc.connect("DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=SIPA;"
                        "Trusted_Connection=yes")
    cur = cx.cursor()

    def uno(sql):
        cur.execute(sql)
        return cur.fetchone()

    def todos(sql):
        cur.execute(sql)
        return cur.fetchall()

    d = {}
    d["reportes"] = uno("SELECT COUNT(*) FROM reporte WHERE id_fuente IN (1, 4)")[0]
    d["abiertos"], d["costo_pendiente"] = uno(
        "SELECT SUM(baches_pendientes), SUM(costo_total) FROM ind.v_costo_pendiente_territorio")
    d["pend_territorio"] = todos("SELECT TOP 3 territorio, costo_total FROM ind.v_costo_pendiente_territorio "
                                 "ORDER BY costo_total DESC")
    d["por_intervencion"] = todos("""
        SELECT t.nombre, COUNT(*), SUM(cp.costo_estimado)
        FROM bache b
        CROSS APPLY (SELECT TOP 1 clave_tarifa, costo_estimado FROM calculo_prioridad x
                     WHERE x.id_bache = b.id_bache ORDER BY x.id_calculo DESC) cp
        JOIN tarifa_reparacion t ON t.clave = cp.clave_tarifa
        WHERE b.id_estado_bache IN (2, 3, 4)
        GROUP BY t.nombre ORDER BY SUM(cp.costo_estimado) DESC""")
    d["decisiones"] = dict(todos("SELECT decision, COUNT(*) FROM decision_humana GROUP BY decision"))
    d["tiempos"] = {r[0]: r for r in todos(
        "SELECT semaforo_final, baches, dias_promedio, meta_dias, pct_en_meta FROM ind.v_tiempo_respuesta_semaforo")}
    d["cobertura"] = dict(todos("SELECT territorio, pct_reparados FROM ind.v_cobertura_territorio"))
    d["resueltos"] = dict(todos("""SELECT anio, CAST(100.0 * SUM(resueltos) / SUM(reportes) AS DECIMAL(5,1))
                                   FROM ind.v_cobertura_reportes_anual GROUP BY anio"""))
    d["reinc"] = uno("""SELECT SUM(IIF(tipo = 'REAPARICION', 1, 0)), SUM(IIF(tipo = 'DUPLICADO', 1, 0))
                        FROM ind.reporte_reaparicion""")
    d["cronicas"] = uno("SELECT COUNT(*) FROM ind.v_reincidencia_celda WHERE clasificacion = 'CRONICA'")[0]
    d["azcapo"] = uno("SELECT pct_reportes_en_cronicas FROM ind.v_reincidencia_territorio "
                      "WHERE territorio = 'AZCAPOTZALCO'")[0]
    d["causas"] = dict(todos("SELECT causa_probable, COUNT(*) FROM ind.v_causa_probable_bache GROUP BY causa_probable"))
    d["lluvias"] = dict(todos("""SELECT temporada_lluvias,
                                 COUNT(*) * 1.0 / COUNT(DISTINCT FORMAT(fecha_solicitud, 'yyyy-MM'))
                                 FROM reporte WHERE periodo_atipico = 0 AND id_fuente = 1 GROUP BY temporada_lluvias"""))
    d["contexto"] = uno("""SELECT COUNT(*), SUM(IIF(paradas_300m > 0, 1, 0)), COUNT(id_col),
                                  SUM(IIF(grado_marginacion IN ('Alto', 'Muy alto'), 1, 0))
                           FROM contexto_celda""")
    d["paradas"] = uno("SELECT COUNT(*) FROM parada_transporte")[0]
    d["milpa"] = uno("""SELECT COUNT(*) FROM reporte r JOIN colonia c ON c.id_colonia = r.id_colonia
                        JOIN territorio t ON t.id_territorio = c.id_territorio
                        WHERE t.nombre = 'MILPA ALTA' AND r.id_fuente = 1""")[0]
    cx.close()

    dw = pyodbc.connect("DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=SIPA_DW;"
                        "Trusted_Connection=yes").cursor()
    dw.execute("""SELECT COUNT(*) FROM (SELECT TOP 50 * FROM dm_priorizacion.v_reportes_vs_ipu
                  ORDER BY lugar_por_reportes) x WHERE lugar_por_ipu > 1000""")
    d["top50_tras_1000"] = dw.fetchone()[0]
    dw.execute("""SELECT TOP 2 colonia FROM dm_priorizacion.v_ranking_baches
                  WHERE territorio = 'CHALCO' ORDER BY ipu DESC""")
    d["chalco_top"] = [nombre(r[0]) for r in dw.fetchall()]
    return d


# ---------------------------------------------------------------------------
# Secciones
# ---------------------------------------------------------------------------

def portada(doc):
    for texto, tam, neg in [
        ("Universidad Nacional Rosario Castellanos", 14, True),
        ("Licenciatura en Ciencia de Datos para Negocios · Unidad Académica Chalco", 12, False),
        ("Tercer semestre · Semestre 2026-2", 12, False),
        ("", 12, False),
        ("Evidencia integradora del problema prototípico", 14, True),
        ("Bacheo inteligente y priorización urbana", 13, False),
        ("", 12, False),
        ("SIPA", 30, True),
        ("Sistema Inteligente de Priorización Asfáltica", 14, False),
        ("", 12, False),
        ("1. Prototipo funcional de la Plataforma de Bacheo Inteligente", 12, False),
        ("2. Plan de viabilidad y propuesta de intervenciones públicas basadas en evidencia", 12, False),
        ("", 12, False),
    ]:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(texto)
        r.font.size = Pt(tam)
        r.bold = neg
        if tam >= 14:
            r.font.color.rgb = AZUL
    tabla(doc, ["#", "Integrantes del equipo", "Matrícula"],
          [[1, "Sandra Luna Altos", ""], [2, "Joshua David Aquino", ""],
           [3, "Rebeca Jaimes Cruz", ""], [4, "Ithan Felipe Santiago", ""]], [1.2, 8, 4])
    tabla(doc, ["Dato", ""], [
        ["UCA que integra", "Fundamentos de Bases de Datos, Estructuras de Datos, Probabilidad, Cálculo Integral, "
                            "Contabilidad Financiera y Pensamiento Complejo para la Argumentación"],
        ["Grupo", "302"],
        ["Fecha de entrega", "[POR DEFINIR]"],
    ], [4, 9.5])
    doc.add_page_break()


def declaracion(doc):
    parrafo(doc, "El código del prototipo, los modelos y este documento se elaboraron con apoyo de IA "
                 "generativa (Claude, de Anthropic), con autorización de las y los docentes y dando el crédito "
                 "correspondiente. El equipo revisó, ejecutó y verificó los resultados, y es responsable de su "
                 "contenido. La percepción inicial de la sección 3.1 la escribe el equipo sin apoyo de IA.",
            "Declaración de uso de IA. ")


def introduccion(doc, d):
    titulo(doc, "1. El problema y nuestra respuesta")
    parrafo(doc, "El problema prototípico plantea la siguiente pregunta:")
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(1)
    p.add_run("«¿Cómo diseñar un sistema inteligente de priorización del mantenimiento vial que, mediante el "
              "análisis de datos y la integración de herramientas matemáticas, estadísticas, tecnológicas, "
              "financieras y sociales, permita determinar de manera transparente y equitativa qué vialidades "
              "deben ser atendidas primero […]?»").italic = True
    parrafo(doc, "Hoy un bache se atiende, sobre todo, porque alguien lo reportó o porque hubo presión. Así "
                 "quedan fuera el riesgo de accidente, el paso del transporte público, la vulnerabilidad de la "
                 "zona y el costo de esperar, y salen perdiendo las colonias que reportan menos: Milpa Alta tiene "
                 f"solo {d['milpa']} reportes en cuatro años.")
    parrafo(doc, "SIPA reúne en una base de datos los reportes ciudadanos y la información del entorno. Para "
                 "cada bache calcula un Índice de Prioridad Urbana (IPU) con diez criterios, lo traduce en un "
                 "semáforo (rojo: atender en 3 días; amarillo: en 15; verde: programar en 60), recomienda una "
                 "intervención y estima su costo. Cada recomendación incluye una ficha que muestra cuánto aportó "
                 "cada criterio, para que se pueda revisar y discutir.", "Nuestra respuesta. ")
    parrafo(doc, "Somos un equipo de asesoría técnica, como pide el problema prototípico. SIPA recomienda qué "
                 "atender, por qué y cuánto costaría, pero no repara. Las brigadas, el material y el presupuesto "
                 "son de la autoridad, que siempre toma la decisión final y después informa el avance. Así se mide "
                 "si la recomendación se siguió y en cuánto tiempo.", "Alcance. ")
    parrafo(doc, f"Trabajamos con datos reales: {d['reportes']:,} reportes de bacheo de la CDMX (2019-2022) y de "
                 "Chalco (2025-2026), 30,654 hechos de tránsito de la SSC, "
                 f"{d['paradas']:,} paradas de transporte público (GTFS de SEMOVI), el índice de marginación 2020 "
                 "por colonia (CONAPO) y el Atlas de Riesgo de Chalco. La severidad de los baches y la atención "
                 "que informa la autoridad son simuladas y así se declaran.", "Datos. ")
    parrafo(doc, "SIPA trabaja en dos niveles. El nivel operativo (qué bache atender primero) se probó en la "
                 "CDMX, porque ahí hay datos abiertos de baches georreferenciados; lo usan Probabilidad, Cálculo, "
                 "Estructuras de Datos, Bases de Datos y Pensamiento Complejo. El nivel financiero (cuánto le "
                 "cuestan al gobierno los baches que no atiende) se estimó para el Estado de México, como pidió el "
                 "incidente de Contabilidad, con el INEGI (accidentes por mala condición del camino y vehículos "
                 "registrados por municipio) y la Ley de Responsabilidad Patrimonial del Edomex. El segundo nivel "
                 "dimensiona el problema en la región de la UNRC Chalco y justifica llevar el piloto ahí.",
           "Dos territorios. ")


def prototipo(doc, d):
    titulo(doc, "2. Producto 1: prototipo funcional")
    parrafo(doc, "El prototipo tiene cuatro capas que trabajan sobre los mismos datos:")
    tabla(doc, ["Capa", "Qué hace", "Dónde está"], [
        ["Base de datos (SQL Server)",
         "Registra, almacena y relaciona los reportes, los baches, el contexto, los cálculos del IPU, las "
         "decisiones y el seguimiento. 32 tablas en tercera forma normal, con transacciones y restricciones "
         "que hacen cumplir las reglas (por ejemplo, no se puede ajustar una prioridad sin justificarla).",
         "bd/01 a 07, 13"],
        ["Modelos analíticos (Python)",
         "Riesgo de accidente a 72 h (Probabilidad), pérdida de material y costo de esperar (Cálculo), "
         "provisiones por reclamaciones (Contabilidad), cola de prioridad, eliminación de duplicados y rutas "
         "(Estructuras de Datos).", "probabilidad/, calculo/, contabilidad/, estructuras/"],
        ["Data Warehouse", "Base de análisis con tres tablas de hechos, dos datamarts y una réplica de solo "
                           "lectura para el tablero.", "bd/09 a 12"],
        ["Tablero (Streamlit)", "La interfaz: modo ciudadano, recomendación de SIPA, modo autoridad e "
                                "indicadores.", "tablero/app.py"],
    ], [3.5, 9.5, 3.5])
    parrafo(doc, "El recorrido completo de un bache en el tablero:", "Cómo se usa. ")
    vinetas(doc, [
        "El ciudadano reporta el bache sin crear una cuenta. Si ya existe un bache en la misma celda de 250 m, "
        "el reporte se une a él, así que se cuentan daños y no avisos repetidos.",
        "SIPA calcula el IPU, el semáforo, la intervención recomendada y el costo estimado, y muestra la ficha "
        "de justificación.",
        "La autoridad aprueba, ajusta o rechaza la recomendación (ajustar o rechazar exige escribir el motivo) "
        "e informa el avance: en atención, reparado con su costo real o descartado con el motivo.",
        "Cuando el bache se repara o se descarta, quien lo reportó recibe el aviso en su folio.",
    ])
    if (CAPTURAS / "p0.png").exists():
        figura(doc, CAPTURAS / "p0.png", "Figura 1. Resumen del tablero: indicadores clave, mapa de los baches "
                                         "abiertos por semáforo y costo pendiente por territorio.")
        figura(doc, CAPTURAS / "p2.png", "Figura 2. Recomendación de SIPA para Chalco: ranking y ficha de "
                                         "justificación del IPU de un bache.")
        figura(doc, CAPTURAS / "p3.png", "Figura 3. Modo autoridad: decisión sobre la recomendación e informe "
                                         "del avance.")
    else:
        parrafo(doc, "[Insertar las capturas del tablero: tablero/capturas/p0.png, p2.png y p3.png]")
    parrafo(doc, "La plataforma combina la ubicación del reporte (celda de 250 m), el nivel de deterioro "
                 f"(severidad, profundidad y área), el transporte público (paradas y salidas por día a 300 m; "
                 f"{d['contexto'][1]:,} de {d['contexto'][0]:,} celdas de la CDMX tienen servicio cerca), la "
                 "vulnerabilidad (marginación de la colonia), el riesgo de accidente, la inundación, la "
                 "cercanía a escuelas, hospitales y mercados, y el número de reportes, con un peso acotado.",
            "Información que integra. ")


def contraste(doc, d, v, sipa_ed, fifo):
    titulo(doc, "3. Producto 2: plan de viabilidad")
    parrafo(doc, "El plan sigue los cinco elementos que pide el problema prototípico. Empezamos por el "
                 "contraste entre percepción y evidencia, porque es el punto de partida del plan.")
    titulo(doc, "3.1 Contraste entre percepción y evidencia (inciso e)", 2)
    parrafo(doc, "[PARA EL EQUIPO: cada integrante escribe aquí, sin consultar los resultados de este documento, "
                 "qué intervenciones habría considerado prioritarias al iniciar el proyecto y por qué. Anotar la "
                 "fecha real en que se escribe. Después, llenar la última columna con ayuda de la "
                 "tabla 3.1b.]")
    tabla(doc, ["Integrante", "Fecha", "Intervención que consideraba prioritaria y por qué",
                "¿Se mantuvo, cambió o se descartó?"],
          [["Sandra Luna Altos", "", "", ""], ["Joshua David Aquino", "", "", ""],
           ["Rebeca Jaimes Cruz", "", "", ""], ["Ithan Felipe Santiago", "", "", ""]], [3.2, 2, 7, 3.8])
    parrafo(doc, "Tabla 3.1b. Percepciones frecuentes sobre el bacheo, puestas a prueba con los datos. Sirven "
                 "como referencia para la tabla anterior; no sustituyen la percepción del equipo.")
    lluvias, secas = float(d["lluvias"][True]), float(d["lluvias"][False])
    tabla(doc, ["Percepción", "Qué mostró la evidencia", "Resultado"], [
        ["Hay que atender primero los baches con más reportes.",
         f"{d['top50_tras_1000']} de los 50 baches con más reportes quedan después del lugar 1,000 por IPU. El "
         "número de reportes mide participación, no riesgo.", "Se modifica"],
        ["El orden de llegada es lo más justo.",
         f"Con orden de llegada, solo el {pct(fifo['rojos_en_3_dias'])} de los rojos se atiende en 3 días o "
         f"menos; con la cola de prioridad, el {pct(sipa_ed['rojos_en_3_dias'])}, con la misma espera promedio "
         f"({sipa_ed['todos']['espera_promedio']} días).", "Se descarta"],
        ["Priorizar resuelve por sí solo la falta de atención.",
         f"En lluvias llegan {v['llegadas_por_dia']['lluvias']} baches por día; con 15 reparaciones diarias la "
         "cola crece con cualquier orden. Ordenar no sustituye la capacidad.", "Se modifica"],
        ["Priorizar por riesgo es neutral entre zonas.",
         f"La cola pura amplía la brecha de espera entre alcaldías de {fifo['brecha_alcaldias']} a "
         f"{sipa_ed['brecha_alcaldias']} días.", "Surge el cupo de equidad"],
        ["Tapar baches basta.",
         f"{d['reinc'][0]:,} reapariciones y {d['cronicas']} celdas crónicas; en Azcapotzalco el {d['azcapo']} % de "
         "los reportes cae en ellas.", "Surge el reencarpetado"],
        ["Las lluvias no cambian mucho las cosas.",
         f"Llegan {lluvias:,.0f} reportes por mes en lluvias contra {secas:,.0f} en secas.",
         "Surge el bacheo preventivo antes de lluvias"],
    ], [4.3, 9, 3.2])
    parrafo(doc, "¿Qué se mantuvo, qué dejó de ser prioritario, qué surgió y qué evidencia lo decidió? "
                 "[PARA EL EQUIPO: responder en un párrafo a partir de las dos tablas.]")


def cuantitativo(doc, d, calc, prob, v):
    titulo(doc, "3.2 Análisis cuantitativo y de riesgo (inciso a)", 2)
    lluv = {x["meses"]: x for x in calc["tabla_perdida"] if x["temporada"] == "Lluvias"}
    pend = prob["pendientes"]
    parrafo(doc, "El IPU es una suma ponderada de diez criterios, cada uno entre 0 y 1. Los criterios sin datos "
                 "para un territorio valen 0.5 (neutral), para no premiar ni castigar la falta de información. "
                 "Hoy tienen datos reales el riesgo de accidente, el transporte, la vulnerabilidad, la "
                 "inundación (en Chalco), el acceso a servicios, los reportes y la recurrencia; personas "
                 "afectadas y tránsito siguen en 0.5 porque no hay aforos abiertos por calle.", "Índice de prioridad. ")
    parrafo(doc, f"Con {prob['accidentes']:,} hechos de tránsito, el modelo de Probabilidad estima para cada celda "
                 "la probabilidad de al menos un accidente en 72 horas con un proceso de Poisson y la usa en el "
                 f"criterio de riesgo del IPU. El semáforo por riesgo coincide con el del IPU en el "
                 f"{pct(pend['coinciden'])} de los baches pendientes; {pend['rojo72_no_rojo_ipu']} están en rojo "
                 "por riesgo sin estarlo en el IPU, porque el IPU pondera también otros criterios.",
            "Riesgo de accidente a 72 horas. ")
    parrafo(doc, f"Con Cálculo Integral, la pérdida de material es P(T) = V₀(e^(kT) − 1). En lluvias el daño "
                 f"crece {calc['factor_lluvias']:.2f} veces más rápido, un factor que sale de los reportes reales. "
                 f"Un bache típico cuesta {m(lluv[0]['costo'])} si se repara hoy y {m(lluv[6]['costo'])} tras 6 meses "
                 f"de lluvias. Para los {d['abiertos']:,} baches abiertos, esperar 6 meses cuesta "
                 f"{mm(calc['total_baches']['extra_6m'])} más. El intervalo óptimo de conservación preventiva es de "
                 f"unos {calc['intervalo_optimo']['promedio']:.0f} meses.", "Degradación y costo de esperar. ")
    rec = {r["temporada"]: r for r in v["recursos"]}
    parrafo(doc, f"Llegan {v['llegadas_por_dia']['lluvias']} baches nuevos por día en lluvias y "
                 f"{v['llegadas_por_dia']['secas']} en secas. Con 6 reparaciones por brigada al día, la autoridad "
                 f"necesitaría {int(rec['lluvias']['brigadas'])} brigadas en lluvias y {int(rec['secas']['brigadas'])} "
                 f"en secas, y unas {rec['lluvias']['toneladas_mes']:.0f} toneladas de mezcla al mes en lluvias.",
            "Recursos que se recomiendan a la autoridad. ")
    parrafo(doc, "Costo estimado para atender los baches abiertos, por tipo de intervención (tarifas del archivo "
                 "JSON de SIPA):")
    tabla(doc, ["Intervención recomendada", "Baches", "Costo estimado"],
          [[n, f"{b:,}", m(float(c))] for n, b, c in d["por_intervencion"]]
          + [["Total", f"{d['abiertos']:,}", m(float(d["costo_pendiente"]))]], [9, 2.5, 4])


def gestion(doc, d, exp, v, sipa_ed, cupo):
    titulo(doc, "3.3 Gestión y optimización de los datos y los recursos (inciso b)", 2)
    dd, ru = exp["desduplicacion"], exp["rutas"]
    vinetas(doc, [
        "Organización: la base relaciona territorio, colonia, celda, bache, reporte, contexto, cálculo, decisión "
        "y seguimiento. Lo que no cambia (coordenadas de la celda, tarifas, estatus) vive en catálogos, sin "
        "repetirse.",
        f"Eliminación de duplicados: una tabla hash revisa la celda y sus 8 vecinas y detecta {dd['duplicados']:,} "
        f"reportes duplicados en {dd['segundos_hash']:.1f} s ({dd['busquedas_hash']:,} búsquedas en lugar de "
        f"{dd['comparaciones_por_pares'] / 1e6:,.0f} millones de comparaciones).",
        "Orden de atención: un max-heap entrega el bache de mayor IPU en tiempo logarítmico. La prioridad sube "
        "un poco con la espera para que ningún bache se quede atrás para siempre.",
        f"Equidad: un cupo de 4 de cada 15 lugares para los baches que más han esperado reduce la brecha entre "
        f"alcaldías de {sipa_ed['brecha_alcaldias']} a {cupo['brecha_alcaldias']} días sin perder rojos.",
        f"Rutas: sobre un grafo de la red de celdas ({ru['vertices']} vértices), la ruta por vecino más cercano "
        f"recorre {ru['km_vecino_cercano']:.1f} km contra {ru['km_orden_prioridad']:.1f} km en orden de prioridad "
        f"({nombre(ru['alcaldia'])}), un {100 * (1 - ru['km_vecino_cercano'] / ru['km_orden_prioridad']):.0f} % menos.",
        "Transporte público: las paradas del GTFS entran al IPU, de modo que los baches por donde pasa más "
        "transporte suben de prioridad.",
        "Análisis: el Data Warehouse separa las consultas pesadas de la operación, y la réplica de solo lectura "
        "alimenta el tablero sin cargar la base principal.",
    ])


def financiera(doc, d, cont):
    titulo(doc, "3.4 Viabilidad financiera (inciso c)", 2)
    esc = {e["escenario"]: e for e in cont["escenarios"]}
    sup = cont["supuestos"]
    parrafo(doc, "Comparamos dos escenarios para los mismos baches abiertos: preventivo (se atienden según el "
                 "semáforo) y reactivo (se espera 180 días, como pasa hoy en muchos casos). Incluimos el costo de "
                 "reparar y la provisión por las reclamaciones que se esperan por accidentes y ponchaduras, según "
                 "la NIF C-9.")
    tabla(doc, ["Concepto", "Preventivo (SIPA)", "Reactivo"], [
        ["Costo de reparar", mm(esc["preventivo"]["costo_reparar"]), mm(esc["reactivo"]["costo_reparar"])],
        ["Provisión por reclamaciones", mm(esc["preventivo"]["provision_total"]), mm(esc["reactivo"]["provision_total"])],
        ["Costo total para el erario", mm(esc["preventivo"]["costo_total"]), mm(esc["reactivo"]["costo_total"])],
    ], [6, 4.5, 4.5])
    parrafo(doc, f"El esquema preventivo ahorra {mm(cont['ahorro_preventivo'])}. Aun sin contar ninguna "
                 f"ponchadura, el ahorro es de {mm(cont['sensibilidad'][0]['ahorro'])}, así que la conclusión no "
                 f"depende del supuesto más incierto. La plataforma requiere {mm(sup['equipo'])} en equipo y "
                 f"{mm(sup['software'])} en software, que se recuperan con el ahorro del primer año.")
    ed = leer("contabilidad/resultados_edomex/resumen.json")
    parrafo(doc, f"A escala del Estado de México, el valor esperado de las indemnizaciones por daños viales es "
                 f"{mm(ed['valor_esperado'])} al año (entre {mm(ed['percentil_5'])} y {mm(ed['percentil_95'])} con "
                 f"90 % de confianza), con unos {ed['casos_viables']:,.0f} casos viables. Es una provisión probable "
                 "según la NIF C-9 que hoy no aparece en los estados financieros.", "Estado de México. ")
    parrafo(doc, "El beneficio no es solo financiero: menos accidentes y menos tiempo de traslado para quienes "
                 "usan el transporte público, y una cifra auditable de cuánto debe el gobierno por los baches que "
                 "no atiende.")


def equidad(doc, d):
    titulo(doc, "3.5 Equidad social y justificación de las decisiones (inciso d)", 2)
    vinetas(doc, [
        f"El número de reportes pesa poco y en escala logarítmica, para no favorecer a las zonas con más acceso "
        f"digital (Milpa Alta: {d['milpa']} reportes en cuatro años).",
        f"La vulnerabilidad entra al IPU con el índice de marginación de CONAPO; {d['contexto'][3]:,} celdas tienen "
        "marginación alta o muy alta.",
        "El transporte público eleva la prioridad porque un bache en una ruta afecta a muchas más personas que "
        "uno en una calle local.",
        f"La atención no es pareja: Cuauhtémoc tiene reparado el {d['cobertura']['CUAUHTEMOC']:.0f} % de sus baches "
        f"y Tláhuac el {d['cobertura']['TLAHUAC']:.0f} %. Los reportes resueltos bajan de "
        f"{d['resueltos'][2019]} % en 2019 a {d['resueltos'][2022]} % en 2022. El cupo de equidad y el seguimiento "
        "por territorio hacen visible esa brecha.",
        f"Supervisión humana: la autoridad cambió la recomendación en {d['decisiones'].get('AJUSTAR', 0)} de "
        f"{sum(d['decisiones'].values())} casos, y cada cambio quedó registrado con su justificación. Los datos "
        "personales son opcionales, piden consentimiento y están en un esquema protegido que ni el tablero ni la "
        "autoridad pueden leer.",
    ])


def catalogo(doc, d, calc, cont, v, exp, sipa_ed, fifo, cupo):
    titulo(doc, "4. Propuesta de intervenciones públicas priorizadas")
    parrafo(doc, "Cada intervención se ordena por su impacto en la seguridad y el beneficio colectivo, y se "
                 "sustenta con evidencia técnica, cuantitativa, financiera y social.")
    tr = d["tiempos"]
    top = v["top_celdas"][0]
    ru, dd = exp["rutas"], exp["desduplicacion"]
    filas = [
        [1, "Atender los baches rojos en 72 horas o menos con la cola de prioridad",
         f"Con la cola, el {pct(sipa_ed['rojos_en_3_dias'])} de los rojos se atiende en 3 días o menos, contra "
         f"{pct(fifo['rojos_en_3_dias'])} por orden de llegada. Con la atención simulada, "
         f"{tr['ROJO'][4]:.0f} % de los rojos se reparó dentro de la meta.",
         "Sin costo adicional; evita la provisión por accidentes del esquema reactivo.",
         "Protege primero a quien tiene más riesgo.", "% de rojos reparados en 72 h"],
        [2, "Bacheo preventivo antes de la temporada de lluvias (abril-mayo)",
         f"El daño crece {calc['factor_lluvias']:.2f} veces más rápido en lluvias; intervalo preventivo óptimo de "
         f"{calc['intervalo_optimo']['promedio']:.0f} meses.",
         f"Esperar 6 meses cuesta {mm(calc['total_baches']['extra_6m'])} más; el preventivo ahorra "
         f"{mm(cont['ahorro_preventivo'])}.", "Menos baches en la época de más tránsito y lluvia.",
         "Costo por m² reparado"],
        [3, "Reencarpetar las celdas crónicas en lugar de bachearlas",
         f"{d['cronicas']} celdas con 3 o más reapariciones; la peor ({nombre(top['alcaldia'])}) tiene "
         f"{top['reincidencias']} reapariciones.",
         "Una inversión mayor por celda que evita repetir el bacheo cada año.",
         "Termina con el daño repetido en las mismas colonias.", "Reapariciones por celda al año"],
        [4, "Recomendar a la autoridad ajustar sus brigadas por temporada",
         f"{v['llegadas_por_dia']['lluvias']} baches/día en lluvias contra {v['llegadas_por_dia']['secas']} en "
         "secas; con 15 reparaciones/día la cola crece.",
         f"{int(v['recursos'][0]['brigadas'])} brigadas en lluvias y {int(v['recursos'][1]['brigadas'])} en secas.",
         "Evita que la espera crezca justo cuando más se usan las calles.", "Pendientes al cierre de mes"],
        [5, "Cupo de equidad: 4 de cada 15 lugares para los baches que más esperan",
         f"La brecha de espera entre alcaldías baja de {sipa_ed['brecha_alcaldias']} a {cupo['brecha_alcaldias']} "
         "días sin perder rojos.", "Sin costo adicional.",
         "Ninguna alcaldía queda siempre al final.", "Brecha de espera entre alcaldías"],
        [6, "Priorizar los baches sobre rutas de transporte público",
         f"{d['contexto'][1]:,} celdas de la CDMX tienen transporte a 300 m; el criterio ya entra al IPU con datos "
         "del GTFS.", "Sin costo adicional.", "Beneficia a quienes no tienen auto.",
         "Baches abiertos en rutas de transporte"],
        [7, "Rutas diarias por vecino más cercano",
         f"{100 * (1 - ru['km_vecino_cercano'] / ru['km_orden_prioridad']):.0f} % menos kilómetros en "
         f"{nombre(ru['alcaldia'])}.", "Ahorra combustible y horas de cuadrilla.",
         "Más reparaciones con la misma capacidad.", "Km por bache reparado"],
        [8, "Eliminar los reportes duplicados de forma automática",
         f"{dd['duplicados']:,} duplicados detectados en {dd['segundos_hash']:.1f} s.",
         "Evita pagar inspecciones repetidas.", "Cada daño cuenta una vez, sin importar cuántos lo reporten.",
         "Reportes duplicados"],
        [9, "Publicar la ficha de justificación de cada prioridad",
         f"La autoridad ajustó {d['decisiones'].get('AJUSTAR', 0)} de {sum(d['decisiones'].values())} "
         "recomendaciones, todas con motivo registrado.", "Sin costo adicional.",
         "La ciudadanía puede verificar por qué se atendió un bache antes que otro.",
         "Ajustes con justificación publicada"],
    ]
    tabla(doc, ["#", "Intervención", "Evidencia técnica y cuantitativa", "Evidencia financiera",
                "Evidencia social", "Indicador"], filas, [0.6, 3.2, 4.4, 3, 2.9, 2.4])
    parrafo(doc, f"Costo estimado de atender hoy los {d['abiertos']:,} baches abiertos: "
                 f"{mm(float(d['costo_pendiente']))}. Los territorios que más necesitan son "
                 + ", ".join(f"{nombre(t)} ({mm(float(c))})" for t, c in d["pend_territorio"]) + ". En Chalco, los "
                 f"primeros baches por atender están en {d['chalco_top'][0]} y {d['chalco_top'][1]}.")


def integracion(doc):
    titulo(doc, "5. Integración interdisciplinaria")
    parrafo(doc, "Cada asignatura resuelve una parte de la decisión, y los resultados de una alimentan a las "
                 "otras. Las cifras de este documento son las mismas en todos los entregables.")
    tabla(doc, ["Asignatura", "Qué aporta", "Cómo se usa en la decisión"], [
        ["Fundamentos de Bases de Datos", "Modelo entidad-relación, base normalizada, transacciones, Data "
         "Warehouse, datamarts, fragmentación y réplica",
         "Organiza todos los datos, calcula el IPU y guarda cada decisión para rendir cuentas"],
        ["Estructuras de Datos", "Lista enlazada, tabla hash, AVL, max-heap, pila de deshacer, grafo y Dijkstra",
         "Elimina duplicados, ordena la atención, reparte con equidad y traza rutas"],
        ["Probabilidad", "Proceso de Poisson, riesgo de accidente a 72 h, semáforo de riesgo",
         "Alimenta el criterio de riesgo del IPU y el cálculo de las provisiones"],
        ["Cálculo Integral", "Integral definida de la pérdida de material, valor presente, intervalo óptimo",
         "Dice cuánto cuesta esperar y cada cuánto conviene la conservación preventiva"],
        ["Contabilidad Financiera", "Provisiones NIF C-9, registro contable, estados financieros",
         "Compara el costo total preventivo contra el reactivo y propone controles"],
        ["Pensamiento Complejo", "Mapa de red de agentes, argumentación lógico-formal y dialéctica",
         "Explica las prioridades a vecinos y autoridades y anticipa sus objeciones"],
    ], [3.7, 6, 6.3])
    parrafo(doc, "Ejemplo de la cadena completa: un bache sobre una vía rápida en lluvias recibe un riesgo alto "
                 "(Probabilidad), sube en la cola (Estructuras de Datos) y en el IPU (Bases de Datos); su costo "
                 "crece si espera (Cálculo), y ese costo y la reclamación probable se reconocen como provisión "
                 "(Contabilidad). La autoridad decide con esa ficha y la explica a los vecinos (Pensamiento "
                 "Complejo).")


def dilemas(doc, d, cont):
    titulo(doc, "6. Respuesta a los dilemas del problema prototípico")
    tabla(doc, ["Dilema", "Nuestra respuesta"], [
        ["¿Mayor flujo vehicular o población más vulnerable?",
         "Las dos cosas entran al IPU con pesos explícitos y configurables por territorio, y el cupo de equidad "
         "evita que las zonas vulnerables esperen siempre."],
        ["¿El bache con más reportes o el de mayor riesgo?",
         f"El de mayor riesgo. Los reportes cuentan, pero acotados: {d['top50_tras_1000']} de los 50 más reportados "
         "no están entre los 1,000 primeros por IPU."],
        ["¿Lo más visible o el mantenimiento preventivo?",
         f"El preventivo: ahorra {mm(cont['ahorro_preventivo'])} y al menos {mm(cont['sensibilidad'][0]['ahorro'])} "
         "aun con supuestos conservadores."],
        ["¿Invertir hoy en un sistema cuyos beneficios llegan después?",
         "Sí: la inversión en la plataforma se recupera con el ahorro del primer año."],
        ["¿Hasta dónde decide el algoritmo?",
         "SIPA recomienda y la autoridad decide. Ajustar o rechazar exige un motivo, y queda registrado."],
        ["¿Criterios técnicos pero comprensibles?",
         "Cada prioridad tiene una ficha que muestra cuánto aportó cada criterio, y los pesos son públicos y "
         "tienen fecha de vigencia."],
    ], [5.5, 10.5])


def limitaciones(doc):
    titulo(doc, "7. Limitaciones y siguientes pasos")
    vinetas(doc, [
        "La severidad de los baches y la atención que informa la autoridad son simuladas; los tiempos y los "
        "costos reportados son ilustrativos.",
        "Las tarifas de reparación son una estimación del equipo; deben sustituirse por el tabulador oficial.",
        "Personas afectadas y tránsito siguen en valor neutral por falta de aforos abiertos por calle.",
        "Las fuentes de transporte, marginación y riesgo solo cubren la CDMX; en Chalco esos criterios son "
        "neutrales.",
        "Los pesos del IPU son ilustrativos: el siguiente paso es definirlos con el método AHP "
        "(pesos/AHP_pesos_IPU.xlsx).",
        "La unidad espacial es una cuadrícula de 250 m, no la red de calles; el siguiente paso es cargar la red "
        "vial de OpenStreetMap o INEGI.",
    ])


def referencias(doc):
    titulo(doc, "Referencias")
    for r in [
        "Base maestra de solicitudes de bacheo de la Ciudad de México 2019-2022 [Conjunto de datos]. Proporcionada "
        "para el problema prototípico (base_maestra_baches_2019_2024.csv).",
        "Comisión Nacional de Población. (2021). Índice de marginación urbana 2020 [Conjunto de datos]. CONAPO.",
        "Gobierno de la Ciudad de México. (2025, 20 de agosto). Arrancamos con el Programa Integral de Bacheo "
        "Nocturno en la Ciudad de México. Jefatura de Gobierno.",
        "Gobierno Municipal de Chalco. (2026). Datos abiertos del municipio de Chalco [Conjunto de datos]. "
        "https://datosabiertos.chalco.gob.mx",
        "Highway Research Board. (1962). The AASHO Road Test, Report 5: Pavement Research (Special Report 61E).",
        "Instituto Nacional de Estadística y Geografía. (2024). Estadística de Accidentes de Tránsito Terrestre en "
        "Zonas Urbanas y Suburbanas (ATUS) 2024. INEGI.",
        "Instituto Nacional de Estadística y Geografía. (2024). Vehículos de motor registrados en circulación "
        "1980-2023 [Conjunto de datos]. INEGI.",
        "Legislatura del Estado de México. (2017, reforma 2023). Ley de Responsabilidad Patrimonial para el Estado "
        "de México y Municipios. Gaceta del Gobierno.",
        "Meadows, D. H. (2008). Thinking in systems: A primer. Chelsea Green Publishing.",
        "Saaty, T. L. (1980). The analytic hierarchy process. McGraw-Hill.",
        "Secretaría de Movilidad. (2021). GTFS [Conjunto de datos]. Portal de Datos Abiertos de la Ciudad de México. "
        "https://datos.cdmx.gob.mx/dataset/gtfs",
        "Secretaría de Seguridad Ciudadana de la Ciudad de México. (s. f.). Hechos de tránsito registrados por la SSC "
        "[Conjunto de datos]. Portal de Datos Abiertos de la Ciudad de México.",
        "Toulmin, S. (2003). Los usos de la argumentación. Península.",
    ]:
        p = doc.add_paragraph(r)
        p.paragraph_format.left_indent = Cm(1)
        p.paragraph_format.first_line_indent = Cm(-1)


def anexo(doc):
    titulo(doc, "Anexo. Cómo ejecutar el prototipo y entregables por asignatura", 2)
    tabla(doc, ["Paso", "Comando o archivo"], [
        ["1. Construir la base, el Data Warehouse y la réplica", "powershell -File bd\\ejecutar_todo.ps1"],
        ["2. Correr los modelos", "python probabilidad/riesgo_72h.py · python calculo/degradacion.py · "
                                  "python contabilidad/provisiones.py · python contabilidad/contingencias_edomex.py · "
                                  "python estructuras/viabilidad.py"],
        ["3. Abrir el tablero", "streamlit run tablero/app.py"],
        ["Bases de Datos", "avance2_BD_entrega.docx"],
        ["Estructuras de Datos", "avance2_ED_plan_viabilidad.docx"],
        ["Probabilidad", "avance2_Probabilidad_semaforo72h.docx"],
        ["Cálculo Integral", "avance2_Calculo_degradacion.docx"],
        ["Contabilidad Financiera", "avance2_Contabilidad_NIF_C9.docx"],
        ["Contabilidad (incidente Edomex)", "avance_Contabilidad_contingencias_Edomex.docx"],
        ["Pensamiento Complejo", "avance2_PensamientoComplejo_argumentacion.docx"],
    ], [6, 10])


def main():
    d = datos_base()
    calc = leer("calculo/resultados/resumen.json")
    prob = leer("probabilidad/resultados/resumen.json")
    cont = leer("contabilidad/resultados/resumen.json")
    v = leer("estructuras/resultados/viabilidad.json")
    exp = leer("estructuras/resultados/resumen.json")
    eq = v["equidad"]
    fifo, sipa_ed, cupo = eq["FIFO"], eq["SIPA β=0.10"], eq["SIPA + cupo"]

    doc = Document()
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(11)
    for s in doc.sections:
        s.left_margin = s.right_margin = Cm(2.2)

    portada(doc)
    declaracion(doc)
    introduccion(doc, d)
    prototipo(doc, d)
    contraste(doc, d, v, sipa_ed, fifo)
    cuantitativo(doc, d, calc, prob, v)
    gestion(doc, d, exp, v, sipa_ed, cupo)
    financiera(doc, d, cont)
    equidad(doc, d)
    catalogo(doc, d, calc, cont, v, exp, sipa_ed, fifo, cupo)
    integracion(doc)
    dilemas(doc, d, cont)
    limitaciones(doc)
    referencias(doc)
    anexo(doc)
    doc.save(SALIDA)
    print(f"Documento generado: {SALIDA}")


if __name__ == "__main__":
    main()
