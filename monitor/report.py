"""Genera el dashboard HTML estático (site/index.html).

El HTML es autocontenido salvo Plotly, que se copia desde el paquete de Python
instalado a site/assets/ (así la versión de plotly.js siempre calza con la del
paquete y no se depende de un CDN). Estilos, fuentes y JS viven en
monitor/assets/ y se incrustan en la página al generarla.
"""

from __future__ import annotations

import base64
import html
import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import plotly.offline

from . import config, glossary
from .analysis import Signal

ASSETS = Path(__file__).resolve().parent / "assets"

# Colores (mismos tokens que assets/dashboard.css)
S1, S2 = "#4040b5", "#d9622b"     # serie 1 (índigo) y 2 (naranja)
INK, INK2, INK3 = "#333333", "#6e6e6e", "#a7a8aa"
LINE, GRID = "#e3e3e0", "#ededeb"
FONT_TEXT = "'Noto Sans', system-ui, -apple-system, 'Segoe UI', sans-serif"

MONTHS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
LATIN = ("U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, "
         "U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD")
FONTS = [("Figtree", "figtree-latin.woff2", "300 900"), ("Noto Sans", "notosans-latin.woff2", "100 900")]

LEVEL_PILL = {"verde": "ok", "amarillo": "warn", "rojo": "bad"}

ICONS = """<svg xmlns="http://www.w3.org/2000/svg" style="display:none">
<symbol id="i-check" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" fill="currentColor"/><path d="m7.5 12.5 3 3 6-6.5" fill="none" stroke="#fff" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></symbol>
<symbol id="i-empty" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-width="2"/></symbol>
<symbol id="i-na" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-width="2" stroke-dasharray="3 3"/><path d="M8 12h8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></symbol>
<symbol id="i-info" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M12 11v5.5" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><circle cx="12" cy="7.8" r="1.2" fill="currentColor"/></symbol>
<symbol id="i-close" viewBox="0 0 24 24"><path d="M6 6l12 12M18 6 6 18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></symbol>
<symbol id="i-dot" viewBox="0 0 24 24"><circle cx="12" cy="12" r="6" fill="currentColor"/></symbol>
<symbol id="i-clock" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-width="2"/><path d="M12 7v5l3 2" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></symbol>
<symbol id="i-alert" viewBox="0 0 24 24"><path d="M12 3.5 2.5 20h19L12 3.5Z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/><path d="M12 10v4.5M12 17.2v.1" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/></symbol>
</svg>"""

LOGO = ('<svg viewBox="0 0 32 32" aria-hidden="true" focusable="false">'
        '<rect width="32" height="32" rx="8" fill="#fff" fill-opacity=".12"/>'
        '<rect x="7" y="16" width="4.5" height="9" rx="2.25" fill="#4fd1b8"/>'
        '<rect x="13.75" y="11" width="4.5" height="14" rx="2.25" fill="#fff"/>'
        '<rect x="20.5" y="6" width="4.5" height="19" rx="2.25" fill="#9d9df2"/></svg>')
FAVICON = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" rx="8" fill="#1e1e5c"/>'
           '<rect x="7" y="16" width="4.5" height="9" rx="2.25" fill="#4fd1b8"/>'
           '<rect x="13.75" y="11" width="4.5" height="14" rx="2.25" fill="#fff"/>'
           '<rect x="20.5" y="6" width="4.5" height="19" rx="2.25" fill="#9d9df2"/></svg>')


# ---------------------------------------------------------------------------
# Formato
# ---------------------------------------------------------------------------

def _isnum(x) -> bool:
    return x is not None and not (isinstance(x, float) and pd.isna(x))


def _fmt(x, nd=1, suf="", sign=False):
    """Número con separador de miles y signo menos tipográfico (−)."""
    if not _isnum(x):
        return "—"
    s = f"{x:+,.{nd}f}" if sign else f"{x:,.{nd}f}"
    return s.replace("-", "−") + suf


def _chg(x, nd=1, suf="%"):
    """Variación con signo, coloreada y con flecha implícita en el signo (no depende solo del color)."""
    if not _isnum(x):
        return "—"
    cls = "up" if x > 0 else "down" if x < 0 else ""
    return f'<span class="{cls}">{_fmt(x, nd, suf, True)}</span>'


def _date_es(d) -> str:
    try:
        d = pd.Timestamp(d)
    except (ValueError, TypeError):
        return str(d)
    return f"{d.day} {MONTHS[d.month - 1]} {d.year}"


def _e(s) -> str:
    return html.escape(str(s))


def _icon(name: str, cls: str = "icon") -> str:
    return f'<svg class="{cls}" aria-hidden="true" focusable="false"><use href="#i-{name}"/></svg>'


def _info(key: str, what: str) -> str:
    """Botón ⓘ que abre la explicación `key` del glosario."""
    if not key:
        return ""
    return (f'<button type="button" class="info" data-info="{key}" aria-haspopup="dialog" '
            f'aria-label="Qué significa {_e(what)}">{_icon("info")}</button>')


def _sep(*vals: str) -> str:
    return ' <span class="sep" aria-hidden="true">·</span> '.join(vals)


# ---------------------------------------------------------------------------
# Gráficos
# ---------------------------------------------------------------------------

