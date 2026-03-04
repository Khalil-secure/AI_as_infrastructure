param([string]$action = "help")

function Print-Header {
    Write-Host ""
    Write-Host "================================================" -ForegroundColor Cyan
    Write-Host "  AII - AI as Infrastructure" -ForegroundColor Cyan
    Write-Host "================================================" -ForegroundColor Cyan
}

function Start-AII {
    Print-Header
    Write-Host "  ACTION : START" -ForegroundColor Green
    Write-Host "================================================" -ForegroundColor Cyan
    Write-Host ""

    if (-not (Test-Path ".env")) {
        Write-Host "ERROR: .env file missing!" -ForegroundColor Red
        Write-Host "Create .env with: ANTHROPIC_API_KEY=sk-ant-..." -ForegroundColor Yellow
        exit 1
    }

    Write-Host "Starting AII environment..." -ForegroundColor Yellow
    docker compose up -d

    Write-Host ""
    Write-Host "Waiting for services (10s)..." -ForegroundColor Yellow
    Start-Sleep -Seconds 10

    Show-Status

    Write-Host ""
    Write-Host "To see logs             : .\manage.ps1 logs" -ForegroundColor Cyan
    Write-Host "To stop (save budget)   : .\manage.ps1 stop" -ForegroundColor Cyan
    Write-Host ""
}

function Stop-AII {
    Print-Header
    Write-Host "  ACTION : STOP" -ForegroundColor Red
    Write-Host "================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Stopping all AII containers..." -ForegroundColor Yellow
    docker compose down
    Write-Host ""
    Write-Host "All containers stopped." -ForegroundColor Green
    Write-Host "No more API tokens being spent." -ForegroundColor Green
    Write-Host ""
}

function Show-Status {
    Print-Header
    Write-Host "  ACTION : STATUS" -ForegroundColor Yellow
    Write-Host "================================================" -ForegroundColor Cyan
    Write-Host ""

    $running = docker ps --filter "name=aii" --format "{{.Names}} : {{.Status}}" 2>$null

    if (-not $running) {
        Write-Host "No AII containers running." -ForegroundColor Yellow
        Write-Host "Run: .\manage.ps1 start" -ForegroundColor White
        return
    }

    Write-Host "  CONTAINERS:" -ForegroundColor Cyan
    docker ps -a --filter "name=aii" --format "  {{.Names}} : {{.Status}}"

    Write-Host ""
    Write-Host "  URLS:" -ForegroundColor Cyan
    Write-Host "  App Python  : http://localhost:5000" -ForegroundColor White
    Write-Host "  Prometheus  : http://localhost:9090" -ForegroundColor White
    Write-Host "  Grafana     : http://localhost:3000  (admin / aii2026)" -ForegroundColor White
    Write-Host "  Nginx       : http://localhost:80" -ForegroundColor White
    Write-Host ""

    $watcherState = docker inspect aii-watcher --format "{{.State.Status}}" 2>$null
    if ($watcherState -eq "running") {
        Write-Host "  AII Watcher : ACTIVE - watching every 30s" -ForegroundColor Green
        Write-Host "  API Budget  : 0.50 EUR max / session (auto hard stop)" -ForegroundColor Yellow
        Write-Host "  NOTE: AI only called when anomaly is detected" -ForegroundColor Gray
    } else {
        Write-Host "  AII Watcher : STOPPED" -ForegroundColor Red
    }
    Write-Host ""
}

function Show-Logs {
    Print-Header
    Write-Host "  ACTION : LOGS (Ctrl+C to quit)" -ForegroundColor Yellow
    Write-Host "================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Live watcher logs..." -ForegroundColor Cyan
    Write-Host "Ctrl+C stops the logs but NOT the watcher" -ForegroundColor Gray
    Write-Host ""
    docker logs -f aii-watcher
}

function Restart-Watcher {
    Print-Header
    Write-Host "  ACTION : RESTART WATCHER" -ForegroundColor Yellow
    Write-Host "================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Rebuilding and restarting watcher..." -ForegroundColor Yellow
    docker compose up -d --build aii-watcher
    Start-Sleep -Seconds 3
    Write-Host "Watcher restarted." -ForegroundColor Green
    Write-Host ""
    Write-Host "See logs: .\manage.ps1 logs" -ForegroundColor Cyan
    Write-Host ""
}

function Show-Help {
    Print-Header
    Write-Host ""
    Write-Host "  Usage:" -ForegroundColor Yellow
    Write-Host "  .\manage.ps1 start    - Start everything" -ForegroundColor White
    Write-Host "  .\manage.ps1 stop     - Stop everything (saves API budget)" -ForegroundColor White
    Write-Host "  .\manage.ps1 status   - Show container status + URLs" -ForegroundColor White
    Write-Host "  .\manage.ps1 logs     - Live watcher logs" -ForegroundColor White
    Write-Host "  .\manage.ps1 restart  - Rebuild + restart watcher only" -ForegroundColor White
    Write-Host ""
}

switch ($action.ToLower()) {
    "start"   { Start-AII }
    "stop"    { Stop-AII }
    "status"  { Show-Status }
    "logs"    { Show-Logs }
    "restart" { Restart-Watcher }
    default   { Show-Help }
}