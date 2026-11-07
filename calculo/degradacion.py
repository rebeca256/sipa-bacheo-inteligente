"""
SIPA - Cálculo Integral
Incidente crítico: «Degradación acumulada del asfalto: ¿cuánto material se
pierde y cuánto cuesta esperar?»

Modelo (sección 5.4 de la propuesta de arquitectura):

    r(t, W) = a · (W / W0)^4 · e^(k·t)        tasa de pérdida [m3 / mes]

    - (W / W0)^4: ley de la cuarta potencia; el daño crece con la cuarta
      potencia de la carga por eje respecto a una carga de referencia W0.
    - e^(k·t): el daño se acelera; un bache más grande retiene más agua y
      recibe más golpes, así que crece más rápido.
    - a = k · V0, con V0 el volumen inicial del bache. Así el volumen del
      bache cumple la ecuación diferencial dV/dt = k·V  ->  V(t) = V0·e^(kt)
      (cuando W = W0).

Volumen perdido entre 0 y T (integral definida, teorema fundamental):

    P(T) = ∫0^T r(t) dt = a·φ·(e^(kT) − 1)/k = V0·φ·(e^(kT) − 1),   φ = (W/W0)^4

Costo (mismas tarifas que la base SIPA, datos/costos/tarifas_reparacion.json):

    C(T) = F + c_m2 · MAX(A(T), A_min),   A(T) = (V0 + P(T)) / d

    El daño se extiende a lo ancho con la profundidad d del bache, así que el
    área a reparar crece con el volumen. En T = 0 da exactamente el costo
    estimado que calcula sp_calcular_ipu para el mismo bache.

Uso (desde la carpeta del proyecto):
    python calculo/degradacion.py
Genera en calculo/resultados/: gráficas PNG, tablas CSV y resumen.json.
"""

import json
import warnings
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import brentq

warnings.filterwarnings("ignore", message="pandas only supports SQLAlchemy")

SALIDA = Path("calculo/resultados")

# ---------------------------------------------------------------------------
# Parámetros (ilustrativos salvo FACTOR_LLUVIAS, que sale de los datos)
# ---------------------------------------------------------------------------

K_SECAS = 0.08            # tasa mensual de crecimiento en secas (duplica en ~8.7 meses)
FACTOR_LLUVIAS = None     # se calcula con la base de datos (reportes lluvias / secas)
DENSIDAD = 2.4            # t/m3, mezcla asfáltica compactada
DESPERDICIO = 1.10        # 10 % extra de material al reparar
DESCUENTO_ANUAL = 0.11    # tasa de descuento para valor presente
V_GRIETA = 0.004          # m3: defecto inicial tras una reparación (para el ciclo preventivo)

# Tarifas: el mismo archivo JSON que carga la base (02_catalogos.sql)
TARIFAS = {t["clave"]: t for t in json.loads(
    Path("datos/costos/tarifas_reparacion.json").read_text(encoding="utf-8"))["tarifas"]}
TARIFA_TIPICA = "BACHEO_PROFUNDO"   # la más recomendada por SIPA; se confirma con la base en main()
PROF_TIPICA_CM = 9.8                # se recalcula con la mediana de la base en main()
COSTO_FIJO = TARIFAS[TARIFA_TIPICA]["costo_fijo"]
COSTO_M3 = TARIFAS[TARIFA_TIPICA]["costo_m2"] / (PROF_TIPICA_CM / 100)   # $ por m3 de bache


# ---------------------------------------------------------------------------
# Funciones del modelo
# ---------------------------------------------------------------------------

def phi(w_rel):
    """Factor de carga (ley de la cuarta potencia). w_rel = W / W0."""
    return w_rel ** 4


def tasa(t, v0, k, w_rel=1.0):
    """r(t) = a·φ·e^(kt), con a = k·V0. [m3/mes]"""
    return k * v0 * phi(w_rel) * np.exp(k * t)