@dataclass
class Chart:
    title: str
    unit: str
    yfmt: str = ",.1f"
    ysuffix: str = ""
    series: list = field(default_factory=list)   # (nombre, serie, color, decimales, sufijo)
    refs: list = field(default_factory=list)     # (y, etiqueta)
    info: str = ""                               # clave en glossary.entries()


CHART_INFO = {
    "Caída del S&P 500 desde su máximo": "spx_dd", "S&P 500 y su media de 200 días": "ma200",
    "VIX: volatilidad esperada": "vix", "Spreads de crédito": "hy", "Rendimiento de los Treasuries": "t10",
    "Curva de tasas": "curve", "Amplitud: igual ponderación vs S&P 500": "rsp_spy",
    "Semiconductores (SOX): caída desde su máximo": "sox",
}


def _window(s: pd.Series) -> pd.Series:
    s = s.dropna()
    if s.empty:
        return s
    return s[s.index >= s.index[-1] - pd.DateOffset(years=config.CHART_YEARS)]


def chart_specs(d, m) -> list[Chart]:
    f, p = d.fred, d.prices
    out: list[Chart] = []

    if "spx_dd_series" in m:
        out.append(Chart("Caída del S&P 500 desde su máximo", "% bajo el máximo histórico", ".0f", "%",
                         [("Caída", _window(m["spx_dd_series"]), S1, 1, "%")],
                         [(-10, "Corrección −10%"), (-20, "Mercado bajista −20%")]))

    full = d.spx_full if len(d.spx_full) else p.get("^GSPC", pd.Series(dtype=float))
    full = full.dropna()
    if len(full):
        out.append(Chart("S&P 500 y su media de 200 días", "Puntos del índice", ",.0f", "",
                         [("S&P 500", _window(full), S1, 0, ""),
                          ("Media 200 días", _window(full.rolling(200).mean()), S2, 0, "")]))

    vix = p["^VIX"] if "^VIX" in p else f.get("VIXCLS", pd.Series(dtype=float))
    if len(vix.dropna()):
        out.append(Chart("VIX: volatilidad esperada", "Puntos", ".0f", "",
                         [("VIX", _window(vix), S1, 1, "")],
                         [(20, "20 · incertidumbre"), (30, "30 · estrés")]))

    if "BAMLH0A0HYM2" in f:
        s = [("High Yield", _window(f["BAMLH0A0HYM2"] * 100), S1, 0, " pb")]
        if "BAMLC0A0CM" in f:
            s.append(("Investment Grade", _window(f["BAMLC0A0CM"] * 100), S2, 0, " pb"))
        out.append(Chart("Spreads de crédito", "Puntos base sobre Treasuries (OAS)", ",.0f", "", s,
                         [(500, "HY 500 pb · estrés")]))

    if "DGS10" in f:
        s = [("10 años", _window(f["DGS10"]), S1, 2, "%")]
        if "DGS2" in f:
            s.append(("2 años", _window(f["DGS2"]), S2, 2, "%"))
        out.append(Chart("Rendimiento de los Treasuries", "% anual", ".1f", "%", s))

    if "T10Y2Y" in f:
        s = [("10a − 2a", _window(f["T10Y2Y"]), S1, 2, " pp")]
        if "T10Y3M" in f:
            s.append(("10a − 3m", _window(f["T10Y3M"]), S2, 2, " pp"))
        out.append(Chart("Curva de tasas", "Puntos porcentuales", ".1f", "", s, [(0, "Inversión")]))

    if "rsp_spy_ratio" in m:
        r = m["rsp_spy_ratio"].dropna()
        if len(r):
            out.append(Chart("Amplitud: igual ponderación vs S&P 500", "RSP/SPY, base 100", ".0f", "",
                             [("RSP/SPY", 100 * r / r.iloc[0], S1, 1, "")]))

    if "^SOX" in p:
        sox = p["^SOX"].dropna()
        if len(sox):
            out.append(Chart("Semiconductores (SOX): caída desde su máximo", "% bajo el máximo", ".0f", "%",
                             [("SOX", 100 * (sox / sox.cummax() - 1), S1, 1, "%")], [(-20, "−20%")]))
    for c in out:
        c.info = CHART_INFO.get(c.title, "")
    return out


def _figure(c: Chart) -> go.Figure:
    fig = go.Figure()
    for name, s, color, nd, suf in c.series:
        s = s.dropna()
        fig.add_trace(go.Scatter(
            x=s.index, y=s.values, name=name, mode="lines",
            line=dict(color=color, width=2),
            hovertemplate=f"%{{y:,.{nd}f}}{suf}"))
    for y, label in c.refs:
        fig.add_hline(y=y, line=dict(color=INK3, width=1, dash="dot"),
                      annotation_text=label, annotation_position="top left",
                      annotation_font=dict(size=11, color=INK2),
                      annotation_bgcolor="rgba(255,255,255,0.85)")
    fig.update_layout(
        template="none", autosize=True, showlegend=False, dragmode=False,
        margin=dict(l=4, r=8, t=8, b=4),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT_TEXT, size=12, color=INK2),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="#ffffff", bordercolor=LINE, font=dict(family=FONT_TEXT, size=13, color=INK)),
        xaxis=dict(type="date", showgrid=False, showline=True, linecolor=LINE, ticks="outside",
                   tickcolor=LINE, ticklen=4, nticks=4, tickangle=0, fixedrange=True, automargin=True,
                   hoverformat="%d %b %Y", showspikes=True, spikemode="across", spikesnap="cursor",
                   spikethickness=1, spikecolor=INK3, spikedash="solid"),
        yaxis=dict(gridcolor=GRID, zeroline=False, showline=False, nticks=5, fixedrange=True,
                   automargin=True, tickformat=c.yfmt, ticksuffix=c.ysuffix),
    )
    return fig


