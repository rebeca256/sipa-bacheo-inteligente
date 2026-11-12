"""
SIPA - Genera el documento de la 2ª entrega de Probabilidad a partir de los
resultados de probabilidad/riesgo_72h.py (ejecutarlo antes).

Uso (desde la carpeta del proyecto):
    python probabilidad/riesgo_72h.py
    python scripts/generar_doc_probabilidad.py
Salida:
    avance2_Probabilidad_semaforo72h.docx
"""

import json
from pathlib import Path

import pandas as pd
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt

from generar_doc_planeacion_bd import AZUL, parrafo, tabla, titulo, vinetas

RES = Path("probabilidad/resultados")
SALIDA = "avance2_Probabilidad_semaforo72h.docx"


def ecuacion(doc, texto):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(texto)
    r.font.name = "Cambria Math"
    r.font.size = Pt(12)
    return p


def figura(doc, archivo, pie, ancho=15):
    doc.add_picture(str(RES / archivo), width=Cm(ancho))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(pie)
    r.italic = True
    r.font.size = Pt(9)


def pc(x, d=1):
    return f"{x * 100:.{d}f} %"


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
        ("Segunda entrega · Probabilidad", 14, True),
        ("Incidente crítico: ¿Qué vialidad debe atenderse primero?", 12, False),
        ("Semáforo de Prioridad de Bacheo y riesgo de siniestro a 72 horas", 12, False),
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
          [["UCA", "Probabilidad (LCDN3PRO8)"],
           ["Docente", "María Guadalupe Sierra Hernández"],
           ["Grupo", "302"],
           ["Fecha de entrega", "13 de noviembre de 2026"]], [4.5, 7])
    doc.add_page_break()


