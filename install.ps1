# Windows installer for AmniTex Cursor wiring.
# hc emits a Linux/macOS host binary or C. This script uses WSL when it is
# present, which covers the supported native build. A native Win32 compile of
# the generated C file is not run here.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
if (Get-Command wsl.exe -ErrorAction SilentlyContinue) {
    $unix = wsl wslpath -a $Root
    wsl -e bash -lc "cd '$unix' && sh ./install.sh"
    Write-Host "[amnitex] installed through WSL. Open a new terminal and run: atex doctor"
    exit 0
}
Write-Host "[amnitex] WSL was not found."
Write-Host "Install WSL, then from this checkout run: wsl bash ./install.sh"
Write-Host "Or on Linux/macOS run: sh ./install.sh"
Write-Host "The Helium compiler writes the host executable. On Windows the tested path is WSL."
exit 1