def _chart_html(i: int, c: Chart) -> tuple[str, str]:
    """Devuelve (tarjeta HTML, JSON de la figura)."""
    fig = _figure(c)
    spec = json.loads(pio.to_json(fig, validate=False))
    spec["config"] = {"displayModeBar": False, "responsive": True, "scrollZoom": False,
                      "doubleClick": False, "showTips": False}
    data = json.dumps(spec, separators=(",", ":")).replace("</", "<\\/")

    legend, alt = [], []
    for name, s, color, nd, suf in c.series:
        s = s.dropna()
        last = _fmt(s.iloc[-1], nd, suf) if len(s) else "—"
        when = _date_es(s.index[-1]) if len(s) else ""
        legend.append(f'<li><span class="swatch" style="color:{color}" aria-hidden="true"></span>'
                      f'{_e(name)} <strong>{last}</strong></li>')
        alt.append(f"{name}: {last}" + (f" al {when}" if when else ""))
    label = f"Gráfico de líneas de {c.title}, últimos {config.CHART_YEARS} años. Último dato: " + "; ".join(alt) + "."
    card = (f'<li><figure class="card chart-card">'
            f'<div class="head-row"><div><h3>{_e(c.title)}</h3><p class="chart-card__unit">{_e(c.unit)}</p></div>'
            f'{_info(c.info, c.title)}</div>'
            f'<div class="chart" data-chart="cd{i}" role="img" aria-label="{_e(label)}"></div>'
            f'<figcaption><ul class="legend">{"".join(legend)}</ul></figcaption></figure></li>')
    script = f'<script type="application/json" id="cd{i}">{data}</script>'
    return card, script


# ---------------------------------------------------------------------------
# Bloques HTML
# ---------------------------------------------------------------------------

def _tile(label: str, value: str, sub: str = "", info: str = "") -> str:
    return (f'<li class="card tile"><div class="head-row"><p class="tile__label">{_e(label)}</p>'
            f'{_info(info, label)}</div>'
            f'<p class="tile__value">{value}</p>'
            + (f'<p class="tile__sub">{sub}</p>' if sub else "") + "</li>")


def _group(title: str, tiles: list[str], md: int, lg: int, xl: int | None = None) -> str:
    cols = f"--cols-md:{md};--cols-lg:{lg};--cols-xl:{xl or lg}"
    return (f'<div class="group"><h3>{_e(title)}</h3>'
            f'<ul class="tiles" style="{cols}">{"".join(tiles)}</ul></div>')


def _indicators(m) -> str:
    mercado = [
        _tile("S&P 500", _fmt(m.get("spx"), 0),
              f"{_chg(m.get('spx_1d'), 2)} hoy · {_chg(m.get('spx_5d'), 1)} en 5 días", info="spx"),
        _tile("Caída desde máximo", _fmt(m.get("spx_dd"), 1, "%"),
              f"Máximo {_fmt(m.get('spx_ath'), 0)} el {_date_es(m['spx_ath_date']) if m.get('spx_ath_date') else '—'}", info="spx_dd"),
        _tile("vs media 200 días", _fmt(m.get("spx_vs_ma200"), 1, "%", True),
              f"RSI (14 días) {_fmt(m.get('spx_rsi'), 0)}", info="ma200"),
        _tile("VIX", _fmt(m.get("vix"), 1), f"VIX/VIX3M {_fmt(m.get('vix_term'), 2)}", info="vix"),
        _tile("Breadth", _fmt(m.get("breadth"), 0, "%"), "Acciones sobre su media de 200 días", info="breadth"),
        _tile("Nasdaq-100 · SOX", _sep(_fmt(m.get("ndx_dd"), 1, "%"), _fmt(m.get("sox_dd"), 1, "%")),
              "Caída desde su máximo (3 años)", info="ndx_sox"),
    ]
    tasas = [
        _tile("Spread High Yield", _fmt(m.get("hy_bp"), 0, " pb"),
              f"{_fmt(m.get('hy_20d_bp'), 0, ' pb', True)} en 20 días · IG {_fmt(m.get('ig_bp'), 0, ' pb')}", info="hy"),
        _tile("Treasury 10 años", _fmt(m.get("DGS10"), 2, "%"),
              f"Real {_fmt(m.get('DFII10'), 2, '%')} · {_fmt(m.get('DGS10_20d'), 2, ' pp', True)} en 20 días", info="t10"),
        _tile("Curva 10a − 2a", _fmt(m.get("T10Y2Y"), 2, " pp"), f"10a − 3m {_fmt(m.get('T10Y3M'), 2, ' pp')}", info="curve"),
        _tile("Fed funds", _e(m.get("fed_range", "—")), f"2a − Fed {_fmt(m.get('fed_bias'), 2, ' pp', True)}", info="fed"),
    ]
    macro = [
        _tile("P/E · CAPE", _sep(_fmt(m.get("pe"), 1), _fmt(m.get("cape"), 1)),
              f"Promedio P/E 10 años {_fmt(m.get('pe_10y_avg'), 1)}", info="pe_cape"),
        _tile("Prima de riesgo (ERP)", _fmt(m.get("erp"), 2, " pp"), "Rentabilidad de utilidades − 10 años", info="erp"),
        _tile("Petróleo WTI · Dólar DXY", _sep(_fmt(m.get("wti"), 1), _fmt(m.get("dxy"), 1)), "US$ por barril · índice", info="wti_dxy"),
        _tile("Solicitudes de desempleo", _fmt(m.get("claims"), 0), "Semanales, EE.UU.", info="claims"),
    ]
    return (_group("Mercado", mercado, 3, 3) + _group("Tasas y crédito", tasas, 2, 4)
            + _group("Valoración y macro", macro, 2, 4))


