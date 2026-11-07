"""
SIPA · Estructuras de Datos
Pruebas de correctitud de cada estructura (sección 11 del avance).

Uso (desde la carpeta del proyecto):
    python estructuras/pruebas.py

Desarrollado con apoyo de IA generativa (Claude, de Anthropic), con autorización de la
docente y crédito declarado. El equipo revisó, probó y es responsable del código.
"""

import random
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from avl import ArbolAVL                      # noqa: E402
from grafo import GrafoVial, grafo_de_celdas  # noqa: E402
from heap import ColaFIFO, MaxHeap, MinHeap   # noqa: E402
from lista_enlazada import ListaReportes      # noqa: E402
from modelos import Reporte                   # noqa: E402
from pila import PilaDecisiones               # noqa: E402
from sipa_ed import SistemaSIPA               # noqa: E402
from tabla_hash import TablaHash              # noqa: E402


class PruebaLista(unittest.TestCase):
    def test_insertar_eliminar_fusionar(self):
        l = ListaReportes()
        nodos = [l.insertar_final(i) for i in range(5)]
        l.eliminar(nodos[2])                      # en medio
        l.eliminar(nodos[0])                      # cabeza
        l.eliminar(nodos[4])                      # cola
        self.assertEqual(list(l), [1, 3])
        self.assertEqual(list(l.recorrer_inverso()), [3, 1])
        otra = ListaReportes()
        otra.insertar_final(9)
        l.fusionar(otra)
        self.assertEqual(list(l), [1, 3, 9])
        self.assertEqual(len(l), 3)
        self.assertEqual(len(otra), 0)


class PruebaTablaHash(unittest.TestCase):
    def test_buscar_y_rehash(self):
        t = TablaHash(capacidad=4)
        for i in range(1000):
            t.insertar((i, -i), i)
        self.assertEqual(len(t), 1000)
        self.assertTrue(t.factor_carga() <= TablaHash.FACTOR_MAXIMO)
        self.assertGreater(t.rehashes, 0)
        self.assertEqual(t.buscar((500, -500)), 500)
        self.assertIsNone(t.buscar((5000, 1)))
        t.insertar((500, -500), "nuevo")          # reemplazo, no duplica
        self.assertEqual(t.buscar((500, -500)), "nuevo")
        self.assertEqual(len(t), 1000)


class PruebaAVL(unittest.TestCase):
    def test_balanceado_y_ordenado(self):
        a = ArbolAVL()
        claves = list(range(2000))                 # el peor caso para un árbol sin balancear
        for k in claves:
            a.insertar(k, str(k))
        self.assertTrue(a.esta_balanceado())
        self.assertLessEqual(a.altura(), 1.44 * (2000).bit_length())
        self.assertEqual(a.en_orden(), claves)
        self.assertEqual(a.buscar(1234), "1234")
        self.assertEqual([k for k, _ in a.rango(10, 15)], [10, 11, 12, 13, 14, 15])

    def test_aleatorio(self):
        a = ArbolAVL()
        azar = random.Random(1)
        claves = azar.sample(range(100_000), 3000)
        for k in claves:
            a.insertar(k, k)
        self.assertTrue(a.esta_balanceado())
        self.assertEqual(a.en_orden(), sorted(claves))


class PruebaHeap(unittest.TestCase):
    def test_extrae_siempre_el_mayor(self):
        h = MaxHeap()
        azar = random.Random(7)
        valores = [azar.random() for _ in range(500)]
        for i, v in enumerate(valores):
            h.insertar(i, v)
            self.assertTrue(h.es_valido())
        salida = [h.extraer_max()[0] for _ in range(500)]
        self.assertEqual(salida, sorted(valores, reverse=True))

    def test_actualizar_prioridad(self):
        h = MaxHeap()
        for i, v in enumerate([0.3, 0.8, 0.5]):
            h.insertar(i, v)
        h.actualizar(0, 0.95)                      # el bache 0 sube al frente
        self.assertEqual(h.ver_max()[2], 0)
        h.actualizar(0, 0.10)                      # y luego baja
        self.assertTrue(h.es_valido())
        self.assertEqual(h.extraer_max()[2], 1)

    def test_ejemplo_del_avance(self):
        # Tabla del avance: FIFO atiende R4 (el más grave) en 4.º lugar; el heap, en 1.º
        ipu = {"R1": 0.31, "R2": 0.84, "R3": 0.52, "R4": 0.91, "R5": 0.67}
        h, fifo = MaxHeap(), ColaFIFO()
        for r, v in ipu.items():
            h.insertar(r, v)
            fifo.encolar(r)
        self.assertEqual([h.extraer_max()[2] for _ in range(5)], ["R4", "R2", "R5", "R3", "R1"])
        self.assertEqual([fifo.desencolar() for _ in range(5)], ["R1", "R2", "R3", "R4", "R5"])

    def test_min_heap(self):
        m = MinHeap()
        for v in [5, 1, 4, 2, 3]:
            m.insertar(v, str(v))
        self.assertEqual([m.extraer_min()[0] for _ in range(5)], [1, 2, 3, 4, 5])


