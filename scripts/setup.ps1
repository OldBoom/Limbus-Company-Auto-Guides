# One-time environment setup (Windows PowerShell)
# Run from repo root: .\scripts\setup.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Find-Python {
    $candidates = @(
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        (Get-Command python -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source)
    )
    foreach ($py in $candidates) {
        if ($py -and (Test-Path $py)) {
            $ver = & $py -c "import sys; print(sys.version_info[:2])" 2>$null
            if ($LASTEXITCODE -eq 0) { return $py }
        }
    }
    Write-Host "Python not found. Install with:"
    Write-Host "  winget install Python.Python.3.12"
    Write-Host "Or download from https://www.python.org/downloads/"
    exit 1
}

$Python = Find-Python
Write-Host "Using: $Python (& $Python --version)"

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Creating virtual environment..."
    & $Python -m venv .venv
}

$VenvPy = ".\.venv\Scripts\python.exe"
& $VenvPy -m pip install -q --upgrade pip
& $VenvPy -m pip install -q -r requirements.txt
& $VenvPy -m pip install -q -e .
& $VenvPy -m pip install -q pytest
& $VenvPy -m spacy download en_core_web_sm

Write-Host ""
Write-Host "Setup complete. Next steps:"
Write-Host "  .\.venv\Scripts\Activate.ps1"
Write-Host "  python scripts/run_poc_evaluations.py"
Write-Host "  python scripts/run_pipeline.py"
Write-Host "  streamlit run src/limbus_guides/dashboard/app.py"