def perdida(T, v0, k, w_rel=1.0):
    """P(T) = ∫0^T r(t) dt = V0·φ·(e^(kT) − 1). [m3]  (antiderivada evaluada)"""
    return v0 * phi(w_rel) * (math.exp(k * T) - 1)


def costo_reparar(T, v0, k, w_rel=1.0, prof_cm=None, tarifa=None):
    """Costo de reparar en el mes T con la tarifa del JSON:
    F + c_m2 · MAX((V0 + P(T)) / d, área mínima)."""
    t = TARIFAS[tarifa or TARIFA_TIPICA]
    d = (prof_cm or PROF_TIPICA_CM) / 100
    area = (v0 + perdida(T, v0, k, w_rel)) / d
    return t["costo_fijo"] + t["costo_m2"] * max(area, t["area_minima_m2"])


def riemann(f, a, b, n, metodo):
    """Suma de Riemann de f en [a, b] con n rectángulos."""
    dx = (b - a) / n
    if metodo == "izquierda":
        xs = a + dx * np.arange(n)
    elif metodo == "derecha":
        xs = a + dx * np.arange(1, n + 1)
    else:  # punto medio
        xs = a + dx * (np.arange(n) + 0.5)
    return float(np.sum(f(xs)) * dx)


def punto_valor_medio(T, k):
    """Teorema del valor medio para integrales: c en [0, T] con r(c) = promedio de r.
    r(c) = P(T)/T  ->  k·e^(kc) = (e^(kT) − 1)/T  ->  c = ln((e^(kT) − 1)/(kT)) / k"""
    return math.log((math.exp(k * T) - 1) / (k * T)) / k


def valor_presente_esperar(T, v0, k, w_rel=1.0, d_anual=DESCUENTO_ANUAL):
    """Valor presente de reparar en el mes T, con descuento continuo:
    VP = C(T)·e^(−δT). Si k > δ, esperar sale más caro aun descontando."""
    delta = math.log(1 + d_anual) / 12
    return costo_reparar(T, v0, k, w_rel) * math.exp(-delta * T)


def costo_promedio_ciclo(T, k, w_rel=1.0, v_ini=V_GRIETA):
    """Programa preventivo: se repara cada T meses.
    Costo promedio mensual A(T) = (F + c·V(T)) / T, con V(T) = v·φ·e^(kT)."""
    return (COSTO_FIJO + COSTO_M3 * v_ini * phi(w_rel) * math.exp(k * T)) / T


def intervalo_optimo(k, w_rel=1.0, v_ini=V_GRIETA):
    """A'(T) = 0  ->  c·v·φ·e^(kT)·(kT − 1) = F. Se resuelve numéricamente."""
    g = lambda T: COSTO_M3 * v_ini * phi(w_rel) * math.exp(k * T) * (k * T - 1) - COSTO_FIJO
    return brentq(g, 1 / k + 1e-6, 200)


def perdida_anual_estacional(v0, k_secas, k_lluvias, w_rel=1.0, mes_inicio=1):
    """Pérdida en 12 meses alternando secas (nov-abr) y lluvias (may-oct).
    Se integra por tramos (aditividad de la integral): en cada mes se usa la k
    de su temporada y el volumen con el que termina el mes anterior."""
    v, total, detalle = v0, 0.0, []
    for i in range(12):
        mes = (mes_inicio - 1 + i) % 12 + 1
        k = k_lluvias if 5 <= mes <= 10 else k_secas
        p = perdida(1, v, k, w_rel)      # ∫ de un mes con la k de la temporada
        total += p
        v += p
        detalle.append({"mes": mes, "k": k, "perdida_m3": p, "volumen_fin_m3": v})
    return total, detalle


# ---------------------------------------------------------------------------
# Datos de la base SIPA
# ---------------------------------------------------------------------------

