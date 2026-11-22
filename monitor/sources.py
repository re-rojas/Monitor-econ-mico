"""Descarga de datos. Cada fuente falla de forma aislada: si una cae, el
reporte se genera igual y marca ese dato como 'sin dato'."""

from __future__ import annotations

import io
import logging
import time
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import requests

from . import config

log = logging.getLogger(__name__)
UA = {"User-Agent": "Mozilla/5.0 (monitor-sp500)"}


@dataclass
class MarketData:
    fred: pd.DataFrame = field(default_factory=pd.DataFrame)      # columnas = series FRED
    prices: pd.DataFrame = field(default_factory=pd.DataFrame)    # cierres, columnas = tickers
    spx_full: pd.Series = field(default_factory=pd.Series)        # S&P 500 historia completa
    breadth_pct_above_200: float | None = None
    pe_trailing: pd.Series = field(default_factory=pd.Series)     # mensual
    cape: pd.Series = field(default_factory=pd.Series)            # mensual
    errors: list[str] = field(default_factory=list)


def _get(url: str, tries: int = 3, timeout: int = 30) -> requests.Response:
    last = None
    for i in range(tries):
        try:
            r = requests.get(url, headers=UA, timeout=timeout)
            r.raise_for_status()
            return r
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2 ** i)
    raise last  # type: ignore[misc]


def fetch_fred(series: dict[str, str], start: str) -> tuple[pd.DataFrame, list[str]]:
    frames, errors = [], []
    for sid in series:
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}&cosd={start}"
        try:
            df = pd.read_csv(io.StringIO(_get(url).text))
            df.columns = ["date", sid]
            df["date"] = pd.to_datetime(df["date"])
            df[sid] = pd.to_numeric(df[sid], errors="coerce")  # FRED usa "." para vacíos
            frames.append(df.set_index("date"))
        except Exception as e:  # noqa: BLE001
            errors.append(f"FRED {sid}: {e}")
    fred = pd.concat(frames, axis=1).sort_index() if frames else pd.DataFrame()
    return fred, errors


def fetch_prices(tickers: list[str], period: str) -> tuple[pd.DataFrame, list[str]]:
    import yfinance as yf

    try:
        raw = yf.download(tickers, period=period, auto_adjust=True, progress=False, threads=True)
        close = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw[["Close"]]
        if not isinstance(raw.columns, pd.MultiIndex):
            close.columns = tickers[:1]
        missing = [t for t in tickers if t not in close.columns or close[t].dropna().empty]
        return close, [f"yfinance sin datos: {', '.join(missing)}"] if missing else []
    except Exception as e:  # noqa: BLE001
        return pd.DataFrame(), [f"yfinance: {e}"]


def fetch_spx_full() -> tuple[pd.Series, list[str]]:
    import yfinance as yf

    try:
        s = yf.Ticker("^GSPC").history(period="max", auto_adjust=True)["Close"]
        s.index = s.index.tz_localize(None)
        return s, []
    except Exception as e:  # noqa: BLE001
        return pd.Series(dtype=float), [f"S&P 500 historia: {e}"]


def fetch_breadth() -> tuple[float | None, list[str]]:
    """% de componentes del S&P 500 sobre su media móvil de 200 días."""
    import yfinance as yf

    try:
        html = _get("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies").text
        tickers = pd.read_html(io.StringIO(html))[0]["Symbol"].str.replace(".", "-", regex=False).tolist()
        raw = yf.download(tickers, period="1y", auto_adjust=True, progress=False, threads=True)["Close"]
        valid = raw.dropna(axis=1, thresh=200)
        above = (valid.iloc[-1] > valid.rolling(200).mean().iloc[-1]).sum()
        return round(100 * above / valid.shape[1], 1), []
    except Exception as e:  # noqa: BLE001
        return None, [f"breadth: {e}"]


def _multpl(path: str) -> pd.Series:
    html = _get(f"https://www.multpl.com/{path}/table/by-month").text
    df = pd.read_html(io.StringIO(html))[0]
    df.columns = ["date", "value"]
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["value"] = pd.to_numeric(df["value"].astype(str).str.extract(r"([\d.]+)")[0], errors="coerce")
    return df.dropna().set_index("date")["value"].sort_index()


