"""
SIPA - Probabilidad
Incidente crítico: «¿Qué vialidad debe atenderse primero?»
Semáforo de Prioridad de Bacheo y modelo de riesgo de siniestro a 72 horas.

Datos reales:
  - Hechos de tránsito registrados por la SSC (datos abiertos CDMX, 2018-2019):
    datos/accidentes/hechos_transito_ssc.csv
  - Base maestra de reportes de baches CDMX (2019-2022, ya limpia):
    datos/limpios/base_maestra_limpia.csv
  - Baches pendientes y su IPU, de la base SIPA (SQL Server).

Ambas fuentes se cruzan en la misma cuadrícula de 250 m que usa SIPA
(asignar_celda de scripts/limpiar_base_maestra.py). El año en común es 2019.

Modelo de riesgo a 72 h de una celda c con un bache activo:

    N_c ~ Poisson(μ_c),   μ_c = λ_c · RR · 3/365
    P(al menos un accidente en 72 h) = 1 − e^(−μ_c)

    λ_c : accidentes por año de la celda, suavizado con Bayes (Gamma-Poisson)
    RR  : riesgo relativo de las celdas con baches frente a las que no tienen

Uso (desde la carpeta del proyecto):
    python probabilidad/riesgo_72h.py
Genera en probabilidad/resultados/: gráficas PNG, tablas CSV y resumen.json.
"""

import json
import math
import sys
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from limpiar_base_maestra import LAT_MAX, LAT_MIN, LON_MAX, LON_MIN, asignar_celda  # noqa: E402

warnings.filterwarnings("ignore", message="pandas only supports SQLAlchemy")

SALIDA = Path("probabilidad/resultados")
RUTA_ACCIDENTES = Path("datos/accidentes/hechos_transito_ssc.csv")
RUTA_REPORTES = Path("datos/limpios/base_maestra_limpia.csv")

ANIO_COMUN = 2019
DIAS_VENTANA = 3            # 72 horas
ANIOS_ACCIDENTES = 2        # 2018 y 2019

# Vías de acceso controlado ("vías rápidas") de la CDMX, por nombre de calle
VIAS_RAPIDAS = r"PERIFERICO|CIRCUITO|VIADUCTO|TLALPAN|CHURUBUSCO|AUTOPISTA|ZARAGOZA|AQUILES SERDAN|CONSTITUYENTES"

# Umbrales del semáforo por probabilidad de al menos un accidente en 72 h
UMBRAL_ROJO = 0.03          # 1 de cada 33 ventanas de 72 h o más
UMBRAL_AMARILLO = 0.01      # entre 1 de cada 100 y 1 de cada 33

# Escenario de ponchadura (ilustrativo, se declara como supuesto)
AFORO_VIA_RAPIDA = 40_000   # veh/día, aforo de referencia de vía primaria en el catálogo de SIPA
P_PISAR = 0.03              # fracción de vehículos que pasa la llanta por el bache
P_DANO = 0.01               # probabilidad de daño en llanta o rin al pisar un bache profundo


# ---------------------------------------------------------------------------
# Lectura y cruce de datos
# ---------------------------------------------------------------------------

def leer_accidentes():
    a = pd.read_csv(RUTA_ACCIDENTES, encoding="latin1", low_memory=False)
    a["latitud"] = pd.to_numeric(a["coordenada_y"], errors="coerce")
    a["longitud"] = pd.to_numeric(a["coordenada_x"], errors="coerce")
    a = a[a["latitud"].between(LAT_MIN, LAT_MAX) & a["longitud"].between(LON_MIN, LON_MAX)].copy()
    a = asignar_celda(a)
    a["fecha"] = pd.to_datetime(a["fecha_evento"])
    a["anio"] = a["fecha"].dt.year
    # grave: hubo persona fallecida o la SSC lo clasificó como prioridad ALTA
    a["grave"] = (a["condicion"] == "OCCISO") | (a["prioridad"] == "ALTA")
    calles = a["punto_1"].fillna("").str.upper() + " " + a["punto_2"].fillna("").str.upper()
    a["via_rapida"] = calles.str.contains(VIAS_RAPIDAS)
    return a


