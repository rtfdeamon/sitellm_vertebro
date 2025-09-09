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
  - Для публичного репо можно не задавать — будет использован
    `https://github.com/<owner>/<repo>.git`.
  - Для приватного — используйте Deploy Key (SSH) или https с токеном.

Как это работает:
- Workflow: `.github/workflows/deploy.yml`.
- Серверные скрипты:
  - `scripts/bootstrap.sh` — первая установка: ставит Docker, клонирует репозиторий в `APP_DIR`,
    генерирует `.env` (или дополняет из `*.example`), создаёт systemd-сервисы для стека и
    таймер для ежедневного краула.
  - `scripts/rollout.sh` — без интерактива обновляет стек: `git fetch/reset`,
    `docker compose pull/build/up -d` и healthcheck API.

Проверка:
- После пуша в `main` откройте Actions → Deploy и смотрите логи.
- На сервере проверьте контейнеры: `docker compose ps` в `${APP_DIR}`.

Типичные ошибки:
- Нет прав `sudo` у `SSH_USER` — дайте права или запускайте bootstrap под root.
- Приватный репозиторий — задайте `REPO_URL` (ssh/https) и используйте Deploy Key/токен.
- Firewalld/ufw закрывает порт 8000 — откройте приём внешних соединений или поставьте reverse-proxy.
