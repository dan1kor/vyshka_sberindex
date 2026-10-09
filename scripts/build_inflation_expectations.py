"""Сборка рядов инфляционных ожиданий инФОМ / Банка России из Excel-файлов ЦБ.

Источник: файлы *Infl_exp_YY-MM.xlsx в data/raw/infl_exp/.
Результат:
    data/raw/cbr_inflation_expectations.parquet      — вся анкета в длинном формате
    data/raw/cbr_inflation_expectations_key.parquet  — 11 ключевых рядов для модели
"""
import datetime as dt
import glob
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC, OUT = ROOT / "data" / "raw" / "infl_exp", ROOT / "data" / "raw"


def parse(f, sheet):
    d = pd.read_excel(f, sheet_name=sheet, header=None)
    rows, q, dates = [], None, None
    for i in range(1, len(d)):
        rowv = d.iloc[i, 1:]
        isdate = rowv.map(lambda x: isinstance(x, (pd.Timestamp, dt.datetime)))
        if isdate.sum() >= 3 and isdate.sum() >= 0.8 * rowv.notna().sum():      # строка с датами блока
            dates = rowv.map(lambda x: pd.Timestamp(x) if isinstance(x, (pd.Timestamp, dt.datetime)) else pd.NaT)
            continue
        lab = d.iloc[i, 0]
        if pd.isna(lab) or dates is None:
            continue
        lab = str(lab).strip()
        vals = pd.to_numeric(rowv, errors="coerce")
        if vals.notna().sum() == 0:                                               # заголовок вопроса
            q = lab
            continue
        for t, v in zip(dates, vals):
            if pd.notna(t) and pd.notna(v):
                rows.append((sheet, q, lab, t, float(v)))
    o = pd.DataFrame(rows, columns=["sheet", "question", "answer", "period", "value"])
    o["source_file"] = Path(f).name
    return o


files = sorted(glob.glob(str(SRC / "*Infl_exp_*.xlsx")), key=lambda f: re.search(r"(\d\d-\d\d)", f).group(1))
a = pd.concat([parse(f, s) for f in files for s in ["Данные за все годы", "Данные для графиков"]])
a["ord"] = a.source_file.str.extract(r"(\d\d-\d\d)")[0]
# одна и та же точка встречается в нескольких выпусках — берём самый свежий (учёт пересмотров)
full = (a.sort_values("ord").drop_duplicates(["sheet", "question", "answer", "period"], keep="last")
        .drop(columns="ord").reset_index(drop=True))
full.to_parquet(OUT / "cbr_inflation_expectations.parquet", index=False)

norm = lambda s: re.sub(r"\s+", " ", str(s)).strip().lower()
full["a"] = full.answer.map(norm)
CHART = {  # в свежих файлах ЦБ строки переименованы — сводим старые и новые названия
    "exp_1y_median": ["ожидаемая инфляция", "годовая инфляция, ожидаемая через год"],
    "obs_median": ["наблюдаемая инфляция", "годовая наблюдаемая инфляция"],
    "exp_1y_savers": ["ожидаемая инфляция среди тех, кто имеет сбережения (в %)",
                      "ожидаемая через год инфляция среди тех, кто имеет сбережения"],
    "exp_1y_nosavers": ["ожидаемая инфляция среди тех, кто не имеет сбережений (в %)",
                        "ожидаемая через год инфляция среди тех, кто не имеет сбережений"],
    "obs_savers": ["наблюдаемая инфляция среди тех, кто имеет сбережения (в %)",
                   "наблюдаемая инфляция среди тех, кто имеет сбережения"],
    "obs_nosavers": ["наблюдаемая инфляция среди тех, кто не имеет сбережений (в %)",
                     "наблюдаемая инфляция среди тех, кто не имеет сбережений"],
    "exp_5y_median": ["годовая инфляция, ожидаемая через пять лет"],
}
ALL_YEARS = {
    "ipn": ["индекс потребительских настроений (в пунктах)"],
    "idx_expectations": ["индекс ожиданий (в пунктах)"],
    "idx_current": ["индекс текущего состояния (в пунктах)"],
    "idx_big_purchases": ["индекс крупных покупок (в пунктах)"],
}
parts = []
for sheet, mapping in [("Данные для графиков", CHART), ("Данные за все годы", ALL_YEARS)]:
    s = full[full.sheet == sheet]
    for key, labels in mapping.items():
        x = s[s.a.isin(labels)][["period", "value", "source_file"]].copy()
        x["series"] = key
        parts.append(x)
k = pd.concat(parts)
k["ord"] = k.source_file.str.extract(r"(\d\d-\d\d)")[0]
k = k.sort_values("ord").drop_duplicates(["series", "period"], keep="last")
k.pivot(index="period", columns="series", values="value").sort_index().to_parquet(OUT / "cbr_inflation_expectations_key.parquet")
print("готово:", len(files), "файлов")
