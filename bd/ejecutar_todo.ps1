# SIPA - crea la base desde cero y ejecuta todos los scripts en orden.
#
# Uso (desde cualquier carpeta):
#   powershell -ExecutionPolicy Bypass -File bd\ejecutar_todo.ps1                       # instalación nueva
#   powershell -ExecutionPolicy Bypass -File bd\ejecutar_todo.ps1 -Reconstruir          # borra y recrea SIPA, SIPA_DW, SIPA_REPLICA
#   powershell -ExecutionPolicy Bypass -File bd\ejecutar_todo.ps1 -Servidor .\SQLEXPRESS
#
# Protecciones (antes de escribir nada):
#   1. Comprueba que existan sqlcmd y todos los scripts y archivos de datos.
#   2. Comprueba que el servidor responda.
#   3. Si SIPA, SIPA_DW o SIPA_REPLICA ya existen, se detiene SIN tocarlas
#      salvo que se indique -Reconstruir (los scripts 01, 09 y 12 las recrean).
#
# Rutas: los scripts usan la variable $(RAIZ) de sqlcmd, que aquí se toma de la
# carpeta del repositorio. BULK INSERT lee los archivos con la cuenta del servicio
# de SQL Server: la carpeta debe ser accesible para ese servicio (en un equipo
# local con instancia propia lo es; en un servidor remoto, use una ruta UNC).
param(
    [string]$Servidor = $(if ($env:SIPA_SERVIDOR) { $env:SIPA_SERVIDOR } else { "localhost" }),
    [string]$Raiz = (Split-Path $PSScriptRoot -Parent),
    [switch]$Reconstruir
)

$scripts = "01_crear_bd.sql", "02_catalogos.sql", "03_carga_base_maestra.sql",
           "04_datos_sinteticos.sql", "05_procedimientos_transacciones.sql", "05b_riesgo_72h.sql", "05c_transporte_marginacion.sql", "06_carga_chalco.sql",
           "07_demo_y_consultas.sql", "08_simular_operacion.sql",
           "09_dw_crear.sql", "10_dw_etl.sql", "11_dw_consultas_olap.sql",
           "12_replicacion.sql", "13_vistas_indicadores.sql", "14_carga_toluca.sql"

# Archivos de datos que leen los scripts (relativos a la raíz del repositorio)
$datos = "datos\costos\tarifas_reparacion.json",                  # 02
         "datos\limpios\base_maestra_limpia.csv",                    # 03
         "probabilidad\resultados\t4_riesgo_72h_por_celda.csv",      # 05b
         "datos\gtfs\limpios\paradas.csv",                          # 05c
         "datos\marginacion\limpios\colonias_marginacion.csv",      # 05c
         "datos\chalco\limpios\comunidades.csv",                    # 06
         "datos\chalco\limpios\reportes_chalco.csv",
         "datos\chalco\limpios\zonas_inundables.csv",
         "datos\chalco\limpios\equipamiento.csv",
         "datos\limpios\toluca_baches.csv",                          # 14
         "datos\limpios\toluca_medidas.csv"

function Fallar($msg) { Write-Host "ALTO: $msg" -ForegroundColor Red; exit 1 }

# 1. Herramientas y archivos
if (-not (Get-Command sqlcmd -ErrorAction SilentlyContinue)) { Fallar "no se encontró sqlcmd en el PATH." }
$faltan = @()
foreach ($s in $scripts) { if (-not (Test-Path (Join-Path $PSScriptRoot $s))) { $faltan += "bd\$s" } }
foreach ($d in $datos)   { if (-not (Test-Path (Join-Path $Raiz $d) -PathType Leaf)) { $faltan += $d } }
if ($faltan.Count) { Fallar ("faltan archivos; no se modificó ninguna base:`n  " + ($faltan -join "`n  ")) }

# 2. Servidor
$existentes = sqlcmd -S $Servidor -E -b -h -1 -W -Q "SET NOCOUNT ON; SELECT name FROM sys.databases WHERE name IN ('SIPA','SIPA_DW','SIPA_REPLICA')"
if ($LASTEXITCODE -ne 0) { Fallar "el servidor '$Servidor' no responde; no se modificó ninguna base." }
$existentes = @($existentes | Where-Object { $_.Trim() })

# 3. Bases existentes
if ($existentes.Count -and -not $Reconstruir) {
    Fallar ("ya existen: " + ($existentes -join ", ") + ". No se tocaron. " +
            "Para borrarlas y reconstruir la demostración, repita con -Reconstruir.")
}

# sqlcmd toma las variables de entorno como variables de script: $(RAIZ) en los .sql
# (pasarla con -v falla porque la ruta lleva ':').
$env:RAIZ = $Raiz
foreach ($s in $scripts) {
    Write-Host "== $s" -ForegroundColor Cyan
    sqlcmd -S $Servidor -E -b -f 65001 -i (Join-Path $PSScriptRoot $s)
    if ($LASTEXITCODE -ne 0) { Fallar "falló $s" }
}
Write-Host "Listo: SIPA, SIPA_DW y SIPA_REPLICA creadas y probadas (servidor $Servidor, raíz $Raiz)." -ForegroundColor Green
