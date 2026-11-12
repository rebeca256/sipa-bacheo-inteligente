"""
SIPA - Estructuras de Datos con baches reales de Toluca (74,319 registros).

Prueba de escala de las estructuras programadas desde cero:
  1. Tabla hash (clave = folio): inserción, factor de carga, cubeta más larga y búsqueda
     frente a búsqueda lineal en una lista.
  2. Árbol AVL (clave = fecha, folio): altura frente a log2(n) y consulta por rango de fechas.
  3. Max-heap: orden de atención por tipo (profundo primero) y antigüedad; se compara la
     construcción con n inserciones frente a ordenar la lista completa.
Requiere: python scripts/limpiar_toluca.py
Uso:  python estructuras/toluca_ed.py
Salida: estructuras/resultados/toluca_ed.json
"""
import json
import math
import random
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from avl import ArbolAVL  # noqa: E402
from heap import MaxHeap  # noqa: E402
from tabla_hash import TablaHash  # noqa: E402

SAL = Path("estructuras/resultados")


def cron(f):
    t = time.perf_counter()
    r = f()
    return r, time.perf_counter() - t


def main():
    b = pd.read_csv("datos/limpios/toluca_baches.csv", dtype=str)
    regs = b.to_dict("records")
    n = len(regs)
    random.seed(2026)
    consultas = random.sample([r["folio"] for r in regs], 1000)
    r = {"n": n}

    th = TablaHash()
    _, t_ins = cron(lambda: [th.insertar(x["folio"], x) for x in regs])
    _, t_busca = cron(lambda: [th.buscar(f) for f in consultas])
    lista = regs
    _, t_lineal = cron(lambda: [next(x for x in lista if x["folio"] == f) for f in consultas[:200]])
    r["hash"] = dict(segundos_insertar=round(t_ins, 3), factor_carga=round(th.factor_carga(), 3),
                     cubeta_mas_larga=th.cubeta_mas_larga(),
                     us_por_busqueda_hash=round(t_busca / 1000 * 1e6, 2),
                     us_por_busqueda_lista=round(t_lineal / 200 * 1e6, 1))
    r["hash"]["veces_mas_rapida"] = round(r["hash"]["us_por_busqueda_lista"] / r["hash"]["us_por_busqueda_hash"])

    avl = ArbolAVL()
    _, t_avl = cron(lambda: [avl.insertar((x["fecha"], x["folio"]), x["tipo"]) for x in regs])
    rango, t_rango = cron(lambda: avl.rango(("2025-07-01", ""), ("2025-09-30", "~")))
    r["avl"] = dict(segundos_insertar=round(t_avl, 3), altura=avl.altura(), log2n=round(math.log2(n), 2),
                    limite_avl=round(1.44 * math.log2(n + 2), 1), balanceado=avl.esta_balanceado(),
                    baches_lluvias_2025=len(rango), ms_consulta_rango=round(t_rango * 1000, 2))

    def prioridad(x):
        return 2 if x["tipo"] == "PROFUNDO" else 1

    hp = MaxHeap()
    _, t_heap = cron(lambda: [hp.insertar(x["folio"], prioridad(x), -int(x["fecha"].replace("-", "")))
                              for x in regs])
    primeros = [hp.extraer_max() for _ in range(10)]
    _, t_ord = cron(lambda: sorted(regs, key=lambda x: (prioridad(x), -int(x["fecha"].replace("-", ""))),
                                   reverse=True))
    r["heap"] = dict(segundos_insertar=round(t_heap, 3), valido=hp.es_valido(),
                     segundos_sorted_python=round(t_ord, 3),
                     primeros=[dict(folio=p[2], prioridad=p[0], fecha=str(-int(p[1]))) for p in primeros[:3]])
    (SAL / "toluca_ed.json").write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(r, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
