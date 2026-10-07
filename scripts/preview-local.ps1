param([int]$WebPort = 4316, [int]$ApiPort = 8316)

$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path $PSScriptRoot -Parent
$taskApi = Join-Path $taskRoot 'apps/api'
$taskWeb = Join-Path $taskRoot 'apps/web'
$taskRuntime = Join-Path $taskRoot 'tmp/client-preview'
New-Item -ItemType Directory -Force -Path $taskRuntime | Out-Null
$taskPython = Join-Path $taskApi '.venv/Scripts/python.exe'
$env:PYTHONPATH = Join-Path $taskApi 'src'
if (-not (Test-Path -LiteralPath $taskPython)) { throw 'Install the locked API dependencies first. See README.md.' }
if (-not (Test-Path -LiteralPath (Join-Path $taskWeb 'node_modules/vite/bin/vite.js'))) { throw 'Install the locked web dependencies first. See README.md.' }
$env:MODE = 'DEMO'
$env:LANGSMITH_TRACING = 'false'
$env:DEMO_SEED = 'true'
$env:DATABASE_URL = 'sqlite:///' + (Join-Path $taskRuntime 'preview.db').Replace('\', '/')
$env:ASSET_DIR = Join-Path $taskRuntime 'assets'
$env:PUBLIC_BASE_URL = "http://127.0.0.1:$WebPort"
$env:API_BASE_URL = "http://127.0.0.1:$ApiPort"
$env:VITE_API_PROXY_TARGET = $env:API_BASE_URL
$env:TEMP = $taskRuntime
$env:TMP = $taskRuntime
Push-Location $taskApi
try {
    & $taskPython -m quoteflow.cli init-demo
    if ($LASTEXITCODE -ne 0) { throw 'Demo database initialization failed.' }
} finally { Pop-Location }
$taskApiProcess = Start-Process -FilePath $taskPython -ArgumentList @('-m', 'uvicorn', 'quoteflow.main:app', '--host', '127.0.0.1', '--port', "$ApiPort", '--no-access-log') -WorkingDirectory $taskApi -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $taskRuntime 'api.log') -RedirectStandardError (Join-Path $taskRuntime 'api-error.log')
try {
    $taskReady = $false
    for ($taskAttempt = 0; $taskAttempt -lt 20; $taskAttempt++) {
        try {
            $taskHealth = Invoke-RestMethod -Uri "$($env:API_BASE_URL)/api/health" -TimeoutSec 2
            if ($taskHealth.status -eq 'ok' -and $taskHealth.synthetic -eq $true) { $taskReady = $true; break }
        } catch { }
        if ($taskApiProcess.HasExited) { throw 'The local API stopped before becoming healthy. See tmp/client-preview/api-error.log.' }
        Start-Sleep -Milliseconds 300
    }
    if (-not $taskReady) { throw 'The synthetic API did not become ready. See tmp/client-preview/api-error.log.' }
    Write-Output "Synthetic local preview: http://127.0.0.1:$WebPort (SQLite; no live calls)"
    Write-Output 'Press Ctrl+C to stop. Local preview data are kept under tmp/client-preview.'
    Push-Location $taskWeb
    try {
        & node node_modules/vite/bin/vite.js --host 127.0.0.1 --port $WebPort --strictPort
    } finally { Pop-Location }
} finally {
    # The Windows virtualenv launcher can spawn a runtime child. Stop only its owned children.
    $taskApiChildren = @(Get-CimInstance Win32_Process -Filter "ParentProcessId = $($taskApiProcess.Id)" -ErrorAction SilentlyContinue)
    foreach ($taskChild in $taskApiChildren) { Stop-Process -Id $taskChild.ProcessId -ErrorAction SilentlyContinue }
    if (-not $taskApiProcess.HasExited) { Stop-Process -Id $taskApiProcess.Id }
}