class PruebaGrafo(unittest.TestCase):
    def test_dijkstra_a_mano(self):
        # Grafo pequeño resuelto a mano: A-B 4, A-C 1, C-B 2, B-D 5, C-D 8 → A→C→B→D = 8
        g = GrafoVial()
        for v in "ABCD":
            g.agregar_vertice(v, 0, 0)
        for u, v, p in [("A", "B", 4), ("A", "C", 1), ("C", "B", 2), ("B", "D", 5), ("C", "D", 8)]:
            g.agregar_arista(u, v, p)
        dist, previo = g.dijkstra("A")
        self.assertEqual(dist, {"A": 0, "B": 3, "C": 1, "D": 8})
        self.assertEqual(GrafoVial.camino(previo, "A", "D"), ["A", "C", "B", "D"])
        self.assertEqual(len(g.dfs("A")), 4)

    def test_cuadricula(self):
        celdas = {(f, c): (19 + f * 0.00225, -99 + c * 0.0024) for f in range(5) for c in range(5)}
        g = grafo_de_celdas(celdas)
        self.assertEqual(len(g), 25)
        self.assertEqual(g.num_aristas(), 2 * 5 * 4 + 2 * 4 * 4)   # horizontales+verticales+diagonales
        ruta, metros = g.recorrido_vecino_cercano((0, 0), [(4, 4), (0, 4), (4, 0)])
        self.assertEqual(ruta[0], (0, 0))
        self.assertEqual(sorted(ruta[1:]), [(0, 4), (4, 0), (4, 4)])
        self.assertGreater(metros, 0)


class PruebaSistema(unittest.TestCase):
    def setUp(self):
        self.s = SistemaSIPA(riesgo=TablaHash())

    def reporte(self, folio, dia, lat, lon):
        return Reporte(folio, date(2019, 7, dia), lat, lon, "COYOACAN", "F000_C000")

    def test_duplicado_vecino_y_reincidencia(self):
        b1, t1 = self.s.registrar(self.reporte(1, 1, 19.30000, -99.15000))
        _, t2 = self.s.registrar(self.reporte(2, 5, 19.30001, -99.15011))    # ≈ 11 m, celda vecina
        self.assertEqual((t1, t2), ("NUEVO", "DUPLICADO"))
        self.assertEqual(b1.num_reportes, 2)
        b1.reparar(date(2019, 7, 6))
        _, t3 = self.s.registrar(self.reporte(3, 20, 19.30000, -99.15000))   # mismo lugar, ya reparado
        self.assertEqual(t3, "REINCIDENCIA")
        _, t4 = self.s.registrar(self.reporte(4, 21, 19.40000, -99.15000))   # lejos
        self.assertEqual(t4, "NUEVO")

    def test_pila_deshacer_rehacer(self):
        b, _ = self.s.registrar(self.reporte(1, 1, 19.3, -99.15))
        self.s.registrar(self.reporte(2, 1, 19.4, -99.15))
        pila = PilaDecisiones(self.s.heap, self.s.baches)
        antes = b.prioridad
        with self.assertRaises(ValueError):
            pila.ajustar(b.id, 0.99, "", "supervisora")             # sin motivo no se permite
        pila.ajustar(b.id, 0.99, "Acceso a hospital", "supervisora")
        self.assertEqual(self.s.heap.ver_max()[2], b.id)
        pila.deshacer()
        self.assertEqual(b.prioridad, antes)
        pila.rehacer()
        self.assertEqual(b.prioridad, 0.99)
        self.assertEqual([e for e, _ in pila.bitacora], ["AJUSTE", "DESHACER", "REHACER"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
