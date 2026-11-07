"""
SIPA - Documento de la 2ª entrega de Fundamentos de Bases de Datos PARA LA DOCENTE.

A diferencia de avance2_BD_planeacion.docx (control interno del equipo, con las
tablas de cumplimiento de cada rúbrica), este documento explica en prosa qué se
diseñó y construyó, por qué y qué resultados da.

Alcance (nov 2026): SIPA es un sistema de ASESORÍA. Recomienda qué bache atender,
por qué y cuánto costaría; la reparación la hace la autoridad.

Uso (desde la carpeta del proyecto):
    python scripts/generar_doc_entrega_bd.py
Salida:
    avance2_BD_entrega.docx
"""
import sys
from pathlib import Path

from docx import Document
from docx.shared import Pt, Cm

sys.path.insert(0, str(Path(__file__).parent))
from generar_doc_planeacion_bd import portada, titulo, parrafo, vinetas, tabla, figura  # noqa: E402

SALIDA = "avance2_BD_entrega.docx"


def codigo(doc, texto):
    for linea in texto.strip("\n").split("\n"):
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.left_indent = Cm(0.8)
        r = p.add_run(linea)
        r.font.name = "Consolas"
        r.font.size = Pt(8.5)
    doc.add_paragraph()


def introduccion(doc):
    titulo(doc, "1. Introducción")
    parrafo(doc, "La planeación de la UCA plantea la siguiente pregunta:")
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(1)
    p.add_run("«¿Cómo ayuda la UCA de Bases de Datos a diseñar e implementar una estructura de información "
              "confiable que permita organizar, relacionar, consultar y manipular los datos del deterioro vial, "
              "para contribuir al funcionamiento de la Plataforma de Bacheo Inteligente y a la toma de "
              "decisiones públicas basadas en evidencia?»").italic = True
    parrafo(doc, "Hoy un bache se atiende, sobre todo, porque alguien lo reportó. Eso favorece a las zonas con más "
                 "acceso digital y deja fuera criterios como el riesgo de accidente, el paso del transporte público "
                 "o la cercanía a escuelas y hospitales. Nuestra respuesta es SIPA (Sistema Inteligente de "
                 "Priorización Asfáltica): una base de datos que reúne los reportes ciudadanos con información del "
                 "entorno y calcula, para cada bache, un Índice de Prioridad Urbana (IPU), la intervención "
                 "recomendada y su costo estimado.")
    parrafo(doc, "SIPA es un sistema de asesoría. Le dice a la autoridad qué bache atender primero, por qué y "
                 "cuánto costaría, pero no repara: las brigadas, el material y el presupuesto son de la autoridad. "
                 "Por eso la base no administra esa logística. Solo registra lo que decide la autoridad y el "
                 "avance que informa, para poder medir si la recomendación se siguió y en cuánto tiempo se "
                 "atendió.", "Alcance. ")
    parrafo(doc, "El documento sigue el orden en que se construyó la base: primero los datos, luego el modelo "
                 "conceptual y su paso al modelo relacional, después la implementación en SQL Server con sus "
                 "transacciones y, al final, el Data Warehouse con el que se analiza la información.")


def datos(doc):
    titulo(doc, "2. Los datos")
    parrafo(doc, "Trabajamos con datos reales siempre que existían y declaramos como sintético lo que no:")
    vinetas(doc, [
        "Base maestra de solicitudes de bacheo de la CDMX 2019-2022. Tras la limpieza quedaron 35,629 reportes "
        "válidos; los excluidos (sin coordenadas, fuera de la ciudad o duplicados exactos) quedaron registrados "
        "en una bitácora con el motivo.",
        "Datos abiertos del municipio de Chalco: 68 reportes de bacheo 2025-2026, 55 comunidades, 23 zonas "
        "inundables del Atlas de Riesgo, 473 escuelas, 28 hospitales y 44 mercados.",
        "Fuentes de contexto para el IPU: paradas y frecuencias del transporte público (GTFS de SEMOVI), índice "
        "de marginación urbana 2020 por colonia (CONAPO) y el riesgo de accidente a 72 horas que calcula el "
        "modelo de la UCA de Probabilidad.",
        "Tarifas de reparación: un archivo JSON con el costo por metro cuadrado de cada tipo de intervención. "
        "Los valores son una estimación del equipo; cada autoridad puede reemplazar el archivo por su propio "
        "tabulador sin modificar la base.",
        "Datos sintéticos: la severidad y las medidas de los baches, y un historial simulado en el que la "
        "autoridad decide sobre 300 baches y los informa como reparados, para poder medir tiempos y costos.",
    ])
    parrafo(doc, "La base maestra no trae calle ni severidad. Por eso usamos como unidad espacial una cuadrícula "
                 "de celdas de 250 m: cada reporte se asigna a la celda en la que cae, y la información del "
                 "entorno (transporte, marginación, riesgo) también se resume por celda.")


