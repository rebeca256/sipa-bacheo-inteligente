"""
SIPA - Genera el documento de la 2ª entrega de Fundamentos de Bases de Datos:
el desarrollo del proyecto relacionado con la planeación didáctica de la UCA
(temas, productos de aprendizaje y criterios de cada rúbrica).

Uso (desde la carpeta del proyecto):
    python scripts/generar_doc_planeacion_bd.py
Salida:
    avance2_BD_planeacion.docx
"""

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor, Cm

SALIDA = "avance2_BD_planeacion.docx"
AZUL = RGBColor(0x1F, 0x3A, 0x5F)
GRIS = "D9E2EC"

ESTADO = {"ok": "Cumplido", "parcial": "Parcial", "pend": "Pendiente"}


# ---------------------------------------------------------------------------
# Utilidades de formato
# ---------------------------------------------------------------------------

def sombrear(celda, color):
    tcPr = celda._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), color)
    tcPr.append(shd)


def tabla(doc, encabezados, filas, anchos=None):
    t = doc.add_table(rows=1, cols=len(encabezados))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(encabezados):
        c = t.rows[0].cells[i]
        c.text = ""
        r = c.paragraphs[0].add_run(h)
        r.bold = True
        r.font.size = Pt(9.5)
        sombrear(c, GRIS)
    for fila in filas:
        celdas = t.add_row().cells
        for i, v in enumerate(fila):
            celdas[i].text = ""
            r = celdas[i].paragraphs[0].add_run(str(v))
            r.font.size = Pt(9.5)
    if anchos:
        for fila in t.rows:
            for i, a in enumerate(anchos):
                fila.cells[i].width = Cm(a)
    doc.add_paragraph()
    return t


def parrafo(doc, texto, negrita_inicial=None):
    p = doc.add_paragraph()
    if negrita_inicial:
        p.add_run(negrita_inicial).bold = True
    p.add_run(texto)
    return p


def vinetas(doc, items):
    for it in items:
        doc.add_paragraph(it, style="List Bullet")


def titulo(doc, texto, nivel=1):
    h = doc.add_heading(texto, level=nivel)
    for r in h.runs:
        r.font.color.rgb = AZUL
    return h


# ---------------------------------------------------------------------------
# Contenido
# ---------------------------------------------------------------------------

def portada(doc):
    for texto, tam, neg in [
        ("Universidad Nacional Rosario Castellanos", 14, True),
        ("Licenciatura en Ciencia de Datos para Negocios", 12, False),
        ("Unidad Académica Chalco", 12, False),
        ("Tercer semestre · Semestre 2026-2", 12, False),
        ("", 12, False),
        ("Problema prototípico: Bacheo inteligente y priorización urbana", 12, False),
        ("SIPA", 28, True),
        ("Sistema Inteligente de Priorización Asfáltica", 14, False),
        ("", 12, False),
        ("Segunda entrega · Fundamentos de Bases de Datos", 14, True),
        ("Desarrollo del proyecto y su relación con la planeación didáctica", 12, False),
        ("", 12, False),
    ]:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(texto)
        r.font.size = Pt(tam)
        r.bold = neg
        if tam >= 14:
            r.font.color.rgb = AZUL

    tabla(doc, ["#", "Integrantes del equipo"],
          [[1, "Sandra Luna Altos"], [2, "Joshua David Aquino"],
           [3, "Rebeca Jaimes Cruz"], [4, "Ithan Felipe Santiago"]], [1.5, 10])
    tabla(doc, ["Dato", ""],
          [["UCA", "Fundamentos de Bases de Datos (LCDN3FUN8)"],
           ["Docente", "Rosa Graciela Castro Carrera"],
           ["Grupo", "302"],
           ["Gestor de base de datos", "Microsoft SQL Server 2025"],
           ["Fecha de entrega", "13 de noviembre de 2026"]], [4.5, 7])
    doc.add_page_break()


