# AI_LOG — журнал ИИ-агента

Проект: финальный проект СРС «AI Driven Development», вариант №3 «Мероприятия» (React + FastAPI + MongoDB).

## Сессии

### 2026-11-09 — Обзор проекта
- Прочитаны AGENTS.md, docs/SPEC.md, docs/PLAN.md, бэкенд и фронтенд-шаблон.
- Зафиксировано состояние: бэкенд (auth, бронирование, статусы, тесты) готов частично, фронтенд — шаблон Vite.
- План работ по неделям 2–3. История: `docs/prompts/2026-11-09_01_overview.txt`.

### 2026-11-09 — Неделя 2: основная логика
- Каталог ресурсов: поиск, фильтр по типу, пагинация.
- Бронирование: атомарная блокировка ресурса через `bookings_locks` (`find_one_and_update` + upsert), `DuplicateKeyError` → 409; повторная попытка при истёкшей блокировке (>10 мин).
- Hold 10 минут: `held_until = now + 10min`, конфликт учитывает `held_until > now`.
- Статусы: допустимые переходы `created→{confirmed,cancelled}`, `confirmed→{completed,cancelled}`; недопустимые/терминальные → 409; журнал в `status_logs`.
- Тест конкурентности: 10 параллельных запросов → 1 бронь, остальные 409. Тест освобождения после истечения hold.
- История: `docs/prompts/2026-11-09_02_week2.txt`.

### 2026-11-09 — Неделя 3: фронтенд, отчёт, админ
- Фронтенд: `api/client.js`, `AuthContext`, `Layout`, страницы Login/Register/Catalog/Book/MyBookings/Panel/Admin/Reports/Logs, роутинг.
- Бэкенд: панель бронирований `GET /api/bookings?date=&resource_id=`, логи брони/общие `GET /api/bookings/{id}/logs`, `GET /api/logs`.
- Отчёты: `POST /api/reports` (агрегация MongoDB по периоду/ресурсу), `POST /api/reports/csv` (StreamingResponse).
- Админ: `GET/PATCH/DELETE /api/admin/users`, `DELETE /api/resources/{id}`.
- Тесты доведены до 28, все проходят. История: `docs/prompts/2026-11-09_03_week3.txt`.

### 2026-11-11 — Финализация и подготовка к защите
- Исправлен `backend/app/database.py`: клиент MongoDB создаётся из `settings.MONGODB_URL` (без дублирования чтения env).
- Исправлен `backend/scripts/seed.py`: добавлен `sys.path` на `backend/` для корректного импорта `app.*` при запуске скрипта.
- Переписан `frontend/src/index.css` под проектные компоненты (layout, формы, таблицы, статусы, сетка каталога).
- Обновлены `docs/AI_LOG.md`, `docs/AI_REVIEW.md`, `README.md`; сохранена история промптов в `docs/prompts/`.
- Прогон тестов: `pytest backend/tests -q` → 28 passed (mongomock-motor).
- Попытка запуска seed на MongoDB Atlas из `backend/.env` завершилась ошибкой аутентификации (`bad auth`, AtlasError 8000) — учётные данные/доступ в окружении недействительны; seed оставлен рабочим при корректном `MONGODB_URL`.
- История: `docs/prompts/2026-11-11_04_finalize.txt`.
