# Инструкция для бэкендера: лиды, сделки, статистика, фильтры

Документ описывает, что должен поддерживать бэк для фронта CRM по разделам:
- Лиды (`/app/leads`)
- Сделки (`/app/deals`)
- Дашборд и статистика (`/app`)
- Общая фильтрация, сортировка, пагинация

## 1) Общие требования к API

### 1.1 Формат списка (единый для всех разделов)
- `GET`-списки должны поддерживать пагинацию:
```json
{
  "count": 123,
  "next": "https://...page=2",
  "previous": null,
  "results": []
}
```

### 1.2 Если фронт прислал фильтры — бэк обязан применить
- Если фильтр невалидный -> `400` с объяснением поля.
- Если фильтр валидный, но совпадений нет -> `200` и пустой `results`.

### 1.3 Multitenancy обязательно
- Любые сущности отдаются только в рамках `company_id` текущего пользователя.
- Нельзя отдавать или менять данные другой компании.

### 1.4 Аудит
- Для ключевых действий писать историю: кто, когда, что изменил (статус лида, сумма сделки, удаление).

---

## 2) Лиды

## 2.1 Какие кнопки/действия есть на фронте
- `Новый лид` -> создать лид.
- `Детали` -> открыть карточку лида.
- `В сделку` -> конвертация лида в сделку.
- `Изменить статус` (в карточке/таблице).
- `Назначить ответственного` (manager/employee).
- `Удалить` (только admin/manager при наличии прав).

## 2.2 Обязательные endpoint-ы
- `GET /api/leads/` — список лидов.
- `POST /api/leads/` — создать лид.
- `GET /api/leads/{id}/` — карточка лида.
- `PATCH /api/leads/{id}/` — частичное обновление.
- `DELETE /api/leads/{id}/` — удалить/архивировать лид.
- `POST /api/leads/{id}/convert/` — конвертация в сделку.
- `GET /api/leads/{id}/history/` — история изменений (рекомендуется).

## 2.3 Поля лида (минимум)
- `id`
- `first_name`, `last_name`
- `phone`, `email`
- `source` (instagram, сайт, звонок, реферал...)
- `status` (`new`, `in_progress`, `qualified`, `converted`, `closed_lost`)
- `budget` (nullable)
- `comment` (nullable)
- `responsible_id`
- `created_at`, `updated_at`

## 2.4 Фильтрация лидов
- Поиск: `search` (имя/телефон/email).
- Статус: `status`.
- Источник: `source`.
- Ответственный: `responsible_id`.
- Период создания: `created_from`, `created_to`.

Пример:
- `GET /api/leads/?search=иван&status=in_progress&responsible_id=15&created_from=2026-04-01&created_to=2026-04-30&page=1&page_size=20&ordering=-created_at`

## 2.5 Конвертация лида в сделку
`POST /api/leads/{id}/convert/`

Ожидаемое поведение:
- Проверить, что лид еще не `converted`.
- Создать сделку.
- Обновить статус лида в `converted`.
- Вернуть созданную сделку или `deal_id`.

Пример response:
```json
{
  "lead_id": 77,
  "deal_id": 312,
  "status": "converted"
}
```

---

## 3) Сделки (deals)

## 3.1 Какие кнопки/действия есть на фронте
- `Новая сделка`.
- `Редактировать сделку`.
- `Переместить по этапу` (воронка).
- `Закрыть как успешно`.
- `Закрыть как проиграно`.
- `Удалить сделку` (ограниченно по ролям).

## 3.2 Обязательные endpoint-ы
- `GET /api/deals/`
- `POST /api/deals/`
- `GET /api/deals/{id}/`
- `PATCH /api/deals/{id}/`
- `DELETE /api/deals/{id}/`
- `POST /api/deals/{id}/stage/` — смена этапа.
- `POST /api/deals/{id}/close-won/`
- `POST /api/deals/{id}/close-lost/`
- `GET /api/deals/{id}/history/` (рекомендуется)

