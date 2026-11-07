"""
SIPA - Contabilidad Financiera
Incidente crítico: gestión contable de la infraestructura vial. Los baches generan
pasivos contingentes y provisiones (NIF C-9) por las reclamaciones de daños que
provocan; se compara el mantenimiento reactivo con el preventivo.

Entradas (ejecutar antes los modelos de Probabilidad y Cálculo):
  - probabilidad/resultados/t6_baches_pendientes_72h.csv  riesgo a 72 h por bache
  - probabilidad/resultados/t4_riesgo_72h_por_celda.csv   vía rápida por celda
  - probabilidad/resultados/resumen.json                  fracción atribuible al bache
  - calculo/resultados/t5_baches_detalle.csv              costo de reparar hoy y tras esperar

Modelo de reclamaciones de un bache que permanece abierto T días:

    accidentes atribuibles por día  a = −ln(1 − P72) / 3 · FA
    reclamaciones esperadas          E = a·T·p_rec  (+ ponchaduras en vía rápida)
    P(al menos una reclamación)      = 1 − e^(−E)
    provisión (mejor estimación)     = Σ E · monto promedio

Clasificación NIF C-9: probable (> 50 %) se provisiona; posible (10 % a 50 %) se
revela en notas; remota (< 10 %) no se registra ni se revela.

Además arma la contabilidad de un ejercicio de la Unidad de Bacheo: libro diario,
esquemas de mayor, balanza, estado de resultados, balance general y flujo de efectivo.

Uso (desde la carpeta del proyecto):
    python contabilidad/provisiones.py
Genera en contabilidad/resultados/: tablas CSV, gráficas, libro_contable.xlsx y resumen.json.
"""

import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

SALIDA = Path("contabilidad/resultados")
PROB = Path("probabilidad/resultados")
CALC = Path("calculo/resultados")

# Escenarios de días que un bache queda abierto
DIAS_REACTIVO = 180                                  # se repara hasta después de las lluvias
DIAS_PREVENTIVO = {"ROJO": 3, "AMARILLO": 7, "VERDE": 30}   # según el semáforo a 72 h

# Supuestos de reclamaciones (ilustrativos, se declaran en el documento)
P_RECLAMA_ACCIDENTE = 0.10       # fracción de accidentes atribuibles que termina en reclamación
MONTO_ACCIDENTE = 35_000         # pago promedio por reclamación de accidente (daños materiales y lesiones leves)
PONCHADURAS_DIA = 40_000 * 0.03 * 0.01   # vía rápida: aforo × pisan el bache × sufren daño (Probabilidad, 5.4)
P_RECLAMA_PONCHADURA = 0.02      # fracción de ponchaduras que se reclaman
MONTO_PONCHADURA = 2_500         # llanta y rin
PROFUNDIDAD_PROFUNDO = 10        # cm: a partir de aquí el bache poncha llantas

# Umbrales NIF C-9
PROBABLE, POSIBLE = 0.50, 0.10

# Datos del ejercicio de la Unidad de Bacheo (supuestos de presupuesto y activos)
PRESUPUESTO = 6_000_000
EQUIPO = 1_200_000               # camión bacheador con petrolizadora
VIDA_EQUIPO = 10
SOFTWARE = 360_000               # desarrollo e implantación de SIPA
VIDA_SOFTWARE = 3
PRECIO_MEZCLA = 1_850            # por tonelada, sin IVA (referencia para desglosar el costo en toneladas)
IVA = 0.16
FACTOR_MANO_OBRA = 0.6           # mano de obra = 60 % del material (como en Cálculo)
PAGADO_RECLAMACIONES = 0.40      # parte de la provisión que se paga en el ejercicio


# ---------------------------------------------------------------------------
# Provisiones NIF C-9
# ---------------------------------------------------------------------------

