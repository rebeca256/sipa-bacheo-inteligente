"""
SIPA - Documento del incidente crítico «Contingencias por daños viales» (Estado de México).
Requiere ejecutar antes:  python contabilidad/contingencias_edomex.py
Uso:  python scripts/generar_doc_contingencias_edomex.py
Salida: avance_Contabilidad_contingencias_Edomex.docx
"""
import json
from pathlib import Path

import pandas as pd
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt

from generar_doc_planeacion_bd import AZUL, parrafo, tabla, titulo, vinetas

RES = Path("contabilidad/resultados_edomex")
SALIDA = "avance_Contabilidad_contingencias_Edomex.docx"


def m(x):
    return f"${x:,.0f}"


def mm(x):
    return f"${x / 1e6:,.2f} M"


def pct(x):
    return f"{x * 100:.1f} %"


def figura(doc, archivo, pie, ancho=15):
    doc.add_picture(str(RES / archivo), width=Cm(ancho))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(pie)
    r.italic = True
    r.font.size = Pt(9)


def portada(doc):
    for texto, tam, neg in [
        ("Universidad Nacional Rosario Castellanos", 14, True),
        ("Licenciatura en Ciencia de Datos para Negocios", 12, False),
        ("Unidad Académica Chalco", 12, False),
        ("Tercer semestre · Semestre 2026-2", 12, False), ("", 12, False),
        ("Problema prototípico: Bacheo inteligente y priorización urbana", 12, False),
        ("SIPA", 28, True), ("Sistema Inteligente de Priorización Asfáltica", 14, False), ("", 12, False),
        ("Contabilidad Financiera · Incidente crítico", 14, True),
        ("Contingencias por daños viales en el Estado de México", 12, False),
        ("Valor esperado de las reclamaciones y provisión NIF C-9 al 31 de diciembre", 12, False),
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
          [["UCA", "Contabilidad Financiera (LCDN3CON8)"], ["Docente", "Yesenia Biffano Rodríguez"],
           ["Grupo", "302"], ["Fecha de entrega", "13 de noviembre de 2026"]], [4.5, 7])
    doc.add_page_break()