def fetch_valuation() -> tuple[pd.Series, pd.Series, list[str]]:
    errors, pe, cape = [], pd.Series(dtype=float), pd.Series(dtype=float)
    try:
        pe = _multpl("s-p-500-pe-ratio")
    except Exception as e:  # noqa: BLE001
        errors.append(f"P/E multpl: {e}")
    try:
        cape = _multpl("shiller-pe")
    except Exception as e:  # noqa: BLE001
        errors.append(f"CAPE multpl: {e}")
    return pe, cape, errors


def fetch_all() -> MarketData:
    d = MarketData()
    start = (pd.Timestamp.today() - pd.DateOffset(years=max(config.CHART_YEARS, 11))).strftime("%Y-%m-%d")
    d.fred, e1 = fetch_fred(config.FRED_SERIES, start)
    tickers = list(config.INDEX_TICKERS) + list(config.AI_BASKET)
    d.prices, e2 = fetch_prices(tickers, f"{config.CHART_YEARS}y")
    d.spx_full, e3 = fetch_spx_full()
    e4: list[str] = []
    if config.COMPUTE_BREADTH:
        d.breadth_pct_above_200, e4 = fetch_breadth()
    d.pe_trailing, d.cape, e5 = fetch_valuation()
    d.errors = e1 + e2 + e3 + e4 + e5
    for err in d.errors:
        log.warning(err)
    return d


# ---------------------------------------------------------------------------
# Datos sintéticos para probar el pipeline sin red (python -m monitor --demo)
# ---------------------------------------------------------------------------
def demo_data(seed: int = 7) -> MarketData:
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=252 * 11)

    def walk(start, vol, drift=0.0003):
        return pd.Series(start * np.exp(np.cumsum(rng.normal(drift, vol, len(idx)))), index=idx)

    spx = walk(2100, 0.01)
    spx.iloc[-35:] *= np.linspace(1, 0.88, 35)  # corrección reciente
    prices = pd.DataFrame({t: walk(100, 0.02) for t in list(config.INDEX_TICKERS) + list(config.AI_BASKET)})
    prices["^GSPC"] = spx
    prices["^VIX"] = (16 + 4 * rng.standard_normal(len(idx)).cumsum() * 0.05).clip(11, 80)
    prices.iloc[-20:, prices.columns.get_loc("^VIX")] = np.linspace(18, 32, 20)
    prices["^VIX3M"] = prices["^VIX"].rolling(20, min_periods=1).mean() + 1.5
    prices["SPY"] = spx / 10
    fred = pd.DataFrame(index=idx)
    fred["DGS10"] = 4.0 + rng.normal(0, 0.03, len(idx)).cumsum() * 0.1 + 0.9
    fred["DGS2"] = fred["DGS10"] - 0.3
    fred["DGS3MO"] = 4.05
    fred["DFII10"] = fred["DGS10"] - 2.4
    fred["T10Y2Y"] = fred["DGS10"] - fred["DGS2"]
    fred["T10Y3M"] = fred["DGS10"] - fred["DGS3MO"]
    fred["BAMLH0A0HYM2"] = 3.2 + np.abs(rng.normal(0, 0.05, len(idx)).cumsum()) * 0.2
    fred["BAMLC0A0CM"] = 0.9 + fred["BAMLH0A0HYM2"] * 0.1
    fred["DFEDTARU"], fred["DFEDTARL"] = 4.0, 3.75
    fred["VIXCLS"] = prices["^VIX"]
    fred["DCOILWTICO"] = 82.0
    fred["ICSA"] = 230000.0
    months = pd.date_range(end=idx[-1], periods=130, freq="MS")
    return MarketData(
        fred=fred,
        prices=prices.iloc[-252 * config.CHART_YEARS:],
        spx_full=spx,
        breadth_pct_above_200=31.5,
        pe_trailing=pd.Series(np.linspace(22, 27, len(months)), index=months),
        cape=pd.Series(np.linspace(30, 37, len(months)), index=months),
        errors=["DEMO: datos sintéticos, no reales"],
    )