def modelo_conceptual(doc):
    titulo(doc, "3. Modelo conceptual: el diagrama entidad-relación")
    parrafo(doc, "El modelo tiene 27 entidades organizadas en cinco ámbitos, que corresponden a las preguntas que "
                 "la plataforma tiene que poder responder:")
    vinetas(doc, [
        "Territorio y ubicación: territorio (alcaldía o municipio), colonia, celda y tramo. ¿Dónde está el bache?",
        "Baches y reportes: el bache es el daño físico; el reporte es cada aviso ciudadano sobre él. Los separamos "
        "porque varios vecinos pueden reportar el mismo bache, y queremos contar daños reales, no avisos.",
        "Contexto: aforo vehicular, rutas de transporte, accidentes, riesgo de accidente por celda, zonas "
        "inundables y equipamiento (escuelas, hospitales, mercados). ¿Qué hay alrededor del bache?",
        "Priorización: criterios del IPU, sus pesos por territorio, cada cálculo con su detalle por criterio, la "
        "tarifa con la que se estima el costo y la decisión de la autoridad. ¿Por qué este bache va primero y "
        "cuánto costaría?",
        "Seguimiento: los cambios de estado que informa la autoridad y las notificaciones al ciudadano. ¿Qué pasó "
        "con el bache?",
    ])
    figura(doc, "bd/img/MER_SIPA.png", 16.5,
           "Figura 1. Modelo entidad-relación de SIPA (notación de pata de gallo).")
    parrafo(doc, "La plataforma tiene dos tipos de usuario:", "Dos modos de uso. ")
    vinetas(doc, [
        "El ciudadano reporta un bache y consulta el avance con su folio. No necesita cuenta; si quiere recibir "
        "avisos, deja un dato de contacto opcional.",
        "La autoridad tiene una cuenta ligada a su territorio. Revisa la recomendación de SIPA, la aprueba, la "
        "ajusta o la rechaza, y después informa el avance: en atención, reparado (con el costo real) o descartado "
        "(con el motivo).",
    ])
    parrafo(doc, "En el diagrama aparecen los tres tipos de relación:", "Relaciones y cardinalidades. ")
    vinetas(doc, [
        "Uno a muchos, la más común: un territorio tiene muchas colonias; un bache, muchos reportes y muchos "
        "registros de seguimiento; una tarifa se usa en muchos cálculos.",
        "Uno a uno opcional: un reporte puede tener o no un contacto ciudadano. Ese contacto vive aparte porque "
        "son datos personales.",
        "Muchos a muchos: una ruta de transporte pasa por muchos tramos y un tramo es parte de muchas rutas. Se "
        "resuelve con la tabla intermedia ruta_tramo.",
    ])
    parrafo(doc, "Las tablas de cálculo, decisión y seguimiento (calculo_prioridad, detalle_calculo, "
                 "decision_humana, seguimiento_bache) nunca se sobrescriben: cada cálculo o cambio es un renglón "
                 "nuevo. Así se puede reconstruir después por qué se recomendó atender un bache antes que otro. "
                 "La autoridad puede cambiar la recomendación, pero solo si escribe una justificación de al menos "
                 "20 caracteres.", "Auditoría. ")


