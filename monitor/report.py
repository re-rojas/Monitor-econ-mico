"""Genera el dashboard HTML estático (site/index.html)."""

from __future__ import annotations

import html
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

from . import config
from .analysis import Signal

S1, S2 = "#2a78d6", "#eb6834"          # serie 1 y 2 (paleta categórica validada)
REF = "#8a8984"                         # líneas de referencia
GRID = "#ecebe8"
STATUS = {"verde": "#0ca30c", "amarillo": "#fab219", "rojo": "#d03b3b"}
ICON = {True: "●", False: "○", None: "–"}


def _fmt(x, nd=1, suf="", sign=False):
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return "—"
    return f"{x:+.{nd}f}{suf}" if sign else f"{x:,.{nd}f}{suf}"


def _fig(title: str, unit: str) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        title=dict(text=title, x=0, font=dict(size=15, color="#0b0b0b")),
        template="plotly_white", height=300, margin=dict(l=48, r=16, t=48, b=32),
        hovermode="x unified", paper_bgcolor="#fcfcfb", plot_bgcolor="#fcfcfb",
        font=dict(family="system-ui, -apple-system, Segoe UI, sans-serif", size=12, color="#52514e"),
        legend=dict(orientation="h", y=1.12, x=1, xanchor="right"),
        yaxis=dict(ticksuffix=unit, gridcolor=GRID, zeroline=False),
        xaxis=dict(gridcolor=GRID, showspikes=True, spikemode="across", spikethickness=1, spikecolor=REF),
    )
    return fig


def _line(fig, s: pd.Series, name: str, color: str, fmt: str):
    s = s.dropna()
    fig.add_trace(go.Scatter(x=s.index, y=s.values, name=name, mode="lines",
                             line=dict(color=color, width=2), hovertemplate=f"%{{y:{fmt}}}"))


def _ref(fig, y: float, label: str):
    fig.add_hline(y=y, line=dict(color=REF, width=1, dash="dot"),
                  annotation_text=label, annotation_position="top left",
                  annotation_font=dict(size=11, color=REF))


def _window(s: pd.Series) -> pd.Series:
    if s.empty:
        return s
    return s[s.index >= s.index[-1] - pd.DateOffset(years=config.CHART_YEARS)]


def build_charts(d, m) -> list[str]:
    f, p = d.fred, d.prices
    figs = []

    if "spx_dd_series" in m:
        fig = _fig("S&P 500: caída desde máximo histórico", "%")
        _line(fig, _window(m["spx_dd_series"]), "Drawdown", S1, ".1f")
        _ref(fig, -10, "Corrección −10%")
        _ref(fig, -20, "Mercado bajista −20%")
        fig.update_layout(showlegend=False)
        figs.append(fig)

    spx = _window(d.spx_full if len(d.spx_full) else p.get("^GSPC", pd.Series(dtype=float)))
    if len(spx):
        fig = _fig("S&P 500 y media móvil de 200 días", "")
        full = d.spx_full if len(d.spx_full) else spx
        _line(fig, spx, "S&P 500", S1, ",.0f")
        _line(fig, _window(full.rolling(200).mean()), "Media 200 días", S2, ",.0f")
        figs.append(fig)

    vix = p["^VIX"] if "^VIX" in p else f.get("VIXCLS", pd.Series(dtype=float))
    if len(vix.dropna()):
        fig = _fig("VIX (volatilidad implícita)", "")
        _line(fig, _window(vix), "VIX", S1, ".1f")
        _ref(fig, 20, "20 incertidumbre")
        _ref(fig, 30, "30 estrés")
        fig.update_layout(showlegend=False)
        figs.append(fig)

    if "BAMLH0A0HYM2" in f:
        fig = _fig("Spreads de crédito (OAS)", " pb")
        _line(fig, _window(f["BAMLH0A0HYM2"] * 100), "High Yield", S1, ".0f")
        if "BAMLC0A0CM" in f:
            _line(fig, _window(f["BAMLC0A0CM"] * 100), "Investment Grade", S2, ".0f")
        _ref(fig, 500, "HY 500 pb estrés")
        figs.append(fig)

    if "DGS10" in f:
        fig = _fig("Rendimiento de los Treasuries", "%")
        _line(fig, _window(f["DGS10"]), "10 años", S1, ".2f")
        if "DGS2" in f:
            _line(fig, _window(f["DGS2"]), "2 años", S2, ".2f")
        figs.append(fig)

    if "T10Y2Y" in f:
        fig = _fig("Curva de tasas", " pp")
        _line(fig, _window(f["T10Y2Y"]), "10a − 2a", S1, ".2f")
        if "T10Y3M" in f:
            _line(fig, _window(f["T10Y3M"]), "10a − 3m", S2, ".2f")
        _ref(fig, 0, "Inversión")
        figs.append(fig)

    if "rsp_spy_ratio" in m:
        r = m["rsp_spy_ratio"]
        fig = _fig("Amplitud: Equal Weight vs S&P 500 (RSP/SPY, base 100)", "")
        _line(fig, 100 * r / r.dropna().iloc[0], "RSP/SPY", S1, ".1f")
        fig.update_layout(showlegend=False)
        figs.append(fig)

    if "^SOX" in p:
        sox = p["^SOX"].dropna()
        if len(sox):
            fig = _fig("Semiconductores (SOX): caída desde máximo", "%")
            _line(fig, 100 * (sox / sox.cummax() - 1), "SOX", S1, ".1f")
            _ref(fig, -20, "−20%")
            fig.update_layout(showlegend=False)
            figs.append(fig)

    out = []
    for i, fig in enumerate(figs):
        out.append(fig.to_html(full_html=False, include_plotlyjs=False,
                               config={"displayModeBar": False, "responsive": True}, div_id=f"c{i}"))
    return out


