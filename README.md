# Fitness App — Продуктовая аналитика
### Анализ воронки и удержания · Декабрь 2025

![Python](https://img.shields.io/badge/Python-3.10-blue?logo=python&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791?logo=postgresql&logoColor=white)
![pandas](https://img.shields.io/badge/pandas-2.x-150458?logo=pandas&logoColor=white)
![NumPy](https://img.shields.io/badge/NumPy-1.26-013243?logo=numpy&logoColor=white)
![Seaborn](https://img.shields.io/badge/Seaborn-0.13-4EAED0)
![Tableau](https://img.shields.io/badge/Tableau-export-E97627?logo=tableau&logoColor=white)

---

## Что исследовалось

Построил ETL-пайплайн на PostgreSQL и провёл продуктовый анализ фитнес-приложения: воронка конверсии, retention-кривые, когортный анализ, влияние онбординга и сегментация по ОС.

Дополнительно локализовал причину сбоев при инициализации сессии — через анализ логов ошибок по дням, версиям приложения и платформам выяснилось, что всплески `session_init_error` коррелируют с конкретными датами деплоев, а не являются системной проблемой платформы.

Собранные агрегаты экспортированы в CSV для еженедельного продуктового ревью в Tableau.

---

## Ключевые результаты

| Метрика | Значение |
|---|---|
| Установок (реальные пользователи) | 50 000 |
| Install → Session Open | **68%** |
| Session → Workout Start | **56%** |
| Workout Start → Complete | **73%** |
| D1 Retention | **~28%** |
| D7 Retention | **~14%** |
| D30 Retention | **~6%** |
| D1: завершили онбординг vs пропустили | **35% vs 18%** |
| Session init error rate | **~6% активных юзеров** |
| Топ страна | **US (35%)** |
| Пик активности | **18:00–19:00 UTC** |

**Главный вывод:** онбординг — сильнейший рычаг retention. Пользователи, прошедшие его, возвращаются на D1 почти в 2× чаще. Снижение dropout на онбординге (сейчас ~30% бросают до последнего шага) даст прямой прирост еженедельного удержания.

---

## Стек

| Слой | Инструменты |
|---|---|
| Хранение | PostgreSQL 15 |
| ETL | Python · psycopg2 · SQLAlchemy · pandas |
| Анализ | pandas · NumPy · SQL (оконные функции, CTE) |
| Визуализация | Seaborn · Matplotlib |
| Дашборд | Tableau (CSV-экспорт из пайплайна) |

---

## Структура проекта

```
fitness-app-product-analytics/
│
├── generate_data.py            # генератор синтетических данных (NumPy, векторизация)
│
├── etl/
│   └── etl.py                  # ETL-пайплайн: CSV → PostgreSQL
│
├── notebook/
│   └── fitness_analytics.ipynb # полный анализ (9 разделов, 52 ячейки)
│
└── data/
    ├── installs.csv             # 52 500 строк (50k реальных + 2.5k ботов)
    ├── events.csv               # ~147k событий
    ├── onboarding.csv           # ~36k сессий онбординга
    └── exports/                 # CSV для Tableau
        ├── retention_cohorts.csv
        ├── funnel_by_segment.csv
        └── dau_by_segment.csv
```

---

## Разделы ноутбука

| # | Раздел | Содержание |
|---|---|---|
| 1 | Обзор данных | Размеры таблиц, фильтрация ботов, разбивка по платформам и каналам |
| 2 | Воронка конверсии | Пошаговый drop-off, воронка с процентами |
| 3 | Анализ ошибок сессии | Общая статистика, разбивка по платформам, версиям, тренд по дням |
| 4 | Retention | D1/D7/D30 общий и по платформам, когортная тепловая карта (Day 1–14) |
| 5 | Влияние онбординга | Lift retention, распределение по целям |
| 6 | Платформы и география | iOS vs Android по воронке, топ-10 стран |
| 7 | Вовлечённость | DAU/WAU тренд, пиковые часы, разбивка по типам тренировок |
| 8 | Каналы привлечения | Session rate и completion rate по каналу |
| 9 | Экспорт для Tableau | 3 сегментированных CSV |

---

## Быстрый старт

### 1. Генерация данных

```bash
pip install numpy pandas
python generate_data.py
```

### 2. Загрузка в PostgreSQL

```bash
pip install sqlalchemy psycopg2-binary
# по умолчанию: postgresql://postgres:postgres@localhost:5432/fitness_analytics
python etl/etl.py

# или с кастомным подключением:
DATABASE_URL=postgresql://user:pass@host:5432/mydb python etl/etl.py
```

### 3. Запуск ноутбука

```bash
pip install jupyter seaborn matplotlib sqlalchemy psycopg2-binary
jupyter notebook notebook/fitness_analytics.ipynb
```

Если параметры PostgreSQL отличаются от дефолтных — установи переменную `DATABASE_URL`.

---

## Модель данных

```
installs              onboarding            events
────────              ──────────            ──────
user_id      PK  ←── user_id      FK   ──► user_id        FK
install_date          started_at           event_id        PK
install_timestamp     completed_at         event_timestamp
platform              completed            event_type
country               steps_completed      platform
channel               goal                 workout_type
app_version                                session_id
is_bot
```

**Индексы:** `events(user_id)`, `events(event_type, event_timestamp)`, `installs(install_date)`, `installs(platform)`, `installs(channel)`

---

## ETL-пайплайн

`etl/etl.py` запускается один раз в неделю перед продуктовым ревью:

1. Создаёт таблицы с FK-ограничениями (если не существуют)
2. Загружает каждый CSV чанками по 5 000 строк (`method='multi'`)
3. Создаёт индексы для ускорения аналитических запросов
4. Выводит validation summary — количество строк и типов событий

Пайплайн идемпотентен: `if_exists='replace'` позволяет перезапускать без ручной очистки.

---

## Определение Retention

**D1** — пользователь с хотя бы одним `session_start` ровно на 1-й день после установки.
**D7** — вернулся в любой день в промежутке 1–7.
**D30** — вернулся в любой день в промежутке 1–30.

Когорты с менее чем 7 днями наблюдения исключаются из расчёта D7/D30 во избежание смещения по неполным окнам.
