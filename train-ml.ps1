# Requires: Python 3.10 ML venv at ..\.venv-ml310
$ErrorActionPreference = 'Stop'

$projectRoot = $PSScriptRoot
$repoRoot = Resolve-Path (Join-Path $projectRoot '..')
$mlPython = Join-Path $repoRoot '.venv-ml310\Scripts\python.exe'

if (-not (Test-Path $mlPython)) {
  Write-Host "ML Python not found at: $mlPython" -ForegroundColor Red
  Write-Host "Make sure you created the ML env at $repoRoot\.venv-ml310" -ForegroundColor Yellow
  exit 1
}

$preprocess = Join-Path $projectRoot 'src\preprocess.py'
$train = Join-Path $projectRoot 'src\train.py'

Write-Host "Using ML Python: $mlPython" -ForegroundColor Cyan

& $mlPython $preprocess
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $mlPython $train
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Training complete. Artifacts saved to dataset/ and model/." -ForegroundColor Green
