"""
SIPA - Segundo avance de Estructuras de Datos: prototipo funcional y plan de viabilidad.

El documento gira alrededor de las estructuras (lo que evalúa la UCA: «el cumplimiento de las
complejidades solicitadas y el uso de estructuras que faciliten la gestión de los datos»):
para cada una explica qué problema resuelve, muestra el código real (extraído del archivo, no
copiado a mano), su complejidad teórica y lo que midió el prototipo. Después, el plan de
viabilidad y las intervenciones, con las cifras de los resultados.

Uso (desde la carpeta del proyecto):
    python estructuras/pruebas.py
    python estructuras/experimentos.py
    python estructuras/viabilidad.py
    python scripts/generar_doc_viabilidad_ED.py
Salida:
    avance2_ED_plan_viabilidad.docx

Desarrollado con apoyo de IA generativa (Claude, de Anthropic), con autorización de la
docente y crédito declarado. El equipo revisó y es responsable del contenido.
"""

import ast
import csv
import json
import sys
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt

sys.path.insert(0, str(Path(__file__).parent))
from generar_doc_planeacion_bd import AZUL, parrafo, tabla, titulo, vinetas  # noqa: E402

ED = Path("estructuras")
RES = ED / "resultados"
SALIDA = "avance2_ED_plan_viabilidad.docx"

ACENTOS = {"Juarez": "Juárez", "Coyoacan": "Coyoacán", "Tlahuac": "Tláhuac", "Alvaro": "Álvaro",
           "Obregon": "Obregón", "Cuauhtemoc": "Cuauhtémoc", "De": "de", "La": "La"}


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def leer(ruta):
    return json.loads(Path(ruta).read_text(encoding="utf-8"))


