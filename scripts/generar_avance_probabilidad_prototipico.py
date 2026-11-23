"""
SIPA · Avance del problema prototípico para Probabilidad (formato breve).

Formato pedido por la docente: tema, breve justificación, implementación o
planteamiento, esquemas/diagramas/fórmulas sustituidas y resueltas, y
viabilidad (conclusión positiva). Se abordan solo dos temas, los que explican
el Semáforo de Prioridad de Bacheo:
  1. Probabilidad total y teorema de Bayes.
  2. Distribución de Poisson: riesgo de accidente a 72 horas.

Todas las cifras salen de probabilidad/resultados/ (python probabilidad/riesgo_72h.py).

Uso (desde la carpeta del proyecto):
    python scripts/generar_avance_probabilidad_prototipico.py
Salida: avance_Probabilidad_prototipico_semaforo.docx
"""
import json
import math
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generar_doc_planeacion_bd import AZUL, parrafo, tabla, titulo, vinetas  # noqa: E402

RES = Path("probabilidad/resultados")
SALIDA = Path("avance_Probabilidad_prototipico_semaforo.docx")
FIG = RES / "g7_arbol_probabilidad_total.png"
FIG2 = RES / "g8_semaforo_ejemplos.png"


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


def figura(doc, ruta, pie, ancho=14):
    doc.add_picture(str(ruta), width=Cm(ancho))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(pie)
    r.italic = True
    r.font.size = Pt(9)


def pc(x, d=1):
    return f"{x * 100:.{d}f} %"


def arbol(pb, pa_b, pa_nb):
    """Diagrama de árbol de la probabilidad total."""
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.axis("off")
    raiz = (0.05, 0.5)
    nodos1 = {"B": (0.38, 0.8), "B'": (0.38, 0.2)}
    hojas = {("B", "A"): (0.75, 0.92), ("B", "A'"): (0.75, 0.68), ("B'", "A"): (0.75, 0.32), ("B'", "A'"): (0.75, 0.08)}
    p1 = {"B": pb, "B'": 1 - pb}
    p2 = {("B", "A"): pa_b, ("B", "A'"): 1 - pa_b, ("B'", "A"): pa_nb, ("B'", "A'"): 1 - pa_nb}
    for k, (x, y) in nodos1.items():
        ax.plot([raiz[0], x], [raiz[1], y], color="#1F4E8C", lw=1.6)
        ax.text((raiz[0] + x) / 2, (raiz[1] + y) / 2 + 0.04, f"{p1[k]:.4f}", ha="center", fontsize=10, color="#1F4E8C")
        ax.text(x + 0.01, y, k, va="center", fontsize=12, fontweight="bold")
    for (a, b), (x, y) in hojas.items():
        xa, ya = nodos1[a]
        ax.plot([xa + 0.05, x], [ya, y], color="#C8962E", lw=1.4)
        ax.text((xa + 0.05 + x) / 2, (ya + y) / 2 + 0.03, f"{p2[(a, b)]:.4f}", ha="center", fontsize=9.5, color="#8A6514")
        prod = p1[a] * p2[(a, b)]
        ax.text(x + 0.01, y, f"{b}   P = {prod:.4f}", va="center", fontsize=10.5,
                fontweight="bold" if b == "A" else "normal")
    ax.text(raiz[0] - 0.02, raiz[1], "Celda", ha="right", va="center", fontsize=11)
    ax.text(0.38, 1.0, "¿Tuvo baches reportados?", ha="center", fontsize=10, color="#3D4B63")
    ax.text(0.80, 1.0, "¿Tuvo al menos un accidente?", ha="center", fontsize=10, color="#3D4B63")
    ax.set_xlim(-0.12, 1.05)
    ax.set_ylim(-0.02, 1.05)
    fig.tight_layout()
    fig.savefig(FIG, dpi=170)
    plt.close(fig)