def leer_baches():
    pend = pd.read_csv(PROB / "t6_baches_pendientes_72h.csv")
    celdas = pd.read_csv(PROB / "t4_riesgo_72h_por_celda.csv", usecols=["celda_id", "via_rapida"])
    det = pd.read_csv(CALC / "t5_baches_detalle.csv", encoding="utf-8-sig",
                      usecols=["id_bache", "territorio", "costo_hoy", "extra_6m"])
    df = pend.merge(celdas, on="celda_id", how="left").merge(det, on="id_bache", how="left")
    df["via_rapida"] = df["via_rapida"].fillna(False).astype(bool)
    return df


def ponchan(df):
    return df["via_rapida"] & (df["profundidad_cm"] >= PROFUNDIDAD_PROFUNDO)


def reclamaciones(df, dias, fa, p_rec_pon=P_RECLAMA_PONCHADURA):
    """Reclamaciones esperadas y montos (accidentes, ponchaduras) si el bache queda abierto `dias` días."""
    acc_dia = -np.log(1 - df["p72_accidente"]) / 3 * fa
    e_acc = acc_dia * dias * P_RECLAMA_ACCIDENTE
    e_pon = np.where(ponchan(df), PONCHADURAS_DIA * dias * p_rec_pon, 0.0)
    return e_acc + e_pon, e_acc * MONTO_ACCIDENTE, e_pon * MONTO_PONCHADURA


def clasificar(p):
    return np.select([p > PROBABLE, p >= POSIBLE], ["PROBABLE", "POSIBLE"], "REMOTA")


def dias_preventivo(df):
    """Días abiertos en el esquema preventivo: según el semáforo; si poncha llantas en vía rápida, 72 h."""
    return np.where(ponchan(df), 3, df["semaforo_72h"].map(DIAS_PREVENTIVO))


def provisiones(df, fa):
    out = df.copy()
    for esc, dias in [("reactivo", DIAS_REACTIVO), ("preventivo", dias_preventivo(out))]:
        e, m_acc, m_pon = reclamaciones(out, dias, fa)
        out[f"rec_esperadas_{esc}"] = e
        out[f"p_reclamacion_{esc}"] = 1 - np.exp(-e)
        out[f"monto_accidentes_{esc}"] = m_acc
        out[f"monto_ponchaduras_{esc}"] = m_pon
        out[f"monto_esperado_{esc}"] = m_acc + m_pon
        out[f"nif_c9_{esc}"] = clasificar(out[f"p_reclamacion_{esc}"])
    out["costo_reparar_reactivo"] = out["costo_hoy"] + out["extra_6m"]
    out["costo_reparar_preventivo"] = out["costo_hoy"]
    return out


def sensibilidad(b, fa):
    """Ahorro del esquema preventivo al variar el supuesto más incierto (reclamación de ponchaduras)."""
    filas = []
    for nombre, p in [("Sin ponchaduras", 0.0), ("Bajo (0.5 %)", 0.005), ("Base (2 %)", P_RECLAMA_PONCHADURA),
                      ("Alto (5 %)", 0.05)]:
        _, a_r, p_r = reclamaciones(b, DIAS_REACTIVO, fa, p)
        _, a_p, p_p = reclamaciones(b, dias_preventivo(b), fa, p)
        reactivo = b["costo_reparar_reactivo"].sum() + a_r.sum() + p_r.sum()
        preventivo = b["costo_reparar_preventivo"].sum() + a_p.sum() + p_p.sum()
        filas.append(dict(supuesto=nombre, p_reclama_ponchadura=p, costo_total_reactivo=reactivo,
                          costo_total_preventivo=preventivo, ahorro=reactivo - preventivo))
    return pd.DataFrame(filas)