def introduccion(doc):
    titulo(doc, "1. Introducción")
    parrafo(doc, "La planeación de la UCA plantea la siguiente pregunta:")
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(1)
    r = p.add_run("«¿Cómo ayuda la UCA de Bases de Datos a diseñar e implementar una estructura de información "
                  "confiable que permita organizar, relacionar, consultar y manipular los datos del deterioro vial, "
                  "para contribuir al funcionamiento de la Plataforma de Bacheo Inteligente y a la toma de "
                  "decisiones públicas basadas en evidencia?»")
    r.italic = True
    parrafo(doc, "Nuestra respuesta es SIPA, cuya base de datos se construyó en los tres niveles que pide la "
                 "planeación (conceptual, lógico y físico) y se complementa con un Data Warehouse para el análisis. "
                 "Este documento muestra, tema por tema y criterio por criterio de cada rúbrica, qué hicimos, "
                 "dónde está la evidencia y qué falta.")
    parrafo(doc, "La base trabaja con datos reales: ", "Datos. ")
    vinetas(doc, [
        "Base maestra de solicitudes de bacheo de la CDMX 2019-2022: 35,629 reportes válidos tras la limpieza.",
        "Datos abiertos del municipio de Chalco (datosabiertos.chalco.gob.mx): 68 reportes de bacheo 2025-2026, "
        "55 comunidades del Bando 2026, 23 zonas inundables del Atlas de Riesgo 2023, 473 escuelas, "
        "28 hospitales y 44 mercados.",
        "Datos sintéticos, declarados como tales: severidad y medidas de los baches, y la atención simulada de 300 "
        "baches que la autoridad decide e informa como reparados. Las tarifas de reparación vienen de un JSON "
        "ilustrativo.",
    ])


def mapa_general(doc):
    titulo(doc, "2. Mapa de la planeación al proyecto")
    tabla(doc, ["Tema de la UCA", "Producto de aprendizaje", "Evidencia en SIPA"], [
        ["1. Datos", "(base para todos los productos)",
         "Limpieza documentada de la base maestra CDMX y de los datos de Chalco, con bitácoras y registros excluidos"],
        ["2. Teoría de diseño de bases de datos relacionales",
         "Modelo Entidad-Relación y modelo relacional normalizado",
         "MER_SIPA.md (diagrama y justificación de 1FN, 2FN y 3FN)"],
        ["3. Sistema Administrador de Bases de Datos Relacionales (RDBMS)",
         "Base de datos implementada",
         "Scripts 01 a 07: 32 tablas, 39 llaves foráneas, 56 restricciones CHECK, 5 procedimientos y 2 roles"],
        ["4. Gestión y análisis distribuido (transacciones, DW, datamarts, replicación, fragmentación)",
         "Prototipo de gestión y análisis distribuido de datos",
         "Scripts 05 y 08 a 12, DW_SIPA.md: base SIPA_DW, ETL, 2 datamarts, consultas OLAP, partición por año, "
         "réplica de solo lectura"],
    ], [4, 4.5, 7.5])


def figura(doc, ruta, ancho_cm, pie):
    """Imagen centrada con su pie de figura (las imágenes salen de bd/img con mermaid-cli)."""
    doc.add_picture(ruta, width=Cm(ancho_cm))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(pie)
    r.italic = True
    r.font.size = Pt(9)


def rubrica(doc, nombre, producto, filas):
    titulo(doc, nombre, 2)
    parrafo(doc, producto, "Producto: ")
    tabla(doc, ["Criterio de la rúbrica", "Valor", "Cómo lo cumple SIPA", "Evidencia", "Estado"],
          [[c, v, como, ev, ESTADO[e]] for c, v, como, ev, e in filas],
          [3.6, 1.2, 6.2, 3.2, 1.8])