def main():
    r = json.loads((RES / "resumen.json").read_text(encoding="utf-8"))
    serie = pd.read_csv(RES / "t1_serie_accidentes_camino.csv", index_col=0)
    grav = pd.read_csv(RES / "t2_gravedad_2023.csv", index_col=0)
    ve = pd.read_csv(RES / "t3_valor_esperado.csv")
    mun = pd.read_csv(RES / "t4_provision_municipio.csv")
    asi = pd.read_csv(RES / "t5_asiento_31dic.csv")
    sens = pd.read_csv(RES / "t6_sensibilidad.csv")

    doc = Document()
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(11)
    for s in doc.sections:
        s.left_margin = s.right_margin = Cm(2.2)
    portada(doc)

    titulo(doc, "1. El incidente crítico")
    parrafo(doc, "Cuando un bache daña un vehículo o provoca un accidente, la persona afectada puede reclamar al "
                 "Estado o al municipio la reparación del daño. En el Estado de México esto lo regula la Ley de "
                 "Responsabilidad Patrimonial para el Estado de México y Municipios: la responsabilidad es objetiva "
                 "y directa, y las indemnizaciones se pagan con cargo al presupuesto de la dependencia responsable. "
                 "Si la autoridad la niega, la persona puede demandar ante el Tribunal de Justicia Administrativa "
                 "del Estado de México (TRIJAEM).")
    parrafo(doc, "Se pide (1) analizar los reportes para estimar cuántas reclamaciones con sustento legal hay y qué "
                 "tan graves son, multiplicar los casos viables por su costo histórico y obtener con un modelo de "
                 "valor esperado la probabilidad de que se conviertan en salida de efectivo; y (2) convertir el "
                 "resultado en la provisión que exige la NIF C-9 al 31 de diciembre.")

    parrafo(doc, "SIPA trabaja en dos niveles. El nivel operativo, que decide qué bache atender primero, se "
                 "probó en la Ciudad de México porque ahí hay datos abiertos de baches georreferenciados. Este "
                 "documento corresponde al nivel financiero: estima para todo el Estado de México, la región de la "
                 "UNRC Chalco, cuánto le cuestan al erario los baches que no se atienden. No encontramos una base "
                 "pública de baches del Edomex con ubicación exacta, por eso el análisis se hace por municipio.",
           "Dos territorios. ")

    titulo(doc, "2. Fuentes de datos del Estado de México")
    tabla(doc, ["Fuente", "Qué aporta", "Uso en el modelo"], [
        ["INEGI, ATUS 1997-2023 (datos abiertos)", f"{r['accidentes_camino_2010_2023']:,} accidentes en el Edomex "
         "(2010-2023) cuya causa es «mala condición del camino», con municipio, gravedad, heridos y muertos",
         "Volumen y gravedad de los casos mayores"],
        ["INEGI, Vehículos de motor registrados 2023", f"{r['vehiculos_edomex_2023']:,} vehículos en los 125 municipios",
         "Escalar las reclamaciones menores a cada municipio"],
        ["Programa de Metepec (Milenio, 2024)", "≈ 200 reportes de daños por bache, 37 dictámenes positivos, pago "
         "de hasta $10,000", "Tasa de reclamación y probabilidad de que proceda (18.5 %)"],
        ["Ley de Responsabilidad Patrimonial del Edomex, art. 18", "Daños personales y muerte se indemnizan con la "
         "Ley Federal del Trabajo; daño moral con tope de 10,000 UMA", "Tabulador legal de lesiones y muerte"],
        ["Enunciado de la docente / iniciativa del Congreso (El Universal, 2024)", "Daños ordinarios de $3,000 a "
         "$40,000; reparación de auto de $2,000 a $20,000", "Rango del costo de los casos menores"],
        ["AMIS (Publimetro, 2024)", "Colisión promedio $15,000-$28,000; daños mayores $100,000-$150,000",
         "Costo de los accidentes con solo daños"],
        ["Tablero de bacheo de Toluca (DGOP)", "74,319 baches reparados 2025-2026 con tipo, colonia, coordenadas "
         "y medidas por folio", "Costo real de reparar en Toluca (sección 4.4)"],
        ["TRIJAEM, informe 2021", "2,909 sentencias, 81 % favorables a la ciudadanía",
         "Probabilidad de que un juicio por accidente grave prospere"],
    ], [4.5, 6.5, 5])
    parrafo(doc, "Fuentes consultadas sin cifras utilizables: el portal de sentencias del TRIJAEM (las sentencias "
                 "públicas revisadas no eran de baches), la Cuenta Pública estatal (la partida 3961 «Otros gastos "
                 "por responsabilidades» no separa los daños viales) y la Junta de Caminos (no publica estadística "
                 "de reclamaciones). Se propone pedir por SAIMEX el registro de indemnizaciones que el artículo 9 "
                 "de la ley obliga a llevar a cada dependencia.", "Nota. ")

    titulo(doc, "3. Paso 1: reclamaciones viables y su gravedad")
    titulo(doc, "3.1 Accidentes por mala condición del camino", 2)
    filas = [[int(a), int(x.get("Sólo daños", 0)), int(x.get("No fatal", 0)), int(x.get("Fatal", 0)), int(x.Total),
              f"{x['% del total de accidentes']:.2f} %"] for a, x in serie.loc[2015:].iterrows()]
    tabla(doc, ["Año", "Sólo daños", "No fatal", "Fatal", "Total", "% de los accidentes"], filas,
          [2, 2.5, 2.5, 2, 2, 3.5])
    figura(doc, "g1_accidentes_camino_edomex.png", "Figura 1. Accidentes por mala condición del camino en el "
           "Estado de México. Fuente: INEGI, ATUS.")
    g = grav
    parrafo(doc, f"En 2023 hubo {r['accidentes_camino_2023']} accidentes por mala condición del camino, con "
                 f"{int(g.heridos.sum())} heridos y {int(g.muertos.sum())} muertos; es el doble que en 2022 y la cifra "
                 "más alta desde 2010. Se usa 2023 como volumen anual por ser el dato más reciente. De los accidentes "
                 f"de 2019-2023, {r['accidentes_por_responsable_2019_2023'].get('Municipio', 0)} fueron en calles "
                 "municipales y "
                 f"{r['accidentes_por_responsable_2019_2023'].get('Estado (Junta de Caminos / SEMOV)', 0)} en "
                 "carreteras estatales: la mayor parte de la contingencia es de los ayuntamientos.")
    titulo(doc, "3.2 Daños ordinarios (llantas, rines, suspensión)", 2)
    parrafo(doc, f"Estos daños casi nunca llegan a la estadística de accidentes. Se estimaron con el único programa "
                 f"mexiquense con cifras públicas: Metepec recibió unos 200 reportes con "
                 f"{r['vehiculos_metepec_2023']:,} vehículos registrados, es decir "
                 f"{r['tasa_reclamacion_ordinaria_por_1000_veh']:.2f} reclamaciones por cada 1,000 vehículos al año. "
                 f"Aplicada a los {r['vehiculos_edomex_2023']:,} vehículos del estado da "
                 f"{r['reclamaciones_ordinarias_esperadas']:,} reclamaciones ordinarias al año, de las que procede el "
                 "18.5 % (37 de 200 en Metepec).")

    titulo(doc, "4. Modelo de valor esperado")
    parrafo(doc, "Para cada tipo de caso: casos viables = eventos × P(reclama) × P(procede); valor esperado = casos "
                 "viables × costo promedio. P(reclama) × P(procede) es la probabilidad de que un evento se convierta "
                 "en salida real de efectivo. Los costos se modelan con distribuciones triangulares (mínimo, más "
                 "probable, máximo) tomadas de las fuentes.", "Fórmula. ")
    tabla(doc, ["Tipo", "Gravedad", "Eventos/año", "P(salida)", "Casos viables", "Costo promedio", "Valor esperado"],
          [[x.tipo, x.gravedad, f"{x.eventos_anuales:,.0f}", pct(x.p_salida_efectivo), f"{x.casos_viables:,.0f}",
            m(x.costo_promedio), m(x.valor_esperado)] for x in ve.itertuples()]
          + [["Total", "", "", "", f"{ve.casos_viables.sum():,.0f}", "", m(ve.valor_esperado.sum())]],
          [3.6, 2.4, 1.8, 1.6, 1.8, 2.3, 2.5])
    parrafo(doc, f"Tabulador legal: por persona fallecida se paga lo que marca la LFT (5,000 días más 2 meses de "
                 f"funeral, con el tope de dos salarios mínimos de 2025): {m(r['costo_por_muerte_LFT'])}. Por persona "
                 f"herida, incapacidad de 30 a 180 días más gastos médicos: {m(r['costo_medio_herido'])} en "
                 "promedio.", "Lesiones y muerte. ")
    titulo(doc, "4.1 Simulación Monte Carlo", 2)
    parrafo(doc, f"Para medir la incertidumbre se simularon 20,000 años: el número de casos sigue una distribución "
                 f"de Poisson y cada monto, su triangular. El valor esperado es {mm(r['valor_esperado'])}; con 90 % "
                 f"de confianza el pago anual queda entre {mm(r['percentil_5'])} y {mm(r['percentil_95'])}. La "
                 f"probabilidad de que haya al menos un pago es {pct(r['p_al_menos_un_pago'])}.")
    figura(doc, "g2_montecarlo.png", "Figura 2. Distribución simulada del costo anual de indemnizaciones.")
    titulo(doc, "4.2 Sensibilidad", 2)
    tabla(doc, ["Escenario", "Provisión"], [[x.escenario, mm(x.provision)] for x in sens.itertuples()], [10, 4])
    titulo(doc, "4.3 Municipios con mayor provisión", 2)
    tabla(doc, ["Municipio", "Vehículos 2023", "Accidentes por camino 2019-2023", "Provisión"],
          [[x.municipio, f"{x.vehiculos:,.0f}", int(x.accidentes_camino_2019_2023), mm(x.provision)]
           for x in mun.head(10).itertuples()], [5, 3, 4, 3])
    fila_chalco = mun[mun.municipio == "Chalco"]
    if len(fila_chalco):
        c = fila_chalco.iloc[0]
        parrafo(doc, f"Chalco, sede del proyecto, ocupa el lugar {fila_chalco.index[0] + 1} de 125, con "
                     f"{int(c.accidentes_camino_2019_2023)} accidentes por mala condición del camino y una provisión "
                     f"estimada de {mm(c.provision)}.")

    tol = r["toluca"]
    ct = pd.read_csv(RES / "t7_costo_reparar_toluca_2025.csv")
    titulo(doc, "4.4 Caso Toluca: costo de reparar frente a costo de indemnizar", 2)
    parrafo(doc, f"El tablero público de bacheo de la Dirección General de Obras Públicas de Toluca registra cada "
                 f"bache reparado con su tipo, colonia, coordenadas y, por folio, su largo, ancho y profundidad. "
                 f"Descargamos los 74,319 registros (enero 2025 a noviembre 2026) y las medidas de una muestra "
                 f"aleatoria de {tol['muestra']:,} baches (área media {tol['area_media']} m²). Con las tarifas de "
                 "SIPA se estimó cuánto costó reparar los baches de 2025:")
    tabla(doc, ["Tipo", "Baches 2025", "Área media", "Costo medio", "Costo 2025"],
          [[x.tipo.capitalize(), f"{x.baches_2025:,.0f}", f"{x.area_media:.2f} m²", m(x.costo_medio),
            mm(x.costo_2025)] for x in ct.itertuples()]
          + [["Total", f"{tol['baches_2025']:,}", "", m(tol['costo_por_bache']), mm(tol['costo_reparar_2025'])]],
          [3, 2.5, 2.5, 3, 3])
    parrafo(doc, f"Con 95 % de confianza el costo de 2025 está en {mm(tol['costo_reparar_2025'])} ± "
                 f"{mm(tol['costo_reparar_ic95'])}. La provisión por reclamaciones estimada para Toluca es "
                 f"{mm(tol['provision_toluca'])}: reparar cuesta mucho más que indemnizar, pero no reparar genera "
                 "un pasivo que crece y que no se ve en los estados financieros. El argumento contable de SIPA no "
                 "es evitar reparaciones, sino ordenarlas para que el gasto en bacheo reduzca primero los baches que "
                 "más reclamaciones producen.", "Interpretación. ")
    parrafo(doc, "Las tarifas son una estimación ilustrativa del equipo; deben sustituirse por el tabulador de "
                 "precios unitarios del municipio, que también puede pedirse por SAIMEX.", "Nota. ")

    titulo(doc, "5. Paso 2: provisión NIF C-9 al 31 de diciembre")
    tabla(doc, ["Requisito NIF C-9", "Cumplimiento"], [
        ["Obligación presente por un suceso pasado", "Los daños ya ocurrieron en el ejercicio; la ley estatal hace "
         "la responsabilidad objetiva y directa"],
        ["Salida de recursos probable (> 50 %)", f"Para el grupo de reclamaciones la probabilidad de pagar es "
         f"{pct(r['p_al_menos_un_pago'])}: {r['clasificacion_nif_c9']}"],
        ["Estimación confiable", "Valor esperado con datos del INEGI, tabulador legal y costos con fuente"],
    ], [5.5, 10.5])
    tabla(doc, ["Fecha", "Cuenta", "Cargo", "Abono"],
          [[x.fecha, x.cuenta, m(x.cargo) if x.cargo else "", m(x.abono) if x.abono else ""] for x in asi.itertuples()],
          [2.5, 8.5, 2.5, 2.5])
    parrafo(doc, "El cargo al gasto reduce el resultado del ejercicio (principio de prudencia) y el abono crea un "
                 "pasivo a corto plazo en el balance al 31 de diciembre. Cuando se pague una indemnización se carga "
                 "la provisión y se abona a bancos, sin volver a afectar el resultado.")
    parrafo(doc, f"Revelación en notas: la diferencia entre el percentil 95 y el valor esperado "
                 f"({mm(r['pasivo_contingente_a_revelar'])}) se revela como pasivo contingente, porque es posible "
                 "pero no probable. También se revelan los supuestos y el número de reclamaciones en trámite.")

    titulo(doc, "6. Supuestos y limitaciones")
    vinetas(doc, [
        "P(reclama) en accidentes graves (30 % solo daños, 50 % lesiones, 60 % fatales) es un supuesto: no hay "
        "estadística pública; la sensibilidad muestra su efecto.",
        "Se supone que la tasa de Metepec (un año de programa) representa al resto del estado.",
        "ATUS solo registra accidentes en zonas urbanas y suburbanas atendidos por la autoridad; los de carreteras "
        "federales quedan fuera.",
        "Los salarios son de 2025; para el cierre de 2026 deben actualizarse con el salario mínimo vigente.",
        "No se descuenta a valor presente porque los pagos se esperan dentro del año.",
    ])
    parrafo(doc, "Los tres porcentajes no tienen que sumar 100 %, porque cada uno se aplica a un grupo distinto de "
                 "accidentes y responde a una pregunta de sí o no dentro de ese grupo. Son probabilidades "
                 "condicionales: P(reclama | fatal) = 0.60 se lee «probabilidad de reclamar, dado que el accidente "
                 "fue fatal». Lo que suma 100 % es cada renglón (reclama + no reclama). Sumarían 100 % solo si "
                 "describieran cómo se reparten todas las reclamaciones entre los tres tipos, que es otra pregunta.",
            "¿Por qué no suman 100 %? ")
    graves = ve[ve.tipo.str.startswith("Accidente")]
    tabla(doc, ["Grupo de accidentes", "Accidentes/año", "Reclama", "No reclama", "Suma", "Reclamaciones esperadas"],
          [[x.tipo.replace("Accidente: ", ""), f"{x.eventos_anuales:,.0f}", pct(x.p_reclama), pct(1 - x.p_reclama),
            "100 %", f"{x.eventos_anuales * x.p_reclama:,.1f}"] for x in graves.itertuples()],
          [3.4, 2.4, 2, 2.2, 1.6, 3.4])
    titulo(doc, "Referencias")
    vinetas(doc, r["fuentes"] + [
        "Consejo Mexicano de Normas de Información Financiera. (2024). NIF C-9 Provisiones, contingencias y "
        "compromisos. IMCP."])
    parrafo(doc, "python contabilidad/contingencias_edomex.py y después python scripts/"
                 "generar_doc_contingencias_edomex.py. Datos en datos/edomex/.", "Reproducir: ")
    doc.save(SALIDA)
    print("Documento generado:", SALIDA)


if __name__ == "__main__":
    main()