def leer_base():
    import pyodbc
    cx = pyodbc.connect("DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;"
                        "DATABASE=SIPA;Trusted_Connection=yes")
    estacional = pd.read_sql("""
        SELECT temporada_lluvias,
               COUNT(*) * 1.0 / COUNT(DISTINCT FORMAT(fecha_solicitud, 'yyyy-MM')) AS reportes_mes
        FROM reporte r JOIN cat_fuente_reporte f ON f.id_fuente = r.id_fuente
        WHERE f.nombre = 'BASE_MAESTRA_CDMX' AND periodo_atipico = 0
        GROUP BY temporada_lluvias""", cx)
    baches = pd.read_sql("""
        SELECT b.id_bache, t.nombre AS territorio, b.severidad, b.profundidad_cm, b.area_m2,
               b.area_m2 * b.profundidad_cm / 100.0 AS v0_m3,
               cp.clave_tarifa, cp.costo_estimado
        FROM bache b
        CROSS APPLY (SELECT TOP 1 clave_tarifa, costo_estimado FROM calculo_prioridad x
                     WHERE x.id_bache = b.id_bache ORDER BY x.id_calculo DESC) cp
        CROSS APPLY (SELECT TOP 1 c.id_territorio FROM reporte r JOIN colonia c ON c.id_colonia = r.id_colonia
                     WHERE r.id_bache = b.id_bache GROUP BY c.id_territorio ORDER BY COUNT(*) DESC) x
        JOIN territorio t ON t.id_territorio = x.id_territorio
        WHERE b.area_m2 IS NOT NULL AND b.profundidad_cm IS NOT NULL
          AND b.id_estado_bache IN (2, 3, 4)     -- abiertos: aún no reparados ni descartados""", cx)
    cx.close()
    return estacional, baches


# ---------------------------------------------------------------------------
# Gráficas
# ---------------------------------------------------------------------------