## 3.3 Поля сделки (минимум)
- `id`
- `title`
- `client_id`
- `lead_id` (nullable, если сделка создана не из лида)
- `amount`
- `currency` (`RUB` по умолчанию)
- `stage` (`new`, `contacted`, `proposal`, `negotiation`, `won`, `lost`)
- `close_reason` (nullable; обязательно для lost)
- `responsible_id`
- `expected_close_date` (nullable)
- `created_at`, `updated_at`, `closed_at` (nullable)

## 3.4 Фильтрация сделок
- Поиск: `search` (название, клиент).
- Этап: `stage`.
- Ответственный: `responsible_id`.
- Диапазон суммы: `amount_min`, `amount_max`.
- Период закрытия: `closed_from`, `closed_to`.
- Только активные: `is_active=true` (исключить won/lost при необходимости).

---

## 4) Статистика и дашборд

## 4.1 Что должно отображаться на фронте
- Количество лидов.
- Количество активных сделок.
- Сумма сделок в работе.
- Конверсия лид -> сделка.
- Выручка (won).
- Динамика по периодам (день/неделя/месяц).
- Разрез по менеджерам.

## 4.2 Обязательные endpoint-ы статистики
- `GET /api/dashboard/summary/`
- `GET /api/dashboard/funnel/`
- `GET /api/dashboard/revenue/`
- `GET /api/dashboard/manager-performance/`

Допустимо объединить в 1 endpoint:
- `GET /api/dashboard/analytics/`

### Query параметры для аналитики
- `scope=company|team|personal`
- `period=day|week|month|quarter|year|custom`
- `date_from`, `date_to`
- `responsible_id` (для admin/manager)

## 4.3 Пример response summary
```json
{
  "leads_total": 420,
  "leads_new": 54,
  "deals_active": 63,
  "deals_won": 18,
  "pipeline_amount": 2850000,
  "won_amount": 740000,
  "conversion_rate": 0.23,
  "avg_check": 41111
}
```

## 4.4 Пример response funnel
```json
{
  "stages": [
    { "key": "new", "count": 120 },
    { "key": "in_progress", "count": 90 },
    { "key": "qualified", "count": 56 },
    { "key": "converted", "count": 34 },
    { "key": "won", "count": 18 },
    { "key": "lost", "count": 16 }
  ]
}
```

---

## 5) Единая логика фильтрации/сортировки

Для `GET /leads/`, `GET /deals/`, `GET /clients/` сделать одинаковый подход:
- `page`, `page_size`
- `search`
- `ordering` (например, `-created_at`, `amount`, `status`)
- `created_from`, `created_to`

Важно: чтобы фронт мог переиспользовать один фильтр-компонент, названия query-параметров должны быть максимально едиными.

---

## 6) Права по ролям (кратко)

- `admin`
  - лиды: full CRUD + convert
  - сделки: full CRUD + close-won/lost
  - статистика: company/team/personal

- `manager`
  - лиды: CRUD в рамках команды + convert
  - сделки: CRUD в рамках команды
  - статистика: team/personal

- `employee`
  - лиды: read/update только назначенные
  - сделки: read/update stage только назначенные
  - статистика: personal

---

## 7) Ошибки и edge cases

- Конвертация уже сконвертированного лида -> `409`.
- Попытка закрыть `lost` без `close_reason` -> `400`.
- Попытка доступа к чужой сделке/лиду в другой компании -> `404` или `403` (единообразно по проекту).
- Некорректный диапазон дат (`from > to`) -> `400`.

---

## 8) Рекомендации по производительности

- Индексы: `company_id`, `status`, `responsible_id`, `created_at`, `stage`.
- Для тяжелой статистики — кэш на короткий TTL (30-120 сек) или materialized view.
- Поддержать агрегации на уровне БД (не в Python/Node циклах на больших данных).

---

## 9) Definition of Done для бэка

Считаем задачу закрытой, когда:
- Все endpoint-ы выше реализованы и покрыты базовыми тестами.
- Роли `admin/manager/employee` реально ограничивают доступ.
- Фильтрация, сортировка и пагинация работают единообразно.
- Фронт может:
  - создать лид;
  - конвертировать лид в сделку;
  - двигать сделку по этапам;
  - получить цифры дашборда за выбранный период.
