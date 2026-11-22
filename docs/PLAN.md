# Plan y alternativas

Registro de las decisiones del proyecto y de las opciones que quedaron para más adelante. El plan completo con el contexto de mercado de noviembre de 2026 está en el doc "Plan: Monitor diario del S&P 500".

> Material informativo, no asesoría financiera.

## Decisiones tomadas (22 nov 2026)

| Tema | Decisión |
|---|---|
| Entregable | A1 + A2: GitHub Actions 2 veces al día → dashboard estático en GitHub Pages + resumen por Telegram |
| Horario | 12:30 y 18:30 hora de Chile, lunes a viernes |
| Repo | Público (también hay GitHub Pro vía licencia de estudiante, pero puede vencer) |
| Indicadores | Track B completo: 7 paneles + semáforo |
| Estrategia | E2: tramos por nivel con fecha límite |

## Track A: todas las opciones de entregable

| Opción | Qué es | A favor | En contra | Costo |
|---|---|---|---|---|
| **A1. Dashboard estático + cron** (elegida) | Python en GitHub Actions genera HTML y lo publica en GitHub Pages | Gratis, sin servidor, histórico versionado | Snapshots, no tiempo real | $0 |
| **A2. Reporte push** (elegida) | Resumen por Telegram o email | Llega solo; ideal para el semáforo | Poco interactivo | $0 |
| A3. App Streamlit / Dash | App interactiva en Streamlit Community Cloud | Filtros, zoom, rápida de iterar | Se duerme sin uso; rate limits de yfinance | $0 |
| A4. Local en Windows | Programador de tareas + HTML en OneDrive | Sin cuentas, privado | Depende del PC encendido | $0 |
| A5. Google Sheets | GOOGLEFINANCE + Apps Script | Casi sin código | Sin spreads ni breadth | $0 |

### Alternativas dentro de A1/A2

- **Hosting privado gratis** si el repo deja de ser público o vence GitHub Pro: Cloudflare Pages o Netlify (conectan al repo y despliegan `site/`).
- **Email en vez de Telegram**: SMTP de Gmail con contraseña de aplicación, o Resend (plan gratis).
- **Frontend**: hoy es HTML generado desde Python con Plotly. Alternativa: frontend propio (React/Vite) que lea un `data.json` generado por el pipeline.

## Plan futuro: página web propia

Objetivo: pasar del dashboard estático a un sitio con dominio propio, sin rehacer el pipeline. El histórico en `data/history.csv` y el cálculo en `monitor/` se reutilizan tal cual.

### Fase 1: dominio propio sobre lo que ya existe (bajo esfuerzo)
- Comprar un dominio (~US$10–15/año en Cloudflare Registrar, Namecheap o Porkbun; un `.cl` en NIC Chile cuesta parecido).
- Apuntarlo a GitHub Pages (Settings → Pages → Custom domain) o a Cloudflare Pages. HTTPS gratis.
- Sin costo de hosting.

### Fase 2: separar datos y presentación
- El pipeline exporta `data.json` (métricas, señales, series) además del HTML.
- Frontend en React/Vite, Astro o SvelteKit que lea ese JSON: selector de rango de fechas, comparar indicadores, ver el histórico del semáforo, modo oscuro.
- Sigue siendo estático: Cloudflare Pages, Netlify o Vercel en plan gratis.

### Fase 3: backend y datos en vivo (si hace falta)
- API (FastAPI) + base de datos (Postgres en Supabase/Neon, plan gratis) para guardar series y consultas a demanda.
- Hosting: Fly.io, Railway o Render (desde ~US$5/mes), o un VPS (Hetzner ~€4/mes).
- Precios intradía requieren un proveedor con API estable (Polygon, Tiingo, Twelve Data; planes de ~US$10–30/mes), porque yfinance no es oficial.
- Alertas configurables, login, varios usuarios.

**Recomendación:** hacer la Fase 1 cuando quieras el dominio y la Fase 2 solo si echas de menos interactividad. La Fase 3 tiene sentido si necesitas datos intradía o compartirlo con más gente.

## Track B: indicadores y su porqué

| Panel | Métricas | Por qué importa |
|---|---|---|
| B1. Precio | Drawdown desde máximo, MA50/MA200, RSI, Nasdaq-100, RSP | Dónde estamos en la caída; −10% corrección, −20% bajista |
| B2. Crédito | Spread HY e IG (OAS), proxies ORCL/CRWV/NBIS | Si el problema es la deuda de IA, aparece aquí primero. HY <350 pb calma, 500+ estrés, 700+ crisis |
| B3. Tasas y Fed | 10a, 2a, real 10a, curva, Fed funds, 2a − Fed, ERP | Con el 10a cerca de 5% la prima de riesgo es baja; el 2a anticipa a la Fed |
| B4. Volatilidad | VIX, VIX/VIX3M | Los fondos suelen formarse cuando el VIX hace pico y empieza a ceder |
| B5. Valoración | P/E, CAPE vs promedio 10a | Cuánto margen de caída queda, no sirve para timing de corto plazo |
| B6. Breadth | % sobre MA200, RSP/SPY | Un washout (<20%) suele acompañar fondos |
| B7. IA | SOX, canasta de 12 acciones | Epicentro de la corrección actual |

### Pendiente para una segunda iteración
- Backtest de los umbrales del semáforo con el histórico de FRED y yfinance.
- Put/call ratio (CBOE), sentimiento AAII, Fear & Greed (fuentes no oficiales).
- Trayectoria implícita de la Fed (FedWatch no tiene API gratis).
- Capex trimestral de hyperscalers (carga manual tras cada earnings).
- P/E forward (requiere fuente de estimaciones; FMP tiene plan gratis limitado).

## Estrategias de entrada evaluadas

| Estrategia | Cómo | Riesgo |
|---|---|---|
| E1. Todo con señal | Esperar a que el semáforo llegue a X | Puede no llegar nunca |
| **E2. Tramos + límite de tiempo** (elegida) | 1/3 a −10%, 1/3 a −20% o semáforo ≥4, 1/3 a −25% o semáforo ≥6; lo que no se active se invierte en la fecha límite | Si sigue cayendo, el primer tramo pierde, pero se promedia abajo |
| E3. DCA fijo | Mismo monto cada mes por 6–12 meses | Ignora la información del monitor |

Los tramos y la fecha límite (22 may 2027, seis meses) se editan en `monitor/config.py`.