def resumen_escenarios(b):
    filas = []
    for esc in ["preventivo", "reactivo"]:
        e_total = b[f"rec_esperadas_{esc}"].sum()
        clas = b[f"nif_c9_{esc}"]
        filas.append(dict(
            escenario=esc,
            costo_reparar=b[f"costo_reparar_{esc}"].sum(),
            reclamaciones_esperadas=e_total,
            p_al_menos_una=1 - math.exp(-e_total),
            provision_total=b[f"monto_esperado_{esc}"].sum(),
            provision_accidentes=b[f"monto_accidentes_{esc}"].sum(),
            provision_ponchaduras=b[f"monto_ponchaduras_{esc}"].sum(),
            provision_individual=b.loc[clas == "PROBABLE", f"monto_esperado_{esc}"].sum(),
            revelacion_individual=b.loc[clas == "POSIBLE", f"monto_esperado_{esc}"].sum(),
            baches_probable=int((clas == "PROBABLE").sum()),
            baches_posible=int((clas == "POSIBLE").sum()),
            baches_remota=int((clas == "REMOTA").sum()),
        ))
    t = pd.DataFrame(filas)
    t["costo_total"] = t["costo_reparar"] + t["provision_total"]
    return t


# ---------------------------------------------------------------------------
# Contabilidad del ejercicio
# ---------------------------------------------------------------------------

NATURALEZA = {  # D = deudora, A = acreedora; grupo para los estados financieros
    "Bancos": ("D", "Activo circulante"),
    "Inventario de mezcla asfáltica": ("D", "Activo circulante"),
    "Equipo de bacheo": ("D", "Activo no circulante"),
    "Depreciación acumulada de equipo": ("A", "Activo no circulante"),
    "Software SIPA (intangible)": ("D", "Activo no circulante"),
    "Amortización acumulada de software": ("A", "Activo no circulante"),
    "Acreedores diversos (contratista)": ("A", "Pasivo a corto plazo"),
    "Provisión para reclamaciones por daños": ("A", "Pasivo a corto plazo"),
    "Patrimonio inicial": ("A", "Patrimonio"),
    "Ingresos por asignación presupuestal": ("A", "Ingresos"),
    "Costo de materiales de bacheo": ("D", "Costo de operación"),
    "Costo de mano de obra de bacheo": ("D", "Costo de operación"),
    "Gasto por provisión de reclamaciones": ("D", "Gastos de operación"),
    "Depreciación y amortización": ("D", "Gastos de operación"),
}


