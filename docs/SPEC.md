# SPEC — Финальный проект по AI Driven Development

**Вариант:** №3 — «Мероприятия»

## 1. Назначение

Веб-приложение с бронированием мероприятий в зале.

- **Зритель (клиент)** выбирает конкретное место в зале и бронирует его.
- **Организатор (сотрудник / администратор)** подтверждает бронь.
- **Особое правило:** выбранное место удерживается **10 минут** (`held_until = now + 10min`).
  Если заказ не подтверждён в течение этого времени, место считается свободным
  при проверке и показе зала (фон задачи не требуется).

## 2. Текущий стек

- Backend: **FastAPI** (REST API)
- Frontend: **React**
- База данных: **MongoDB** (Motor / PyMongo)
- Auth: JWT — access (15 мин) / refresh (7 дней, blacklist в коллекции `refresh_tokens`)
- Бан: bcrypt (passlib) + python-jose (HS256)

## 3. Роли и авторизация

| Роль | Права |
|---|---|
| `client` | Бронирует места, ведёт свои брони, отменяет |
| `employee` | Панель: брони на день, смена статуса |
| `admin` | Управление каталогом и пользователями, отчёт |

- JWT: access — короткий (15 мин, подпись, без БД); refresh — 7 дней, blacklist (коллекция `refresh_tokens`: jti, user_id, revoked, expires_at).
- Logout: помечать refresh-токен как revoked.
- Все проверки прав — на backend. Клиент видит и меняет только свои брони
  (фильтр по `user_id` текущего пользователя); чужая бронь → 404/403.

## 4. Коллекции MongoDB — минимум 6 шардов/коллекций связанных данных

1. `users` — email, password_hash, role, is_active, created_at, updated_at
2. `resources` — name, resource_type, capacity, image, description, created_at, updated_at
   (каталог объектов: залы, переговорные, площадки — для мероприятий «конкретное место в зале»)
3. `bookings` — user_id, resource_id, status, start_at, end_at, held_until, created_at, updated_at, confirmed_at, confirmed_by, cancelled_at, cancel_reason
4. `status_logs` — booking_id, from_status, to_status, changed_by, changed_at, note (журнал действий)
5. `refresh_tokens` — jti, user_id, revoked, created_at, expires_at (blacklist refresh)
6. `booking_participants` — booking_id, user_id, created_at (участники/гости, приглашённые на мероприятие)

Индекс: `bookings.resource_id + start_at`.

## 5. Бронирование и защита от двойного бронирования

- Активные брони: `status IN ('created','confirmed')` и `held_until > now`.
- Пересечение интервалов: `start_at < :new_end AND end_at > :new_start`.
- Конфликт → `409 Conflict`.
- В FastAPI проверка выполняется перед вставкой; для конкурентной целостности — атомарная операция/блокировка.

## 6. Статусы брони

- `created -> confirmed, cancelled`
- `confirmed -> completed, cancelled`
- `completed`, `cancelled` — терминальны
- Недопустимый переход → `409`. Статус + запись в журнал — атомарно.

## 7. API (FastAPI)

- `POST /api/auth/register`, `POST /api/auth/login`, `POST /api/auth/refresh`, `POST /api/auth/logout`, `GET /api/auth/me`
- `GET /api/resources/{resource_id}`
- `POST /api/bookings`, `POST /api/bookings/{booking_id}/status`
- `GET /api/reports/...`

## 8. Экраны (React)

Auth → Каталог (поиск/фильтры/пагинация, карточка с изображением) → Бронирование (выбор места, время, занятость, ошибки) → Мои брони → Панель сотрудника → Панель администратора → Отчёт/CSV → Журнал действий. На каждом экране: loading / empty / error.

## 9. Отчёт

Агрегация MongoDB (group), параметры периода, даты в одном часовом поясе.

## 10. Тесты — минимум 15 backend

Auth, права доступа, переходы статусов, особое правило (hold), конкурентное бронирование (10 параллельных запросов → 1 бронь).

## 11. Demo data — одна команда

Один пользователь каждой роли, минимум 20 объектов, минимум 30 броней.

## 12. Секреты

`.env` (вне репозитория) + `.env.example` в репозитории. Без секретов в истории коммитов.