def leer_csv(ruta):
    with open(ruta, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def nombre(texto):
    return " ".join(ACENTOS.get(w, w) for w in texto.title().split())


def pct(x):
    return f"{100 * x:.0f} %"


def m(x):
    return f"${x:,.0f}"


def mm(x):
    return f"${x / 1e6:,.2f} M"


def figura(doc, ruta, pie, ancho=15):
    doc.add_picture(str(ruta), width=Cm(ancho))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(pie)
    r.italic = True
    r.font.size = Pt(9)


def fuente(archivo, nombre_funcion, clase=None):
    """Código real de una función o método, tomado del archivo del prototipo."""
    texto = (ED / archivo).read_text(encoding="utf-8")
    arbol = ast.parse(texto)
    nodos = arbol.body
    if clase:
        nodos = next(n for n in arbol.body if isinstance(n, ast.ClassDef) and n.name == clase).body
    nodo = next(n for n in nodos if isinstance(n, ast.FunctionDef) and n.name == nombre_funcion)
    lineas = texto.splitlines()[nodo.lineno - 1:nodo.end_lineno]
    sangria = len(lineas[0]) - len(lineas[0].lstrip())
    return "\n".join(linea[sangria:] for linea in lineas)


def codigo(doc, texto, pie=None):
    """Bloque de código con el estilo «Codigo» (Consolas; exportar_pdf.py lo convierte en <pre>)."""
    if "Codigo" not in [s.name for s in doc.styles]:
        from docx.enum.style import WD_STYLE_TYPE
        estilo = doc.styles.add_style("Codigo", WD_STYLE_TYPE.PARAGRAPH)
        estilo.base_style = doc.styles["Normal"]
        estilo.font.name = "Consolas"
        estilo.font.size = Pt(8)
        estilo.paragraph_format.space_after = Pt(0)
        estilo.paragraph_format.left_indent = Cm(0.6)
    for linea in texto.strip("\n").split("\n"):
        doc.add_paragraph(linea if linea else " ", style="Codigo")
    if pie:
        p = doc.add_paragraph()
        r = p.add_run(pie)
        r.italic = True
        r.font.size = Pt(8.5)
    else:
        doc.add_paragraph()


def ficha(doc, problema, complejidad, medida):
    tabla(doc, ["Problema que resuelve", "Complejidad", "Lo que midió el prototipo"],
          [[problema, complejidad, medida]], [6.5, 3, 6.5])


# ---------------------------------------------------------------------------
# Secciones
# ---------------------------------------------------------------------------

def portada(doc):
    for texto, tam, neg in [
        ("Universidad Nacional Rosario Castellanos", 14, True),
        ("Licenciatura en Ciencia de Datos para Negocios", 12, False),
        ("Unidad Académica Chalco", 12, False),
        ("Tercer semestre · Semestre 2026-2", 12, False),
        ("", 12, False),
        ("Problema prototípico: Bacheo inteligente y priorización urbana", 12, False),
        ("SIPA", 28, True),
        ("Sistema Inteligente de Priorización Asfáltica", 14, False),
        ("", 12, False),
        ("Segundo avance · Estructuras de Datos", 14, True),
        ("Prototipo funcional y plan de viabilidad", 12, False),
        ("", 12, False),
    ]:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(texto)
        r.font.size = Pt(tam)
        r.bold = neg
        if tam >= 14:
            r.font.color.rgb = AZUL
    tabla(doc, ["#", "Integrantes del equipo"],
          [[1, "Sandra Luna Altos"], [2, "Joshua David Aquino"],
           [3, "Rebeca Jaimes Cruz"], [4, "Ithan Felipe Santiago"]], [1.5, 10])
    tabla(doc, ["Dato", ""],
          [["UCA", "Estructuras de Datos (LCDN3EST8)"],
           ["Docente", "Luisa Reyna Beatriz Ayon Muñoz"],
           ["Grupo", "302"],
           ["Fecha de entrega", "[POR DEFINIR]"]], [4.5, 7])
    doc.add_page_break()
    parrafo(doc, "El código del prototipo (carpeta estructuras/) y este documento se elaboraron con apoyo "
                 "de IA generativa (Claude, de Anthropic), con autorización de la docente y dando el crédito "
                 "correspondiente. El equipo revisó, ejecutó y probó el código, y es responsable de su contenido. "
                 "Todas las estructuras están programadas desde cero, sin heapq, dict de Python como tabla hash "
                 "ni otras bibliotecas que ya las resuelvan.", "Declaración de uso de IA. ")


def problema(doc, fifo, sipa, ll):
    titulo(doc, "1. El problema: una cola FIFO para atender baches")
    parrafo(doc, "El incidente crítico describe un sistema que atiende los reportes en orden de llegada (FIFO). "
                 "Eso trae tres fallas:")
    vinetas(doc, [
        f"Ignora la urgencia. En nuestra simulación de 90 días de lluvias de 2019 con datos reales, la cola FIFO "
        f"atiende a tiempo (3 días o menos) solo el {pct(fifo['rojos_en_3_dias'])} de los baches de mayor riesgo.",
        "Satura la memoria con duplicados: varios vecinos reportan el mismo bache y cada aviso se vuelve una "
        "solicitud distinta.",
        "Genera rutas caóticas: la brigada visita los baches en el orden en que llegaron, sin importar dónde están.",
    ])
    parrafo(doc, "El prototipo sustituye la cola por un conjunto de estructuras, cada una para una parte del "
                 "problema. Un reporte recorre este camino:")
    tabla(doc, ["Paso", "Estructura", "Complejidad"], [
        ["1. Llega el reporte", "Lista doblemente enlazada", "O(1)"],
        ["2. ¿Ya existe ese bache?", "Tabla hash (y conjunto)", "O(1) en promedio"],
        ["3. Se calcula su prioridad y entra a la cola de atención", "Max-heap", "O(log n)"],
        ["4. La autoridad ajusta una prioridad y puede deshacerlo", "Pila de deshacer y rehacer", "O(1) + O(log n)"],
        ["5. Se arma el plan del día y la ruta de la brigada", "Max-heap + grafo con Dijkstra", "O(k log n) + O((V+E) log V)"],
        ["6. Consultas por rango (por ejemplo, una zona)", "Árbol AVL", "O(log n + k)"],
    ], [6.5, 5.5, 4])
    parrafo(doc, f"Datos: los reportes reales de baches de la CDMX 2019-2022 (sin periodos atípicos) y el riesgo de "
                 f"accidente a 72 horas por celda que calcula el modelo de Probabilidad. En lluvias llegan "
                 f"{ll['lluvias']} baches nuevos por día y en secas {ll['secas']}.")


def poo(doc):
    titulo(doc, "2. Diseño orientado a objetos")
    parrafo(doc, "El dominio se modela con tres clases. Reporte guarda el aviso ciudadano y calcula su clave de "
                 "ubicación. Bache agrupa los reportes de un mismo daño y calcula su prioridad. Brigada recibe un "
                 "plan y arma su ruta sobre el grafo. La clase SistemaSIPA integra las estructuras: cada una es un "
                 "atributo con una sola responsabilidad (encapsulamiento), y sus operaciones se usan sin conocer "
                 "cómo están programadas por dentro.")
    figura(doc, ED / "img/clases.png", "Figura 1. Diagrama de clases del prototipo (estructuras/*.py).", 15.5)
    parrafo(doc, "El índice de prioridad de un bache vive en un método de la clase, así que cambiar la fórmula "
                 "no afecta a ninguna estructura:")
    codigo(doc, fuente("modelos.py", "calcular_ipu", "Bache"),
           "modelos.py · Bache.calcular_ipu: severidad (45 %), riesgo de accidente a 72 h (40 %) y reportes con "
           "tope de 10 (15 %).")
    parrafo(doc, "El prototipo usa este IPU simplificado de tres criterios para probar las estructuras. La base de "
                 "datos SIPA calcula el IPU completo con diez criterios; el max-heap funciona igual con cualquiera "
                 "de los dos, porque solo compara números.", "Nota. ")


def estructuras(doc, exp, ef):
    titulo(doc, "3. Las estructuras del prototipo")
    dd = exp["desduplicacion"]
    grande = ef[-1]

    titulo(doc, "3.1 Lista doblemente enlazada: entrada de reportes", 2)
    parrafo(doc, "Los reportes llegan en ráfagas y a veces hay que cancelar uno o unir los de otro canal (por "
                 "ejemplo, los de una app con los de una línea telefónica). En un arreglo, borrar en medio obliga a "
                 "recorrer todo lo que sigue. Cada nodo de la lista apunta al anterior y al siguiente, así que "
                 "basta con reconectar dos referencias.")
    codigo(doc, fuente("lista_enlazada.py", "eliminar", "ListaReportes"))
    ficha(doc, "Registrar, cancelar y fusionar reportes sin reacomodar la memoria",
          "O(1) para insertar, eliminar y fusionar",
          f"{dd['reportes']:,} reportes registrados; la prueba verifica el recorrido en los dos sentidos")

    titulo(doc, "3.2 Tabla hash y conjunto: eliminación de duplicados", 2)
    parrafo(doc, "La clave de un reporte es su ubicación redondeada a cuatro decimales (unos 11 m). Para saber si "
                 "un bache ya existe, se busca esa clave y sus 8 vecinas, porque dos personas pueden marcar el mismo "
                 "bache unos metros aparte. Si hay un bache pendiente reportado hace menos de 30 días, es un "
                 "duplicado; si ya se reparó o el último reporte tiene 30 días o más, se cuenta como una reaparición. Las colisiones se resuelven por encadenamiento "
                 "(cada cubeta es una lista) y la tabla duplica su tamaño cuando el factor de carga pasa de 0.75. "
                 "La clase Conjunto se construye sobre la misma tabla y se usa en Dijkstra y en el DFS para marcar "
                 "los vértices visitados.")
    codigo(doc, fuente("tabla_hash.py", "_indice", "TablaHash") + "\n\n" + fuente("tabla_hash.py", "insertar", "TablaHash"))
    ficha(doc, "Saber en tiempo constante si un bache ya fue reportado",
          "O(1) en promedio; O(n) el rehash, pocas veces",
          f"{dd['duplicados']:,} duplicados y {dd['reincidencias']:,} reapariciones entre {dd['reportes']:,} reportes en "
          f"{dd['segundos_hash']:.1f} s: {dd['busquedas_hash']:,} búsquedas en lugar de "
          f"{dd['comparaciones_por_pares'] / 1e6:,.0f} millones de comparaciones por pares. Factor de carga "
          f"{float(grande['factor_carga']):.2f}; la cubeta más larga tiene {grande['cubeta_mas_larga']} elementos")

    titulo(doc, "3.3 Árbol AVL y recursividad: consultas ordenadas", 2)
    parrafo(doc, "Un árbol binario de búsqueda se degrada a una lista si las claves llegan ordenadas, y los "
                 "reportes llegan ordenados por fecha. El AVL lo evita: después de cada inserción revisa el factor de "
                 "balance y, si una rama es dos niveles más alta que la otra, la corrige con una o dos rotaciones. "
                 "La inserción es recursiva: cada llamada baja un nivel y, al regresar, rebalancea el nodo.")
    codigo(doc, fuente("avl.py", "_insertar", "ArbolAVL"))
    parrafo(doc, "El recorrido en orden y la búsqueda por rango también son recursivos. La búsqueda por rango "
                 "poda las ramas que no pueden contener claves del intervalo:")
    codigo(doc, fuente("avl.py", "_rango", "ArbolAVL"))
    ficha(doc, "Mantener los baches ordenados y consultar rangos (una zona, un periodo)",
          "O(log n) para insertar y buscar; O(log n + k) para un rango",
          f"Con {int(grande['claves_distintas']):,} claves, altura {grande['altura_avl']} (la cota teórica es "
          f"{float(grande['cota_avl']):.1f}) y {float(grande['comparaciones_avl']):.1f} comparaciones por búsqueda, "
          f"contra {float(grande['comparaciones_lineal']):,.0f} de la búsqueda lineal")

    titulo(doc, "3.4 Max-heap: la cola de atención", 2)
    parrafo(doc, "Es la estructura que reemplaza a la cola FIFO. Se guarda en un arreglo donde los hijos del "
                 "nodo i están en 2i+1 y 2i+2, y cada padre tiene una prioridad mayor o igual que la de sus hijos, "
                 "así que el bache más urgente siempre está en la raíz. Al extraerlo, el último elemento pasa a la "
                 "raíz y baja hasta su lugar. Además, el heap guarda la posición de cada bache, lo que permite "
                 "actualizar su prioridad (cuando llega otro reporte o cuando la autoridad la ajusta) sin buscarlo.")
    codigo(doc, fuente("heap.py", "extraer_max", "MaxHeap") + "\n\n" + fuente("heap.py", "_bajar", "MaxHeap"))
    parrafo(doc, "Para que un bache de prioridad baja no espere para siempre, su prioridad sube un poco con los "
                 "días de espera, con un tope que impide que rebase a un rojo:")
    codigo(doc, fuente("modelos.py", "prioridad_efectiva", "Bache"))
    ficha(doc, "Entregar siempre el bache más urgente, aunque lleguen reportes nuevos",
          "O(1) ver el máximo; O(log n) insertar, extraer y actualizar",
          "La prueba extrae 500 elementos aleatorios y comprueba que salen en orden descendente; ver los resultados "
          "de la sección 5")

    titulo(doc, "3.5 Pila: deshacer y rehacer las decisiones de la autoridad", 2)
    parrafo(doc, "Cuando la autoridad ajusta una prioridad, la decisión se apila con su motivo (es obligatorio). "
                 "Deshacer saca la última decisión de una pila y la pasa a la otra; rehacer hace lo contrario. Una "
                 "bitácora aparte guarda todo, incluidos los deshacer, para rendir cuentas.")
    codigo(doc, fuente("pila.py", "deshacer", "PilaDecisiones"))
    ficha(doc, "Corregir un ajuste sin perder el historial", "O(1) en la pila, más O(log n) para actualizar el heap",
          "La prueba ajusta, deshace y rehace, y verifica la prioridad en el heap y la bitácora")

    titulo(doc, "3.6 Grafo, Dijkstra y DFS: rutas de las brigadas", 2)
    ru = exp["rutas"]
    parrafo(doc, f"La red se representa con listas de adyacencia: cada celda de 250 m con baches es un vértice y "
                 f"se conecta con sus vecinas, con la distancia en metros como peso. Dijkstra calcula la distancia "
                 f"mínima desde un origen usando un min-heap propio. El recorrido en profundidad (DFS) es recursivo "
                 f"y sirve para comprobar qué vértices son alcanzables desde la planta de asfalto. En "
                 f"{nombre(ru['alcaldia'])} el grafo tiene {ru['vertices']} vértices y {ru['aristas']:,} aristas.")
    codigo(doc, fuente("grafo.py", "dijkstra", "GrafoVial") + "\n\n" + fuente("grafo.py", "dfs", "GrafoVial"))
    ficha(doc, "Ordenar la visita de la brigada para recorrer menos",
          "O((V + E) log V) Dijkstra; O(V + E) DFS",
          f"El plan de 8 baches recorre {ru['km_orden_prioridad']:.1f} km en orden de prioridad y "
          f"{ru['km_vecino_cercano']:.1f} km por vecino más cercano: "
          f"{100 * (1 - ru['km_vecino_cercano'] / ru['km_orden_prioridad']):.0f} % menos")
    if (RES / "g3_ruta_brigada.png").exists():
        figura(doc, RES / "g3_ruta_brigada.png", f"Figura 2. Ruta de la brigada en {nombre(ru['alcaldia'])}.", 13)
    parrafo(doc, "El heap decide qué baches entran al plan del día y el grafo decide en qué orden se visitan, así "
                 "que acortar la ruta no sacrifica la prioridad.")


def hash_vs_avl(doc, ef):
    titulo(doc, "4. ¿Tabla hash o árbol AVL? La decisión")
    parrafo(doc, "El incidente pide elegir entre las dos para la búsqueda de coordenadas repetidas. Medimos el "
                 "tiempo promedio por búsqueda con tamaños crecientes de la base:")
    tabla(doc, ["Reportes", "Búsqueda lineal", "Tabla hash", "AVL", "Comparaciones lineal", "Comparaciones AVL",
                "Altura AVL"],
          [[f"{int(f['n']):,}", f"{float(f['us_lineal']):,.1f} µs", f"{float(f['us_hash']):.1f} µs",
            f"{float(f['us_avl']):.1f} µs", f"{float(f['comparaciones_lineal']):,.0f}",
            f"{float(f['comparaciones_avl']):.1f}", f['altura_avl']] for f in ef],
          [2.2, 2.5, 2, 1.6, 2.8, 2.6, 2])
    figura(doc, RES / "g1_eficiencia_busqueda.png", "Figura 3. Tiempo de búsqueda según el tamaño de la base.", 13)
    lin, ha, av = float(ef[-1]["us_lineal"]), float(ef[-1]["us_hash"]), float(ef[-1]["us_avl"])
    parrafo(doc, f"Las dos estructuras resuelven el problema: con toda la base, la búsqueda lineal tarda "
                 f"{lin:,.0f} µs y la hash y el AVL tardan unos pocos microsegundos. En nuestra implementación el AVL "
                 f"resultó un poco más rápido ({av:.1f} µs contra {ha:.1f} µs), porque la función hash recorre el "
                 f"texto de la clave carácter por carácter en Python. Aun así elegimos la tabla hash para los "
                 f"duplicados, por tres razones:")
    vinetas(doc, [
        "Su costo no depende del tamaño de la base: el del AVL crece con log n, y el de la hash se mantiene.",
        "La desduplicación busca claves exactas (la celda y sus 8 vecinas), que es justo lo que hace bien una tabla "
        "hash; no necesita orden.",
        "Optimizar la función hash es sencillo (por ejemplo, combinar los dos enteros de la clave en lugar de "
        "recorrer su texto); el AVL ya está en su mejor caso.",
    ])
    parrafo(doc, "El AVL se queda para lo que la hash no puede hacer: recorrer los baches en orden y consultar "
                 "rangos. Así cada estructura se usa donde es mejor.")


def pruebas(doc):
    titulo(doc, "5. Pruebas de correctitud")
    parrafo(doc, "Las 12 pruebas automáticas (python estructuras/pruebas.py) pasan:")
    tabla(doc, ["Estructura", "Qué se prueba"], [
        ["Lista doblemente enlazada", "Insertar, eliminar en medio, fusionar dos listas y recorrer en los dos sentidos"],
        ["Tabla hash", "Buscar, reemplazar un valor y conservar los datos después del rehash"],
        ["Árbol AVL", "Que quede balanceado y ordenado al insertar claves en orden (el peor caso) y al azar"],
        ["Max-heap", "Que siempre extraiga el mayor, que actualizar una prioridad conserve la propiedad de heap y "
                     "el ejemplo resuelto a mano en el primer avance"],
        ["Min-heap", "Que extraiga siempre la menor distancia (lo usa Dijkstra)"],
        ["Grafo", "Dijkstra contra un ejemplo calculado a mano y la conexión de una cuadrícula"],
        ["Sistema completo", "Que un reporte en la celda vecina cuente como duplicado y uno tras la reparación como "
                             "reaparición"],
        ["Pila de decisiones", "Ajustar, deshacer y rehacer, con motivo obligatorio y bitácora completa"],
    ], [4, 12])


def resultados(doc, v, eq, cap):
    titulo(doc, "6. Resultados: FIFO contra la cola de prioridad")
    fifo, sipa, cupo = eq["FIFO"], eq["SIPA β=0.10"], eq["SIPA + cupo"]
    parrafo(doc, f"Simulamos julio a septiembre de 2019 (90 días, reportes reales) con 15 reparaciones por día y "
                 f"cuatro políticas. La variante con cupo reserva 4 de los 15 lugares diarios para los baches que más "
                 f"han esperado, usando un segundo max-heap ordenado por antigüedad.")
    tabla(doc, ["Política", "Rojos ≤ 3 días", "Espera promedio (días)", "Espera p90", "Brecha entre alcaldías",
                "Pendientes día 90"],
          [[k.replace("SIPA", "Cola de prioridad"), pct(x["rojos_en_3_dias"]), x["todos"]["espera_promedio"],
            x["espera_p90"], x["brecha_alcaldias"], f"{x['pendientes_al_final']:,}"] for k, x in eq.items()],
          [4.2, 2.3, 2.6, 2, 2.6, 2.3])
    figura(doc, RES / "v1_equidad.png", "Figura 4. Rojos atendidos a tiempo y brecha entre alcaldías por política.", 14)
    vinetas(doc, [
        f"La cola de prioridad atiende a tiempo el {pct(sipa['rojos_en_3_dias'])} de los rojos, contra "
        f"{pct(fifo['rojos_en_3_dias'])} con FIFO, sin cambiar la espera promedio ({sipa['todos']['espera_promedio']} días): "
        "solo cambia quién espera.",
        f"Efecto no deseado: priorizar por riesgo alarga la espera en las alcaldías periféricas, que tienen baches de "
        f"prioridad baja. La brecha entre alcaldías sube de {fifo['brecha_alcaldias']} a {sipa['brecha_alcaldias']} "
        f"días. El cupo la baja a {cupo['brecha_alcaldias']} sin perder ningún rojo.",
        "Ninguna regla de orden evita que la cola crezca si llegan más baches de los que se reparan. Con capacidad "
        "suficiente, en cambio, la brecha casi desaparece:",
    ])
    tabla(doc, ["Reparaciones por día", "Brigadas", "Espera promedio", "Brecha", "Pendientes día 90"],
          [[c["capacidad"], c["brigadas"], c["espera_promedio"], c["brecha_alcaldias"],
            f"{c['pendientes_al_final']:,}"] for c in cap], [3.5, 2.5, 3, 2.5, 3.5])
    figura(doc, RES / "v2_capacidad.png", "Figura 5. Baches pendientes al final del periodo según la capacidad.", 13)


def viabilidad(doc, v, calc, cont, prob, exp, eq, cap):
    titulo(doc, "7. Plan de viabilidad")
    rec = {r["temporada"]: r for r in v["recursos"]}
    esc = {e["escenario"]: e for e in cont["escenarios"]}
    dd = exp["desduplicacion"]
    lluv = {x["meses"]: x for x in calc["tabla_perdida"] if x["temporada"] == "Lluvias"}
    parrafo(doc, f"El prototipo procesa toda la base (desduplicación de {dd['reportes']:,} reportes) en "
                 f"{dd['segundos_hash']:.1f} s y simula 90 días en segundos, en una computadora personal. No requiere "
                 "servidores especiales ni bibliotecas externas para las estructuras.", "Técnica. ")
    parrafo(doc, f"Con 6 reparaciones por brigada al día, la autoridad necesitaría "
                 f"{int(rec['lluvias']['brigadas'])} brigadas en lluvias y {int(rec['secas']['brigadas'])} en secas, "
                 f"y unas {rec['lluvias']['toneladas_mes']:.0f} toneladas de mezcla al mes en lluvias. SIPA lo "
                 "recomienda; las brigadas son de la autoridad.", "Operativa. ")
    parrafo(doc, f"Atender los baches abiertos según el semáforo cuesta {mm(esc['preventivo']['costo_total'])} "
                 f"contra {mm(esc['reactivo']['costo_total'])} si se espera (reparación más reclamaciones por "
                 f"daños, Contabilidad). Un bache típico cuesta {m(lluv[0]['costo'])} si se repara hoy y "
                 f"{m(lluv[6]['costo'])} tras 6 meses de lluvias (Cálculo).", "Financiera. ")
    parrafo(doc, f"El tope de reportes evita que las colonias con más participación digital desplacen a las demás, "
                 f"y el cupo de equidad reduce la brecha entre alcaldías. La autoridad conserva la decisión final y "
                 f"cada ajuste queda en la pila de decisiones con su motivo.", "Social. ")

    titulo(doc, "7.1 Contraste entre percepción y evidencia", 2)
    parrafo(doc, "[PARA EL EQUIPO: escribir aquí, con su fecha real, qué intervenciones consideraba prioritarias "
                 "el equipo al empezar y por qué. Después, completar la última columna de la tabla con lo que se "
                 "mantuvo, cambió o se descartó.]")
    fifo, sipa = eq["FIFO"], eq["SIPA β=0.10"]
    tabla(doc, ["Percepción frecuente", "Qué mostró el prototipo", "Resultado"], [
        ["El orden de llegada es lo más justo.",
         f"FIFO atiende a tiempo el {pct(fifo['rojos_en_3_dias'])} de los rojos; la cola de prioridad, el "
         f"{pct(sipa['rojos_en_3_dias'])}, con la misma espera promedio.", "Se descarta"],
        ["Priorizar resuelve la falta de atención.",
         f"Con 15 reparaciones al día la cola crece con cualquier política ({fifo['pendientes_al_final']:,} pendientes "
         f"al día 90). Ordenar no sustituye la capacidad.", "Se modifica"],
        ["Priorizar por riesgo es neutral entre zonas.",
         f"La brecha entre alcaldías sube de {fifo['brecha_alcaldias']} a {sipa['brecha_alcaldias']} días.",
         "Surge el cupo de equidad"],
        ["Cada reporte es un bache distinto.",
         f"{dd['duplicados']:,} reportes eran duplicados y {dd['reincidencias']:,} reapariciones del mismo bache.",
         "Surge la desduplicación y el reencarpetado"],
    ], [4.5, 8.5, 3])


def intervenciones(doc, v, calc, exp, eq, cap):
    titulo(doc, "8. Propuesta de intervenciones públicas priorizadas")
    fifo, sipa, cupo = eq["FIFO"], eq["SIPA β=0.10"], eq["SIPA + cupo"]
    ru, dd = exp["rutas"], exp["desduplicacion"]
    rec = {r["temporada"]: r for r in v["recursos"]}
    top = v["top_celdas"][0]
    c15 = next(c for c in cap if c["capacidad"] == 15)
    c35 = next(c for c in cap if c["capacidad"] == 35)
    tabla(doc, ["#", "Intervención", "Estructura que la hace posible", "Evidencia", "Indicador"], [
        [1, "Atender los baches rojos en 72 horas o menos", "Max-heap",
         f"{pct(sipa['rojos_en_3_dias'])} de rojos a tiempo contra {pct(fifo['rojos_en_3_dias'])} con FIFO",
         "% de rojos atendidos en 72 h"],
        [2, "Eliminar los reportes duplicados al registrarlos", "Tabla hash y conjunto",
         f"{dd['duplicados']:,} duplicados detectados en {dd['segundos_hash']:.1f} s", "Reportes duplicados"],
        [3, "Cupo de equidad: 4 de cada 15 lugares para los baches que más esperan", "Segundo max-heap por antigüedad",
         f"Brecha entre alcaldías {sipa['brecha_alcaldias']} → {cupo['brecha_alcaldias']} días sin perder rojos",
         "Brecha de espera entre alcaldías"],
        [4, "Rutas diarias por vecino más cercano", "Grafo y Dijkstra",
         f"{100 * (1 - ru['km_vecino_cercano'] / ru['km_orden_prioridad']):.0f} % menos km en {nombre(ru['alcaldia'])}",
         "Km por bache reparado"],
        [5, "Recomendar a la autoridad ajustar sus brigadas por temporada", "Simulación con el max-heap",
         f"{v['llegadas_por_dia']['lluvias']} baches/día en lluvias; con 15 reparaciones/día quedan "
         f"{c15['pendientes_al_final']:,} pendientes en 90 días y con 35, solo {c35['pendientes_al_final']}. Se "
         f"necesitan {int(rec['lluvias']['brigadas'])} brigadas en lluvias y {int(rec['secas']['brigadas'])} en secas",
         "Pendientes al cierre de mes"],
        [6, "Reencarpetar las celdas donde el bache reaparece", "Tabla hash (reapariciones)",
         f"{v['celdas_reincidencia_3']} celdas con 3 o más reapariciones; la peor ({nombre(top['alcaldia'])}) "
         f"tiene {top['reincidencias']}", "Reapariciones por celda al año"],
        [7, "Registrar y poder revertir cada ajuste de prioridad", "Pila de decisiones",
         "Cada ajuste exige motivo y queda en la bitácora", "Ajustes con motivo publicado"],
        [8, "Bacheo preventivo antes de las lluvias", "Max-heap con envejecimiento",
         f"Esperar 6 meses de lluvias cuesta {mm(calc['total_baches']['extra_6m'])} más (Cálculo)",
         "Costo por bache reparado"],
    ], [0.6, 4, 3.2, 5.4, 2.8])
    parrafo(doc, "Las intervenciones 1, 2, 3, 4 y 7 no requieren presupuesto adicional: solo cambian cómo se "
                 "organizan los datos y las decisiones. La 5, la 6 y la 8 requieren inversión de la autoridad, "
                 "justificada en la sección 7 y en el entregable final del problema prototípico.")
    filas = leer_csv(RES / "v4_celdas_reencarpetado.csv")[:10]
    titulo(doc, "Celdas candidatas a reencarpetado", 2)
    tabla(doc, ["Celda", "Alcaldía", "Baches", "Reapariciones", "Riesgo 72 h"],
          [[f["celda"], nombre(f["alcaldia"]), f["baches"], f["reincidencias"], f"{float(f['riesgo_72h']):.2f}"]
           for f in filas], [3, 5, 2.5, 3, 2.5])


def limitaciones(doc):
    titulo(doc, "9. Limitaciones")
    vinetas(doc, [
        "La severidad de los baches es sintética (la base abierta no la trae); el IPU del prototipo es una versión "
        "simplificada del de la base SIPA.",
        "Las rutas usan una cuadrícula de 250 m, no la red de calles real; el siguiente paso es cargar la red vial "
        "de OpenStreetMap.",
        "La productividad de 6 baches por brigada al día es un supuesto que debe calibrar la autoridad.",
        "Las simulaciones usan 2019; la tasa de llegadas puede ser distinta hoy.",
        "La función hash recorre el texto de la clave; con una función numérica sería más rápida.",
    ])
    titulo(doc, "10. Conclusiones")
    parrafo(doc, "Sustituir la cola FIFO por estructuras adecuadas cambia el resultado sin cambiar los recursos: el "
                 "max-heap atiende primero lo urgente, la tabla hash evita trabajar dos veces el mismo bache, el "
                 "grafo acorta las rutas y la pila deja registro de cada decisión. Todas cumplen las complejidades "
                 "que pide el incidente y lo comprueban las pruebas y las mediciones. La simulación también mostró "
                 "los límites: priorizar puede dejar atrás a las zonas periféricas, lo que se corrige con un cupo, y "
                 "ninguna estructura sustituye la capacidad de reparación, que es una decisión de la autoridad.")
    titulo(doc, "Referencias")
    for r in [
        "Bader, D. (2020). Common Python data structures (guide). Real Python. "
        "https://realpython.com/python-data-structures/",
        "Base maestra de solicitudes de bacheo de la Ciudad de México 2019-2022 [Conjunto de datos]. "
        "Proporcionada para el problema prototípico.",
        "Cormen, T. H., Leiserson, C. E., Rivest, R. L. y Stein, C. (2022). Introduction to algorithms (4a ed.). "
        "MIT Press.",
        "Secretaría de Seguridad Ciudadana de la Ciudad de México. (s. f.). Hechos de tránsito registrados por la "
        "SSC [Conjunto de datos]. Portal de Datos Abiertos de la Ciudad de México.",
    ]:
        p = doc.add_paragraph(r)
        p.paragraph_format.left_indent = Cm(1)
        p.paragraph_format.first_line_indent = Cm(-1)
    titulo(doc, "Anexo. Cómo ejecutar el prototipo", 2)
    tabla(doc, ["Comando", "Qué hace"], [
        ["python estructuras/pruebas.py", "Corre las 12 pruebas de correctitud"],
        ["python estructuras/experimentos.py", "Mide la eficiencia de búsqueda, desduplica la base, simula FIFO "
                                               "contra la cola de prioridad y calcula la ruta"],
        ["python estructuras/viabilidad.py", "Simula 90 días con las variantes de política y de capacidad"],
    ], [6, 10])


def main():
    exp = leer(RES / "resumen.json")
    v = leer(RES / "viabilidad.json")
    calc = leer("calculo/resultados/resumen.json")
    cont = leer("contabilidad/resultados/resumen.json")
    prob = leer("probabilidad/resultados/resumen.json")
    ef = leer_csv(RES / "t1_eficiencia_busqueda.csv")
    eq = v["equidad"]
    cap = v["capacidad"]

    doc = Document()
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(11)
    for s in doc.sections:
        s.left_margin = s.right_margin = Cm(2.2)

    portada(doc)
    problema(doc, eq["FIFO"], eq["SIPA β=0.10"], v["llegadas_por_dia"])
    poo(doc)
    estructuras(doc, exp, ef)
    hash_vs_avl(doc, ef)
    pruebas(doc)
    resultados(doc, v, eq, cap)
    viabilidad(doc, v, calc, cont, prob, exp, eq, cap)
    intervenciones(doc, v, calc, exp, eq, cap)
    limitaciones(doc)
    doc.save(SALIDA)
    print(f"Documento generado: {SALIDA}")


if __name__ == "__main__":
    main()
