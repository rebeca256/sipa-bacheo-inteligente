"""
SIPA - Genera el documento de estrategia de argumentación de Pensamiento Complejo
para la Argumentación, en formato APA 7.ª ed. (ejecutar antes pensamiento/mapa_red.py).

Uso (desde la carpeta del proyecto):
    python pensamiento/mapa_red.py
    python scripts/generar_doc_pensamiento.py
Salida:
    avance2_PensamientoComplejo_argumentacion.docx  (exportarlo a PDF para entregar)
"""

from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

RES = Path("pensamiento/resultados")
SALIDA = "avance2_PensamientoComplejo_argumentacion.docx"
FUENTE = "Times New Roman"


# ---------------------------------------------------------------------------
# Formato APA 7
# ---------------------------------------------------------------------------

def configurar(doc):
    st = doc.styles["Normal"]
    st.font.name = FUENTE
    st.element.rPr.rFonts.set(qn("w:eastAsia"), FUENTE)
    st.font.size = Pt(12)
    pf = st.paragraph_format
    pf.line_spacing_rule = WD_LINE_SPACING.DOUBLE
    pf.space_before = pf.space_after = Pt(0)
    for s in doc.sections:
        s.top_margin = s.bottom_margin = s.left_margin = s.right_margin = Cm(2.54)
        numero_pagina(s.header.paragraphs[0])


def numero_pagina(p):
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = p.add_run()
    for tipo, texto in [("begin", None), (None, "PAGE"), ("end", None)]:
        if tipo:
            e = OxmlElement("w:fldChar")
            e.set(qn("w:fldCharType"), tipo)
        else:
            e = OxmlElement("w:instrText")
            e.set(qn("xml:space"), "preserve")
            e.text = texto
        r._r.append(e)


def h1(doc, texto):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True
    p.add_run(texto).bold = True


def h2(doc, texto):
    p = doc.add_paragraph()
    p.paragraph_format.keep_with_next = True
    p.add_run(texto).bold = True


def par(doc, texto, negrita=None, sangria=True):
    p = doc.add_paragraph()
    if sangria:
        p.paragraph_format.first_line_indent = Cm(1.27)
    if negrita:
        p.add_run(negrita).bold = True
    p.add_run(texto)
    return p


def lista(doc, items):
    for t in items:
        p = doc.add_paragraph(style="List Bullet")
        if isinstance(t, tuple):
            p.add_run(t[0]).bold = True
            p.add_run(t[1])
        else:
            p.add_run(t)


def rotulo(doc, numero, titulo, tipo="Tabla"):
    """Rótulo APA: número en negritas y título en cursiva, arriba de la tabla o figura."""
    p = doc.add_paragraph()
    p.paragraph_format.keep_with_next = True
    p.add_run(f"{tipo} {numero}").bold = True
    p = doc.add_paragraph()
    p.paragraph_format.keep_with_next = True
    p.add_run(titulo).italic = True


def tabla(doc, encabezados, filas, anchos):
    t = doc.add_table(rows=1, cols=len(encabezados))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.style = "Table Grid"
    for i, e in enumerate(encabezados):
        c = t.rows[0].cells[i]
        c.text = ""
        c.paragraphs[0].add_run(e).bold = True
    for f in filas:
        cells = t.add_row().cells
        for i, v in enumerate(f):
            cells[i].text = str(v)
    for fila in t.rows:
        for i, c in enumerate(fila.cells):
            c.width = Cm(anchos[i])
            for p in c.paragraphs:
                p.paragraph_format.line_spacing = 1.0
                for r in p.runs:
                    r.font.size = Pt(10)
    doc.add_paragraph()
    return t


def figura(doc, numero, titulo, archivo, ancho=16):
    rotulo(doc, numero, titulo, "Figura")
    doc.add_picture(str(RES / archivo), width=Cm(ancho))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER


def nota(doc, texto):
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.0
    p.add_run("Nota. ").italic = True
    r = p.add_run(texto)
    r.font.size = Pt(10)
    doc.add_paragraph()


def referencia(doc, texto):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(1.27)
    p.paragraph_format.first_line_indent = Cm(-1.27)
    p.add_run(texto)


# ---------------------------------------------------------------------------
# Contenido
# ---------------------------------------------------------------------------

