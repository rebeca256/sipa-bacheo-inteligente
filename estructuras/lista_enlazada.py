"""
SIPA · Estructuras de Datos
Lista doblemente enlazada de reportes entrantes (tema F. Listas enlazadas).

Desarrollado con apoyo de IA generativa (Claude, de Anthropic), con autorización de la
docente y crédito declarado. El equipo revisó, probó y es responsable del código.
"""


class NodoReporte:
    """Nodo de la lista: guarda un reporte y apunta al anterior y al siguiente."""

    def __init__(self, reporte):
        self.reporte = reporte
        self.anterior = None
        self.siguiente = None


class ListaReportes:
    """Lista doblemente enlazada con referencia a la cabeza y a la cola."""

    def __init__(self):
        self.cabeza = None
        self.cola = None
        self.tamano = 0

    def insertar_final(self, reporte):
        """Agrega un reporte al final. O(1): no hay que recorrer la lista."""
        nodo = NodoReporte(reporte)
        if self.cola is None:
            self.cabeza = self.cola = nodo
        else:
            nodo.anterior = self.cola
            self.cola.siguiente = nodo
            self.cola = nodo
        self.tamano += 1
        return nodo

    def eliminar(self, nodo):
        """Quita un nodo conocido (por ejemplo, un reporte cancelado). O(1)."""
        if nodo.anterior is not None:
            nodo.anterior.siguiente = nodo.siguiente
        else:
            self.cabeza = nodo.siguiente
        if nodo.siguiente is not None:
            nodo.siguiente.anterior = nodo.anterior
        else:
            self.cola = nodo.anterior
        nodo.anterior = nodo.siguiente = None
        self.tamano -= 1
        return nodo.reporte

    def fusionar(self, otra):
        """Pega otra lista al final de esta (por ejemplo, reportes de otro canal). O(1)."""
        if otra.cabeza is None:
            return
        if self.cola is None:
            self.cabeza, self.cola = otra.cabeza, otra.cola
        else:
            self.cola.siguiente = otra.cabeza
            otra.cabeza.anterior = self.cola
            self.cola = otra.cola
        self.tamano += otra.tamano
        otra.cabeza = otra.cola = None
        otra.tamano = 0

    def __iter__(self):
        actual = self.cabeza
        while actual is not None:
            yield actual.reporte
            actual = actual.siguiente

    def recorrer_inverso(self):
        actual = self.cola
        while actual is not None:
            yield actual.reporte
            actual = actual.anterior

    def __len__(self):
        return self.tamano
