"""
SIPA · Estructuras de Datos
Núcleo del prototipo: registra reportes, elimina duplicados y arma el plan de atención.

Flujo de un reporte:
  1. Entra a la lista doblemente enlazada.                        O(1)
  2. Se busca su ubicación y las 8 vecinas en la tabla hash.        9 × O(1)
  3. Si hay un bache con reporte en los últimos 30 días, se suma a él (duplicado).
     Si hay uno más viejo, se registra como reincidencia. Si no, es un bache nuevo.
  4. El bache entra (o se actualiza) en el max-heap por prioridad.  O(log n)

Desarrollado con apoyo de IA generativa (Claude, de Anthropic), con autorización de la
docente y crédito declarado. El equipo revisó, probó y es responsable del código.
"""

import csv
import random
from pathlib import Path

from heap import MaxHeap
from lista_enlazada import ListaReportes
from modelos import Bache, Reporte, a_fecha
from tabla_hash import TablaHash

RAIZ = Path(__file__).resolve().parent.parent
RUTA_REPORTES = RAIZ / "datos/limpios/base_maestra_limpia.csv"
RUTA_RIESGO = RAIZ / "probabilidad/resultados/t4_riesgo_72h_por_celda.csv"

DIAS_DUPLICADO = 30
RIESGO_SIN_DATO = 0.06       # riesgo base del modelo para celdas sin accidentes registrados
VECINAS = [(dl, dn) for dl in (-1, 0, 1) for dn in (-1, 0, 1)]


def leer_reportes(ruta=RUTA_REPORTES, limite=None):
    """Lee la base limpia (sin periodos atípicos) en orden de llegada."""
    reportes = []
    with open(ruta, encoding="utf-8-sig", newline="") as f:
        for fila in csv.DictReader(f):
            if fila["periodo_atipico"] == "True":
                continue
            reportes.append(Reporte(int(fila["id_folio"]), a_fecha(fila["fecha_solicitud"]),
                                    float(fila["latitud"]), float(fila["longitud"]),
                                    fila["alcaldia"], fila["celda_id"]))
    reportes.sort(key=lambda r: (r.fecha, r.id_folio))          # ordenamiento por fecha de llegada
    return reportes[:limite] if limite else reportes


def leer_riesgo(ruta=RUTA_RIESGO):
    """Riesgo normalizado a 72 h por celda de 250 m (resultado del modelo de Probabilidad)."""
    riesgo = TablaHash(capacidad=16_384)
    if Path(ruta).exists():
        with open(ruta, encoding="utf-8", newline="") as f:
            for fila in csv.DictReader(f):
                riesgo.insertar(fila["celda_id"], float(fila["v_riesgo_72h"]))
    return riesgo


class SistemaSIPA:
    def __init__(self, riesgo=None, semilla=2026):
        self.reportes = ListaReportes()
        self.por_ubicacion = TablaHash()     # clave ≈ 11 m → bache más reciente en ese punto
        self.baches = TablaHash()            # id → bache
        self.lista_baches = []               # en orden de creación (para la cola FIFO)
        self.heap = MaxHeap()
        self.riesgo = riesgo if riesgo is not None else leer_riesgo()
        self.azar = random.Random(semilla)   # severidad sintética reproducible
        self.duplicados = 0
        self.reincidencias = 0

    def _severidad(self):
        # Distribución sintética de severidad 1 a 5 (la base no la trae; ver limitaciones)
        return self.azar.choices([1, 2, 3, 4, 5], weights=[15, 30, 30, 17, 8])[0]

    def buscar_cercano(self, clave):
        """Revisa la celda de ≈ 11 m y sus 8 vecinas; devuelve el bache más reciente encontrado."""
        mejor = None
        for dl, dn in VECINAS:
            b = self.por_ubicacion.buscar((clave[0] + dl, clave[1] + dn))
            if b is not None and (mejor is None or b.fecha_ultimo_reporte > mejor.fecha_ultimo_reporte):
                mejor = b
        return mejor

    def registrar(self, reporte, usar_heap=True):
        self.reportes.insertar_final(reporte)
        clave = reporte.clave_celda()
        existente = self.buscar_cercano(clave)

        if existente is not None and existente.estado == "PENDIENTE" and \
                (reporte.fecha - existente.fecha_ultimo_reporte).days < DIAS_DUPLICADO:
            existente.agregar_reporte(reporte)
            self.duplicados += 1
            if usar_heap and self.heap.contiene(existente.id):
                self.heap.actualizar(existente.id, existente.prioridad_efectiva(reporte.fecha),
                                     existente.dias_en_espera(reporte.fecha))
            return existente, "DUPLICADO"

        reincidente = existente is not None
        riesgo = self.riesgo.buscar(reporte.celda_id)
        bache = Bache(len(self.lista_baches) + 1, reporte, self._severidad(),
                      riesgo if riesgo is not None else RIESGO_SIN_DATO, reincidente)
        self.baches.insertar(bache.id, bache)
        self.lista_baches.append(bache)
        self.por_ubicacion.insertar(clave, bache)
        if reincidente:
            self.reincidencias += 1
        if usar_heap:
            self.heap.insertar(bache.id, bache.prioridad, 0)
        return bache, "REINCIDENCIA" if reincidente else "NUEVO"

    def envejecer(self, hoy):
        """Recalcula la prioridad efectiva de todo lo que está en el heap. O(n log n)."""
        for _, _, ident in list(self.heap.arreglo):
            b = self.baches.buscar(ident)
            b.prioridad = b.prioridad_efectiva(hoy)
            self.heap.actualizar(ident, b.prioridad, b.dias_en_espera(hoy))

    def plan_del_dia(self, capacidad):
        """Extrae los baches de mayor prioridad que caben en la capacidad del día."""
        plan = []
        while len(plan) < capacidad and len(self.heap):
            _, _, ident = self.heap.extraer_max()
            plan.append(self.baches.buscar(ident))
        return plan
