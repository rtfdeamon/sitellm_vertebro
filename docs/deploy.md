Автодеплой на сервер (push в main)
=================================

Что делает:
- При `push` в ветку `main` GitHub Actions подключается к целевому серверу по SSH,
  обновляет код до последнего `main`, пересобирает Docker-образы и перезапускает
  `docker compose`-стек. Проверяет здоровье API.

Что нужно на целевом сервере (один раз):
- Ничего, кроме SSH-доступа с правами `sudo` без пароля для пользователя из `SSH_USER`.
  Workflow сам установит Docker, подготовит `.env`, создаст unit-файлы systemd.

Секреты репозитория (GitHub → Settings → Secrets and variables → Actions):
- `SSH_HOST`: адрес сервера.
- `SSH_USER`: пользователь для SSH.
- `SSH_KEY`: приватный ключ (PEM) для SSH-доступа на сервер.
- `SSH_PORT` (опционально): порт SSH, по умолчанию 22.
- `APP_DIR`: путь на сервере, куда разворачивается проект, например `/opt/sitellm_vertebro`.
- `REPO_URL` (опционально): URL репозитория для `git clone` на сервере.
  - По умолчанию используется `https://github.com/rtfdeamon/sitellm_vertebro.git`.
  - Для приватного доступа используйте Deploy Key (SSH) или HTTPS с токеном.
 - `DOMAIN` (опц.): домен для reverse‑proxy (Caddy) и TLS.
 - `LETSENCRYPT_EMAIL` (опц.): контактный e‑mail для ACME у Caddy.
 - `INSTALL_PROXY` (опц.): если `caddy`, установит reverse‑proxy автоматически.
- `OPEN_APP_PORT` (опц.): `1` чтобы открыть 8000 в firewall (по умолчанию 0).
 - `USE_GPU` (опц.): `true/1` для включения GPU-режима (compose.gpu.yaml).
 - `INSTALL_NVIDIA_TOOLKIT` (опц.): `1` — поставить NVIDIA Container Toolkit.
 - `INSTALL_NVIDIA_DRIVER` (опц.): `1` — попытаться поставить проприетарный драйвер NVIDIA (может потребовать перезагрузку).

Как это работает:
- Workflow: `.github/workflows/deploy.yml`.
- Серверные скрипты:
  - `scripts/bootstrap.sh` — первая установка: ставит Docker, клонирует репозиторий в `APP_DIR`,
    генерирует `.env` (или дополняет из `*.example`), создаёт systemd-сервисы для стека и
    таймер для ежедневного краула. При заданном `DOMAIN` поставит Caddy и настроит TLS
    (авто‑сертификаты через Let’s Encrypt/ZeroSSL). Откроет порты 80/443 в UFW/Firewalld
    (если firewall активен). Опционально откроет 8000, если `OPEN_APP_PORT=1`.
  - `scripts/rollout.sh` — без интерактива обновляет стек: `git fetch/reset`,
    `docker compose pull/build/up -d` и healthcheck API.

Проверка:
- После пуша в `main` откройте Actions → Deploy и смотрите логи.
- На сервере проверьте контейнеры: `docker compose ps` в `${APP_DIR}`.

Типичные ошибки:
- Нет прав `sudo` у `SSH_USER` — дайте права или запускайте bootstrap под root.
- Приватный репозиторий — задайте `REPO_URL` (ssh/https) и используйте Deploy Key/токен.
- Firewalld/ufw закрывает порт 8000 — откройте приём внешних соединений или поставьте reverse-proxy.

Одной SSH-командой (первая установка)
-------------------------------------

Если хотите развернуть проект одной командой без GitHub Actions:

- Через `curl` на целевой машине (требуется `curl`):

  ```bash
  ssh user@server \
    'APP_DIR=/opt/sitellm_vertebro REPO_URL=https://github.com/rtfdeamon/sitellm_vertebro.git \
     CRAWL_START_URL=https://example.com \
     bash -lc "curl -fsSL https://raw.githubusercontent.com/rtfdeamon/sitellm_vertebro/main/scripts/bootstrap.sh | bash"'
  ```

- Без `curl` на сервере (передаём скрипт с локальной машины):

  ```bash
  ssh user@server \
    'APP_DIR=/opt/sitellm_vertebro REPO_URL=https://github.com/rtfdeamon/sitellm_vertebro.git \
     CRAWL_START_URL=https://example.com bash -s' < scripts/bootstrap.sh
  ```

Альтернатива — скрипт-обёртка (минимальная команда)
--------------------------------------------------

С локальной машины (где есть репозиторий):

```bash
scripts/remote_deploy.sh user@server
```

Опции: `--dir /opt/sitellm_vertebro`, `--url https://example.com`, `--domain example.com`, `--repo <URL>`, `-i key`, `-p 22`.

Все варианты:
- Установят Docker + Compose (через `sudo`).
- Клонируют репозиторий в `APP_DIR` и подготовят `.env`.
- Создадут `systemd` сервис для `docker compose up -d` и таймер ежедневного краула.
- Запустят стек (после чего API будет доступен на `http://<server>:8000`).
 - При `--domain`/`DOMAIN` — настроят Caddy с TLS. При `USE_GPU=true` — применят `compose.gpu.yaml`
   с `device_requests` для NVIDIA и переменными сборки для CUDA; при необходимости
   установят `nvidia-container-toolkit` и драйвер (если заданы соответствующие флаги).

Обновление на новой ревизии одной командой
-----------------------------------------

После первичного запуска обновление до последнего `main` можно сделать так:

```bash
ssh user@server 'APP_DIR=/opt/sitellm_vertebro BRANCH=main DOCKER_BIN="sudo docker" \
  bash -lc "cd $APP_DIR && bash scripts/rollout.sh"'
```
