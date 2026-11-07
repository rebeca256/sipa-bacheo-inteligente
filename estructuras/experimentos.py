"""
SIPA · Estructuras de Datos
Experimentos con los datos reales (sección 11 del avance):
  1. Eficiencia: búsqueda lineal vs. tabla hash vs. árbol AVL con 1,000, 10,000 y todos los registros.
  2. Desduplicación de la base completa con la tabla hash.
  3. Simulación de 30 días: atención FIFO vs. SIPA (max-heap con envejecimiento).
  4. Rutas: Dijkstra y vecino más cercano para el plan del día de una brigada.

Uso (desde la carpeta del proyecto):
    python estructuras/experimentos.py
Genera en estructuras/resultados/: tablas CSV, gráficas y resumen.json.

Desarrollado con apoyo de IA generativa (Claude, de Anthropic), con autorización de la
docente y crédito declarado. El equipo revisó, probó y es responsable del código.
"""

import csv
import json
import math
import random
import sys
import time
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib                                  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt                    # noqa: E402

from avl import ArbolAVL                           # noqa: E402
from grafo import grafo_de_celdas, distancia_m     # noqa: E402
from heap import ColaFIFO                          # noqa: E402
from modelos import Brigada                        # noqa: E402
from sipa_ed import SistemaSIPA, leer_reportes, leer_riesgo  # noqa: E402
from tabla_hash import TablaHash                   # noqa: E402

SALIDA = Path(__file__).resolve().parent / "resultados"

# Simulación
INICIO_SIM = date(2019, 7, 1)        # temporada de lluvias
DIAS_SIM = 30
CAPACIDAD_DIARIA = 15                # baches que reparan las brigadas por día

# Rutas: planta de asfalto de la CDMX en Coyoacán (ubicación aproximada)
ALCALDIA_RUTA = "COYOACAN"
PLANTA = (19.3070, -99.1690)
BACHES_EN_RUTA = 8


def escribir_csv(nombre, filas):
    with open(SALIDA / nombre, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0].keys()))
        w.writeheader()
        w.writerows(filas)


# ---------------------------------------------------------------------------
# 1. Eficiencia de la búsqueda
# ---------------------------------------------------------------------------

def medir_busquedas(reportes, tamanos, consultas=300, semilla=1):
    azar = random.Random(semilla)
    filas = []
    for n in tamanos:
        claves = [r.clave_celda() for r in reportes[:n]]
        lista = list(claves)
        tabla, arbol = TablaHash(), ArbolAVL()
        for k in claves:
            tabla.insertar(k, True)
            arbol.insertar(k, True)
        muestra = [azar.choice(claves) for _ in range(consultas)]

        t0 = time.perf_counter()
        comp_lineal = 0
        for k in muestra:                          # búsqueda lineal: recorre hasta encontrarla
            for i, x in enumerate(lista):
                if x == k:
                    comp_lineal += i + 1
                    break
        t_lineal = time.perf_counter() - t0

        t0 = time.perf_counter()
        for k in muestra:
            tabla.buscar(k)
        t_hash = time.perf_counter() - t0

        arbol.comparaciones = 0
        t0 = time.perf_counter()
        for k in muestra:
            arbol.buscar(k)
        t_avl = time.perf_counter() - t0

        filas.append(dict(
            n=n, claves_distintas=len(tabla),
            us_lineal=round(t_lineal / consultas * 1e6, 2),
            us_hash=round(t_hash / consultas * 1e6, 2),
            us_avl=round(t_avl / consultas * 1e6, 2),
            comparaciones_lineal=round(comp_lineal / consultas, 1),
            comparaciones_avl=round(arbol.comparaciones / consultas, 1),
            altura_avl=arbol.altura(), cota_avl=round(1.44 * math.log2(len(arbol) + 2), 1),
            cubeta_mas_larga=tabla.cubeta_mas_larga(), factor_carga=round(tabla.factor_carga(), 3),
        ))
    return filas