def modelo_relacional(doc):
    titulo(doc, "4. Del modelo conceptual al modelo relacional")
    parrafo(doc, "Cada entidad se convirtió en una tabla con su llave primaria y cada relación uno a muchos en una "
                 "llave foránea del lado «muchos». La relación muchos a muchos se convirtió en una tabla con llave "
                 "compuesta (id_ruta, id_tramo). Los pesos del IPU también usan llave compuesta: un peso depende "
                 "del criterio, del territorio y de la fecha desde la que está vigente, para que cada municipio "
                 "pueda tener los suyos y cualquier cambio quede registrado.")
    parrafo(doc, "La base original venía en una sola tabla plana. Al normalizarla:", "Normalización. ")
    vinetas(doc, [
        "Primera forma normal: todos los atributos son atómicos. Las rutas que pasan por un tramo no se guardan "
        "como lista separada por comas, sino como renglones de ruta_tramo.",
        "Segunda forma normal: en las tablas con llave compuesta (peso_criterio, detalle_calculo, ruta_tramo) "
        "cada atributo depende de la llave completa y no solo de una parte.",
        "Tercera forma normal: quitamos las dependencias transitivas. La alcaldía depende de la colonia, así que "
        "no se repite en cada reporte; el año y el mes se obtienen de la fecha; el estatus agrupado depende del "
        "estatus original y vive en un catálogo; las coordenadas del centro de la celda viven en la tabla celda; "
        "el costo por metro cuadrado depende del tipo de intervención y vive en tarifa_reparacion, no en cada "
        "cálculo.",
    ])
    parrafo(doc, "Las fuentes de contexto se guardaron en tablas propias, ligadas a la celda: el riesgo de "
                 "accidente a 72 horas, las paradas de transporte y las colonias de CONAPO con su polígono. Las "
                 "colonias de CONAPO no se fusionaron con la tabla colonia porque tienen otra delimitación; se "
                 "cruzan por ubicación geográfica.")


def modelo_fisico(doc):
    titulo(doc, "5. Implementación en SQL Server")
    parrafo(doc, "La base SIPA está en Microsoft SQL Server 2025. Tiene 32 tablas en tres esquemas: dbo para la "
                 "operación, priv para los datos personales e ind para los indicadores.")
    parrafo(doc, "Elegimos el tipo según el dato: DECIMAL(9,6) para coordenadas, DATE y DATETIME2 para fechas, "
                 "TINYINT para escalas como la severidad, BIT para marcas de sí o no y GEOGRAPHY para puntos y "
                 "polígonos. Con GEOGRAPHY la base calcula distancias reales en metros, por ejemplo, si un bache "
                 "está a menos de 200 m de una zona inundable o cuántas escuelas tiene a 500 m.", "Tipos de datos. ")
    parrafo(doc, "La base tiene 39 llaves foráneas y 56 restricciones CHECK. Las reglas del negocio viven en la "
                 "propia base y no dependen de que la aplicación las respete. Por ejemplo:", "Integridad. ")
    codigo(doc, """
severidad  TINYINT NULL CONSTRAINT ck_bache_severidad CHECK (severidad BETWEEN 1 AND 5)
CONSTRAINT ck_decision_justificacion CHECK (decision = 'APROBAR'
    OR (justificacion IS NOT NULL AND LEN(LTRIM(RTRIM(justificacion))) >= 20))
CONSTRAINT ck_seguimiento_descarte CHECK (id_estado_nuevo <> 6
    OR (comentario IS NOT NULL AND LEN(LTRIM(RTRIM(comentario))) >= 15))
CONSTRAINT ck_seguimiento_costo_rep CHECK (costo_reportado IS NULL OR id_estado_nuevo = 5)
""")
    parrafo(doc, "El IS NOT NULL de las dos reglas de justificación es necesario: SQL Server acepta una fila "
                 "cuando un CHECK da «desconocido», y eso es lo que pasa al medir un texto nulo. Lo descubrimos al "
                 "probar la base: sin esa condición, se podía descartar un bache sin escribir ningún motivo.")
    parrafo(doc, "Además usamos UNIQUE para los folios, valores DEFAULT para fechas y estados iniciales, e índices "
                 "espaciales para que las búsquedas por distancia no recorran toda la tabla.")
    parrafo(doc, "La carga de los 35,629 reportes se hace con BULK INSERT a una tabla temporal y de ahí, con "
                 "INSERT…SELECT, a las tablas normalizadas. Las tarifas se leen del archivo JSON con OPENJSON. El "
                 "procedimiento sp_calcular_ipu combina diez criterios: cada uno toma un valor entre 0 y 1 y se "
                 "multiplica por su peso. Cuando un criterio no tiene dato vale 0.5 (neutral), para no premiar ni "
                 "castigar a un bache por falta de información. El resultado se traduce en un semáforo: rojo, "
                 "atender en 3 días; amarillo, en 15; verde, programar en 60.", "Carga y cálculo. ")
    parrafo(doc, "El mismo procedimiento elige la intervención y estima el costo con la fórmula costo fijo + "
                 "costo por m² × área. Si la celda tiene muchos reportes históricos recomienda reencarpetar, porque "
                 "bachear no resolvería el problema. Si está en zona inundable, bacheo con sello. Si el bache es "
                 "severo o tiene 10 cm o más de profundidad, bacheo profundo. En los demás casos, bacheo "
                 "superficial.", "Intervención y costo. ")
    parrafo(doc, "Los dos modos de uso también existen en la base, como roles. rol_ciudadano solo puede ejecutar "
                 "los procedimientos para reportar y consultar un folio; no puede leer ninguna tabla. "
                 "rol_autoridad puede consultar la información, registrar decisiones y actualizar el estado de un "
                 "bache. Ninguno de los dos puede leer los datos personales.", "Permisos. ")
    parrafo(doc, "Toda la base se reconstruye desde cero con un solo script (ejecutar_todo.ps1), que corre los "
                 "scripts numerados en orden y termina sin errores.")


