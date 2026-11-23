"""Datos de la pestaña Histórico: compacta la historia de precios para incrustarla en el sitio.

Formato (window.HIST en site/assets/historico-data.js):
  assets: [{id, name, group, t0, dt, v}]
    t0  primer día como días desde 1970-01-01
    dt  diferencias en días entre observaciones consecutivas (delta-encoding)
    v   cierres con 5 cifras significativas
  episodes: [{id, name, start}]
Los datos más antiguos que config.HISTORY_DAILY_YEARS se guardan como cierre semanal.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import config

EPOCH = pd.Timestamp("1970-01-01")


def _compact(s: pd.Series) -> pd.Series:
    s = s.dropna()
    s = s[~s.index.duplicated(keep="last")].sort_index()
    if s.empty:
        return s
    cutoff = s.index[-1] - pd.DateOffset(years=config.HISTORY_DAILY_YEARS)
    old = s[s.index < cutoff]
    if len(old):
        weekly = old.groupby(old.index.to_period("W-FRI")).tail(1)   # último cierre real de cada semana
        s = pd.concat([weekly, s[s.index >= cutoff]])
    return s


def payload(close: pd.DataFrame, errors: list[str], generated: str) -> dict:
    assets = []
    for group, items in config.HISTORY_ASSETS.items():
        for ticker, name in items.items():
            if ticker not in close.columns:
                continue
            s = _compact(close[ticker])
            if len(s) < 2:
                continue
            days = ((s.index.normalize() - EPOCH).days).to_numpy()
            assets.append({
                "id": ticker, "name": name, "group": group,
                "t0": int(days[0]), "dt": np.diff(days).astype(int).tolist(),
                "v": [float(f"{x:.5g}") for x in s.to_numpy()],
            })
    return {"generated": generated, "assets": assets, "episodes": config.HISTORY_EPISODES,
            "dailyYears": config.HISTORY_DAILY_YEARS, "errors": errors}


def write(data: dict, out_dir: Path) -> str:
    dest = out_dir / "assets"
    dest.mkdir(parents=True, exist_ok=True)
    js = "window.HIST=" + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n"
    (dest / "historico-data.js").write_text(js, encoding="utf-8")
    return "assets/historico-data.js"
