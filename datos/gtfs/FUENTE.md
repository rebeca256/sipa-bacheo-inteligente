# GTFS de la Ciudad de México

- **Archivo:** `originales/gtfs.zip` (2.4 MB), descargado el 5 nov 2026.
- **Fuente:** Portal de Datos Abiertos CDMX, conjunto «GTFS», publicado por SEMOVI.
  https://datos.cdmx.gob.mx/dataset/gtfs
  Descarga directa: https://datos.cdmx.gob.mx/dataset/75538d96-3ade-4bc5-ae7d-d85595e4522d/resource/32ed1b6b-41cd-49b3-b7f0-b57acb0eb819/download/gtfs-2.zip
- **Contenido:** agency, routes, trips, stop_times, stops, calendar, shapes, frequencies. Cubre Metro, Metrobús, Trolebús, RTP, Tren Ligero, Cablebús, Ferrocarril Suburbano y corredores concesionados.
- **Vigencia:** el portal fecha la edición en octubre de 2021, pero `calendar.txt` trae servicios con vigencia de 2024 a 2026. Casi todos los viajes vienen como frecuencias (`frequencies.txt`), no como horarios exactos.
- **Procesado:** `scripts/procesar_fuentes_ipu.py` → `limpios/paradas.csv` (10,961 paradas con servicio, rutas y salidas por día).
- **Uso en SIPA:** criterio TRANSPORTE (rutas y frecuencia de paso cerca del bache).