def leer_reportes():
    r = pd.read_csv(RUTA_REPORTES, parse_dates=["fecha_solicitud"])
    return r[~r["posible_duplicado"] & ~r["periodo_atipico"]].copy()


def tabla_celdas(acc, rep):
    """Una fila por celda con accidentes y reportes de baches de 2019."""
    a19 = acc[acc["anio"] == ANIO_COMUN]
    r19 = rep[rep["anio"] == ANIO_COMUN]
    celdas = sorted(set(acc["celda_id"]) | set(rep["celda_id"]))
    df = pd.DataFrame(index=pd.Index(celdas, name="celda_id"))
    df["reportes_2019"] = r19["celda_id"].value_counts()
    df["acc_2019"] = a19["celda_id"].value_counts()
    df["graves_2019"] = a19[a19["grave"]]["celda_id"].value_counts()
    df["acc_total"] = acc["celda_id"].value_counts()
    df["graves_total"] = acc[acc["grave"]]["celda_id"].value_counts()
    df["via_rapida"] = acc[acc["via_rapida"]]["celda_id"].value_counts()
    df = df.fillna(0)
    df[df.columns] = df[df.columns].astype(int)
    df["via_rapida"] = df["via_rapida"] > 0
    df["B"] = df["reportes_2019"] > 0      # la celda tuvo baches reportados
    df["A"] = df["acc_2019"] > 0           # la celda tuvo al menos un accidente
    df["G"] = df["graves_2019"] > 0        # la celda tuvo al menos un accidente grave
    return df


# ---------------------------------------------------------------------------
# A) Conceptos básicos: espacio muestral, condicional, total, Bayes, conteo
# ---------------------------------------------------------------------------

def conceptos_basicos(df, rep):
    n = len(df)
    p_b = df["B"].mean()
    p_a = df["A"].mean()
    p_ab = (df["A"] & df["B"]).mean()
    p_a_dado_b = df.loc[df["B"], "A"].mean()
    p_a_dado_nob = df.loc[~df["B"], "A"].mean()
    p_g_dado_b = df.loc[df["B"], "G"].mean()
    p_g_dado_nob = df.loc[~df["B"], "G"].mean()
    p_g_total = p_g_dado_b * p_b + p_g_dado_nob * (1 - p_b)        # probabilidad total
    p_b_dado_g = p_g_dado_b * p_b / p_g_total                      # Bayes

    tabla = pd.crosstab(df["B"], df["A"])
    chi2, p_valor, _, _ = stats.chi2_contingency(tabla)

    # Interpretación frecuentista: proporción de reportes en temporada de lluvias
    p_lluvias = rep["temporada_lluvias"].mean()

    # Conteo: de 20 baches en ROJO, 8 están en vía rápida; un supervisor revisa 5 al azar.
    # P(al menos 3 en vía rápida) con combinaciones (hipergeométrica).
    total, exito, muestra = 20, 8, 5
    p_conteo = sum(math.comb(exito, k) * math.comb(total - exito, muestra - k)
                   for k in range(3, muestra + 1)) / math.comb(total, muestra)

    filas = [
        ("Celdas analizadas (espacio muestral)", n),
        ("P(B): celda con baches reportados en 2019", p_b),
        ("P(A): celda con al menos un accidente en 2019", p_a),
        ("P(A ∩ B)", p_ab),
        ("P(A)·P(B) (si fueran independientes)", p_a * p_b),
        ("P(A | B)", p_a_dado_b),
        ("P(A | no B)", p_a_dado_nob),
        ("P(G | B): accidente grave dado bache", p_g_dado_b),
        ("P(G | no B)", p_g_dado_nob),
        ("P(G) por probabilidad total", p_g_total),
        ("P(B | G) por Bayes", p_b_dado_g),
        ("Chi cuadrada de independencia A-B", chi2),
        ("Valor p", p_valor),
        ("P(reporte en temporada de lluvias), frecuentista", p_lluvias),
        ("P(≥3 de 5 revisados en vía rápida), conteo", p_conteo),
    ]
    t = pd.DataFrame(filas, columns=["concepto", "valor"])
    return t, tabla, dict(p_a_dado_b=p_a_dado_b, p_a_dado_nob=p_a_dado_nob, p_b_dado_g=p_b_dado_g,
                          p_g_total=p_g_total, chi2=chi2, p_valor=p_valor, p_lluvias=p_lluvias,
                          p_conteo=p_conteo, p_b=p_b, p_g_dado_b=p_g_dado_b, p_g_dado_nob=p_g_dado_nob)


