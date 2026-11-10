"""
SIPA - Incidente crítico de Contabilidad: contingencias por daños viales en el Estado de México.

Paso 1 (19-11-2026): reclamaciones con sustento legal, gravedad, costo histórico/legal,
valor esperado y probabilidad de salida de efectivo.
Paso 2: provisión NIF C-9 al 31 de diciembre (asiento de gasto y pasivo).

Datos reales descargados (datos/edomex/raw):
  - INEGI, Accidentes de Tránsito Terrestre en Zonas Urbanas y Suburbanas (ATUS) 1997-2023.
    Se usan los accidentes del Edomex cuya causa es «Mala condición del camino».
  - INEGI, Vehículos de Motor Registrados en Circulación (VMRC) 1980-2023, por municipio.
  - Ley de Responsabilidad Patrimonial para el Estado de México y Municipios (art. 18):
    daños personales y muerte se indemnizan con la Ley Federal del Trabajo.
Parámetros con fuente (ver FUENTES): programa de Metepec (200 reportes, 37 procedentes,
hasta $10,000), rango de la docente ($3,000-$40,000), AMIS (costos de colisión),
TRIJAEM (81 % de sentencias favorables en 2021), salario mínimo 2025.

Uso:  python contabilidad/contingencias_edomex.py
"""

import json
from pathlib import Path
import zipfile

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
RAW = RAIZ / "datos/edomex/raw"
ATUS = RAIZ / "datos/edomex/atus_edomex_2010_2023.csv"
RES = RAIZ / "contabilidad/resultados_edomex"
RES.mkdir(exist_ok=True)
rng = np.random.default_rng(2026)

# ---------------------------------------------------------------- parámetros con fuente
SM_2025 = 278.80                 # salario mínimo general 2025 (CONASAMI)
SALARIO_TOPE = 2 * SM_2025       # LFT art. 486: tope de salario para indemnizaciones
UMA_2025 = 113.14                # INEGI
METEPEC = dict(reportes=200, procedentes=37, tope=10_000, clave="054")   # Milenio, 2024
P_PROCEDE_ORD = METEPEC["procedentes"] / METEPEC["reportes"]             # 0.185
P_SENTENCIA_FAVORABLE = 0.81     # TRIJAEM, informe 2021 (2,909 sentencias)

# Monto por evento: distribución triangular (mín, moda, máx) en pesos
COSTO = {
    # llanta/rin/suspensión: rango de la docente; moda = tope de Metepec
    "Ordinario (llanta, rin, suspensión)": (3_000, 10_000, 40_000),
    # accidente con solo daños: AMIS colisión promedio 15-28 mil, daños mayores hasta 150 mil
    "Sólo daños": (15_000, 28_000, 150_000),
}
# Por persona herida (LFT): incapacidad temporal 30-180 días de salario tope + gastos médicos
HERIDO = (30 * SALARIO_TOPE + 10_000, 90 * SALARIO_TOPE + 30_000, 180 * SALARIO_TOPE + 120_000)
# Por persona fallecida: LFT art. 502 (5,000 días) + art. 500 (2 meses de funeral)
MUERTO = 5_000 * SALARIO_TOPE + 60 * SALARIO_TOPE

# Supuestos (no hay dato público): fracción de afectados que reclama formalmente
P_RECLAMA = {"Sólo daños": 0.30, "No fatal": 0.50, "Fatal": 0.60}
N_SIM = 20_000

FUENTES = [
    "INEGI (2024). Accidentes de tránsito terrestre en zonas urbanas y suburbanas (ATUS) 1997-2023 [conjunto de datos]. https://www.inegi.org.mx/programas/accidentes/",
    "INEGI (2024). Vehículos de motor registrados en circulación 1980-2023 [conjunto de datos]. https://www.inegi.org.mx/programas/vehiculosmotor/",
    "Legislatura del Estado de México (2017, reforma 2023). Ley de Responsabilidad Patrimonial para el Estado de México y Municipios, art. 18. https://legislacion.edomex.gob.mx/",
    "Milenio (8 de octubre de 2024). Te decimos qué municipio del Edomex pagará daños al caer en un bache. https://www.milenio.com/politica/comunidad/te-decimos-que-municipio-del-edomex-pagara-danos-al-caer-en-un-bache",
    "El Universal Edomex (2024). Edomex: ¿te dañó un bache? Podrías recibir una indemnización. https://www.eluniversaledomex.com.mx/gobierno/edomex-te-dano-un-bache-podrias-recibir-una-indemnizacion/",
    "Publimetro (8 de febrero de 2024). Choque de auto: cuáles son los estados con más accidentes en México (cifras AMIS). https://www.publimetro.com.mx/noticias/2024/02/08/choque-de-auto-cuales-son-los-estados-con-mas-accidentes-en-mexico/",
    "El Día Oficial (enero de 2022). Magistrada Arlen Siu Jaime Merlos presentó Informe Anual de Actividades 2021 del TRIJAEM. https://eldiaoficial.com/2022/01/magistrada-arlen-siu-jaime-merlos-presento-informe-anual-de-actividades-2021-del-trijaem/",
    "Ley Federal del Trabajo, arts. 486, 491, 500 y 502.",
]


