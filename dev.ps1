# Start LuxTJ backend locally
# Usage: .\dev.ps1   or   .\dev.bat

$ErrorActionPreference = "Stop"

$env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
$env:PYTHONPATH = "src"

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Error "uv not found. Install from https://docs.astral.sh/uv/ and reopen the terminal."
}

Set-Location $PSScriptRoot

$envFile = Join-Path $PSScriptRoot ".dev.env"
if (-not (Test-Path $envFile)) {
    Write-Error ".dev.env not found. Copy .env.example to .dev.env and configure it."
}

# Load .dev.env into this process so uvicorn --reload child workers inherit vars.
Get-Content $envFile | ForEach-Object {
    $line = $_.Trim()
    if ($line -eq "" -or $line.StartsWith("#")) { return }
    $parts = $line -split "=", 2
    if ($parts.Count -ne 2) { return }
    $name = $parts[0].Trim()
    $value = $parts[1].Trim()
    Set-Item -Path "Env:$name" -Value $value
}

Write-Host "Starting LuxTJ BE on http://127.0.0.1:9000"
Write-Host ("Admin dev auth enabled: " + $env:LTJBE_ADMIN_DEV_AUTH_ENABLED)

uv run --env-file .dev.env uvicorn luxtj.bootstrap.api:server_factory --factory --host 127.0.0.1 --port 9000 --reload