# ---------------------------------------------------------------------------
# B) Variables aleatorias: X = accidentes de una celda en un año
# ---------------------------------------------------------------------------

def variable_aleatoria(df):
    filas = []
    for nombre, sub in [("Con baches (B)", df[df["B"]]), ("Sin baches", df[~df["B"]]), ("Todas", df)]:
        x = sub["acc_2019"]
        filas.append((nombre, len(x), x.mean(), x.var(), x.var() / x.mean(), (x == 0).mean()))
    t = pd.DataFrame(filas, columns=["grupo", "celdas", "E[X]", "Var[X]", "Var/E", "P(X=0)"])
    pmf = df["acc_2019"].clip(upper=10).value_counts(normalize=True).sort_index()
    return t, pmf


# ---------------------------------------------------------------------------
# C) Discretas: Bernoulli, binomial, geométrica, binomial negativa, Poisson
# ---------------------------------------------------------------------------

def ajuste_binomial_negativa(x):
    """Método de momentos. Equivale a Poisson con λ ~ Gamma(r, r/m)."""
    m, v = x.mean(), x.var()
    r = m * m / (v - m)
    return m, v, r


def distribuciones_discretas(df, acc):
    x = df["acc_2019"]
    m, v, r = ajuste_binomial_negativa(x)
    p_nb = r / (r + m)
    ks = np.arange(0, 11)
    emp = np.array([(x == k).mean() for k in ks])
    poi = stats.poisson.pmf(ks, m)
    nbn = stats.nbinom.pmf(ks, r, p_nb)
    comparacion = pd.DataFrame({"k": ks, "empirica": emp, "poisson": poi, "binomial_negativa": nbn})

    # Celda con más accidentes: Bernoulli diaria, binomial en 3 días, Poisson, geométrica
    top = df.sort_values("acc_total", ascending=False).index[0]
    lam_dia = df.loc[top, "acc_total"] / (365 * ANIOS_ACCIDENTES)
    dias = acc[acc["celda_id"] == top]["fecha"].dt.normalize().nunique()
    p_dia = dias / (365 * ANIOS_ACCIDENTES)                    # Bernoulli: día con accidente
    celda_top = dict(
        celda=top, accidentes=int(df.loc[top, "acc_total"]), lam_dia=lam_dia, p_dia=p_dia,
        p72_binomial=1 - (1 - p_dia) ** DIAS_VENTANA,
        p72_poisson=1 - math.exp(-lam_dia * DIAS_VENTANA),
        esperanza_geometrica=1 / p_dia,                         # días hasta el primer accidente
        p_geom_7=1 - (1 - p_dia) ** 7,
        esperanza_nbinom_3=3 / p_dia,                           # días hasta el 3.er día con accidente
    )

    # Aproximación de la binomial por Poisson: ponchaduras en vía rápida (escenario)
    n = AFORO_VIA_RAPIDA * DIAS_VENTANA
    p = P_PISAR * P_DANO
    ks2 = np.arange(0, 80)
    error = np.abs(stats.binom.pmf(ks2, n, p) - stats.poisson.pmf(ks2, n * p)).max()
    ponchadura = dict(n=n, p=p, mu=n * p, p_al_menos_una=1 - math.exp(-n * p),
                      p_al_menos_10=1 - stats.poisson.cdf(9, n * p), error_max_aprox=error)
    return comparacion, dict(media=m, varianza=v, r=r), celda_top, ponchadura