def tri_media(a, c, b):
    return (a + c + b) / 3


# ---------------------------------------------------------------- 1. datos
def cargar():
    e = pd.read_csv(ATUS, dtype=str)
    num = [c for c in e.columns if c.endswith(("MUERTO", "HERIDO"))]
    e[num] = e[num].apply(pd.to_numeric, errors="coerce").fillna(0)
    e["muertos"] = e[[c for c in num if c.endswith("MUERTO")]].sum(axis=1)
    e["heridos"] = e[[c for c in num if c.endswith("HERIDO")]].sum(axis=1)
    e["ANIO"] = e.ANIO.astype(int)
    e["MUN"] = e.ID_MUNICIPIO.str.zfill(3)
    e["responsable"] = np.where(e.SUBURBANA.str.contains("carretera estatal", na=False),
                                "Estado (Junta de Caminos / SEMOV)", "Municipio")
    camino = e[e.CAUSAACCI.str.startswith("Mala")].copy()

    z = zipfile.ZipFile(RAW / "vmrc.zip")
    v = pd.read_csv(z.open("conjunto_de_datos/vmrc_anual_tr_cifra_2023.csv"),
                    dtype=str, index_col=False, encoding="latin1")
    v = v.apply(lambda s: s.str.strip())
    v = v[v.ID_ENTIDAD.str.zfill(2) == "15"].copy()
    cols = [c for c in v.columns if c.startswith(("AUTO", "CAM_", "CYC", "MOTO"))]
    v["vehiculos"] = v[cols].apply(pd.to_numeric).sum(axis=1)
    v["MUN"] = v.ID_MUNICIPIO.str.zfill(3)
    v = v.groupby("MUN", as_index=False).vehiculos.sum()

    cat = pd.read_csv(z.open("catalogos/tc_municipio.csv"), dtype=str, encoding="utf-8-sig")
    cat = cat.apply(lambda s: s.str.strip())
    cat.columns = [c.strip().upper() for c in cat.columns]
    cat = cat[cat.ID_ENTIDAD.str.zfill(2) == "15"]
    ncol = [c for c in cat.columns if "NOM" in c][0]
    nombres = dict(zip(cat.ID_MUNICIPIO.str.zfill(3), cat[ncol]))
    return e, camino, v, nombres


# ---------------------------------------------------------------- 2. volumen y gravedad
def volumen(e, camino, v):
    serie = pd.crosstab(camino.ANIO, camino.CLASACC)
    serie["Total"] = serie.sum(axis=1)
    serie["% del total de accidentes"] = (serie.Total / e.groupby("ANIO").size() * 100).round(2)
    ult = camino[camino.ANIO == 2023]
    graves = pd.DataFrame({
        "accidentes": ult.groupby("CLASACC").size(),
        "heridos": ult.groupby("CLASACC").heridos.sum(),
        "muertos": ult.groupby("CLASACC").muertos.sum(),
    }).reindex(["Sólo daños", "No fatal", "Fatal"]).fillna(0)

    veh_metepec = v.loc[v.MUN == METEPEC["clave"], "vehiculos"].iloc[0]
    tasa = METEPEC["reportes"] / veh_metepec          # reclamaciones ordinarias por vehículo-año
    v = v.assign(reclam_ordinarias=v.vehiculos * tasa)
    return serie, graves, v, tasa, veh_metepec


