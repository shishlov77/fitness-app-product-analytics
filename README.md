# Mobile App Funnel & Retention Analytics (SQL + Python)

Это учебный, но максимально приближенный к реальности проект продуктовой аналитики мобильного приложения: генерируем данные, считаем воронку, retention (D1/D7/D30), когорты, влияние онбординга и разницу iOS vs Android, а в конце сохраняем готовые агрегаты под дашборды. [conversation_history:1]

## Зачем это
Я делал этот проект как портфолио-кейс: показать, что умею работать с табличными данными (100k пользователей), писать SQL-метрики и собирать итоговые витрины для визуализации. [conversation_history:1]

## Что именно считается
- Воронка: install → reopen (R1) → workout_start → workout_complete. [conversation_history:1]
- Retention: D1 / D7 / D30, плюс когортный разрез по дате установки. [conversation_history:1]
- Влияние onboarding: сравнение retention у тех, кто завершил обучение, и у тех, кто нет. [conversation_history:1]
- Сегментации: iOS vs Android, а также базовые срезы (например, по стране/версии приложения, если нужно). [conversation_history:1]

## Как запустить (в Google Colab)
1) Открываешь ноутбук в Colab и запускаешь ячейки сверху вниз.  
2) В процессе создаются таблицы `installs`, `sessions`, `events`, `onboarding` и грузятся в SQLite внутри ноутбука. [conversation_history:1]  
3) Дальше метрики считаются SQL-запросами и/или в pandas — как тебе удобнее. [conversation_history:1]

## Что получить на выходе (для дашбордов)
Я обычно сохраняю несколько CSV-витрин (агрегатов), чтобы дашборд строился быстро и без тяжёлых join’ов:
- funnel.csv — шаги воронки и конверсии. [conversation_history:1]
- daily_metrics.csv — DAU/инсталлы/сессии по дням (для трендов). [conversation_history:1]
- retention_cohorts_d1_d7_d30.csv — размеры когорт и D1/D7/D30 по датам установки. [conversation_history:1]
- os_metrics.csv — метрики по OS (R1/retention/completion). [conversation_history:1]
- onboarding_impact.csv — эффект обучения на retention (сравнение групп). [conversation_history:1]

## Важная ремарка про когорты
Если считать D1 по самым последним датам установок, там легко получить нули просто потому, что “следующий день” ещё не попал в окно данных (например, установки 31 декабря требуют сессий 1 января). [conversation_history:1]  
В реальной аналитике такие “неполные” когорты либо исключают из расчёта, либо расширяют период данных. [conversation_history:1]