# ---------------------------------------------------------------------------
# D) Continuas: exponencial, gamma, uniforme, normal, TLC, chi cuadrada, t
# ---------------------------------------------------------------------------

def distribuciones_continuas(acc, rep, celda_top):
    # Exponencial: días entre accidentes consecutivos de la celda con más accidentes
    f = acc[acc["celda_id"] == celda_top["celda"]]["fecha"].sort_values()
    espera = f.diff().dt.days.dropna().to_numpy()
    media_espera = espera.mean()
    ks_exp = stats.kstest(espera, "expon", args=(0, media_espera))
    p_exp_72 = 1 - math.exp(-DIAS_VENTANA / media_espera)
    # Gamma: tiempo hasta el 3.er accidente (suma de 3 exponenciales)
    gamma_3 = stats.gamma(a=3, scale=media_espera)

    # Uniforme: ¿los accidentes se reparten igual en las 24 horas? (chi cuadrada)
    horas = acc["hora2"].dropna().astype(int).value_counts().reindex(range(24), fill_value=0)
    chi_hora = stats.chisquare(horas)

    # Normal y TLC: reportes de baches por día en la ciudad, por temporada
    diarios = (rep.groupby(["temporada_lluvias", rep["fecha_solicitud"].dt.normalize()])
                  .size().rename("reportes").reset_index())
    ll = diarios[diarios["temporada_lluvias"]]["reportes"]
    se = diarios[~diarios["temporada_lluvias"]]["reportes"]
    capacidad = float(np.ceil(se.quantile(0.95)))              # capacidad = día alto de secas
    p_normal = 1 - stats.norm.cdf(capacidad, ll.mean(), ll.std())
    p_empirica = (ll > capacidad).mean()
    # TLC: promedio semanal de reportes (n = 7 días) ~ Normal(μ, σ/√7)
    ic_lluvias = stats.norm.interval(0.95, ll.mean(), ll.std() / math.sqrt(len(ll)))
    # t de Student (Welch): ¿la media diaria en lluvias es mayor que en secas?
    t_res = stats.ttest_ind(ll, se, equal_var=False, alternative="greater")

    return dict(
        espera=espera, media_espera=media_espera, ks_estadistico=ks_exp.statistic, ks_p=ks_exp.pvalue,
        p_exp_72=p_exp_72, gamma3_media=gamma_3.mean(), gamma3_p30=gamma_3.cdf(30),
        horas=horas, chi_hora=chi_hora.statistic, chi_hora_p=chi_hora.pvalue,
        lluvias=ll, secas=se, media_ll=ll.mean(), sd_ll=ll.std(), media_se=se.mean(), sd_se=se.std(),
        capacidad=capacidad, p_normal=p_normal, p_empirica=p_empirica, ic_lluvias=ic_lluvias,
        t=t_res.statistic, t_p=t_res.pvalue,
    )


# ---------------------------------------------------------------------------
# E) Modelo de riesgo a 72 h y semáforo
# ---------------------------------------------------------------------------

