<#
  Windows one-shot deploy script for sitellm_vertebro
  - Проверяет утилиты (Docker Desktop, docker compose, git, PowerShell 7+)
  - Создаёт/обновляет .env
  - Делает бэкап env в deploy-backups\<timestamp>-windows.zip
  - Собирает образы последовательно (без --no-parallel) — безопасно для слабых CPU
  - Поднимает контейнеры, ждёт health-check API с хоста (без curl внутри контейнера)
  - Опционально запускает первичный crawl, если передан CRAWL_START_URL
#>
param(
  [string]$Domain,
  [switch]$GPU,                        # -GPU включает профиль GPU (если присутствует)
  [string]$Model = "Vikhrmodels/Vikhr-YandexGPT-5-Lite-8B-it",
  [string]$MongoUser = "root",
  [string]$MongoPassword,              # если пусто — сгенерируем
  [string]$CrawlUrl,                   # опционально; если не задано — шаг пропустим
  [switch]$NoBuild,                    # пропустить сборку образов
  [string]$ProjectName = "sitellm_vertebro",
  [int]$AppPort = 8000,
  [int]$HealthTimeoutSec = 300
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Write-Info($msg){ Write-Host "[+] $msg" -ForegroundColor Cyan }
function Write-Ok($msg){ Write-Host "[✓] $msg" -ForegroundColor Green }
function Write-Warn($msg){ Write-Host "[!] $msg" -ForegroundColor Yellow }
function Write-Err($msg){ Write-Host "[✗] $msg" -ForegroundColor Red }

function Test-Cmd($name){
  $null -ne (Get-Command $name -ErrorAction SilentlyContinue)
}

function Require-Cmd($name, $hint){
  if (-not (Test-Cmd $name)) {
    throw "$name не найден. $hint"
  }
}

function New-RandomPassword([int]$len=28){
  $chars = ('a'..'z') + ('A'..'Z') + ('0'..'9')
  -join (1..$len | % { $chars[(Get-Random -Max $chars.Count)] })
}

function Ensure-File($path, $templatePath){
  if (-not (Test-Path $path)) {
    if ($templatePath -and (Test-Path $templatePath)) {
      Copy-Item $templatePath $path
    } else {
      New-Item -ItemType File -Path $path | Out-Null
    }
  }
}

function Set-EnvVarInFile([string]$file, [string]$name, [string]$value){
  $pair = "$name=$value"
  if (-not (Test-Path $file)) { New-Item -ItemType File -Path $file | Out-Null }
  $content = Get-Content -Path $file -Raw
  if ($content -match "^[\s#]*$name\s*="){
    $new = [regex]::Replace($content, "^[\s#]*$name\s*=.*$", $pair, 'Multiline')
  } else {
    if ($content.Length -gt 0 -and -not $content.EndsWith("`n")) { $content += "`n" }
    $new = $content + $pair + "`n"
  }
  Set-Content -Path $file -Value $new -NoNewline
}

function Get-ComposeCmd(){
  # Проверяем наличие docker compose (v2)
  if (Test-Cmd "docker"){
    try {
      $null = (docker compose version) 2>$null
      if ($LASTEXITCODE -eq 0) {
        return @("docker","compose")
      }
    } catch {}
  }
  # Проверяем наличие docker-compose (v1)
  if (Test-Cmd "docker-compose"){
    try {
      $null = (docker-compose version) 2>$null
      if ($LASTEXITCODE -eq 0) {
        return @("docker-compose")
      }
    } catch {}
  }
  throw "Docker Compose не найден или не исполняется (ни 'docker compose', ни 'docker-compose'). Проверьте, что Docker Desktop установлен, и перезапустите PowerShell."
}

function Compose([string[]]$args){
  if (-not $script:ComposeCmd -or $script:ComposeCmd.Count -eq 0) {
    throw "Docker Compose не найден или не инициализирован. Проверьте установку Docker Desktop и перезапустите PowerShell."
  }
  try {
    & $script:ComposeCmd @args
  } catch {
    throw "Ошибка запуска Docker Compose: $($_.Exception.Message)"
  }
  if ($LASTEXITCODE -ne 0){ throw "Команда 'docker compose $args' завершилась ошибкой." }
}

function Test-DockerAvailability {
    Write-Info "Проверка Docker..."
    
    # Check Docker installation
    $dockerPath = (Get-Command "docker" -ErrorAction SilentlyContinue).Path
    if (-not $dockerPath) {
        Write-Err "Docker не установлен или не доступен в PATH."
        Write-Host "→ Установите Docker Desktop с https://www.docker.com/products/docker-desktop" -ForegroundColor Yellow
        return $false
    }

    # Check Docker service
    $dockerService = Get-Service "com.docker.service" -ErrorAction SilentlyContinue
    if (-not $dockerService -or $dockerService.Status -ne 'Running') {
        Write-Err "Служба Docker не запущена."
        Write-Host "→ Запустите Docker Desktop и попробуйте снова." -ForegroundColor Yellow
        return $false
    }

    # Test Docker functionality
    try {
        $null = docker version 2>&1
        if ($LASTEXITCODE -ne 0) { throw "Docker version check failed" }
    } catch {
        Write-Err "Docker установлен, но не отвечает."
        Write-Host "→ Перезапустите Docker Desktop и попробуйте снова." -ForegroundColor Yellow
        return $false
    }

    return $true
}

try {
  Push-Location $PSScriptRoot

  Write-Host "[+] Проверка требований…"

  if (-not (Test-DockerAvailability)) {
      exit 1
  }

  # Check docker-compose availability using existing Get-ComposeCmd function
  $script:ComposeCmd = Get-ComposeCmd

  # Явная проверка запуска docker compose до сборки
  try {
    & $script:ComposeCmd version | Out-Null
  } catch {
    Write-Err "Docker Compose не исполняется (PATH не обновлён или требуется перезапуск PowerShell)."
    Write-Host "→ Закройте все окна PowerShell и откройте новое, либо перезагрузите компьютер после установки Docker Desktop." -ForegroundColor Yellow
    exit 1
  }
  if ($LASTEXITCODE -ne 0) {
    Write-Err "Docker Compose не исполняется (ошибка запуска). Проверьте установку и перезапустите PowerShell."
    Write-Host "→ Закройте все окна PowerShell и откройте новое, либо перезагрузите компьютер после установки Docker Desktop." -ForegroundColor Yellow
    exit 1
  }

  if ($PSVersionTable.PSVersion.Major -lt 7){
    Write-Warn "Рекомендуется PowerShell 7+. Текущая версия: $($PSVersionTable.PSVersion)"
  }
  Write-Ok "Инструменты найдены"

  # Сбор пользовательских параметров (если не переданы флагами)
  if (-not $Domain){ $Domain = Read-Host "Домен (например, mmvs.ru). Можно оставить пустым" }
  if (-not $MongoPassword){ $MongoPassword = New-RandomPassword 30 }
  $gpuFlag = if ($GPU) { "1" } else { "0" }

  # .env
  Ensure-File ".env" ".env.example"
  Write-Info "Заполняем .env"
  if ($Domain){ Set-EnvVarInFile ".env" "DOMAIN" $Domain }
  Set-EnvVarInFile ".env" "GPU_ENABLED" $gpuFlag
  Set-EnvVarInFile ".env" "LLM_MODEL" $Model
  Set-EnvVarInFile ".env" "MONGO_INITDB_ROOT_USERNAME" $MongoUser
  Set-EnvVarInFile ".env" "MONGO_INITDB_ROOT_PASSWORD" $MongoPassword
  Set-EnvVarInFile ".env" "APP_PORT" "$AppPort"
  if ($CrawlUrl){ Set-EnvVarInFile ".env" "CRAWL_START_URL" $CrawlUrl }

  # Бэкап env
  $stamp = (Get-Date).ToString("yyyyMMddHHmmss")
  $backupDir = "deploy-backups"
  if (-not (Test-Path $backupDir)){ New-Item -ItemType Directory -Path $backupDir | Out-Null }
  $zip = Join-Path $backupDir "$stamp-windows.zip"
  Write-Info "Бэкап env -> $zip"
  $envFiles = Get-ChildItem -File -Filter ".env*" | % { $_.FullName }
  if ($envFiles.Count -gt 0){
    Compress-Archive -Path $envFiles -DestinationPath $zip -Force
    Write-Ok "Бэкап сохранён"
  } else {
    Write-Warn "Файлы .env* не найдены — пропускаем бэкап"
  }

  # Сборка (последовательно, чтобы исключить 'unknown flag: --no-parallel')
  if (-not $NoBuild){
    Write-Info "Сборка образов (последовательно)…"
    $services = @("app","celery_worker","celery_beat","telegram-bot")
    foreach($svc in $services){
      try {
        Write-Info "build $svc"
        Compose @("build", $svc)
      } catch {
        Write-Warn "Не удалось собрать $svc напрямую, пробуем общее 'up --build' позже. Детали: $($_.Exception.Message)"
      }
    }
  } else {
    Write-Warn "Флаг -NoBuild: сборка пропущена"
  }

  # docker compose up
  Write-Info "Запуск контейнеров…"
  $composeArgs = @("up","-d")
  if (-not $NoBuild){ $composeArgs += "--build" }
  # Если есть windows-оверрайд — используем
  if (Test-Path "docker-compose.override.windows.yml"){
    $composeArgs = @("-f","docker-compose.yml","-f","docker-compose.override.windows.yml") + $composeArgs
  }
  Compose $composeArgs
  Write-Ok "Контейнеры подняты"

  # Health-check API: проверяем с хоста, чтобы не требовался curl в контейнере
  $healthPaths = @("/healthz","/health","/api/healthz")
  $deadline = (Get-Date).AddSeconds($HealthTimeoutSec)
  $healthy = $false
  Write-Info "Ожидание готовности API (до $HealthTimeoutSec сек)…"
  while((Get-Date) -lt $deadline -and -not $healthy){
    foreach($p in $healthPaths){
      $url = "http://localhost:$AppPort$p"
      try{
        $resp = Invoke-WebRequest -Uri $url -TimeoutSec 5 -UseBasicParsing
        if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 300){
          Write-Ok "API готово: $url"
          $healthy = $true
          break
        }
      } catch {
        Start-Sleep -Seconds 3
      }
    }
  }
  if (-not $healthy){
    Write-Err "API не ответило вовремя. Показываю последние логи приложения:"
    try { Compose @("logs","--tail","200","app") } catch {}
    throw "Health-check провалился."
  }

  # Первичный crawl (опционально)
  if ($CrawlUrl){
    Write-Info "Старт первичного crawl по $CrawlUrl"
    Write-Warn "Если имя CLI-модуля проекта иное — поправьте команду ниже под ваш код."
    try {
      Compose @("run","--rm","app","python","-m","sitellm_vertebro.crawl","--url",$CrawlUrl)
    } catch {
      Write-Warn "CLI для crawl не найден или завершился с ошибкой. Шаг можно выполнить вручную позднее."
    }
  } else {
    Write-Warn "CRAWL_START_URL не задан — шаг crawl пропущен."
  }

  Write-Ok "Готово! Приложение должно отвечать на http://localhost:$AppPort/"
  Write-Info "Подсказка: задать вопрос модели по HTTP можно из PowerShell так:"
  Write-Host @"
Invoke-RestMethod -Uri "http://localhost:$AppPort/api/chat" -Method POST `
  -ContentType "application/json" `
  -Body (@{messages=@(@{role="user";content="Привет!"})} | ConvertTo-Json -Depth 5)
"@
}
catch {
  Write-Err $_.Exception.Message
  exit 1
}
finally {
  Pop-Location
}
