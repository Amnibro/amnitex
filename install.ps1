# Installs atex on Windows: downloads atex.exe into %USERPROFILE%\.local\bin,
# adds that folder to your PATH, runs the self-test, indexes this folder and
# wires Claude Code, Claude Desktop, Cursor, Windsurf, Gemini CLI, OpenAI Codex
# and Grok Build. No WSL, compiler or administrator rights needed.
#
#   irm https://github.com/Amnibro/amnitex/releases/latest/download/install.ps1 | iex
#
# Optional settings, as environment variables:
#   ATEX_BIN_DIR  install folder (default %USERPROFILE%\.local\bin)
#   ATEX_DIR      knowledge base folder (default %USERPROFILE%\.atex)
#   ATEX_URL      where to download atex.exe from
& {
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
function Say($m) { Write-Host "[amnitex] $m" }
if ((Test-Path variable:IsWindows) -and -not $IsWindows) { throw 'install.ps1 is for Windows. On Linux and macOS, run install.sh.' }
$arch = if ($env:PROCESSOR_ARCHITEW6432) { $env:PROCESSOR_ARCHITEW6432 } else { $env:PROCESSOR_ARCHITECTURE }
if ($arch -ne 'AMD64' -and $arch -ne 'ARM64') { throw "atex needs 64-bit Windows; this is $arch." }
$repo = if ($env:ATEX_REPO) { $env:ATEX_REPO } else { 'Amnibro/amnitex' }
$url = if ($env:ATEX_URL) { $env:ATEX_URL } else { "https://github.com/$repo/releases/latest/download/atex-windows-x64.exe" }
$dest = if ($env:ATEX_BIN_DIR) { $env:ATEX_BIN_DIR } else { Join-Path $env:USERPROFILE '.local\bin' }
$kb = if ($env:ATEX_DIR) { $env:ATEX_DIR } else { Join-Path $env:USERPROFILE '.atex' }
$kb = $kb -replace '\\', '/'
New-Item -ItemType Directory -Force -Path $dest, $kb | Out-Null
$exe = Join-Path $dest 'atex.exe'
$new = "$exe.new"

$local = if ($PSScriptRoot) { Join-Path $PSScriptRoot 'bin\atex-windows-x64.exe' } else { '' }
if ($local -and (Test-Path $local)) {
    Copy-Item $local $new -Force
} else {
    Say "downloading $url"
    Invoke-WebRequest -Uri $url -OutFile $new -UseBasicParsing
}
Unblock-File $new -ErrorAction SilentlyContinue
# A running atex.exe (an open MCP server) can be renamed but not overwritten.
Get-ChildItem -Path $dest -Filter 'atex.exe.old-*' -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
if (Test-Path $exe) { Move-Item $exe "$exe.old-$([guid]::NewGuid().ToString('N').Substring(0, 8))" -Force }
Move-Item $new $exe -Force
Get-ChildItem -Path $dest -Filter 'atex.exe.old-*' -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue

$reg = [Microsoft.Win32.Registry]::CurrentUser.OpenSubKey('Environment', $true)
$raw = [string]$reg.GetValue('Path', '', [Microsoft.Win32.RegistryValueOptions]::DoNotExpandEnvironmentNames)
$parts = @($raw -split ';' | Where-Object { $_ })
if (-not ($parts | Where-Object { [Environment]::ExpandEnvironmentVariables($_).TrimEnd('\') -ieq $dest.TrimEnd('\') })) {
    $reg.SetValue('Path', (($parts + $dest) -join ';'), [Microsoft.Win32.RegistryValueKind]::ExpandString)
    # Setting a user variable tells Windows the environment changed, so apps started from now on see the new PATH.
    [Environment]::SetEnvironmentVariable('ATEX_INSTALL_PING', '1', 'User')
    [Environment]::SetEnvironmentVariable('ATEX_INSTALL_PING', $null, 'User')
    Say "added $dest to your PATH"
}
$reg.Close()
if (-not (($env:Path -split ';') -contains $dest)) { $env:Path = "$dest;$env:Path" }

function Run-Atex([string[]]$a) { & $exe @a; if ($LASTEXITCODE -ne 0) { throw "atex $($a -join ' ') failed with exit code $LASTEXITCODE." } }
Run-Atex @('--version')
Run-Atex @('--selftest')
Run-Atex @('init', '.', '--atex-dir', $kb)
Run-Atex @('install', '--atex-dir', $kb)
Say "installed $exe (kb=$kb)"
Say 'restart Claude Code, Claude Desktop or Cursor to load it, and open a new terminal to run atex by name. Check with: atex doctor'
}
