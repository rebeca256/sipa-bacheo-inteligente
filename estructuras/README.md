# SIPA · Prototipo de Estructuras de Datos

Prototipo funcional del procesamiento de reportes de baches de SIPA: registro, eliminación de
duplicados, cola de prioridad, deshacer decisiones y rutas de las brigadas. Implementa el diseño
del avance `avance2_PP_incidente_ED.docx` (secciones 7 a 11).

> **Declaración de uso de IA.** Este código se desarrolló con apoyo de IA generativa
> (Claude, de Anthropic), con autorización de la docente y dando el crédito correspondiente.
> El equipo revisó, ejecutó y probó el código, y es responsable de su contenido.

## Archivos

| Archivo | Tema de la UCA | Contenido |
|---|---|---|
| `modelos.py` | A. POO | Clases `Reporte`, `Bache` (IPU, envejecimiento, semáforo) y `Brigada` |
| `pila.py` | B. Pilas | `Pila` y `PilaDecisiones`: deshacer y rehacer ajustes del supervisor, con motivo obligatorio |
| `avl.py` | C. Recursividad, G. Árboles | Árbol AVL: inserción recursiva con rotaciones, recorrido en orden, búsqueda por rango |
| `tabla_hash.py` | D. Conjuntos | Tabla hash con encadenamiento y rehash al pasar 0.75 de carga; `Conjunto` sobre ella |
| `heap.py` | E. Colas, G. Árboles | `MaxHeap` con actualización de prioridad, `MinHeap` para Dijkstra y `ColaFIFO` de línea base |
| `lista_enlazada.py` | F. Listas enlazadas | Lista doblemente enlazada: insertar, eliminar y fusionar en O(1) |
| `grafo.py` | H. Grafos | Grafo con lista de adyacencia, Dijkstra, DFS recursivo y vecino más cercano |
| `sipa_ed.py` | Integración | `SistemaSIPA`: flujo completo de un reporte |
| `pruebas.py` | Correctitud | 12 pruebas (heap, AVL balanceado, Dijkstra a mano, duplicados, deshacer…) |
| `experimentos.py` | Eficiencia e impacto | Tiempos de búsqueda, desduplicación, simulación FIFO vs. SIPA, rutas |

Todas las estructuras están programadas desde cero, sin `heapq` ni otras bibliotecas que ya
las resuelvan. Se usan `csv` para leer los datos y `matplotlib` solo para las gráficas.

## Cómo ejecutar (desde la carpeta del proyecto)

```
python estructuras/pruebas.py        # pruebas de correctitud
python estructuras/experimentos.py   # experimentos con los datos reales (≈ 1 minuto)
```

Los resultados quedan en `estructuras/resultados/`.

## Datos

- `datos/limpios/base_maestra_limpia.csv`: 34,945 reportes reales de la CDMX (sin periodos atípicos).
- `probabilidad/resultados/t4_riesgo_72h_por_celda.csv`: riesgo de accidente a 72 h por celda.
- La severidad del bache es sintética (la base no la trae), igual que en la base SIPA.
- El IPU del prototipo es una versión simplificada (severidad 0.45, riesgo a 72 h 0.40, reportes
  acotados 0.15); el IPU completo de 10 criterios está en la base de datos SQL Server.