def transacciones(doc):
    titulo(doc, "6. Transacciones")
    parrafo(doc, "Algunas operaciones tocan varias tablas a la vez y no pueden quedar a medias. Cuando la autoridad "
                 "informa que un bache se reparó o se descartó, la base tiene que cambiar el estado del bache, dejar "
                 "el registro en la bitácora de seguimiento y avisar a cada ciudadano que lo reportó. No debe "
                 "quedar un bache marcado como reparado sin su registro ni un aviso enviado por un cambio que no "
                 "ocurrió. El procedimiento sp_actualizar_estado_bache lo resuelve así:")
    codigo(doc, """
BEGIN TRANSACTION;
    -- valida que la transición esté permitida (p. ej. EN_ATENCION -> REPARADO)
    UPDATE bache SET id_estado_bache = @nuevo WHERE id_bache = @id_bache;
    INSERT INTO seguimiento_bache (id_bache, id_estado_anterior, id_estado_nuevo,
                                   id_usuario, comentario, costo_reportado)
    VALUES (...);                         -- aquí se revisan los CHECK
    IF @nuevo IN (5, 6)                   -- reparado o descartado
        INSERT INTO notificacion (id_reporte, id_seguimiento, medio)
        SELECT id_reporte, @id_seguimiento, 'FOLIO' FROM reporte WHERE id_bache = @id_bache;
COMMIT TRANSACTION;                       -- con XACT_ABORT ON, un error revierte todo
""")
    parrafo(doc, "En la demostración (07_demo_y_consultas.sql) la autoridad intenta descartar un bache sin escribir "
                 "el motivo. El estado del bache ya se había cambiado, pero al insertar el seguimiento falla la "
                 "restricción ck_seguimiento_descarte y la transacción completa se revierte. Al final se comprueba "
                 "que el bache sigue en su estado anterior y que no se agregó ningún registro. Los demás "
                 "procedimientos que modifican datos (registrar un reporte, calcular el IPU y registrar una "
                 "decisión) siguen el mismo esquema, igual que las cargas masivas.")


