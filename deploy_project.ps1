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
  if (Test-Cmd "docker"){
    # docker compose (v2) предпочительнее
    try {
      $v = (docker compose version) 2>$null
      if ($LASTEXITCODE -eq 0) { return @("docker","compose") }
    } catch {}
  }
  if (Test-Cmd "docker-compose"){ return @("docker-compose") }
  throw "Docker Compose не найден (ни 'docker compose', ни 'docker-compose')."
}

function Compose([string[]]$args){
  & $script:ComposeCmd @args
  if ($LASTEXITCODE -ne 0){ throw "Команда 'docker compose $args' завершилась ошибкой." }
}

try {
  Push-Location $PSScriptRoot

  Write-Info "Проверка требований…"
  Require-Cmd "git" "Установите Git for Windows."
  Require-Cmd "docker" "Установите Docker Desktop и запустите его."
  $ComposeCmd = Get-ComposeCmd
  if ($PSVersionTable.PSVersion.Major -lt 7){
    Write-Warn "Рекомендуется PowerShell 7+. Текущая версия: $($PSVersionTable.PSVersion)"
  }
  Write-Ok "Инструменты найдены"

  # Сбор пользовательских параметров (если не переданы флагами)
  if (-not $Domain){ $Domain = Read-Host "Домен (например, mmvs.ru). Можно оставить пустым" }
  if (-not $MongoPassword){ $MongoPassword = New-RandomPassword 30 }
  $gpuFlag = if ($GPU) { "1" } else { "0" }
  if (-not $CrawlUrl -and $Domain){ $CrawlUrl = "https://$Domain" }

  # .env
  Ensure-File ".env" ".env.example"
  Write-Info "Заполняем .env"
  if ($Domain){ Set-EnvVarInFile ".env" "DOMAIN" $Domain }
  Set-EnvVarInFile ".env" "GPU_ENABLED" $gpuFlag
  Set-EnvVarInFile ".env" "LLM_MODEL" $Model
  Set-EnvVarInFile ".env" "MONGO_INITDB_ROOT_USERNAME" $MongoUser
  Set-EnvVarInFile ".env" "MONGO_INITDB_ROOT_PASSWORD" $MongoPassword
  Set-EnvVarInFile ".env" "APP_PORT" "$AppPort"
  Set-EnvVarInFile ".env" "CRAWL_START_URL" $CrawlUrl

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
      Compose @("run","--rm","-e","CRAWL_START_URL=$CrawlUrl","app","python","-m","sitellm_vertebro.crawl","--url",$CrawlUrl)
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