def _tile(label, value, sub=""):
    return (f'<div class="tile"><div class="tl">{html.escape(label)}</div>'
            f'<div class="tv">{value}</div><div class="ts">{sub}</div></div>')


def render(d, m, signals: list[Signal], pts: int, n_avail: int, level: str, level_text: str,
           tranches: list[dict], generated: str, out_dir: Path) -> Path:
    tiles = "".join([
        _tile("S&P 500", _fmt(m.get("spx"), 0), f"{_fmt(m.get('spx_1d'), 2, '%', True)} hoy · {_fmt(m.get('spx_5d'), 1, '%', True)} 5d"),
        _tile("Caída desde máximo", _fmt(m.get("spx_dd"), 1, "%"), f"máx. {_fmt(m.get('spx_ath'), 0)} ({m.get('spx_ath_date', '—')})"),
        _tile("vs media 200d", _fmt(m.get("spx_vs_ma200"), 1, "%", True), f"RSI(14) {_fmt(m.get('spx_rsi'), 0)}"),
        _tile("VIX", _fmt(m.get("vix"), 1), f"VIX/VIX3M {_fmt(m.get('vix_term'), 2)}"),
        _tile("Spread High Yield", _fmt(m.get("hy_bp"), 0, " pb"), f"{_fmt(m.get('hy_20d_bp'), 0, ' pb', True)} en 20d · IG {_fmt(m.get('ig_bp'), 0, ' pb')}"),
        _tile("Treasury 10a", _fmt(m.get("DGS10"), 2, "%"), f"real {_fmt(m.get('DFII10'), 2, '%')} · {_fmt(m.get('DGS10_20d'), 2, ' pp', True)} 20d"),
        _tile("Curva 10a−2a", _fmt(m.get("T10Y2Y"), 2, " pp"), f"10a−3m {_fmt(m.get('T10Y3M'), 2, ' pp')}"),
        _tile("Fed funds", m.get("fed_range", "—"), f"2a − fed = {_fmt(m.get('fed_bias'), 2, ' pp', True)}"),
        _tile("P/E · CAPE", f"{_fmt(m.get('pe'), 1)} · {_fmt(m.get('cape'), 1)}", f"prom. P/E 10a {_fmt(m.get('pe_10y_avg'), 1)}"),
        _tile("Prima de riesgo (ERP)", _fmt(m.get("erp"), 2, " pp"), "rent. utilidades − 10a"),
        _tile("Breadth", _fmt(m.get("breadth"), 0, "%"), "acciones sobre su MA200"),
        _tile("Nasdaq-100 · SOX", f"{_fmt(m.get('ndx_dd'), 1, '%')} · {_fmt(m.get('sox_dd'), 1, '%')}", "caída desde máximo (3a)"),
        _tile("WTI · DXY", f"{_fmt(m.get('wti'), 1)} · {_fmt(m.get('dxy'), 1)}", f"desempleo semanal {_fmt(m.get('claims'), 0)}"),
    ])

    sig_rows = "".join(
        f'<li class="{"on" if s.met else "off" if s.met is False else "na"}">'
        f'<span class="ic">{ICON[s.met]}</span><b>{html.escape(s.label)}</b>'
        f'<span class="st">{"Cumple" if s.met else "No cumple" if s.met is False else "Sin dato"}</span>'
        f'<span class="dt">{html.escape(s.detail)}</span></li>' for s in signals)

    tr_rows = "".join(
        f"<tr><td>{t['name']}</td><td>{t['fraction']:.0%}</td>"
        f"<td>drawdown ≤ {t['drawdown_pct']:.0f}%" + (f" o semáforo ≥ {t['score_min']}" if t['score_min'] else "") +
        f"</td><td>{'✅ Activo: ' + ', '.join(t['reasons']) if t['active'] else '⏳ Esperando'}</td></tr>"
        for t in tranches)

    ai_rows = "".join(
        f"<tr><td>{a['ticker']}</td><td>{html.escape(a['name'])}</td><td class='n'>{_fmt(a['price'], 2)}</td>"
        f"<td class='n'>{_fmt(a['d1'], 1, '%', True)}</td><td class='n'>{_fmt(a['d5'], 1, '%', True)}</td>"
        f"<td class='n'>{_fmt(a['dd'], 1, '%')}</td></tr>"
        for a in sorted(m.get("ai_basket", []), key=lambda a: a["dd"]))

    errors = "".join(f"<li>{html.escape(e)}</li>" for e in d.errors)
    charts = "".join(f'<div class="card">{c}</div>' for c in build_charts(d, m))
    color = STATUS[level]

    page = f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Monitor S&amp;P 500</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js" charset="utf-8"></script>