def data_warehouse(doc):
    titulo(doc, "7. Data Warehouse y datamarts")
    parrafo(doc, "La base SIPA está pensada para registrar la operación diaria: muchas escrituras pequeñas y "
                 "normalización para evitar inconsistencias. Para analizar la historia (tendencias por año, "
                 "comparaciones entre alcaldías, cumplimiento de tiempos) conviene otra estructura. Por eso creamos "
                 "una base aparte, SIPA_DW, desnormalizada, en la que las consultas pesadas no frenan el registro "
                 "de reportes.")
    parrafo(doc, "SIPA_DW tiene tres tablas de hechos: reportes, cálculos de prioridad y atención (cada bache que la "
                 "autoridad decidió atender, con el costo que estimó SIPA, el que reportó la autoridad y el tiempo "
                 "que tardó). Las tres comparten siete dimensiones: tiempo, ubicación, celda, estatus, fuente, "
                 "semáforo e intervención. Como varias tablas de hechos usan las mismas dimensiones, el esquema es "
                 "una constelación de hechos.", "Modelo dimensional. ")
    figura(doc, "bd/img/DW_SIPA.png", 16.5,
           "Figura 2. Esquema en constelación del Data Warehouse SIPA_DW.")
    parrafo(doc, "Un procedimiento (dw.sp_etl_cargar) extrae los datos de SIPA y los transforma: crea llaves "
                 "sustitutas, convierte la fecha a la llave de la dimensión tiempo, pasa los criterios del IPU de "
                 "renglones a columnas y calcula las horas entre la decisión y la reparación y el cumplimiento de "
                 "la meta. Luego los carga dentro de una transacción: si un paso falla, el Data Warehouse queda "
                 "como estaba. Cada paso deja en una bitácora las filas, la duración y los errores. La carga "
                 "completa tarda unos 8 segundos.", "Proceso ETL. ")
    parrafo(doc, "Sobre el Data Warehouse definimos dos datamarts como conjuntos de vistas:", "Datamarts. ")
    vinetas(doc, [
        "Priorización, para el personal técnico: ranking de baches, semáforo por territorio, celdas críticas "
        "y contraste entre número de reportes e IPU.",
        "Financiero, para dirección y finanzas: costo estimado contra costo reportado por mes, cumplimiento de "
        "los tiempos del semáforo y la inversión necesaria por tipo de intervención.",
    ])
    parrafo(doc, "Las consultas usan las operaciones OLAP: roll-up con GROUP BY ROLLUP (territorio, luego año, "
                 "luego total), cubo con CUBE (temporada por estatus con todos los subtotales), GROUPING SETS, "
                 "PIVOT (un año por columna), drill-down (Chalco, luego colonia, luego celda), slice y dice con "
                 "filtros sobre una o varias dimensiones, y funciones de ventana para el promedio móvil de tres "
                 "meses.", "Consultas analíticas. ")


def distribuido(doc):
    titulo(doc, "8. Fragmentación y replicación")
    parrafo(doc, "La tabla de hechos de reportes está particionada por año con una función y un esquema de "
                 "partición. Una consulta sobre 2021 solo lee la partición de 2021, y los años viejos se pueden "
                 "archivar sin tocar los recientes. Como cada municipio atiende sus propios baches, también "
                 "proponemos fragmentar la base operativa por territorio: un servidor por alcaldía o municipio y un "
                 "nodo central que consolide. Por eso los pesos del IPU y las cuentas de autoridad ya se guardan "
                 "por territorio.", "Fragmentación. ")
    parrafo(doc, "Montamos una réplica de solo lectura, SIPA_REPLICA, por envío de registros (log shipping). La "
                 "base principal se respalda y se restaura en modo STANDBY, que permite consultar pero no "
                 "modificar. Después, el procedimiento sp_replicar envía los cambios del registro de "
                 "transacciones y los aplica en la réplica. El tablero de consulta lee de la réplica, así que no "
                 "carga a la base principal y sigue disponible aunque esta falle.", "Replicación. ")
    parrafo(doc, "La demostración comprueba cuatro cosas:")
    vinetas(doc, [
        "Un reporte nuevo aparece en la réplica solo después de replicar.",
        "La réplica rechaza las escrituras.",
        "El rol del tablero puede consultar los datos operativos.",
        "Ese mismo rol no puede leer los datos personales, porque el permiso DENY viaja con la réplica.",
    ])


def resultados(doc):
    titulo(doc, "9. Lo que la base permite responder")
    parrafo(doc, "Con la base construida pudimos contestar preguntas del problema prototípico:")
    vinetas(doc, [
        "La temporada de lluvias casi duplica los reportes: unos 1,147 por mes, contra 639 en secas.",
        "Más reportes no significa más prioridad. Algunos de los 50 baches más reportados quedan después del "
        "lugar 1,000 por IPU, porque están en calles con poco tránsito y lejos de servicios.",
        "Hay baches que vuelven a salir: detectamos 2,271 reapariciones y 161 celdas crónicas (con tres o más). "
        "En Azcapotzalco, el 21.7 % de los reportes cae en ellas. Ahí conviene reencarpetar, no bachear.",
        "La atención no es pareja entre alcaldías: Cuauhtémoc tiene reparado el 43 % de sus baches y Tláhuac el "
        "2 %. Los reportes resueltos bajan de 97.5 % en 2019 a 67.9 % en 2022.",
        "Atender los 1,345 baches que siguen abiertos costaría unos 4.6 millones de pesos con las tarifas del "
        "archivo JSON. Benito Juárez es el que más necesita, unos 720 mil pesos.",
        "La autoridad cambió la recomendación en 31 de 301 casos, y cada cambio quedó justificado.",
        "En Chalco, los primeros baches por atender están en Unión de Guadalupe y San Miguel Jacalones II, cerca de "
        "zonas inundables y con muchos servicios alrededor.",
    ])


