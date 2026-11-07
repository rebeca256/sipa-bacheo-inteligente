"""
SIPA · Estructuras de Datos
Experimentos para el plan de viabilidad y la propuesta de intervenciones (2º producto):
  1. Equidad: el max-heap puro deja esperando a las alcaldías con baches de IPU bajo.
     Se comparan FIFO, SIPA (β = 0.10), SIPA con envejecimiento fuerte (β = 0.30) y
     SIPA con cupo de antigüedad (un segundo max-heap ordenado por días de espera).
  2. Recursos: ¿cuántas reparaciones al día hacen falta para que la cola no crezca?
     Llegadas reales por temporada y barrido de capacidad.
  3. Catálogo: celdas con reincidencia (candidatas a reencarpetado, no a bacheo) y
     resumen por alcaldía, a partir de la desduplicación de toda la base.

Uso (desde la carpeta del proyecto):
    python estructuras/viabilidad.py
Genera en estructuras/resultados/: v*.csv, v*.png y viabilidad.json.

Desarrollado con apoyo de IA generativa (Claude, de Anthropic), con autorización de la
docente y crédito declarado. El equipo revisó, probó y es responsable del código.
"""

import json
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib                                  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt                    # noqa: E402

import modelos                                     # noqa: E402
from experimentos import SALIDA, escribir_csv, metricas   # noqa: E402
from heap import ColaFIFO, MaxHeap                 # noqa: E402
from sipa_ed import SistemaSIPA, leer_reportes, leer_riesgo  # noqa: E402
from tabla_hash import TablaHash                   # noqa: E402

INICIO = date(2019, 7, 1)            # temporada de lluvias completa
DIAS = 90
CAPACIDAD = 15                       # la misma del experimento de 30 días
CUPO_ANTIGUEDAD = 4                  # de cada 15 lugares, 4 van al bache que más ha esperado

# Supuestos de recursos (declarados en el documento)
BACHES_POR_BRIGADA_DIA = 6
# Bache típico de Cálculo (calculo/degradacion.py, mismas tarifas que la base SIPA)
_CALC = json.loads(Path("calculo/resultados/resumen.json").read_text(encoding="utf-8"))
_LLUVIAS = {x["meses"]: x for x in _CALC["tabla_perdida"] if x["temporada"] == "Lluvias"}
TONELADAS_POR_BACHE = round(_LLUVIAS[0]["toneladas"], 3)
COSTO_POR_BACHE = round(_LLUVIAS[0]["costo"])       # reparado a tiempo
COSTO_POR_BACHE_6M = round(_LLUVIAS[6]["costo"])    # tras 6 meses de lluvias


# ---------------------------------------------------------------------------
# 1. Simulación con variantes de la política
# ---------------------------------------------------------------------------

def simular(reportes, riesgo, politica, capacidad=CAPACIDAD, beta=0.10, cupo=0,
            inicio=INICIO, dias=DIAS):
    """politica: "FIFO" o "SIPA". Con cupo > 0, esos lugares del día se toman del heap de antigüedad."""
    modelos.BETA = beta
    s = SistemaSIPA(riesgo=riesgo)
    fifo = ColaFIFO()
    antiguedad = MaxHeap()           # prioridad = −fecha: el más viejo queda arriba
    llegadas = [r for r in reportes if inicio <= r.fecha < inicio + timedelta(days=dias)]
    i = 0
    for d in range(dias):
        hoy = inicio + timedelta(days=d)
        while i < len(llegadas) and llegadas[i].fecha == hoy:
            bache, tipo = s.registrar(llegadas[i], usar_heap=(politica == "SIPA"))
            if tipo != "DUPLICADO":
                if politica == "FIFO":
                    fifo.encolar(bache)
                elif cupo:
                    antiguedad.insertar(bache.id, -bache.fecha_primer_reporte.toordinal())
            i += 1

        if politica == "FIFO":
            plan = [fifo.desencolar() for _ in range(min(capacidad, len(fifo)))]
        else:
            s.envejecer(hoy)
            plan = []
            # Primero la prioridad (rojos y amarillos nunca pierden su lugar), luego el cupo
            while len(plan) < capacidad - cupo and len(s.heap):
                b = s.baches.buscar(s.heap.extraer_max()[2])
                if b.estado == "PENDIENTE":          # eliminación perezosa
                    b.reparar(hoy); plan.append(b)
            while len(plan) < capacidad and len(antiguedad):
                b = s.baches.buscar(antiguedad.extraer_max()[2])
                if b.estado == "PENDIENTE":
                    b.reparar(hoy); plan.append(b)
            while len(plan) < capacidad and len(s.heap):   # si sobró cupo
                b = s.baches.buscar(s.heap.extraer_max()[2])
                if b.estado == "PENDIENTE":
                    b.reparar(hoy); plan.append(b)
        for b in plan:
            b.reparar(hoy)
    modelos.BETA = 0.10
    baches = s.lista_baches
    fin = inicio + timedelta(days=dias)
    m = metricas(baches, fin)
    m["pendientes_al_final"] = sum(b.estado == "PENDIENTE" for b in baches)
    m["llegadas_por_dia"] = round(len(baches) / dias, 1)
    esperas = sorted(((b.fecha_reparacion or fin) - b.fecha_primer_reporte).days for b in baches)
    m["espera_p90"] = esperas[int(0.9 * (len(esperas) - 1))]
    return m