def _signals(signals: list[Signal]) -> str:
    rows = []
    for s in signals:
        if s.met:
            cls, icon, pill = "on", "check", '<span class="pill pill--ok">Cumple</span>'
        elif s.met is False:
            cls, icon, pill = "off", "empty", '<span class="pill pill--muted">No cumple</span>'
        else:
            cls, icon, pill = "na", "na", '<span class="pill pill--outline">Sin dato</span>'
        key = glossary.SIGNAL_KEYS.get(s.key, "")
        rows.append(f'<li class="signal signal--{cls}"><span class="signal__icon">{_icon(icon)}</span>'
                    f'<span class="signal__name">{_e(s.label)}{_info(key, "la señal " + s.label)}</span>'
                    f'<span class="signal__status">{pill}</span>'
                    f'<span class="signal__detail">{_e(s.detail).replace("-", "−")}</span></li>')
    return f'<ul class="card signals">{"".join(rows)}</ul>'


def _tranches(tranches: list[dict], m: dict, pts: int) -> str:
    dd = m.get("spx_dd")
    cards = []
    for t in tranches:
        thr = t["drawdown_pct"]
        cond = f"Se activa si el S&P 500 cae {_fmt(thr, 0, '%')} o más desde su máximo"
        if t["score_min"]:
            cond += f", o si el semáforo llega a {t['score_min']} puntos (hoy {pts})"
        cond += "."
        if t["active"]:
            pill = f'<span class="pill pill--ok">{_icon("check")}Activo</span>'
            why = f'<p class="tranche__cond"><strong>Motivo:</strong> {_e(", ".join(t["reasons"])).replace("-", "−")}</p>'
        else:
            pill = f'<span class="pill pill--muted">{_icon("clock")}Esperando</span>'
            why = ""
        prog = ""
        if _isnum(dd) and thr:
            pct = max(0.0, min(1.0, dd / thr)) * 100
            prog = (f'<div class="progress"><div class="progress__bar" role="progressbar" aria-valuemin="0" '
                    f'aria-valuemax="100" aria-valuenow="{pct:.0f}" aria-label="Avance hacia la caída requerida">'
                    f'<span style="--p:{pct:.0f}%"></span></div>'
                    f'<p class="progress__text"><span>Caída actual <strong>{_fmt(dd, 1, "%")}</strong></span>'
                    f'<span>Meta <strong>{_fmt(thr, 0, "%")}</strong></span></p></div>')
        cards.append(
            f'<li class="card tranche{" tranche--active" if t["active"] else ""}">'
            f'<div class="tranche__head"><h3 class="tranche__name">{_e(t["name"])}</h3>{pill}</div>'
            f'<p class="tranche__fraction">{t["fraction"]:.0%}<span>del monto</span></p>'
            f'<p class="tranche__cond">{cond}</p>{why}{prog}</li>')
    return f'<ul class="tranches">{"".join(cards)}</ul>'


def _ai_table(m: dict) -> str:
    rows = sorted(m.get("ai_basket", []), key=lambda a: a["dd"])
    if not rows:
        return '<p class="card tile">Sin datos de la canasta en esta corrida.</p>'
    worst = max((abs(a["dd"]) for a in rows), default=1) or 1
    body = "".join(
        f'<tr><th scope="row"><span class="ticker">{_e(a["ticker"])}</span>'
        f'<span class="company">{_e(a["name"])}</span></th>'
        f'<td class="num">{_fmt(a["price"], 2)}</td>'
        f'<td class="num">{_chg(a["d1"], 1)}<span class="m-only">{_chg(a["d5"], 1)}</span></td>'
        f'<td class="num col-5d">{_chg(a["d5"], 1)}</td>'
        f'<td class="num"><span class="dd"><span class="dd__bar" aria-hidden="true">'
        f'<span style="--p:{100 * abs(a["dd"]) / worst:.0f}%"></span></span>{_fmt(a["dd"], 1, "%")}</span></td></tr>'
        for a in rows)
    return (f'<div class="card table-wrap" role="region" aria-labelledby="ia-title" tabindex="0">'
            f'<table><caption class="sr-only">Canasta IA ordenada por caída desde máximo</caption>'
            f'<thead><tr><th scope="col">Empresa</th><th scope="col" class="num">Precio</th>'
            f'<th scope="col" class="num">1 día<span class="m-only">5 días</span></th>'
            f'<th scope="col" class="num col-5d">5 días</th>'
            f'<th scope="col" class="num">Desde máx.</th></tr></thead><tbody>{body}</tbody></table></div>')


