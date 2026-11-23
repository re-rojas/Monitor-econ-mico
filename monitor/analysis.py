"""Cálculo de métricas, semáforo de entrada y estado de los tramos."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import config
from .sources import MarketData


def _last(s: pd.Series | None) -> float | None:
    if s is None:
        return None
    s = s.dropna()
    return float(s.iloc[-1]) if len(s) else None


def _col(df: pd.DataFrame, c: str) -> pd.Series:
    return df[c].dropna() if c in df.columns else pd.Series(dtype=float)


def _chg(s: pd.Series, n: int) -> float | None:
    s = s.dropna()
    return float(s.iloc[-1] - s.iloc[-1 - n]) if len(s) > n else None


def _pct(s: pd.Series, n: int) -> float | None:
    s = s.dropna()
    return float(100 * (s.iloc[-1] / s.iloc[-1 - n] - 1)) if len(s) > n else None


def rsi(s: pd.Series, n: int = 14) -> float | None:
    s = s.dropna()
    if len(s) <= n:
        return None
    d = s.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return float(100 - 100 / (1 + up.iloc[-1] / dn.iloc[-1])) if dn.iloc[-1] else 100.0


@dataclass
class Signal:
    key: str
    label: str
    detail: str
    met: bool | None  # None = sin dato


def compute_metrics(d: MarketData) -> dict:
    m: dict = {}
    f, p = d.fred, d.prices
    spx = d.spx_full if len(d.spx_full) else _col(p, "^GSPC")

    # Precio y tendencia
    if len(spx):
        ath = spx.cummax()
        m["spx"] = _last(spx)
        m["spx_ath"] = float(ath.iloc[-1])
        m["spx_ath_date"] = spx.idxmax().strftime("%Y-%m-%d")
        m["spx_dd"] = float(100 * (spx.iloc[-1] / ath.iloc[-1] - 1))
        m["spx_dd_series"] = 100 * (spx / ath - 1)
        m["spx_1d"] = _pct(spx, 1)
        m["spx_5d"] = _pct(spx, 5)
        m["spx_ma50"] = float(spx.rolling(50).mean().iloc[-1])
        m["spx_ma200"] = float(spx.rolling(200).mean().iloc[-1])
        m["spx_vs_ma200"] = 100 * (m["spx"] / m["spx_ma200"] - 1)
        m["spx_rsi"] = rsi(spx)
    for t, k in [("^NDX", "ndx"), ("RSP", "rsp")]:
        s = _col(p, t)
        if len(s):
            m[f"{k}_dd"] = float(100 * (s.iloc[-1] / s.cummax().iloc[-1] - 1))
    rsp, spy = _col(p, "RSP"), _col(p, "SPY")
    if len(rsp) and len(spy):
        ratio = (rsp / spy).dropna()
        m["rsp_spy_ratio"] = ratio
        m["rsp_spy_20d"] = _pct(ratio, 20)

    # Volatilidad
    vix = _col(p, "^VIX")
    if vix.empty:
        vix = _col(f, "VIXCLS")
    vix3m = _col(p, "^VIX3M")
    m["vix"] = _last(vix)
    if len(vix):
        m["vix_30d_max"] = float(vix.iloc[-30:].max())
        m["vix_off_peak"] = 100 * (m["vix"] / m["vix_30d_max"] - 1)
    if len(vix) and len(vix3m):
        m["vix_term"] = float(vix.iloc[-1] / vix3m.iloc[-1])

    # Tasas y Fed
    for sid in ["DGS10", "DGS2", "DGS3MO", "DFII10", "T10Y2Y", "T10Y3M"]:
        m[sid] = _last(_col(f, sid))
    m["DGS10_20d"] = _chg(_col(f, "DGS10"), 20)
    up, lo = _last(_col(f, "DFEDTARU")), _last(_col(f, "DFEDTARL"))
    if up is not None and lo is not None:
        m["fed_mid"] = (up + lo) / 2
        m["fed_range"] = f"{lo:.2f}–{up:.2f}%"
        if m["DGS2"] is not None:
            m["fed_bias"] = m["DGS2"] - m["fed_mid"]

    # Crédito (OAS en %, se muestra en puntos base)
    hy, ig = _col(f, "BAMLH0A0HYM2"), _col(f, "BAMLC0A0CM")
    m["hy_bp"] = _last(hy) * 100 if len(hy) else None
    m["ig_bp"] = _last(ig) * 100 if len(ig) else None
    m["hy_20d_bp"] = _chg(hy, 20) * 100 if len(hy) > 20 else None
    if len(hy) > config.THRESHOLDS["hy_stable_days"]:
        n = config.THRESHOLDS["hy_stable_days"]
        m["hy_stable"] = bool(hy.iloc[-1] <= hy.iloc[-1 - n])

    # Valoración
    m["pe"] = _last(d.pe_trailing)
    m["cape"] = _last(d.cape)
    if len(d.pe_trailing):
        cutoff = d.pe_trailing.index[-1] - pd.DateOffset(years=10)
        m["pe_10y_avg"] = float(d.pe_trailing[d.pe_trailing.index >= cutoff].mean())
    if m.get("pe") and m.get("DGS10") is not None:
        m["erp"] = 100 / m["pe"] - m["DGS10"]  # earnings yield - 10a

    # Breadth
    m["breadth"] = d.breadth_pct_above_200

    # IA
    sox = _col(p, "^SOX")
    if len(sox):
        m["sox_dd"] = float(100 * (sox.iloc[-1] / sox.cummax().iloc[-1] - 1))
    basket = []
    for t, name in config.AI_BASKET.items():
        s = _col(p, t)
        if len(s) < 2:
            continue
        basket.append({
            "ticker": t, "name": name, "price": float(s.iloc[-1]),
            "d1": _pct(s, 1), "d5": _pct(s, 5),
            "dd": float(100 * (s.iloc[-1] / s.cummax().iloc[-1] - 1)),
        })
    m["ai_basket"] = basket

    # Macro
    m["wti"] = _last(_col(f, "DCOILWTICO"))
    m["dxy"] = _last(_col(p, "DX-Y.NYB"))
    m["claims"] = _last(_col(f, "ICSA"))
    return m


def compute_signals(m: dict) -> list[Signal]:
    T = config.THRESHOLDS

    def fmt(x, nd=1, suf=""):
        return "sin dato" if x is None else f"{x:.{nd}f}{suf}"

    vix_panic = None
    if m.get("vix") is not None:
        vix_panic = m["vix"] > T["vix_panic"] or (m.get("vix_term") or 0) > T["vix_term_panic"]
    pe_ok = None
    if m.get("pe") and m.get("pe_10y_avg"):
        pe_ok = m["pe"] - m["pe_10y_avg"] < T["pe_vs_10y_avg"]

    def lt(x, thr):
        return None if x is None else x <= thr

    return [
        Signal("drawdown", "Drawdown", f"S&P {fmt(m.get('spx_dd'), 1, '%')} (umbral {T['drawdown_pct']}%)",
               lt(m.get("spx_dd"), T["drawdown_pct"])),
        Signal("panic", "Pánico", f"VIX {fmt(m.get('vix'))}, VIX/VIX3M {fmt(m.get('vix_term'), 2)}", vix_panic),
        Signal("panic_fading", "Pánico cediendo",
               f"VIX {fmt(m.get('vix_off_peak'), 0, '%')} vs máx 30d (umbral {T['vix_off_peak_pct']:.0f}%)",
               lt(m.get("vix_off_peak"), T["vix_off_peak_pct"]) if (m.get("vix_30d_max") or 0) >= 25 else
               (None if m.get("vix") is None else False)),
        Signal("washout", "Washout breadth", f"{fmt(m.get('breadth'), 0, '%')} sobre MA200 (umbral {T['breadth_washout']:.0f}%)",
               lt(m.get("breadth"), T["breadth_washout"])),
        Signal("credit", "Crédito estable",
               f"HY {fmt(m.get('hy_bp'), 0, ' pb')} ({fmt(m.get('hy_20d_bp'), 0, ' pb')} en 20d)", m.get("hy_stable")),
        Signal("valuation", "Valoración", f"P/E {fmt(m.get('pe'))} vs prom. 10a {fmt(m.get('pe_10y_avg'))}", pe_ok),
        Signal("fed", "Fed hacia recortes", f"2a − fed funds = {fmt(m.get('fed_bias'), 2, ' pp')}",
               None if m.get("fed_bias") is None else m["fed_bias"] < T["fed_cut_bias"]),
    ]


def score(signals: list[Signal]) -> tuple[int, int]:
    return sum(1 for s in signals if s.met), sum(1 for s in signals if s.met is not None)


def score_label(pts: int) -> tuple[str, str]:
    if pts >= 5:
        return "verde", "Varias señales de fondo alineadas: se parece a buenos momentos de entrada del pasado"
    if pts >= 3:
        return "amarillo", "Señales mixtas: zona para entrar de forma gradual"
    return "rojo", "Pocas señales de fondo: todavía no hay una venta por pánico (capitulación)"


def tranche_status(m: dict, pts: int, today: pd.Timestamp | None = None) -> list[dict]:
    today = today or pd.Timestamp.today()
    deadline = pd.Timestamp(config.TRANCHE_DEADLINE)
    out = []
    for t in config.TRANCHES:
        reasons = []
        if m.get("spx_dd") is not None and m["spx_dd"] <= t["drawdown_pct"]:
            reasons.append(f"drawdown ≤ {t['drawdown_pct']:.0f}%")
        if t["score_min"] is not None and pts >= t["score_min"]:
            reasons.append(f"semáforo ≥ {t['score_min']}")
        if today >= deadline:
            reasons.append("fecha límite")
        out.append({**t, "active": bool(reasons), "reasons": reasons})
    return out


def is_number(x) -> bool:
    return isinstance(x, (int, float, np.floating)) and not pd.isna(x)
