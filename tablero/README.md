# SIPA · Tablero del prototipo funcional

Interfaz en Streamlit sobre la base `SIPA` (SQL Server). Todo pasa por los procedimientos almacenados de `bd/05`, así que las reglas de la base (transacciones, restricciones CHECK) son las mismas que en SQL.

| Sección | Qué hace |
|---|---|
| Resumen y mapa | Indicadores clave, mapa de baches abiertos por semáforo y costo pendiente por territorio |
| Modo ciudadano | Reportar un bache (se liga al bache existente de la misma celda) y consultar el folio |
| Recomendación de SIPA | Ranking por territorio, ficha de justificación del IPU, intervención y costo estimado; recalcular el IPU |
| Modo autoridad | Aprobar, ajustar o rechazar la recomendación e informar el avance (en atención, reparado con costo real, descartado con motivo) |
| Indicadores | Reincidencia, causa probable, tiempos de respuesta, cobertura y reportes resueltos por año |

## Cómo ejecutar (desde la carpeta del proyecto)

```
pip install --user streamlit pydeck
streamlit run tablero/app.py
```

Requiere la base construida (`bd/ejecutar_todo.ps1`) y el ODBC Driver 17 for SQL Server. Lo que se registre desde el tablero queda en la base; para volver a los datos de los documentos, reconstruirla con `ejecutar_todo.ps1` (los datos sintéticos son reproducibles).