VARIANTES = [
    ("FIFO", dict(politica="FIFO")),
    ("SIPA β=0.10", dict(politica="SIPA", beta=0.10)),
    ("SIPA β=0.30", dict(politica="SIPA", beta=0.30)),
    ("SIPA + cupo", dict(politica="SIPA", beta=0.10, cupo=CUPO_ANTIGUEDAD)),
]


# ---------------------------------------------------------------------------
# 2. Llegadas por temporada (toda la base, ya desduplicada)
# ---------------------------------------------------------------------------

def desduplicar_todo(reportes, riesgo):
    s = SistemaSIPA(riesgo=riesgo)
    for r in reportes:
        s.registrar(r, usar_heap=False)
    return s


def llegadas_por_temporada(s):
    dias = {"lluvias": set(), "secas": set()}
    baches = {"lluvias": 0, "secas": 0}
    for b in s.lista_baches:
        t = "lluvias" if 6 <= b.fecha_primer_reporte.month <= 10 else "secas"
        baches[t] += 1
        dias[t].add(b.fecha_primer_reporte)
    return {t: round(baches[t] / len(dias[t]), 1) for t in baches}


# ---------------------------------------------------------------------------
# 3. Catálogo: reincidencia por celda y resumen por alcaldía
# ---------------------------------------------------------------------------

def catalogo(s):
    por_celda = TablaHash()
    celdas = []
    for b in s.lista_baches:
        c = por_celda.buscar(b.celda_id)
        if c is None:
            c = dict(celda=b.celda_id, alcaldia=b.alcaldia, baches=0, reincidencias=0,
                     riesgo_72h=b.riesgo_72h, lat=0.0, lon=0.0)
            por_celda.insertar(b.celda_id, c)
            celdas.append(c)
        c["baches"] += 1
        c["reincidencias"] += b.reincidente
        c["lat"] += b.latitud
        c["lon"] += b.longitud
    for c in celdas:
        c["lat"] = round(c["lat"] / c["baches"], 5)
        c["lon"] = round(c["lon"] / c["baches"], 5)
        # Puntaje de reencarpetado: reincidencia (el bacheo no está resolviendo) × riesgo
        c["puntaje"] = round(c["reincidencias"] * (0.5 + c["riesgo_72h"]), 2)
    celdas.sort(key=lambda c: c["puntaje"], reverse=True)

    alcaldias = {}
    for b in s.lista_baches:
        a = alcaldias.setdefault(b.alcaldia, dict(alcaldia=b.alcaldia, baches=0, reincidentes=0,
                                                   rojos=0, riesgo_sum=0.0))
        a["baches"] += 1
        a["reincidentes"] += b.reincidente
        a["rojos"] += b.semaforo() == "ROJO"
        a["riesgo_sum"] += b.riesgo_72h
    filas = []
    for a in alcaldias.values():
        if a["baches"] < 50:
            continue
        filas.append(dict(alcaldia=a["alcaldia"], baches=a["baches"],
                          pct_reincidencia=round(100 * a["reincidentes"] / a["baches"], 1),
                          pct_rojos=round(100 * a["rojos"] / a["baches"], 1),
                          riesgo_72h_medio=round(a["riesgo_sum"] / a["baches"], 3)))
    filas.sort(key=lambda f: f["baches"], reverse=True)
    return celdas, filas


# ---------------------------------------------------------------------------
# Principal
# ---------------------------------------------------------------------------

