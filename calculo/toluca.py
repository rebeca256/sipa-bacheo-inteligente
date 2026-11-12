"""
SIPA - Cálculo Integral con baches reales de Toluca.

Requiere: python scripts/limpiar_toluca.py  y  python calculo/degradacion.py
  1. Bache típico real (mediana de área y profundidad) frente al simulado de SIPA.
  2. Material perdido si espera 6 meses de lluvias: P(T) = V0 (e^{kT} − 1) = ∫0^T k V0 e^{kt} dt.
  3. Costo esperado por bache como integral: E[c] = ∫ c(a) f(a) da, con f lognormal;
     sumas de Riemann con n = 10, 100 y 1000 frente al promedio de la muestra.
  4. Mezcla asfáltica de un año: toneladas = N · E[V] · densidad · desperdicio.
Uso:  python calculo/toluca.py
Salida: calculo/resultados_toluca/resumen.json
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

SAL = Path("calculo/resultados_toluca")
SAL.mkdir(exist_ok=True)
DENSIDAD, DESPERDICIO = 2.4, 1.10
TAR = {t["clave"]: t for t in json.loads(Path("datos/costos/tarifas_reparacion.json")
                                         .read_text(encoding="utf-8"))["tarifas"]}


def riemann(f, a, b, n):
    dx = (b - a) / n
    xs = a + dx * (np.arange(n) + 0.5)
    return float(np.sum(f(xs)) * dx)


def main():
    base = json.loads(Path("calculo/resultados/resumen.json").read_text(encoding="utf-8"))
    k_l = base["k_lluvias"]
    m = pd.read_csv("datos/limpios/toluca_medidas.csv")
    b = pd.read_csv("datos/limpios/toluca_baches.csv")
    mp = m.dropna(subset=["profundidad_cm"])
    r = {}

    area, prof = float(m.area_m2.median()), float(mp.profundidad_cm.median())
    v0 = area * prof / 100
    perd6 = v0 * (np.exp(k_l * 6) - 1)
    r["tipico"] = dict(area_real=round(area, 2), prof_real_cm=round(prof, 1), v0_real=round(v0, 4),
                       area_sim=base["area_tipica_m2"], prof_sim_cm=base["profundidad_tipica_cm"],
                       v0_sim=base["v0_tipico_m3"], k_lluvias=round(k_l, 4),
                       perdida_6m_real_m3=round(perd6, 4), perdida_6m_riemann=round(
                           riemann(lambda t: k_l * v0 * np.exp(k_l * t), 0, 6, 100), 4),
                       crece_6m_pct=round(float(np.exp(k_l * 6) - 1) * 100, 1))

    res = {}
    for tipo, clave in [("SUPERFICIAL", "BACHEO_SUPERFICIAL"), ("PROFUNDO", "BACHEO_PROFUNDO")]:
        a = m.area_m2[m.tipo == tipo].values
        s, _, esc = stats.lognorm.fit(a, floc=0)
        t = TAR[clave]
        c = lambda x, t=t: t["costo_fijo"] + t["costo_m2"] * np.maximum(x, t["area_minima_m2"])
        f = lambda x, s=s, esc=esc: c(x) * stats.lognorm.pdf(x, s, 0, esc)
        tope = float(stats.lognorm.ppf(0.9999, s, 0, esc))
        res[tipo] = dict(
            sigma=round(s, 3), mediana=round(esc, 2),
            riemann={str(n): round(riemann(f, 1e-6, tope, n), 2) for n in (10, 100, 1000)},
            exacto=round(float(t["costo_fijo"] + t["costo_m2"] * (
                t["area_minima_m2"] * stats.lognorm.cdf(t["area_minima_m2"], s, 0, esc)
                + esc * np.exp(s ** 2 / 2) * stats.norm.sf((np.log(t["area_minima_m2"] / esc) - s ** 2) / s))), 2),
            muestra=round(float(c(a).mean()), 2), n=len(a))
    r["costo_esperado"] = res

    n25 = b[b.anio == 2025].shape[0]
    ev = float(mp.volumen_m3.mean())
    r["mezcla_2025"] = dict(baches=n25, volumen_medio_m3=round(ev, 4),
                            toneladas=round(n25 * ev * DENSIDAD * DESPERDICIO, 0),
                            toneladas_espera_6m=round(n25 * ev * np.exp(k_l * 6) * DENSIDAD * DESPERDICIO, 0))
    (SAL / "resumen.json").write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(r, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
