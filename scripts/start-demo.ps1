$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
$demoPort = if ($env:QUOTEFLOW_PORT) { $env:QUOTEFLOW_PORT } else { '8080' }
docker compose up --build -d
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
for ($attempt = 1; $attempt -le 60; $attempt++) {
    try {
        $health = Invoke-RestMethod -Uri "http://127.0.0.1:$demoPort/api/health" -TimeoutSec 2
        if ($health.status -eq 'ok') {
            Write-Host "QuoteFlow demo ready: http://localhost:$demoPort"
            exit 0
        }
    } catch { }
    Start-Sleep -Seconds 2
}
throw 'QuoteFlow did not become healthy within two minutes. Inspect: docker compose logs api web db worker'