def main():
    r = json.loads((RES / "resumen.json").read_text(encoding="utf-8"))
    b, ct, po, co = r["basicos"], r["celda_top"], r["ponchadura"], r["continuas"]
    nb, rg, inc, pe = r["binomial_negativa"], r["riesgo"], r["incidente"], r["pendientes"]
    cont = pd.read_csv(RES / "t1b_contingencia.csv", index_col=0)
    comp = pd.read_csv(RES / "t3_poisson_vs_binomial_negativa.csv")
    sem = r["semaforo_celdas"]
    n_celdas = r["celdas"]

    doc = Document()
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(11)
    for s in doc.sections:
        s.left_margin = s.right_margin = Cm(2.2)

    portada(doc)

    # 1 -----------------------------------------------------------------
    titulo(doc, "1. El incidente crítico")
    parrafo(doc, "La autoridad tiene recursos limitados y debe decidir qué vialidades atender primero. Una vialidad "
                 "puede tener muchos reportes de baches y poco riesgo de accidente, y otra pocos reportes y mucho "
                 "riesgo. El incidente plantea dos preguntas:")
    vinetas(doc, [
        "¿Debe priorizarse la vialidad con más baches reportados o la que tiene mayor probabilidad de generar "
        "consecuencias negativas para la población?",
        "¿Cómo diseñar un modelo de riesgo de siniestro a 72 horas y comunicarlo con un semáforo verde, amarillo "
        "y rojo?",
    ])
    parrafo(doc, "Además pide calcular la probabilidad de que un bache profundo en vía rápida provoque un accidente "
                 "grave o una ponchadura, con base en el aforo vehicular y el historial de accidentes.")

    # 2 -----------------------------------------------------------------
    titulo(doc, "2. Datos y unidad de análisis")
    tabla(doc, ["Fuente", "Contenido", "Uso"], [
        ["Hechos de tránsito de la SSC (datos abiertos CDMX)",
         f"{r['accidentes']:,} accidentes georreferenciados 2018-2019; {r['graves']:,} graves "
         "(con persona fallecida o prioridad ALTA)", "Historial de accidentes por celda"],
        ["Base maestra de reportes de bacheo CDMX (limpia)",
         "Reportes ciudadanos 2019-2022, sin duplicados ni periodos atípicos", "Presencia de baches por celda"],
        ["Base de datos SIPA (SQL Server)",
         f"{pe['baches']:,} baches pendientes con su IPU y semáforo actual", "Comparación con el semáforo actual"],
    ], [4.5, 7, 4.5])
    parrafo(doc, f"Las dos fuentes se cruzan en la misma cuadrícula de 250 m × 250 m que usa SIPA. El año en común "
                 f"es 2019, y el espacio muestral son las {n_celdas:,} celdas con algún accidente o reporte. Para "
                 f"cada celda se definen tres eventos:", "Unidad de análisis. ")
    vinetas(doc, [
        "B: la celda tuvo baches reportados en 2019.",
        "A: la celda tuvo al menos un accidente en 2019.",
        "G: la celda tuvo al menos un accidente grave en 2019.",
    ])

    # 3 -----------------------------------------------------------------
    titulo(doc, "3. Unidad A · Conceptos básicos de probabilidad")

    titulo(doc, "3.1 Interpretación frecuentista y probabilidad condicional", 2)
    parrafo(doc, f"Interpretación frecuentista: de todos los reportes de baches, el {pc(b['p_lluvias'])} se hizo en "
                 "temporada de lluvias; esa frecuencia relativa es la estimación de la probabilidad.")
    c = cont.values  # filas: no B, B · columnas: no A, A
    tabla(doc, ["", "Sin accidente (no A)", "Con accidente (A)", "Total"], [
        ["Sin baches (no B)", int(c[0, 0]), int(c[0, 1]), int(c[0].sum())],
        ["Con baches (B)", int(c[1, 0]), int(c[1, 1]), int(c[1].sum())],
        ["Total", int(c[:, 0].sum()), int(c[:, 1].sum()), int(c.sum())],
    ], [4, 3.5, 3.5, 2.5])
    ecuacion(doc, f"P(A | B) = {b['p_a_dado_b']:.3f}        P(A | no B) = {b['p_a_dado_nob']:.3f}")
    parrafo(doc, "Si A y B fueran independientes, ambas probabilidades serían iguales. Una celda con baches tiene "
                 "más probabilidad de registrar accidentes.")

    titulo(doc, "3.2 Independencia: prueba chi cuadrada", 2)
    ecuacion(doc, f"χ² = {b['chi2']:.2f}      valor p = {b['p_valor']:.1e}")
    parrafo(doc, "Con un valor p mucho menor que 0.05 se rechaza la independencia: los eventos «bache» y "
                 "«accidente» están asociados. Asociación no es causalidad: las calles con más tránsito tienen más "
                 "baches y más accidentes a la vez (ver limitaciones).")

    titulo(doc, "3.3 Probabilidad total y teorema de Bayes", 2)
    parrafo(doc, "Probabilidad de que una celda tenga un accidente grave, considerando ambos casos:")
    ecuacion(doc, f"P(G) = P(G|B)·P(B) + P(G|no B)·P(no B) = {b['p_g_dado_b']:.4f}·{b['p_b']:.3f} + "
                  f"{b['p_g_dado_nob']:.4f}·{1 - b['p_b']:.3f} = {b['p_g_total']:.4f}")
    parrafo(doc, "Pregunta inversa: si en una celda ocurrió un accidente grave, ¿qué probabilidad hay de que tuviera "
                 "baches reportados?")
    ecuacion(doc, f"P(B | G) = P(G|B)·P(B) / P(G) = {b['p_b_dado_g']:.3f}")
    parrafo(doc, f"La evidencia de un accidente grave sube la probabilidad de que haya baches de "
                 f"{pc(b['p_b'])} (a priori) a {pc(b['p_b_dado_g'])} (a posteriori). Así se usa Bayes en SIPA: "
                 "un accidente grave reportado debe disparar una inspección de la zona.")

    titulo(doc, "3.4 Técnicas de conteo", 2)
    parrafo(doc, "Ejemplo ilustrativo: hay 20 baches en rojo, 8 de ellos en vía rápida, y la autoridad revisa 5 "
                 "al azar. ¿Qué probabilidad hay de que al menos 3 estén en vía rápida? Con combinaciones:")
    ecuacion(doc, f"P(X ≥ 3) = Σₖ₌₃⁵ C(8,k)·C(12,5−k) / C(20,5) = {b['p_conteo']:.3f}")
    parrafo(doc, "Este cálculo sirve para diseñar auditorías de la autoridad por muestreo, sin revisar todos los casos.")

    # 4 -----------------------------------------------------------------
    titulo(doc, "4. Unidad B · Variables aleatorias")
    parrafo(doc, "Sea X el número de accidentes de una celda en 2019 (variable aleatoria discreta). Sus parámetros "
                 "por grupo:")
    tabla(doc, ["Grupo", "Celdas", "E[X]", "Var[X]", "Var / E", "P(X = 0)"],
          [[x["grupo"], f"{x['celdas']:,}", f"{x['E[X]']:.2f}", f"{x['Var[X]']:.2f}", f"{x['Var/E']:.2f}",
            f"{x['P(X=0)']:.3f}"] for x in r["variable_aleatoria"]], [3.8, 2, 2, 2, 2, 2.2])
    va = {x["grupo"]: x for x in r["variable_aleatoria"]}
    parrafo(doc, f"Una celda con baches tiene en promedio {va['Con baches (B)']['E[X]']:.2f} accidentes al año, "
                 f"contra {va['Sin baches']['E[X]']:.2f} sin baches: {rg['rr']:.2f} veces más. Ese cociente es el "
                 "riesgo relativo (RR) que usa el modelo de 72 h.")
    parrafo(doc, f"en una distribución Poisson la varianza es igual a la media (Var/E = 1). Aquí "
                 f"Var/E ≈ {va['Todas']['Var/E']:.1f}: hay sobredispersión, porque unas pocas celdas concentran "
                 "muchos accidentes. Eso obliga a usar otra distribución (sección 5.2).",
            "Momento de segundo orden: ")

    # 5 -----------------------------------------------------------------
    titulo(doc, "5. Unidad C · Distribuciones discretas")

    titulo(doc, "5.1 Bernoulli, binomial y Poisson en la celda más peligrosa", 2)
    parrafo(doc, f"La celda {ct['celda']} tuvo {ct['accidentes']} accidentes en 2 años. Cada día es un ensayo "
                 f"Bernoulli: hay accidente con probabilidad p = {ct['p_dia']:.4f}. En 72 h (n = 3 días):")
    ecuacion(doc, f"Binomial:  P(X ≥ 1) = 1 − (1 − p)³ = {ct['p72_binomial']:.3f}")
    ecuacion(doc, f"Poisson:  λ = {ct['lam_dia']:.4f}/día,  μ = 3λ,  P(X ≥ 1) = 1 − e^(−μ) = {ct['p72_poisson']:.3f}")
    parrafo(doc, "Ambos modelos coinciden: en esa celda hay casi 1 de cada 5 probabilidades de un accidente en las "
                 "próximas 72 horas.")

    titulo(doc, "5.2 Binomial negativa frente a Poisson", 2)
    parrafo(doc, "Por la sobredispersión, se ajustó una binomial negativa por el método de momentos:")
    ecuacion(doc, f"r = m² / (s² − m) = {nb['media']:.3f}² / ({nb['varianza']:.3f} − {nb['media']:.3f}) = "
                  f"{nb['r']:.3f}")
    tabla(doc, ["k accidentes", "Datos 2019", "Poisson", "Binomial negativa"],
          [[int(x.k), f"{x.empirica:.3f}", f"{x.poisson:.3f}", f"{x.binomial_negativa:.3f}"]
           for x in comp.head(7).itertuples()], [3, 3, 3, 3.5])
    parrafo(doc, f"Poisson predice muy pocas celdas sin accidentes ({comp.poisson[0]:.3f} contra "
                 f"{comp.empirica[0]:.3f} real) y casi ninguna con muchos; la binomial negativa reproduce ambos "
                 "extremos.")
    figura(doc, "g1_accidentes_por_celda.png", "Figura 1. Accidentes por celda: datos, Poisson y binomial negativa.")

    titulo(doc, "5.3 Geométrica y tiempo de espera discreto", 2)
    parrafo(doc, "Número de días hasta el primer día con accidente en la celda más peligrosa (geométrica) y hasta "
                 "el tercero (binomial negativa):")
    ecuacion(doc, f"E[días hasta el 1.º] = 1/p = {ct['esperanza_geometrica']:.1f}      "
                  f"P(primero en ≤ 7 días) = {ct['p_geom_7']:.3f}      E[días hasta el 3.º] = 3/p = "
                  f"{ct['esperanza_nbinom_3']:.1f}")

    titulo(doc, "5.4 Aproximación de la binomial por Poisson: ponchaduras", 2)
    parrafo(doc, f"Escenario de un bache profundo en vía rápida con {po['n'] // 3:,} vehículos al día. Si el 3 % pasa "
                 f"la llanta por el bache y el 1 % de esos sufre daño, cada vehículo tiene p = {po['p']:.4f}. En 72 h "
                 f"pasan n = {po['n']:,} vehículos: X ~ Binomial(n, p), con n grande y p pequeña, así que se aproxima "
                 "con Poisson:")
    ecuacion(doc, f"μ = n·p = {po['mu']:.0f} ponchaduras esperadas en 72 h      "
                  f"error máximo de la aproximación = {po['error_max_aprox']:.1e}")
    parrafo(doc, "Con ese aforo, que haya al menos una ponchadura es prácticamente seguro. El costo social "
                 "esperado (ponchaduras × costo de reparar una llanta) justifica atender en horas un bache profundo "
                 "en vía rápida. Los porcentajes de 3 % y 1 % son supuestos y deben calibrarse.")

    # 6 -----------------------------------------------------------------
    titulo(doc, "6. Unidad D · Distribuciones continuas")

    titulo(doc, "6.1 Exponencial y gamma: tiempo entre accidentes", 2)
    parrafo(doc, f"En la celda más peligrosa, el tiempo entre accidentes tiene media {co['media_espera']:.1f} días. "
                 f"La prueba de Kolmogorov-Smirnov (D = {co['ks_estadistico']:.3f}, valor p = {co['ks_p']:.2f}) no "
                 "rechaza que sea exponencial, como predice un proceso de Poisson.")
    ecuacion(doc, f"P(T ≤ 3 días) = 1 − e^(−3/{co['media_espera']:.1f}) = {co['p_exp_72']:.3f}")
    parrafo(doc, f"El tiempo hasta el tercer accidente es la suma de tres exponenciales, una gamma(3, θ): su media es "
                 f"{co['gamma3_media']:.1f} días y la probabilidad de que ocurra en 30 días es "
                 f"{co['gamma3_p30']:.3f}.")
    figura(doc, "g2_exponencial.png", "Figura 2. Días entre accidentes y la densidad exponencial ajustada.")

    titulo(doc, "6.2 Uniforme: ¿los accidentes ocurren a cualquier hora?", 2)
    parrafo(doc, f"Si fueran uniformes, cada hora tendría 1/24 de los accidentes. La chi cuadrada de bondad de "
                 f"ajuste da χ² = {co['chi_hora']:,.0f} (valor p ≈ 0): se rechaza la uniformidad. Las brigadas y "
                 "la señalización deben concentrarse en las horas de mayor riesgo.")
    figura(doc, "g4_hora_uniforme.png", "Figura 3. Proporción de accidentes por hora frente a la uniforme.")

    titulo(doc, "6.3 Normal, teorema del límite central y t de Student", 2)
    parrafo(doc, f"Reportes de baches por día en la ciudad: en lluvias, media {co['media_ll']:.1f} y desviación "
                 f"{co['sd_ll']:.1f}; en secas, media {co['media_se']:.1f} y desviación {co['sd_se']:.1f}. Si la "
                 f"capacidad diaria de atención es {co['capacidad']:.0f} reportes (un día alto de secas):")
    ecuacion(doc, f"P(X > {co['capacidad']:.0f}) = 1 − Φ(({co['capacidad']:.0f} − {co['media_ll']:.1f}) / "
                  f"{co['sd_ll']:.1f}) = {co['p_normal']:.3f}      (frecuencia real: {co['p_empirica']:.3f})")
    parrafo(doc, "La aproximación normal es razonable: en lluvias, más de 1 de cada 4 días se rebasa la capacidad.")
    lo, hi = r["ic_lluvias"]
    parrafo(doc, f"Por el teorema del límite central, la media muestral es aproximadamente normal aunque los datos "
                 f"no lo sean. El intervalo de confianza del 95 % para la media diaria en lluvias es "
                 f"[{lo:.1f}, {hi:.1f}] reportes.")
    parrafo(doc, f"La prueba t de Welch (lluvias > secas) da t = {co['t']:.1f}, con valor p ≈ 0: en lluvias "
                 "llegan significativamente más reportes, lo que justifica recomendar a la autoridad que refuerce sus brigadas de mayo a octubre.")
    figura(doc, "g3_normal_temporadas.png", "Figura 4. Reportes diarios por temporada y su aproximación normal.")

    # 7 -----------------------------------------------------------------
    titulo(doc, "7. Modelo de riesgo de siniestro a 72 horas")
    parrafo(doc, "Para una celda c con un bache activo, el número de accidentes en las próximas 72 horas se modela "
                 "como Poisson:")
    ecuacion(doc, "N_c ~ Poisson(μ_c),     μ_c = λ_c · RR · 3/365,     P(al menos uno en 72 h) = 1 − e^(−μ_c)")
    tabla(doc, ["Componente", "Cómo se obtiene"], [
        ["λ_c (accidentes por año)",
         "Bayes empírico gamma-Poisson: λ_c = (r + n_c) / (r/m + 2). Una celda sin accidentes no queda con "
         "riesgo cero y una con pocos datos se acerca al promedio."],
        ["RR (riesgo relativo)", f"{rg['rr']:.2f}: accidentes por celda con baches / sin baches (sección 4)."],
        ["3/365", "Ventana de 72 horas."],
        ["Accidente grave", f"Igual, con la proporción de graves ({pc(rg['p_grave'])}) en lugar de todos."],
    ], [4, 12])
    titulo(doc, "7.1 Semáforo de Prioridad de Bacheo", 2)
    tabla(doc, ["Color", "Regla", "Celdas", "Interpretación"], [
        ["ROJO", "P(72 h) ≥ 3 %", f"{sem['ROJO']:,}", "Atender en 72 h"],
        ["AMARILLO", "1 % ≤ P(72 h) < 3 %", f"{sem['AMARILLO']:,}", "Programar en la semana"],
        ["VERDE", "P(72 h) < 1 %", f"{sem['VERDE']:,}", "Mantenimiento programado"],
    ], [2.5, 4, 2.5, 6])
    parrafo(doc, "El umbral rojo de 3 % equivale a un accidente en 1 de cada 33 ventanas de 72 horas. Los umbrales "
                 "son una decisión de política pública y deben acordarse con la autoridad; el modelo da la "
                 "probabilidad, no el umbral.")
    figura(doc, "g5_semaforo_72h.png", "Figura 5. Distribución del riesgo a 72 h por celda y umbrales del semáforo.")

    titulo(doc, "7.2 Bache profundo en vía rápida", 2)
    parrafo(doc, f"En las {inc['celdas_via_rapida']:,} celdas de vías rápidas (Periférico, Circuito Interior, "
                 "Viaducto, Calzada de Tlalpan, etc.):")
    tabla(doc, ["Indicador", "Mediana", "Percentil 90"], [
        ["P(accidente en 72 h)", pc(inc["p72_accidente_mediana"], 2), pc(inc["p72_accidente_p90"], 2)],
        ["P(accidente grave en 72 h)", pc(inc["p72_grave_mediana"], 3), pc(inc["p72_grave_p90"], 3)],
        ["P(accidente en 72 h) en otras vías", pc(inc["p72_otras_mediana"], 2), "—"],
        ["Ponchaduras esperadas en 72 h (escenario)", f"{po['mu']:.0f}", "—"],
    ], [7, 3.5, 3.5])
    parrafo(doc, f"Una celda típica de vía rápida tiene {inc['p72_accidente_mediana'] / inc['p72_otras_mediana']:.1f}"
                 f" veces más riesgo de accidente a 72 h que una de otras vías. La fracción atribuible al bache es "
                 f"1 − 1/RR = {pc(inc['fraccion_atribuible'])}: aproximadamente uno de cada cuatro accidentes en "
                 "celdas con baches se evitaría si el riesgo bajara al de las celdas sin baches. El accidente grave "
                 "es poco probable en 72 h, pero la ponchadura es casi segura.")

    # 8 -----------------------------------------------------------------
    titulo(doc, "8. ¿Más reportes o más riesgo? Comparación con el semáforo actual")
    parrafo(doc, f"Se aplicó el modelo a los {pe['baches']:,} baches pendientes de la base SIPA y se comparó con el "
                 "semáforo del IPU actual:")
    tabla(doc, ["Semáforo", "Por riesgo a 72 h", "Por IPU actual"],
          [[c, pe["semaforo_72h"].get(c, 0), pe["semaforo_ipu"].get(c, 0)] for c in ["ROJO", "AMARILLO", "VERDE"]],
          [4, 4, 4])
    parrafo(doc, f"Solo coinciden en el {pc(pe['coinciden'], 0)} de los casos, y {pe['rojo72_no_rojo_ipu']} baches "
                 "con riesgo rojo a 72 h no están en rojo en el IPU. La razón: el criterio «riesgo de accidente a "
                 "72 h» del IPU (peso 0.15) hoy usa un valor neutro de 0.5 por falta de un modelo. Este modelo lo "
                 "llena con el valor normalizado v_riesgo_72h, que ya se calcula para cada celda.")
    figura(doc, "g6_ipu_vs_72h.png", "Figura 6. Baches pendientes según el semáforo del IPU y el de riesgo a 72 h.",
           ancho=11)

    # 8.1 Toluca ---------------------------------------------------------
    tl = json.loads(Path("probabilidad/resultados_toluca/resumen.json").read_text(encoding="utf-8"))
    bi, ln, we, co, tc = tl["binomial"], tl["lognormal"], tl["welch"], tl["conteos"], tl["tlc"]
    titulo(doc, "8.1 Validación con baches reales del Estado de México (Toluca)", 2)
    parrafo(doc, f"El tablero público de bacheo de Toluca registra {bi['n']:,} baches reparados (2025-2026) con su "
                 f"tipo y, por folio, sus medidas. Con esos datos reales y una muestra aleatoria de {tc['n']:,} "
                 "medidas se aplicaron las mismas herramientas del curso:")
    tabla(doc, ["Herramienta", "Resultado con datos de Toluca"], [
        ["Binomial: proporción de baches profundos",
         f"p = {pc(bi['p'], 1)} (IC 95 %: {pc(bi['ic95'][0], 1)} a {pc(bi['ic95'][1], 1)}). En una cuadrilla de 10 "
         f"baches, P(al menos 5 profundos) = {pc(bi['p_al_menos_5_de_10'], 1)}"],
        ["Lognormal: área del bache",
         f"mediana {ln['mediana']} m², media {ln['media_teorica']} m²; P(área > 10 m²) = "
         f"{pc(ln['p_mayor_10m2'], 1)} según el modelo y {pc(ln['p_mayor_10m2_observada'], 1)} observada. "
         f"Prueba K-S: D = {ln['ks_D']}, p = {ln['ks_p']}"],
        ["t de Welch (sobre log del área)",
         f"profundos {we['media_profundo']} m² frente a superficiales {we['media_superficial']} m²; "
         f"t = {we['t']}, p = {we['p']:.1e}: los profundos son más grandes"],
        ["Poisson frente a binomial negativa",
         f"baches por colonia y mes: media {co['media']}, varianza {co['varianza']:,.0f} (dispersión "
         f"{co['dispersion']:.0f}). P(0 baches) = {pc(co['p_cero_poisson'], 1)} con Poisson, "
         f"{pc(co['p_cero_binneg'], 1)} con binomial negativa y {pc(co['p_cero_observada'], 1)} observada"],
        ["TLC e intervalo t", f"área media {tc['media']} m², IC 95 % de {tc['ic95'][0]} a {tc['ic95'][1]} m²"],
    ], [5, 11])
    figura(doc, "../resultados_toluca/g1_area_y_meses.png",
           "Figura 7. Área de los baches de Toluca con la lognormal ajustada y baches reparados por mes.")
    parrafo(doc, "La lognormal describe bien la forma del área, aunque con 1,491 datos la prueba K-S detecta "
                 "diferencias pequeñas (sobrestima un poco la cola). Los conteos confirman lo que vimos con los "
                 "accidentes de la CDMX: hay mucha sobredispersión, por eso la binomial negativa es el modelo "
                 "adecuado y Poisson no lo es. Estos datos reemplazan los tamaños simulados del proyecto.",
           "Interpretación. ")

    # 9 -----------------------------------------------------------------
    titulo(doc, "9. Respuesta al incidente crítico")
    vinetas(doc, [
        "¿Más reportes o más riesgo? Más riesgo. El número de reportes depende de la participación ciudadana; el "
        "riesgo depende del historial de accidentes y del tránsito. Las dos clasificaciones solo coinciden en "
        f"{pc(pe['coinciden'], 0)} de los baches pendientes.",
        f"Modelo a 72 h: Poisson con tasa por celda estimada con Bayes empírico (binomial negativa, porque los "
        f"datos tienen sobredispersión) y un riesgo relativo de {rg['rr']:.2f} por la presencia de baches.",
        f"Semáforo: rojo con P ≥ 3 %, amarillo entre 1 % y 3 %, verde menos de 1 %. En la CDMX quedan "
        f"{sem['ROJO']:,} celdas en rojo.",
        f"Bache profundo en vía rápida: P(accidente en 72 h) mediana de {pc(inc['p72_accidente_mediana'], 1)} "
        f"(hasta {pc(inc['p72_accidente_p90'], 1)} en el 10 % más riesgoso), P(accidente grave) de "
        f"{pc(inc['p72_grave_mediana'], 3)} y unas {po['mu']:.0f} ponchaduras esperadas.",
        "Asignación de recursos: en lluvias se rebasa la capacidad diaria más de 1 de cada 4 días; el semáforo "
        "dice qué atender primero esos días.",
    ])
    parrafo(doc, "el semáforo es una recomendación. La decisión final y la reparación son de la autoridad, y cada "
                 "cambio queda registrado en la base de datos.", "Supervisión humana: ")

    # 10 ----------------------------------------------------------------
    titulo(doc, "10. Supuestos y limitaciones")
    vinetas(doc, [
        "Asociación no es causalidad: el riesgo relativo puede deberse en parte al tránsito, que aumenta tanto los "
        "baches como los accidentes. Sin datos de aforo por calle no se puede separar ese efecto.",
        "Los accidentes son de 2018-2019 y los reportes de baches de 2019-2022; el cruce se hace solo con 2019.",
        "La celda de 250 m es una aproximación: no sabemos si el accidente ocurrió exactamente sobre el bache.",
        "Las vías rápidas se identifican por el nombre de la calle en el registro del accidente.",
        "Los accidentes registrados por la SSC casi se duplican a partir de julio de 2019 y siguen altos en "
        "noviembre y diciembre (secas). Parece un cambio en el registro, no un efecto de la lluvia, así que no se "
        "usó para medir la temporada.",
        "El escenario de ponchaduras (aforo de 40,000 vehículos al día, 3 % y 1 %) es ilustrativo.",
        "El ejemplo de conteo (20 baches, 8 en vía rápida) es hipotético.",
        "Los umbrales del semáforo (1 % y 3 %) son una propuesta y deben acordarse con la autoridad.",
    ])

    titulo(doc, "Referencias")
    vinetas(doc, [
        "Walpole, R., Myers, R., Myers, S., & Ye, K. (2012). Probabilidad y estadística para ingeniería y "
        "ciencias (9.ª ed.). Pearson.",
        "Hauer, E. (1997). Observational Before-After Studies in Road Safety. Pergamon.",
        "Secretaría de Seguridad Ciudadana de la Ciudad de México. Hechos de tránsito registrados por la SSC. "
        "Portal de Datos Abiertos de la CDMX.",
        "Datos: base maestra de solicitudes de bacheo CDMX 2019-2022; base de datos SIPA.",
    ])
    titulo(doc, "Anexo. Cómo reproducir los cálculos", 2)
    parrafo(doc, "python probabilidad/riesgo_72h.py  (cruza accidentes y reportes, calcula todo y genera las "
                 "gráficas y tablas en probabilidad/resultados/). Si la base SIPA no está disponible, todo corre "
                 "excepto la comparación de la sección 8.")

    doc.save(SALIDA)
    print(f"Documento generado: {SALIDA}")


if __name__ == "__main__":
    main()
