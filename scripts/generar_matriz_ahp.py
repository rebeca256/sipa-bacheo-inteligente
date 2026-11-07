"""
SIPA - Genera pesos/AHP_pesos_IPU.xlsx: plantilla de AHP (Saaty) para que el
equipo defina los pesos definitivos del IPU.
  - Instrucciones: pasos, escala de Saaty y criterios con sus pesos v1 y v2
  - Ejemplo: comparaciones derivadas de los pesos v2 vigentes (no entra al consolidado)
  - Evaluador_1..4: 45 comparaciones por pares -> matriz, pesos y consistencia
  - Consolidado: media geométrica de los evaluadores incluidos (AIJ), pesos,
    consistencia, comparación con v1 y v2 y las líneas SQL para peso_criterio.
Uso (desde la carpeta del proyecto): python scripts/generar_matriz_ahp.py
"""
import os
from itertools import combinations

from openpyxl import Workbook
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter as L
from openpyxl.worksheet.datavalidation import DataValidation

SALIDA = "pesos/AHP_pesos_IPU.xlsx"
CRIT = [  # clave, nombre, peso v1, peso v2, dato disponible en la base
    ("DETERIORO", "Nivel de deterioro actual", 0.20, 0.15, "Severidad (sintética por ahora)"),
    ("RIESGO_72H", "Riesgo de accidente a 72 h", 0.20, 0.15, "Modelo de Probabilidad (CDMX)"),
    ("PERSONAS", "Personas afectadas", 0.15, 0.10, "Sin dato (0.5)"),
    ("TRANSPORTE", "Relevancia para transporte público", 0.10, 0.05, "Sin dato (0.5); falta GTFS"),
    ("TRANSITO", "Intensidad del tránsito", 0.10, 0.10, "Sin dato (0.5)"),
    ("VULNERABILIDAD", "Vulnerabilidad territorial", 0.10, 0.10, "Sin dato (0.5); falta CONAPO"),
    ("DETERIORO_MAYOR", "Riesgo de deterioro mayor", 0.10, 0.05, "Historial de reportes de la celda"),
    ("REPORTES", "Reportes ciudadanos (acotado)", 0.05, 0.05, "Reportes del bache (escala log)"),
    ("INUNDACION", "Inundación y drenaje", 0.00, 0.15, "Atlas de riesgo (solo Chalco)"),
    ("ACCESO_SERVICIOS", "Acceso a servicios", 0.00, 0.10, "Equipamiento a 500 m (solo Chalco)"),
]
N = len(CRIT)
RI = 1.49                                   # índice aleatorio de Saaty para n = 10
PARES = list(combinations(range(N), 2))     # 45 comparaciones
EVALUADORES = 4

FUENTE = "Arial"
F = Font(name=FUENTE, size=10)
FB = Font(name=FUENTE, size=10, bold=True)
FT = Font(name=FUENTE, size=14, bold=True, color="1F3A5F")
FH = Font(name=FUENTE, size=10, bold=True, color="FFFFFF")
AZUL_IN = Font(name=FUENTE, size=10, color="0000FF")
AMARILLO = PatternFill("solid", fgColor="FFFF00")
ENC = PatternFill("solid", fgColor="1F3A5F")
GRIS = PatternFill("solid", fgColor="E7ECF2")
LINEA = Side(style="thin", color="A6B4C3")
BORDE = Border(left=LINEA, right=LINEA, top=LINEA, bottom=LINEA)
CENTRO = Alignment(horizontal="center", vertical="center", wrap_text=True)
IZQ = Alignment(horizontal="left", vertical="center", wrap_text=True)

FILA_PAR0 = 8      # primera comparación (hoja de evaluador)
COL_M = 9          # columna I: etiquetas de la matriz
FILA_M = 7         # fila de encabezado de la matriz