def graficas(k_s, k_l, v0, resumen):
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    t = np.linspace(0, 12, 400)

    # 1. Área bajo la curva: pérdida acumulada en 6 meses, secas vs. lluvias
    fig, ax = plt.subplots(figsize=(7, 4))
    for k, nombre, color in [(k_s, "Secas", "#2E7D32"), (k_l, "Lluvias", "#1565C0")]:
        ax.plot(t, tasa(t, v0, k), color=color, label=f"{nombre} (k = {k:.3f})")
        tt = t[t <= 6]
        ax.fill_between(tt, tasa(tt, v0, k), alpha=0.18, color=color)
    ax.axvline(6, color="gray", ls="--", lw=0.8)
    ax.set_xlabel("t (meses)"); ax.set_ylabel("r(t)  [m³ perdidos por mes]")
    ax.set_title("Tasa de pérdida de asfalto y área bajo la curva (0 a 6 meses)")
    ax.legend(); fig.tight_layout(); fig.savefig(SALIDA / "g1_area_bajo_curva.png", dpi=150); plt.close(fig)

    # 2. Sumas de Riemann (izquierda, n = 6) contra la curva
    fig, ax = plt.subplots(figsize=(7, 4))
    n, T = 6, 6
    dx = T / n
    xs = np.arange(n) * dx
    ax.bar(xs, tasa(xs, v0, k_l), width=dx, align="edge", alpha=0.3, edgecolor="#1565C0",
           color="#90CAF9", label=f"Suma izquierda, n = {n}")
    ax.plot(t[t <= T], tasa(t[t <= T], v0, k_l), color="#1565C0", label="r(t) lluvias")
    ax.set_xlabel("t (meses)"); ax.set_ylabel("r(t)  [m³/mes]")
    ax.set_title("Aproximación de la integral con sumas de Riemann")
    ax.legend(); fig.tight_layout(); fig.savefig(SALIDA / "g2_riemann.png", dpi=150); plt.close(fig)

    # 3. Costo de reparar según cuánto se espera
    fig, ax = plt.subplots(figsize=(7, 4))
    meses = np.arange(0, 13)
    for k, nombre, color in [(k_s, "Secas", "#2E7D32"), (k_l, "Lluvias", "#1565C0")]:
        ax.plot(meses, [costo_reparar(m, v0, k) for m in meses], marker="o", color=color, label=nombre)
    ax.set_xlabel("Meses de espera"); ax.set_ylabel("Costo de reparar ($)")
    ax.set_title("¿Cuánto cuesta esperar? (bache típico)")
    ax.legend(); fig.tight_layout(); fig.savefig(SALIDA / "g3_costo_esperar.png", dpi=150); plt.close(fig)

    # 4. Costo promedio mensual del programa preventivo y su mínimo
    fig, ax = plt.subplots(figsize=(7, 4))
    Ts = np.linspace(2, 45, 300)
    k_p = (k_s + k_l) / 2
    for k, nombre, color in [(k_p, "Promedio anual", "#6A1B9A"), (k_l, "Lluvias (peor caso)", "#1565C0")]:
        ax.plot(Ts, [costo_promedio_ciclo(x, k) for x in Ts], color=color, label=nombre)
        T_opt = intervalo_optimo(k)
        ax.plot(T_opt, costo_promedio_ciclo(T_opt, k), "o", color=color)
        ax.annotate(f"T* = {T_opt:.1f} meses", (T_opt, costo_promedio_ciclo(T_opt, k)),
                    textcoords="offset points", xytext=(5, 10), color=color)
    ax.set_xlabel("T: cada cuántos meses se interviene"); ax.set_ylabel("A(T)  [$ por mes]")
    ax.set_title("Intervalo óptimo de conservación preventiva: A'(T) = 0")
    ax.set_ylim(0, 600)
    ax.legend(); fig.tight_layout(); fig.savefig(SALIDA / "g4_intervalo_optimo.png", dpi=150); plt.close(fig)

    # 5. Ley de la cuarta potencia
    fig, ax = plt.subplots(figsize=(7, 4))
    w = [1.0, 1.1, 1.2, 1.3, 1.5]
    ax.bar([f"{x:.1f}" for x in w], [phi(x) for x in w], color="#EF6C00")
    for i, x in enumerate(w):
        ax.text(i, phi(x) + 0.08, f"×{phi(x):.2f}", ha="center")
    ax.set_xlabel("Carga relativa por eje  W / W0"); ax.set_ylabel("Factor de daño  (W/W0)⁴")
    ax.set_title("Ley de la cuarta potencia: un poco más de carga, mucho más daño")
    fig.tight_layout(); fig.savefig(SALIDA / "g5_cuarta_potencia.png", dpi=150); plt.close(fig)


# ---------------------------------------------------------------------------
# Programa principal
# ---------------------------------------------------------------------------