def modelo_riesgo(df, acc, nb):
    # Riesgo relativo: accidentes por celda con baches / sin baches (2019)
    rr = df.loc[df["B"], "acc_2019"].mean() / df.loc[~df["B"], "acc_2019"].mean()
    p_grave = acc["grave"].mean()

    # Bayes empírico (Gamma-Poisson): λ_c = (r + n_c) / (r/m + años)
    # Una celda sin accidentes no queda con riesgo 0, y una con pocos datos se acerca al promedio.
    r, m = nb["r"], nb["media"]
    lam = (r + df["acc_total"]) / (r / m + ANIOS_ACCIDENTES)
    lam_grave = (r * p_grave + df["graves_total"]) / (r / m + ANIOS_ACCIDENTES)

    mu = lam * rr * DIAS_VENTANA / 365
    out = df.copy()
    out["lambda_anual"] = lam
    out["p72_accidente"] = 1 - np.exp(-mu)
    out["p72_grave"] = 1 - np.exp(-lam_grave * rr * DIAS_VENTANA / 365)
    out["semaforo_72h"] = np.select(
        [out["p72_accidente"] >= UMBRAL_ROJO, out["p72_accidente"] >= UMBRAL_AMARILLO],
        ["ROJO", "AMARILLO"], "VERDE")
    # Valor normalizado para el criterio RIESGO_72H del IPU (0 a 1)
    tope = out["p72_accidente"].quantile(0.99)
    out["v_riesgo_72h"] = (out["p72_accidente"] / tope).clip(upper=1).round(4)

    # Incidente: bache profundo en vía rápida.
    vr = out[out["via_rapida"]]
    atribuible = 1 - 1 / rr          # fracción del riesgo atribuible al bache
    incidente = dict(
        celdas_via_rapida=len(vr),
        p72_accidente_mediana=vr["p72_accidente"].median(),
        p72_grave_mediana=vr["p72_grave"].median(),
        p72_accidente_p90=vr["p72_accidente"].quantile(0.9),
        p72_grave_p90=vr["p72_grave"].quantile(0.9),
        fraccion_atribuible=atribuible,
        p72_otras_mediana=out[~out["via_rapida"]]["p72_accidente"].median(),
    )
    return out, dict(rr=rr, p_grave=p_grave), incidente


def leer_pendientes():
    """Baches validados o priorizados en la base SIPA, con su último IPU."""
    import pyodbc
    cx = pyodbc.connect("DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;"
                        "DATABASE=SIPA;Trusted_Connection=yes")
    q = pd.read_sql("""
        SELECT b.id_bache, b.celda_id, b.profundidad_cm, cp.ipu, cp.semaforo AS semaforo_ipu
        FROM bache b
        OUTER APPLY (SELECT TOP 1 ipu, semaforo FROM calculo_prioridad c
                     WHERE c.id_bache = b.id_bache ORDER BY c.id_calculo DESC) cp
        WHERE b.id_estado_bache IN (2, 3, 4)""", cx)
    cx.close()
    return q


# ---------------------------------------------------------------------------
# Gráficas
# ---------------------------------------------------------------------------

