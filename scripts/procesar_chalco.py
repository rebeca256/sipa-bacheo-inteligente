"""
SIPA - Sistema Inteligente de Priorización Asfáltica
Preparación de los datos abiertos de Chalco (Estado de México) para cargarlos
en la base SIPA.

Entradas (datos/chalco/originales/, descargadas de datosabiertos.chalco.gob.mx):
    Reportes-Bacheo_2025-2026.csv   reportes de bacheo
    comunidades_bando2026.xlsx      catálogo oficial de comunidades (Bando 2026)
    ESCUELAS_CHALCO.xlsx            escuelas con número de alumnos
    ATLAS_ESTRUCTURA-3.kml          Atlas de Riesgo 2023 (capas geográficas)

Salidas (datos/chalco/limpios/):
    reportes_chalco.csv        reportes válidos, con comunidad oficial y celda
    reportes_excluidos.csv     reportes descartados y el motivo
    comunidades.csv            catálogo de comunidades
    zonas_inundables.csv       polígonos de inundación en WKT (lon lat)
    equipamiento.csv           escuelas, hospitales y mercados con coordenadas
    limite_municipal.csv       polígono del municipio en WKT
    bitacora_chalco.csv        qué se hizo en cada paso

Uso (desde la carpeta del proyecto):
    python scripts/procesar_chalco.py

Igual que en la limpieza de la CDMX, los originales no se modifican y todo lo
corregido o inferido queda marcado en columnas de control.
"""

import math
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from limpiar_base_maestra import METROS_POR_GRADO, Bitacora, asignar_celda, marcar_posibles_duplicados  # noqa: E402

ORIGEN = Path("datos/chalco/originales")
SALIDA = Path("datos/chalco/limpios")
KML_NS = "{http://www.opengis.net/kml/2.2}"

# Nombres de los reportes que no coinciden literalmente con el Bando 2026.
# Se revisaron a mano contra el catálogo oficial.
ALIAS_COMUNIDAD = {
    "BARRIO LA CONCHITA": "LA CONCHITA",
    "BARRIO SAN ANTONIO": "SAN ANTONIO",
    "CHALCO CENTRO": "CENTRO",
    "VILLAS DE SAN MARTIN": "CHALCO VILLAS DE SAN MARTIN",
}

# El polígono municipal del atlas es aproximado: los puntos que quedan fuera,
# pero a menos de esta distancia del límite, se conservan como ubicación dudosa.
TOLERANCIA_LIMITE_M = 1000

# Meses de temporada de lluvias (mismo criterio que en la CDMX).
MESES_LLUVIA = {5, 6, 7, 8, 9, 10}

# Capas del atlas que se usan como equipamiento y su tipo en SIPA.
CAPAS_EQUIPAMIENTO = {"HOSPITALES": "HOSPITAL", "MERCADOS": "MERCADO"}


# ---------------------------------------------------------------------------
# Funciones auxiliares
# ---------------------------------------------------------------------------

def leer_texto_mixto(ruta):
    """El CSV mezcla líneas en UTF-8 y en Windows-1252 (por eso aparecían
    caracteres raros como 'M�XICO'). Se decodifica línea por línea."""
    lineas = []
    for linea in ruta.read_bytes().splitlines():
        try:
            lineas.append(linea.decode("utf-8"))
        except UnicodeDecodeError:
            lineas.append(linea.decode("cp1252"))
    return "\n".join(lineas).lstrip("﻿")


def sin_acentos(texto):
    texto = unicodedata.normalize("NFKD", str(texto))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", texto).strip().upper()


def punto_en_poligono(lon, lat, anillo):
    """Algoritmo de trazado de rayos: cuenta cuántas veces una línea horizontal
    desde el punto cruza los lados del polígono. Impar = adentro."""
    dentro = False
    j = len(anillo) - 1
    for i in range(len(anillo)):
        xi, yi = anillo[i]
        xj, yj = anillo[j]
        if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / (yj - yi) + xi:
            dentro = not dentro
        j = i
    return dentro


def distancia_a_anillo_m(lon, lat, anillo):
    """Distancia aproximada (m) de un punto al lado más cercano del polígono."""
    k = METROS_POR_GRADO * math.cos(math.radians(lat))
    px, py = lon * k, lat * METROS_POR_GRADO
    mejor = float("inf")
    for (x1, y1), (x2, y2) in zip(anillo, anillo[1:] + anillo[:1]):
        ax, ay, bx, by = x1 * k, y1 * METROS_POR_GRADO, x2 * k, y2 * METROS_POR_GRADO
        dx, dy = bx - ax, by - ay
        t = 0 if dx == dy == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
        mejor = min(mejor, math.hypot(px - (ax + t * dx), py - (ay + t * dy)))
    return mejor


