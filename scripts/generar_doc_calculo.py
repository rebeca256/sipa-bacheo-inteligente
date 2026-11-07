"""
SIPA - Genera el documento de la 2ª entrega de Cálculo Integral a partir de los
resultados de calculo/degradacion.py (ejecutarlo antes).

Uso (desde la carpeta del proyecto):
    python calculo/degradacion.py
    python scripts/generar_doc_calculo.py
Salida:
    avance2_Calculo_degradacion.docx
"""

import json
from pathlib import Path

import pandas as pd
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt

from generar_doc_planeacion_bd import AZUL, parrafo, tabla, titulo, vinetas

RES = Path("calculo/resultados")
SALIDA = "avance2_Calculo_degradacion.docx"


def ecuacion(doc, texto):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(texto)
    r.font.name = "Cambria Math"
    r.font.size = Pt(12)
    return p


def figura(doc, archivo, pie):
    doc.add_picture(str(RES / archivo), width=Cm(15))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(pie)
    r.italic = True
    r.font.size = Pt(9)


def m(x, d=0):
    return f"${x:,.{d}f}"


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
        ("Segunda entrega · Cálculo Integral", 14, True),
        ("Incidente crítico: Degradación acumulada del asfalto.", 12, False),
        ("¿Cuánto material se pierde y cuánto cuesta esperar?", 12, False),
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
          [["UCA", "Cálculo Integral (LCDN3CAL8)"],
           ["Docente", "María Guadalupe Sierra Hernández"],
           ["Grupo", "302"],
           ["Fecha de entrega", "1 de noviembre de 2026"]], [4.5, 7])
    doc.add_page_break()