def _glossary_templates() -> str:
    out = []
    for key, g in glossary.entries().items():
        body = "<h3>Qué es</h3>" + "".join(f"<p>{_e(p)}</p>" for p in g["what"])
        body += "<h3>Cómo leerlo</h3>" + "".join(f"<p>{_e(p)}</p>" for p in g["read"])
        if g.get("monitor"):
            body += f'<div class="sheet__note"><h3>En este monitor</h3><p>{_e(g["monitor"])}</p></div>'
        out.append(f'<template id="info-{key}" data-title="{_e(g["title"])}">{body}</template>')
    return "\n".join(out)


def _font_faces() -> str:
    out = []
    for family, file, weight in FONTS:
        p = ASSETS / "fonts" / file
        if not p.exists():
            continue
        b64 = base64.b64encode(p.read_bytes()).decode("ascii")
        out.append(f'@font-face{{font-family:"{family}";font-style:normal;font-weight:{weight};'
                   f'font-display:swap;src:url(data:font/woff2;base64,{b64}) format("woff2");'
                   f'unicode-range:{LATIN}}}')
    return "\n".join(out)


def _plotly_asset(out_dir: Path) -> str:
    """Copia plotly.js (misma versión que el paquete de Python) a site/assets/."""
    ver = plotly.offline.get_plotlyjs_version()
    name = f"plotly-{ver}.min.js"
    dest = out_dir / "assets"
    dest.mkdir(parents=True, exist_ok=True)
    for old in dest.glob("plotly-*.min.js"):
        if old.name != name:
            old.unlink()
    if not (dest / name).exists():
        (dest / name).write_text(plotly.offline.get_plotlyjs(), encoding="utf-8")
    fonts_dir = dest / "fonts"
    fonts_dir.mkdir(exist_ok=True)
    for lic in (ASSETS / "fonts").glob("*-OFL.txt"):
        shutil.copyfile(lic, fonts_dir / lic.name)
    return f"assets/{name}"


# ---------------------------------------------------------------------------
# Estructura común de las páginas
# ---------------------------------------------------------------------------

TABS = [("hoy", "index.html", "Resumen diario"), ("historico", "historico.html", "Histórico")]


def _brand(active: str, h1: bool = True) -> str:
    tag = "h1" if h1 else "p"
    cur = ' aria-current="page"'
    tabs = "".join(f'<a href="{href}"{cur if key == active else ""}>{_e(label)}</a>'
                   for key, href, label in TABS)
    return (f'<div class="brand"><a class="brand__home" href="index.html">{LOGO}'
            f'<{tag} class="brand__name">Monitor S&amp;P 500</{tag}></a>'
            f'<nav class="tabs" aria-label="Vistas del monitor">{tabs}</nav></div>')


def _head(title: str, desc: str, plotly_src: str) -> str:
    css = (ASSETS / "dashboard.css").read_text(encoding="utf-8")
    favicon = "data:image/svg+xml," + FAVICON.replace("#", "%23").replace('"', "'")
    return f"""<!DOCTYPE html>
<html lang="es" class="no-js">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{_e(title)}</title>
<meta name="description" content="{_e(desc)}">
<meta name="theme-color" content="#1e1e5c">
<meta name="color-scheme" content="light">
<meta property="og:title" content="Monitor S&amp;P 500">
<meta property="og:description" content="{_e(desc)}">
<link rel="icon" href="{favicon}">
<script>(function(d){{d.classList.replace("no-js","js");try{{if(localStorage.getItem("monitor-info")==="off")d.classList.add("info-off")}}catch(e){{}}}})(document.documentElement)</script>
<script src="{plotly_src}" defer></script>
<style>
{_font_faces()}
{css}
</style>
</head>
<body>
{ICONS}
<a class="skip-link" href="#contenido">Saltar al contenido</a>
"""


def _toggle() -> str:
    return (f'<button type="button" class="toggle" role="switch" aria-checked="true" id="info-toggle">'
            f'{_icon("info")}<span class="toggle__label">Explicaciones</span>'
            f'<span class="toggle__track" aria-hidden="true"></span></button>')


