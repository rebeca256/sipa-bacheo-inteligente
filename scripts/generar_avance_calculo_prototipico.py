"""
SIPA · Avance del problema prototípico para Cálculo Integral (formato breve).

Mismo formato que el avance de Probabilidad: tema, breve justificación,
implementación o planteamiento, esquemas/fórmulas sustituidas y resueltas, y
viabilidad (conclusión positiva). Dos temas:
  1. Integral definida y teorema fundamental del cálculo: material perdido y
     costo de esperar.
  2. Sumas de Riemann: comprobación numérica de la integral.

Cifras de calculo/resultados/ (python calculo/degradacion.py).

Uso (desde la carpeta del proyecto):
    python scripts/generar_avance_calculo_prototipico.py
Salida: avance_Calculo_prototipico_degradacion.docx
"""
import json
import math
import sys
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generar_doc_planeacion_bd import AZUL, parrafo, tabla, titulo, vinetas  # noqa: E402

RES = Path("calculo/resultados")
SALIDA = Path("avance_Calculo_prototipico_degradacion.docx")


def ecuacion(doc, texto):
    """Fórmula centrada. Marcado: ^{...} superíndice y _{...} subíndice (formato de Word, sin
    caracteres Unicode raros que algunos programas muestran como cuadritos)."""
    import re
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(6)
    for parte in re.split(r"([\^_]\{[^}]*\})", texto):
        if not parte:
            continue
        r = p.add_run(parte[2:-1] if parte[:2] in ("^{", "_{") else parte)
        r.font.name = "Cambria Math"
        r.font.size = Pt(12)
        if parte.startswith("^{"):
            r.font.superscript = True
        elif parte.startswith("_{"):
            r.font.subscript = True


def figura(doc, archivo, pie, ancho=14):
    doc.add_picture(str(RES / archivo), width=Cm(ancho))
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
        ("Licenciatura en Ciencia de Datos para Negocios · Unidad Académica Chalco", 12, False),
        ("Tercer semestre · Semestre 2026-2", 12, False),
        ("", 12, False),
        ("Avance del problema prototípico · Cálculo Integral", 16, True),
        ("Bacheo inteligente y priorización urbana", 13, False),
        ("SIPA: ¿cuánto material se pierde y cuánto cuesta esperar?", 14, True),
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
        ["UCA", "Cálculo Integral (LCDN3CAL8)"],
        ["Docente", "María Guadalupe Sierra Hernández"],
        ["Grupo", "302"],
        ["Temas", "1. Integral definida y teorema fundamental del cálculo · 2. Sumas de Riemann"],
    ], [4, 9.5])
    doc.add_page_break()