def celda(ws, ref, valor, font=F, fill=None, align=CENTRO, fmt=None, borde=True):
    c = ws[ref]
    c.value = valor
    c.font = font
    c.alignment = align
    if fill:
        c.fill = fill
    if fmt:
        c.number_format = fmt
    if borde:
        c.border = BORDE
    return c


def resultados(ws, c0, r0, fila):
    """Pesos (media geométrica por fila), λmax, IC y RC de la matriz que empieza en (c0, r0)."""
    cw = c0 + N                                     # columna de pesos, a la derecha de la matriz
    celda(ws, f"{L(cw)}{r0 - 1}", "Peso", FH, ENC)
    celda(ws, f"{L(cw + 1)}{r0 - 1}", "Media geom.", FH, ENC)
    for i in range(N):
        r = r0 + i
        celda(ws, f"{L(cw + 1)}{r}", f"=GEOMEAN({L(c0)}{r}:{L(c0 + N - 1)}{r})", fmt="0.0000")
        celda(ws, f"{L(cw)}{r}", f"={L(cw + 1)}{r}/SUM(${L(cw + 1)}${r0}:${L(cw + 1)}${r0 + N - 1})",
              FB, fmt="0.0%")
    celda(ws, f"{L(c0 - 1)}{r0 + N}", "Suma columna", FB, GRIS, IZQ)
    for j in range(N):
        celda(ws, f"{L(c0 + j)}{r0 + N}", f"=SUM({L(c0 + j)}{r0}:{L(c0 + j)}{r0 + N - 1})", fmt="0.000")
    lam = "=" + "+".join(f"{L(c0 + j)}{r0 + N}*{L(cw)}{r0 + j}" for j in range(N))
    v = f"{L(c0)}"
    filas = [("λ máx", lam, "0.000"),
             ("Índice de consistencia (IC)", f"=({v}{fila}-{N})/({N}-1)", "0.000"),
             ("Índice aleatorio (RI, n = 10)", RI, "0.00"),
             ("Razón de consistencia (RC = IC/RI)", f"={v}{fila + 1}/{v}{fila + 2}", "0.0%"),
             ("¿Consistente? (RC ≤ 10 %)", f'=IF({v}{fila + 3}<=0.1,"SÍ","NO: revisa comparaciones")', None)]
    for k, (t, val, fmt) in enumerate(filas):
        r = fila + k
        celda(ws, f"{L(c0 - 1)}{r}", t, FB, GRIS, IZQ)
        celda(ws, f"{v}{r}", val, FB if k >= 3 else F, fmt=fmt)
        ws.merge_cells(f"{v}{r}:{L(c0 + 2)}{r}")
    ok = f"{v}{fila + 4}"
    ws.conditional_formatting.add(ok, CellIsRule(operator="equal", formula=['"SÍ"'],
                                                 fill=PatternFill("solid", fgColor="C6EFCE")))
    ws.conditional_formatting.add(ok, CellIsRule(operator="notEqual", formula=['"SÍ"'],
                                                 fill=PatternFill("solid", fgColor="FFC7CE")))
    return cw


