# Runs every backend test suite in a throw-away virtualenv (no Docker needed). Requires Python 3.11+.
$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -q -r services/auth/requirements-dev.txt -r services/video/requirements-dev.txt -r services/content/requirements-dev.txt
& .\.venv\Scripts\python.exe -m pip install -q .\libs\common
Write-Host '=== libs/common ==='
Push-Location libs/common; & ..\..\.venv\Scripts\python.exe -m pytest tests -q; Pop-Location
foreach ($s in 'gateway','auth','user','content','video','watchlist','history') {
  Write-Host "=== $s ==="
  Push-Location "services/$s"
  & ..\..\.venv\Scripts\python.exe -m pytest
  if ($LASTEXITCODE -ne 0) { Pop-Location; exit $LASTEXITCODE }
  Pop-Location
}
