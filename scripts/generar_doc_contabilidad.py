"""
SIPA - Genera el documento de la 2ª entrega de Contabilidad Financiera a partir de
los resultados de contabilidad/provisiones.py (ejecutarlo antes).

Uso (desde la carpeta del proyecto):
    python contabilidad/provisiones.py
    python scripts/generar_doc_contabilidad.py
Salida:
    avance2_Contabilidad_NIF_C9.docx
"""

import json
from pathlib import Path

import pandas as pd
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt

from generar_doc_planeacion_bd import AZUL, parrafo, tabla, titulo, vinetas

RES = Path("contabilidad/resultados")
SALIDA = "avance2_Contabilidad_NIF_C9.docx"


def figura(doc, archivo, pie, ancho=15):
    doc.add_picture(str(RES / archivo), width=Cm(ancho))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(pie)
    r.italic = True
    r.font.size = Pt(9)


def m(x, d=0):
    if pd.isna(x):
        return ""
    return f"−${-x:,.{d}f}" if x < 0 else f"${x:,.{d}f}"


def mm(x):
    return f"${x / 1e6:,.2f} M"


def estado(doc, df, ancho=(11, 4)):
    """Tabla de un estado financiero; las filas sin importe son encabezados de sección."""
    filas = [[c, m(v, 2)] for c, v in zip(df["concepto"], df["importe"])]
    tabla(doc, ["Concepto", "Importe"], filas, list(ancho))


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
        ("Segunda entrega · Contabilidad Financiera", 14, True),
        ("Incidente crítico: gestión contable de la infraestructura vial.", 12, False),
        ("Pasivos contingentes y provisiones por baches (NIF C-9)", 12, False),
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
          [["UCA", "Contabilidad Financiera (LCDN3CON8)"],
           ["Docente", "Yesenia Biffano Rodríguez"],
           ["Grupo", "302"],
           ["Fecha de entrega", "13 de noviembre de 2026"]], [4.5, 7])
    doc.add_page_break()


