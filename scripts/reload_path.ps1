# Script para recargar el PATH del sistema en PowerShell
# Útil cuando agregas nuevas rutas a las variables de entorno

# Recargar PATH del sistema y usuario
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

Write-Host "PATH recargado. Verificando Allure..." -ForegroundColor Green
allure --version