def main():
    SALIDA.mkdir(exist_ok=True)
    reportes = leer_reportes()
    riesgo = leer_riesgo()

    # 1. Equidad
    equidad = {}
    for nombre, kw in VARIANTES:
        equidad[nombre] = simular(reportes, riesgo, **kw)
        m = equidad[nombre]
        print(f"{nombre:12s} rojos≤3d={m['rojos_en_3_dias']:.0%} espera={m['todos']['espera_promedio']} "
              f"p90={m['espera_p90']} brecha={m['brecha_alcaldias']} pendientes={m['pendientes_al_final']}")
    escribir_csv("v1_equidad_variantes.csv", [
        dict(variante=n, rojos_en_3_dias=m["rojos_en_3_dias"], espera_promedio=m["todos"]["espera_promedio"],
             espera_p90=m["espera_p90"], espera_maxima=m["todos"]["espera_maxima"],
             espera_verdes=m["verdes"]["espera_promedio"], brecha_alcaldias=m["brecha_alcaldias"],
             alcaldia_peor=max(m["espera_por_alcaldia"], key=m["espera_por_alcaldia"].get),
             pendientes_al_final=m["pendientes_al_final"])
        for n, m in equidad.items()])

    # 2. Capacidad necesaria
    s = desduplicar_todo(reportes, riesgo)
    llegadas = llegadas_por_temporada(s)
    barrido = []
    for cap in [15, 20, 25, 30, 35]:
        m = simular(reportes, riesgo, "SIPA", capacidad=cap, cupo=round(cap * CUPO_ANTIGUEDAD / CAPACIDAD))
        barrido.append(dict(capacidad=cap, brigadas=-(-cap // BACHES_POR_BRIGADA_DIA),
                            rojos_en_3_dias=m["rojos_en_3_dias"], espera_promedio=m["todos"]["espera_promedio"],
                            espera_p90=m["espera_p90"], brecha_alcaldias=m["brecha_alcaldias"],
                            pendientes_al_final=m["pendientes_al_final"]))
        print(barrido[-1])
    escribir_csv("v2_capacidad.csv", barrido)
    recursos = []
    for t, tasa in llegadas.items():
        meses = 5 if t == "lluvias" else 7
        recursos.append(dict(temporada=t, meses=meses, baches_por_dia=tasa,
                             brigadas=-(-tasa // BACHES_POR_BRIGADA_DIA),
                             toneladas_mes=round(tasa * 30 * TONELADAS_POR_BACHE, 1),
                             costo_material_mes=round(tasa * 30 * COSTO_POR_BACHE)))
    escribir_csv("v3_recursos_temporada.csv", recursos)

    # 3. Catálogo
    celdas, alcaldias = catalogo(s)
    top = celdas[:15]
    escribir_csv("v4_celdas_reencarpetado.csv", top)
    escribir_csv("v5_alcaldias.csv", alcaldias)
    celdas_reinc = [c for c in celdas if c["reincidencias"] >= 3]

    # Gráficas
    fig, ax = plt.subplots(1, 2, figsize=(10, 4))
    nombres = list(equidad)
    ax[0].bar(nombres, [100 * equidad[n]["rojos_en_3_dias"] for n in nombres], color="#c62828")
    ax[0].set_ylabel("% de rojos atendidos en ≤ 3 días"); ax[0].set_ylim(0, 105)
    ax[1].bar(nombres, [equidad[n]["brecha_alcaldias"] for n in nombres], color="#455a64")
    ax[1].set_ylabel("Brecha de espera entre alcaldías (días)")
    for a in ax:
        a.tick_params(axis="x", rotation=20)
    fig.suptitle(f"Política de atención, julio-septiembre 2019 ({CAPACIDAD} reparaciones/día)")
    fig.tight_layout(); fig.savefig(SALIDA / "v1_equidad.png", dpi=150); plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4))
    caps = [b["capacidad"] for b in barrido]
    ax.plot(caps, [b["pendientes_al_final"] for b in barrido], "o-", label="Baches pendientes al día 90")
    ax.axvline(llegadas["lluvias"], ls="--", color="#c62828", label=f"Llegadas en lluvias ({llegadas['lluvias']}/día)")
    ax.set_xlabel("Reparaciones por día"); ax.set_ylabel("Baches pendientes")
    ax.set_title("Capacidad necesaria para que la cola no crezca"); ax.legend()
    fig.tight_layout(); fig.savefig(SALIDA / "v2_capacidad.png", dpi=150); plt.close(fig)

    resumen = dict(
        parametros=dict(inicio=str(INICIO), dias=DIAS, capacidad=CAPACIDAD, cupo=CUPO_ANTIGUEDAD,
                        baches_por_brigada_dia=BACHES_POR_BRIGADA_DIA),
        equidad=equidad, llegadas_por_dia=llegadas, capacidad=barrido, recursos=recursos,
        celdas_total=len(celdas), celdas_reincidencia_3=len(celdas_reinc),
        baches_en_celdas_reincidencia_3=sum(c["baches"] for c in celdas_reinc),
        baches_total=len(s.lista_baches), top_celdas=top, alcaldias=alcaldias)
    with open(SALIDA / "viabilidad.json", "w", encoding="utf-8") as f:
        json.dump(resumen, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