# ---------------------------------------------------------------- 3. valor esperado
def valor_esperado(graves, v):
    filas = []
    n_ord = v.reclam_ordinarias.sum()
    c = tri_media(*COSTO["Ordinario (llanta, rin, suspensión)"])
    filas.append(["Ordinario (llanta, rin, suspensión)", "Daño material menor", n_ord, 1.0,
                  P_PROCEDE_ORD, c])
    for clase, sev in [("Sólo daños", "Daño material mayor"), ("No fatal", "Lesiones"),
                       ("Fatal", "Muerte")]:
        g = graves.loc[clase]
        if clase == "Sólo daños":
            costo = tri_media(*COSTO["Sólo daños"])
        elif clase == "No fatal":
            costo = tri_media(*COSTO["Sólo daños"]) + g.heridos / max(g.accidentes, 1) * tri_media(*HERIDO)
        else:
            costo = (tri_media(*COSTO["Sólo daños"]) + g.heridos / max(g.accidentes, 1) * tri_media(*HERIDO)
                     + g.muertos / max(g.accidentes, 1) * MUERTO)
        filas.append([f"Accidente: {clase}", sev, g.accidentes, P_RECLAMA[clase],
                      P_SENTENCIA_FAVORABLE, costo])
    t = pd.DataFrame(filas, columns=["tipo", "gravedad", "eventos_anuales", "p_reclama",
                                     "p_procede", "costo_promedio"])
    t["p_salida_efectivo"] = t.p_reclama * t.p_procede
    t["casos_viables"] = t.eventos_anuales * t.p_salida_efectivo
    t["valor_esperado"] = t.casos_viables * t.costo_promedio
    return t


# ---------------------------------------------------------------- 4. Monte Carlo
def simulacion(t, graves):
    tot = np.zeros(N_SIM)
    a, c, b = COSTO["Ordinario (llanta, rin, suspensión)"]
    n = rng.poisson(t.casos_viables.iloc[0], N_SIM)
    tot += np.array([rng.triangular(a, c, b, k).sum() for k in n])
    for i, clase in zip(range(1, 4), ["Sólo daños", "No fatal", "Fatal"]):
        g = graves.loc[clase]
        n = rng.poisson(t.casos_viables.iloc[i], N_SIM)
        for j, k in enumerate(n):
            if k == 0:
                continue
            monto = rng.triangular(*COSTO["Sólo daños"], k).sum()
            her = rng.poisson(g.heridos / max(g.accidentes, 1), k).sum()
            monto += rng.triangular(*HERIDO, her).sum() if her else 0
            if clase == "Fatal":
                monto += rng.poisson(g.muertos / max(g.accidentes, 1), k).sum() * MUERTO
            tot[j] += monto
    return tot


# ---------------------------------------------------------------- 5. NIF C-9 y asiento
def nif_c9(ve, sim):
    p_salida = (sim > 0).mean()
    p95 = np.percentile(sim, 95)
    clas = "Probable (> 50 %): se reconoce provisión" if p_salida > 0.5 else "Posible: solo revelar"
    asiento = pd.DataFrame([
        ["31/12/2026", "5.5.9 Gasto por responsabilidad patrimonial (daños viales)", round(ve, 2), 0],
        ["31/12/2026", "2.1.7 Provisión para reclamaciones por daños viales (pasivo a corto plazo)", 0, round(ve, 2)],
    ], columns=["fecha", "cuenta", "cargo", "abono"])
    revelar = p95 - ve
    return p_salida, p95, clas, asiento, revelar


def graficas(serie, sim, ve, p95, mun):
    fig, ax = plt.subplots(figsize=(8, 4))
    serie[["Sólo daños", "No fatal", "Fatal"]].loc[2015:].plot(kind="bar", stacked=True, ax=ax,
                                                              color=["#9bb7d4", "#e3a857", "#c0392b"])
    ax.set_title("Accidentes por mala condición del camino, Edomex (INEGI ATUS)")
    ax.set_xlabel(""); ax.set_ylabel("Accidentes")
    fig.tight_layout(); fig.savefig(RES / "g1_accidentes_camino_edomex.png", dpi=150); plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(sim / 1e6, bins=60, color="#9bb7d4")
    ax.axvline(ve / 1e6, color="#1f4e79", label=f"Valor esperado ${ve/1e6:,.1f} M")
    ax.axvline(p95 / 1e6, color="#c0392b", ls="--", label=f"Percentil 95 ${p95/1e6:,.1f} M")
    ax.set_xlabel("Salida de efectivo anual (millones de pesos)"); ax.set_ylabel("Simulaciones")
    ax.set_title("Distribución del costo anual de indemnizaciones (Monte Carlo)")
    ax.legend(); fig.tight_layout(); fig.savefig(RES / "g2_montecarlo.png", dpi=150); plt.close(fig)

    top = mun.head(15).iloc[::-1]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh(top.municipio, top.provision / 1e6, color="#1f4e79")
    ax.set_xlabel("Provisión (millones de pesos)")
    ax.set_title("Municipios con mayor provisión estimada")
    fig.tight_layout(); fig.savefig(RES / "g3_municipios.png", dpi=150); plt.close(fig)