def asientos(esc):
    """Operaciones del ejercicio (escenario preventivo). Cada asiento cuadra cargos y abonos."""
    material_sin_iva = esc["costo_reparar"] / (1 + FACTOR_MANO_OBRA)
    toneladas = material_sin_iva / PRECIO_MEZCLA
    compra = round(material_sin_iva * 1.10 * (1 + IVA), 2)       # se compra 10 % de reserva; IVA no acreditable
    consumo = round(material_sin_iva * (1 + IVA), 2)
    mano_obra = round(material_sin_iva * FACTOR_MANO_OBRA * (1 + IVA), 2)
    mano_obra_pagada = round(mano_obra * 0.85, 2)
    provision = round(esc["provision_total"], 2)
    pagos_rec = round(provision * PAGADO_RECLAMACIONES, 2)
    dep = EQUIPO / VIDA_EQUIPO
    amo = SOFTWARE / VIDA_SOFTWARE

    A = [
        ("01/01", "Aportación inicial de patrimonio a la Unidad de Bacheo",
         [("Bancos", 500_000, 0), ("Patrimonio inicial", 0, 500_000)]),
        ("15/01", "Se recibe la asignación presupuestal anual del programa de bacheo",
         [("Bancos", PRESUPUESTO, 0), ("Ingresos por asignación presupuestal", 0, PRESUPUESTO)]),
        ("01/02", "Compra de camión bacheador con petrolizadora, pago por transferencia",
         [("Equipo de bacheo", EQUIPO, 0), ("Bancos", 0, EQUIPO)]),
        ("01/02", "Desarrollo e implantación del sistema SIPA",
         [("Software SIPA (intangible)", SOFTWARE, 0), ("Bancos", 0, SOFTWARE)]),
        ("10/02", f"Compra de {toneladas * 1.10:,.0f} t de mezcla asfáltica (IVA incluido, no acreditable)",
         [("Inventario de mezcla asfáltica", compra, 0), ("Bancos", 0, compra)]),
        ("31/03", "Consumo de mezcla en la reparación de los baches pendientes",
         [("Costo de materiales de bacheo", consumo, 0), ("Inventario de mezcla asfáltica", 0, consumo)]),
        ("31/03", "Mano de obra del contratista; queda 15 % por pagar",
         [("Costo de mano de obra de bacheo", mano_obra, 0), ("Bancos", 0, mano_obra_pagada),
          ("Acreedores diversos (contratista)", 0, round(mano_obra - mano_obra_pagada, 2))]),
        ("30/06", "Reconocimiento de la provisión por reclamaciones de daños (NIF C-9)",
         [("Gasto por provisión de reclamaciones", provision, 0),
          ("Provisión para reclamaciones por daños", 0, provision)]),
        ("30/09", "Pago de reclamaciones procedentes contra la provisión",
         [("Provisión para reclamaciones por daños", pagos_rec, 0), ("Bancos", 0, pagos_rec)]),
        ("31/12", "Depreciación anual del equipo (10 años, línea recta) y amortización de SIPA (3 años)",
         [("Depreciación y amortización", dep + amo, 0), ("Depreciación acumulada de equipo", 0, dep),
          ("Amortización acumulada de software", 0, amo)]),
    ]
    filas = []
    for i, (fecha, concepto, movs) in enumerate(A, start=1):
        cargos = round(sum(c for _, c, _ in movs), 2)
        abonos = round(sum(a for _, _, a in movs), 2)
        assert abs(cargos - abonos) < 0.01, f"El asiento {i} no cuadra"
        for cuenta, c, a in movs:
            filas.append(dict(asiento=i, fecha=fecha, cuenta=cuenta, cargo=round(c, 2), abono=round(a, 2),
                              concepto=concepto))
    detalle = dict(toneladas=toneladas, compra=compra, consumo=consumo, mano_obra=mano_obra,
                   mano_obra_pagada=mano_obra_pagada, provision=provision, pagos_rec=pagos_rec,
                   dep=dep, amo=amo)
    return pd.DataFrame(filas), detalle


def mayor(diario):
    """Esquemas de mayor: movimientos por cuenta con su saldo acumulado y referencia al asiento."""
    partes = []
    for cuenta in [c for c in NATURALEZA if c in set(diario["cuenta"])]:
        m = diario[diario["cuenta"] == cuenta][["cuenta", "asiento", "fecha", "cargo", "abono"]].copy()
        signo = 1 if NATURALEZA[cuenta][0] == "D" else -1
        m["saldo"] = (signo * (m["cargo"] - m["abono"])).cumsum().round(2)
        partes.append(m)
    return pd.concat(partes, ignore_index=True)


def mayor_y_balanza(diario):
    g = diario.groupby("cuenta")[["cargo", "abono"]].sum()
    g["naturaleza"] = [NATURALEZA[c][0] for c in g.index]
    g["grupo"] = [NATURALEZA[c][1] for c in g.index]
    g["saldo_deudor"] = (g["cargo"] - g["abono"]).clip(lower=0)
    g["saldo_acreedor"] = (g["abono"] - g["cargo"]).clip(lower=0)
    orden = list(NATURALEZA)
    g = g.reindex([c for c in orden if c in g.index])
    assert abs(g["cargo"].sum() - g["abono"].sum()) < 0.01
    assert abs(g["saldo_deudor"].sum() - g["saldo_acreedor"].sum()) < 0.01
    return g.round(2)