def graficas(comp, cont, riesgo, pendientes):
    plt.rcParams.update({"font.size": 10})

    fig, ax = plt.subplots(figsize=(7, 4))
    w = 0.28
    ax.bar(comp["k"] - w, comp["empirica"], w, label="Datos 2019")
    ax.bar(comp["k"], comp["poisson"], w, label="Poisson")
    ax.bar(comp["k"] + w, comp["binomial_negativa"], w, label="Binomial negativa")
    ax.set_xlabel("Accidentes de una celda en el año")
    ax.set_ylabel("Probabilidad")
    ax.set_title("La binomial negativa describe mejor los accidentes por celda")
    ax.legend()
    fig.tight_layout(); fig.savefig(SALIDA / "g1_accidentes_por_celda.png", dpi=150); plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4))
    e = cont["espera"]
    ax.hist(e, bins=25, density=True, alpha=0.6, label="Días entre accidentes (datos)")
    xs = np.linspace(0, e.max(), 200)
    ax.plot(xs, stats.expon.pdf(xs, 0, cont["media_espera"]), lw=2, label="Exponencial")
    ax.set_xlabel("Días"); ax.set_ylabel("Densidad")
    ax.set_title("Tiempo entre accidentes en la celda más peligrosa")
    ax.legend()
    fig.tight_layout(); fig.savefig(SALIDA / "g2_exponencial.png", dpi=150); plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4))
    for serie, nombre in [(cont["secas"], "Secas"), (cont["lluvias"], "Lluvias")]:
        ax.hist(serie, bins=30, density=True, alpha=0.5, label=nombre)
        xs = np.linspace(serie.min(), serie.max(), 200)
        ax.plot(xs, stats.norm.pdf(xs, serie.mean(), serie.std()), lw=2)
    ax.axvline(cont["capacidad"], color="k", ls="--", label="Capacidad de atención")
    ax.set_xlabel("Reportes de baches por día"); ax.set_ylabel("Densidad")
    ax.set_title("Reportes diarios por temporada y aproximación normal")
    ax.legend()
    fig.tight_layout(); fig.savefig(SALIDA / "g3_normal_temporadas.png", dpi=150); plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(cont["horas"].index, cont["horas"].values / cont["horas"].sum(), label="Datos")
    ax.axhline(1 / 24, color="r", ls="--", label="Uniforme (1/24)")
    ax.set_xlabel("Hora del día"); ax.set_ylabel("Proporción de accidentes")
    ax.set_title("Los accidentes no se reparten uniformemente en el día")
    ax.legend()
    fig.tight_layout(); fig.savefig(SALIDA / "g4_hora_uniforme.png", dpi=150); plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4))
    colores = {"VERDE": "#2e7d32", "AMARILLO": "#f9a825", "ROJO": "#c62828"}
    p = riesgo["p72_accidente"]
    ax.hist(p, bins=60, color="#607d8b")
    ax.axvline(UMBRAL_AMARILLO, color=colores["AMARILLO"], lw=2, label=f"Amarillo ≥ {UMBRAL_AMARILLO:.0%}")
    ax.axvline(UMBRAL_ROJO, color=colores["ROJO"], lw=2, label=f"Rojo ≥ {UMBRAL_ROJO:.0%}")
    ax.set_yscale("log")
    ax.set_xlabel("P(al menos un accidente en 72 h) con un bache activo")
    ax.set_ylabel("Celdas (escala log)")
    ax.set_title("Semáforo de riesgo a 72 horas")
    ax.legend()
    fig.tight_layout(); fig.savefig(SALIDA / "g5_semaforo_72h.png", dpi=150); plt.close(fig)

    if pendientes is not None and len(pendientes):
        t = pd.crosstab(pendientes["semaforo_ipu"], pendientes["semaforo_72h"])
        orden = [c for c in ["ROJO", "AMARILLO", "VERDE"]]
        t = t.reindex(index=orden, columns=orden, fill_value=0)
        fig, ax = plt.subplots(figsize=(5.5, 4))
        ax.imshow(t.values, cmap="Blues")
        ax.set_xticks(range(3), orden); ax.set_yticks(range(3), orden)
        ax.set_xlabel("Semáforo de riesgo a 72 h"); ax.set_ylabel("Semáforo IPU actual")
        for i in range(3):
            for j in range(3):
                ax.text(j, i, t.values[i, j], ha="center", va="center")
        ax.set_title("Baches pendientes: IPU vs. riesgo a 72 h")
        fig.tight_layout(); fig.savefig(SALIDA / "g6_ipu_vs_72h.png", dpi=150); plt.close(fig)


# ---------------------------------------------------------------------------
# Principal
# ---------------------------------------------------------------------------

