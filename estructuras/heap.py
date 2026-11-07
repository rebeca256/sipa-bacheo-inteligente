"""
SIPA · Estructuras de Datos
Cola de prioridad con montículo binario (temas E. Colas y G. Árboles).
- MaxHeap: orden de atención por prioridad (IPU con envejecimiento). Guarda la posición de
  cada bache para actualizar su prioridad en O(log n).
- MinHeap: lo usa Dijkstra para sacar el vértice más cercano.
También incluye la cola FIFO que sirve de línea base.

Desarrollado con apoyo de IA generativa (Claude, de Anthropic), con autorización de la
docente y crédito declarado. El equipo revisó, probó y es responsable del código.
"""


class MaxHeap:
    """Arreglo donde los hijos del nodo i están en 2i+1 y 2i+2 y cada padre ≥ sus hijos."""

    def __init__(self):
        self.arreglo = []           # elementos (prioridad, desempate, id)
        self.posicion = {}          # id → índice en el arreglo

    def _mayor(self, i, j):
        return self.arreglo[i][:2] > self.arreglo[j][:2]

    def _intercambiar(self, i, j):
        a = self.arreglo
        a[i], a[j] = a[j], a[i]
        self.posicion[a[i][2]] = i
        self.posicion[a[j][2]] = j

    def _subir(self, i):
        while i > 0:
            padre = (i - 1) // 2
            if not self._mayor(i, padre):
                break
            self._intercambiar(i, padre)
            i = padre

    def _bajar(self, i):
        n = len(self.arreglo)
        while True:
            mayor, izq, der = i, 2 * i + 1, 2 * i + 2
            if izq < n and self._mayor(izq, mayor):
                mayor = izq
            if der < n and self._mayor(der, mayor):
                mayor = der
            if mayor == i:
                return
            self._intercambiar(i, mayor)
            i = mayor

    def insertar(self, ident, prioridad, desempate=0.0):
        """O(log n). El desempate (por ejemplo, días en espera) decide entre prioridades iguales."""
        self.arreglo.append((prioridad, desempate, ident))
        self.posicion[ident] = len(self.arreglo) - 1
        self._subir(len(self.arreglo) - 1)

    def ver_max(self):
        """O(1)."""
        return self.arreglo[0] if self.arreglo else None

    def extraer_max(self):
        """O(log n): el último pasa a la raíz y baja."""
        if not self.arreglo:
            return None
        self._intercambiar(0, len(self.arreglo) - 1)
        maximo = self.arreglo.pop()
        del self.posicion[maximo[2]]
        if self.arreglo:
            self._bajar(0)
        return maximo

    def actualizar(self, ident, prioridad, desempate=0.0):
        """Cambia la prioridad de un elemento que ya está en el heap. O(log n)."""
        i = self.posicion[ident]
        anterior = self.arreglo[i]
        self.arreglo[i] = (prioridad, desempate, ident)
        if (prioridad, desempate) > anterior[:2]:
            self._subir(i)
        else:
            self._bajar(i)

    def contiene(self, ident):
        return ident in self.posicion

    def es_valido(self):
        """Comprueba la propiedad de heap (para las pruebas)."""
        a = self.arreglo
        return all(a[(i - 1) // 2][:2] >= a[i][:2] for i in range(1, len(a)))

    def __len__(self):
        return len(self.arreglo)


class MinHeap:
    """Montículo de mínimos sencillo para Dijkstra: elementos (distancia, vértice)."""

    def __init__(self):
        self.a = []

    def insertar(self, distancia, vertice):
        a = self.a
        a.append((distancia, vertice))
        i = len(a) - 1
        while i > 0 and a[(i - 1) // 2] > a[i]:
            p = (i - 1) // 2
            a[i], a[p] = a[p], a[i]
            i = p

    def extraer_min(self):
        a = self.a
        a[0], a[-1] = a[-1], a[0]
        minimo = a.pop()
        i, n = 0, len(a)
        while True:
            menor, izq, der = i, 2 * i + 1, 2 * i + 2
            if izq < n and a[izq] < a[menor]:
                menor = izq
            if der < n and a[der] < a[menor]:
                menor = der
            if menor == i:
                return minimo
            a[i], a[menor] = a[menor], a[i]
            i = menor

    def __len__(self):
        return len(self.a)


class ColaFIFO:
    """Cola por orden de llegada, con dos índices sobre un arreglo (línea base del incidente)."""

    def __init__(self):
        self.elementos = []
        self.frente = 0

    def encolar(self, elemento):
        self.elementos.append(elemento)

    def desencolar(self):
        if self.frente == len(self.elementos):
            return None
        e = self.elementos[self.frente]
        self.frente += 1
        return e

    def __len__(self):
        return len(self.elementos) - self.frente
