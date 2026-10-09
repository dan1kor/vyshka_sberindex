"""Ключевая ставка Банка России → помесячный ряд.

Источник: Excel-выгрузка https://www.cbr.ru/hd_base/KeyRate/ в data/raw/KeyRate.xlsx.
Результат: файл из configs/panel.yaml → files.key_rate (колонки month, key_rate_pct) — ставка, действовавшая
на первый день месяца (известна в начале месяца, поэтому в панели её лаг публикации = 0).
"""
from pathlib import Path
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
CFG = yaml.safe_load((ROOT / "configs" / "panel.yaml").read_text(encoding="utf-8"))
src = ROOT / "data" / "raw" / "KeyRate.xlsx"
d = pd.read_excel(src)
date_col = next(c for c in d.columns if "дат" in str(c).lower())
rate_col = next(c for c in d.columns if "став" in str(c).lower())
d = pd.DataFrame({"date": pd.to_datetime(d[date_col], dayfirst=True),
                  "rate": pd.to_numeric(d[rate_col].astype(str).str.replace(",", "."), errors="coerce")}).dropna()
daily = d.set_index("date").rate.sort_index().asfreq("D").ffill()      # ставка действует до следующего решения
monthly = daily[daily.index.day == 1].rename("key_rate_pct").rename_axis("month").reset_index()
monthly.to_parquet(ROOT / "data" / "raw" / CFG["files"]["key_rate"], index=False)
print(monthly.tail())
