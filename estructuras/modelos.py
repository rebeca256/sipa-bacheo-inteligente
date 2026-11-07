"""
SIPA · Estructuras de Datos
Clases del dominio (tema A. Programación orientada a objetos): Reporte, Bache y Brigada.

Desarrollado con apoyo de IA generativa (Claude, de Anthropic), con autorización de la
docente y crédito declarado. El equipo revisó, probó y es responsable del código.
"""

import math
from datetime import date

# Pesos del IPU simplificado del prototipo (el IPU completo, con 10 criterios, vive en la base SIPA)
PESO_SEVERIDAD = 0.45
PESO_RIESGO = 0.40
PESO_REPORTES = 0.15
TOPE_REPORTES = 10          # a partir de 10 reportes ya no sube (evita el sesgo de participación)

# Envejecimiento acotado: prioridad = IPU + BETA · mín(días, D) / D
BETA = 0.10
D_MAX = 60

UMBRAL_ROJO = 0.60
UMBRAL_AMARILLO = 0.40


class Reporte:
    def __init__(self, id_folio, fecha, latitud, longitud, alcaldia, celda_id):
        self.id_folio = id_folio
        self.fecha = fecha
        self.latitud = latitud
        self.longitud = longitud
        self.alcaldia = alcaldia
        self.celda_id = celda_id

    def clave_celda(self):
        """Ubicación redondeada a 4 decimales (≈ 11 m), como enteros para comparar sin errores de redondeo."""
        return (round(self.latitud * 10_000), round(self.longitud * 10_000))


class Bache:
    def __init__(self, ident, reporte, severidad, riesgo_72h, reincidente=False):
        self.id = ident
        self.clave_celda = reporte.clave_celda()
        self.latitud = reporte.latitud
        self.longitud = reporte.longitud
        self.alcaldia = reporte.alcaldia
        self.celda_id = reporte.celda_id
        self.severidad = severidad            # 1 a 5 (sintética, como en la base SIPA)
        self.riesgo_72h = riesgo_72h          # 0 a 1, del modelo de Probabilidad
        self.reincidente = reincidente
        self.fecha_primer_reporte = reporte.fecha
        self.fecha_ultimo_reporte = reporte.fecha
        self.num_reportes = 1
        self.estado = "PENDIENTE"
        self.fecha_reparacion = None
        self.ipu = self.calcular_ipu()
        self.prioridad = self.ipu

    def agregar_reporte(self, reporte):
        self.num_reportes += 1
        self.fecha_ultimo_reporte = max(self.fecha_ultimo_reporte, reporte.fecha)
        self.ipu = self.calcular_ipu()

    def calcular_ipu(self):
        v_sev = (self.severidad - 1) / 4
        v_rep = min(math.log(1 + self.num_reportes) / math.log(1 + TOPE_REPORTES), 1.0)
        return round(PESO_SEVERIDAD * v_sev + PESO_RIESGO * self.riesgo_72h + PESO_REPORTES * v_rep, 4)

    def dias_en_espera(self, hoy):
        return (hoy - self.fecha_primer_reporte).days

    def prioridad_efectiva(self, hoy):
        """IPU más envejecimiento acotado: un verde que espera mucho sube, pero no rebasa a un rojo."""
        return round(self.ipu + BETA * min(self.dias_en_espera(hoy), D_MAX) / D_MAX, 4)

    def semaforo(self):
        if self.ipu >= UMBRAL_ROJO:
            return "ROJO"
        return "AMARILLO" if self.ipu >= UMBRAL_AMARILLO else "VERDE"

    def reparar(self, hoy):
        self.estado = "REPARADO"
        self.fecha_reparacion = hoy

    def __repr__(self):
        return f"Bache({self.id}, IPU={self.ipu}, {self.semaforo()}, {self.alcaldia})"


class Brigada:
    def __init__(self, ident, base, capacidad_diaria):
        self.id = ident
        self.base = base                      # vértice del grafo donde inicia
        self.capacidad_diaria = capacidad_diaria
        self.ruta = []
        self.metros = 0.0

    def asignar(self, grafo, destinos):
        self.ruta, self.metros = grafo.recorrido_vecino_cercano(self.base, destinos)
        return self.ruta


def a_fecha(texto):
    a, m, d = texto[:10].split("-")
    return date(int(a), int(m), int(d))
