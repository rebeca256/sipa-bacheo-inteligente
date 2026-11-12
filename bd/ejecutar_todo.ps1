# SIPA - crea la base desde cero y ejecuta todos los scripts en orden.
# Uso (desde la carpeta bd):   powershell -ExecutionPolicy Bypass -File .\ejecutar_todo.ps1
param([string]$Servidor = "localhost")

$scripts = "01_crear_bd.sql", "02_catalogos.sql", "03_carga_base_maestra.sql",
           "04_datos_sinteticos.sql", "05_procedimientos_transacciones.sql", "05b_riesgo_72h.sql", "05c_transporte_marginacion.sql", "06_carga_chalco.sql",
           "07_demo_y_consultas.sql", "08_simular_operacion.sql",
           "09_dw_crear.sql", "10_dw_etl.sql", "11_dw_consultas_olap.sql",
           "12_replicacion.sql", "13_vistas_indicadores.sql", "14_carga_toluca.sql"

foreach ($s in $scripts) {
    Write-Host "== $s" -ForegroundColor Cyan
    sqlcmd -S $Servidor -E -b -f 65001 -i (Join-Path $PSScriptRoot $s)
    if ($LASTEXITCODE -ne 0) { Write-Host "Falló $s" -ForegroundColor Red; exit 1 }
}
Write-Host "Listo: SIPA, SIPA_DW y SIPA_REPLICA creadas y probadas." -ForegroundColor Green
