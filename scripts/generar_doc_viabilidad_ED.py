"""
SIPA - Genera el plan de viabilidad y la propuesta de intervenciones públicas (2º producto
de la evidencia integradora, UCA Estructuras de Datos) a partir de los resultados de
estructuras/experimentos.py, estructuras/viabilidad.py y de Cálculo, Probabilidad y Contabilidad.

Uso (desde la carpeta del proyecto):
    python estructuras/experimentos.py
    python estructuras/viabilidad.py
    python scripts/generar_doc_viabilidad_ED.py
Salida:
    avance2_ED_plan_viabilidad.docx

Desarrollado con apoyo de IA generativa (Claude, de Anthropic), con autorización de la
docente y crédito declarado. El equipo revisó y es responsable del contenido.
"""

import json
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt

from generar_doc_planeacion_bd import AZUL, parrafo, tabla, titulo, vinetas

ED = Path("estructuras/resultados")
SALIDA = "avance2_ED_plan_viabilidad.docx"


def leer(ruta):
    return json.loads(Path(ruta).read_text(encoding="utf-8"))


def figura(doc, ruta, pie, ancho=15):
    doc.add_picture(str(ruta), width=Cm(ancho))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(pie)
    r.italic = True
    r.font.size = Pt(9)


def pct(x):
    return f"{100 * x:.0f} %"


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
        ("Evidencia integradora · Producto 2", 14, True),
        ("Plan de viabilidad y propuesta de intervenciones públicas basadas en evidencia", 12, False),
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
          [["UCA", "Estructuras de Datos (LCDN3EST8)"],
           ["Docente", "Luisa Reyna Beatriz Ayon Muñoz"],
           ["Grupo", "302"],
           ["Fecha de entrega", "[fecha]"]], [4.5, 7])
    doc.add_page_break()


