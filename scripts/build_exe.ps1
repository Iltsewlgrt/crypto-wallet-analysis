param(
    [string]$Name = "CryptoWalletAnalyzer",
    [string]$Entry = "run_app.py"
)

$ErrorActionPreference = "Stop"

# Run from repository root
Set-Location (Split-Path -Parent $PSScriptRoot)

$python = Join-Path $PWD ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Venv not found. Create it with: python -m venv .venv"
}

& $python -m pip install -U pyinstaller | Out-Host

# Clean previous builds
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue build, dist

& $python -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --name $Name `
    $Entry | Out-Host

Write-Host "Built: dist\$Name\$Name.exe"
