# SPEC — Финальный проект по AI Driven Development

**Вариант:** №3 — «Мероприятия»

## 1. Назначение

Веб-приложение с бронированием мероприятий в зале.

- **Зритель (клиент)** выбирает конкретное место в зале и бронирует его.
- **Организатор (сотрудник / администратор)** подтверждает бронь.
- **Особое правило:** выбранное место удерживается **10 минут** (`held_until = now + 10min`).
  Если заказ не подтверждён в течение этого времени, место считается свободным
  при проверке и показе зала (фон задачи не требуется).

## 2. Роли и авторизация

| Роль | Права |
|---|---|
| `client` | Бронирует места, ведёт свои брони, отменяет |
| `employee` | Панель: брони на день, смена статуса |
| `admin` | Управление каталогом и пользователями, отчёт |

- JWT: access — короткий (15 мин, подпись, без БД), refresh — длинный (7 дней, blacklist).
- Logout: отозвать refresh-токен (SimpleJWT `token_blacklist`).
- Все проверки прав — на backend. Клиент видит и меняет только свои брони
  (`WHERE id = :id AND user_id = :current_user`); чужая бронь по прямому URL → 404/403.

## 3. Схема БД — минимум 6 таблиц (только через миграции)

1. `users` — id, email (unique), password_hash, role, created_at, updated_at
2. `resources` — id, name, resource_type, capacity, image, description, created_at, updated_at
   (каталог объектов: залы, переговорные, площадки — для мероприятий «конкретное место в зале»)
3. `bookings` — id, user_id FK→users, resource_id FK→resources, status,
   start_at, end_at, held_until, created_at, updated_at, confirmed_at, confirmed_by FK→users nullable,
   cancelled_at, cancel_reason
4. `status_logs` — id, booking_id FK→bookings, from_status, to_status, changed_by FK→users nullable,
   changed_at, note (журнал действий: кто, когда, какой статус изменил)
5. `refresh_tokens` — id, user_id FK→users, jti, revoked, created_at, expires_at (blacklist refresh)
6. `booking_participants` — id, booking_id FK→bookings, user_id FK→users, created_at
   (участники/гости, приглашённые на мероприятие)

Индекс: `bookings(resource_id, start_at)`.

## 4. Бронирование и защита от двойного бронирования

- Активные брони: `status IN ('created', 'confirmed')` и срок удержания не истёк (`held_until > now`).
- Пересечение интервалов: `start_at < :new_end AND end_at > :new_start`.
- Конфликт → `409 Conflict`.
- Алгоритм: `transaction.atomic()` → `Resource.objects.select_for_update().get(pk=...)` → проверка → INSERT → COMMIT; при конфликте ROLLBACK + 409.

## 5. Статусы брони

- `created -> confirmed, cancelled`
- `confirmed -> completed, cancelled`
- `completed`, `cancelled` — терминальны

- Недопустимый переход → `409`. Новый статус + запись в журнал — в одной транзакции.

## 6. JWT

- Access: 15 мин, проверка подписи без обращения к БД.
- Refresh: 7 дней, blacklist; `POST /api/auth/refresh` → новый access; logout → revoke.

## 7. API (Django REST)

- `POST /api/auth/register|login|refresh|logout`
- `GET /api/resources` — поиск, фильтры, пагинация (с сервера)
- `GET /api/resources/{id}`
- `POST /api/bookings` — создать бронь
- `GET /api/bookings/mine` — мои брони (текущие + история)
- `GET /api/bookings/{id}` — только свои (иначе 404/403)
- `POST /api/bookings/{id}/cancel`
- `POST /api/bookings/{id}/status` — employee/admin
- `GET /api/admin/resources`, `GET /api/admin/users`
- `GET /api/reports/bookings?from=&to=` — SQL-агрегация → CSV

## 8. Экраны (React)

Auth → Каталог (поиск/фильтры/пагинация, карточка с изображением) → Бронирование (выбор места, время, занятость, ошибки) → Мои брони → Панель сотрудника → Панель администратора → Отчёт/CSV → Журнал действий. На каждом экране: loading / empty / error.

## 9. Отчёт

SQL-агрегация через JOIN, условия периода — в `ON`, параметры — через подстановку (без SQL-инъекции), даты в одном часовом поясе, индекс по `resource_id, start_at`.

## 10. Тесты — минимум 15 backend

Права доступа, переходы статусов, особое правило (hold), конкурентное бронирование (10 параллельных запросов → 1×201, 9×409, 1 запись).

## 11. Demo data — одна команда

Один пользователь каждой роли, минимум 20 объектов, минимум 30 броней.

## 12. Секреты

`.env` (вне репозитория) + `.env.example` в репозитории. Без секретов в истории коммитов.
