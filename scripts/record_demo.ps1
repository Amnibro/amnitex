$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING = "utf-8"
$ATEX_DIR = "$env:USERPROFILE\.atex-demo-record"
if (Test-Path $ATEX_DIR) { Remove-Item -Recurse -Force $ATEX_DIR }
Write-Host ""
Write-Host "  $ atex demo --model qwen2.5:0.5b-instruct" -ForegroundColor Cyan
Write-Host ""
Start-Sleep -Milliseconds 800
$python = if ($env:ATEX_PYTHON) { $env:ATEX_PYTHON } else { "python" }
& $python -m atex.cli demo --atex-dir "$ATEX_DIR\.atex" --model qwen2.5:0.5b-instruct --no-consent
Write-Host ""
Write-Host "  $ atex stats --atex-dir $ATEX_DIR\.atex" -ForegroundColor Cyan
Write-Host ""
Start-Sleep -Milliseconds 600
& $python -m atex.cli stats --atex-dir "$ATEX_DIR\.atex"
Write-Host ""
Write-Host "  Done." -ForegroundColor Green
Write-Host ""
