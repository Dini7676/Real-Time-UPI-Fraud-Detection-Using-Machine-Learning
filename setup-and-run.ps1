# All-in-one setup, train (ML env), and run app (base env)
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\setup-and-run.ps1

$ErrorActionPreference = 'Stop'

function Ensure-App-Venv {
  param([string]$ProjectRoot)
  $appVenv = Join-Path $ProjectRoot '.venv'
  $appPython = Join-Path $appVenv 'Scripts\python.exe'

  if (-not (Test-Path $appPython)) {
    Write-Host 'Creating app venv (.venv)...' -ForegroundColor Cyan
    # Prefer Python 3.10 for consistency with ML env and wider wheel support
    $py310Exists = $false
    try {
      $ver = (& py -3.10 -V) 2>$null
      if ($LASTEXITCODE -eq 0) { $py310Exists = $true }
    } catch { $py310Exists = $false }
    if ($py310Exists) {
      & py -3.10 -m venv $appVenv
    } else {
      python -m venv $appVenv
    }
  }
  if (-not (Test-Path $appPython)) {
    throw "App venv Python not found at $appPython"
  }

  Write-Host 'Installing base requirements in app venv...' -ForegroundColor Cyan
  & $appPython -m pip install --upgrade pip
  & $appPython -m pip install -r (Join-Path $ProjectRoot 'requirements.txt')

  return $appPython
}

function Ensure-ML-Venv {
  param([string]$RepoRoot, [string]$ProjectRoot)

  $mlVenv = Join-Path $RepoRoot '.venv-ml310'
  $mlPython = Join-Path $mlVenv 'Scripts\python.exe'

  if (-not (Test-Path $mlPython)) {
    Write-Host 'Ensuring Python 3.10 via py launcher...' -ForegroundColor Cyan
    $py310Exists = $false
    try {
      $ver = (& py -3.10 -V) 2>$null
      if ($LASTEXITCODE -eq 0) { $py310Exists = $true }
    } catch { $py310Exists = $false }

    if (-not $py310Exists) {
      Write-Host 'Python 3.10 not found. Installing via winget...' -ForegroundColor Yellow
      & winget install -e --id Python.Python.3.10 --source winget --accept-source-agreements --accept-package-agreements
    }

    Write-Host 'Creating ML venv (.venv-ml310) with Python 3.10...' -ForegroundColor Cyan
    & py -3.10 -m venv $mlVenv
  }
  if (-not (Test-Path $mlPython)) {
    throw "ML venv Python not found at $mlPython"
  }

  Write-Host 'Installing ML packages (NumPy, Pandas, SciKit-Learn, TensorFlow)...' -ForegroundColor Cyan
  & $mlPython -m pip install --upgrade pip
  & $mlPython -m pip install --only-binary=:all: numpy==1.26.4 pandas==2.2.3
  & $mlPython -m pip install scikit-learn==1.4.2
  & $mlPython -m pip install --only-binary=:all: tensorflow==2.15.0

  return $mlPython
}

function Train-Models {
  param([string]$MlPython, [string]$ProjectRoot)

  $gen = Join-Path $ProjectRoot 'src\generate_sample_dataset.py'
  $prep = Join-Path $ProjectRoot 'src\preprocess.py'
  $train = Join-Path $ProjectRoot 'src\train.py'

  Write-Host 'Generating sample dataset...' -ForegroundColor Cyan
  & $MlPython $gen
  if ($LASTEXITCODE -ne 0) { throw 'Dataset generation failed.' }

  Write-Host 'Preprocessing dataset...' -ForegroundColor Cyan
  & $MlPython $prep
  if ($LASTEXITCODE -ne 0) { throw 'Preprocessing failed.' }

  Write-Host 'Training models (LogReg/KNN/RF + CNN)...' -ForegroundColor Cyan
  & $MlPython $train
  if ($LASTEXITCODE -ne 0) { throw 'Training failed.' }

  Write-Host 'Training complete. Artifacts saved in dataset/ and model/.' -ForegroundColor Green
}

function Run-App {
  param([string]$AppPython, [string]$ProjectRoot)
  $app = Join-Path $ProjectRoot 'app.py'
  Write-Host 'Starting Flask app...' -ForegroundColor Cyan
  & $AppPython $app
}

# Entry point
$ProjectRoot = $PSScriptRoot
$RepoRoot = Resolve-Path (Join-Path $ProjectRoot '..')

Write-Host "Project root: $ProjectRoot" -ForegroundColor Gray
Write-Host "Repo root: $RepoRoot" -ForegroundColor Gray

# 1) Ensure app venv + install base deps
$appPython = Ensure-App-Venv -ProjectRoot $ProjectRoot

# 2) Ensure ML venv + install ML deps
$mlPython = Ensure-ML-Venv -RepoRoot $RepoRoot -ProjectRoot $ProjectRoot

# 3) Train models in ML env
Train-Models -MlPython $mlPython -ProjectRoot $ProjectRoot

# 4) Run the app
Run-App -AppPython $appPython -ProjectRoot $ProjectRoot
