# Прогноз потребления в МО и раннее обнаружение шоков

Прогноз безналичных потребительских расходов муниципальных образований на 1, 3, 6 и 12 месяцев
по данным СберИндекса и онлайн-обнаружение структурных сдвигов (шоков).
Подробная методология — в методологическом отчёте.

## Результаты

| Модель | MAE h=1, руб. | h=3 | h=6 | h=12 |
| --- | --- | --- | --- | --- |
| Сезонный бейзлайн с трендом + LightGBM | **907** | **1355** | **1620** | — |
| Prophet (бейзлайн) | 1530 | 1769 | 2145 | **2997** |
| Chronos-Bolt, zero-shot | 2058 | 2799 | 4444 | 9842 |

Обнаружение шоков: лучший метод — BOCPD (F1 0,68 на синтетике, 4 ложные тревоги за 2019–2026 на национальных рядах).

## Структура

```
notebooks/   01_build_panel  — сбор панели «МО × месяц» и признаков
             02_backtest     — бэктест: naive, seasonal naive, Prophet, LightGBM, ансамбли
             03_changepoints — сравнение детекторов: PELT, BinSeg, CUSUM, BOCPD, EWMA-остатки
             07_foundation_models_eval — сравнение Chronos с Prophet и бейзлайнами
colab/       04_chronos_colab, 06_chronos_national_colab — Chronos-Bolt (GPU)
             05_news_gdelt   — новостной поток GDELT по регионам
scripts/     build_inflation_expectations.py — ряды инфляционных ожиданий из Excel ЦБ
configs/     backtest.yaml, changepoints.yaml — все гиперпараметры
data/raw/        исходные файлы (в .gitignore, см. ниже)
data/external/   events_calendar.csv — календарь событий с источниками
data/processed/  panel_mo_month.parquet, mo_matching_log.csv
results/         метрики (csv), прогнозы, графики
```

## Данные (`data/raw/`)

| Файл | Источник |
| --- | --- |
| `potrebitelskie-beznalicnye-rashody-na-urovne-munizipalnyh-obrazovanij_ru_*.parquet` | СберИндекс: траты по МО |
| `consumer-spending_ru_*.parquet`, `consumer-spending-growth_ru_*.parquet`, `consumper-spending-index-sa_ru_*.parquet` | СберИндекс: национальные ряды |
| `potrebitelskaya-aktivnost-...parquet`, `ver-izmenenie-trat-po-kategoriyam_ru_*.parquet` | СберИндекс: недельные ряды |
| `BUL_MO_2023.xlsx`, `BUL_MO_2024.xlsx` | Росстат: численность населения по МО |
| `ipc_mes_08-2026.xlsx`, `ipc_RF_fo_sub_08-2026.xlsx` | Росстат: ИПЦ по России и регионам |
| `tab2-zpl_07-2026.xlsx`, `trud_3_15-72.xlsx` | Росстат: зарплата, безработица |
| `02_04_New_loans_ind.xlsx` | Банк России: кредиты физлицам по регионам |
| `key_rate_monthly_2023_2026.parquet`, `cbr_inflation_expectations_key.parquet` | Банк России: ключевая ставка, инфляционные ожидания |

## Запуск

```bash
pip install -r requirements.txt
# положить исходные файлы в data/raw/
# (необязательно) пересобрать инфляционные ожидания из Excel ЦБ в data/raw/infl_exp/:
python scripts/build_inflation_expectations.py
# запустить по порядку из папки notebooks/:
#   01_build_panel -> 02_backtest -> 03_changepoints -> 07_foundation_models_eval
```

Ноутбуки Chronos запускаются в Google Colab с GPU; результат (`chronos_*.parquet`) кладётся в `results/`.
Prophet обучается ~7 минут и кешируется в `results/`; полный бэктест — около 25 минут на одном ядре.
Зерно случайности — 42.

## Ограничения

24 месяца истории по МО (горизонт 12 месяцев проверен на одном окне); 7% названий МО не сопоставлены
с ОКТМО из-за отсутствия идентификаторов в открытом датасете; в данных нет Белгородской области
и приграничных районов Курской.