def caratula(doc):
    for _ in range(2):
        doc.add_paragraph()
    for texto, negrita in [
        ("Universidad Nacional Rosario Castellanos", True),
        ("Unidad Académica Chalco", False),
        ("Licenciatura en Ciencia de Datos para Negocios", False),
        ("", False),
        ("SIPA: una estrategia de argumentación para priorizar el bacheo con evidencia y acuerdos", True),
        ("", False),
        ("Pensamiento Complejo para la Argumentación (TR3PEC6)", False),
        ("Grupo 302 · Semestre 2026-2", False),
        ("", False),
        ("Sandra Luna Altos · Matrícula: [matrícula]", False),
        ("Joshua David Aquino · Matrícula: [matrícula]", False),
        ("Rebeca Jaimes Cruz · Matrícula: [matrícula]", False),
        ("Ithan Felipe Santiago · Matrícula: [matrícula]", False),
        ("", False),
        ("Docente: [nombre de la persona docente]", False),
        ("1 de noviembre de 2026", False),
    ]:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.add_run(texto).bold = negrita
    doc.add_page_break()


def main():
    doc = Document()
    configurar(doc)
    caratula(doc)

    # 1 -----------------------------------------------------------------
    h1(doc, "Síntesis del problema prototípico")
    par(doc, "Los baches afectan la movilidad, la seguridad vial, los costos de transporte y la calidad de vida. "
             "Hoy la mayoría de los gobiernos los atiende de forma reactiva: repara donde llegan más quejas o donde "
             "la presión es más visible. El problema prototípico pide transformar esa gestión mediante un sistema de "
             "bacheo inteligente y un modelo de priorización multicriterio que use datos de tránsito, siniestralidad, "
             "transporte público y vulnerabilidad social, y que permita justificar de forma transparente y "
             "equitativa qué se repara primero, manteniendo la supervisión humana.")
    par(doc, "Nuestra propuesta es SIPA (Sistema Inteligente de Priorización Asfáltica). Integra los reportes "
             "ciudadanos de la Ciudad de México (35,629 registros de 2019 a 2022) y de Chalco, los hechos de "
             "tránsito de la Secretaría de Seguridad Ciudadana y datos de riesgo como las zonas inundables. Con ellos "
             "calcula un Índice de Prioridad Urbana (IPU) y un semáforo de riesgo a 72 horas. SIPA asesora: la "
             "decisión y la reparación son de la autoridad, y cada cambio queda registrado.")
    par(doc, "Este documento sostiene que el bacheo no es un problema técnico aislado, sino un sistema social "
             "complejo, y propone una estrategia de argumentación para que los agentes involucrados lleguen a "
             "acuerdos pacíficos sobre cómo priorizar.")

    # 2 -----------------------------------------------------------------
    h1(doc, "El bacheo como sistema social complejo")
    par(doc, "La mirada lineal dice: «hay un bache, alguien lo reporta, se repara». Bajo esa lógica, la calle con "
             "más reportes debería atenderse primero. Pero nuestros datos contradicen esa idea: varios de los 50 "
             "baches con más reportes de la ciudad quedan después del lugar 1,000 cuando se ordenan por riesgo e "
             "impacto. Morin (1998) llama simplificación a este tipo de pensamiento que separa lo que está unido y "
             "reduce lo múltiple a una sola causa. El bacheo es complejo, y no solo complicado, porque sus "
             "elementos están entretejidos y se transforman entre sí.")
    par(doc, "Tres principios del pensamiento complejo ayudan a verlo:")
    lista(doc, [
        ("Principio recursivo. ", "Los efectos se vuelven causas. Reparar tarde hace que el bache crezca (en "
         "lluvias, 1.8 veces más rápido según nuestros datos), lo que encarece la reparación, reduce lo que alcanza "
         "el presupuesto y deja más baches esperando. Es un círculo vicioso (Figura 1)."),
        ("Principio dialógico. ", "Lógicas opuestas conviven y se necesitan: eficiencia y equidad, datos y "
         "experiencia de campo, recomendación del modelo y criterio humano. En nuestras pruebas, la persona "
         "autoridad cambió la recomendación del modelo en 31 de 301 casos; ninguna de las dos lógicas basta "
         "sola."),
        ("Principio hologramático. ", "La parte contiene al todo: un solo bache en Chalco reúne el subsuelo "
         "arcilloso, el drenaje insuficiente, el tránsito de carga hacia la autopista México–Cuautla y la baja "
         "participación digital de la comunidad."),
    ])
    par(doc, "También hay orden y caos. La temporada de lluvias casi duplica los reportes por mes (1,147 contra "
             "639 en secas), un patrón ordenado; pero cada bache aparece en un lugar y momento imprevisibles. SIPA "
             "no intenta eliminar la incertidumbre: la mide con probabilidades y la comunica con un semáforo.")
    figura(doc, 1, "Ciclos de retroalimentación del sistema de bacheo", "g2_ciclos.png")
    nota(doc, "Los ciclos 1 y 2 se refuerzan solos (R) y empeoran el problema; el ciclo 3 es el que SIPA busca "
              "activar. Elaboración propia con datos de la base maestra de bacheo de la CDMX (2019-2022).")
    par(doc, "El segundo ciclo muestra la desigualdad oculta: Milpa Alta registró solo 133 reportes en cuatro años "
             "y Chalco 75 en 17 meses. Pocas quejas no significan pocos baches; pueden significar que la gente no "
             "tiene cómo reportar o ya no confía en que se atiendan. Un sistema que solo cuenta reportes hace "
             "invisibles a esas comunidades.")

    # 3 -----------------------------------------------------------------
    h1(doc, "Agentes que intervienen en el fenómeno")
    par(doc, "Un agente es cualquier actor con capacidad de influir en el sistema (agencia). Identificamos 17, "
             "agrupados en cinco tipos. La Tabla 1 describe a los principales.")
    rotulo(doc, 1, "Agentes del sistema de bacheo y su interés principal")
    tabla(doc, ["Agente", "Descripción", "Interés principal"], [
        ["Ciudadanía conductora", "Personas que manejan automóvil o motocicleta", "Calles sin daño; no pagar reparaciones del vehículo"],
        ["Peatones y ciclistas", "Las personas más vulnerables en la vía", "Seguridad física"],
        ["Usuarios del transporte público", "Mayoría de los viajes en la zona metropolitana", "Rutas rápidas y seguras"],
        ["Comunidades con poca participación digital", "Zonas rurales o periféricas (Milpa Alta, Chalco)", "Ser vistas y atendidas"],
        ["Transportistas de carga", "Vehículos pesados en vías primarias", "Circular sin restricciones"],
        ["Alcaldías y Ayuntamiento de Chalco", "Gobierno local responsable de vías secundarias", "Respuesta visible a sus habitantes"],
        ["Secretaría de Obras (SOBSE)", "Responsable de vías primarias en la CDMX", "Cumplir metas con presupuesto limitado"],
        ["Finanzas y Auditoría", "Asignan y fiscalizan el gasto", "Gasto justificado y sin pasivos sorpresa"],
        ["Organismo del agua (SACMEX, ODAPAS)", "Drenaje y redes hidráulicas", "Hacer sus obras, que abren el pavimento"],
        ["SSC y servicios de emergencia", "Registran y atienden accidentes", "Reducir siniestros"],
        ["Autoridad (alcaldía o municipio)", "Valida o corrige la recomendación de SIPA e informa el avance", "Decidir bien y poder justificarlo"],
        ["Brigadas y contratistas", "Ejecutan la reparación por encargo de la autoridad", "Trabajo programado y pagado a tiempo"],
        ["Medios y redes sociales", "Amplifican quejas", "Historias visibles"],
        ["SIPA y el equipo universitario", "Modelo, datos y su diseño", "Que la decisión se base en evidencia"],
        ["Lluvia, suelo y drenaje", "Entorno físico, agente no humano", "No tiene intereses, pero condiciona a todos"],
    ], [4.2, 5.8, 6])

    # 4 -----------------------------------------------------------------
    h1(doc, "Problemática de cada agente")
    par(doc, "Cada agente vive el problema de forma distinta. Reconocerlo es el primer paso para argumentar sin "
             "imponer (Tabla 2).")
    rotulo(doc, 2, "Problemática de cada agente y evidencia que la respalda")
    tabla(doc, ["Agente", "Problemática", "Evidencia"], [
        ["Ciudadanía conductora", "Daños al vehículo; siente que reportar no sirve",
         "Hasta 36 ponchaduras esperadas en 72 h por un bache profundo en vía rápida (escenario)"],
        ["Peatones y ciclistas", "Riesgo de caída y de accidente grave; casi no reportan", "Las celdas con baches tienen 1.38 veces más accidentes"],
        ["Usuarios del transporte", "Rutas lentas y desgaste de unidades", "El IPU incluye el criterio de transporte público"],
        ["Comunidades poco digitales", "Invisibilidad: sin reportes no hay atención", "Milpa Alta: 133 reportes en 4 años; Chalco: 75 en 17 meses"],
        ["Transportistas", "Se les culpa del daño; también lo sufren", "El daño crece con la cuarta potencia del peso por eje"],
        ["Alcaldías y Chalco", "Presión por resultados visibles; turnan reportes que no les tocan",
         "Tláhuac turna el 32 % de sus reportes a otras áreas"],
        ["SOBSE", "Presupuesto insuficiente para tanta demanda", "En lluvias se rebasa la capacidad diaria más de 1 de cada 4 días"],
        ["Finanzas y Auditoría", "Pasivos ocultos por reclamaciones de daños",
         "Esperar 6 meses cuesta $1.81 M más en reparación y eleva la provisión por reclamaciones"],
        ["Organismo del agua", "Sus obras rompen el pavimento sin coordinarse con obras", "El agua y el suelo arcilloso explican la reincidencia"],
        ["Autoridad (alcaldía o municipio)", "Decidir entre el modelo y la presión política", "Cambió 31 de 301 recomendaciones, con registro"],
        ["Brigadas", "Trabajo urgente sin planeación; baches que reaparecen", "Reincidencia en zonas inundables"],
        ["SIPA y el equipo", "Datos incompletos (sin aforos, severidad simulada)", "Cinco criterios del IPU aún usan valores neutros"],
    ], [3.6, 6.2, 6.2])

    # 5 -----------------------------------------------------------------
    h1(doc, "Mapa de red de agentes y problemáticas")
    par(doc, "La Figura 2 conecta a los agentes. Las líneas continuas son intercambios (información, recursos, "
             "órdenes) y las punteadas, tensiones o conflictos. El mapa revela tres hallazgos:")
    lista(doc, [
        ("SIPA es un nodo de mediación. ", "Recibe información de la ciudadanía, la SSC y el avance que informa la "
         "autoridad, y la entrega a quien decide y a quien paga. Si la red pasa por un modelo verificable, las tensiones se "
         "discuten con datos y no solo con fuerza política."),
        ("Las alcaldías concentran tensiones. ", "Reciben la presión de medios y peatones, disputan "
         "competencias con la Secretaría de Obras y presionan a la autoridad que decide. Ahí se debe negociar."),
        ("El entorno físico no se puede negociar. ", "La lluvia y el suelo afectan a todos, pero nadie los "
         "representa en la mesa; el organismo del agua es el agente que más puede hacer y el menos conectado."),
    ])
    figura(doc, 2, "Mapa de red de los agentes del bacheo y sus problemáticas", "g1_mapa_red_agentes.png")
    nota(doc, "Elaboración propia. Los colores indican el tipo de agente.")

    # 6 -----------------------------------------------------------------
    h1(doc, "Estrategia de argumentación para un arreglo pacífico")
    par(doc, "Nuestra tesis es: ", None)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run("Los baches deben priorizarse por su riesgo y su impacto en las personas, medidos con criterios "
              "públicos y acordados, y no solo por el número de reportes o la presión de quien más se hace "
              "escuchar.").italic = True
    par(doc, "Para sostenerla usamos el modelo de Toulmin (2007), que separa cada parte del argumento y obliga a "
             "reconocer sus límites (Tabla 3).")
    rotulo(doc, 3, "Estructura del argumento central según el modelo de Toulmin")
    tabla(doc, ["Elemento", "Contenido"], [
        ["Dato", "Baches con muchos reportes quedan después del lugar 1,000 por riesgo; 285 baches pendientes "
                 "tienen riesgo alto de accidente a 72 h y no están en rojo en el índice actual"],
        ["Garantía", "Un recurso público limitado debe dirigirse a donde evita más daño a más personas"],
        ["Respaldo", "Modelos de probabilidad (Poisson, Bayes) con 30,654 accidentes reales; costo de esperar "
                     "calculado con integrales; NIF C-9 para las reclamaciones"],
        ["Calificador", "Probablemente: los datos tienen límites (severidad simulada, sin aforos)"],
        ["Refutación", "Salvo que la comunidad aporte información que el modelo no ve; por eso existe la "
                       "supervisión humana y los pesos se acuerdan"],
        ["Conclusión", "Priorizar con el IPU y el semáforo de riesgo, con revisión humana y criterios acordados"],
    ], [3.5, 12.5])
    h2(doc, "Argumentación lógico-formal")
    par(doc, "Si un bache permanece abierto, su reparación cuesta más y su riesgo de causar daños aumenta. En "
             "lluvias, los baches permanecen abiertos más tiempo porque se rebasa la capacidad. Por lo tanto, en "
             "lluvias, cada día de espera cuesta más y pone en riesgo a más personas (modus ponens). Y si atender "
             "a tiempo cuesta $4.74 M y esperar $12.31 M para los mismos 1,345 baches, esperar no es una decisión "
             "racional para ningún agente que pague o sufra el daño.")
    h2(doc, "Argumentación dialéctica: objeciones y réplicas")
    par(doc, "Argumentar para la paz no es ganar la discusión, sino tomar en serio la postura contraria. La Tabla "
             "4 anticipa las objeciones de cada agente.")
    rotulo(doc, 4, "Objeciones previsibles y réplicas")
    tabla(doc, ["Agente", "Objeción", "Réplica constructiva"], [
        ["Alcaldía", "«Mi gente se queja de este bache y el modelo no lo pone primero»",
         "El reporte sigue contando en el IPU, y la autoridad puede subir la prioridad justificándolo. Lo que no "
         "cambia es que la decisión quede registrada y sea pública."],
        ["Ciudadanía", "«Una máquina decide qué calle se arregla»",
         "El modelo recomienda; decide una persona. Los criterios y sus pesos son públicos y se acuerdan con la "
         "comunidad."],
        ["Finanzas", "«No hay dinero para un programa preventivo»",
         "Prevenir es más barato: el esquema preventivo ahorra al menos $2.8 M aun con supuestos conservadores."],
        ["Transportistas", "«Nos culpan del daño a las calles»",
         "No se trata de culpar: las vías de carga necesitan revisiones más frecuentes, lo que también los "
         "beneficia."],
        ["Comunidades periféricas", "«A nosotros nunca nos toca»",
         "SIPA limita el peso de los reportes y agrega criterios de vulnerabilidad y acceso a servicios, para que "
         "reportar poco no signifique quedar fuera."],
    ], [3, 5.2, 7.8])
    par(doc, "La estrategia se apoya en la cultura de paz en el sentido de Galtung (1998): no basta con evitar el "
             "conflicto abierto; hay que atender la violencia estructural, en este caso la desigualdad que hace "
             "invisibles a las comunidades que reportan poco.")

    # 7 -----------------------------------------------------------------
    h1(doc, "Recursos de habilidades blandas que se movilizan")
    par(doc, "Las habilidades duras del equipo (programación, estadística, bases de datos) producen la evidencia; "
             "las habilidades blandas hacen que esa evidencia se escuche y se convierta en acuerdo. A continuación "
             "explicamos cada una y cómo se usa en este caso.")
    for nombre, texto in [
        ("Empatía. ", "Ponerse en el lugar del otro. Antes de presentar datos, reconocemos que el vecino que "
         "reportó cinco veces el mismo bache tiene razón en estar molesto, aunque su bache no sea el más riesgoso."),
        ("Escucha atenta. ", "Escuchar para entender, no para responder. En las mesas de diálogo, la comunidad "
         "puede aportar lo que el modelo no ve: una escuela sin acceso, un bache que siempre reaparece."),
        ("Comunicación asertiva. ", "Decir con claridad lo que sabemos y lo que no, sin agredir ni ceder la "
         "evidencia. Por ejemplo: «El modelo indica que este bache tiene bajo riesgo; si conocen algo que no "
         "estemos viendo, lo revisamos»."),
        ("Pensamiento crítico. ", "Cuestionar también nuestros resultados. Por eso declaramos los límites del "
         "modelo, como la severidad simulada o la falta de aforos, en lugar de presentarlo como infalible."),
        ("Negociación. ", "Buscar acuerdos basados en intereses y no en posiciones (Fisher et al., 2011). La "
         "alcaldía no quiere «ese bache primero»; quiere que su gente vea respuesta. Un tablero público de avance "
         "puede satisfacer ese interés."),
        ("Inteligencia emocional. ", "Reconocer y regular emociones propias y ajenas (Goleman, 1995). En una "
         "reunión tensa, bajar el tono y volver a los datos evita que la discusión se vuelva personal."),
        ("Trabajo colaborativo y liderazgo compartido. ", "Cada integrante del equipo lidera la parte que domina "
         "(datos, base de datos, modelos, comunicación); las decisiones del proyecto se tomaron por consenso."),
        ("Adaptabilidad y flexibilidad. ", "Cuando el docente propuso nuevos criterios (inundación, acceso a "
         "servicios), los integramos al índice en lugar de defender el diseño original."),
        ("Ética y responsabilidad. ", "Proteger los datos personales de quienes reportan y no ocultar que algunas "
         "cifras son estimaciones."),
        ("Paciencia y gestión del tiempo. ", "Los acuerdos entre gobierno y comunidad toman tiempo; la "
         "estrategia se plantea por fases con fechas."),
    ]:
        par(doc, texto, nombre)

    # 8 -----------------------------------------------------------------
    h1(doc, "Estrategia para alcanzar acuerdos pacíficos")
    par(doc, "Proponemos un proceso en cinco fases, inspirado en los principios de negociación de Fisher et al. "
             "(2011): separar a las personas del problema, centrarse en intereses, inventar opciones de beneficio "
             "mutuo y usar criterios objetivos.")
    lista(doc, [
        ("1. Mapeo y escucha. ", "Reuniones por separado con cada grupo de agentes para conocer sus intereses y "
         "problemáticas (Tablas 1 y 2). Se usa la encuesta de percepción del proyecto."),
        ("2. Diagnóstico compartido. ", "Se presentan los datos de forma accesible: mapas, el semáforo y los "
         "hallazgos (por ejemplo, que más reportes no significan más riesgo). El objetivo es que todos vean el "
         "mismo problema antes de discutir soluciones."),
        ("3. Construcción de criterios. ", "Una mesa con representantes de cada grupo acuerda los pesos de los "
         "criterios del IPU mediante comparación por pares (Saaty, 1980). Así el criterio objetivo no lo impone "
         "el equipo técnico: lo construyen los agentes."),
        ("4. Acuerdos y reglas. ", "Se firman compromisos concretos: tiempos de atención por color del semáforo, "
         "coordinación de obras con el organismo del agua, un cupo de atención para comunidades con pocos "
         "reportes y la regla de que todo cambio de prioridad se justifique por escrito."),
        ("5. Seguimiento y transparencia. ", "Un tablero público muestra los indicadores (tiempo de respuesta, "
         "reincidencia, cobertura por territorio) y cada seis meses se revisan los pesos con la misma mesa."),
    ])
    par(doc, "Esta estrategia convierte el conflicto en un proceso de aprendizaje colectivo: los datos alimentan "
             "el diálogo y el diálogo mejora los datos, que es el círculo virtuoso de la Figura 1.")

    # 9 -----------------------------------------------------------------
    h1(doc, "Reflexión metacognitiva")
    par(doc, "Al empezar el proyecto pensábamos el bacheo como un problema de ingeniería: detectar el bache y "
             "repararlo. Al cruzar datos de distintas fuentes y leer los documentos sobre Chalco, descubrimos que "
             "las causas están en el agua, el suelo, la desigualdad digital y la forma en que se reparte el poder "
             "de decidir. Aprendimos que un buen modelo no basta si los agentes no confían en él, y que argumentar "
             "también significa reconocer lo que el modelo no sabe.")

    # Referencias ---------------------------------------------------------
    doc.add_page_break()
    h1(doc, "Referencias")
    for ref in [
        "Fisher, R., Ury, W., & Patton, B. (2011). Obtenga el sí: El arte de negociar sin ceder (3.ª ed.). Gestión 2000.",
        "Galtung, J. (1998). Tras la violencia, 3R: Reconstrucción, reconciliación, resolución. Bakeaz; Gernika Gogoratuz.",
        "Goleman, D. (1995). La inteligencia emocional. Javier Vergara.",
        "Morin, E. (1998). Introducción al pensamiento complejo. Gedisa.",
        "Saaty, T. L. (1980). The analytic hierarchy process. McGraw-Hill.",
        "Secretaría de Seguridad Ciudadana de la Ciudad de México. (2019). Hechos de tránsito registrados por la "
        "SSC [Conjunto de datos]. Portal de Datos Abiertos de la Ciudad de México. https://datos.cdmx.gob.mx",
        "Toulmin, S. (2007). Los usos de la argumentación. Península.",
    ]:
        referencia(doc, ref)

    doc.save(SALIDA)
    print(f"Documento generado: {SALIDA}")


if __name__ == "__main__":
    main()
