# Мероприятия — бронирование мест в зале

Финальный проект СРС «AI Driven Development», вариант №3.

Веб-приложение для бронирования ресурсов (залы/переговорные): React + FastAPI + MongoDB, JWT-аутентификация.

## Стек
- Backend: FastAPI, Motor (MongoDB), python-jose (JWT HS256), passlib/bcrypt
- Frontend: React (Vite), React Router, Axios
- БД: MongoDB

## Структура
```
backend/
  app/                 # auth, bookings, resources, reports, logs, users, schemas, config, database, main
  scripts/seed.py      # demo-данные
  tests/               # pytest (28 тестов)
frontend/
  src/api/contexts/components/pages
docs/
  SPEC.md, PLAN.md, AI_LOG.md, AI_REVIEW.md, prompts/
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
pytest -q
```
Тесты используют `mongomock-motor` и не требуют запущенной MongoDB.

## API (основное)
- Auth: `POST /api/auth/register`, `POST /api/auth/login`, `POST /api/auth/refresh`, `POST /api/auth/logout`, `GET /api/auth/me`
- Ресурсы: `GET /api/resources?search=&resource_type=&skip=&limit=`, `GET /api/resources/{id}`, `POST /api/resources` (admin/employee), `DELETE /api/resources/{id}` (admin)
- Бронирования: `POST /api/bookings` (client), `GET /api/bookings/mine`, `GET /api/bookings?date=&resource_id=` (staff), `POST /api/bookings/{id}/status`, `GET /api/bookings/{id}/logs` (staff)
- Отчёты/журнал: `POST /api/reports`, `POST /api/reports/csv` (staff), `GET /api/logs` (staff)
- Админ: `GET/PATCH/DELETE /api/admin/users` (admin)
- `GET /health`

## Особые правила (SPEC)
- Удержание места: `held_until = now + 10 min`.
- Активные брони: `status in (created, confirmed)` и `held_until > now`.
- Конфликт интервалов (`start_at < new_end && end_at > new_start`) → 409.
- Конкурентное бронирование защищено атомарной блокировкой ресурса: из 10 параллельных запросов создаётся ровно 1 бронь.

## Демо-пользователи (seed)
- `client@example.com` / `ClientPass123!`
- `employee@example.com` / `EmpPass123!`
- `admin@example.com` / `AdminPass123!`