def _tail(js: str, data: str = "", sources: str = "") -> str:
    sources = sources or ('Datos de <a href="https://fred.stlouisfed.org/">FRED</a>, '
                          '<a href="https://finance.yahoo.com/">Yahoo Finance</a> y '
                          '<a href="https://www.multpl.com/">multpl.com</a>. Los umbrales se ajustan en '
                          '<code>monitor/config.py</code>.')
    return f"""
<footer class="footer">
  <div class="wrap">
    <p><strong>Material informativo, no constituye asesoría financiera.</strong></p>
    <p>{sources}</p>
  </div>
</footer>

<dialog class="sheet" id="info-sheet" aria-labelledby="sheet-title">
  <div class="sheet__head"><h2 id="sheet-title"></h2>
    <button type="button" class="sheet__close" data-close aria-label="Cerrar">{_icon("close")}</button></div>
  <div class="sheet__body" id="sheet-body"></div>
</dialog>
{_glossary_templates()}
{data}
<script>
{js}
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Página principal
# ---------------------------------------------------------------------------

def render(d, m, signals: list[Signal], pts: int, n_avail: int, level: str, level_text: str,
           tranches: list[dict], generated: str, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    plotly_src = _plotly_asset(out_dir)
    js = (ASSETS / "dashboard.js").read_text(encoding="utf-8")

    try:
        gdt = datetime.strptime(generated, "%Y-%m-%d %H:%M")
        gen_iso, gen_txt = gdt.strftime("%Y-%m-%dT%H:%M"), f"{_date_es(gdt)}, {gdt:%H:%M}"
    except ValueError:
        gen_iso, gen_txt = "", generated

    # Cabecera: semáforo
    meter = "".join(
        f'<li class="{"is-on" if s.met else "is-na" if s.met is None else ""}"></li>' for s in signals)
    n_active = sum(1 for t in tranches if t["active"])
    pill_kind = LEVEL_PILL.get(level, "muted")

    charts = [_chart_html(i, c) for i, c in enumerate(chart_specs(d, m))]
    chart_cards = "".join(c for c, _ in charts)
    chart_data = "\n".join(s for _, s in charts)

    errors = d.errors
    nav = [("indicadores", "Indicadores"), ("senales", "Señales"), ("tramos", "Tramos"),
           ("graficos", "Gráficos"), ("canasta", "Canasta IA")]
    if errors:
        nav.append(("avisos", f"Avisos ({len(errors)})"))
    nav_html = "".join(f'<li><a href="#{i}">{_e(t)}</a></li>' for i, t in nav)

    notice = ""
    if errors:
        items = "".join(f"<li>{_e(e)}</li>" for e in errors)
        notice = (f'<section class="section" id="avisos" aria-labelledby="avisos-title">'
                  f'<h2 class="sr-only" id="avisos-title">Avisos de datos</h2>'
                  f'<details class="card notice"><summary>{_icon("alert")}'
                  f'Avisos de datos: {len(errors)} fuente{"s" if len(errors) != 1 else ""} con problemas</summary>'
                  f'<ul>{items}</ul></details></section>')

    desc = f"Semáforo {level}: {pts} de {n_avail} señales. {level_text}."
    head = _head(f"Monitor S&P 500 · semáforo {level} ({pts}/{n_avail})", desc, plotly_src)

    page = head + f"""

<header class="masthead level--{_e(level)}">
  <div class="wrap masthead__inner">
    {_brand("hoy")}
    <div class="masthead__intro">
      <p class="lead">{_e(level_text)}.{_info("titular", "este titular")}</p>
      <p class="updated">Actualizado el <time datetime="{gen_iso}">{_e(gen_txt)}</time> (hora de Chile)</p>
    </div>
    <section class="scorecard" aria-labelledby="score-title">
      <div class="head-row"><h2 class="scorecard__label" id="score-title" style="font:inherit">Semáforo de entrada</h2>{_info("semaforo", "el semáforo de entrada")}</div>
      <div class="scorecard__row">
        <p class="score">{pts}<small>/{n_avail}</small><span class="sr-only"> señales cumplidas de {n_avail} con datos</span></p>
        <span class="pill pill--{pill_kind}">{_icon("dot")}Semáforo {_e(level)}</span>
      </div>
      <ul class="meter" style="--n:{len(signals)}" aria-hidden="true">{meter}</ul>
      <p class="scorecard__foot">{n_avail} de {len(signals)} señales con datos · Tramos activos: <strong>{n_active} de {len(tranches)}</strong></p>
    </section>
  </div>
</header>

<nav class="subnav" aria-label="Secciones"><div class="wrap subnav__inner"><ul>{nav_html}</ul>
  {_toggle()}</div></nav>

<main id="contenido" class="wrap" tabindex="-1">
  <section class="section" id="indicadores" aria-labelledby="indicadores-title">
    <div class="section__head"><h2 id="indicadores-title">Indicadores clave</h2>
      <p>La foto del mercado con el último dato disponible de cada fuente.</p>
      <p class="info-hint">{_icon("info")}<span>Toca <b>ⓘ</b> para ver qué significa cada dato. Cuando ya los conozcas, puedes
      ocultar estas ayudas con el interruptor de la barra de secciones.</span></p></div>
    {_indicators(m)}
  </section>

  <section class="section" id="senales" aria-labelledby="senales-title">
    <div class="section__head"><div class="title-row"><h2 id="senales-title">Señales de fondo</h2>{_info("semaforo", "las señales de fondo")}</div>
      <p>Cada señal que se cumple suma un punto al semáforo de entrada.</p></div>
    {_signals(signals)}
  </section>

  <section class="section" id="tramos" aria-labelledby="tramos-title">
    <div class="section__head"><div class="title-row"><h2 id="tramos-title">Plan por tramos</h2>{_info("tramos", "el plan por tramos")}</div>
      <p>La inversión se divide en tres partes. Si un tramo no se activa antes del
      {_e(_date_es(config.TRANCHE_DEADLINE))}, se invierte igual.</p></div>
    {_tranches(tranches, m, pts)}
  </section>

  <section class="section" id="graficos" aria-labelledby="graficos-title">
    <div class="section__head"><h2 id="graficos-title">Gráficos</h2>
      <p>Últimos {config.CHART_YEARS} años. Toca o pasa el cursor sobre un gráfico para ver el valor de cada día.</p></div>
    <ul class="charts">{chart_cards}</ul>
  </section>

  <section class="section" id="canasta" aria-labelledby="ia-title">
    <div class="section__head"><div class="title-row"><h2 id="ia-title">Canasta IA</h2>{_info("ai_basket", "la canasta IA")}</div>
      <p>Precios en US$, ordenados de mayor a menor caída desde su máximo.</p></div>
    {_ai_table(m)}
  </section>

  {notice}
