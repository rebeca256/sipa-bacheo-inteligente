"""
SIPA - Sistema Inteligente de Priorización Asfáltica
Limpieza de la base maestra de solicitudes de bacheo (CDMX, 2019-2022).

Entrada:
    base_maestra_baches_2019_2024.csv  (no se modifica)

Salidas (carpeta datos/limpios/):
    base_maestra_limpia.csv   registros válidos, limpios y con columnas derivadas
    registros_excluidos.csv   registros descartados y el motivo
    bitacora_limpieza.csv     qué se hizo en cada paso y a cuántos registros afectó
    cat_estatus.csv           catálogo de estatus (original -> agrupado)

Uso (desde la carpeta del proyecto):
    python scripts/limpiar_base_maestra.py
    python scripts/limpiar_base_maestra.py --entrada otra_ruta.csv --salida otra_carpeta

Criterio general: los datos originales nunca se borran ni se sobrescriben.
Lo que se corrige o se infiere queda marcado en columnas de control
(alcaldia_inferida, colonia_inferida, ubicacion_dudosa, posible_duplicado,
periodo_atipico).

Limitación conocida: la validación de ubicación usa un rectángulo alrededor de
la CDMX, que también incluye partes del Estado de México. Los puntos que quedan
sin alcaldía se marcan como ubicacion_dudosa. Para una validación exacta haría
falta el polígono oficial de las alcaldías.
"""

import argparse
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Parámetros de limpieza (ajustables y documentados en el informe)
# ---------------------------------------------------------------------------

# Rectángulo que contiene a la CDMX, con un pequeño margen.
LAT_MIN, LAT_MAX = 19.00, 19.65
LON_MIN, LON_MAX = -99.40, -98.90

# Distancia máxima (m) para inferir alcaldía o colonia a partir de vecinos.
DIST_MAX_ALCALDIA_M = 1000
DIST_MAX_COLONIA_M = 150
K_VECINOS = 5

# Dos reportes se consideran posible duplicado si caen en la misma celda de
# ~11 m (coordenadas redondeadas a 4 decimales) y con menos de N días entre sí.
DECIMALES_DUPLICADO = 4
DIAS_DUPLICADO = 30

# Tamaño de la celda de la cuadrícula usada como unidad de análisis.
TAMANO_CELDA_M = 250

# Meses de temporada de lluvias en la CDMX (mayo a octubre).
MESES_LLUVIA = {5, 6, 7, 8, 9, 10}

# Meses con registro anormalmente bajo (probable pandemia y corte del sistema).
PERIODOS_ATIPICOS = {"2020-04", "2020-05", "2020-06", "2021-12", "2022-01"}

# Años para entrenar y para probar el modelo predictivo.
ANIOS_ENTRENAMIENTO = {2019, 2020, 2021}
ANIOS_PRUEBA = {2022}

# Agrupación de estatus: los nombres cambiaron entre años.
CATALOGO_ESTATUS = {
    "ATENDIDO": ("RESUELTO", "Solicitud atendida (nombre usado en 2019-2021)"),
    "CERRADO": ("RESUELTO", "Solicitud cerrada (nombre usado en 2022)"),
    "TURNADO": ("TURNADO", "Enviada a otra área o dependencia"),
    "RECIBIDO": ("PENDIENTE", "Recibida sin atención registrada"),
}

METROS_POR_GRADO = 111_320


# ---------------------------------------------------------------------------
# Funciones auxiliares
# ---------------------------------------------------------------------------

class Bitacora:
    """Registra cada paso de limpieza para poder reportarlo."""

    def __init__(self):
        self.pasos = []

    def registrar(self, paso, descripcion, afectados):
        self.pasos.append({"paso": paso, "descripcion": descripcion, "registros_afectados": int(afectados)})
        print(f"  [{paso}] {descripcion}: {afectados:,}")

    def a_dataframe(self):
        return pd.DataFrame(self.pasos)


def normalizar_texto(serie):
    """Quita espacios al inicio y final, colapsa espacios dobles y pasa a mayúsculas."""
    return serie.str.strip().str.replace(r"\s+", " ", regex=True).str.upper()


def distancias_m(lat, lon, lats, lons):
    """Distancia aproximada en metros de un punto a muchos puntos
    (aproximación plana; suficiente para distancias cortas dentro de la ciudad)."""
    dy = (lats - lat) * METROS_POR_GRADO
    dx = (lons - lon) * METROS_POR_GRADO * math.cos(math.radians(lat))
    return np.sqrt(dx ** 2 + dy ** 2)


def inferir_por_vecinos(df, columna, dist_max_m):
    """Para los registros con `columna` vacía, toma los K vecinos más cercanos que
    sí la tienen y asigna el valor más frecuente, solo si el vecino más cercano está
    a menos de `dist_max_m`. Devuelve una serie booleana con los registros inferidos."""
    conocidos = df[df[columna] != ""]
    lats, lons = conocidos["latitud"].to_numpy(), conocidos["longitud"].to_numpy()
    valores = conocidos[columna].to_numpy()

    inferidos = pd.Series(False, index=df.index)
    for idx in df.index[df[columna] == ""]:
        d = distancias_m(df.at[idx, "latitud"], df.at[idx, "longitud"], lats, lons)
        cercanos = np.argsort(d)[:K_VECINOS]
        if d[cercanos[0]] <= dist_max_m:
            df.at[idx, columna] = pd.Series(valores[cercanos]).mode().iloc[0]
            inferidos.at[idx] = True
    return inferidos


