"""
SIPA - Pensamiento Complejo para la Argumentación
Mapa de red de los agentes del problema del bacheo y sus conexiones, y diagrama
de los ciclos de retroalimentación.

Uso (desde la carpeta del proyecto):
    python pensamiento/mapa_red.py
Genera en pensamiento/resultados/: g1_mapa_red_agentes.png y g2_ciclos.png
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch

SALIDA = Path("pensamiento/resultados")

# Agentes: (x, y, grupo). Grupos: sociedad, gobierno, operación, conocimiento, entorno
AGENTES = {
    "Ciudadanía\nconductora": (-3.2, 2.4, "sociedad"),
    "Peatones y\nciclistas": (-4.3, 0.9, "sociedad"),
    "Usuarios del\ntransporte público": (-4.3, -0.8, "sociedad"),
    "Comunidades con\npoca participación\ndigital": (-3.2, -2.4, "sociedad"),
    "Transportistas\nde carga": (-1.2, 3.4, "sociedad"),
    "Alcaldías y\nAyuntamiento\nde Chalco": (0.6, 1.0, "gobierno"),
    "Secretaría de Obras\n(SOBSE)": (2.4, 2.8, "gobierno"),
    "Finanzas y\nAuditoría": (4.3, 1.4, "gobierno"),
    "Organismo del agua\n(SACMEX / ODAPAS)": (4.7, 0.0, "gobierno"),
    "SSC y servicios\nde emergencia": (0.4, 3.6, "gobierno"),
    "Brigadas y\ncontratistas": (2.0, -3.0, "operacion"),
    "Proveedores\nde asfalto": (4.3, -3.0, "operacion"),
    "Persona\nsupervisora": (1.4, -1.0, "operacion"),
    "SIPA\n(datos y modelo)": (-1.0, -0.3, "conocimiento"),
    "Universidad y\nequipo SIPA": (-1.2, -3.4, "conocimiento"),
    "Lluvia, suelo\narcilloso y\ndrenaje": (5.8, -1.7, "entorno"),
    "Medios y\nredes sociales": (-1.8, 1.6, "sociedad"),
}

COLORES = {"sociedad": "#90caf9", "gobierno": "#ffcc80", "operacion": "#a5d6a7",
           "conocimiento": "#ce93d8", "entorno": "#bcaaa4"}
NOMBRES = {"sociedad": "Sociedad", "gobierno": "Gobierno", "operacion": "Operación",
           "conocimiento": "Conocimiento", "entorno": "Entorno físico"}

# Conexiones: (origen, destino, etiqueta, tipo[, posición de la etiqueta 0-1]) · tipo: flujo, conflicto
CONEXIONES = [
    ("Ciudadanía\nconductora", "SIPA\n(datos y modelo)", "reportes", "flujo", 0.25),
    ("Comunidades con\npoca participación\ndigital", "SIPA\n(datos y modelo)", "pocos reportes (sesgo)", "conflicto"),
    ("Peatones y\nciclistas", "Alcaldías y\nAyuntamiento\nde Chalco", "exigen seguridad", "flujo"),
    ("Usuarios del\ntransporte público", "SIPA\n(datos y modelo)", "rutas afectadas", "flujo"),
    ("Transportistas\nde carga", "Secretaría de Obras\n(SOBSE)", "daño ×(peso)⁴", "conflicto"),
    ("SSC y servicios\nde emergencia", "SIPA\n(datos y modelo)", "accidentes", "flujo", 0.3),
    ("SIPA\n(datos y modelo)", "Persona\nsupervisora", "recomienda", "flujo"),
    ("Persona\nsupervisora", "Brigadas y\ncontratistas", "ordena", "flujo"),
    ("Brigadas y\ncontratistas", "SIPA\n(datos y modelo)", "evidencia", "flujo"),
    ("Proveedores\nde asfalto", "Brigadas y\ncontratistas", "mezcla", "flujo"),
    ("Finanzas y\nAuditoría", "Secretaría de Obras\n(SOBSE)", "presupuesto", "flujo"),
    ("Secretaría de Obras\n(SOBSE)", "Alcaldías y\nAyuntamiento\nde Chalco", "turnos y\ncompetencias", "conflicto"),
    ("Alcaldías y\nAyuntamiento\nde Chalco", "Persona\nsupervisora", "presión política", "conflicto"),
    ("Medios y\nredes sociales", "Alcaldías y\nAyuntamiento\nde Chalco", "visibilidad", "conflicto"),
    ("Ciudadanía\nconductora", "Medios y\nredes sociales", "quejas", "flujo"),
    ("Ciudadanía\nconductora", "Finanzas y\nAuditoría", "reclamaciones", "conflicto", 0.75),
    ("Lluvia, suelo\narcilloso y\ndrenaje", "Organismo del agua\n(SACMEX / ODAPAS)", "", "flujo"),
    ("Organismo del agua\n(SACMEX / ODAPAS)", "Secretaría de Obras\n(SOBSE)", "obras sin\ncoordinar", "conflicto", 0.3),
    ("Lluvia, suelo\narcilloso y\ndrenaje", "Brigadas y\ncontratistas", "reincidencia", "conflicto"),
    ("Universidad y\nequipo SIPA", "SIPA\n(datos y modelo)", "diseña", "flujo"),
    ("SIPA\n(datos y modelo)", "Finanzas y\nAuditoría", "costo de esperar", "flujo"),
]


def mapa_red():
    fig, ax = plt.subplots(figsize=(13, 9))
    for o, d, etiqueta, tipo, *pos in CONEXIONES:
        f = pos[0] if pos else 0.5
        x0, y0, _ = AGENTES[o]
        x1, y1, _ = AGENTES[d]
        conflicto = tipo == "conflicto"
        ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=14,
                                     shrinkA=34, shrinkB=34, lw=1.6,
                                     color="#c62828" if conflicto else "#455a64",
                                     linestyle="--" if conflicto else "-",
                                     connectionstyle="arc3,rad=0.08"))
        if etiqueta:
            ax.text(x0 + f * (x1 - x0), y0 + f * (y1 - y0), etiqueta, fontsize=7.5, ha="center", va="center",
                    color="#c62828" if conflicto else "#263238",
                    bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.85))
    for nombre, (x, y, g) in AGENTES.items():
        ax.text(x, y, nombre, ha="center", va="center", fontsize=8.5, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.45", fc=COLORES[g], ec="#37474f", lw=1.2))
    for i, (g, c) in enumerate(COLORES.items()):
        ax.text(-5.2 + i * 2.1, -4.4, NOMBRES[g], fontsize=9, ha="left", va="center",
                bbox=dict(boxstyle="round,pad=0.35", fc=c, ec="#37474f"))
    ax.plot([2.4, 3.0], [4.35, 4.35], color="#455a64", lw=1.6)
    ax.text(3.1, 4.35, "relación de intercambio", fontsize=8.5, va="center")
    ax.plot([5.0, 5.6], [4.35, 4.35], color="#c62828", lw=1.6, ls="--")
    ax.text(5.7, 4.35, "tensión o conflicto", fontsize=8.5, va="center")
    ax.set_xlim(-5.6, 7.2)
    ax.set_ylim(-4.8, 4.7)
    ax.axis("off")
    ax.set_title("Mapa de red de los agentes del bacheo y sus problemáticas", fontsize=13, fontweight="bold")
    fig.tight_layout()
    fig.savefig(SALIDA / "g1_mapa_red_agentes.png", dpi=170)
    plt.close(fig)


def ciclo(ax, cx, cy, nodos, titulo, color, signo):
    import math
    n = len(nodos)
    r = 1.55
    pos = [(cx + r * math.cos(math.pi / 2 - 2 * math.pi * i / n),
            cy + r * math.sin(math.pi / 2 - 2 * math.pi * i / n)) for i in range(n)]
    for i in range(n):
        ax.add_patch(FancyArrowPatch(pos[i], pos[(i + 1) % n], arrowstyle="-|>", mutation_scale=14,
                                     shrinkA=30, shrinkB=30, lw=1.8, color=color,
                                     connectionstyle="arc3,rad=-0.25"))
    for (x, y), t in zip(pos, nodos):
        ax.text(x, y, t, ha="center", va="center", fontsize=8,
                bbox=dict(boxstyle="round,pad=0.35", fc="white", ec=color, lw=1.3))
    ax.text(cx, cy, signo, ha="center", va="center", fontsize=20, fontweight="bold", color=color)
    ax.text(cx, cy + 2.35, titulo, ha="center", fontsize=10, fontweight="bold")


def ciclos():
    fig, ax = plt.subplots(figsize=(13, 5))
    ciclo(ax, 0, 0, ["Se repara\ntarde", "El bache crece\n(×1.8 en lluvias)", "Cuesta más\nrepararlo",
                     "El presupuesto\nalcanza para\nmenos baches", "Más baches\nen espera"],
          "1. Círculo vicioso del mantenimiento reactivo", "#c62828", "R")
    ciclo(ax, 4.6, 0, ["Pocos reportes\nen la zona", "Menos\natención", "Desconfianza\nen el gobierno",
                       "Nadie\nreporta"],
          "2. Invisibilidad de las zonas con poca participación", "#ef6c00", "R")
    ciclo(ax, 9.2, 0, ["SIPA prioriza\ncon evidencia", "Reparación\npreventiva", "Ahorro y menos\naccidentes",
                       "Confianza y\nmás reportes", "Mejores\ndatos"],
          "3. Círculo virtuoso que propone SIPA", "#2e7d32", "R")
    ax.set_xlim(-2.3, 11.5)
    ax.set_ylim(-2.2, 2.8)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(SALIDA / "g2_ciclos.png", dpi=170)
    plt.close(fig)


def main():
    SALIDA.mkdir(parents=True, exist_ok=True)
    mapa_red()
    ciclos()
    print("Gráficas generadas en", SALIDA)


if __name__ == "__main__":
    main()