def hoja_evaluador(wb, nombre, ejemplo=False):
    ws = wb.create_sheet(nombre)
    ws.sheet_view.showGridLines = False
    celda(ws, "A1", "Comparación por pares de los criterios del IPU (AHP)" + (" · EJEMPLO" if ejemplo else ""),
          FT, align=IZQ, borde=False)
    celda(ws, "A3", "Nombre:", FB, align=IZQ, borde=False)
    celda(ws, "B3", "Ejemplo: derivado de los pesos v2" if ejemplo else None, AZUL_IN, AMARILLO, IZQ)
    ws.merge_cells("B3:D3")
    celda(ws, "A4", "¿Incluir?", FB, align=IZQ, borde=False)
    celda(ws, "B4", "NO" if ejemplo else "SÍ", AZUL_IN, AMARILLO)
    celda(ws, "C4", '=IF(B4="SÍ",1,0)', fmt="0")    # bandera numérica que usa el consolidado
    dv_si = DataValidation(type="list", formula1='"SÍ,NO"', allow_blank=False)
    ws.add_data_validation(dv_si)
    dv_si.add("B4")
    celda(ws, "A5", "Para cada par, elige qué criterio importa más para decidir qué bache reparar primero y "
                    "cuánto más (escala de Saaty en Instrucciones). Edita solo las celdas amarillas.",
          F, align=IZQ, borde=False)
    ws.merge_cells("A5:G5")
    ws.row_dimensions[5].height = 30

    for col, t in zip("ABCDEFG", ["#", "Criterio A", "Criterio B", "¿Cuál importa más?",
                                   "¿Cuánto más? (1-9)", "Valor A/B", "Justificación (opcional)"]):
        celda(ws, f"{col}7", t, FH, ENC)
    dv_cual = DataValidation(type="list", formula1='"A,B,Igual"', allow_blank=False)
    dv_int = DataValidation(type="whole", operator="between", formula1="1", formula2="9",
                            showErrorMessage=True, error="Usa un entero del 1 al 9.")
    ws.add_data_validation(dv_cual)
    ws.add_data_validation(dv_int)

    fila_par = {}
    for k, (i, j) in enumerate(PARES):
        r = FILA_PAR0 + k
        fila_par[(i, j)] = r
        if ejemplo:
            razon = CRIT[i][3] / CRIT[j][3]
            if abs(razon - 1) < 0.25:
                cual, inten = "Igual", 1
            elif razon > 1:
                cual, inten = "A", min(9, round(razon))
            else:
                cual, inten = "B", min(9, round(1 / razon))
        else:
            cual, inten = "Igual", 1
        celda(ws, f"A{r}", k + 1)
        celda(ws, f"B{r}", CRIT[i][0], align=IZQ)
        celda(ws, f"C{r}", CRIT[j][0], align=IZQ)
        celda(ws, f"D{r}", cual, AZUL_IN, AMARILLO)
        celda(ws, f"E{r}", inten, AZUL_IN, AMARILLO)
        celda(ws, f"F{r}", f'=IF(D{r}="Igual",1,IF(D{r}="A",E{r},1/E{r}))', fmt="0.000")
        celda(ws, f"G{r}", None, AZUL_IN, AMARILLO, IZQ)
        dv_cual.add(f"D{r}")
        dv_int.add(f"E{r}")

    # Matriz recíproca, calculada a partir de las comparaciones
    celda(ws, f"{L(COL_M)}{FILA_M - 1}", "Matriz de comparación (se calcula sola)", FB, align=IZQ, borde=False)
    celda(ws, f"{L(COL_M)}{FILA_M}", "", FH, ENC)
    for a in range(N):
        celda(ws, f"{L(COL_M + 1 + a)}{FILA_M}", CRIT[a][0], FH, ENC)
        celda(ws, f"{L(COL_M)}{FILA_M + 1 + a}", CRIT[a][0], FH, ENC, IZQ)
    for i in range(N):
        for j in range(N):
            ref = f"{L(COL_M + 1 + j)}{FILA_M + 1 + i}"
            if i == j:
                val = 1
            elif i < j:
                val = f"=$F${fila_par[(i, j)]}"
            else:
                val = f"=1/{L(COL_M + 1 + i)}{FILA_M + 1 + j}"
            celda(ws, ref, val, fill=GRIS if i == j else None, fmt="0.000")
    resultados(ws, COL_M + 1, FILA_M + 1, FILA_M + N + 3)

    ws.column_dimensions["A"].width = 9
    for c in "BC":
        ws.column_dimensions[c].width = 18
    for c, w in zip("DEFG", [13, 11, 9, 34]):
        ws.column_dimensions[c].width = w
    ws.column_dimensions[L(COL_M)].width = 30
    for a in range(N + 2):
        ws.column_dimensions[L(COL_M + 1 + a)].width = 12
    ws.freeze_panes = "A8"