def rubricas(doc):
    titulo(doc, "3. Cumplimiento de cada rúbrica")

    rubrica(doc, "3.1 Rúbrica del modelo conceptual y lógico (tema 2)",
            "Modelo Entidad-Relación (MER) y modelo relacional normalizado de la Plataforma de Bacheo Inteligente.", [
        ("Identificación de entidades y atributos de acuerdo con la problemática", "20%",
         "Entidades de los seis ámbitos del problema: territorio y ubicación; baches y reportes; contexto (aforo, "
         "rutas, accidentes, zonas inundables, equipamiento); priorización (criterios, pesos, cálculos, decisiones "
         "humanas, tarifas de costo); seguimiento que informa la autoridad (estados y notificaciones; sin logística, "
         "notificaciones).", "MER_SIPA.md", "ok"),
        ("Definición de relaciones y cardinalidades", "20%",
         "Relaciones 1:N (territorio-colonia, bache-reporte), 1:1 opcional (reporte-contacto ciudadano) y N:M "
         "resuelta con tabla puente (ruta de transporte-tramo).", "MER_SIPA.md, notación de pata de gallo", "ok"),
        ("Elaboración correcta del MER", "20%",
         "Diagrama con 27 entidades (figura 1), sus atributos, llaves y cardinalidades.", "MER_SIPA.md", "ok"),
        ("Transformación del MER al modelo relacional", "20%",
         "Cada entidad es una tabla con llave primaria; cada relación, una llave foránea; la relación N:M, una tabla "
         "con llave compuesta.", "01_crear_bd.sql", "ok"),
        ("Normalización para evitar redundancia e inconsistencias", "15%",
         "3FN: año, mes y alcaldía no se repiten en reporte (se derivan de la fecha y de la colonia); el estatus "
         "agrupado vive en un catálogo; las coordenadas de la celda viven en su tabla.",
         "MER_SIPA.md, sección de normalización", "ok"),
        ("Presentación, organización y claridad", "5%",
         "Diagrama comentado y tabla de decisiones de diseño.", "MER_SIPA.md", "ok"),
    ])
    figura(doc, "bd/img/MER_SIPA.png", 16.5,
           "Figura 1. Modelo entidad-relación de SIPA (notación de pata de gallo). Fuente: bd/MER_SIPA.md.")

    rubrica(doc, "3.2 Rúbrica del modelo físico (tema 3)",
            "Base de datos implementada de la Plataforma de Bacheo Inteligente en SQL Server.", [
        ("Creación de tablas de acuerdo con el modelo relacional", "25%",
         "32 tablas creadas tal como aparecen en el MER, organizadas en los esquemas dbo y priv.",
         "01_crear_bd.sql", "ok"),
        ("Tipos de datos, llaves primarias y foráneas", "20%",
         "Tipos ajustados a cada dato: DECIMAL(9,6) para coordenadas, DATE y DATETIME2 para fechas, TINYINT para "
         "escalas, BIT para marcas, GEOGRAPHY para zonas y puntos. 32 llaves primarias (algunas compuestas).",
         "01_crear_bd.sql", "ok"),
        ("Relaciones entre tablas mediante llaves foráneas", "20%",
         "39 llaves foráneas con nombre explícito (fk_tabla_referencia).", "01_crear_bd.sql", "ok"),
        ("Restricciones de integridad", "15%",
         "56 CHECK (por ejemplo: severidad entre 1 y 5, motivo obligatorio al descartar un bache, costo real solo "
         "al repararlo, justificación obligatoria si la autoridad cambia una prioridad), 9 UNIQUE, "
         "16 DEFAULT y un índice único filtrado para los folios.", "01_crear_bd.sql", "ok"),
        ("Uso correcto de SQL y del RDBMS", "15%",
         "DDL (CREATE, esquemas, índices), DML (BULK INSERT de 35,629 registros, INSERT…SELECT, UPDATE con JOIN), "
         "procedimientos almacenados, cursores y funciones geográficas (STDistance).",
         "Scripts 01 a 07", "ok"),
        ("Organización y presentación de evidencias", "5%",
         "Scripts numerados y comentados; ejecutar_todo.ps1 reconstruye la base desde cero y termina sin errores.",
         "Carpeta bd/", "ok"),
    ])

    rubrica(doc, "3.3 Rúbrica del prototipo de gestión y análisis distribuido (tema 4)",
            "Transacciones, Data Warehouse, datamart y propuesta de replicación y fragmentación.", [
        ("Transacciones para garantizar consistencia e integridad", "20%",
         "Procedimientos con BEGIN TRAN / COMMIT / ROLLBACK. Ejemplo: cuando la autoridad marca un bache como "
         "reparado o descartado, se cambia su estado, se registra el seguimiento y se notifica a cada reporte, todo "
         "o nada. La demostración descarta un bache sin motivo y comprueba que nada cambia. Las cargas masivas "
         "también son transaccionales.",
         "05_procedimientos_transacciones.sql, 07_demo_y_consultas.sql (parte B)", "ok"),
        ("Diseño de un Data Warehouse según las necesidades del proyecto", "20%",
         "Base separada SIPA_DW con 7 dimensiones y 3 tablas de hechos (reporte, priorización, atención), "
         "alimentada por un ETL transaccional con bitácora.", "09_dw_crear.sql, 10_dw_etl.sql, DW_SIPA.md", "ok"),
        ("Diseño de un datamart orientado al análisis vial", "20%",
         "Dos datamarts: priorización (ranking, semáforo por territorio, celdas críticas, reportes vs. IPU) y "
         "financiero (costo estimado vs. reportado, cumplimiento de tiempos, inversión por intervención). Consultas OLAP: ROLLUP, CUBE, GROUPING "
         "SETS, PIVOT, drill-down, slice/dice y ventanas.", "09_dw_crear.sql, 11_dw_consultas_olap.sql", "ok"),
        ("Aplicación de replicación para mejorar la disponibilidad", "15%",
         "Implementada: réplica de solo lectura SIPA_REPLICA por log shipping (respaldo completo restaurado en modo "
         "STANDBY y envío del registro de transacciones con sp_replicar). La demostración comprueba que los cambios "
         "llegan a la réplica, que esta rechaza escrituras y que el rol del tablero no puede leer datos personales.",
         "12_replicacion.sql, DW_SIPA.md, sección 6", "ok"),
        ("Aplicación de fragmentación según las características de la información", "15%",
         "Implementada: la tabla de hechos de reportes está particionada por año (función y esquema de partición). "
         "Propuesta adicional: fragmentación horizontal por territorio.", "09_dw_crear.sql, DW_SIPA.md", "ok"),
        ("Organización, claridad y presentación de evidencias", "10%",
         "Documento DW_SIPA.md con diagrama en estrella, ETL, datamarts y tabla de particiones.", "DW_SIPA.md", "ok"),
    ])
    figura(doc, "bd/img/DW_SIPA.png", 16.5,
           "Figura 2. Esquema en constelación del Data Warehouse SIPA_DW: 3 tablas de hechos que comparten "
           "7 dimensiones. Fuente: bd/DW_SIPA.md.")


