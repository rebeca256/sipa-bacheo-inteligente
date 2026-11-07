"""
SIPA · Estructuras de Datos
Tabla hash con encadenamiento para detectar reportes duplicados (tema D. Conjuntos y
búsqueda eficiente). La clave es la ubicación redondeada a 4 decimales (≈ 11 m).

Desarrollado con apoyo de IA generativa (Claude, de Anthropic), con autorización de la
docente y crédito declarado. El equipo revisó, probó y es responsable del código.
"""


class TablaHash:
    """Cada cubeta es una lista de pares [clave, valor]. Se duplica si el factor de carga pasa de 0.75."""

    FACTOR_MAXIMO = 0.75

    def __init__(self, capacidad=16):
        self.m = capacidad
        self.n = 0
        self.cubetas = [[] for _ in range(self.m)]
        self.rehashes = 0

    def _indice(self, clave):
        # Función hash polinomial sobre el texto de la clave (no usamos dict de Python)
        h = 0
        for caracter in str(clave):
            h = (h * 31 + ord(caracter)) % 2_147_483_647
        return h % self.m

    def buscar(self, clave):
        """Devuelve el valor o None. O(1) en promedio."""
        for k, v in self.cubetas[self._indice(clave)]:
            if k == clave:
                return v
        return None

    def insertar(self, clave, valor):
        """Inserta o reemplaza. O(1) en promedio (amortizado por el rehash)."""
        cubeta = self.cubetas[self._indice(clave)]
        for par in cubeta:
            if par[0] == clave:
                par[1] = valor
                return
        cubeta.append([clave, valor])
        self.n += 1
        if self.n / self.m > self.FACTOR_MAXIMO:
            self._rehash()

    def _rehash(self):
        """Duplica el número de cubetas y reacomoda todo. O(n), pero ocurre pocas veces."""
        viejas = self.cubetas
        self.m *= 2
        self.cubetas = [[] for _ in range(self.m)]
        self.n = 0
        self.rehashes += 1
        for cubeta in viejas:
            for k, v in cubeta:
                self.insertar(k, v)

    def contiene(self, clave):
        return self.buscar(clave) is not None

    def factor_carga(self):
        return self.n / self.m

    def cubeta_mas_larga(self):
        return max(len(c) for c in self.cubetas)

    def __len__(self):
        return self.n


class Conjunto:
    """Conjunto construido sobre la tabla hash (pertenencia en O(1) promedio)."""

    def __init__(self):
        self._tabla = TablaHash()

    def agregar(self, elemento):
        self._tabla.insertar(elemento, True)

    def __contains__(self, elemento):
        return self._tabla.contiene(elemento)

    def __len__(self):
        return len(self._tabla)