def instrucciones(wb):
    ws = wb.active
    ws.title = "Instrucciones"
    ws.sheet_view.showGridLines = False
    celda(ws, "A1", "SIPA · Pesos del Índice de Prioridad Urbana (IPU) por AHP", FT, align=IZQ, borde=False)
    pasos = [
        "1. Cada integrante llena una hoja Evaluador_N. Si son menos de 4, pongan NO en «¿Incluir?» en las que sobren.",
        "2. En cada una de las 45 filas elige qué criterio importa más (A, B o Igual) y cuánto más, con la escala de abajo.",
        "3. Revisa la razón de consistencia (RC) de tu hoja: debe ser de 10 % o menos. Si no, busca comparaciones "
        "contradictorias (por ejemplo, A > B y B > C, pero C > A).",
        "4. La hoja Consolidado combina a todos con la media geométrica de cada comparación (agregación de juicios "
        "individuales, AIJ) y calcula los pesos finales.",
        "5. Discutan en equipo las diferencias grandes con v2 y anoten la justificación. Luego usen las líneas SQL de "
        "Consolidado para cargar los pesos nuevos en peso_criterio.",
        "Solo se editan las celdas amarillas (texto azul); todo lo demás se calcula. La hoja Ejemplo muestra el llenado "
        "a partir de los pesos v2 y no entra en el consolidado.",
        "Pregunta guía para cada par: «Si dos baches solo se distinguen en estos dos criterios, ¿cuál debería "
        "repararse primero y con cuánta claridad?».",
    ]
    for k, p in enumerate(pasos):
        celda(ws, f"A{3 + k}", p, align=IZQ, borde=False)
        ws.merge_cells(f"A{3 + k}:E{3 + k}")
        ws.row_dimensions[3 + k].height = 30

    r = 12
    celda(ws, f"A{r}", "Escala de Saaty", FB, align=IZQ, borde=False)
    celda(ws, f"A{r + 1}", "Valor", FH, ENC)
    celda(ws, f"B{r + 1}", "Significado", FH, ENC)
    escala = [(1, "Igual importancia"), (3, "Moderadamente más importante"), (5, "Claramente más importante"),
              (7, "Mucho más importante"), (9, "Extremadamente más importante"), ("2, 4, 6, 8", "Valores intermedios")]
    for k, (val, s) in enumerate(escala):
        celda(ws, f"A{r + 2 + k}", val)
        celda(ws, f"B{r + 2 + k}", s, align=IZQ)

    r = 21
    celda(ws, f"A{r}", "Criterios", FB, align=IZQ, borde=False)
    for col, t in zip("ABCDE", ["Clave", "Criterio", "Peso v1", "Peso v2 (vigente)", "Dato en la base hoy"]):
        celda(ws, f"{col}{r + 1}", t, FH, ENC)
    for k, (cl, nom, v1, v2, dato) in enumerate(CRIT):
        rr = r + 2 + k
        celda(ws, f"A{rr}", cl, align=IZQ)
        celda(ws, f"B{rr}", nom, align=IZQ)
        celda(ws, f"C{rr}", v1, fmt="0%")
        celda(ws, f"D{rr}", v2, fmt="0%")
        celda(ws, f"E{rr}", dato, align=IZQ)
    nota = r + 3 + N
    celda(ws, f"A{nota}", "Fuente de v1 y v2: bd/03_carga_base_maestra.sql (tabla peso_criterio). "
                          "RI = 1.49 para n = 10 (Saaty, 1980).", align=IZQ, borde=False)
    ws.merge_cells(f"A{nota}:E{nota}")
    for c, w in zip("ABCDE", [20, 34, 10, 16, 36]):
        ws.column_dimensions[c].width = w