def resultados(doc):
    titulo(doc, "4. Resultados que la base permite obtener")
    parrafo(doc, "La base no solo almacena datos: responde preguntas del problema prototípico.")
    tabla(doc, ["Pregunta", "Resultado", "Consulta"], [
        ["¿Influye la temporada de lluvias?",
         "Casi el doble de reportes por mes en lluvias (~1,147) que en secas (~639).", "07, C2"],
        ["¿Qué alcaldías turnan más reportes a otras áreas?",
         "Tláhuac (32%), Tlalpan (26%) y Álvaro Obregón (24%).", "07, C4"],
        ["¿Más reportes significa más prioridad?",
         "No siempre: baches entre los 50 con más reportes quedan después del lugar 1,000 por IPU.", "11, P4"],
        ["¿La autoridad sigue siempre al modelo?",
         "Cambió la recomendación en 31 de 301 casos, y cada cambio quedó justificado.", "11, P5"],
        ["¿Qué baches de Chalco atender primero?",
         "Los de Unión de Guadalupe y San Miguel Jacalones II: cerca de zonas inundables y con muchos servicios alrededor.",
         "11, P1"],
        ["¿Dónde vuelve a salir el bache después de repararlo?",
         "2,271 reapariciones y 161 celdas crónicas (3 o más); en Azcapotzalco el 21.7% de los reportes cae en "
         "ellas. Son candidatas a reencarpetado, no a bacheo.", "13, ind.v_reincidencia_*"],
        ["¿Se cumplen los tiempos de atención?",
         "Con la atención simulada, los rojos tardan 2.7 días (60% dentro de la meta de 3) y los amarillos 14.6 "
         "(52% dentro de la meta de 15).", "13, ind.v_tiempo_respuesta_*"],
        ["¿Todas las alcaldías reciben la misma atención?",
         "No: Cuauhtémoc tiene reparado el 43% de sus baches y Tláhuac el 2%. Los reportes resueltos bajan de "
         "97.5% (2019) a 67.9% (2022).", "13, ind.v_cobertura_*"],
    ], [5, 8.5, 2.5])


def modelo_educativo(doc):
    titulo(doc, "5. Vinculación con el modelo educativo")
    tabla(doc, ["Eje", "Cómo se refleja en la base de datos"], [
        ["Pensamiento crítico",
         "Se contrastan los reportes ciudadanos con el IPU; se documentan las limitaciones de cada fuente "
         "(por ejemplo, solo 75 reportes en Chalco en 17 meses)."],
        ["Actuación ética profesional",
         "Privacidad desde el diseño: los datos de contacto van en un esquema aparte, son opcionales, requieren "
         "consentimiento y, en la réplica, el rol del tablero tiene prohibido leerlos. Todos los datos sintéticos "
         "están declarados."],
        ["Responsabilidad social",
         "Toda prioridad requiere aprobación humana con justificación registrada; los pesos del IPU se guardan por "
         "territorio y con vigencia, para que cualquier cambio sea auditable."],
        ["Diversidad e inclusión",
         "El número de reportes tiene un peso acotado para no favorecer zonas con más acceso digital "
         "(Milpa Alta: 133 reportes en 4 años). Se agregaron criterios de vulnerabilidad, inundación y acceso a "
         "servicios."],
    ], [4, 12])


