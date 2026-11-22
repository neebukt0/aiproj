# Мероприятия — бронирование мест в зале

Финальный проект СРС «AI Driven Development», вариант №3.

Веб-приложение для бронирования ресурсов (залы/переговорные): React + FastAPI + MongoDB, JWT-аутентификация.

## Стек
- Backend: FastAPI, Motor (MongoDB), python-jose (JWT HS256), passlib/bcrypt
- Frontend: React (Vite), React Router, Axios
- Тесты: pytest, Vitest + Testing Library, Playwright
- БД: MongoDB

## Структура
```
backend/
  app/                 # auth, bookings, resources, reports, logs, users, schemas, config, database, main
  scripts/seed.py      # demo-данные
  scripts/mock_server.py  # FastAPI + mongomock для frontend/E2E
  tests/               # pytest (51 тест)
frontend/
  src/api/contexts/components/pages
  src/test/setup.js    # настройка Vitest (jsdom, jest-dom)
  src/**/*.test.jsx    # 55 компонентных тестов
  e2e/*.spec.js        # 13 E2E-сценариев Playwright
docs/
  SPEC.md, PLAN.md, AI_LOG.md, AI_REVIEW.md, prompts/ (13 файлов истории)
```

## Запуск

### Backend
```bash
cd backend
python -m venv .venv && .venv\Scripts\activate   # Windows (или source .venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env   # задать MONGODB_URL, MONGODB_DB, SECRET_KEY
python scripts/seed.py   # наполнение демо-данными (опционально)
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```
По умолчанию API ожидается на `http://localhost:8000`. Базовый URL можно задать через `VITE_API_BASE` в `frontend/.env`.

## Тесты
```bash
cd backend
pytest -q                       # 51 тест, mongomock-motor без MongoDB

cd ../frontend
npm test                        # 55 компонентных тестов (Vitest + jsdom)
npm run test:watch              # watch-режим Vitest
npm run test:e2e                # 13 E2E-сценариев Playwright
```
Backend-тесты используют `mongomock-motor` и не требуют запущенной MongoDB.
Playwright сам поднимает mock backend (`backend/scripts/mock_server.py`) и Vite;
по умолчанию используется установленный Edge/Chrome, а не скачанный Chromium.
Для другого браузера задайте `PLAYWRIGHT_CHANNEL=chrome|msedge|chromium`.
Компонентные тесты мокают `src/api/client.js`, E2E ходят в живой mock API.

## API (основное)
- Auth: `POST /api/auth/register` (всегда роль `client`), `POST /api/auth/login`, `POST /api/auth/refresh`, `POST /api/auth/logout`, `GET /api/auth/me`
- Ресурсы: `GET /api/resources?search=&resource_type=&skip=&limit=`, `GET /api/resources/{id}`, `GET /api/resources/{id}/availability?date=YYYY-MM-DD` (публично: занятые интервалы на день), `POST /api/resources` (admin/employee), `DELETE /api/resources/{id}` (admin)
- Бронирования: `POST /api/bookings` (client, с `participant_ids`), `GET /api/bookings/mine`, `GET /api/bookings/{id}` (владелец или staff, чужой → 403), `GET /api/bookings?date=&resource_id=` (staff), `POST /api/bookings/{id}/status`, `GET /api/bookings/{id}/logs` (staff), `GET /api/bookings/{id}/participants` (владелец или staff)
- Отчёты/журнал: `POST /api/reports`, `POST /api/reports/csv` (staff), `GET /api/logs` (staff)
- Админ: `GET/POST /api/admin/users`, `PATCH/DELETE /api/admin/users/{id}` (admin)
- `GET /health`

## Интерфейс
- Тема: светлая/тёмная, переключатель 🌙/☀️ в топбаре и плавающая кнопка на
  страницах входа. Выбор хранится в `localStorage['theme']`, по умолчанию —
  системная тема; применяется до отрисовки, без вспышки.
- Картинки каталога: внешний image API без ключа — Lorem Picsum
  (`https://picsum.photos/seed/<seed>/640/360`). Seed фиксирован в `seed.py`;
  для объектов без `image` URL строится на frontend, при недоступности API
  показывается иконка типа.

## Особые правила (SPEC)
- Удержание места: `held_until = now + 10 min` для новой брони.
- При подтверждении hold продлевается до `end_at`, иначе место освободилось бы через 10 минут.
- Активные брони: `status in (created, confirmed)` и `held_until > now`.
- Экран бронирования показывает занятые интервалы выбранного дня (`/availability`).
- Конфликт интервалов (`start_at < new_end && end_at > new_start`) → 409.
- Конкурентное бронирование защищено атомарной блокировкой ресурса: из 10 параллельных запросов создаётся ровно 1 бронь.
- Кабинет клиента разделён на вкладки «Актуальные» и «История».

## Проверка конкуренции на живом сервере
```bash
cd backend
python scripts/concurrency_check.py --resource-id <id> --date 2026-12-20
# ожидаемый вывод: codes=[200, 409, ...], created=1, conflicts=9, RESULT: OK
```

## Сквозной smoke-тест
```bash
cd backend
python scripts/seed.py            # демо-данные: 3 пользователя, 20 объектов, 30 броней
python scripts/smoke_check.py     # 37 проверок на живом сервере
# ожидаемый вывод: checks: 37 passed, 0 failed, RESULT: OK
```
Проверяются все роли, каталог и поиск, занятость, бронь и 409, подтверждение,
недопустимый переход, отмена, панель, журнал, отчёты и CSV, админ-операции,
refresh/logout/blacklist. Скрипт работает через HTTP и не обращается к БД напрямую.

## Роли и права

| Роль | Что может делать | Что запрещено |
|---|---|---|
| `client` (зритель) | Смотреть каталог, бронировать место, видеть и отменять только свои брони, смотреть свои участники | Панель сотрудника, отчёты, журнал, управление пользователями/каталогом; доступ к чужим броням |
| `employee` (организатор) | Всё, что клиент, плюс брони на день, подтверждение/завершение/отмена броней, отчёты и CSV, журнал действий, создание объектов | Управление пользователями, удаление объектов |
| `admin` | Всё, что сотрудник, плюс управление пользователями (создание, блокировка, роль, удаление) и удаление объектов каталога | — |

Права проверяются на backend (`get_current_user` + роль из БД), а не только
скрытием кнопок в React. Публичная регистрация всегда создаёт `client`.

## Проверка обновления access-токена
```bash
cd backend
python scripts/refresh_check.py --email client@example.com --password ClientPass123!
# login → protected call → refresh → новый access → logout → повторный refresh 401
```

## Демо-пользователи (seed)
- `client@example.com` / `ClientPass123!`
- `employee@example.com` / `EmpPass123!`
- `admin@example.com` / `AdminPass123!`

Публичная регистрация создаёт только клиентов. Сотрудников и администраторов
создаёт администратор через `POST /api/admin/users` (или seed).

## Проверка и отчёт
- Word-отчёт: `docs/report/Отчёт_по_проекту_Мероприятия.docx`
- Скриншоты интерфейса: `docs/report/screens/`
- Проверки: `pytest -q` → 51 passed; `npm test` → 55 passed; `npm run test:e2e` → 13 passed; `npm run lint` (0 ошибок); `npm run build`; `backend/scripts/concurrency_check.py`; `backend/scripts/smoke_check.py` (37 проверок).
- История промптов: 13 файлов в `docs/prompts/` (последний — frontend-тесты и E2E).