<style>
:root{{--bg:#f4f3f0;--surface:#fcfcfb;--t1:#0b0b0b;--t2:#52514e;--t3:#8a8984;--line:#e3e2de}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--t1);font:14px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif}}
main{{max-width:1200px;margin:0 auto;padding:24px 16px 48px}}
h1{{font-size:22px;margin:0}} h2{{font-size:16px;margin:28px 0 10px}}
.meta{{color:var(--t2);margin:4px 0 20px}}
.hero{{display:flex;gap:20px;align-items:center;background:var(--surface);border:1px solid var(--line);border-left:6px solid {color};border-radius:10px;padding:16px 20px}}
.score{{font-size:40px;font-weight:700}} .score small{{font-size:18px;color:var(--t2)}}
.lvl{{font-weight:600;text-transform:uppercase;letter-spacing:.04em}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:10px}}
.tile{{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:12px 14px}}
.tl{{color:var(--t2);font-size:12px}} .tv{{font-size:22px;font-weight:650;margin:2px 0}} .ts{{color:var(--t3);font-size:12px}}
ul.sig{{list-style:none;padding:0;margin:0;background:var(--surface);border:1px solid var(--line);border-radius:10px}}
ul.sig li{{display:grid;grid-template-columns:22px 170px 90px 1fr;gap:8px;padding:9px 14px;border-top:1px solid var(--line)}}
ul.sig li:first-child{{border-top:0}} .on .ic{{color:#0ca30c}} .off .ic{{color:var(--t3)}} .na .ic{{color:var(--t3)}}
.st{{color:var(--t2)}} .dt{{color:var(--t2)}}
.charts{{display:grid;grid-template-columns:repeat(auto-fill,minmax(520px,1fr));gap:12px}}
.card{{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:6px}}
table{{width:100%;border-collapse:collapse;background:var(--surface);border:1px solid var(--line);border-radius:10px;overflow:hidden}}
th,td{{padding:8px 12px;border-top:1px solid var(--line);text-align:left}} th{{color:var(--t2);font-weight:600;border-top:0}}
td.n,th.n{{text-align:right;font-variant-numeric:tabular-nums}}
.err{{color:var(--t2);font-size:12px}} footer{{color:var(--t3);font-size:12px;margin-top:32px}}
@media (max-width:600px){{.charts{{grid-template-columns:1fr}} ul.sig li{{grid-template-columns:22px 1fr;}} ul.sig .st,ul.sig .dt{{grid-column:2}}}}
</style></head><body><main>
<h1>Monitor S&amp;P 500</h1>
<div class="meta">Actualizado {generated} (hora de Chile) · datos de FRED, Yahoo Finance, multpl.com</div>

<div class="hero"><div class="score">{pts}<small>/{n_avail}</small></div>
<div><div class="lvl" style="color:{color}">● Semáforo {level}</div><div>{level_text}</div></div></div>

<h2>Indicadores clave</h2><div class="grid">{tiles}</div>

<h2>Señales de fondo</h2><ul class="sig">{sig_rows}</ul>

<h2>Plan por tramos (límite {config.TRANCHE_DEADLINE})</h2>
<table><tr><th>Tramo</th><th>Fracción</th><th>Condición</th><th>Estado</th></tr>{tr_rows}</table>

<h2>Gráficos</h2><div class="charts">{charts}</div>

<h2>Canasta IA (ordenada por caída desde máximo)</h2>
<table><tr><th>Ticker</th><th>Empresa</th><th class="n">Precio</th><th class="n">1d</th><th class="n">5d</th><th class="n">Desde máx.</th></tr>{ai_rows}</table>

{"<h2>Avisos de datos</h2><ul class='err'>" + errors + "</ul>" if errors else ""}
<footer>Material informativo, no asesoría financiera. Los umbrales son configurables en monitor/config.py.</footer>
</main></body></html>"""
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "index.html"
    path.write_text(page, encoding="utf-8")
    return path