def limitaciones(doc):
    titulo(doc, "6. Limitaciones y trabajo pendiente")
    vinetas(doc, [
        "La réplica está en la misma instancia que la base principal y se actualiza a mano; en producción iría en "
        "otro servidor y la actualizaría el Agente de SQL Server.",
        "La base maestra no incluye calle, severidad ni fecha de cierre; se usa una cuadrícula de 250 m como unidad "
        "espacial y la severidad es sintética.",
        "En la CDMX, tres criterios ya usan datos reales (IPU v0.4): riesgo de accidente a 72 h (modelo de "
        "Probabilidad), transporte público (GTFS de SEMOVI) y vulnerabilidad (índice de marginación 2020 de "
        "CONAPO por colonia). Personas afectadas y tránsito siguen en 0.5, igual que transporte, vulnerabilidad "
        "y riesgo en Chalco, porque esas fuentes solo cubren la CDMX.",
        "Las órdenes de trabajo del Data Warehouse son simuladas: los tiempos y el cumplimiento de meta son "
        "ilustrativos.",
        "El ETL hace una carga completa, no incremental.",
    ])


def anexo(doc):
    titulo(doc, "Anexo. Archivos entregados y cómo ejecutarlos")
    tabla(doc, ["Archivo", "Contenido"], [
        ["bd/01_crear_bd.sql", "Diseño físico: tablas, llaves, restricciones e índices"],
        ["bd/02_catalogos.sql", "Catálogos y criterios del IPU"],
        ["bd/03_carga_base_maestra.sql", "Carga de los 35,629 reportes de la CDMX y pesos del IPU"],
        ["bd/04_datos_sinteticos.sql", "Baches sintéticos (severidad, profundidad, área)"],
        ["bd/05_procedimientos_transacciones.sql", "Procedimientos con transacciones y roles ciudadano/autoridad"],
        ["bd/05b_riesgo_72h.sql", "Riesgo de accidente a 72 h por celda (modelo de Probabilidad) para el IPU"],
        ["bd/05c_transporte_marginacion.sql", "Paradas del GTFS y marginación CONAPO por colonia, resumidas por celda"],
        ["bd/06_carga_chalco.sql", "Datos abiertos de Chalco: comunidades, reportes, zonas inundables, equipamiento"],
        ["bd/07_demo_y_consultas.sql", "Recorrido completo de un reporte, ROLLBACK y consultas de análisis"],
        ["bd/08_simular_operacion.sql", "Historial operativo simulado para el Data Warehouse"],
        ["bd/09_dw_crear.sql", "Data Warehouse, partición por año y datamarts"],
        ["bd/10_dw_etl.sql", "Proceso ETL"],
        ["bd/11_dw_consultas_olap.sql", "Consultas OLAP y de datamarts"],
        ["bd/12_replicacion.sql", "Réplica de solo lectura (log shipping) y su demostración"],
        ["bd/13_vistas_indicadores.sql", "Indicadores: reincidencia, tiempo de respuesta y cobertura (esquema ind)"],
        ["bd/img/", "Imágenes del MER y del DW (generadas con mermaid-cli desde los .md)"],
        ["bd/MER_SIPA.md", "Modelo entidad-relación y normalización"],
        ["bd/DW_SIPA.md", "Data Warehouse, datamarts, fragmentación y replicación"],
        ["scripts/limpiar_base_maestra.py, scripts/procesar_chalco.py", "Limpieza de datos (Python)"],
    ], [6.5, 9.5])
    parrafo(doc, "desde la carpeta bd, ejecutar en PowerShell: powershell -ExecutionPolicy Bypass -File "
                 ".\\ejecutar_todo.ps1. Reconstruye SIPA, SIPA_DW y SIPA_REPLICA en aproximadamente un minuto. Antes, ajustar "
                 "las rutas de los CSV en los scripts 03 y 06.", "Para reconstruir todo: ")
    parrafo(doc, "el diagrama del MER (MER_SIPA.md) y el del Data Warehouse (DW_SIPA.md) se pueden ver en "
                 "VS Code o exportar como imagen desde mermaid.live para insertarlos en este documento.",
            "Diagramas: ")


def main():
    doc = Document()
    estilo = doc.styles["Normal"]
    estilo.font.name = "Calibri"
    estilo.font.size = Pt(11)
    for s in doc.sections:
        s.left_margin = s.right_margin = Cm(2.2)

    portada(doc)
    introduccion(doc)
    mapa_general(doc)
    rubricas(doc)
    resultados(doc)
    modelo_educativo(doc)
    limitaciones(doc)
    anexo(doc)
    doc.save(SALIDA)
    print(f"Documento generado: {SALIDA}")


if __name__ == "__main__":
    main()