def coordenadas(elemento):
    """Lee el texto <coordinates> de KML como lista de (lon, lat)."""
    texto = elemento.find(f".//{KML_NS}coordinates").text.split()
    return [tuple(float(v) for v in par.split(",")[:2]) for par in texto]


def anillo_a_wkt(anillo):
    if anillo[0] != anillo[-1]:
        anillo = anillo + [anillo[0]]
    return "POLYGON((" + ", ".join(f"{lon:.7f} {lat:.7f}" for lon, lat in anillo) + "))"


def capas_kml(ruta):
    """Devuelve {nombre_de_capa: [Placemark, ...]} con las capas que tienen datos."""
    raiz = ET.parse(ruta).getroot()
    capas = {}
    for carpeta in raiz.iter(f"{KML_NS}Folder"):
        marcas = carpeta.findall(f"{KML_NS}Placemark")
        if marcas:
            capas[carpeta.find(f"{KML_NS}name").text] = marcas
    return capas


# ---------------------------------------------------------------------------
# Procesamiento
# ---------------------------------------------------------------------------

def procesar():
    SALIDA.mkdir(parents=True, exist_ok=True)
    bit = Bitacora()

    # --- Catálogo de comunidades -----------------------------------------
    com = pd.read_excel(ORIGEN / "comunidades_bando2026.xlsx")
    com["NOMBRE"] = com["NOMBRE"].map(sin_acentos)
    com = com.rename(columns={"UT": "clave_ut", "NOMBRE": "nombre", "TIPO": "tipo"})
    com.to_csv(SALIDA / "comunidades.csv", index=False, encoding="utf-8-sig")
    bit.registrar("C1", "Comunidades oficiales (Bando 2026)", len(com))

    # --- Atlas de Riesgo: límite municipal, inundaciones, equipamiento ----
    capas = capas_kml(ORIGEN / "ATLAS_ESTRUCTURA-3.kml")

    limite = max((coordenadas(p) for p in capas["LIMITE MUNICIPAL"]
                  for p in p.iter(f"{KML_NS}Polygon")), key=len)
    pd.DataFrame([{"nombre": "CHALCO", "wkt": anillo_a_wkt(limite)}]).to_csv(
        SALIDA / "limite_municipal.csv", index=False, encoding="utf-8-sig")

    zonas = [{"clave": p.find(f"{KML_NS}name").text, "wkt": anillo_a_wkt(coordenadas(pol))}
             for p in capas["INUNDACIONES"] for pol in p.iter(f"{KML_NS}Polygon")]
    pd.DataFrame(zonas).to_csv(SALIDA / "zonas_inundables.csv", index=False, encoding="utf-8-sig")
    bit.registrar("A1", "Polígonos de zonas inundables (Atlas de Riesgo 2023)", len(zonas))

    equip = []
    for capa, tipo in CAPAS_EQUIPAMIENTO.items():
        for p in capas[capa]:
            puntos = coordenadas(p)                      # punto o polígono: se usa el centro
            lon = sum(x for x, _ in puntos) / len(puntos)
            lat = sum(y for _, y in puntos) / len(puntos)
            equip.append({"tipo": tipo, "nombre": p.find(f"{KML_NS}name").text,
                          "latitud": round(lat, 6), "longitud": round(lon, 6),
                          "personas": None, "fuente": "ATLAS_RIESGO_2023"})
    bit.registrar("A2", "Hospitales y mercados del atlas", len(equip))

    # Escuelas: se usa el catálogo porque trae el número de alumnos
    esc = pd.read_excel(ORIGEN / "ESCUELAS_CHALCO.xlsx")
    esc = esc.dropna(subset=["latitud", "longitud"])
    for _, e in esc.iterrows():
        equip.append({"tipo": "ESCUELA", "nombre": sin_acentos(e["Nombre del centro de trabajo"]),
                      "latitud": round(e["latitud"], 6), "longitud": round(e["longitud"], 6),
                      "personas": int(e["Alumnos total"]) if pd.notna(e["Alumnos total"]) else None,
                      "fuente": "CATALOGO_ESCUELAS"})
    bit.registrar("A3", "Escuelas con coordenadas (catálogo municipal)", len(esc))
    equip = pd.DataFrame(equip)
    equip["personas"] = equip["personas"].astype("Int64")
    equip.to_csv(SALIDA / "equipamiento.csv", index=False, encoding="utf-8-sig")

    # --- Reportes de bacheo ----------------------------------------------
    from io import StringIO
    df = pd.read_csv(StringIO(leer_texto_mixto(ORIGEN / "Reportes-Bacheo_2025-2026.csv")), dtype=str)
    df.columns = ["id", "folio", "comunidad", "latitud", "longitud", "estatus", "origen", "fecha_alta"]
    bit.registrar("R1", "Reportes leídos", len(df))

    excluidos = []

    def excluir(mascara, motivo):
        nonlocal df
        excluidos.append(df[mascara].assign(motivo=motivo))
        df = df[~mascara].copy()
        bit.registrar("R-X", f"Excluidos: {motivo}", mascara.sum())

    df["latitud"] = pd.to_numeric(df["latitud"], errors="coerce")
    df["longitud"] = pd.to_numeric(df["longitud"], errors="coerce")
    excluir(df["latitud"].isna() | df["longitud"].isna(), "sin coordenadas")

    dist = df.apply(lambda r: 0.0 if punto_en_poligono(r["longitud"], r["latitud"], limite)
                    else distancia_a_anillo_m(r["longitud"], r["latitud"], limite), axis=1)
    excluir(dist > TOLERANCIA_LIMITE_M, f"a más de {TOLERANCIA_LIMITE_M} m del límite municipal de Chalco")
    df["ubicacion_dudosa"] = dist[df.index] > 0
    bit.registrar("R1b", "Fuera del polígono pero cerca del límite (ubicación dudosa)", df["ubicacion_dudosa"].sum())

    # Comunidad: acentos, parte entre paréntesis (subcomunidad) y alias revisados
    df["comunidad_original"] = df["comunidad"]
    base = df["comunidad"].map(sin_acentos).str.replace(r"\s*\(.*\)$", "", regex=True)
    df["comunidad"] = base.replace(ALIAS_COMUNIDAD)
    oficiales = set(com["nombre"])
    df["comunidad_corregida"] = df["comunidad"] != df["comunidad_original"].map(sin_acentos)
    bit.registrar("R2", "Comunidades corregidas (acentos, paréntesis o alias)", df["comunidad_corregida"].sum())
    sin_match = ~df["comunidad"].isin(oficiales)
    bit.registrar("R3", "Comunidades que no están en el Bando 2026 (se conservan)", sin_match.sum())

    df["fecha_solicitud"] = pd.to_datetime(df["fecha_alta"], format="%d/%m/%Y %H:%M")
    df["temporada_lluvias"] = df["fecha_solicitud"].dt.month.isin(MESES_LLUVIA)
    df["estatus"] = df["estatus"].str.strip().str.upper()

    # Mismas reglas que en la CDMX: duplicados (~11 m, < 30 días) y celda de 250 m
    df = df.rename(columns={"id": "id_folio"})
    df["id_folio"] = df["id_folio"].astype(int)
    df = marcar_posibles_duplicados(df)
    bit.registrar("R4", "Marcados como posible duplicado", df["posible_duplicado"].sum())
    df = asignar_celda(df)
    bit.registrar("R5", "Celdas de 250 m con al menos un reporte", df["celda_id"].nunique())

    columnas = ["id_folio", "folio", "fecha_solicitud", "temporada_lluvias", "comunidad",
                "comunidad_original", "comunidad_corregida", "estatus", "latitud", "longitud",
                "celda_id", "celda_lat", "celda_lon", "ubicacion_dudosa", "posible_duplicado", "grupo_ubicacion"]
    df[columnas].to_csv(SALIDA / "reportes_chalco.csv", index=False, encoding="utf-8-sig",
                        date_format="%Y-%m-%d %H:%M")
    pd.concat(excluidos).to_csv(SALIDA / "reportes_excluidos.csv", index=False, encoding="utf-8-sig")
    bit.registrar("R6", "Reportes válidos guardados", len(df))

    bit.a_dataframe().to_csv(SALIDA / "bitacora_chalco.csv", index=False, encoding="utf-8-sig")
    print(f"\nListo. Archivos en {SALIDA}/")


if __name__ == "__main__":
    procesar()