def main():
    r = json.loads((RES / "resumen.json").read_text(encoding="utf-8"))
    sup = r["supuestos"]
    esc = {e["escenario"]: e for e in r["escenarios"]}
    pv, rv = esc["preventivo"], esc["reactivo"]
    a, ar = r["asientos"], r["asientos_reactivo"]
    raz = r["razones"]
    terr = pd.read_csv(RES / "t3_provision_por_territorio.csv")
    diario = pd.read_csv(RES / "t4_libro_diario.csv")
    bal = pd.read_csv(RES / "t5_balanza.csv", index_col=0)
    er = pd.read_csv(RES / "t6_estado_resultados.csv")
    bg = pd.read_csv(RES / "t7_balance_general.csv")
    fe = pd.read_csv(RES / "t8_flujo_efectivo.csv")
    sens = pd.DataFrame(r["sensibilidad"])
    bancos_r = next(x["importe"] for x in r["balance_reactivo"] if x["concepto"] == "Bancos")

    doc = Document()
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(11)
    for s in doc.sections:
        s.left_margin = s.right_margin = Cm(2.2)

    portada(doc)

    # 1 -----------------------------------------------------------------
    titulo(doc, "1. El incidente crítico")
    parrafo(doc, "Los baches no solo cuestan lo que vale repararlos. Cuando provocan un accidente o dañan un "
                 "vehículo, la persona afectada puede reclamar al gobierno la reparación del daño (responsabilidad "
                 "patrimonial del Estado). Cada bache abierto es, por lo tanto, una obligación latente para las "
                 "finanzas públicas que normalmente no aparece en los estados financieros hasta que se paga.")
    parrafo(doc, "El incidente propone aplicar la NIF C-9 para reconocer esa deuda latente, usar datos espaciales, "
                 "temporales y ciudadanos para calcular provisiones precisas, y pasar del mantenimiento reactivo a "
                 "un modelo de inversión preventiva. Este documento responde:")
    vinetas(doc, [
        "¿Cuánto deben provisionar las finanzas públicas por los baches pendientes y cómo se clasifica cada caso "
        "según la NIF C-9?",
        "¿Cómo se registra en la contabilidad (cargo y abono) y cómo se refleja en los estados financieros?",
        "¿Cuánto le cuesta al erario el mantenimiento reactivo frente al preventivo?",
    ])

    # 2 -----------------------------------------------------------------
    titulo(doc, "2. La contabilidad como sistema de información del proyecto")
    parrafo(doc, "La contabilidad captura, registra y clasifica las operaciones económicas para mostrar la "
                 "situación financiera de una entidad. Su base es la partida doble, sistematizada por Fray Luca "
                 "Pacioli en 1494: toda operación afecta al menos dos cuentas y la suma de cargos es igual a la de "
                 "abonos. Hoy esa misma regla vive en las bases de datos: en SIPA, cada recomendación con su costo "
                 "estimado, cada decisión de la autoridad y cada costo real que ella reporta quedan registrados y se "
                 "pueden conciliar.")
    tabla(doc, ["Tipo de contabilidad", "Usuario", "Uso de la información de SIPA"], [
        ["Financiera", "Ciudadanía, auditores, Congreso",
         "Estados financieros con la provisión por reclamaciones y el valor de los activos de bacheo"],
        ["Gubernamental", "Secretaría de Finanzas, Auditoría Superior",
         "Registro presupuestal y patrimonial conforme a la Ley General de Contabilidad Gubernamental (CONAC)"],
        ["Administrativa (de costos)", "Dirección de obras de la autoridad",
         "Costo estimado por bache y por territorio, costo de esperar, costo reportado contra estimado"],
        ["Fiscal", "SAT, proveedores", "IVA pagado en compras, comprobantes fiscales de contratistas"],
    ], [3.5, 4, 8.5])
    parrafo(doc, "la información contable es un instrumento de dirección y control: el semáforo de SIPA "
                 "dice qué reparar, y la contabilidad dice cuánto cuesta no hacerlo.", "Idea central: ")

    # 3 -----------------------------------------------------------------
    titulo(doc, "3. Marco normativo: NIF C-9")
    parrafo(doc, "La NIF C-9 «Provisiones, contingencias y compromisos» distingue tres conceptos:")
    tabla(doc, ["Concepto", "Definición", "Tratamiento", "En los baches"], [
        ["Provisión", "Pasivo de cuantía o fecha inciertas: obligación presente, salida de recursos probable y "
         "monto estimable confiablemente", "Se reconoce en el balance (cargo a gasto, abono a pasivo)",
         "Reclamaciones esperadas por baches con alta probabilidad de causar daños"],
        ["Pasivo contingente", "Obligación posible, o presente pero sin salida probable o sin estimación confiable",
         "No se registra; se revela en notas", "Baches con probabilidad intermedia de reclamación"],
        ["Remota", "Salida de recursos muy poco probable", "No se registra ni se revela",
         "Baches de bajo riesgo"],
    ], [2.8, 5.2, 4, 4])
    parrafo(doc, f"probable = más del {sup.get('probable', 0.5) * 100:.0f} % (más probable que no); posible = "
                 "entre 10 % y 50 %; remota = menos de 10 %.", "Umbrales usados: ")
    parrafo(doc, "cuando hay muchas obligaciones similares (como 1,345 baches), la NIF C-9 indica evaluar la "
                 "probabilidad considerando el grupo en conjunto. Aunque cada bache por separado sea remoto, es "
                 "prácticamente seguro que al menos uno genere una reclamación; por eso se provisiona la mejor "
                 "estimación del total (valor esperado).", "Obligaciones en grupo: ")
    titulo(doc, "3.1 Cuadro comparativo de normas", 2)
    tabla(doc, ["Aspecto", "NIF C-9 (México)", "NIC 37 (internacional)", "CONAC (gobierno de México)"], [
        ["Emisor", "CINIF", "IASB", "Consejo Nacional de Armonización Contable"],
        ["Aplica a", "Entidades que emiten estados financieros conforme a NIF",
         "Entidades bajo IFRS", "Entes públicos (LGCG)"],
        ["Reconocer provisión", "Obligación presente, salida probable, estimación confiable", "Mismos tres criterios",
         "Cuenta 2.1.7 «Provisiones a corto plazo» con los mismos criterios"],
        ["Pasivo contingente", "Se revela en notas", "Se revela en notas", "Se revela en notas (cuentas de orden)"],
        ["Medición", "Mejor estimación; valor presente si el efecto es importante", "Igual",
         "Se remite a la normativa supletoria (NIF / NICSP 19)"],
        ["Aportación al análisis", "Evita «sorpresas» financieras: la deuda latente aparece antes de pagarse",
         "Comparabilidad internacional", "Transparencia y fiscalización del gasto público"],
    ], [3, 4.4, 4, 4.6])

    # 4 -----------------------------------------------------------------
    titulo(doc, "4. Estimación de la provisión")
    parrafo(doc, "La provisión se calcula bache por bache con los modelos que el proyecto ya desarrolló en otras "
                 "materias:")
    tabla(doc, ["Dato", "Valor", "Origen"], [
        ["Probabilidad de accidente en 72 h por bache", "Una por celda de 250 m",
         "Modelo de Probabilidad (Poisson con Bayes empírico, datos de la SSC)"],
        ["Fracción de accidentes atribuible al bache", f"{r['fraccion_atribuible'] * 100:.1f} %",
         "Riesgo relativo de celdas con baches (Probabilidad)"],
        ["Costo de reparar hoy y tras 6 meses de lluvias", "Por bache", "Modelo de degradación (Cálculo Integral)"],
        ["Días que el bache queda abierto, reactivo", f"{sup['dias_reactivo']} días", "Se repara tras las lluvias"],
        ["Días abierto, preventivo", "Rojo 3, amarillo 7, verde 30; vía rápida profunda 3",
         "Semáforo de SIPA"],
        ["Reclamaciones por accidente atribuible", f"{sup['p_reclama_accidente'] * 100:.0f} % · "
         f"{m(sup['monto_accidente'])} c/u", "Supuesto"],
        ["Ponchaduras por día (bache ≥ 10 cm en vía rápida)", f"{sup['ponchaduras_dia']:.0f}",
         "Escenario de aforo de Probabilidad"],
        ["Reclamaciones por ponchadura", f"{sup['p_reclama_ponchadura'] * 100:.0f} % · "
         f"{m(sup['monto_ponchadura'])} c/u", "Supuesto"],
    ], [6, 4.5, 5.5])
    parrafo(doc, "Reclamaciones esperadas E = (accidentes atribuibles por día × días abierto × % que reclama) + "
                 "(ponchaduras por día × días abierto × % que reclama). Probabilidad de al menos una reclamación = "
                 "1 − e^(−E). Provisión = E × monto promedio.", "Fórmulas: ")

    titulo(doc, "4.1 Resultados por escenario", 2)
    tabla(doc, ["Concepto", "Preventivo", "Reactivo"], [
        ["Reclamaciones esperadas", f"{pv['reclamaciones_esperadas']:,.0f}", f"{rv['reclamaciones_esperadas']:,.0f}"],
        ["Provisión por accidentes", m(pv["provision_accidentes"]), m(rv["provision_accidentes"])],
        ["Provisión por ponchaduras", m(pv["provision_ponchaduras"]), m(rv["provision_ponchaduras"])],
        ["Provisión total (grupo, mejor estimación)", m(pv["provision_total"]), m(rv["provision_total"])],
        ["Baches PROBABLES (provisión individual)", pv["baches_probable"], rv["baches_probable"]],
        ["Baches POSIBLES (pasivo contingente, se revela)", pv["baches_posible"], rv["baches_posible"]],
        ["Monto de pasivo contingente a revelar", m(pv["revelacion_individual"]), m(rv["revelacion_individual"])],
        ["Baches REMOTOS", pv["baches_remota"], rv["baches_remota"]],
        ["Costo de reparar", m(pv["costo_reparar"]), m(rv["costo_reparar"])],
        ["COSTO TOTAL PARA EL ERARIO", m(pv["costo_total"]), m(rv["costo_total"])],
    ], [7.5, 4, 4])
    parrafo(doc, f"El esquema preventivo cuesta {mm(pv['costo_total'])} y el reactivo {mm(rv['costo_total'])}: "
                 f"atender a tiempo ahorra {mm(r['ahorro_preventivo'])}. Los {r['baches_ponchan']} baches profundos "
                 "en vía rápida son los únicos que quedan como «probables» uno por uno: son la prioridad contable.")
    figura(doc, "g1_reactivo_vs_preventivo.png", "Figura 1. Costo de reparar más provisión, por escenario.")
    figura(doc, "g2_clasificacion_nif_c9.png", "Figura 2. Clasificación NIF C-9 de cada bache pendiente.")

    titulo(doc, "4.2 Sensibilidad al supuesto más incierto", 2)
    parrafo(doc, "La provisión por ponchaduras depende de qué porcentaje de las personas afectadas reclama, dato que "
                 "no tenemos. Al variarlo, la conclusión no cambia:")
    tabla(doc, ["Supuesto de reclamación por ponchadura", "Costo reactivo", "Costo preventivo", "Ahorro"],
          [[x.supuesto, mm(x.costo_total_reactivo), mm(x.costo_total_preventivo), mm(x.ahorro)]
           for x in sens.itertuples()], [6, 3.3, 3.3, 3.3])
    parrafo(doc, f"Aun sin contar ninguna ponchadura, el esquema preventivo ahorra {mm(sens.ahorro[0])}.")

    titulo(doc, "4.3 Territorios con mayor provisión", 2)
    tabla(doc, ["Territorio", "Baches", "Provisión preventiva", "Provisión reactiva"],
          [[x.territorio, int(x.baches), m(x.provision_preventivo), m(x.provision_reactivo)]
           for x in terr.head(6).itertuples()], [5, 2.5, 4, 4])

    # 5 -----------------------------------------------------------------
    titulo(doc, "5. Registro contable (escenario preventivo)")
    parrafo(doc, "Caso de estudio: la Unidad de Bacheo opera el programa SIPA durante un ejercicio (1 de enero a "
                 f"31 de diciembre). Recibe una asignación de {m(sup['presupuesto'])}, compra equipo, contrata la "
                 "asesoría de SIPA, repara con sus brigadas los 1,345 baches pendientes y reconoce la provisión por reclamaciones.")
    titulo(doc, "5.1 Libro diario", 2)
    filas = []
    for n, g in diario.groupby("asiento", sort=False):
        filas.append([f"{n}", g["fecha"].iloc[0], g["concepto"].iloc[0], "", ""])
        for x in g.itertuples():
            cuenta = x.cuenta if x.cargo > 0 else "      " + x.cuenta
            filas.append(["", "", cuenta, m(x.cargo, 2) if x.cargo else "", m(x.abono, 2) if x.abono else ""])
    filas.append(["", "", "Sumas iguales", m(diario.cargo.sum(), 2), m(diario.abono.sum(), 2)])
    tabla(doc, ["#", "Fecha", "Cuenta / concepto", "Cargo", "Abono"], filas, [0.8, 1.4, 8.6, 2.6, 2.6])
    parrafo(doc, "el asiento 8 es el corazón del incidente. Se carga a «Gasto por provisión de "
                 "reclamaciones» (afecta el resultado) y se abona a «Provisión para reclamaciones por daños» "
                 "(pasivo), antes de que llegue la primera reclamación. Cuando se paga (asiento 9), el pago se "
                 "aplica contra la provisión y no vuelve a afectar el resultado.", "Asiento clave: ")

    titulo(doc, "5.2 Esquemas de mayor", 2)
    parrafo(doc, "Las dos cuentas más relevantes, con referencia al asiento de origen:")
    for cuenta in ["Bancos", "Provisión para reclamaciones por daños"]:
        g = diario[diario["cuenta"] == cuenta]
        debe = [f"({x.asiento}) {m(x.cargo, 2)}" for x in g.itertuples() if x.cargo]
        haber = [f"({x.asiento}) {m(x.abono, 2)}" for x in g.itertuples() if x.abono]
        k = max(len(debe), len(haber))
        debe += [""] * (k - len(debe))
        haber += [""] * (k - len(haber))
        sd, sa = bal.loc[cuenta, "saldo_deudor"], bal.loc[cuenta, "saldo_acreedor"]
        filas = [[d, h] for d, h in zip(debe, haber)]
        filas.append([f"Σ {m(g.cargo.sum(), 2)}", f"Σ {m(g.abono.sum(), 2)}"])
        filas.append([f"Saldo deudor {m(sd, 2)}" if sd else "", f"Saldo acreedor {m(sa, 2)}" if sa else ""])
        tabla(doc, [f"{cuenta} · Debe", "Haber"], filas, [7.5, 7.5])
    parrafo(doc, "Los esquemas de mayor de todas las cuentas están en el archivo libro_contable.xlsx.")

    titulo(doc, "5.3 Balanza de comprobación", 2)
    filas = [[c, m(x.cargo, 2), m(x.abono, 2), m(x.saldo_deudor, 2) if x.saldo_deudor else "",
              m(x.saldo_acreedor, 2) if x.saldo_acreedor else ""] for c, x in bal.iterrows()]
    filas.append(["Sumas iguales", m(bal.cargo.sum(), 2), m(bal.abono.sum(), 2), m(bal.saldo_deudor.sum(), 2),
                  m(bal.saldo_acreedor.sum(), 2)])
    tabla(doc, ["Cuenta", "Cargos", "Abonos", "Saldo deudor", "Saldo acreedor"], filas, [5.4, 2.7, 2.7, 2.7, 2.7])

    # 6 -----------------------------------------------------------------
    titulo(doc, "6. Estados financieros")
    parrafo(doc, "Unidad de Bacheo · Programa SIPA. Cifras en pesos. Escenario preventivo.")
    titulo(doc, "6.1 Estado de resultados (estado de actividades) del 1 de enero al 31 de diciembre", 2)
    estado(doc, er)
    titulo(doc, "6.2 Balance general al 31 de diciembre", 2)
    estado(doc, bg)
    titulo(doc, "6.3 Estado de flujo de efectivo (método indirecto)", 2)
    estado(doc, fe)
    parrafo(doc, "el efectivo final del flujo coincide con el saldo de Bancos del balance, la balanza "
                 "tiene sumas iguales y el activo es igual al pasivo más el patrimonio. El programa verifica estas "
                 "igualdades cada vez que se ejecuta.", "Validación cruzada: ")

    titulo(doc, "6.4 Interpretación y razones financieras", 2)
    tabla(doc, ["Razón", "Fórmula", "Resultado"], [
        ["Liquidez", "Activo circulante / pasivo", f"{raz['liquidez']:.1f}"],
        ["Prueba ácida", "Bancos / pasivo", f"{raz['prueba_acida']:.1f}"],
        ["Endeudamiento", "Pasivo / activo", f"{raz['endeudamiento'] * 100:.1f} %"],
        ["Peso de la provisión en el pasivo", "Provisión / pasivo", f"{raz['provision_sobre_pasivo'] * 100:.1f} %"],
        ["Gasto por provisión / ingresos", "Gasto por provisión / asignación",
         f"{raz['provision_sobre_ingresos'] * 100:.1f} %"],
    ], [5, 6, 4])
    parrafo(doc, f"Con el esquema preventivo la unidad cubre sus obligaciones con holgura y queda un ahorro de "
                 f"{mm(r['resultado'])} para atender nuevos baches o la conservación preventiva.")
    titulo(doc, "6.5 El mismo ejercicio con el esquema reactivo", 2)
    parrafo(doc, "Con la misma asignación, pero reparando hasta después de las lluvias:")
    vinetas(doc, [
        f"El costo de reparar sube de {mm(pv['costo_reparar'])} a {mm(rv['costo_reparar'])}, porque los baches "
        "crecen (modelo de Cálculo).",
        f"La provisión sube de {mm(pv['provision_total'])} a {mm(rv['provision_total'])}.",
        f"El resultado del ejercicio pasa de un ahorro de {mm(r['resultado'])} a un desahorro de "
        f"{mm(-r['resultado_reactivo'])}.",
        f"El efectivo no alcanza: Bancos terminaría en {mm(bancos_r)}, así que se necesitaría una ampliación "
        "presupuestal o endeudamiento.",
    ])
    parrafo(doc, "La NIF C-9 hace visible este costo desde el momento en que se decide esperar, y no hasta que "
                 "llegan las reclamaciones: esa es la «prevención de sorpresas financieras».")

    # 7 -----------------------------------------------------------------
    titulo(doc, "7. Aspectos fiscales")
    vinetas(doc, [
        "IVA: la Unidad de Bacheo realiza actividades de servicio público que no causan IVA, así que el IVA que "
        f"paga en sus compras ({sup['iva'] * 100:.0f} %) no es acreditable y se registra como parte del costo de la "
        "mezcla y de la mano de obra (asientos 5 y 7).",
        "ISR: los entes públicos no son contribuyentes del ISR por sus funciones de derecho público; el resultado "
        "del ejercicio es un ahorro de la gestión, no una utilidad gravable. Sí deben retener y enterar el ISR de "
        "sus trabajadores y exigir comprobantes fiscales (CFDI) a los contratistas.",
        "Diferencia entre resultado contable y fiscal: para una empresa privada, una provisión no es deducible "
        "hasta que se paga. Por eso el gasto por provisión genera una diferencia temporal entre la utilidad "
        "contable y la fiscal.",
        "Código Fiscal de la Federación: obliga a conservar la contabilidad y sus comprobantes. Los comprobantes de "
        "obra y de material son de la Unidad de Bacheo; SIPA conserva la parte que le toca: la recomendación, la "
        "decisión y el costo que la autoridad reporta al cerrar cada bache.",
    ])

    # 8 -----------------------------------------------------------------
    titulo(doc, "8. Control interno y fiscalización con SIPA")
    tabla(doc, ["Riesgo", "Control en SIPA"], [
        ["Pagar reparaciones que no se hicieron", "Cada bache reparado queda en el seguimiento con fecha, autoridad "
         "responsable y costo; la ciudadanía que lo reportó recibe el aviso y puede desmentirlo"],
        ["Sobrecostos en la reparación",
         "SIPA compara el costo reportado con el estimado por las tarifas y marca las desviaciones "
         "(datamart financiero)"],
        ["Prioridades por presión política", "IPU con criterios verificables; los cambios de la autoridad quedan "
         "registrados con su justificación (31 de 301 casos)"],
        ["Reclamaciones falsas o duplicadas", "Se validan contra la ubicación y la fecha del bache en la base"],
        ["Provisión subestimada o sobrestimada", "Se recalcula al cierre con el modelo y se compara con los pagos "
         "reales"],
        ["Acceso indebido a datos personales", "Roles en la base de datos; el tablero no puede leer datos personales"],
    ], [5.5, 10.5])

    # 9 -----------------------------------------------------------------
    titulo(doc, "9. Respuesta al incidente crítico")
    vinetas(doc, [
        f"Los baches pendientes sí generan una obligación que debe reconocerse: la mejor estimación es "
        f"{mm(pv['provision_total'])} si se atienden según el semáforo y {mm(rv['provision_total'])} si se "
        "espera a que pasen las lluvias.",
        f"Por bache, solo los {r['baches_ponchan']} baches profundos en vía rápida son probables; en el esquema "
        f"reactivo aparecen además {rv['baches_posible']} pasivos contingentes que deben revelarse en notas.",
        "El registro es: cargo a «Gasto por provisión de reclamaciones» y abono a «Provisión para "
        "reclamaciones por daños»; los pagos se aplican contra la provisión.",
        f"El mantenimiento preventivo es una inversión: ahorra {mm(r['ahorro_preventivo'])} al erario y la "
        "conclusión se sostiene aunque no se cuente ninguna ponchadura.",
        "Los datos espaciales (celdas de 250 m), temporales (temporada de lluvias, 72 horas) y ciudadanos "
        "(reportes) convierten una deuda invisible en una cifra auditable.",
    ])

    # 10 ----------------------------------------------------------------
    titulo(doc, "10. Supuestos y limitaciones")
    vinetas(doc, [
        "Los porcentajes de reclamación y los montos promedio son supuestos ilustrativos. Deben calibrarse con los "
        "expedientes reales de responsabilidad patrimonial de la Ciudad de México.",
        "La Unidad de Bacheo y sus operaciones (presupuesto, equipo, software) son un caso de estudio construido; "
        "los costos de reparación sí salen del modelo de Cálculo y de los baches de la base SIPA.",
        "El tamaño y la profundidad de los baches son sintéticos (ver limitaciones del proyecto), así que las cifras "
        "deben leerse como orden de magnitud.",
        "No se descontó la provisión a valor presente porque las reclamaciones se pagan dentro del año.",
        "La contabilidad gubernamental real usa el catálogo de cuentas del CONAC y registros presupuestales "
        "(momentos contables) que aquí se simplificaron.",
    ])

    titulo(doc, "Referencias")
    vinetas(doc, [
        "Consejo Mexicano de Normas de Información Financiera. (2024). Normas de Información Financiera: NIF C-9 "
        "Provisiones, contingencias y compromisos. IMCP.",
        "IFRS Foundation. (2023). NIC 37 Provisiones, pasivos contingentes y activos contingentes.",
        "Consejo Nacional de Armonización Contable. (2024). Plan de cuentas y Marco conceptual de contabilidad "
        "gubernamental. CONAC.",
        "Ley General de Contabilidad Gubernamental. (2008, última reforma). Diario Oficial de la Federación.",
        "Ley de Responsabilidad Patrimonial de la Ciudad de México. Gaceta Oficial de la Ciudad de México.",
        "Guajardo, G., & Andrade, N. (2018). Contabilidad financiera (7.ª ed.). McGraw-Hill.",
    ])
    titulo(doc, "Anexo. Archivos y cómo reproducir", 2)
    parrafo(doc, "python contabilidad/provisiones.py  (calcula la provisión por bache, los asientos, la balanza y "
                 "los estados financieros, y verifica todas las igualdades contables). Genera "
                 "contabilidad/resultados/libro_contable.xlsx con el libro diario, los esquemas de mayor, la "
                 "balanza, los tres estados financieros y la provisión de cada bache.")

    doc.save(SALIDA)
    print(f"Documento generado: {SALIDA}")


if __name__ == "__main__":
    main()
