"""Envío del resumen por Telegram. Requiere TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID."""

from __future__ import annotations

import os

import requests


def _f(x, nd=1, suf="", sign=False):
    if x is None:
        return "—"
    return f"{x:+.{nd}f}{suf}" if sign else f"{x:,.{nd}f}{suf}"


def build_message(m, signals, pts, n_avail, level, level_text, tranches, site_url, prev_pts=None) -> str:
    emoji = {"verde": "🟢", "amarillo": "🟡", "rojo": "🔴"}[level]
    change = "" if prev_pts is None or prev_pts == pts else f" (antes {prev_pts})"
    lines = [
        f"{emoji} *Monitor S&P 500*: semáforo {pts}/{n_avail}{change}",
        level_text,
        "",
        f"S&P {_f(m.get('spx'), 0)} ({_f(m.get('spx_1d'), 2, '%', True)}) · desde máx {_f(m.get('spx_dd'), 1, '%')}",
        f"VIX {_f(m.get('vix'))} · HY {_f(m.get('hy_bp'), 0, ' pb')} ({_f(m.get('hy_20d_bp'), 0, ' pb', True)} 20d)",
        f"10a {_f(m.get('DGS10'), 2, '%')} · 10a−2a {_f(m.get('T10Y2Y'), 2, ' pp')} · Fed {m.get('fed_range', '—')}",
        f"Breadth {_f(m.get('breadth'), 0, '%')} · SOX desde máx {_f(m.get('sox_dd'), 1, '%')}",
        "",
        "Señales: " + " ".join(("✅" if s.met else "▫️" if s.met is False else "❔") + s.label for s in signals),
    ]
    active = [t["name"] for t in tranches if t["active"]]
    lines.append("Tramos activos: " + (", ".join(active) if active else "ninguno"))
    if site_url:
        lines += ["", site_url]
    return "\n".join(lines)


def send_telegram(text: str) -> bool:
    token, chat = os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat:
        print("Telegram no configurado; mensaje:\n" + text)
        return False
    r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                      json={"chat_id": chat, "text": text, "parse_mode": "Markdown",
                            "disable_web_page_preview": True}, timeout=(5, 20))
    r.raise_for_status()
    return True
