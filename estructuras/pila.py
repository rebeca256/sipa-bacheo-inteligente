"""
SIPA · Estructuras de Datos
Pila de decisiones de la persona supervisora, para deshacer y rehacer (tema B. Pilas).
Cada ajuste exige un motivo, que queda en la bitácora.

Desarrollado con apoyo de IA generativa (Claude, de Anthropic), con autorización de la
docente y crédito declarado. El equipo revisó, probó y es responsable del código.
"""


class Pila:
    def __init__(self):
        self._elementos = []

    def apilar(self, elemento):        # O(1)
        self._elementos.append(elemento)

    def desapilar(self):               # O(1)
        return self._elementos.pop() if self._elementos else None

    def tope(self):
        return self._elementos[-1] if self._elementos else None

    def esta_vacia(self):
        return not self._elementos

    def __len__(self):
        return len(self._elementos)


class PilaDecisiones:
    """Historial de cambios de prioridad: deshacer y rehacer en O(1) (más la actualización del heap)."""

    def __init__(self, heap, baches):
        self.heap = heap
        self.baches = baches        # tabla hash id → Bache
        self.hechas = Pila()
        self.deshechas = Pila()
        self.bitacora = []          # registro permanente, nunca se borra

    def ajustar(self, id_bache, nueva_prioridad, motivo, persona):
        if not motivo or not motivo.strip():
            raise ValueError("Todo ajuste de prioridad debe tener un motivo.")
        bache = self.baches.buscar(id_bache)
        decision = dict(id_bache=id_bache, antes=bache.prioridad, despues=nueva_prioridad,
                        motivo=motivo, persona=persona)
        self._aplicar(id_bache, nueva_prioridad)
        self.hechas.apilar(decision)
        self.deshechas = Pila()     # una decisión nueva invalida lo que se podía rehacer
        self.bitacora.append(("AJUSTE", decision))

    def deshacer(self):
        decision = self.hechas.desapilar()
        if decision is None:
            return None
        self._aplicar(decision["id_bache"], decision["antes"])
        self.deshechas.apilar(decision)
        self.bitacora.append(("DESHACER", decision))
        return decision

    def rehacer(self):
        decision = self.deshechas.desapilar()
        if decision is None:
            return None
        self._aplicar(decision["id_bache"], decision["despues"])
        self.hechas.apilar(decision)
        self.bitacora.append(("REHACER", decision))
        return decision

    def _aplicar(self, id_bache, prioridad):
        bache = self.baches.buscar(id_bache)
        bache.prioridad = prioridad
        if self.heap.contiene(id_bache):
            self.heap.actualizar(id_bache, prioridad)
