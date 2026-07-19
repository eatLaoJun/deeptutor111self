$ErrorActionPreference = "Stop"
Set-Location "C:\file\ownWork\DeepTutor"

# Clash actual port is 7897 (NOT 7890). DeepTutor/httpx reads these env vars.
$env:HTTP_PROXY  = "http://127.0.0.1:7897"
$env:HTTPS_PROXY = "http://127.0.0.1:7897"
$env:http_proxy  = "http://127.0.0.1:7897"
$env:https_proxy = "http://127.0.0.1:7897"
# Avoid proxying local backend/frontend
$env:NO_PROXY = "127.0.0.1,localhost"
$env:no_proxy = "127.0.0.1,localhost"

Write-Host "HTTPS_PROXY=$env:HTTPS_PROXY"
& ".\.venv\Scripts\Activate.ps1"
& ".\.venv\Scripts\python.exe" -m deeptutor_cli.main start