def estados(bal, d):
    s = lambda c: bal.loc[c, "saldo_deudor"] - bal.loc[c, "saldo_acreedor"] if c in bal.index else 0.0

    ingresos = -s("Ingresos por asignación presupuestal")
    costo_op = s("Costo de materiales de bacheo") + s("Costo de mano de obra de bacheo")
    margen = ingresos - costo_op
    gasto_prov = s("Gasto por provisión de reclamaciones")
    dep = s("Depreciación y amortización")
    resultado = margen - gasto_prov - dep
    er = [
        ("Ingresos por asignación presupuestal", ingresos),
        ("(−) Costo de materiales de bacheo", -s("Costo de materiales de bacheo")),
        ("(−) Costo de mano de obra de bacheo", -s("Costo de mano de obra de bacheo")),
        ("= Resultado bruto de operación", margen),
        ("(−) Gasto por provisión de reclamaciones (NIF C-9)", -gasto_prov),
        ("(−) Depreciación y amortización", -dep),
        ("= Resultado del ejercicio (ahorro de la gestión)", resultado),
    ]

    bancos = s("Bancos")
    inventario = s("Inventario de mezcla asfáltica")
    equipo_neto = s("Equipo de bacheo") + s("Depreciación acumulada de equipo")
    software_neto = s("Software SIPA (intangible)") + s("Amortización acumulada de software")
    acreedores = -s("Acreedores diversos (contratista)")
    provision = -s("Provisión para reclamaciones por daños")
    patrimonio = -s("Patrimonio inicial")
    activo = bancos + inventario + equipo_neto + software_neto
    pasivo = acreedores + provision
    capital = patrimonio + resultado
    assert abs(activo - (pasivo + capital)) < 0.01, "El balance no cuadra"
    bg = [
        ("ACTIVO", None),
        ("Bancos", bancos), ("Inventario de mezcla asfáltica", inventario),
        ("Total activo circulante", bancos + inventario),
        ("Equipo de bacheo, neto de depreciación", equipo_neto),
        ("Software SIPA, neto de amortización", software_neto),
        ("Total activo no circulante", equipo_neto + software_neto),
        ("TOTAL ACTIVO", activo),
        ("PASIVO", None),
        ("Acreedores diversos (contratista)", acreedores),
        ("Provisión para reclamaciones por daños (NIF C-9)", provision),
        ("TOTAL PASIVO", pasivo),
        ("PATRIMONIO", None),
        ("Patrimonio inicial", patrimonio), ("Resultado del ejercicio", resultado),
        ("TOTAL PATRIMONIO", capital),
        ("TOTAL PASIVO + PATRIMONIO", pasivo + capital),
    ]

    # Flujo de efectivo, método indirecto
    aumento_inv = inventario
    op = resultado + dep + provision + acreedores - aumento_inv
    inv = -(EQUIPO + SOFTWARE)
    fin = patrimonio
    efectivo_inicial = 0.0
    efectivo_final = efectivo_inicial + op + inv + fin
    assert abs(efectivo_final - bancos) < 0.01, "El flujo de efectivo no concilia con Bancos"
    fe = [
        ("ACTIVIDADES DE OPERACIÓN", None),
        ("Resultado del ejercicio", resultado),
        ("(+) Depreciación y amortización (no son salida de efectivo)", dep),
        ("(+) Aumento de la provisión para reclamaciones", provision),
        ("(+) Aumento de acreedores diversos", acreedores),
        ("(−) Aumento del inventario de mezcla asfáltica", -aumento_inv),
        ("Flujo neto de operación", op),
        ("ACTIVIDADES DE INVERSIÓN", None),
        ("(−) Compra de equipo de bacheo", -EQUIPO),
        ("(−) Desarrollo del software SIPA", -SOFTWARE),
        ("Flujo neto de inversión", inv),
        ("ACTIVIDADES DE FINANCIAMIENTO", None),
        ("(+) Patrimonio inicial aportado", fin),
        ("Flujo neto de financiamiento", fin),
        ("Aumento neto de efectivo", op + inv + fin),
        ("Efectivo al inicio del ejercicio", efectivo_inicial),
        ("Efectivo al final del ejercicio (= Bancos en el balance)", efectivo_final),
    ]
    razones = dict(
        liquidez=(bancos + inventario) / pasivo,
        prueba_acida=bancos / pasivo,
        endeudamiento=pasivo / activo,
        provision_sobre_pasivo=provision / pasivo,
        provision_sobre_ingresos=gasto_prov / ingresos,
    )
    a_df = lambda filas, col: pd.DataFrame(filas, columns=["concepto", col])
    return a_df(er, "importe"), a_df(bg, "importe"), a_df(fe, "importe"), razones, resultado


