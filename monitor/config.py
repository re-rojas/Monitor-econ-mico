"""Configuración central del monitor. Edita aquí tickers, series y umbrales."""

# --- Series de FRED (descarga CSV pública, no requiere API key) ---
FRED_SERIES = {
    "DGS10": "Treasury 10 años (%)",
    "DGS2": "Treasury 2 años (%)",
    "DGS3MO": "Treasury 3 meses (%)",
    "DFII10": "Tasa real 10 años (TIPS, %)",
    "T10Y2Y": "Curva 10a - 2a (pp)",
    "T10Y3M": "Curva 10a - 3m (pp)",
    "BAMLH0A0HYM2": "Spread High Yield (OAS, %)",
    "BAMLC0A0CM": "Spread Investment Grade (OAS, %)",
    "DFEDTARU": "Fed funds, techo (%)",
    "DFEDTARL": "Fed funds, piso (%)",
    "VIXCLS": "VIX (cierre FRED)",
    "DCOILWTICO": "Petróleo WTI (US$)",
    "ICSA": "Solicitudes de desempleo (semanal)",
}

# --- Precios vía yfinance ---
INDEX_TICKERS = {
    "^GSPC": "S&P 500",
    "^NDX": "Nasdaq-100",
    "RSP": "S&P 500 Equal Weight (RSP)",
    "SPY": "SPY",
    "^VIX": "VIX",
    "^VIX3M": "VIX 3 meses",
    "^SOX": "Semiconductores (SOX)",
    "DX-Y.NYB": "Dólar (DXY)",
}

# Canasta IA: megacaps + deudores de IA más expuestos al crédito.
AI_BASKET = {
    "NVDA": "Nvidia",
    "MSFT": "Microsoft",
    "GOOGL": "Alphabet",
    "AMZN": "Amazon",
    "META": "Meta",
    "AAPL": "Apple",
    "AVGO": "Broadcom",
    "TSLA": "Tesla",
    "ORCL": "Oracle",
    "CRWV": "CoreWeave",
    "NBIS": "Nebius",
    "ANT": "Anthropic",
}

# Historia a descargar para gráficos (años). El máximo histórico del S&P se
# calcula con toda la historia disponible.
CHART_YEARS = 3

# Breadth: descarga las ~500 componentes del S&P 500 (lista de Wikipedia).
# Ponlo en False si yfinance empieza a fallar por rate limit.
COMPUTE_BREADTH = True

# --- Semáforo de entrada: umbrales (ajústalos tras un backtest) ---
THRESHOLDS = {
    "drawdown_pct": -15.0,       # S&P <= -15% desde máximo
    "vix_panic": 35.0,           # VIX > 35 ...
    "vix_term_panic": 1.0,       # ... o VIX/VIX3M > 1 (backwardation)
    "vix_off_peak_pct": -20.0,   # VIX bajó 20%+ desde su máximo de 30 días
    "breadth_washout": 20.0,     # < 20% de acciones sobre su media de 200 días
    "hy_stable_days": 5,         # spread HY sin subir en los últimos N datos
    "pe_vs_10y_avg": 0.0,        # P/E bajo su promedio de 10 años
    "fed_cut_bias": 0.0,         # 2a - fed funds medio < 0 => mercado espera recortes
}

# --- Estrategia E2: tramos por nivel con límite de tiempo ---
# Cada tramo se activa si se cumple CUALQUIERA de sus condiciones.
TRANCHES = [
    {"name": "Tramo 1", "fraction": 1 / 3, "drawdown_pct": -10.0, "score_min": None},
    {"name": "Tramo 2", "fraction": 1 / 3, "drawdown_pct": -20.0, "score_min": 4},
    {"name": "Tramo 3", "fraction": 1 / 3, "drawdown_pct": -25.0, "score_min": 6},
]
# Fecha límite: si no se activó un tramo antes de esto, se invierte igual.
TRANCHE_DEADLINE = "2027-05-22"

TIMEZONE = "America/Santiago"

# --- Pestaña "Histórico": activos para comparar (ticker de Yahoo Finance: nombre) ---
# Se descarga toda la historia disponible. Para que la página siga liviana, los
# datos más antiguos que HISTORY_DAILY_YEARS se guardan como cierre semanal.
HISTORY_ASSETS = {
    "Índices": {
        "^GSPC": "S&P 500", "^NDX": "Nasdaq-100", "^DJI": "Dow Jones", "^RUT": "Russell 2000",
        "^VIX": "VIX",
    },
    "Fondos y ETF": {
        "SPY": "SPY (S&P 500)", "QQQ": "QQQ (Nasdaq-100)", "TLT": "TLT (bonos del Tesoro 20+ años)",
        "GLD": "GLD (oro)", "EEM": "EEM (emergentes)", "ECH": "ECH (Chile)", "XLF": "XLF (financiero)",
    },
    "Materias primas": {"CL=F": "Petróleo WTI", "HG=F": "Cobre"},
    "Monedas": {
        "DX-Y.NYB": "Dólar (DXY)", "CLP=X": "Dólar / peso chileno", "EURUSD=X": "Euro / dólar",
        "JPY=X": "Dólar / yen", "BTC-USD": "Bitcoin",
    },
    "Acciones": {
        "AAPL": "Apple", "MSFT": "Microsoft", "NVDA": "Nvidia", "AMZN": "Amazon", "GOOGL": "Alphabet",
        "META": "Meta", "JPM": "JPMorgan",
    },
}
HISTORY_DAILY_YEARS = 10

# Episodios para la vista "Comparar crisis". La fecha es el máximo del S&P 500
# antes de cada caída; todos los activos se alinean en esa misma fecha.
HISTORY_EPISODES = [
    {"id": "1929", "name": "Crash de 1929", "start": "1929-09-16"},
    {"id": "1987", "name": "Lunes negro 1987", "start": "1987-08-25"},
    {"id": "2000", "name": "Burbuja .com", "start": "2000-03-24"},
    {"id": "2008", "name": "Crisis 2008", "start": "2007-10-09"},
    {"id": "2018", "name": "Fin de 2018", "start": "2018-09-20"},
    {"id": "2020", "name": "COVID 2020", "start": "2020-02-19"},
    {"id": "2022", "name": "Inflación 2022", "start": "2022-01-03"},
]
