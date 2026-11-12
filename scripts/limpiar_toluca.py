"""
SIPA - Limpia los datos del tablero de bacheo de Toluca (descargados con scripts/descargar_toluca.py).

Entradas:  datos/toluca/bacheo_toluca.csv, datos/toluca/medidas_muestra.csv
Salidas:   datos/limpios/toluca_baches.csv    (un renglón por bache reparado)
           datos/limpios/toluca_medidas.csv   (muestra aleatoria con largo, ancho, m² y profundidad)
           datos/limpios/toluca_limpieza.json (qué se descartó y por qué)

Reglas:
- Tipo: se unifican las variantes («Profundo», «PROFUNDO», «BACHE PROFUNDO (>12CM)»…) en
  PROFUNDO / SUPERFICIAL; «PENDIENTE» queda como SIN_CLASIFICAR.
- Medidas: se descartan largos o anchos ≤ 0 (errores de captura) y áreas > 50 m², que no son
  un bache sino un tramo para reencarpetar. El área se recalcula como largo × ancho.
- Profundidad: se guarda en cm; se descartan valores ≤ 0 o > 40 cm.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ENT = Path("datos/toluca")
SAL = Path("datos/limpios")
AREA_MAX = 50.0
PROF_MAX_CM = 40.0


def tipo(t):
    t = str(t).upper()
    if "PROFUNDO" in t:
        return "PROFUNDO"
    if "SUPERFICIAL" in t:
        return "SUPERFICIAL"
    return "SIN_CLASIFICAR"


def main():
    SAL.mkdir(exist_ok=True)
    b = pd.read_csv(ENT / "bacheo_toluca.csv", dtype=str)
    n0 = len(b)
    b = b.drop_duplicates(subset=["folio"])
    b["tipo"] = b["tipo"].map(tipo)
    b["fecha"] = pd.to_datetime(b["fecha"], format="%d/%m/%Y", errors="coerce")
    b["lat"] = pd.to_numeric(b["lat"], errors="coerce")
    b["lng"] = pd.to_numeric(b["lng"], errors="coerce")
    fuera = ~b.lat.between(19.0, 19.6) | ~b.lng.between(-99.9, -99.4)
    b.loc[fuera, ["lat", "lng"]] = np.nan
    b["estatus"] = b["estatus"].fillna("Sin dato")
    b["anio"] = b.fecha.dt.year
    b["mes"] = b.fecha.dt.to_period("M").astype(str)
    b = b[["folio", "tipo", "calle", "colonia", "delegacion", "estatus", "fecha", "anio", "mes", "lat", "lng"]]
    b.to_csv(SAL / "toluca_baches.csv", index=False, encoding="utf-8")

    m = pd.read_csv(ENT / "medidas_muestra.csv")
    m0 = len(m)
    m["tipo"] = m["tipo"].map(tipo)
    m["largo"] = pd.to_numeric(m["largo"], errors="coerce")
    m["ancho"] = pd.to_numeric(m["ancho"], errors="coerce")
    malas = (m.largo <= 0) | (m.ancho <= 0) | m.largo.isna() | m.ancho.isna()
    m = m[~malas].copy()
    m["area_m2"] = (m.largo * m.ancho).round(3)
    grandes = m.area_m2 > AREA_MAX
    m = m[~grandes].copy()
    p = pd.to_numeric(m["profundidad"], errors="coerce")
    p = np.where(p < 1, p * 100, p)          # algunos capturan en metros
    m["profundidad_cm"] = np.where((p > 0) & (p <= PROF_MAX_CM), p, np.nan)
    m["volumen_m3"] = (m.area_m2 * m.profundidad_cm / 100).round(4)
    m = m[["folio", "tipo", "largo", "ancho", "area_m2", "profundidad_cm", "volumen_m3", "delegacion", "colonia"]]
    m.to_csv(SAL / "toluca_medidas.csv", index=False, encoding="utf-8")

    info = dict(
        baches_descargados=n0, baches_limpios=len(b), duplicados=n0 - len(b),
        tipos=b.tipo.value_counts().to_dict(), sin_coordenadas=int(b.lat.isna().sum()),
        fecha_min=str(b.fecha.min().date()), fecha_max=str(b.fecha.max().date()),
        medidas_muestra=m0, medidas_negativas_o_vacias=int(malas.sum()), medidas_mayores_50m2=int(grandes.sum()),
        medidas_limpias=len(m), con_profundidad=int(m.profundidad_cm.notna().sum()),
        area_mediana=round(float(m.area_m2.median()), 2), area_media=round(float(m.area_m2.mean()), 2),
        profundidad_mediana_cm=round(float(m.profundidad_cm.median()), 1),
        fuente="Dirección General de Obras Públicas de Toluca, tablero de bacheo "
               "https://dgop.toluca.gob.mx/tablero_bacheo_filtros1.php (consultado el 11-11-2026)",
    )
    (SAL / "toluca_limpieza.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(info, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
