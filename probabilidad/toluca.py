"""
SIPA - Probabilidad con datos reales de Toluca (tablero de bacheo de la DGOP).

Requiere: python scripts/limpiar_toluca.py
  1. Binomial: proporción de baches profundos e intervalo de confianza.
  2. Lognormal: distribución del área del bache (ajuste por máxima verosimilitud y prueba K-S).
  3. t de Welch: ¿los baches profundos son más grandes que los superficiales?
  4. Poisson frente a binomial negativa: baches reparados por colonia y mes.
  5. TLC: intervalo de confianza del área media con la muestra.
Uso:  python probabilidad/toluca.py
Salida: probabilidad/resultados_toluca/ (resumen.json y gráficas)
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

SAL = Path("probabilidad/resultados_toluca")
SAL.mkdir(exist_ok=True)


def main():
    b = pd.read_csv("datos/limpios/toluca_baches.csv")
    b = b[b.tipo != "SIN_CLASIFICAR"]
    m = pd.read_csv("datos/limpios/toluca_medidas.csv")
    m = m[m.tipo != "SIN_CLASIFICAR"]
    r = {}

    # 1. binomial
    n, k = len(b), int((b.tipo == "PROFUNDO").sum())
    p = k / n
    ee = np.sqrt(p * (1 - p) / n)
    r["binomial"] = dict(n=n, profundos=k, p=round(p, 4), ic95=[round(p - 1.96 * ee, 4), round(p + 1.96 * ee, 4)],
                         p_al_menos_5_de_10=round(float(1 - stats.binom.cdf(4, 10, p)), 4))

    # 2. lognormal del área
    a = m.area_m2.values
    s, loc, esc = stats.lognorm.fit(a, floc=0)
    ks = stats.kstest(a, "lognorm", args=(s, loc, esc))
    mu, sigma = np.log(esc), s
    r["lognormal"] = dict(mu=round(mu, 3), sigma=round(sigma, 3), mediana=round(esc, 2),
                          media_teorica=round(float(np.exp(mu + sigma ** 2 / 2)), 2),
                          p_mayor_10m2=round(float(stats.lognorm.sf(10, s, loc, esc)), 4),
                          p_mayor_10m2_observada=round(float((a > 10).mean()), 4),
                          ks_D=round(ks.statistic, 4), ks_p=round(ks.pvalue, 4))

    # 3. t de Welch
    ap, asup = m.area_m2[m.tipo == "PROFUNDO"], m.area_m2[m.tipo == "SUPERFICIAL"]
    t = stats.ttest_ind(np.log(ap), np.log(asup), equal_var=False)
    r["welch"] = dict(media_profundo=round(ap.mean(), 2), media_superficial=round(asup.mean(), 2),
                      n_profundo=len(ap), n_superficial=len(asup), t=round(t.statistic, 3),
                      p=float(f"{t.pvalue:.2e}"))

    # 4. Poisson frente a binomial negativa (colonia × mes, 2025)
    c = b[b.anio == 2025].groupby(["colonia", "mes"]).size()
    tabla = c.unstack(fill_value=0).stack()
    media, var = tabla.mean(), tabla.var()
    kk = media ** 2 / (var - media) if var > media else np.inf
    r["conteos"] = dict(celdas=int(len(tabla)), media=round(media, 2), varianza=round(var, 2),
                        dispersion=round(var / media, 2), k_binneg=round(kk, 3),
                        p_cero_poisson=round(float(np.exp(-media)), 4),
                        p_cero_binneg=round(float((kk / (kk + media)) ** kk), 4),
                        p_cero_observada=round(float((tabla == 0).mean()), 4))

    # 5. TLC
    xb, sd = a.mean(), a.std(ddof=1)
    tc = stats.t.ppf(0.975, len(a) - 1)
    r["tlc"] = dict(n=len(a), media=round(xb, 3), de=round(sd, 3),
                    ic95=[round(xb - tc * sd / np.sqrt(len(a)), 3), round(xb + tc * sd / np.sqrt(len(a)), 3)])
    r["profundidad"] = dict(mediana_cm=float(m.profundidad_cm.median()),
                            valores_frecuentes=m.profundidad_cm.round(1).value_counts().head(4).to_dict())
    r["mensual"] = b.groupby("mes").size().to_dict()

    fig, ax = plt.subplots(1, 2, figsize=(10, 4))
    x = np.linspace(0.05, 25, 400)
    ax[0].hist(a[a <= 25], bins=50, density=True, color="#9bb7d4")
    ax[0].plot(x, stats.lognorm.pdf(x, s, loc, esc), color="#1f4e79", label="Lognormal ajustada")
    ax[0].set_xlabel("Área del bache (m²)"); ax[0].set_title("Área de los baches de Toluca"); ax[0].legend()
    serie = b.groupby("mes").size()
    ax[1].bar(range(len(serie)), serie.values, color="#1f4e79")
    ax[1].set_xticks(range(0, len(serie), 3)); ax[1].set_xticklabels(serie.index[::3], rotation=45, fontsize=8)
    ax[1].set_title("Baches reparados por mes")
    fig.tight_layout(); fig.savefig(SAL / "g1_area_y_meses.png", dpi=150); plt.close(fig)

    (SAL / "resumen.json").write_text(json.dumps(r, ensure_ascii=False, indent=2, default=float), encoding="utf-8")
    print(json.dumps({k: v for k, v in r.items() if k != "mensual"}, ensure_ascii=False, indent=1, default=float))


if __name__ == "__main__":
    main()