</main>

"""
    page += _tail(js, chart_data)
    path = out_dir / "index.html"
    path.write_text(page, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Pestaña Histórico
# ---------------------------------------------------------------------------

def _seg(attr: str, items: list[tuple[str, str]], label: str) -> str:
    """Grupo de botones excluyentes (estado en aria-pressed, lo maneja historico.js)."""
    btns = "".join(f'<button type="button" class="seg__btn" data-{attr}="{v}" aria-pressed="false">{_e(t)}</button>'
                   for v, t in items)
    return f'<div class="seg" role="group" aria-label="{_e(label)}">{btns}</div>'


def _asset_options(assets: list[dict], placeholder: str | None) -> str:
    groups: dict[str, list[dict]] = {}
    for a in assets:
        groups.setdefault(a["group"], []).append(a)
    opts = f'<option value="">{_e(placeholder)}</option>' if placeholder else ""
    for g, items in groups.items():
        opts += f'<optgroup label="{_e(g)}">' + "".join(
            f'<option value="{_e(a["id"])}">{_e(a["name"])}</option>' for a in items) + "</optgroup>"
    return opts


def render_history(close: pd.DataFrame, errors: list[str], generated: str, out_dir: Path) -> Path:
    from . import history

    out_dir.mkdir(parents=True, exist_ok=True)
    plotly_src = _plotly_asset(out_dir)
    data = history.payload(close, errors, generated)
    data_src = history.write(data, out_dir)
    js = ((ASSETS / "dashboard.js").read_text(encoding="utf-8") + "\n"
          + (ASSETS / "historico.js").read_text(encoding="utf-8"))
    assets = data["assets"]

    try:
        gdt = datetime.strptime(generated, "%Y-%m-%d %H:%M")
        gen_iso, gen_txt = gdt.strftime("%Y-%m-%dT%H:%M"), f"{_date_es(gdt)}, {gdt:%H:%M}"
    except ValueError:
        gen_iso, gen_txt = "", generated

    ranges = [("1M", "1M"), ("6M", "6M"), ("YTD", "Este año"), ("1A", "1A"), ("5A", "5A"),
              ("10A", "10A"), ("20A", "20A"), ("MAX", "Máx")]
    measures = [("pct", "Cambio %"), ("dd", "Caída desde máximo"), ("val", "Valor")]
    wins = [("3M", "3 meses"), ("6M", "6 meses"), ("1A", "1 año"), ("2A", "2 años"), ("3A", "3 años"), ("5A", "5 años")]
    ep_chips = "".join(
        f'<button type="button" class="chip chip--toggle" data-ep="{_e(e["id"])}" aria-pressed="false">'
        f'{_icon("check", "icon chip__check")}{_e(e["name"])}</button>'
        for e in config.HISTORY_EPISODES + [{"id": "now", "name": "Actual"}])
    presets = '<option value="">Ir a un período…</option>' + "".join(
        f'<option value="{_e(e["id"])}">{_e(e["name"])}</option>' for e in config.HISTORY_EPISODES)

    notice = ""
    if errors:
        items = "".join(f"<li>{_e(e)}</li>" for e in errors)
        notice = (f'<details class="card notice" style="margin-top:var(--s-6)"><summary>{_icon("alert")}'
                  f'Avisos de datos del histórico ({len(errors)})</summary><ul>{items}</ul></details>')

    table_head = ('<thead><tr><th scope="col">Activo</th><th scope="col" class="num">Cambio</th>'
                  '<th scope="col" class="num">Rent. anual</th><th scope="col" class="num">Peor caída</th>'
                  '<th scope="col" class="num">Fecha del mínimo</th></tr></thead>')
    crisis_head = ('<thead><tr><th scope="col">Episodio</th><th scope="col" class="num">Peor punto</th>'
                   '<th scope="col" class="num">Hasta el piso</th><th scope="col" class="num">Recuperación</th>'
                   '<th scope="col" class="num">Al final</th></tr></thead>')

    desc = "Compara índices, fondos, monedas y acciones en distintos períodos y crisis."
    page = _head("Histórico comparativo · Monitor S&P 500", desc, plotly_src) + f"""
