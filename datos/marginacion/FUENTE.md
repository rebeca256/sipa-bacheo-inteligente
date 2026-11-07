# Índice de marginación urbana 2020 por colonia (CDMX)

- **Archivo:** `originales/im_colonia_cdmx.geojson` (6.5 MB, 2,243 colonias con polígono), descargado el 5 nov 2026.
- **Fuente:** CONAPO, Índice de marginación urbana 2020 (con microdatos del Censo de Población y Vivienda 2020 del INEGI), publicado como la capa `geonode:im_colonia` del Sistema de Información Geográfica de la CDMX (SIEG).
  Capa: https://www.sieg.cdmx.gob.mx/layers/geonode%3Aim_colonia
  Descarga (WFS): https://www.sieg.cdmx.gob.mx/geoserver/ows?service=WFS&version=1.0.0&request=GetFeature&typeName=geonode:im_colonia&outputFormat=application/json&srsName=EPSG:4326
  Página de CONAPO: https://www.gob.mx/conapo/documentos/indices-de-marginacion-2020-284372
- **Campos:** COLONIA, CP, CVE_MUN, NOM_MUN, IM_2020 (índice), GM_2020 (grado: Muy bajo a Muy alto), IMN_2020 (índice normalizado 0-1), CLASIF.
- **Codificación:** NOM_ENT viene con caracteres mal codificados en el servicio («M�xico»); revisar los nombres con acentos al cruzar.
- **Limitación:** solo cubre la CDMX; para Chalco haría falta el índice por AGEB o colonia del Estado de México.
- **Uso en SIPA:** criterio VULNERABILIDAD (columna `colonia.indice_marginacion`). IMN alto = menor marginación (Aguilera, «Bajo», 0.966; Reforma Iztaccíhuatl Norte, «Muy bajo», 0.974), así que hay que invertirlo. El rango real es estrecho (0.868 a 0.995): conviene reescalarlo con mínimo y máximo. Grados: 453 muy bajo, 1,092 bajo, 558 medio, 93 alto y 47 muy alto.
- **Procesado:** `scripts/procesar_fuentes_ipu.py` → `limpios/colonias_marginacion.csv` (polígonos en WKT), cargado por `bd/05c_transporte_marginacion.sql`.