def grafica_ejemplos(filas):
    fig, ax = plt.subplots(figsize=(7.5, 3.6))
    colores = {"VERDE": "#2E8B57", "AMARILLO": "#E0A100", "ROJO": "#C0392B"}
    etiquetas = [f"{n} accidentes\nen 2 años" for n, *_ in filas]
    vals = [p * 100 for *_, p, _ in filas]
    cols = [colores[s] for *_, s in filas]
    barras = ax.bar(etiquetas, vals, color=cols)
    for b, v, (*_, s) in zip(barras, vals, filas):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.3, f"{v:.2f} %\n{s}", ha="center", fontsize=9.5)
    ax.axhline(1, color="#E0A100", ls="--", lw=1)
    ax.axhline(3, color="#C0392B", ls="--", lw=1)
    ax.text(3.45, 1.15, "umbral amarillo 1 %", fontsize=8.5, color="#8A6514", ha="right")
    ax.text(3.45, 3.15, "umbral rojo 3 %", fontsize=8.5, color="#C0392B", ha="right")
    ax.set_ylabel("P(al menos un accidente en 72 h)")
    ax.set_ylim(0, max(vals) * 1.25)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIG2, dpi=170)
    plt.close(fig)


def portada(doc):
    for texto, tam, neg in [
        ("Universidad Nacional Rosario Castellanos", 14, True),
        ("Licenciatura en Ciencia de Datos para Negocios · Unidad Académica Chalco", 12, False),
        ("Tercer semestre · Semestre 2026-2", 12, False),
        ("", 12, False),
        ("Avance del problema prototípico · Probabilidad", 16, True),
        ("Bacheo inteligente y priorización urbana", 13, False),
        ("SIPA: el Semáforo de Prioridad de Bacheo", 14, True),
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
        ["UCA", "Probabilidad (LCDN3PRO8)"],
        ["Docente", "María Guadalupe Sierra Hernández"],
        ["Grupo", "302"],
        ["Temas", "1. Probabilidad total y teorema de Bayes · 2. Distribución de Poisson"],
    ], [4, 9.5])
    doc.add_page_break()


