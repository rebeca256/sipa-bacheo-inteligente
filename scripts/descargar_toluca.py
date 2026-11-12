"""
SIPA - Descarga los datos públicos del tablero de bacheo de Toluca (Dirección General de Obras Públicas).
Fuente: https://dgop.toluca.gob.mx/tablero_bacheo_filtros1.php

1. Tabla completa (ajax/buscar_tablero_bacheo.php, paginada): folio, tipo, calle, colonia,
   delegación, estatus, fecha y coordenadas de cada bache.
2. Medidas (ws/obtenerMarker.php): largo, ancho y m² para una muestra aleatoria de folios.

Hace una petición a la vez con pausa, para no cargar el servidor del municipio. Se puede
interrumpir y volver a ejecutar: continúa donde se quedó.

Uso:  python scripts/descargar_toluca.py [--muestra 1500]
Salida: datos/toluca/bacheo_toluca.csv, datos/toluca/medidas_muestra.csv
"""
import argparse
import csv
import html
import json
import random
import re
import time
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

BASE = "https://dgop.toluca.gob.mx/"
OUT = Path("datos/toluca")
PAGINAS = OUT / "paginas"
PAUSA = 0.4
UA = {"User-Agent": "Mozilla/5.0 (proyecto academico UNRC)"}

FILA = re.compile(r"<tr class=\"pointer-cursor\".*?</tr>", re.S)
CELDA = re.compile(r"<td[^>]*>(.*?)</td>", re.S)


def get(url, post=False, intentos=4):
    for i in range(intentos):
        try:
            req = Request(url, headers=UA, method="POST" if post else "GET")
            with urlopen(req, timeout=60) as r:
                return r.read().decode("utf-8", errors="replace")
        except Exception as e:  # noqa: BLE001
            if i == intentos - 1:
                raise
            time.sleep(3 * (i + 1))


def url_pagina(p):
    return (BASE + f"ajax/buscar_tablero_bacheo.php?action=ajax&page={p}&q=&fi=2000-01-01&ff=2030-12-31"
            "&tipoBacheo=0&mesBacheo=0&idBacheo=0&idEtapa=99&idAnio=0&idMes=0")


def limpiar(x):
    return html.unescape(re.sub(r"<[^>]+>", "", x)).strip()


def parsear(t):
    filas = []
    for tr in FILA.findall(t):
        c = CELDA.findall(tr)
        idm = re.search(r"obtenerInformacion\((\d+)\)", tr)
        ll = re.search(r"q=(-?[\d.]+),(-?[\d.]+)", tr)
        txt = [limpiar(x) for x in c]
        filas.append(dict(id=idm.group(1) if idm else "", folio=txt[0], tipo=txt[1], calle=txt[2], cp=txt[3],
                          colonia=txt[4], delegacion=txt[5], estatus=txt[9], fecha=txt[10],
                          lat=ll.group(1) if ll else "", lng=ll.group(2) if ll else ""))
    return filas


def tabla():
    PAGINAS.mkdir(parents=True, exist_ok=True)
    primera = get(url_pagina(1))
    total = max(int(x) for x in re.findall(r"load\((\d+)", primera) or ["1"])
    print("páginas:", total, flush=True)
    for p in range(1, total + 1):
        f = PAGINAS / f"{p:05d}.json"
        if f.exists():
            continue
        t = primera if p == 1 else get(url_pagina(p))
        f.write_text(json.dumps(parsear(t), ensure_ascii=False), encoding="utf-8")
        if p % 100 == 0:
            print(p, flush=True)
        time.sleep(PAUSA)
    filas = [r for f in sorted(PAGINAS.glob("*.json")) for r in json.loads(f.read_text(encoding="utf-8"))]
    vistos, unicos = set(), []
    for r in filas:
        k = (r["id"], r["folio"])
        if k not in vistos:
            vistos.add(k)
            unicos.append(r)
    with open(OUT / "bacheo_toluca.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(unicos[0]))
        w.writeheader()
        w.writerows(unicos)
    print("filas:", len(unicos), flush=True)
    return unicos


def medidas(filas, n):
    salida = OUT / "medidas_muestra.csv"
    hechos = set()
    if salida.exists():
        with open(salida, encoding="utf-8") as fh:
            hechos = {r["folio"] for r in csv.DictReader(fh)}
    random.seed(2026)
    folios = [r["folio"] for r in filas if r["estatus"] == "Terminado" and r["folio"]]
    muestra = [f for f in random.sample(folios, min(n, len(folios))) if f not in hechos]
    campos = ["folio", "tipo", "largo", "ancho", "profundidad", "m2Total", "date_added", "delegacion", "colonia"]
    nuevo = not salida.exists()
    with open(salida, "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=campos, extrasaction="ignore")
        if nuevo:
            w.writeheader()
        for i, f in enumerate(muestra, 1):
            try:
                d = json.loads(get(BASE + "ws/obtenerMarker.php?folio=" + quote(f), post=True))
            except Exception:  # noqa: BLE001
                continue
            if d:
                w.writerow(d[0])
            if i % 100 == 0:
                print("medidas", i, flush=True)
                fh.flush()
            time.sleep(PAUSA)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--muestra", type=int, default=1500)
    a = ap.parse_args()
    medidas(tabla(), a.muestra)
