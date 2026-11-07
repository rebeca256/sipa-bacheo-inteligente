"""
SIPA - Prepara dos fuentes reales para el IPU (criterios TRANSPORTE y VULNERABILIDAD).

Entradas (ver FUENTE.md de cada carpeta):
    datos/gtfs/originales/gtfs.zip                         GTFS CDMX (SEMOVI)
    datos/marginacion/originales/im_colonia_cdmx.geojson   IMU 2020 por colonia (CONAPO, vía SIEG CDMX)
Salidas:
    datos/gtfs/limpios/paradas.csv
        stop_id, nombre, modo, latitud, longitud, rutas, salidas_dia
        salidas_dia = vehículos que pasan por la parada en un día típico, según
        frequencies.txt: (fin - inicio) / intervalo de cada viaje, sumado.
    datos/marginacion/limpios/colonias_marginacion.csv
        id_col, colonia, alcaldia, cp, im_2020, grado, imn_2020, wkt
Uso (desde la carpeta del proyecto):
    python scripts/procesar_fuentes_ipu.py
"""
import csv
import json
import zipfile
from pathlib import Path

import pandas as pd

GTFS = Path("datos/gtfs/originales/gtfs.zip")
MARG = Path("datos/marginacion/originales/im_colonia_cdmx.geojson")
SAL_GTFS = Path("datos/gtfs/limpios/paradas.csv")
SAL_MARG = Path("datos/marginacion/limpios/colonias_marginacion.csv")

MODOS = {"METRO": "METRO", "MB": "METROBUS", "TROLE": "TROLEBUS", "SEMOVI": "TROLEBUS", "RTP": "RTP",
         "CC": "CONCESIONADO", "TL": "TREN_LIGERO", "CBB": "CABLEBUS", "SUB": "SUBURBANO",
         "INTERURBANO": "INTERURBANO", "PUMABUS": "PUMABUS"}


def segundos(hhmmss):
    h, m, s = (int(x) for x in str(hhmmss).split(":"))
    return h * 3600 + m * 60 + s


def leer(z, nombre):
    return pd.read_csv(z.open(nombre), dtype=str, encoding="utf-8")


def paradas():
    z = zipfile.ZipFile(GTFS)
    routes, trips = leer(z, "routes.txt"), leer(z, "trips.txt")
    freq, st, stops = leer(z, "frequencies.txt"), leer(z, "stop_times.txt"), leer(z, "stops.txt")

    # Salidas por día de cada viaje modelo
    freq["salidas"] = [max(0, (segundos(f) - segundos(i))) / int(h)
                       for i, f, h in zip(freq.start_time, freq.end_time, freq.headway_secs)]
    por_viaje = freq.groupby("trip_id")["salidas"].sum()
    trips["salidas"] = trips.trip_id.map(por_viaje).fillna(1.0)   # viaje sin frecuencia = 1 salida
    trips = trips.merge(routes[["route_id", "agency_id"]], on="route_id", how="left")

    # Cada parada: suma de salidas de los viajes que la tocan (una vez por viaje)
    sv = st[["trip_id", "stop_id"]].drop_duplicates().merge(
        trips[["trip_id", "route_id", "agency_id", "salidas"]], on="trip_id")
    agg = sv.groupby("stop_id").agg(rutas=("route_id", "nunique"), salidas_dia=("salidas", "sum"),
                                    agencia=("agency_id", lambda a: a.mode().iat[0]))
    out = stops.merge(agg, left_on="stop_id", right_index=True)
    out["modo"] = out.agencia.map(MODOS).fillna("OTRO")
    out = out.rename(columns={"stop_name": "nombre", "stop_lat": "latitud", "stop_lon": "longitud"})
    out["salidas_dia"] = out.salidas_dia.round().astype(int)
    out = out[["stop_id", "nombre", "modo", "latitud", "longitud", "rutas", "salidas_dia"]]
    SAL_GTFS.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(SAL_GTFS, index=False, encoding="utf-8")
    sin = len(stops) - len(out)
    print(f"Paradas: {len(out):,} con servicio ({sin} sin viajes, descartadas) -> {SAL_GTFS}")
    print(out.groupby("modo").agg(paradas=("stop_id", "size"), salidas=("salidas_dia", "sum")).to_string())


def anillo(coords):
    return "(" + ", ".join(f"{x:.6f} {y:.6f}" for x, y in coords) + ")"


def wkt(geom):
    if geom["type"] == "Polygon":
        return "POLYGON(" + ", ".join(anillo(r) for r in geom["coordinates"]) + ")"
    return "MULTIPOLYGON(" + ", ".join("(" + ", ".join(anillo(r) for r in p) + ")"
                                       for p in geom["coordinates"]) + ")"


def colonias():
    d = json.load(MARG.open(encoding="utf-8"))
    SAL_MARG.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with SAL_MARG.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id_col", "colonia", "alcaldia", "cp", "im_2020", "grado", "imn_2020", "wkt"])
        for ft in d["features"]:
            p = ft["properties"]
            if ft["geometry"] is None or p["IMN_2020"] is None:
                continue
            w.writerow([p["ID_COL"], p["COLONIA"], p["NOM_MUN"], p["CP"], round(p["IM_2020"], 4),
                        p["GM_2020"], round(p["IMN_2020"], 6), wkt(ft["geometry"])])
            n += 1
    print(f"Colonias con marginación: {n:,} -> {SAL_MARG}")


if __name__ == "__main__":
    paradas()
    colonias()
