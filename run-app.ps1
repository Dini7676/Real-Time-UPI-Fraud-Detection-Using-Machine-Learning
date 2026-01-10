# Run the Flask app using the local .venv (app env)
$ErrorActionPreference = 'Stop'

$projectRoot = $PSScriptRoot
$appPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
$app = Join-Path $projectRoot 'app.py'

if (-not (Test-Path $appPython)) {
  Write-Host "App Python not found at: $appPython" -ForegroundColor Red
  Write-Host "Create the app venv and install requirements first:" -ForegroundColor Yellow
  Write-Host "  python -m venv .venv" -ForegroundColor Yellow
  Write-Host "  Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force" -ForegroundColor Yellow
  Write-Host "  .\\.venv\\Scripts\\Activate.ps1" -ForegroundColor Yellow
  Write-Host "  python -m pip install -r requirements.txt" -ForegroundColor Yellow
  exit 1
}

Write-Host "Starting app with: $appPython $app" -ForegroundColor Cyan

# Clear environment vars that can force wrong Python stdlib/interpreter
Remove-Item Env:PYTHONHOME -ErrorAction SilentlyContinue
Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
Remove-Item Env:PYTHONUSERBASE -ErrorAction SilentlyContinue
$env:PYTHONNOUSERSITE = "1"

& $appPython $app
