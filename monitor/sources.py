"""Descarga de datos. Cada fuente falla de forma aislada: si una cae, el
reporte se genera igual y marca ese dato como 'sin dato'."""

from __future__ import annotations

import io
import logging
import os
import threading
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


# Límite duro (segundos) por fuente. Si una fuente se cuelga, se abandona y
# el reporte sigue con "sin dato". Total máximo aprox. = suma de estos valores.
SOURCE_TIMEOUTS = {"fred": 120, "prices": 120, "spx_full": 60, "breadth": 150, "valuation": 45}


def _get(url: str, tries: int = 2, timeout: tuple[int, int] = (5, 20)) -> requests.Response:
    """GET con timeout de conexión/lectura y reintentos cortos."""
    last = None
    for i in range(tries):
        try:
            r = requests.get(url, headers=UA, timeout=timeout)
            r.raise_for_status()
            return r
        except Exception as e:  # noqa: BLE001
            last = e
            if i < tries - 1:
                time.sleep(2)
    raise last  # type: ignore[misc]


def run_with_timeout(name: str, fn, default, seconds: int):
    """Ejecuta fn() en un hilo daemon; si excede `seconds`, devuelve default.
    yfinance no expone un timeout global fiable, así que esto es el seguro."""
    box: dict = {}

    def target():
        try:
            box["value"] = fn()
        except Exception as e:  # noqa: BLE001
            box["error"] = e

    t0 = time.monotonic()
    log.info("→ %s (límite %ss)", name, seconds)
    th = threading.Thread(target=target, daemon=True)
    th.start()
    th.join(seconds)
    took = time.monotonic() - t0
    if th.is_alive():
        log.warning("✗ %s: excedió %ss, se omite", name, seconds)
        return default[0], list(default[1]) + [f"{name}: tiempo agotado ({seconds}s)"]
    if "error" in box:
        log.warning("✗ %s: %s", name, box["error"])
        return default[0], list(default[1]) + [f"{name}: {box['error']}"]
    log.info("✓ %s en %.0fs", name, took)
    return box["value"]


def _fred_one(sid: str, start: str, key: str | None) -> pd.DataFrame:
    if key:  # API oficial: más estable desde servidores en la nube
        url = (f"https://api.stlouisfed.org/fred/series/observations?series_id={sid}"
               f"&observation_start={start}&file_type=json&api_key={key}")
        obs = _get(url).json()["observations"]
        df = pd.DataFrame(obs)[["date", "value"]]
    else:
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}&cosd={start}"
        df = pd.read_csv(io.StringIO(_get(url).text))
    df.columns = ["date", sid]
    df["date"] = pd.to_datetime(df["date"])
    df[sid] = pd.to_numeric(df[sid], errors="coerce")  # FRED usa "." para vacíos
    return df.set_index("date")


def fetch_fred(series: dict[str, str], start: str) -> tuple[pd.DataFrame, list[str]]:
    key = os.getenv("FRED_API_KEY") or None
    frames, errors = [], []
    for i, sid in enumerate(series):
        try:
            frames.append(_fred_one(sid, start, key))
        except Exception as e:  # noqa: BLE001
            errors.append(f"FRED {sid}: {e}")
            if i == 1 and not frames:  # las dos primeras fallaron: FRED no responde
                errors.append("FRED: se omiten las demás series (sin respuesta)")
                break
    fred = pd.concat(frames, axis=1).sort_index() if frames else pd.DataFrame()
    return fred, errors


def fetch_prices(tickers: list[str], period: str) -> tuple[pd.DataFrame, list[str]]:
    import yfinance as yf

    try:
        raw = yf.download(tickers, period=period, auto_adjust=True, progress=False, threads=True, timeout=20)
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
        s = yf.Ticker("^GSPC").history(period="max", auto_adjust=True, timeout=20)["Close"]
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
        raw = yf.download(tickers, period="1y", auto_adjust=True, progress=False, threads=True,
                          timeout=20)["Close"]
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
    T = SOURCE_TIMEOUTS
    start = (pd.Timestamp.today() - pd.DateOffset(years=max(config.CHART_YEARS, 11))).strftime("%Y-%m-%d")
    d.fred, e1 = run_with_timeout("FRED", lambda: fetch_fred(config.FRED_SERIES, start),
                                  (pd.DataFrame(), []), T["fred"])
    tickers = list(config.INDEX_TICKERS) + list(config.AI_BASKET)
    d.prices, e2 = run_with_timeout("Precios yfinance", lambda: fetch_prices(tickers, f"{config.CHART_YEARS}y"),
                                    (pd.DataFrame(), []), T["prices"])
    d.spx_full, e3 = run_with_timeout("S&P 500 historia", fetch_spx_full,
                                      (pd.Series(dtype=float), []), T["spx_full"])
    e4: list[str] = []
    if config.COMPUTE_BREADTH:
        d.breadth_pct_above_200, e4 = run_with_timeout("Breadth", fetch_breadth, (None, []), T["breadth"])

    def _val():
        pe, cape, errs = fetch_valuation()
        return (pe, cape), errs

    (d.pe_trailing, d.cape), e5 = run_with_timeout(
        "Valoración multpl", _val, ((pd.Series(dtype=float), pd.Series(dtype=float)), []), T["valuation"])
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