def main():
    SALIDA.mkdir(parents=True, exist_ok=True)
    acc, rep = leer_accidentes(), leer_reportes()
    df = tabla_celdas(acc, rep)

    t1, contingencia, basicos = conceptos_basicos(df, rep)
    t2, pmf = variable_aleatoria(df)
    comp, nb, celda_top, ponchadura = distribuciones_discretas(df, acc)
    cont = distribuciones_continuas(acc, rep, celda_top)
    riesgo, params, incidente = modelo_riesgo(df, acc, nb)

    try:
        pend = leer_pendientes()
        pend = pend.merge(riesgo[["p72_accidente", "p72_grave", "semaforo_72h", "v_riesgo_72h"]],
                          left_on="celda_id", right_index=True, how="left")
        # celdas sin ningún accidente ni reporte en el periodo: riesgo base del modelo
        base = 1 - math.exp(-(nb["r"] / (nb["r"] / nb["media"] + ANIOS_ACCIDENTES)) * params["rr"] * DIAS_VENTANA / 365)
        pend["p72_accidente"] = pend["p72_accidente"].fillna(base)
        pend["semaforo_72h"] = pend["semaforo_72h"].fillna("VERDE")
        pend.to_csv(SALIDA / "t6_baches_pendientes_72h.csv", index=False)
    except Exception as e:  # la base no está disponible: el resto del análisis sí corre
        print("Aviso: no se pudo leer SIPA:", e)
        pend = None

    graficas(comp, cont, riesgo, pend)

    t1.to_csv(SALIDA / "t1_conceptos_basicos.csv", index=False)
    contingencia.to_csv(SALIDA / "t1b_contingencia.csv")
    t2.to_csv(SALIDA / "t2_variable_aleatoria.csv", index=False)
    comp.to_csv(SALIDA / "t3_poisson_vs_binomial_negativa.csv", index=False)
    riesgo.reset_index()[["celda_id", "acc_total", "graves_total", "via_rapida", "lambda_anual",
                          "p72_accidente", "p72_grave", "semaforo_72h", "v_riesgo_72h"]] \
        .to_csv(SALIDA / "t4_riesgo_72h_por_celda.csv", index=False)
    semaforo = riesgo["semaforo_72h"].value_counts().reindex(["ROJO", "AMARILLO", "VERDE"], fill_value=0)
    semaforo.rename("celdas").to_csv(SALIDA / "t5_semaforo_celdas.csv")

    resumen = {
        "accidentes": int(len(acc)), "accidentes_2019": int((acc["anio"] == ANIO_COMUN).sum()),
        "graves": int(acc["grave"].sum()), "celdas": int(len(df)),
        "basicos": basicos,
        "variable_aleatoria": t2.to_dict(orient="records"),
        "binomial_negativa": nb, "celda_top": celda_top, "ponchadura": ponchadura,
        "continuas": {k: (float(v) if np.isscalar(v) else None) for k, v in cont.items()
                      if k not in ("espera", "horas", "lluvias", "secas", "ic_lluvias")},
        "ic_lluvias": [float(x) for x in cont["ic_lluvias"]],
        "riesgo": params, "incidente": incidente,
        "semaforo_celdas": semaforo.to_dict(),
        "acc_por_mes_2019": acc[acc["anio"] == ANIO_COMUN]["fecha"].dt.month.value_counts().sort_index().to_dict(),
    }
    if pend is not None:
        resumen["pendientes"] = {
            "baches": int(len(pend)),
            "semaforo_72h": pend["semaforo_72h"].value_counts().to_dict(),
            "semaforo_ipu": pend["semaforo_ipu"].value_counts().to_dict(),
            "coinciden": float((pend["semaforo_72h"] == pend["semaforo_ipu"]).mean()),
            "rojo72_no_rojo_ipu": int(((pend["semaforo_72h"] == "ROJO") & (pend["semaforo_ipu"] != "ROJO")).sum()),
        }
    with open(SALIDA / "resumen.json", "w", encoding="utf-8") as fh:
        json.dump(resumen, fh, ensure_ascii=False, indent=2, default=lambda o: o.item() if hasattr(o, "item") else str(o))

    print(json.dumps(resumen, ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)))


if __name__ == "__main__":
    main()