def main():
    e, camino, v, nombres = cargar()
    serie, graves, v, tasa, veh_metepec = volumen(e, camino, v)
    t = valor_esperado(graves, v)
    ve = t.valor_esperado.sum()
    sim = simulacion(t, graves)
    p_salida, p95, clas, asiento, revelar = nif_c9(ve, sim)

    # reparto por municipio: ordinarios por vehículos; graves por accidentes 2019-2023
    rec = camino[camino.ANIO >= 2019]
    peso_g = rec.groupby("MUN").size() / len(rec)
    ve_ord, ve_g = t.valor_esperado.iloc[0], t.valor_esperado.iloc[1:].sum()
    mun = v.set_index("MUN")
    mun["provision"] = mun.reclam_ordinarias / mun.reclam_ordinarias.sum() * ve_ord \
        + peso_g.reindex(mun.index).fillna(0) * ve_g
    mun["accidentes_camino_2019_2023"] = rec.groupby("MUN").size().reindex(mun.index).fillna(0).astype(int)
    mun["municipio"] = [nombres.get(k, k) for k in mun.index]
    mun = mun.sort_values("provision", ascending=False).reset_index()

    resp = rec.groupby("responsable").size()

    # sensibilidad
    sens = []
    for f in [0.5, 1, 1.5]:
        tt = t.copy(); tt["p_reclama"] = (tt.p_reclama * f).clip(upper=1); tt.loc[0, "p_reclama"] = 1
        tt["valor_esperado"] = tt.eventos_anuales * tt.p_reclama * tt.p_procede * tt.costo_promedio
        sens.append([f"P(reclama) × {f}", tt.valor_esperado.sum()])
    for nombre, lam in [("Volumen 2023", 1), ("Volumen promedio 2019-2023",
                        len(rec) / 5 / len(camino[camino.ANIO == 2023]))]:
        sens.append([nombre + " (accidentes graves)", ve_ord + ve_g * lam])
    sens = pd.DataFrame(sens, columns=["escenario", "provision"])

    serie.to_csv(RES / "t1_serie_accidentes_camino.csv")
    graves.to_csv(RES / "t2_gravedad_2023.csv")
    t.to_csv(RES / "t3_valor_esperado.csv", index=False)
    mun.to_csv(RES / "t4_provision_municipio.csv", index=False)
    asiento.to_csv(RES / "t5_asiento_31dic.csv", index=False)
    sens.to_csv(RES / "t6_sensibilidad.csv", index=False)
    graficas(serie, sim, ve, p95, mun)

    resumen = dict(
        accidentes_camino_2023=int(len(camino[camino.ANIO == 2023])),
        accidentes_camino_2010_2023=int(len(camino)),
        vehiculos_edomex_2023=int(v.vehiculos.sum()), vehiculos_metepec_2023=int(veh_metepec),
        tasa_reclamacion_ordinaria_por_1000_veh=round(tasa * 1000, 3),
        reclamaciones_ordinarias_esperadas=round(float(v.reclam_ordinarias.sum())),
        casos_viables=round(float(t.casos_viables.sum()), 1),
        valor_esperado=round(float(ve), 2), percentil_95=round(float(p95), 2),
        percentil_5=round(float(np.percentile(sim, 5)), 2),
        p_al_menos_un_pago=round(float(p_salida), 4), clasificacion_nif_c9=clas,
        pasivo_contingente_a_revelar=round(float(revelar), 2),
        accidentes_por_responsable_2019_2023={k: int(x) for k, x in resp.items()},
        costo_por_muerte_LFT=round(MUERTO, 2), costo_medio_herido=round(tri_media(*HERIDO), 2),
        fuentes=FUENTES,
    )
    (RES / "resumen.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")
    print(t.round(3).to_string())
    print(json.dumps({k: x for k, x in resumen.items() if k != "fuentes"}, ensure_ascii=False, indent=1))
    print(mun.head(10)[["municipio", "vehiculos", "accidentes_camino_2019_2023", "provision"]])
    print(sens)


if __name__ == "__main__":
    main()