def main():
    exp = leer(ED / "resumen.json")
    v = leer(ED / "viabilidad.json")
    calc = leer("calculo/resultados/resumen.json")
    prob = leer("probabilidad/resultados/resumen.json")
    cont = leer("contabilidad/resultados/resumen.json")

    eq = v["equidad"]
    fifo, sipa, cupo = eq["FIFO"], eq["SIPA β=0.10"], eq["SIPA + cupo"]
    cap = {c["capacidad"]: c for c in v["capacidad"]}
    rec = {r["temporada"]: r for r in v["recursos"]}
    ll = v["llegadas_por_dia"]
    efi = exp["eficiencia"][-1]
    dd = exp["desduplicacion"]
    ru = exp["rutas"]
    esc = {e["escenario"]: e for e in cont["escenarios"]}
    pct_reinc = 100 * v["baches_en_celdas_reincidencia_3"] / v["baches_total"]
    extra_cap = 35 - 15
    lluv = {x["meses"]: x for x in calc["tabla_perdida"] if x["temporada"] == "Lluvias"}
    costo_bache, costo_bache_6m = lluv[0]["costo"], lluv[6]["costo"]
    costo_extra_mes = extra_cap * 30 * costo_bache
    costo_esperar = calc["total_baches"]["extra_6m"]

    doc = Document()
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(11)
    for s in doc.sections:
        s.left_margin = s.right_margin = Cm(2.2)

    portada(doc)

    parrafo(doc, "Este documento y el código que lo sustenta (estructuras/viabilidad.py y "
                 "scripts/generar_doc_viabilidad_ED.py) se elaboraron con apoyo de IA generativa "
                 "(Claude, de Anthropic), con autorización de la docente y dando el crédito "
                 "correspondiente. El equipo revisó, ejecutó y verificó los resultados, y es "
                 "responsable de su contenido.", "Declaración de uso de IA. ")

    # 1 -----------------------------------------------------------------
    titulo(doc, "1. Propósito")
    parrafo(doc, "Actuamos como un equipo de asesoría técnica que presenta recomendaciones a una "
                 "administración pública. La pregunta que guía el plan no es «¿qué bache se reportó "
                 "primero?», sino «¿qué intervención debe realizarse primero para reducir el mayor "
                 "riesgo y generar el mayor beneficio social con los recursos disponibles?». Cada "
                 "intervención propuesta se respalda con resultados del prototipo funcional "
                 "(producto 1) y de los modelos de Cálculo, Probabilidad y Contabilidad.")
    parrafo(doc, f"Datos: {exp['desduplicacion']['reportes']:,} reportes reales de baches de la CDMX "
                 f"(2019-2022, sin periodos atípicos), 30,654 accidentes de la SSC y los 1,345 baches "
                 "pendientes de la base SIPA. La severidad, los costos y la productividad de las "
                 "brigadas son supuestos declarados en la sección 9.")

    # 2 -----------------------------------------------------------------
    titulo(doc, "2. Contraste entre percepción y evidencia")
    parrafo(doc, "La propuesta inicial del equipo (Fase 0) se escribió antes del análisis de "
                 "datos. En la tabla, la primera columna transcribe esa propuesta y las siguientes "
                 "la contrastan con la evidencia.")
    parrafo(doc, "[PENDIENTE DEL EQUIPO: transcribir aquí la propuesta inicial fechada. "
                 "Las filas siguientes son percepciones frecuentes que el análisis permite poner a "
                 "prueba; sustituirlas o completarlas con las del equipo.]")
    tabla(doc, ["Percepción inicial", "Qué mostró la evidencia", "Resultado"], [
        ["Hay que atender primero los baches con más reportes ciudadanos.",
         "Varios de los 50 baches con más reportes quedan después del lugar 1,000 por IPU. "
         "El número de reportes mide la participación, no el riesgo.", "Se modifica"],
        ["El orden de llegada (FIFO) es lo más justo.",
         f"Con FIFO solo el {pct(fifo['rojos_en_3_dias'])} de los baches rojos se atiende en 3 días o menos; "
         f"con SIPA, el {pct(sipa['rojos_en_3_dias'])}, con la misma espera promedio "
         f"({sipa['todos']['espera_promedio']} días).", "Se descarta"],
        ["Un sistema de priorización resuelve por sí solo la falta de atención.",
         f"Con 15 reparaciones/día y {ll['lluvias']} llegadas/día en lluvias, la cola crece igual con "
         f"cualquier política ({fifo['pendientes_al_final']:,} pendientes al día 90). Ordenar no sustituye a la capacidad.",
         "Se modifica"],
        ["Priorizar por riesgo es neutral entre zonas.",
         f"El heap puro amplía la brecha de espera entre alcaldías de {fifo['brecha_alcaldias']} a "
         f"{sipa['brecha_alcaldias']} días (Cuajimalpa, Tláhuac y Magdalena Contreras esperan más).",
         "Surge una intervención nueva (cupo de equidad)"],
        ["Tapar baches basta.",
         f"{v['celdas_reincidencia_3']} celdas de 250 m tienen 3 o más reapariciones y concentran "
         f"{v['baches_en_celdas_reincidencia_3']:,} baches ({pct_reinc:.1f} %). Ahí el bacheo no resuelve.",
         "Surge una intervención nueva (reencarpetado)"],
        ["Esperar a tener más presupuesto es prudente.",
         f"Dejar 6 meses de lluvias los 1,345 baches pendientes cuesta ${costo_esperar / 1e6:.2f} M más (Cálculo) "
         f"y el esquema reactivo cuesta ${esc['reactivo']['costo_total'] / 1e6:.2f} M contra "
         f"${esc['preventivo']['costo_total'] / 1e6:.2f} M (Contabilidad).", "Se descarta"],
    ], [4.5, 9, 3])
    parrafo(doc, "Preguntas de la rúbrica (responder con base en la Fase 0): ¿qué intervenciones "
                 "iniciales se mantuvieron?, ¿cuáles dejaron de ser prioritarias y por qué?, ¿qué "
                 "intervenciones nuevas surgieron? (el cupo de equidad, el ajuste de brigadas por "
                 "temporada y el reencarpetado de celdas reincidentes) y ¿qué evidencia cambió o "
                 "confirmó cada decisión? (la tabla anterior).")

    # 3 -----------------------------------------------------------------
    titulo(doc, "3. Análisis cuantitativo y de riesgo")
    titulo(doc, "3.1 Clasificación del riesgo", 2)
    vinetas(doc, [
        "IPU simplificado del prototipo: severidad (0.45), riesgo de accidente a 72 h (0.40) y "
        "reportes acotados a 10 (0.15). Semáforo: rojo ≥ 0.60, amarillo ≥ 0.40.",
        f"Riesgo a 72 h (Probabilidad): N ~ Poisson(λ·RR·3/365), con λ por Bayes empírico y RR = "
        f"{prob['riesgo']['rr']:.2f}. Un bache profundo en vía rápida tiene P(accidente en 72 h) mediana "
        f"de {100 * prob['incidente']['p72_accidente_mediana']:.1f} % y de "
        f"{100 * prob['incidente']['p72_accidente_p90']:.1f} % en el percentil 90.",
        f"Por alcaldía, Cuauhtémoc (12.4 % de baches en rojo, riesgo medio 0.38) y Venustiano Carranza "
        f"(9.3 %) concentran el riesgo; Milpa Alta, Tláhuac y Magdalena Contreras están por debajo de 1 %.",
    ])
    tabla(doc, ["Alcaldía", "Baches", "% rojos", "% reincidencia", "Riesgo 72 h medio"],
          [[a["alcaldia"].title(), f"{a['baches']:,}", a["pct_rojos"], a["pct_reincidencia"],
            a["riesgo_72h_medio"]] for a in v["alcaldias"]], [5.5, 2.5, 2.5, 3, 3.5])
    titulo(doc, "3.2 Recomendación de materiales y brigadas para la autoridad", 2)
    parrafo(doc, f"Después de eliminar duplicados con la tabla hash, llegan en promedio {ll['lluvias']} "
                 f"baches nuevos por día en lluvias (junio a octubre) y {ll['secas']} en secas. Con un bache "
                 f"típico de 1.71 m² × 9.8 cm ({calc['v0_tipico_m3']:.3f} m³, unas 0.36 t de mezcla) y "
                 "6 reparaciones por brigada al día, SIPA le recomendaría a la autoridad:")
    tabla(doc, ["Temporada", "Baches/día", "Brigadas", "Mezcla (t/mes)", "Material ($/mes)"],
          [[r["temporada"].title(), r["baches_por_dia"], int(r["brigadas"]), r["toneladas_mes"],
            f"${r['costo_material_mes']:,}"] for r in v["recursos"]], [3, 3, 2.5, 3, 3.5])
    parrafo(doc, f"La pérdida de material crece de forma exponencial (Cálculo): en lluvias k = "
                 f"{calc['k_lluvias']:.3f} por mes y el volumen se duplica en "
                 f"{calc['duplica_lluvias_meses']:.1f} meses. Por eso la capacidad debe subir antes de "
                 "las lluvias, no después.")

    # 4 -----------------------------------------------------------------
    titulo(doc, "4. Gestión y optimización de los datos y recursos")
    titulo(doc, "4.1 Cómo se organizan los datos", 2)
    tabla(doc, ["Paso", "Estructura", "Complejidad", "Evidencia"], [
        ["Registro del reporte", "Lista doblemente enlazada", "O(1)", f"{dd['reportes']:,} reportes"],
        ["¿Ya existe ese bache?", "Tabla hash (celda de 11 m y 8 vecinas)", "O(1) promedio",
         f"{dd['duplicados']:,} duplicados y {dd['reincidencias']:,} reincidencias en {dd['segundos_hash']} s "
         f"({dd['busquedas_hash']:,} búsquedas en lugar de {dd['comparaciones_por_pares'] / 1e6:,.0f} M de comparaciones)"],
        ["Consulta por rango", "Árbol AVL", "O(log n)",
         f"{efi['comparaciones_avl']} comparaciones (altura {efi['altura_avl']}) contra "
         f"{efi['comparaciones_lineal']:,.0f} de la búsqueda lineal"],
        ["Cola de atención", "Max-heap con actualización de prioridad", "O(log n)",
         "Rojos atendidos primero; prioridad que sube con la espera"],
        ["Cupo de equidad", "Segundo max-heap por antigüedad, con eliminación perezosa", "O(log n)",
         "Nuevo en este plan (sección 4.3)"],
        ["Decisiones de la autoridad", "Pila de deshacer y rehacer", "O(1)", "Cada ajuste exige motivo"],
        ["Rutas sugeridas a las brigadas", "Grafo, Dijkstra y vecino más cercano", "O((V+E) log V)",
         f"{ru['vertices']} vértices, {ru['aristas']:,} aristas"],
    ], [3.3, 4.2, 2.6, 6.4])
    titulo(doc, "4.2 Rutas de las cuadrillas", 2)
    parrafo(doc, f"En Coyoacán, visitar los {ru['baches_en_plan']} baches del día en orden de prioridad "
                 f"recorre {ru['km_orden_prioridad']} km; ordenar la visita por vecino más cercano, con "
                 f"distancias de Dijkstra, recorre {ru['km_vecino_cercano']} km "
                 f"(−{100 * (1 - ru['km_vecino_cercano'] / ru['km_orden_prioridad']):.0f} %). El heap decide "
                 "qué baches entran al plan del día y el grafo decide en qué orden se visitan: así no se "
                 "sacrifica la prioridad por la ruta.")
    titulo(doc, "4.3 Capacidad y equidad", 2)
    parrafo(doc, f"Simulamos julio a septiembre de 2019 (90 días, datos reales) con 15 reparaciones por día "
                 "y cuatro políticas. La de cupo reserva 4 de los 15 lugares diarios para los baches que "
                 "más han esperado, después de atender rojos y amarillos.")
    tabla(doc, ["Política", "Rojos ≤ 3 días", "Espera promedio", "Espera p90", "Brecha entre alcaldías",
                "Pendientes día 90"],
          [[n, pct(m["rojos_en_3_dias"]), m["todos"]["espera_promedio"], m["espera_p90"],
            m["brecha_alcaldias"], f"{m['pendientes_al_final']:,}"] for n, m in eq.items()],
          [3.2, 2.4, 2.4, 2, 3, 2.6])
    figura(doc, ED / "v1_equidad.png", "Figura 1. Rojos atendidos a tiempo y brecha entre alcaldías por política.")
    parrafo(doc, f"Con 15 reparaciones al día, la prioridad garantiza los rojos, pero ninguna regla de "
                 f"ordenamiento evita que la cola crezca. El cupo reduce la brecha de {sipa['brecha_alcaldias']} "
                 f"a {cupo['brecha_alcaldias']} días; subir el envejecimiento a β = 0.30 casi no ayuda. "
                 "Con capacidad suficiente, en cambio, la brecha desaparece:")
    tabla(doc, ["Reparaciones/día", "Brigadas", "Rojos ≤ 3 días", "Espera promedio", "Espera p90",
                "Brecha", "Pendientes día 90"],
          [[c["capacidad"], c["brigadas"], pct(c["rojos_en_3_dias"]), c["espera_promedio"], c["espera_p90"],
            c["brecha_alcaldias"], f"{c['pendientes_al_final']:,}"] for c in v["capacidad"]],
          [2.6, 2, 2.4, 2.4, 2, 1.8, 2.6])
    figura(doc, ED / "v2_capacidad.png", "Figura 2. Baches pendientes al final del periodo según la capacidad diaria.",
           13)

    # 5 -----------------------------------------------------------------
    titulo(doc, "5. Viabilidad financiera")
    tabla(doc, ["Concepto", "Preventivo (SIPA)", "Reactivo"], [
        ["Costo de reparar los 1,345 baches", f"${esc['preventivo']['costo_reparar'] / 1e6:.2f} M",
         f"${esc['reactivo']['costo_reparar'] / 1e6:.2f} M"],
        ["Provisión por reclamaciones (NIF C-9)", f"${esc['preventivo']['provision_total'] / 1e6:.2f} M",
         f"${esc['reactivo']['provision_total'] / 1e6:.2f} M"],
        ["Costo total para el erario", f"${esc['preventivo']['costo_total'] / 1e6:.2f} M",
         f"${esc['reactivo']['costo_total'] / 1e6:.2f} M"],
        ["Pasivos contingentes probables o posibles", esc["preventivo"]["baches_probable"] + esc["preventivo"]["baches_posible"],
         esc["reactivo"]["baches_probable"] + esc["reactivo"]["baches_posible"]],
    ], [7, 4, 4])
    vinetas(doc, [
        f"Ahorro del esquema preventivo: ${cont['ahorro_preventivo'] / 1e6:.2f} M; sin contar ponchaduras, "
        f"${cont['sensibilidad'][0]['ahorro'] / 1e6:.2f} M. La conclusión no depende del supuesto más incierto.",
        f"Inversión en la plataforma: equipo ${cont['supuestos']['equipo'] / 1e6:.1f} M y software "
        f"${cont['supuestos']['software'] / 1e6:.2f} M. Se recupera con el ahorro del primer ejercicio.",
        f"Pasar de 15 a 35 reparaciones/día en lluvias cuesta unos ${costo_extra_mes / 1e3:,.0f} mil "
        f"al mes en reparaciones. Dejar crecer la cola cuesta más: cada bache que espera 6 meses de lluvias pasa "
        f"de ${costo_bache:,.0f} a ${costo_bache_6m:,.0f} (Cálculo, con las tarifas de SIPA).",
        "La infraestructura de cómputo es mínima: la desduplicación de toda la base tarda menos de 2 s y "
        "la simulación de 90 días, segundos, en una computadora personal.",
    ])

    # 6 -----------------------------------------------------------------
    titulo(doc, "6. Equidad social y justificación de las decisiones")
    vinetas(doc, [
        "El IPU acota el número de reportes en 10 para que las colonias con más participación digital "
        "no desplacen a las que reportan menos.",
        f"El análisis mostró un efecto no deseado: el heap puro alarga la espera en alcaldías periféricas "
        f"con baches de IPU bajo (Cuajimalpa {sipa['espera_por_alcaldia']['CUAJIMALPA DE MORELOS']} días, "
        f"Tláhuac {sipa['espera_por_alcaldia']['TLAHUAC']}). El cupo de antigüedad baja Magdalena Contreras "
        f"de {sipa['espera_por_alcaldia']['LA MAGDALENA CONTRERAS']} a "
        f"{cupo['espera_por_alcaldia']['LA MAGDALENA CONTRERAS']} días sin perder un solo rojo.",
        "Transporte público y movilidad: el riesgo a 72 h es mayor en vías rápidas y corredores "
        "(Cuauhtémoc, Venustiano Carranza, Benito Juárez); atenderlos primero protege a más personas por "
        "peso invertido. El criterio de transporte del IPU completo espera la carga de GTFS.",
        "Supervisión humana: SIPA recomienda y la autoridad aprueba cada prioridad; ajustar o rechazar exige motivo y "
        "queda en la pila de decisiones (y en la base de datos) para rendir cuentas.",
    ])

    # 7 -----------------------------------------------------------------
    titulo(doc, "7. Propuesta de intervenciones públicas priorizadas")
    top = v["top_celdas"][:5]
    tabla(doc, ["#", "Intervención", "Evidencia", "Recursos", "Indicador de seguimiento"], [
        [1, "Atender los baches rojos en 72 h o menos con cola de prioridad",
         f"Rojos ≤ 3 días: {pct(sipa['rojos_en_3_dias'])} con SIPA y {pct(fifo['rojos_en_3_dias'])} con FIFO",
         "Ninguno adicional: reordena la capacidad actual", "% de rojos cerrados en 72 h"],
        [2, "Recomendar a la autoridad ajustar sus brigadas por temporada",
         f"Llegan {ll['lluvias']} baches/día en lluvias y {ll['secas']} en secas; con 15/día quedan "
         f"{cap[15]['pendientes_al_final']:,} pendientes en 90 días, con 35/día, {cap[35]['pendientes_al_final']}",
         f"{int(rec['lluvias']['brigadas'])} brigadas en lluvias, {int(rec['secas']['brigadas'])} en secas; "
         f"{rec['lluvias']['toneladas_mes']} t/mes de mezcla en lluvias", "Pendientes al cierre de mes"],
        [3, "Reencarpetar las celdas con reincidencia, en lugar de bachearlas",
         f"{v['celdas_reincidencia_3']} celdas con ≥ 3 reapariciones concentran {pct_reinc:.1f} % de los baches; "
         f"la peor ({top[0]['alcaldia'].title()}) tiene {top[0]['reincidencias']} reapariciones",
         "Proyecto de obra por celda; empezar por las 15 del anexo", "Reapariciones por celda al año"],
        [4, "Cupo de equidad: 4 de cada 15 lugares para los baches que más esperan",
         f"Brecha entre alcaldías {sipa['brecha_alcaldias']} → {cupo['brecha_alcaldias']} días, rojos al "
         f"{pct(cupo['rojos_en_3_dias'])}", "Ninguno adicional", "Brecha de espera entre alcaldías"],
        [5, "Rutas diarias por vecino más cercano sobre el grafo vial",
         f"−{100 * (1 - ru['km_vecino_cercano'] / ru['km_orden_prioridad']):.0f} % de km en Coyoacán",
         "Ninguno adicional; ahorra combustible y horas", "Km por bache reparado"],
        [6, "Desduplicación automática de reportes",
         f"{dd['duplicados']:,} reportes duplicados que hoy generarían órdenes repetidas", "Ninguno adicional",
         "Órdenes duplicadas"],
        [7, "Bacheo preventivo antes de lluvias",
         f"Esperar 6 meses de lluvias cuesta ${costo_esperar / 1e6:.2f} M más; intervalo preventivo óptimo de "
         "unos 28 meses (Cálculo)", "Programa de abril-mayo", "Costo por m³ reparado"],
        [8, "Cargar el riesgo a 72 h en el IPU completo de la base SIPA",
         "El semáforo a 72 h coincide con el del IPU solo en 36 %; 285 baches están en rojo por riesgo "
         "sin estar en rojo en el IPU (Probabilidad)", "Carga de datos (vista v_riesgo_72h)",
         "Coincidencia de semáforos"],
        [9, "Focalizar la vigilancia en Cuauhtémoc y Venustiano Carranza",
         "12.4 % y 9.3 % de sus baches en rojo; riesgo medio a 72 h de 0.38 y 0.33",
         "Recorridos de detección temprana", "Tiempo entre aparición y reporte"],
    ], [0.7, 3.8, 5, 3.6, 3])
    parrafo(doc, "Las intervenciones 1, 4, 5 y 6 no requieren presupuesto adicional: solo cambian la "
                 "forma de organizar los datos y las decisiones. La 2 y la 3 sí requieren inversión, "
                 "justificada por las secciones 3 y 5.")

    # 8 -----------------------------------------------------------------
    titulo(doc, "8. Viabilidad técnica de la implementación")
    tabla(doc, ["Etapa", "Qué se hace", "Plazo"], [
        ["1. Piloto", "Una alcaldía (Coyoacán): registro, desduplicación, cola de prioridad y rutas", "3 meses"],
        ["2. Datos", "Cargar riesgo a 72 h, GTFS, CONAPO y reincidencia al IPU completo; acordar pesos (AHP)", "2 meses"],
        ["3. Escalamiento", "Todas las alcaldías; tablero sobre el Data Warehouse; réplica de solo lectura", "6 meses"],
        ["4. Evaluación", "Comparar los indicadores de la sección 7 contra el año anterior", "Continuo"],
    ], [3, 10.5, 2.5])
    titulo(doc, "Riesgos y mitigación", 2)
    vinetas(doc, [
        "Capacidad insuficiente: SIPA prioriza y asesora, pero las brigadas son de la autoridad. Se mitiga con la intervención 2.",
        "Sesgo territorial: se mitiga con el cupo de equidad y el tope de reportes.",
        "Calidad de los reportes (ubicaciones imprecisas): la tabla hash revisa la celda y sus 8 vecinas.",
        "Resistencia al cambio: la autoridad conserva la decisión final y su ajuste queda registrado.",
    ])

    # 9 -----------------------------------------------------------------
    titulo(doc, "9. Supuestos y limitaciones")
    vinetas(doc, [
        "La severidad de los baches es sintética (la base abierta no la trae).",
        f"Productividad de 6 baches por brigada al día y costo de ${costo_bache:,.0f} por bache típico (tarifas ilustrativas de SIPA): supuestos por calibrar con la Secretaría de Obras.",
        "Las simulaciones usan 2019; la tasa de llegadas puede ser distinta hoy.",
        "Las rutas usan una cuadrícula de 250 m, no la red de calles real.",
        "Los porcentajes de reclamación de Contabilidad son supuestos; el ahorro se mantiene sin ponchaduras.",
    ])

    # 10 ----------------------------------------------------------------
    titulo(doc, "10. Conclusiones")
    parrafo(doc, "La plataforma es técnicamente viable: con estructuras de datos adecuadas procesa toda la "
                 "base en segundos y garantiza la atención de los baches de mayor riesgo. Es financieramente "
                 "viable: el esquema preventivo cuesta una fracción del reactivo. La evidencia también corrigió "
                 "la idea de que priorizar basta: hace falta ajustar la capacidad a la temporada, reencarpetar "
                 "donde el bache reaparece y vigilar la equidad entre zonas.")

    titulo(doc, "Anexo. Celdas candidatas a reencarpetado")
    tabla(doc, ["Celda", "Alcaldía", "Baches", "Reapariciones", "Riesgo 72 h", "Latitud, longitud"],
          [[c["celda"], c["alcaldia"].title(), c["baches"], c["reincidencias"], c["riesgo_72h"],
            f"{c['lat']}, {c['lon']}"] for c in v["top_celdas"]], [2.5, 4, 1.8, 2.5, 2.2, 3.8])

    titulo(doc, "Referencias")
    for ref in [
        "Agencia Digital de Innovación Pública. (2023). Reportes de baches [Conjunto de datos]. Portal de Datos Abiertos de la Ciudad de México.",
        "Cormen, T. H., Leiserson, C. E., Rivest, R. L. y Stein, C. (2022). Introduction to algorithms (4a ed.). MIT Press.",
        "Gobierno de la Ciudad de México. (2025, 18 de agosto). Presentamos el Plan Integral de Mantenimiento a la Carpeta Asfáltica.",
        "Secretaría de Seguridad Ciudadana. (2020). Hechos de tránsito registrados por la SSC [Conjunto de datos]. Portal de Datos Abiertos de la Ciudad de México.",
    ]:
        p = doc.add_paragraph(ref)
        p.paragraph_format.left_indent = Cm(1)
        p.paragraph_format.first_line_indent = Cm(-1)

    doc.save(SALIDA)
    print(f"Generado {SALIDA}")


if __name__ == "__main__":
    main()