def main():
    SALIDA.mkdir(parents=True, exist_ok=True)
    estacional, baches = leer_base()

    # Calibración: factor de lluvias a partir de los reportes reales de la CDMX
    rm = estacional.set_index("temporada_lluvias")["reportes_mes"]
    factor = float(rm[True] / rm[False])
    k_s, k_l = K_SECAS, K_SECAS * factor

    # Bache típico: mediana de la base; tarifa típica: la que SIPA recomienda más
    global TARIFA_TIPICA, PROF_TIPICA_CM, COSTO_FIJO, COSTO_M3
    v0 = float(baches["v0_m3"].median())
    area = float(baches["area_m2"].median())
    prof = float(baches["profundidad_cm"].median())
    TARIFA_TIPICA = baches["clave_tarifa"].mode().iat[0]
    PROF_TIPICA_CM = prof
    COSTO_FIJO = TARIFAS[TARIFA_TIPICA]["costo_fijo"]
    COSTO_M3 = TARIFAS[TARIFA_TIPICA]["costo_m2"] / (prof / 100)

    r = {"factor_lluvias": factor, "reportes_mes_lluvias": float(rm[True]),
         "reportes_mes_secas": float(rm[False]), "k_secas": k_s, "k_lluvias": k_l,
         "v0_tipico_m3": v0, "area_tipica_m2": area, "profundidad_tipica_cm": prof,
         "costo_m3": COSTO_M3, "baches_analizados": int(len(baches)),
         "tarifa_tipica": TARIFA_TIPICA, "tarifa_nombre": TARIFAS[TARIFA_TIPICA]["nombre"],
         "tarifa_m2": TARIFAS[TARIFA_TIPICA]["costo_m2"], "costo_fijo": COSTO_FIJO,
         "duplica_secas_meses": math.log(2) / k_s, "duplica_lluvias_meses": math.log(2) / k_l}

    # 1. Integral definida: pérdida y costo a 3, 6 y 12 meses
    filas = []
    for nombre, k in [("Secas", k_s), ("Lluvias", k_l)]:
        for T in (0, 3, 6, 12):
            p = perdida(T, v0, k)
            filas.append({"temporada": nombre, "meses": T, "perdida_m3": p,
                          "volumen_total_m3": v0 + p,
                          "toneladas": (v0 + p) * DENSIDAD * DESPERDICIO,
                          "costo": costo_reparar(T, v0, k),
                          "costo_extra_por_esperar": costo_reparar(T, v0, k) - costo_reparar(0, v0, k)})
    pd.DataFrame(filas).to_csv(SALIDA / "t1_perdida_y_costo.csv", index=False, encoding="utf-8-sig")
    r["tabla_perdida"] = filas

    # 2. Sumas de Riemann vs. valor exacto (lluvias, 6 meses)
    exacto = perdida(6, v0, k_l)
    f = lambda x: tasa(x, v0, k_l)
    rie = []
    for n in (3, 6, 12, 60):
        fila = {"n": n}
        for m in ("izquierda", "derecha", "punto medio"):
            s = riemann(f, 0, 6, n, m)
            fila[m] = s
            fila[f"error_{m}_%"] = 100 * (s - exacto) / exacto
        rie.append(fila)
    pd.DataFrame(rie).to_csv(SALIDA / "t2_riemann.csv", index=False, encoding="utf-8-sig")
    r["riemann"] = rie
    r["exacto_lluvias_6m"] = exacto

    # 3. Teorema del valor medio para integrales (lluvias, 6 meses)
    c = punto_valor_medio(6, k_l)
    r["valor_medio"] = {"T": 6, "tasa_promedio": exacto / 6, "c": c, "r_c": float(tasa(c, v0, k_l))}

    # 4. Valor presente: ¿conviene esperar aunque el dinero de mañana valga menos?
    vp = []
    for T in (0, 3, 6, 12):
        vp.append({"meses": T, "vp_secas": valor_presente_esperar(T, v0, k_s),
                   "vp_lluvias": valor_presente_esperar(T, v0, k_l)})
    r["valor_presente"] = vp
    r["delta_mensual"] = math.log(1 + DESCUENTO_ANUAL) / 12

    # 5. Intervalo óptimo del programa preventivo
    k_p = (k_s + k_l) / 2   # 6 meses de secas y 6 de lluvias
    r["k_promedio"] = k_p
    r["intervalo_optimo"] = {"promedio": intervalo_optimo(k_p), "lluvias": intervalo_optimo(k_l),
                             "A_promedio": costo_promedio_ciclo(intervalo_optimo(k_p), k_p),
                             "A_lluvias": costo_promedio_ciclo(intervalo_optimo(k_l), k_l),
                             "A_cada_3_meses": costo_promedio_ciclo(3, k_p),
                             "A_cada_48_meses": costo_promedio_ciclo(48, k_p)}

    # 6. Año completo integrando por tramos (empieza en enero)
    total_anual, det = perdida_anual_estacional(v0, k_s, k_l)
    pd.DataFrame(det).to_csv(SALIDA / "t3_anual_por_tramos.csv", index=False, encoding="utf-8-sig")
    r["anual_por_tramos"] = {"perdida_m3": total_anual, "volumen_final_m3": v0 + total_anual,
                             "costo_enero": costo_reparar(0, v0, k_s),
                             "costo_diciembre": costo_reparar(0, v0 + total_anual, k_s)}

    # 7. Cuarta potencia: cuánto más se pierde con más carga (lluvias, 6 meses)
    r["cuarta_potencia"] = [{"w_rel": w, "phi": phi(w), "perdida_6m": perdida(6, v0, k_l, w)}
                            for w in (1.0, 1.1, 1.2, 1.3, 1.5)]

    # 8. Aplicación a los baches reales de la base: costo de esperar por territorio
    # Cada bache con su propia profundidad y la tarifa que le recomendó SIPA
    filas_b = list(zip(baches["v0_m3"], baches["profundidad_cm"], baches["clave_tarifa"]))
    baches["costo_hoy"] = [costo_reparar(0, v, k_l, prof_cm=d, tarifa=t) for v, d, t in filas_b]
    for T in (3, 6, 12):
        baches[f"extra_{T}m"] = [costo_reparar(T, v, k_l, prof_cm=d, tarifa=t) - c0
                                 for (v, d, t), c0 in zip(filas_b, baches["costo_hoy"])]
    r["coincide_con_base"] = float((baches["costo_hoy"] - baches["costo_estimado"]).abs().max())
    por_terr = (baches.groupby("territorio")
                .agg(baches=("id_bache", "count"), volumen_m3=("v0_m3", "sum"), costo_hoy=("costo_hoy", "sum"),
                     extra_3m=("extra_3m", "sum"), extra_6m=("extra_6m", "sum"), extra_12m=("extra_12m", "sum"))
                .sort_values("extra_6m", ascending=False).reset_index())
    por_terr.to_csv(SALIDA / "t4_costo_esperar_por_territorio.csv", index=False, encoding="utf-8-sig")
    baches.to_csv(SALIDA / "t5_baches_detalle.csv", index=False, encoding="utf-8-sig")
    r["total_baches"] = {"costo_hoy": float(baches["costo_hoy"].sum()),
                         "extra_3m": float(baches["extra_3m"].sum()),
                         "extra_6m": float(baches["extra_6m"].sum()),
                         "extra_12m": float(baches["extra_12m"].sum()),
                         "toneladas_hoy": float(baches["v0_m3"].sum() * DENSIDAD * DESPERDICIO),
                         "toneladas_6m": float(sum(v + perdida(6, v, k_l) for v in baches["v0_m3"]) * DENSIDAD * DESPERDICIO)}
    chalco = por_terr[por_terr["territorio"] == "CHALCO"]
    r["chalco"] = chalco.iloc[0].to_dict() if len(chalco) else None

    graficas(k_s, k_l, v0, r)
    (SALIDA / "resumen.json").write_text(json.dumps(r, indent=2, ensure_ascii=False, default=float), encoding="utf-8")

    print(f"Factor de lluvias (datos CDMX): {factor:.3f}  ->  k_secas = {k_s:.3f}, k_lluvias = {k_l:.3f}")
    print(f"Bache típico: {area:.2f} m2 × {prof:.1f} cm = {v0:.4f} m3   |   tarifa {TARIFA_TIPICA}: ${COSTO_M3:,.0f}/m3")
    print(f"Diferencia máxima con costo_estimado de la base: ${r['coincide_con_base']:.2f}")
    print(f"Pérdida en 6 meses de lluvias: {exacto:.4f} m3  (Riemann punto medio n=6: {rie[1]['punto medio']:.4f})")
    print(f"Valor medio: r promedio = {exacto/6:.4f} m3/mes, alcanzado en c = {c:.2f} meses")
    print(f"Intervalo óptimo preventivo: promedio anual {r['intervalo_optimo']['promedio']:.1f} m, lluvias {r['intervalo_optimo']['lluvias']:.1f} m")
    print(f"{len(baches)} baches pendientes: hoy ${r['total_baches']['costo_hoy']:,.0f}; esperar 6 meses de lluvias cuesta ${r['total_baches']['extra_6m']:,.0f} más")
    print(f"Resultados en {SALIDA}/")


if __name__ == "__main__":
    main()