def main():
    r = json.loads((RES / "resumen.json").read_text(encoding="utf-8"))
    v0, ks, kl = r["v0_tipico_m3"], r["k_secas"], r["k_lluvias"]
    tabla_p = {(x["temporada"], x["meses"]): x for x in r["tabla_perdida"]}
    T = 6
    p_l = v0 * (math.exp(kl * T) - 1)
    p_s = v0 * (math.exp(ks * T) - 1)
    a_l = kl * v0
    tarifa, fijo, prof = r["tarifa_m2"], r["costo_fijo"], r["profundidad_tipica_cm"] / 100
    c_hoy = fijo + tarifa * v0 / prof
    c_l = fijo + tarifa * (v0 + p_l) / prof
    ton_hoy, ton_l = v0 * 2.4 * 1.10, (v0 + p_l) * 2.4 * 1.10

    # Riemann por punto medio con n = 3 (Δt = 2): puntos 1, 3, 5
    n, dt = 3, T / 3
    medios = [dt * (i + 0.5) for i in range(n)]
    valores = [a_l * math.exp(kl * t) for t in medios]
    s_medio = dt * sum(valores)
    izq = [dt * i for i in range(n)]
    val_izq = [a_l * math.exp(kl * t) for t in izq]
    s_izq = dt * sum(val_izq)
    der = [dt * (i + 1) for i in range(n)]
    val_der = [a_l * math.exp(kl * t) for t in der]
    s_der = dt * sum(val_der)

    doc = Document()
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(11)
    for s in doc.sections:
        s.left_margin = s.right_margin = Cm(2.3)
    portada(doc)

    titulo(doc, "La pregunta en una frase")
    parrafo(doc, "Un bache no se queda igual mientras espera: el tránsito y el agua lo hacen crecer. La autoridad necesita "
                 "saber cuánto material se pierde si posterga la reparación y cuánto más le costará. Este avance responde "
                 "con dos temas de Cálculo Integral; el resultado alimenta el semáforo y la comparación entre mantenimiento "
                 "preventivo y reactivo de SIPA.")

    # ================================================================== TEMA 1
    titulo(doc, "Tema 1. Integral definida y teorema fundamental del cálculo")
    titulo(doc, "Breve justificación", 2)
    parrafo(doc, "El tema brinda la herramienta exacta para convertir una tasa en un total: si conocemos con qué rapidez "
                 "se pierde el asfalto en cada instante, la integral definida da el material perdido en todo un periodo. "
                 "Con ese volumen se calcula cuántas toneladas de mezcla harán falta y cuánto costará reparar después, "
                 "que es justo el costo de esperar.")
    titulo(doc, "Implementación o planteamiento", 2)
    parrafo(doc, "Un bache más grande retiene más agua y recibe más impactos, así que crece en proporción a su tamaño. "
                 "Su volumen V(t), con t en meses, cumple:")
    ecuacion(doc, "dV/dt = k · V      ⇒      V(t) = V_{0} · e^{k·t}")
    parrafo(doc, "La tasa de pérdida de material es la derivada del volumen:")
    ecuacion(doc, "r(t) = k · V_{0} · e^{k·t}      [m³ perdidos por mes]")
    tabla(doc, ["Símbolo", "Significado", "Valor", "Origen"], [
        ["V0", "Volumen inicial del bache típico", f"{v0:.5f} m³", f"Mediana de {r['baches_analizados']:,} baches de la base SIPA"],
        ["k (secas)", "Tasa de crecimiento mensual en secas", f"{ks:.3f}", "Supuesto del modelo"],
        ["k (lluvias)", "Tasa en lluvias", f"{kl:.4f}", f"{r['factor_lluvias']:.2f} veces la de secas, según los reportes reales"],
        ["Costo", "Reparar un bache (bacheo profundo)", f"{m(fijo)} fijo + {m(tarifa)} por m²", "Tarifas de SIPA"],
    ], [2.2, 5.3, 3, 5.5])
    parrafo(doc, "Tabla 1. Parámetros del modelo.", None)

    titulo(doc, "Fórmulas sustituidas y resueltas", 2)
    parrafo(doc, "Integral indefinida, con el cambio de variable u = k·t, du = k dt:", "Paso 1. ")
    ecuacion(doc, "∫ k·V_{0}·e^{k·t} dt = V_{0} · ∫ e^{u} du = V_{0} · e^{k·t} + C")
    parrafo(doc, "Integral definida entre 0 y T. Por el teorema fundamental del cálculo, se evalúa la antiderivada en "
                 "los límites:", "Paso 2. ")
    ecuacion(doc, "P(T) = ∫_{0}^{T} k·V_{0}·e^{k·t} dt = [V_{0}·e^{k·t}]_{0}^{T} = V_{0} · (e^{k·T} − 1)")
    parrafo(doc, f"Sustitución: bache típico, T = {T} meses de lluvias.", "Paso 3. ")
    ecuacion(doc, f"P(6) = {v0:.5f} · (e^{{{kl:.4f} × 6}} − 1) = {v0:.5f} · (e^{{{kl * 6:.4f}}} − 1)")
    ecuacion(doc, f"P(6) = {v0:.5f} · ({math.exp(kl * 6):.4f} − 1) = {v0:.5f} × {math.exp(kl * 6) - 1:.4f} = {p_l:.4f} m³")
    parrafo(doc, f"La misma cuenta en secas: P(6) = {v0:.5f} × (e elevado a {ks:.3f} × 6, menos 1) = {p_s:.4f} m³.", "")
    parrafo(doc, f"En seis meses de lluvias el bache pierde {p_l:.3f} m³: más que su volumen inicial "
                 f"({v0:.3f} m³). En secas pierde {p_s:.3f} m³, menos de la mitad.")
    figura(doc, "g1_area_bajo_curva.png", "Figura 1. El área bajo r(t) entre 0 y 6 meses es el material perdido; en "
                                          "lluvias el área es mucho mayor.", 13.5)
    parrafo(doc, "Del volumen al costo (densidad de la mezcla 2.4 t/m³ más 10 % de desperdicio):", "Paso 4. ")
    ecuacion(doc, f"Hoy:      {v0:.4f} m³ × 2.4 × 1.10 = {ton_hoy:.3f} t      Costo = {m(fijo)} + {m(tarifa)} × "
                  f"{v0:.4f} / {prof:.3f} = {m(c_hoy)}")
    ecuacion(doc, f"En 6 meses:  {v0 + p_l:.4f} m³ × 2.4 × 1.10 = {ton_l:.3f} t      Costo = {m(fijo)} + {m(tarifa)} × "
                  f"{v0 + p_l:.4f} / {prof:.3f} = {m(c_l)}")
    tabla(doc, ["Meses de espera", "Material perdido (lluvias)", "Costo (lluvias)", "Material perdido (secas)", "Costo (secas)"],
          [[k, f"{tabla_p[('Lluvias', k)]['perdida_m3']:.3f} m³", m(tabla_p[("Lluvias", k)]["costo"]),
            f"{tabla_p[('Secas', k)]['perdida_m3']:.3f} m³", m(tabla_p[("Secas", k)]["costo"])] for k in [0, 3, 6, 12]],
          [3, 3.4, 2.8, 3.4, 2.8])
    parrafo(doc, "Tabla 2. Material perdido y costo de reparar según el tiempo de espera.", None)

    # ================================================================== TEMA 2
    doc.add_page_break()
    titulo(doc, "Tema 2. Sumas de Riemann")
    titulo(doc, "Breve justificación", 2)
    parrafo(doc, "El tema permite comprobar la integral sin la antiderivada: se divide el periodo en intervalos y se "
                 "suma el área de rectángulos. Es la idea que da origen a la integral y la forma en que una computadora "
                 "la calcula cuando la fórmula no es sencilla, por ejemplo si la tasa cambia mes a mes con la "
                 "temporada.")
    titulo(doc, "Implementación o planteamiento", 2)
    parrafo(doc, "Se aproxima P(6) en lluvias dividiendo [0, 6] en n rectángulos de base Δt = 6 / n. La altura de cada "
                 "rectángulo es r(t) evaluada en su extremo izquierdo, en el derecho o en su punto medio:")
    ecuacion(doc, "P(6) ≈ Σ r(t_{i}*) · Δt,      r(t) = k·V_{0}·e^{k·t}")
    titulo(doc, "Fórmulas sustituidas y resueltas", 2)
    parrafo(doc, f"Con n = 3, Δt = 2 meses y k·V0 = {kl:.4f} × {v0:.5f} = {a_l:.6f}:", "")
    tabla(doc, ["Rectángulo", "Punto medio t*", "Altura r(t*) = k·V0·e^(k·t*)", "Área = r(t*) × Δt"],
          [[i + 1, f"{t:.0f}", f"{a_l:.6f} × e^({kl:.4f} × {t:.0f}) = {v:.5f}", f"{v:.5f} × 2 = {v * dt:.5f}"]
           for i, (t, v) in enumerate(zip(medios, valores))], [2.3, 2.7, 6.5, 4.5])
    ecuacion(doc, f"Suma del punto medio = {' + '.join(f'{v * dt:.5f}' for v in valores)} = {s_medio:.4f} m³")
    parrafo(doc, f"Con los extremos izquierdo (t = 0, 2, 4) y derecho (t = 2, 4, 6) se obtiene {s_izq:.4f} m³ y "
                 f"{s_der:.4f} m³. El valor exacto, {p_l:.4f} m³, queda entre ambos porque r(t) es creciente.")
    rie = r["riemann"]
    tabla(doc, ["n", "Izquierda", "Derecha", "Punto medio", "Error del punto medio"],
          [[x["n"], f"{x['izquierda']:.4f}", f"{x['derecha']:.4f}", f"{x['punto medio']:.4f}",
            f"{abs(x['error_punto medio_%']):.3f} %"] for x in rie], [1.5, 3, 3, 3, 4])
    parrafo(doc, "Tabla 3. Al aumentar n, las tres sumas se acercan al valor exacto; el punto medio converge mucho más "
                 "rápido.", None)
    figura(doc, "g2_riemann.png", "Figura 2. Suma de Riemann por la izquierda con n = 6 rectángulos.", 13)

    # ================================================================== PLANES
    doc.add_page_break()
    titulo(doc, "Plan correctivo y preventivo")
    parrafo(doc, "Con los dos temas anteriores se pueden plantear, con números, los dos tipos de mantenimiento: el "
                 "correctivo repara el daño que ya existe; el preventivo interviene antes de que el daño crezca.")
    tb = r["total_baches"]
    io = r["intervalo_optimo"]
    kp = r["k_promedio"]

    titulo(doc, "Plan correctivo: reparar ya los baches pendientes", 2)
    parrafo(doc, f"Aplicando P(T) = V0 · (e^(kT) − 1) a cada uno de los {r['baches_analizados']:,} baches pendientes de "
                 "la base SIPA y sumando:")
    tabla(doc, ["Escenario", "Mezcla asfáltica", "Costo total", "Costo extra por esperar"], [
        ["Reparar hoy", f"{tb['toneladas_hoy']:,.0f} t", m(tb["costo_hoy"]), "—"],
        ["Esperar 3 meses de lluvias", "—", m(tb["costo_hoy"] + tb["extra_3m"]), m(tb["extra_3m"])],
        ["Esperar 6 meses de lluvias", f"{tb['toneladas_6m']:,.0f} t", m(tb["costo_hoy"] + tb["extra_6m"]), m(tb["extra_6m"])],
        ["Esperar 12 meses", "—", m(tb["costo_hoy"] + tb["extra_12m"]), m(tb["extra_12m"])],
    ], [4.6, 3, 3.6, 4.2])
    parrafo(doc, "Tabla 4. Costo de atender los baches pendientes según el momento de la reparación.", None)
    vinetas(doc, [
        f"Reparar antes de la temporada de lluvias (mayo): esperar 6 meses de lluvias cuesta {m(tb['extra_6m'])} más y "
        f"requiere {tb['toneladas_6m'] / tb['toneladas_hoy']:.1f} veces más mezcla.",
        "Atender en el orden del semáforo de SIPA: primero los rojos (riesgo de accidente) y, entre baches del mismo color, "
        "los que más crecen (zonas con lluvia y tránsito pesado).",
        "Estimar la compra de material con la integral: toneladas = (V0 + P(T)) × 2.4 × 1.10 para cada bache.",
    ])

    titulo(doc, "Plan preventivo: ¿cada cuánto conviene intervenir?", 2)
    parrafo(doc, f"En un programa preventivo se sellan los defectos pequeños cada T meses. Cada intervención cuesta un fijo "
                 f"F = {m(fijo)} (traslado, señalización, cuadrilla) más el material del defecto acumulado, que parte de "
                 "v = 0.004 m³ y crece como e^(kT). El costo promedio por mes es:")
    ecuacion(doc, "A(T) = [F + c · v · e^{k·T}] / T")
    parrafo(doc, "Derivando con la regla del cociente e igualando a cero se obtiene el intervalo óptimo:")
    ecuacion(doc, "A'(T) = [c · v · e^{k·T} · (k·T − 1) − F] / T^{2} = 0      ⇒      c · v · e^{k·T} · (k·T − 1) = F")
    parrafo(doc, f"Resolviendo numéricamente con la k promedio del año ({kp:.3f}):")
    tabla(doc, ["Frecuencia de intervención", "Costo promedio por mes"], [
        ["Cada 3 meses (demasiado seguido)", m(io["A_cada_3_meses"])],
        [f"Cada {io['promedio']:.0f} meses (óptimo, T*)", m(io["A_promedio"])],
        ["Cada 48 meses (demasiado tarde)", m(io["A_cada_48_meses"])],
    ], [8, 5])
    parrafo(doc, "Tabla 5. Costo promedio mensual del mantenimiento preventivo según su frecuencia.", None)
    figura(doc, "g4_intervalo_optimo.png", "Figura 3. Costo promedio mensual A(T): el mínimo marca el intervalo óptimo.", 12.5)
    vinetas(doc, [
        f"Revisar y sellar cada tramo aproximadamente cada {io['promedio']:.0f} meses; en zonas con lluvias intensas, "
        f"cada {io['lluvias']:.0f} meses.",
        "Usar la temporada de secas (noviembre a abril), cuando el daño crece más despacio, para el sellado preventivo.",
        "Revisar con más frecuencia las vías con transporte de carga y autobuses: por la ley de la cuarta potencia, "
        "30 % más de peso por eje casi triplica el material perdido.",
    ])
    tabla(doc, ["", "Plan correctivo", "Plan preventivo"], [
        ["Qué atiende", "Baches que ya existen", "Defectos pequeños antes de que crezcan"],
        ["Cuándo", "Ya, en orden del semáforo y antes de lluvias", f"Cada ≈ {io['promedio']:.0f} meses, de preferencia en secas"],
        ["Herramienta de cálculo", "Integral definida P(T)", "Derivada del costo promedio A(T)"],
        ["Resultado", f"Evita {m(tb['extra_6m'])} de sobrecosto en 6 meses", f"Costo mínimo de {m(io['A_promedio'])} por mes y tramo"],
    ], [3.6, 6, 6.4])
    parrafo(doc, "Tabla 6. Comparación de los dos planes.", None)

    # ================================================================== VIABILIDAD
    titulo(doc, "Viabilidad (conclusión positiva)")
    parrafo(doc, "El cálculo integral hace viable cuantificar el costo de esperar y, con él, justificar el mantenimiento "
                 "preventivo:")
    vinetas(doc, [
        f"Es exacto y verificable: la integral definida da {p_l:.3f} m³ perdidos en 6 meses de lluvias, y las sumas de "
        "Riemann confirman el resultado por un camino independiente.",
        f"Se traduce en dinero: el bache típico pasa de {m(c_hoy)} a {m(c_l)} en 6 meses de lluvias, "
        f"{(c_l / c_hoy - 1) * 100:.0f} % más caro; en 12 meses llega a {m(tabla_p[('Lluvias', 12)]['costo'])}.",
        f"Orienta la planeación: en lluvias el bache duplica su volumen en {r['duplica_lluvias_meses']:.1f} meses, contra "
        f"{r['duplica_secas_meses']:.1f} en secas; conviene reforzar la atención antes y durante la temporada.",
        "Se integra a SIPA: el costo de esperar entra al índice de prioridad y a la comparación financiera, donde el "
        "esquema preventivo resulta 60 % más barato que el reactivo.",
        "Es simple de reproducir: con el área y la profundidad de un bache, cualquier persona puede calcular su costo de "
        "esperar con la fórmula P(T) = V0 · (e^(kT) − 1).",
    ])
    parrafo(doc, "Conclusión: con la integral definida y su comprobación por sumas de Riemann, la autoridad puede saber "
                 "cuánto le cuesta cada mes de retraso; con ello sustenta un plan correctivo (reparar ya, antes de las "
                 "lluvias) y un plan preventivo (intervenir en el intervalo de costo mínimo). Reparar a tiempo es más "
                 "barato, y el modelo es viable y ya está integrado al sistema.", "")

    titulo(doc, "Referencias", 2)
    for ref in [
        "Highway Research Board. (1962). The AASHO Road Test, Report 5: Pavement Research (Special Report 61E).",
        "Stewart, J. (2018). Cálculo de una variable: trascendentes tempranas (8.ª ed.). Cengage Learning.",
        "Base maestra de solicitudes de bacheo de la Ciudad de México 2019-2022 [Conjunto de datos]. Proporcionada para "
        "el problema prototípico.",
    ]:
        pr = doc.add_paragraph(ref)
        pr.paragraph_format.left_indent = Cm(1)
        pr.paragraph_format.first_line_indent = Cm(-1)

    doc.save(SALIDA)
    from simbolos_seguros import asegurar   # sin símbolos que se vean como cuadritos
    asegurar(SALIDA)
    print(f"Documento generado: {SALIDA}")


if __name__ == "__main__":
    main()