<header class="masthead masthead--compact">
  <div class="wrap masthead__inner">
    {_brand("historico", h1=False)}
    <div class="masthead__intro">
      <h1 class="lead">Histórico comparativo</h1>
      <p class="updated">Compara cómo se comportaron índices, fondos, monedas y acciones en distintos períodos.
      Datos al <time datetime="{gen_iso}">{_e(gen_txt)}</time>.</p>
    </div>
  </div>
</header>

<main id="contenido" class="wrap hist" tabindex="-1">
<div id="hist">
  <div class="hist__bar">
    <div class="viewtabs" role="tablist" aria-label="Tipo de comparación">
      <button type="button" role="tab" id="tab-periodo" data-view="periodo" aria-controls="panel-periodo" aria-selected="true">Por período</button>
      <button type="button" role="tab" id="tab-crisis" data-view="crisis" aria-controls="panel-crisis" aria-selected="false" tabindex="-1">Comparar crisis</button>
    </div>
    {_info("hist_modes", "las dos formas de comparar")}
    <span class="hist__spacer"></span>
    {_toggle()}
  </div>

  <p class="card empty" data-empty hidden>No hay datos históricos en esta corrida. Revisa los avisos de datos más abajo.</p>

  <section id="panel-periodo" role="tabpanel" aria-labelledby="tab-periodo" class="panel">
    <div class="card controls">
      <div class="field">
        <div class="field__label"><span id="lbl-assets">Activos</span>{_info("hist_activos", "los activos disponibles")}</div>
        <ul class="chips" id="p-chips" aria-labelledby="lbl-assets"></ul>
        <label class="sr-only" for="p-add">Agregar activo</label>
        <select id="p-add" class="select">{_asset_options(assets, "Agregar activo…")}</select>
      </div>
      <div class="field">
        <div class="field__label">Rango</div>
        {_seg("range", ranges, "Rango de tiempo")}
        <div class="dates">
          <label>Desde<input type="date" id="p-from" class="input"></label>
          <label>Hasta<input type="date" id="p-to" class="input"></label>
          <label class="sr-only" for="p-preset">Ir a un período histórico</label>
          <select id="p-preset" class="select">{presets}</select>
        </div>
      </div>
      <div class="field">
        <div class="field__label">Medida{_info("hist_medidas", "las medidas del gráfico")}</div>
        <div class="field__row">
          {_seg("measure", measures, "Medida")}
          <label class="check"><input type="checkbox" id="p-log"> Escala logarítmica</label>
        </div>
      </div>
    </div>

    <figure class="card chart-card hist-chart">
      <div><h2 id="p-title" class="chart-card__title"></h2><p class="chart-card__unit" id="p-sub"></p></div>
      <div class="chart chart--big" id="p-chart" role="img"></div>
      <figcaption><ul class="legend" id="p-legend"></ul></figcaption>
    </figure>

    <div class="card table-wrap" role="region" aria-labelledby="p-table-title" tabindex="0">
      <div class="table-title"><h2 id="p-table-title">Resumen del rango</h2>{_info("hist_stats", "la tabla de resumen")}</div>
      <table class="stats">{table_head}<tbody id="p-rows"></tbody></table>
    </div>
  </section>

  <section id="panel-crisis" role="tabpanel" aria-labelledby="tab-crisis" class="panel" hidden>
    <div class="card controls">
      <div class="field">
        <label class="field__label" for="c-asset">Activo</label>
        <select id="c-asset" class="select">{_asset_options(assets, None)}</select>
      </div>
      <div class="field">
        <div class="field__label"><span id="lbl-eps">Episodios</span>{_info("hist_episodios", "los episodios de crisis")}</div>
        <div class="chips" role="group" aria-labelledby="lbl-eps">{ep_chips}</div>
        <div class="dates"><label>“Actual” desde<input type="date" id="c-now" class="input"></label></div>
      </div>
      <div class="field">
        <div class="field__label">Ventana</div>
        {_seg("win", wins, "Ventana de tiempo")}
      </div>
    </div>

    <figure class="card chart-card hist-chart">
      <div><h2 id="c-title" class="chart-card__title"></h2><p class="chart-card__unit" id="c-sub"></p></div>
      <div class="chart chart--big" id="c-chart" role="img"></div>
      <figcaption><ul class="legend" id="c-legend"></ul></figcaption>
    </figure>

    <div class="card table-wrap" role="region" aria-labelledby="c-table-title" tabindex="0">
      <div class="table-title"><h2 id="c-table-title">Resumen por episodio</h2>{_info("hist_episodios", "los episodios de crisis")}</div>
      <table class="stats">{crisis_head}<tbody id="c-rows"></tbody></table>
    </div>
  </section>

  <p class="hist__note">Cierres diarios de los últimos {config.HISTORY_DAILY_YEARS} años y semanales antes.
  Fondos y acciones con dividendos reinvertidos. Los activos y episodios se configuran en <code>monitor/config.py</code>.</p>
  <noscript><p class="card empty">Esta pestaña necesita JavaScript para dibujar los gráficos.</p></noscript>
  {notice}
</div>
</main>
<script src="{data_src}"></script>
"""
    page += _tail(js, sources='Datos de <a href="https://finance.yahoo.com/">Yahoo Finance</a>.')
    path = out_dir / "historico.html"
    path.write_text(page, encoding="utf-8")
    return path