def cierre(doc):
    titulo(doc, "10. Consideraciones y conclusiones")
    parrafo(doc, "Los datos de contacto ciudadano son opcionales, piden consentimiento y están en un esquema "
                 "protegido. El número de reportes tiene un peso acotado en el IPU para no favorecer a las zonas "
                 "con más acceso digital; por ejemplo, Milpa Alta tiene solo 133 reportes en cuatro años. SIPA "
                 "recomienda, pero la decisión siempre es de una persona de la autoridad.", "Ética y privacidad. ")
    parrafo(doc, "La severidad de los baches y la atención informada por la autoridad son simuladas, así que los "
                 "tiempos y los costos reportados son ilustrativos. Las tarifas son una estimación del equipo y "
                 "deben sustituirse por el tabulador de cada autoridad. Dos criterios del IPU (personas afectadas "
                 "y tránsito) siguen en valor neutral porque no hay datos abiertos de aforo por calle. Las fuentes "
                 "de transporte, marginación y riesgo solo cubren la CDMX. La réplica y el Data Warehouse están en "
                 "el mismo servidor que la base principal; en producción irían en servidores distintos.",
            "Limitaciones. ")
    parrafo(doc, "La base responde a la pregunta de la UCA: organiza y relaciona los datos del deterioro vial en "
                 "un modelo normalizado, protege su integridad con restricciones y transacciones, y los vuelve "
                 "consultables para decidir con evidencia, mediante el Data Warehouse, los datamarts y la réplica. "
                 "Se queda en su papel de asesoría: entrega a la autoridad una prioridad justificada y un costo "
                 "estimado, y mide después si se atendió a tiempo. El siguiente paso es definir los pesos del IPU "
                 "con el método AHP y sustituir los datos simulados por los que informen las autoridades.",
            "Conclusión. ")
    titulo(doc, "Anexo. Archivos de la base de datos", 2)
    tabla(doc, ["Archivo", "Contenido"], [
        ["bd/01_crear_bd.sql", "Tablas, llaves, restricciones e índices"],
        ["bd/02_catalogos.sql", "Catálogos, criterios del IPU y tarifas leídas del JSON"],
        ["bd/03 a 06", "Carga de datos reales y sintéticos, procedimientos, transacciones y roles"],
        ["bd/07_demo_y_consultas.sql", "Recorrido de un reporte, demostración de ROLLBACK y consultas"],
        ["bd/08 a 11", "Atención simulada, Data Warehouse, ETL y consultas OLAP"],
        ["bd/12_replicacion.sql", "Réplica de solo lectura y su demostración"],
        ["bd/13_vistas_indicadores.sql", "Indicadores de reincidencia, tiempo de respuesta, cobertura y costo pendiente"],
        ["datos/costos/tarifas_reparacion.json", "Tarifas de reparación (editables por la autoridad)"],
        ["bd/ejecutar_todo.ps1", "Reconstruye todas las bases desde cero"],
    ], [6, 10])


def main():
    doc = Document()
    estilo = doc.styles["Normal"]
    estilo.font.name = "Calibri"
    estilo.font.size = Pt(11)
    for s in doc.sections:
        s.left_margin = s.right_margin = Cm(2.2)
    portada(doc)
    for seccion in (introduccion, datos, modelo_conceptual, modelo_relacional, modelo_fisico,
                    transacciones, data_warehouse, distribuido, resultados, cierre):
        seccion(doc)
    doc.save(SALIDA)
    print(f"Documento generado: {SALIDA}")


if __name__ == "__main__":
    main()