def main():
    r = json.loads((RES / "resumen.json").read_text(encoding="utf-8"))
    t1 = pd.read_csv(RES / "t1_perdida_y_costo.csv")
    t4 = pd.read_csv(RES / "t4_costo_esperar_por_territorio.csv")
    v0, ks, kl, kp = r["v0_tipico_m3"], r["k_secas"], r["k_lluvias"], r["k_promedio"]
    lluv6 = t1[(t1.temporada == "Lluvias") & (t1.meses == 6)].iloc[0]
    tb = r["total_baches"]

    doc = Document()
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(11)
    for s in doc.sections:
        s.left_margin = s.right_margin = Cm(2.2)

    portada(doc)

    # 1 -----------------------------------------------------------------
    titulo(doc, "1. El incidente crítico")
    parrafo(doc, "El tránsito, y sobre todo el peso de los vehículos, desgasta la carpeta asfáltica con el tiempo. "
                 "Conocer solo el estado actual de un bache no basta: hay que estimar cuánto material se pierde en un "
                 "periodo para saber cuánto material hará falta y comparar el costo de reparar hoy contra el de "
                 "reparar después. El incidente pregunta:")
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run("¿Cuánto material se pierde y cuánto cuesta esperar?").bold = True
    parrafo(doc, "La pérdida de material es una magnitud que se acumula en el tiempo: si conocemos la rapidez con "
                 "que se pierde, r(t), el total perdido es el área bajo esa curva, es decir, una integral definida.")

    # 2 -----------------------------------------------------------------
    titulo(doc, "2. Planteamiento del modelo")
    ecuacion(doc, "r(t, W) = a · (W / W₀)⁴ · e^(k·t)      [m³ perdidos por mes]")
    tabla(doc, ["Símbolo", "Significado", "Valor usado", "Origen"], [
        ["t", "Tiempo desde la detección del bache", "meses", "—"],
        ["V₀", "Volumen inicial del bache (área × profundidad)",
         f"{v0:.4f} m³ ({r['area_tipica_m2']:.2f} m² × {r['profundidad_tipica_cm']:.1f} cm)",
         f"Mediana de {r['baches_analizados']:,} baches pendientes en la base SIPA"],
        ["W / W₀", "Carga por eje relativa a una carga de referencia", "1.0 (caso base)", "Escenarios 1.0 a 1.5"],
        ["(W/W₀)⁴", "Ley de la cuarta potencia: el daño crece con la cuarta potencia de la carga", "φ = 1", "AASHO Road Test"],
        ["k (secas)", "Tasa de crecimiento mensual del daño en secas", f"{ks:.3f}", "Supuesto ilustrativo"],
        ["k (lluvias)", "Tasa en temporada de lluvias", f"{kl:.3f} = {ks:.2f} × {r['factor_lluvias']:.2f}",
         f"Datos reales: {r['reportes_mes_lluvias']:,.0f} reportes/mes en lluvias contra "
         f"{r['reportes_mes_secas']:,.0f} en secas (CDMX 2019-2022)"],
        ["a", "Constante de escala", "a = k · V₀", "Para que el volumen cumpla dV/dt = kV"],
        ["ρ", "Densidad de la mezcla compactada", "2.4 t/m³ (+10 % desperdicio)", "Referencia técnica"],
        ["c", "Costo por m³ reparado", f"{m(r['costo_m3'])} ({r['tarifa_nombre'].lower()}: {m(r['tarifa_m2'])}/m² "
         f"÷ {r['profundidad_tipica_cm']:.1f} cm de profundidad)",
         "Tarifas de SIPA (datos/costos/tarifas_reparacion.json)"],
    ], [2, 5.5, 4, 4.5])
    parrafo(doc, "un bache más grande retiene más agua y recibe más impactos, así que crece más rápido "
                 "mientras más grande es. Por eso la tasa es exponencial y no constante.", "Por qué e^(kt): ")
    parrafo(doc, f"con k = {kl:.3f}, el bache duplica su volumen en ln 2 / k = "
                 f"{r['duplica_lluvias_meses']:.1f} meses en lluvias y en {r['duplica_secas_meses']:.1f} meses "
                 "en secas.", "Interpretación de k: ")

    # 3 -----------------------------------------------------------------
    titulo(doc, "3. Desarrollo")

    titulo(doc, "3.1 Ecuación diferencial del volumen del bache", 2)
    parrafo(doc, "Si el bache crece en proporción a su tamaño, su volumen V(t) cumple:")
    ecuacion(doc, "dV/dt = k · V")
    parrafo(doc, "Separando variables e integrando ambos lados:")
    ecuacion(doc, "∫ dV / V = ∫ k dt   ⟹   ln V = k·t + C   ⟹   V(t) = V₀ · e^(k·t)")
    parrafo(doc, "La rapidez de pérdida es la derivada del volumen: r(t) = dV/dt = k·V₀·e^(kt), que es el modelo "
                 "con a = k·V₀ y W = W₀.")

    titulo(doc, "3.2 Integral indefinida (antiderivada)", 2)
    parrafo(doc, "Con el cambio de variable u = k·t, du = k dt:")
    ecuacion(doc, "∫ a·φ·e^(kt) dt = (a·φ / k) · ∫ e^u du = (a·φ / k) · e^(kt) + C")

    titulo(doc, "3.3 Integral definida: material perdido entre 0 y T", 2)
    parrafo(doc, "Por el teorema fundamental del cálculo, evaluando la antiderivada en los límites:")
    ecuacion(doc, "P(T) = ∫₀ᵀ a·φ·e^(kt) dt = (a·φ / k) · (e^(kT) − 1) = V₀ · φ · (e^(kT) − 1)")
    parrafo(doc, "Ejemplo, bache típico en lluvias durante T = 6 meses:", None)
    ecuacion(doc, f"P(6) = {v0:.4f} · (e^({kl:.3f}·6) − 1) = {v0:.4f} · {(r['exacto_lluvias_6m'] / v0):.4f} "
                  f"= {r['exacto_lluvias_6m']:.4f} m³")
    parrafo(doc, f"En seis meses de lluvias el bache pierde {r['exacto_lluvias_6m']:.3f} m³ adicionales: más que su "
                 f"volumen inicial ({v0:.3f} m³).")
    figura(doc, "g1_area_bajo_curva.png",
           "Figura 1. El área sombreada bajo r(t) entre 0 y 6 meses es el material perdido. En lluvias el área es "
           "mucho mayor.")

    titulo(doc, "3.4 Sumas de Riemann", 2)
    parrafo(doc, "Para comprobar el resultado se aproxima la misma integral con rectángulos. El error disminuye al "
                 "aumentar n, y la regla del punto medio converge mucho más rápido:")
    rie = r["riemann"]
    tabla(doc, ["n", "Izquierda", "Error", "Derecha", "Error", "Punto medio", "Error"],
          [[x["n"], f"{x['izquierda']:.4f}", f"{x['error_izquierda_%']:.2f}%", f"{x['derecha']:.4f}",
            f"{x['error_derecha_%']:.2f}%", f"{x['punto medio']:.4f}", f"{x['error_punto medio_%']:.3f}%"]
           for x in rie], [1.2, 2.2, 1.8, 2.2, 1.8, 2.4, 1.8])
    parrafo(doc, f"Valor exacto: {r['exacto_lluvias_6m']:.4f} m³. Como r(t) es creciente, la suma izquierda "
                 "subestima y la derecha sobrestima; el valor exacto queda entre ambas.")
    figura(doc, "g2_riemann.png", "Figura 2. Suma de Riemann por la izquierda con n = 6 rectángulos.")

    titulo(doc, "3.5 Teorema del valor medio para integrales", 2)
    vm = r["valor_medio"]
    parrafo(doc, "La tasa promedio de pérdida en [0, 6] es el valor que, multiplicado por la duración, da la misma "
                 "área:")
    ecuacion(doc, f"r̄ = (1/6) ∫₀⁶ r(t) dt = {r['exacto_lluvias_6m']:.4f} / 6 = {vm['tasa_promedio']:.4f} m³/mes")
    parrafo(doc, "El teorema garantiza que existe un instante c en [0, 6] donde r(c) = r̄. Despejando:")
    ecuacion(doc, f"c = ln[(e^(6k) − 1) / (6k)] / k = {vm['c']:.2f} meses")
    parrafo(doc, f"A los {vm['c']:.1f} meses la pérdida instantánea coincide con el promedio. Como la curva es "
                 "convexa, ese instante está después de la mitad del periodo.")

    titulo(doc, "3.6 Material necesario y costo de reparar", 2)
    parrafo(doc, "Toneladas = (V₀ + P(T)) × 2.4 × 1.10   ·   Costo = F + c_m² · (V₀ + P(T)) / d")
    tabla(doc, ["Temporada", "Meses de espera", "Material perdido (m³)", "Toneladas para reparar",
                "Costo de reparar", "Costo extra por esperar"],
          [[x.temporada, int(x.meses), f"{x.perdida_m3:.3f}", f"{x.toneladas:.2f}", m(x.costo),
            m(x.costo_extra_por_esperar)] for x in t1.itertuples()], [2.2, 2, 2.8, 2.8, 2.6, 3])
    figura(doc, "g3_costo_esperar.png", "Figura 3. Costo de reparar un bache típico según los meses de espera.")

    titulo(doc, "3.7 Un año completo: integral por tramos", 2)
    a = r["anual_por_tramos"]
    parrafo(doc, "Durante el año la tasa cambia con la temporada (secas noviembre-abril, lluvias mayo-octubre). Por la "
                 "propiedad de aditividad, la integral anual es la suma de las integrales de cada mes, cada una con "
                 "su k:")
    ecuacion(doc, "P(año) = ∫₀¹ r₁ dt + ∫₁² r₂ dt + … + ∫₁₁¹² r₁₂ dt")
    parrafo(doc, f"Empezando en enero, el bache típico pierde {a['perdida_m3']:.3f} m³ en el año y termina con "
                 f"{a['volumen_final_m3']:.3f} m³. Repararlo en enero cuesta {m(a['costo_enero'])}; en diciembre, "
                 f"{m(a['costo_diciembre'])}: {a['costo_diciembre'] / a['costo_enero']:.1f} veces más.")

    titulo(doc, "3.8 Aplicación a negocios: valor presente de esperar", 2)
    parrafo(doc, "Un argumento para esperar es que el dinero gastado mañana «vale menos» hoy. Con descuento continuo "
                 f"(tasa anual de 11 %, δ = {r['delta_mensual']:.4f} mensual):")
    ecuacion(doc, "VP(T) = C(T) · e^(−δT)")
    tabla(doc, ["Meses de espera", "VP en secas", "VP en lluvias"],
          [[x["meses"], m(x["vp_secas"]), m(x["vp_lluvias"])] for x in r["valor_presente"]], [3.5, 4, 4])
    parrafo(doc, f"Aun descontando, esperar sale más caro, porque el daño crece más rápido (k = {ks:.3f} a {kl:.3f}) "
                 f"que la tasa de descuento (δ ≈ {r['delta_mensual']:.3f}). Solo convendría esperar si k < δ.")

    titulo(doc, "3.9 ¿Cada cuánto conviene intervenir? (optimización)", 2)
    io = r["intervalo_optimo"]
    parrafo(doc, "En un programa preventivo se sellan los defectos cada T meses. Cada intervención tiene un costo fijo "
                 f"F = {m(r['costo_fijo'])} (traslado, señalización, cuadrilla; tarifa de SIPA) más el material del "
                 "defecto acumulado, que parte de "
                 "v = 0.004 m³. El costo promedio por mes es:")
    ecuacion(doc, "A(T) = [F + c · v · e^(kT)] / T")
    parrafo(doc, "Derivando e igualando a cero:")
    ecuacion(doc, "A′(T) = [c·v·e^(kT)·(kT − 1) − F] / T² = 0   ⟹   c·v·e^(kT)·(kT − 1) = F")
    parrafo(doc, f"La ecuación se resuelve numéricamente. Con la k promedio anual ({kp:.3f}) el óptimo es "
                 f"T* = {io['promedio']:.1f} meses, con un costo de {m(io['A_promedio'])} por mes; si todo el año "
                 f"fuera de lluvias, T* = {io['lluvias']:.1f} meses. Intervenir cada 3 meses costaría "
                 f"{m(io['A_cada_3_meses'])} por mes y esperar 4 años, {m(io['A_cada_48_meses'])}.")
    figura(doc, "g4_intervalo_optimo.png", "Figura 4. Costo promedio mensual A(T) y su mínimo.")

    titulo(doc, "3.10 Efecto del peso de los vehículos", 2)
    cp = r["cuarta_potencia"]
    tabla(doc, ["W / W₀", "Factor (W/W₀)⁴", "Material perdido en 6 meses de lluvias (m³)"],
          [[f"{x['w_rel']:.1f}", f"{x['phi']:.2f}", f"{x['perdida_6m']:.3f}"] for x in cp], [3, 4, 7])
    parrafo(doc, "Un aumento de 30 % en la carga por eje casi triplica el material perdido. Por eso las vialidades con "
                 "transporte de carga y autobuses deben tener más prioridad y revisiones más frecuentes.")
    figura(doc, "g5_cuarta_potencia.png", "Figura 5. Ley de la cuarta potencia.")

    # 4 -----------------------------------------------------------------
    titulo(doc, "4. Aplicación a los baches de SIPA")
    parrafo(doc, f"El modelo se aplicó a los {r['baches_analizados']:,} baches validados que aún no tienen orden de "
                 "trabajo en la base de datos (CDMX y Chalco), con su área y profundidad, en el escenario de lluvias:")
    tabla(doc, ["Indicador", "Valor"], [
        ["Costo de repararlos hoy", m(tb["costo_hoy"])],
        ["Costo extra si se espera 3 meses", m(tb["extra_3m"])],
        ["Costo extra si se espera 6 meses", m(tb["extra_6m"])],
        ["Costo extra si se espera 12 meses", m(tb["extra_12m"])],
        ["Mezcla asfáltica necesaria hoy", f"{tb['toneladas_hoy']:,.0f} t"],
        ["Mezcla necesaria tras 6 meses de lluvias", f"{tb['toneladas_6m']:,.0f} t"],
    ], [8, 6])
    parrafo(doc, "Territorios donde esperar cuesta más (6 meses de lluvias):")
    filas = [[x.territorio, int(x.baches), m(x.costo_hoy), m(x.extra_6m)] for x in t4.head(5).itertuples()]
    ch = r.get("chalco")
    if ch:
        filas.append(["CHALCO", int(ch["baches"]), m(ch["costo_hoy"]), m(ch["extra_6m"])])
    tabla(doc, ["Territorio", "Baches", "Costo hoy", "Costo extra a 6 meses"], filas, [5, 2.5, 4, 4.5])

    # 5 -----------------------------------------------------------------
    titulo(doc, "5. Respuesta al incidente crítico")
    vinetas(doc, [
        f"¿Cuánto material se pierde? Un bache típico pierde {lluv6.perdida_m3:.3f} m³ en 6 meses de lluvias "
        f"(P(T) = V₀·(e^(kT) − 1)) y pasa de necesitar {t1.toneladas[4]:.2f} t de mezcla a {lluv6.toneladas:.2f} t.",
        f"¿Cuánto cuesta esperar? Ese mismo bache pasa de {m(t1.costo[4])} a {m(lluv6.costo)}. Para los "
        f"{r['baches_analizados']:,} baches pendientes de SIPA, esperar 6 meses de lluvias cuesta "
        f"{m(tb['extra_6m'])} más que repararlos hoy.",
        "Esperar no se justifica ni con valor presente, porque el daño crece más rápido que la tasa de descuento.",
        "Las lluvias aceleran el daño 1.8 veces (dato real), así que conviene reparar antes de mayo.",
        f"Un programa preventivo con intervenciones cada {io['promedio']:.0f} meses minimiza el costo promedio.",
    ])
    parrafo(doc, "El modelo apoya el enfoque preventivo del problema prototípico y se conecta con SIPA: el costo "
                 "de esperar puede sumarse al criterio «riesgo de deterioro mayor» del Índice de Prioridad Urbana.",
            "Conexión con el proyecto. ")

    # 6 -----------------------------------------------------------------
    titulo(doc, "6. Supuestos y limitaciones")
    vinetas(doc, [
        "La tasa base k = 0.08 mensual es un supuesto ilustrativo; solo el factor de lluvias (1.8) sale de datos reales.",
        "El área y la profundidad de los baches de la base son sintéticas; los resultados deben leerse como orden de "
        "magnitud.",
        "El crecimiento exponencial no puede seguir indefinidamente: un bache real tiene un tamaño máximo (el carril), "
        "así que el modelo es válido para horizontes cortos (meses, no años). Un modelo logístico corregiría esto.",
        "No se modela el tránsito real de cada vialidad (no hay datos de aforo); la cuarta potencia se analiza por "
        "escenarios.",
        "Los costos salen del mismo archivo de tarifas que usa la base SIPA, así que el costo de reparar hoy coincide "
        "con el costo estimado de cada bache en la base. Las tarifas son ilustrativas y deben sustituirse por el "
        "tabulador oficial de la autoridad.",
    ])

    titulo(doc, "Referencias")
    vinetas(doc, [
        "Granville, W., Smith, W., & Longley, J. (2007). Cálculo diferencial e integral (2.ª ed.). McGraw-Hill.",
        "Highway Research Board. (1962). The AASHO Road Test, Report 5: Pavement Research (Special Report 61E). "
        "National Academy of Sciences.",
        "Instituto Mexicano del Transporte. Pavimentos flexibles: problemática, metodologías de diseño y "
        "tendencias (Publicación Técnica 104).",
        "Datos: base maestra de solicitudes de bacheo CDMX 2019-2022; datos abiertos de Chalco 2025-2026.",
    ])
    titulo(doc, "Anexo. Cómo reproducir los cálculos", 2)
    parrafo(doc, "python calculo/degradacion.py  (lee la base SIPA, calcula todo y genera las gráficas y tablas en "
                 "calculo/resultados/). El código documenta cada fórmula.")

    doc.save(SALIDA)
    print(f"Documento generado: {SALIDA}")


if __name__ == "__main__":
    main()