def medir_desduplicacion_total(reportes, riesgo):
    """Desduplica todos los reportes: tabla hash (9 búsquedas por reporte) contra comparación por pares."""
    s = SistemaSIPA(riesgo=riesgo)
    t0 = time.perf_counter()
    tipos = {"NUEVO": 0, "DUPLICADO": 0, "REINCIDENCIA": 0}
    for r in reportes:
        _, tipo = s.registrar(r, usar_heap=False)
        tipos[tipo] += 1
    t_hash = time.perf_counter() - t0
    n = len(reportes)
    return dict(reportes=n, baches=len(s.lista_baches), duplicados=tipos["DUPLICADO"],
                reincidencias=tipos["REINCIDENCIA"], segundos_hash=round(t_hash, 2),
                busquedas_hash=9 * n, comparaciones_por_pares=n * (n - 1) // 2)


# ---------------------------------------------------------------------------
# 3. Simulación FIFO vs. SIPA
# ---------------------------------------------------------------------------

def simular(reportes, riesgo, estrategia):
    s = SistemaSIPA(riesgo=riesgo)
    fifo = ColaFIFO()
    llegadas = [r for r in reportes if INICIO_SIM <= r.fecha < INICIO_SIM + timedelta(days=DIAS_SIM)]
    i = 0
    for d in range(DIAS_SIM):
        hoy = INICIO_SIM + timedelta(days=d)
        while i < len(llegadas) and llegadas[i].fecha == hoy:
            bache, tipo = s.registrar(llegadas[i], usar_heap=(estrategia == "SIPA"))
            if tipo != "DUPLICADO" and estrategia == "FIFO":
                fifo.encolar(bache)
            i += 1
        if estrategia == "SIPA":
            s.envejecer(hoy)
            plan = s.plan_del_dia(CAPACIDAD_DIARIA)
        else:
            plan = [fifo.desencolar() for _ in range(min(CAPACIDAD_DIARIA, len(fifo)))]
        for b in plan:
            b.reparar(hoy)
    return s.lista_baches, INICIO_SIM + timedelta(days=DIAS_SIM)


def metricas(baches, fin):
    def espera(b):
        hasta = b.fecha_reparacion if b.fecha_reparacion else fin
        return (hasta - b.fecha_primer_reporte).days

    def resumen(grupo):
        if not grupo:
            return dict(baches=0, reparados=0, espera_promedio=None, espera_maxima=None)
        e = [espera(b) for b in grupo]
        return dict(baches=len(grupo), reparados=sum(b.estado == "REPARADO" for b in grupo),
                    espera_promedio=round(sum(e) / len(e), 1), espera_maxima=max(e))

    rojos = [b for b in baches if b.semaforo() == "ROJO"]
    por_alcaldia = {}
    for b in baches:
        por_alcaldia.setdefault(b.alcaldia, []).append(espera(b))
    medias = {a: sum(v) / len(v) for a, v in por_alcaldia.items() if len(v) >= 5}
    return dict(
        todos=resumen(baches), rojos=resumen(rojos),
        amarillos=resumen([b for b in baches if b.semaforo() == "AMARILLO"]),
        verdes=resumen([b for b in baches if b.semaforo() == "VERDE"]),
        rojos_en_3_dias=round(sum(1 for b in rojos if b.fecha_reparacion and espera(b) <= 3) / len(rojos), 3),
        espera_por_alcaldia={a: round(v, 1) for a, v in sorted(medias.items())},
        brecha_alcaldias=round(max(medias.values()) - min(medias.values()), 1),
    )


# ---------------------------------------------------------------------------
# 4. Rutas con Dijkstra
# ---------------------------------------------------------------------------

def rutas(reportes, riesgo):
    """Plan del día en una alcaldía: los 8 baches de mayor prioridad y la ruta de la brigada."""
    s = SistemaSIPA(riesgo=riesgo)
    for r in reportes:
        if r.alcaldia == ALCALDIA_RUTA and INICIO_SIM <= r.fecha < INICIO_SIM + timedelta(days=DIAS_SIM):
            s.registrar(r)
    plan = s.plan_del_dia(BACHES_EN_RUTA)

    # Cuadrícula de celdas de 250 m que cubre la zona (vértices) y sus vecinas (aristas)
    paso_lat = 250 / 111_320
    paso_lon = 250 / (111_320 * math.cos(math.radians(19.3)))
    lats = [b.latitud for b in s.lista_baches] + [PLANTA[0]]
    lons = [b.longitud for b in s.lista_baches] + [PLANTA[1]]
    lat0, lon0 = min(lats) - paso_lat, min(lons) - paso_lon
    filas = int((max(lats) - lat0) / paso_lat) + 2
    cols = int((max(lons) - lon0) / paso_lon) + 2
    celdas = {(f, c): (lat0 + (f + 0.5) * paso_lat, lon0 + (c + 0.5) * paso_lon)
              for f in range(filas) for c in range(cols)}
    g = grafo_de_celdas(celdas)

    def vertice(lat, lon):
        return (int((lat - lat0) / paso_lat), int((lon - lon0) / paso_lon))

    base = vertice(*PLANTA)
    destinos = [vertice(b.latitud, b.longitud) for b in plan]
    alcanzables = g.dfs(base)
    assert all(d in alcanzables for d in destinos), "Hay baches no alcanzables desde la planta"

    brigada = Brigada(1, base, BACHES_EN_RUTA)
    brigada.asignar(g, destinos)

    # Comparación: visitar los mismos baches en el orden en que salieron del heap (sin optimizar ruta)
    metros_orden_heap, actual = 0.0, base
    for d in destinos:
        dist, _ = g.dijkstra(actual)
        metros_orden_heap += dist[d]
        actual = d
    dist_planta, _ = g.dijkstra(base)
    return dict(
        alcaldia=ALCALDIA_RUTA, vertices=len(g), aristas=g.num_aristas(),
        baches_en_plan=len(plan),
        km_vecino_cercano=round(brigada.metros / 1000, 2),
        km_orden_prioridad=round(metros_orden_heap / 1000, 2),
        km_linea_recta_planta_promedio=round(
            sum(distancia_m(*PLANTA, b.latitud, b.longitud) for b in plan) / len(plan) / 1000, 2),
        km_red_planta_promedio=round(sum(dist_planta[d] for d in destinos) / len(destinos) / 1000, 2),
    ), plan, brigada, g, dict(zip(destinos, plan))


# ---------------------------------------------------------------------------
# Gráficas
# ---------------------------------------------------------------------------

def graficas(eficiencia, sim, plan, brigada, g):
    plt.rcParams.update({"font.size": 10})
    n = [f["n"] for f in eficiencia]
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(n, [f["us_lineal"] for f in eficiencia], "o-", label="Búsqueda lineal O(n)")
    ax.plot(n, [f["us_avl"] for f in eficiencia], "s-", label="Árbol AVL O(log n)")
    ax.plot(n, [f["us_hash"] for f in eficiencia], "^-", label="Tabla hash O(1)")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("Registros (escala log)"); ax.set_ylabel("Microsegundos por búsqueda (escala log)")
    ax.set_title("Tiempo de búsqueda de un reporte según la estructura")
    ax.legend()
    fig.tight_layout(); fig.savefig(SALIDA / "g1_eficiencia_busqueda.png", dpi=150); plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4))
    grupos = ["rojos", "amarillos", "verdes", "todos"]
    x = range(len(grupos))
    for j, est in enumerate(["FIFO", "SIPA"]):
        v = [sim[est][g_]["espera_promedio"] for g_ in grupos]
        ax.bar([i + (j - 0.5) * 0.38 for i in x], v, 0.38, label=est)
        for i, val in enumerate(v):
            ax.text(i + (j - 0.5) * 0.38, val + 0.2, f"{val:.1f}", ha="center", fontsize=9)
    ax.set_xticks(list(x), ["Rojos", "Amarillos", "Verdes", "Todos"])
    ax.set_ylabel("Días de espera promedio")
    ax.set_title(f"Simulación de {DIAS_SIM} días: FIFO vs. SIPA ({CAPACIDAD_DIARIA} reparaciones/día)")
    ax.legend()
    fig.tight_layout(); fig.savefig(SALIDA / "g2_fifo_vs_sipa.png", dpi=150); plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 6))
    pts = [g.coordenadas[v] for v in brigada.ruta]
    ax.plot([p[1] for p in pts], [p[0] for p in pts], "-", color="#455a64", lw=1.5, zorder=1)
    ax.scatter(pts[0][1], pts[0][0], s=180, marker="s", color="#1565c0", label="Planta de asfalto", zorder=3)
    colores = {"ROJO": "#c62828", "AMARILLO": "#f9a825", "VERDE": "#2e7d32"}
    for k, v in enumerate(brigada.ruta[1:], start=1):
        lat, lon = g.coordenadas[v]
        ax.scatter(lon, lat, s=120, color=colores[plan[v].semaforo()], edgecolor="k", zorder=3)
        ax.annotate(str(k), (lon, lat), textcoords="offset points", xytext=(6, 6), fontsize=10, fontweight="bold")
    ax.set_xlabel("Longitud"); ax.set_ylabel("Latitud")
    ax.set_title(f"Orden de visita de la brigada en {ALCALDIA_RUTA.title()}\n"
                 "(vecino más cercano; distancias calculadas con Dijkstra sobre el grafo)", fontsize=10)
    ax.legend(loc="best")
    fig.tight_layout(); fig.savefig(SALIDA / "g3_ruta_brigada.png", dpi=150); plt.close(fig)