# ---------------------------------------------------------------------------
# Gráficas
# ---------------------------------------------------------------------------

def graficas(esc, b):
    plt.rcParams.update({"font.size": 10})
    fig, ax = plt.subplots(figsize=(7, 4))
    x = np.arange(2)
    rep = esc["costo_reparar"] / 1e6
    pro = esc["provision_total"] / 1e6
    ax.bar(x, rep, 0.5, label="Costo de reparar", color="#546e7a")
    ax.bar(x, pro, 0.5, bottom=rep, label="Provisión por reclamaciones", color="#c62828")
    for i in range(2):
        ax.text(x[i], rep[i] + pro[i] + 0.05, f"${rep[i] + pro[i]:.2f} M", ha="center")
    ax.set_xticks(x, ["Preventivo\n(según semáforo)", f"Reactivo\n({DIAS_REACTIVO} días)"])
    ax.set_ylabel("Millones de pesos")
    ax.set_title("Costo total para el erario de los baches pendientes")
    ax.legend()
    fig.tight_layout(); fig.savefig(SALIDA / "g1_reactivo_vs_preventivo.png", dpi=150); plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4))
    orden = ["PROBABLE", "POSIBLE", "REMOTA"]
    colores = ["#c62828", "#f9a825", "#2e7d32"]
    w = 0.38
    for j, e in enumerate(["preventivo", "reactivo"]):
        cnt = b[f"nif_c9_{e}"].value_counts().reindex(orden, fill_value=0)
        ax.bar(np.arange(3) + (j - 0.5) * w, cnt.values, w, color=colores, alpha=0.55 if j == 0 else 1,
               edgecolor="k", label=e.capitalize())
        for i, v in enumerate(cnt.values):
            ax.text(i + (j - 0.5) * w, v + 10, str(v), ha="center", fontsize=9)
    ax.set_xticks(range(3), ["Probable\n(provisión)", "Posible\n(revelación)", "Remota\n(nada)"])
    ax.set_ylabel("Baches")
    ax.set_title("Clasificación NIF C-9 de cada bache (claro: preventivo, oscuro: reactivo)")
    fig.tight_layout(); fig.savefig(SALIDA / "g2_clasificacion_nif_c9.png", dpi=150); plt.close(fig)


# ---------------------------------------------------------------------------
# Principal
# ---------------------------------------------------------------------------