def main():
    r = json.loads((RES / "resumen.json").read_text(encoding="utf-8"))
    cont = pd.read_csv(RES / "t1b_contingencia.csv", index_col=0)
    # filas: B (celda con baches) False/True; columnas: A (accidente en 2019) False/True
    cont.index = cont.index.astype(str)
    cont.columns = cont.columns.astype(str)
    n_nb_na, n_nb_a = int(cont.loc["False", "False"]), int(cont.loc["False", "True"])
    n_b_na, n_b_a = int(cont.loc["True", "False"]), int(cont.loc["True", "True"])
    n = n_nb_na + n_nb_a + n_b_na + n_b_a
    nb_ = n_b_na + n_b_a
    pb = nb_ / n
    pa_b = n_b_a / nb_
    pa_nb = n_nb_a / (n_nb_na + n_nb_a)
    pa = pb * pa_b + (1 - pb) * pa_nb
    pb_a = pb * pa_b / pa
    bas = r["basicos"]
    pg, pg_b, pg_nb = bas["p_g_total"], bas["p_g_dado_b"], bas["p_g_dado_nob"]
    pb_g = pb * pg_b / pg

    nbn = r["binomial_negativa"]
    R, m = nbn["r"], nbn["media"]
    ejemplos = []
    for k in [1, 4, 10, 52]:
        lam = (R + k) / (R / m + 2)
        mu = lam * 3 / 365
        p = 1 - math.exp(-mu)
        sem = "ROJO" if p >= 0.03 else ("AMARILLO" if p >= 0.01 else "VERDE")
        ejemplos.append((k, lam, mu, p, sem))
    sem = r["semaforo_celdas"]
    vt = r["validacion_temporal"]
    ps = vt["por_semaforo"]

    arbol(pb, pa_b, pa_nb)
    grafica_ejemplos(ejemplos)

    doc = Document()
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(11)
    for s in doc.sections:
        s.left_margin = s.right_margin = Cm(2.3)
    portada(doc)

    # -------------------------------------------------------------- Contexto
    titulo(doc, "El semáforo en una frase")
    parrafo(doc, "SIPA asigna a cada bache un color: rojo (atender en 72 horas), amarillo (en la semana) o verde "
                 "(mantenimiento programado). El color depende sobre todo de una probabilidad: la de que ocurra al menos "
                 "un accidente en la zona del bache en las próximas 72 horas. Este avance presenta los dos temas de "
                 "Probabilidad que sostienen esa decisión.")

    # ============================================================== TEMA 1
    titulo(doc, "Tema 1. Probabilidad total y teorema de Bayes")
    titulo(doc, "Breve justificación", 2)
    parrafo(doc, "El tema brinda un panorama amplio de cómo se relacionan los baches y los accidentes en toda la ciudad. "
                 "La probabilidad total permite calcular la probabilidad de un accidente combinando las zonas con y sin "
                 "baches; el teorema de Bayes permite invertir la pregunta: si ocurrió un accidente grave, ¿qué tan probable "
                 "es que haya sido en una zona con baches? Es el argumento de fondo del semáforo: los baches sí se asocian "
                 "con más riesgo, así que vale la pena priorizarlos por riesgo y no por quejas.")
    titulo(doc, "Implementación o planteamiento", 2)
    parrafo(doc, f"La Ciudad de México se dividió en {n:,} celdas de 250 m. Para cada celda se registró si en 2019 tuvo "
                 "baches reportados y si tuvo al menos un accidente (datos de la SSC). Se definen los eventos:")
    vinetas(doc, [
        "B: la celda tuvo baches reportados en 2019.  B' (complemento de B): no tuvo.",
        "A: la celda tuvo al menos un accidente en 2019.",
        "G: la celda tuvo al menos un accidente grave en 2019 (con persona fallecida o prioridad alta).",
    ])
    tabla(doc, ["", "Con accidente (A)", "Sin accidente (A')", "Total"], [
        ["Con baches (B)", f"{n_b_a:,}", f"{n_b_na:,}", f"{nb_:,}"],
        ["Sin baches (B')", f"{n_nb_a:,}", f"{n_nb_na:,}", f"{n_nb_na + n_nb_a:,}"],
        ["Total", f"{n_b_a + n_nb_a:,}", f"{n_b_na + n_nb_na:,}", f"{n:,}"],
    ], [4, 3.5, 3.5, 2.5])
    parrafo(doc, "Tabla 1. Celdas de la CDMX según baches y accidentes en 2019.", None)

    titulo(doc, "Diagrama, fórmulas sustituidas y resueltas", 2)
    figura(doc, FIG, "Figura 1. Diagrama de árbol: primero si la celda tiene baches y después si tuvo un accidente.", 15)
    parrafo(doc, "Probabilidades de la tabla:", "Paso 1. ")
    ecuacion(doc, f"P(B) = {nb_:,} / {n:,} = {pb:.4f}          P(B') = 1 − {pb:.4f} = {1 - pb:.4f}")
    ecuacion(doc, f"P(A | B) = {n_b_a:,} / {nb_:,} = {pa_b:.4f}          P(A | B') = {n_nb_a:,} / {n_nb_na + n_nb_a:,} = {pa_nb:.4f}")
    parrafo(doc, "Probabilidad total de que una celda tenga un accidente:", "Paso 2. ")
    ecuacion(doc, "P(A) = P(B)·P(A | B) + P(B')·P(A | B')")
    ecuacion(doc, f"P(A) = ({pb:.4f})({pa_b:.4f}) + ({1 - pb:.4f})({pa_nb:.4f}) = {pb * pa_b:.4f} + {(1 - pb) * pa_nb:.4f} = {pa:.4f}")
    parrafo(doc, f"Comprobación con la tabla: {n_b_a + n_nb_a:,} / {n:,} = {(n_b_a + n_nb_a) / n:.4f}: coincide.")
    parrafo(doc, "Teorema de Bayes: si en una celda hubo un accidente, ¿qué probabilidad hay de que tuviera baches?", "Paso 3. ")
    ecuacion(doc, "P(B | A) = P(B)·P(A | B) / P(A)")
    ecuacion(doc, f"P(B | A) = ({pb:.4f})({pa_b:.4f}) / {pa:.4f} = {pb * pa_b:.4f} / {pa:.4f} = {pb_a:.4f}")
    parrafo(doc, "Lo mismo para los accidentes graves, con P(G | B) y P(G | B') calculadas igual:", "Paso 4. ")
    ecuacion(doc, f"P(G) = ({pb:.4f})({pg_b:.4f}) + ({1 - pb:.4f})({pg_nb:.4f}) = {pg:.4f}")
    ecuacion(doc, f"P(B | G) = ({pb:.4f})({pg_b:.4f}) / {pg:.4f} = {pb_g:.4f}")
    titulo(doc, "Interpretación", 2)
    vinetas(doc, [
        f"Una celda con baches tiene accidente con probabilidad {pc(pa_b)}, contra {pc(pa_nb)} sin baches: "
        f"{pa_b / pa_nb:.2f} veces más.",
        f"Las celdas con baches son el {pc(pb)} de la ciudad, pero concentran el {pc(pb_g)} de las celdas con accidentes "
        f"graves.",
        f"La diferencia es estadísticamente significativa (prueba ji cuadrada: χ² = {bas['chi2']:.1f}, valor p < 0.001).",
        "Es una asociación, no una prueba de causa: las calles con más tránsito tienen más baches y más accidentes. Por "
        "eso el semáforo se calcula con el historial de accidentes de cada zona, que es el tema 2.",
    ])

    # ============================================================== TEMA 2
    doc.add_page_break()
    titulo(doc, "Tema 2. Distribución de Poisson: riesgo de accidente a 72 horas")
    titulo(doc, "Breve justificación", 2)
    parrafo(doc, "El tema permite responder la pregunta concreta que necesita la autoridad: si este bache sigue abierto, "
                 "¿qué tan probable es un accidente en los próximos tres días? Los accidentes son eventos raros, "
                 "independientes y que ocurren a una tasa media en el tiempo: exactamente el escenario de la distribución "
                 "de Poisson. De esa probabilidad sale el color del semáforo.")
    titulo(doc, "Implementación o planteamiento", 2)
    parrafo(doc, "Sea N el número de accidentes en una celda durante las próximas 72 horas. Se modela como Poisson con "
                 "media μ:")
    ecuacion(doc, "N ~ Poisson(μ),     P(N = k) = e^{−μ} · μ^{k} / k!")
    ecuacion(doc, "P(al menos un accidente) = 1 − P(N = 0) = 1 − e^{−μ}")
    parrafo(doc, f"La media de 72 horas sale de la tasa anual de la celda, λ: μ = λ · 3/365. Para que una celda con pocos "
                 f"datos no quede con riesgo cero, λ se estima combinando su historial con el promedio de la ciudad "
                 f"(estimación bayesiana): λ = (r + n) / (r/m + 2), donde n son los accidentes de la celda en 2018-2019, "
                 f"m = {m:.3f} es el promedio de accidentes por celda al año y r = {R:.3f} mide qué tanto varían las "
                 f"celdas entre sí.")
    tabla(doc, ["Color", "Regla", "Acción", "Celdas de la CDMX"], [
        ["ROJO", "P(72 h) ≥ 3 %", "Atender en 72 horas", f"{sem['ROJO']:,}"],
        ["AMARILLO", "1 % ≤ P(72 h) < 3 %", "Programar en la semana", f"{sem['AMARILLO']:,}"],
        ["VERDE", "P(72 h) < 1 %", "Mantenimiento programado", f"{sem['VERDE']:,}"],
    ], [2.5, 4, 4.5, 3])
    parrafo(doc, "Tabla 2. Reglas del Semáforo de Prioridad de Bacheo.", None)

    titulo(doc, "Fórmulas sustituidas y resueltas", 2)
    k, lam, mu, p, s = ejemplos[2]
    parrafo(doc, f"Ejemplo completo: una celda con n = {k} accidentes en dos años.", "")
    ecuacion(doc, f"λ = ({R:.4f} + {k}) / ({R:.4f}/{m:.4f} + 2) = {R + k:.4f} / {R / m + 2:.4f} = {lam:.4f} accidentes al año")
    ecuacion(doc, f"μ = {lam:.4f} × 3/365 = {mu:.5f}")
    ecuacion(doc, f"P(al menos uno en 72 h) = 1 − e^{{−{mu:.5f}}} = 1 − {math.exp(-mu):.5f} = {p:.5f} = {pc(p, 2)}")
    parrafo(doc, f"Como {pc(p, 2)} ≥ 3 %, el bache de esa celda se clasifica en ROJO: atender en 72 horas.")
    parrafo(doc, "La misma cuenta para celdas con distinto historial:", "")
    tabla(doc, ["Accidentes en 2 años (n)", "λ (al año)", "μ (72 h)", "P(al menos uno)", "Semáforo"],
          [[f"{k}", f"{lam:.3f}", f"{mu:.5f}", pc(p, 2), s] for k, lam, mu, p, s in ejemplos], [4, 2.5, 2.5, 3, 2.5])
    figura(doc, FIG2, "Figura 2. Probabilidad de accidente en 72 h según el historial de la celda y umbrales del semáforo.", 14)

    titulo(doc, "Comprobación: ¿el semáforo acierta?", 2)
    parrafo(doc, f"Se repitió el cálculo usando solo los accidentes de {vt['periodo_ajuste']} y se comparó con lo que pasó en "
                 f"{vt['periodo_validacion']}, año que el modelo no vio. Se dividió {vt['periodo_validacion']} en "
                 f"{vt['ventanas_72h']} ventanas reales de 72 horas:")
    tabla(doc, ["Celdas", "P(72 h) predicha", "Fracción observada de ventanas con accidente"],
          [[c.title(), pc(ps[c]["p72_predicha"], 2), pc(ps[c]["p72_observada"], 2)] for c in ["ROJO", "AMARILLO"] if c in ps],
          [3, 4, 7])
    parrafo(doc, f"Las celdas rojas tuvieron accidente en {ps['ROJO']['p72_observada'] / ps['AMARILLO']['p72_observada']:.1f} "
                 "veces más ventanas que las amarillas: el semáforo separa bien las zonas peligrosas. Predice un poco más "
                 f"de lo observado porque {vt['periodo_validacion']} tuvo menos accidentes registrados; por eso el modelo "
                 "se recalibra cada año.")

    # ============================================================== PLANES
    titulo(doc, "Plan correctivo y preventivo")
    parrafo(doc, "El semáforo convierte la probabilidad en dos planes de acción: el correctivo atiende ya el riesgo alto; "
                 "el preventivo vigila que el riesgo bajo no crezca.")
    tabla(doc, ["", "Plan correctivo", "Plan preventivo"], [
        ["A quién", f"Celdas en ROJO ({sem['ROJO']:,}) y AMARILLO ({sem['AMARILLO']:,})", f"Celdas en VERDE ({sem['VERDE']:,})"],
        ["Criterio", "P(accidente en 72 h) ≥ 1 %", "P(accidente en 72 h) < 1 %"],
        ["Acción", "Rojo: reparar en 72 horas. Amarillo: programar en la semana.",
         "Mantenimiento programado e inspección periódica."],
        ["Seguimiento", "Verificar que la probabilidad baje después de reparar.",
         "Recalcular λ y P(72 h) cada año con los accidentes nuevos; si una celda sube de color, pasa al plan correctivo."],
    ], [3, 6.5, 6.5])
    parrafo(doc, "Tabla 4. Planes correctivo y preventivo según el semáforo.", None)
    vinetas(doc, [
        "Correctivo: la probabilidad total y Bayes muestran que las zonas con baches concentran más accidentes graves; "
        "por eso los baches en rojo no deben esperar.",
        f"Preventivo: como la validación mostró que el nivel de riesgo cambia de un año a otro ({vt['periodo_ajuste']} a "
        f"{vt['periodo_validacion']}), el modelo de Poisson se recalibra cada año para que el semáforo siga acertando.",
        "Ambos planes priorizan por riesgo y no por número de quejas, y la autoridad conserva la decisión final.",
    ])

    # ============================================================== VIABILIDAD
    titulo(doc, "Viabilidad (conclusión positiva)")
    parrafo(doc, "La probabilidad hace viable un semáforo de prioridad objetivo, verificable y barato de operar:")
    vinetas(doc, [
        "Es objetivo: el color sale de una fórmula con datos públicos (accidentes de la SSC y reportes ciudadanos), no de "
        "quién se queja más.",
        f"Está justificado: por probabilidad total y Bayes, las zonas con baches tienen más accidentes ({pc(pa_b)} contra "
        f"{pc(pa_nb)}) y concentran más accidentes graves.",
        "Funciona: validado con un año que el modelo no conocía, distingue las zonas rojas de las amarillas.",
        "Es simple de calcular y de explicar: con el número de accidentes de una zona, cualquier persona puede reproducir "
        "la cuenta y verificar el color, como en el ejemplo resuelto.",
        "Se integra al sistema: la probabilidad de 72 h alimenta el criterio de riesgo del Índice de Prioridad Urbana, y la "
        "autoridad conserva la decisión final.",
    ])
    parrafo(doc, "Conclusión: con estos dos temas de probabilidad, la autoridad puede decidir qué bache atender primero "
                 "por el riesgo real de accidente y no por el número de reportes. El Semáforo de Prioridad de Bacheo es "
                 "viable técnica y operativamente.", "")

    titulo(doc, "Referencias", 2)
    for ref in [
        "Rincón, L. (2014). Introducción a la probabilidad. Facultad de Ciencias, UNAM.",
        "Secretaría de Seguridad Ciudadana de la Ciudad de México. (s. f.). Hechos de tránsito registrados por la SSC "
        "[Conjunto de datos]. Portal de Datos Abiertos de la Ciudad de México.",
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