# ---------------------------------------------------------------------------
# Principal
# ---------------------------------------------------------------------------

def main():
    SALIDA.mkdir(exist_ok=True)
    reportes = leer_reportes()
    riesgo = leer_riesgo()
    print(f"Reportes leídos: {len(reportes):,}")

    eficiencia = medir_busquedas(reportes, [1_000, 10_000, len(reportes)])
    escribir_csv("t1_eficiencia_busqueda.csv", eficiencia)
    desdup = medir_desduplicacion_total(reportes, riesgo)

    sim = {}
    for est in ["FIFO", "SIPA"]:
        baches, fin = simular(reportes, riesgo, est)
        sim[est] = metricas(baches, fin)
    filas = []
    for est in ["FIFO", "SIPA"]:
        for g_ in ["rojos", "amarillos", "verdes", "todos"]:
            filas.append(dict(estrategia=est, grupo=g_, **sim[est][g_]))
    escribir_csv("t2_simulacion_fifo_vs_sipa.csv", filas)
    escribir_csv("t3_espera_por_alcaldia.csv",
                 [dict(alcaldia=a, espera_fifo=sim["FIFO"]["espera_por_alcaldia"][a],
                       espera_sipa=sim["SIPA"]["espera_por_alcaldia"].get(a))
                  for a in sim["FIFO"]["espera_por_alcaldia"]])

    ruta, plan, brigada, g, bache_de_vertice = rutas(reportes, riesgo)
    escribir_csv("t4_plan_y_ruta.csv",
                 [dict(orden_heap=i + 1, id_bache=b.id, ipu=b.ipu, semaforo=b.semaforo(),
                       reportes=b.num_reportes, latitud=b.latitud, longitud=b.longitud)
                  for i, b in enumerate(plan)])
    graficas(eficiencia, sim, bache_de_vertice, brigada, g)

    resumen = dict(eficiencia=eficiencia, desduplicacion=desdup, simulacion=sim, rutas=ruta,
                   parametros=dict(inicio=str(INICIO_SIM), dias=DIAS_SIM, capacidad=CAPACIDAD_DIARIA))
    with open(SALIDA / "resumen.json", "w", encoding="utf-8") as f:
        json.dump(resumen, f, ensure_ascii=False, indent=2)
    print(json.dumps(resumen, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