def main():
    SALIDA.mkdir(parents=True, exist_ok=True)
    rp = json.loads((PROB / "resumen.json").read_text(encoding="utf-8"))
    fa = rp["incidente"]["fraccion_atribuible"]

    b = provisiones(leer_baches(), fa)
    esc = resumen_escenarios(b)
    prev = esc.set_index("escenario").loc["preventivo"]
    react = esc.set_index("escenario").loc["reactivo"]

    diario, det = asientos(prev)
    bal = mayor_y_balanza(diario)
    er, bg, fe, razones, resultado = estados(bal, det)

    # Mismo ejercicio en escenario reactivo, para comparar
    diario_r, det_r = asientos(react)
    er_r, bg_r, fe_r, razones_r, resultado_r = estados(mayor_y_balanza(diario_r), det_r)

    graficas(esc, b)
    sens = sensibilidad(b, fa)
    sens.to_csv(SALIDA / "t9_sensibilidad.csv", index=False)

    por_terr = (b.groupby("territorio")
                 .agg(baches=("id_bache", "size"), provision_preventivo=("monto_esperado_preventivo", "sum"),
                      provision_reactivo=("monto_esperado_reactivo", "sum"))
                 .sort_values("provision_reactivo", ascending=False))

    cols = ["id_bache", "territorio", "celda_id", "via_rapida", "profundidad_cm", "semaforo_72h", "p72_accidente",
            "costo_hoy", "rec_esperadas_preventivo", "p_reclamacion_preventivo", "monto_esperado_preventivo",
            "nif_c9_preventivo", "rec_esperadas_reactivo", "p_reclamacion_reactivo", "monto_esperado_reactivo",
            "nif_c9_reactivo"]
    b[cols].to_csv(SALIDA / "t1_provision_por_bache.csv", index=False)
    esc.to_csv(SALIDA / "t2_escenarios.csv", index=False)
    por_terr.to_csv(SALIDA / "t3_provision_por_territorio.csv")
    diario.to_csv(SALIDA / "t4_libro_diario.csv", index=False)
    bal.to_csv(SALIDA / "t5_balanza.csv")
    er.to_csv(SALIDA / "t6_estado_resultados.csv", index=False)
    bg.to_csv(SALIDA / "t7_balance_general.csv", index=False)
    fe.to_csv(SALIDA / "t8_flujo_efectivo.csv", index=False)

    # Libro contable en Excel (herramienta tecnológica que pide la competencia de la UCA)
    with pd.ExcelWriter(SALIDA / "libro_contable.xlsx") as xw:
        diario.to_excel(xw, sheet_name="Libro diario", index=False)
        mayor(diario).to_excel(xw, sheet_name="Esquemas de mayor", index=False)
        bal.to_excel(xw, sheet_name="Balanza")
        er.to_excel(xw, sheet_name="Estado de resultados", index=False)
        bg.to_excel(xw, sheet_name="Balance general", index=False)
        fe.to_excel(xw, sheet_name="Flujo de efectivo", index=False)
        esc.to_excel(xw, sheet_name="Escenarios NIF C-9", index=False)
        sens.to_excel(xw, sheet_name="Sensibilidad", index=False)
        b[cols].to_excel(xw, sheet_name="Provisión por bache", index=False)

    resumen = dict(
        fraccion_atribuible=fa,
        supuestos=dict(dias_reactivo=DIAS_REACTIVO, dias_preventivo=DIAS_PREVENTIVO,
                       p_reclama_accidente=P_RECLAMA_ACCIDENTE, monto_accidente=MONTO_ACCIDENTE,
                       ponchaduras_dia=PONCHADURAS_DIA, p_reclama_ponchadura=P_RECLAMA_PONCHADURA,
                       monto_ponchadura=MONTO_PONCHADURA, presupuesto=PRESUPUESTO, equipo=EQUIPO,
                       software=SOFTWARE, iva=IVA),
        baches=int(len(b)),
        baches_ponchan=int(ponchan(b).sum()),
        sensibilidad=sens.to_dict(orient="records"),
        escenarios=esc.to_dict(orient="records"),
        ahorro_preventivo=float(react["costo_total"] - prev["costo_total"]),
        asientos=det, asientos_reactivo=det_r,
        resultado=resultado, resultado_reactivo=resultado_r,
        razones=razones, razones_reactivo=razones_r,
        estado_resultados_reactivo=er_r.to_dict(orient="records"),
        balance_reactivo=bg_r.to_dict(orient="records"),
    )
    with open(SALIDA / "resumen.json", "w", encoding="utf-8") as fh:
        json.dump(resumen, fh, ensure_ascii=False, indent=2,
                  default=lambda o: o.item() if hasattr(o, "item") else str(o))
    print(esc.T.to_string())
    print(sens.to_string())
    print(json.dumps({k: resumen[k] for k in ["baches_ponchan", "ahorro_preventivo", "resultado",
                                              "resultado_reactivo", "razones"]}, indent=1,
                     default=lambda o: o.item() if hasattr(o, "item") else str(o)))


if __name__ == "__main__":
    main()