def consolidado(wb, hojas):
    ws = wb.create_sheet("Consolidado")
    ws.sheet_view.showGridLines = False
    celda(ws, "A1", "Consolidado del equipo (media geométrica de los evaluadores incluidos)", FT,
          align=IZQ, borde=False)
    celda(ws, "A3", "Evaluadores incluidos:", FB, align=IZQ, borde=False)
    celda(ws, "B3", "=" + "+".join(f"{h}!$C$4" for h in hojas), FB, fmt="0")
    celda(ws, "A4", "Vigente desde (AAAA-MM-DD):", FB, align=IZQ, borde=False)
    celda(ws, "B4", "2026-11-15", AZUL_IN, AMARILLO)

    c0, r0 = 2, 8
    celda(ws, f"A{r0 - 1}", "", FH, ENC)
    for a in range(N):
        celda(ws, f"{L(c0 + a)}{r0 - 1}", CRIT[a][0], FH, ENC)
        celda(ws, f"A{r0 + a}", CRIT[a][0], FH, ENC, IZQ)
    for i in range(N):
        for j in range(N):
            src = f"{L(COL_M + 1 + j)}{FILA_M + 1 + i}"
            suma_ln = "+".join(f"{h}!$C$4*LN({h}!{src})" for h in hojas)
            val = 1 if i == j else f"=IF($B$3=0,1,EXP(({suma_ln})/$B$3))"
            celda(ws, f"{L(c0 + j)}{r0 + i}", val, fill=GRIS if i == j else None, fmt="0.000")
    cw = resultados(ws, c0, r0, r0 + N + 2)

    r = r0 + N + 9
    celda(ws, f"A{r}", "Pesos finales y comparación con v1 y v2", FB, align=IZQ, borde=False)
    for k, t in enumerate(["Clave", "Peso AHP", "Peso v1", "Peso v2", "AHP − v2", "Línea SQL para peso_criterio"]):
        celda(ws, f"{L(1 + k)}{r + 1}", t, FH, ENC)
    ws.merge_cells(f"F{r + 1}:K{r + 1}")
    for k, (cl, _, v1, v2, _) in enumerate(CRIT):
        rr = r + 2 + k
        celda(ws, f"A{rr}", cl, align=IZQ)
        celda(ws, f"B{rr}", f"={L(cw)}{r0 + k}", FB, fmt="0.0%")
        celda(ws, f"C{rr}", v1, fmt="0%")
        celda(ws, f"D{rr}", v2, fmt="0%")
        celda(ws, f"E{rr}", f"=B{rr}-D{rr}", fmt="+0.0%;-0.0%;0.0%")
        celda(ws, f"F{rr}", f"=\"('{cl}', '\"&$B$4&\"', NULL, \"&TEXT(B{rr},\"0.0000\")&\"),\"",
              Font(name="Consolas", size=9), align=IZQ)
        ws.merge_cells(f"F{rr}:K{rr}")
    rt = r + 2 + N
    celda(ws, f"A{rt}", "Total", FB, GRIS, IZQ)
    for col in "BCD":
        celda(ws, f"{col}{rt}", f"=SUM({col}{r + 2}:{col}{rt - 1})", FB, GRIS, fmt="0.0%")
    celda(ws, f"A{rt + 2}", "Las líneas SQL redondean a 4 decimales; si la suma no da 1.0000, ajusten el criterio de "
                            "mayor peso. Antes de cargarlas, cierren los pesos v2 con vigente_hasta = la fecha de B4.",
          align=IZQ, borde=False)
    ws.merge_cells(f"A{rt + 2}:K{rt + 2}")
    ws.row_dimensions[rt + 2].height = 30
    ws.column_dimensions["A"].width = 30
    for a in range(1, N + 3):
        ws.column_dimensions[L(1 + a)].width = 12


def main():
    os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
    wb = Workbook()
    instrucciones(wb)
    hoja_evaluador(wb, "Ejemplo", ejemplo=True)
    hojas = [f"Evaluador_{k}" for k in range(1, EVALUADORES + 1)]
    for h in hojas:
        hoja_evaluador(wb, h)
    consolidado(wb, hojas)
    wb.save(SALIDA)
    print("Generado:", SALIDA)


if __name__ == "__main__":
    main()
