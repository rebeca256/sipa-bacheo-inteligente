"""
SIPA · Estructuras de Datos
Red vial como grafo ponderado con lista de adyacencia (tema H. Grafos).
- Dijkstra con nuestro propio MinHeap: distancias mínimas desde la planta de asfalto.
- DFS recursivo: verifica que todos los baches sean alcanzables.
- Recorrido de la brigada con la heurística del vecino más cercano.

Mientras no se integre la red vial de OpenStreetMap o del INEGI, los vértices son los
centros de las celdas de 250 m y cada celda se conecta con sus 8 vecinas.

Desarrollado con apoyo de IA generativa (Claude, de Anthropic), con autorización de la
docente y crédito declarado. El equipo revisó, probó y es responsable del código.
"""

import math

from heap import MinHeap
from tabla_hash import Conjunto


def distancia_m(lat1, lon1, lat2, lon2):
    """Distancia aproximada en metros entre dos puntos (equirrectangular, suficiente a escala de ciudad)."""
    x = math.radians(lon2 - lon1) * math.cos(math.radians((lat1 + lat2) / 2))
    y = math.radians(lat2 - lat1)
    return 6_371_000 * math.hypot(x, y)


class GrafoVial:
    def __init__(self):
        self.adyacencia = {}        # vértice → lista de (vecino, peso)
        self.coordenadas = {}       # vértice → (lat, lon)

    def agregar_vertice(self, v, lat, lon):
        if v not in self.adyacencia:
            self.adyacencia[v] = []
            self.coordenadas[v] = (lat, lon)

    def agregar_arista(self, u, v, peso=None):
        """Arista no dirigida (las calles se recorren en ambos sentidos en este prototipo)."""
        if peso is None:
            peso = distancia_m(*self.coordenadas[u], *self.coordenadas[v])
        self.adyacencia[u].append((v, peso))
        self.adyacencia[v].append((u, peso))

    def dijkstra(self, origen):
        """Distancias mínimas desde origen. O((V + E) log V)."""
        dist = {v: math.inf for v in self.adyacencia}
        previo = {}
        dist[origen] = 0.0
        visitados = Conjunto()
        cola = MinHeap()
        cola.insertar(0.0, origen)
        while len(cola):
            d, u = cola.extraer_min()
            if u in visitados:
                continue
            visitados.agregar(u)
            for v, peso in self.adyacencia[u]:
                nueva = d + peso
                if nueva < dist[v]:
                    dist[v] = nueva
                    previo[v] = u
                    cola.insertar(nueva, v)
        return dist, previo

    @staticmethod
    def camino(previo, origen, destino):
        """Reconstruye el camino usando los predecesores que dejó Dijkstra."""
        camino = [destino]
        while camino[-1] != origen:
            if camino[-1] not in previo:
                return []
            camino.append(previo[camino[-1]])
        return camino[::-1]

    def dfs(self, origen, visitados=None):
        """Recorrido en profundidad recursivo; devuelve el conjunto de vértices alcanzables."""
        if visitados is None:
            visitados = Conjunto()
        visitados.agregar(origen)
        for v, _ in self.adyacencia[origen]:
            if v not in visitados:
                self.dfs(v, visitados)
        return visitados

    def recorrido_vecino_cercano(self, origen, destinos):
        """Ruta de la brigada: siempre va al bache pendiente más cercano por la red (Dijkstra desde cada parada)."""
        ruta, total = [origen], 0.0
        pendientes = list(destinos)
        actual = origen
        while pendientes:
            dist, _ = self.dijkstra(actual)
            siguiente = min(pendientes, key=lambda d: dist[d])
            total += dist[siguiente]
            ruta.append(siguiente)
            pendientes.remove(siguiente)
            actual = siguiente
        return ruta, total

    def num_aristas(self):
        return sum(len(l) for l in self.adyacencia.values()) // 2

    def __len__(self):
        return len(self.adyacencia)


def grafo_de_celdas(celdas):
    """Construye el grafo con todas las celdas (fila, col) → (lat, lon) de una zona y sus 8 vecinas."""
    g = GrafoVial()
    for (f, c), (lat, lon) in celdas.items():
        g.agregar_vertice((f, c), lat, lon)
    for (f, c) in celdas:
        for df, dc in [(0, 1), (1, -1), (1, 0), (1, 1)]:      # cada par se agrega una sola vez
            if (f + df, c + dc) in celdas:
                g.agregar_arista((f, c), (f + df, c + dc))
    return g