def marcar_posibles_duplicados(df):
    """Marca reportes en la misma celda de ~11 m con menos de DIAS_DUPLICADO días
    respecto al reporte anterior de esa celda. No elimina nada: la eliminación de
    duplicados la hace el sistema (tabla hash, sección 5.1 de la arquitectura)."""
    celda = (df["latitud"].round(DECIMALES_DUPLICADO).astype(str) + "," +
             df["longitud"].round(DECIMALES_DUPLICADO).astype(str))
    orden = df.assign(_celda=celda).sort_values(["_celda", "fecha_solicitud"])
    dias = orden.groupby("_celda")["fecha_solicitud"].diff().dt.days
    duplicado = dias.notna() & (dias < DIAS_DUPLICADO)

    # grupo_ubicacion: reportes que comparten la misma celda de ~11 m, sin importar
    # la fecha. Se identifica con el folio del primer reporte de esa celda.
    grupo = orden.groupby("_celda")["id_folio"].transform("first")
    df["posible_duplicado"] = duplicado.reindex(df.index)
    df["grupo_ubicacion"] = grupo.where(orden.groupby("_celda")["id_folio"].transform("size") > 1).reindex(df.index)
    return df


def asignar_celda(df):
    """Asigna cada reporte a una celda de TAMANO_CELDA_M metros de lado."""
    lat_ref = (LAT_MIN + LAT_MAX) / 2
    paso_lat = TAMANO_CELDA_M / METROS_POR_GRADO
    paso_lon = TAMANO_CELDA_M / (METROS_POR_GRADO * math.cos(math.radians(lat_ref)))
    fila = ((df["latitud"] - LAT_MIN) // paso_lat).astype(int)
    col = ((df["longitud"] - LON_MIN) // paso_lon).astype(int)
    df["celda_id"] = "F" + fila.astype(str).str.zfill(3) + "_C" + col.astype(str).str.zfill(3)
    # Centro de la celda, útil para mapas
    df["celda_lat"] = (LAT_MIN + (fila + 0.5) * paso_lat).round(6)
    df["celda_lon"] = (LON_MIN + (col + 0.5) * paso_lon).round(6)
    return df


# ---------------------------------------------------------------------------
# Proceso principal
# ---------------------------------------------------------------------------

def limpiar(ruta_entrada, carpeta_salida):
    bit = Bitacora()
    print(f"Leyendo {ruta_entrada}")
    df = pd.read_csv(ruta_entrada, dtype=str, keep_default_na=False)
    df.insert(0, "fila_original", np.arange(2, len(df) + 2))  # fila 1 = encabezado
    bit.registrar("0", "Registros leídos", len(df))

    excluidos = []

    def excluir(mascara, motivo):
        if mascara.any():
            excluidos.append(df[mascara].assign(motivo_exclusion=motivo))
        bit.registrar("X", f"Excluidos: {motivo}", mascara.sum())
        return df[~mascara].copy()

    # 1. Texto
    for col in ["colonia_datos", "alcaldia", "estatus"]:
        original = df[col]
        df[col] = normalizar_texto(df[col])
        bit.registrar("1", f"Texto normalizado en '{col}'", (original != df[col]).sum())

    # 2. Folio: quitar el prefijo "- " y convertir a número
    df["id_folio"] = df["id_folio"].str.replace(r"^\s*-\s*", "", regex=True)
    folio_valido = df["id_folio"].str.fullmatch(r"\d+")
    df = excluir(~folio_valido, "folio no numérico")
    df["id_folio"] = df["id_folio"].astype("int64")
    bit.registrar("2", "Prefijo '- ' eliminado del folio", len(df))
    df = excluir(df["id_folio"].duplicated(keep="first"), "folio duplicado")

    # 3. Fecha
    df["fecha_solicitud"] = pd.to_datetime(df["fecha_solicitud"], errors="coerce", format="%Y-%m-%d")
    df = excluir(df["fecha_solicitud"].isna(), "fecha inválida")

    # 4. Coordenadas
    df["latitud"] = pd.to_numeric(df["latitud"], errors="coerce")
    df["longitud"] = pd.to_numeric(df["longitud"], errors="coerce")
    df = excluir(df["latitud"].isna() | df["longitud"].isna(), "coordenadas no numéricas")
    fuera = ~(df["latitud"].between(LAT_MIN, LAT_MAX) & df["longitud"].between(LON_MIN, LON_MAX))
    df = excluir(fuera, "coordenadas fuera de la CDMX")

    # 5. Estatus
    desconocido = ~df["estatus"].isin(CATALOGO_ESTATUS.keys())
    df = excluir(desconocido, "estatus desconocido")
    df["estatus_original"] = df["estatus"]
    df["estatus"] = df["estatus_original"].map(lambda e: CATALOGO_ESTATUS[e][0])
    bit.registrar("5", "Estatus agrupados con el catálogo (ATENDIDO y CERRADO -> RESUELTO)",
                  df["estatus_original"].isin(["ATENDIDO", "CERRADO"]).sum())

    # 6. Alcaldía y colonia faltantes, inferidas por vecinos cercanos
    df["alcaldia_inferida"] = inferir_por_vecinos(df, "alcaldia", DIST_MAX_ALCALDIA_M)
    bit.registrar("6", f"Alcaldía inferida por vecinos (<= {DIST_MAX_ALCALDIA_M} m)", df["alcaldia_inferida"].sum())
    bit.registrar("6", "Alcaldía que sigue vacía", (df["alcaldia"] == "").sum())

    df["colonia_inferida"] = inferir_por_vecinos(df, "colonia_datos", DIST_MAX_COLONIA_M)
    bit.registrar("6", f"Colonia inferida por vecinos (<= {DIST_MAX_COLONIA_M} m)", df["colonia_inferida"].sum())
    bit.registrar("6", "Colonia que sigue vacía", (df["colonia_datos"] == "").sum())

    # Sin alcaldía después de inferir: probablemente fuera de la CDMX (Estado de México)
    df["ubicacion_dudosa"] = df["alcaldia"] == ""
    bit.registrar("6", "Marcados como ubicación dudosa (sin alcaldía; posible Estado de México)",
                  df["ubicacion_dudosa"].sum())

    # 7. Posibles duplicados (solo se marcan)
    df = marcar_posibles_duplicados(df)
    bit.registrar("7", f"Marcados como posible duplicado (misma celda ~11 m y < {DIAS_DUPLICADO} días)",
                  df["posible_duplicado"].sum())
    bit.registrar("7", "Reportes que comparten ubicación (~11 m) con otro reporte", df["grupo_ubicacion"].notna().sum())

    # 8. Columnas derivadas para el análisis
    df["anio"] = df["fecha_solicitud"].dt.year
    df["mes"] = df["fecha_solicitud"].dt.month
    df["anio_mes"] = df["fecha_solicitud"].dt.strftime("%Y-%m")
    df["temporada_lluvias"] = df["mes"].isin(MESES_LLUVIA)
    df["periodo_atipico"] = df["anio_mes"].isin(PERIODOS_ATIPICOS)
    bit.registrar("8", "Registros en periodos atípicos (marcados, no excluidos)", df["periodo_atipico"].sum())
    df["conjunto"] = np.where(df["anio"].isin(ANIOS_ENTRENAMIENTO), "ENTRENAMIENTO",
                              np.where(df["anio"].isin(ANIOS_PRUEBA), "PRUEBA", "OTRO"))
    df = asignar_celda(df)
    bit.registrar("8", f"Celdas de {TAMANO_CELDA_M} m con al menos un reporte", df["celda_id"].nunique())

    # 9. Guardar
    carpeta_salida.mkdir(parents=True, exist_ok=True)
    columnas = ["id_folio", "fecha_solicitud", "anio", "mes", "anio_mes", "temporada_lluvias",
                "periodo_atipico", "conjunto", "alcaldia", "alcaldia_inferida", "colonia_datos",
                "colonia_inferida", "estatus", "estatus_original", "latitud", "longitud",
                "celda_id", "celda_lat", "celda_lon", "ubicacion_dudosa", "posible_duplicado", "grupo_ubicacion",
                "fila_original"]
    df = df.sort_values(["fecha_solicitud", "id_folio"])
    df["fecha_solicitud"] = df["fecha_solicitud"].dt.strftime("%Y-%m-%d")
    df["grupo_ubicacion"] = df["grupo_ubicacion"].astype("Int64")
    df[columnas].to_csv(carpeta_salida / "base_maestra_limpia.csv", index=False, encoding="utf-8-sig")

    exc = pd.concat(excluidos) if excluidos else pd.DataFrame(columns=["motivo_exclusion"])
    exc.to_csv(carpeta_salida / "registros_excluidos.csv", index=False, encoding="utf-8-sig")

    bit.registrar("9", "Registros finales en la base limpia", len(df))
    bit.a_dataframe().to_csv(carpeta_salida / "bitacora_limpieza.csv", index=False, encoding="utf-8-sig")

    pd.DataFrame([{"estatus_original": k, "estatus_agrupado": v[0], "descripcion": v[1]}
                  for k, v in CATALOGO_ESTATUS.items()]).to_csv(
        carpeta_salida / "cat_estatus.csv", index=False, encoding="utf-8-sig")

    print(f"\nListo. Archivos guardados en {carpeta_salida}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8-sig")  # acentos correctos en la consola de Windows
    proyecto = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description="Limpieza de la base maestra de solicitudes de bacheo (SIPA)")
    parser.add_argument("--entrada", type=Path, default=proyecto / "base_maestra_baches_2019_2024.csv")
    parser.add_argument("--salida", type=Path, default=proyecto / "datos" / "limpios")
    args = parser.parse_args()
    limpiar(args.entrada, args.salida)
