# Monitor S&P 500

Monitor diario de indicadores para decidir cuándo entrar al S&P 500. Corre en GitHub Actions dos veces por día hábil (12:30 y 18:30, hora de Chile), publica un dashboard en GitHub Pages y envía un resumen por Telegram.

> Material informativo, no asesoría financiera.

## Qué muestra

- **Semáforo de entrada** (0 a 7 puntos): drawdown, pánico en VIX, pánico cediendo, washout de breadth, crédito estable, valoración y Fed hacia recortes.
- **Indicadores clave**: S&P 500, caída desde máximo, media de 200 días, RSI, VIX y VIX/VIX3M, spreads High Yield e Investment Grade, Treasuries 10a/2a y tasa real, curva 10a−2a y 10a−3m, Fed funds, P/E, CAPE, prima de riesgo, breadth, Nasdaq-100, SOX, WTI, dólar, solicitudes de desempleo.
- **Plan por tramos** (estrategia E2): qué tramos están activos según drawdown, semáforo o fecha límite.
- **Gráficos** de 3 años y **canasta IA** (NVDA, MSFT, GOOGL, AMZN, META, AAPL, AVGO, TSLA, ORCL, CRWV, NBIS, ANT).
- **Pestaña Histórico** (`historico.html`): compara índices, fondos, monedas y acciones por período o en crisis pasadas (1929, 1987, 2000, 2008, 2018, 2020, 2022) contra hoy. Activos y episodios en `HISTORY_ASSETS` y `HISTORY_EPISODES` de `config.py`.
- **Histórico** de cada corrida en `data/history.csv`, para analizar o hacer backtest después.

## Fuentes

| Fuente | Datos | Key |
|---|---|---|
| FRED (CSV público) | Tasas, curva, spreads de crédito, Fed funds, VIX, WTI, desempleo | No |
| Yahoo Finance (`yfinance`) | Índices, ETFs, acciones, componentes del S&P 500 | No |
| Wikipedia | Lista de componentes del S&P 500 (para breadth) | No |
| multpl.com | P/E trailing y CAPE mensual | No |

Si una fuente falla o se cuelga, el dashboard se genera igual y la lista "Avisos de datos" indica qué faltó. Cada fuente tiene un límite de tiempo (`SOURCE_TIMEOUTS` en `monitor/sources.py`) y el job de GitHub se corta a los 15 minutos.

## Uso local (Windows, PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

python -m monitor --demo --no-notify   # datos sintéticos, para ver el diseño
python -m monitor --no-notify          # datos reales, sin Telegram
start site\index.html
```

Para probar Telegram en local:

```powershell
$env:TELEGRAM_BOT_TOKEN="..."; $env:TELEGRAM_CHAT_ID="..."
python -m monitor
```

## Puesta en marcha en GitHub

1. Mueve `setup/monitor.yml` a `.github/workflows/monitor.yml` (no pude crear la carpeta `.github` desde aquí). En PowerShell:
   `mkdir .github\workflows; move setup\monitor.yml .github\workflows\`
2. Crea un repo (puede ser público) y sube esta carpeta.
3. **Settings → Pages → Build and deployment → Source: GitHub Actions.**
4. **Telegram** (opcional, recomendado):
   - En Telegram habla con `@BotFather`, usa `/newbot` y copia el token.
   - Escríbele cualquier mensaje a tu bot y abre `https://api.telegram.org/bot<TOKEN>/getUpdates` para ver tu `chat.id`.
   - En el repo: **Settings → Secrets and variables → Actions** y crea `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID`.
5. **FRED API key** (gratis, recomendado en GitHub Actions): pídela en https://fred.stlouisfed.org/docs/api/api_key.html y créala como secret `FRED_API_KEY`. Sin key se usa la descarga CSV pública, que desde servidores en la nube puede ser lenta.
6. **Actions → Monitor S&P 500 → Run workflow** para la primera corrida. Después corre solo.

El dashboard queda en `https://<tu-usuario>.github.io/<repo>/`.

## Ajustes

Todo lo configurable está en [`monitor/config.py`](monitor/config.py): tickers, series de FRED, umbrales del semáforo, tramos y fecha límite.

Los horarios del cron están en UTC en [`.github/workflows/monitor.yml`](.github/workflows/monitor.yml). Revísalos cuando cambie el horario de verano en Chile o EE.UU.

## Estructura

```
monitor/
  config.py     tickers, series, umbrales, tramos
  sources.py    descarga (FRED, yfinance, Wikipedia, multpl) + datos demo
  analysis.py   métricas, semáforo y tramos
  report.py     dashboard HTML (Plotly)
  assets/       estilos (dashboard.css), JS y fuentes (Figtree + Noto Sans, licencia OFL)
                que se incrustan en site/index.html; plotly.js se copia a site/assets/
  history.py    datos compactos de la pestaña Histórico (site/assets/historico-data.js)
  glossary.py   explicaciones en lenguaje simple de cada indicador (botones ⓘ)
  notify.py     mensaje de Telegram
  __main__.py   orquestación e histórico
data/history.csv  una fila por corrida
docs/PLAN.md      todas las alternativas evaluadas y el plan de página web
```
