"""
SIPA · Estructuras de Datos
Árbol AVL indexado por ubicación (temas C. Recursividad y G. Árboles). Sirve para comparar
contra la tabla hash: garantiza O(log n) y permite recorrer en orden y buscar por rango.

Desarrollado con apoyo de IA generativa (Claude, de Anthropic), con autorización de la
docente y crédito declarado. El equipo revisó, probó y es responsable del código.
"""


class NodoAVL:
    def __init__(self, clave, valor):
        self.clave = clave
        self.valor = valor
        self.izq = None
        self.der = None
        self.altura = 1


def _altura(nodo):
    return nodo.altura if nodo else 0


def _actualizar(nodo):
    nodo.altura = 1 + max(_altura(nodo.izq), _altura(nodo.der))


def _balance(nodo):
    return _altura(nodo.izq) - _altura(nodo.der) if nodo else 0


class ArbolAVL:
    def __init__(self):
        self.raiz = None
        self.n = 0
        self.comparaciones = 0      # para medir el costo real de las búsquedas
        self.rotaciones = 0

    # --- rotaciones -------------------------------------------------------
    def _rotar_der(self, y):
        x = y.izq
        y.izq = x.der
        x.der = y
        _actualizar(y)
        _actualizar(x)
        self.rotaciones += 1
        return x

    def _rotar_izq(self, x):
        y = x.der
        x.der = y.izq
        y.izq = x
        _actualizar(x)
        _actualizar(y)
        self.rotaciones += 1
        return y

    # --- inserción recursiva ---------------------------------------------
    def insertar(self, clave, valor):
        self.raiz = self._insertar(self.raiz, clave, valor)

    def _insertar(self, nodo, clave, valor):
        if nodo is None:
            self.n += 1
            return NodoAVL(clave, valor)
        if clave < nodo.clave:
            nodo.izq = self._insertar(nodo.izq, clave, valor)
        elif clave > nodo.clave:
            nodo.der = self._insertar(nodo.der, clave, valor)
        else:
            nodo.valor = valor          # la clave ya existe: se reemplaza
            return nodo

        _actualizar(nodo)
        b = _balance(nodo)
        if b > 1 and clave < nodo.izq.clave:            # caso izquierda-izquierda
            return self._rotar_der(nodo)
        if b < -1 and clave > nodo.der.clave:           # caso derecha-derecha
            return self._rotar_izq(nodo)
        if b > 1 and clave > nodo.izq.clave:            # caso izquierda-derecha
            nodo.izq = self._rotar_izq(nodo.izq)
            return self._rotar_der(nodo)
        if b < -1 and clave < nodo.der.clave:           # caso derecha-izquierda
            nodo.der = self._rotar_der(nodo.der)
            return self._rotar_izq(nodo)
        return nodo

    # --- búsquedas ----------------------------------------------------------
    def buscar(self, clave):
        """Búsqueda iterativa. O(log n) garantizado porque el árbol está balanceado."""
        nodo = self.raiz
        while nodo is not None:
            self.comparaciones += 1
            if clave == nodo.clave:
                return nodo.valor
            nodo = nodo.izq if clave < nodo.clave else nodo.der
        return None

    def en_orden(self):
        """Recorrido en orden (recursivo): devuelve las claves ordenadas."""
        resultado = []
        self._en_orden(self.raiz, resultado)
        return resultado

    def _en_orden(self, nodo, resultado):
        if nodo is None:
            return
        self._en_orden(nodo.izq, resultado)
        resultado.append(nodo.clave)
        self._en_orden(nodo.der, resultado)

    def rango(self, minimo, maximo):
        """Claves entre minimo y maximo; poda las ramas que no pueden contenerlas."""
        resultado = []
        self._rango(self.raiz, minimo, maximo, resultado)
        return resultado

    def _rango(self, nodo, minimo, maximo, resultado):
        if nodo is None:
            return
        if minimo < nodo.clave:
            self._rango(nodo.izq, minimo, maximo, resultado)
        if minimo <= nodo.clave <= maximo:
            resultado.append((nodo.clave, nodo.valor))
        if nodo.clave < maximo:
            self._rango(nodo.der, minimo, maximo, resultado)

    def altura(self):
        return _altura(self.raiz)

    def esta_balanceado(self):
        """Verifica la propiedad AVL en todo el árbol (para las pruebas)."""
        def revisar(nodo):
            if nodo is None:
                return True, 0
            ok_i, h_i = revisar(nodo.izq)
            ok_d, h_d = revisar(nodo.der)
            return ok_i and ok_d and abs(h_i - h_d) <= 1, 1 + max(h_i, h_d)
        return revisar(self.raiz)[0]

    def __len__(self):
        return self.n
