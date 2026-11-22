"""Punto de entrada: python -m monitor [--demo] [--no-notify]"""

from __future__ import annotations

import argparse
import logging
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from . import analysis, config, notify, report, sources

ROOT = Path(__file__).resolve().parent.parent
HISTORY = ROOT / "data" / "history.csv"
HISTORY_COLS = ["timestamp", "score", "available", "spx", "spx_dd", "vix", "vix_term", "hy_bp", "ig_bp",
                "DGS10", "DGS2", "T10Y2Y", "T10Y3M", "fed_mid", "pe", "cape", "erp", "breadth", "sox_dd"]


def main() -> None:
    ap = argparse.ArgumentParser(description="Monitor diario del S&P 500")
    ap.add_argument("--demo", action="store_true", help="usa datos sintéticos (sin red)")
    ap.add_argument("--no-notify", action="store_true", help="no envía Telegram")
    ap.add_argument("--out", default=str(ROOT / "site"), help="carpeta de salida del HTML")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    data = sources.demo_data() if args.demo else sources.fetch_all()
    m = analysis.compute_metrics(data)
    signals = analysis.compute_signals(m)
    pts, n_avail = analysis.score(signals)
    level, level_text = analysis.score_label(pts)
    tranches = analysis.tranche_status(m, pts)
    now = datetime.now(ZoneInfo(config.TIMEZONE))

    path = report.render(data, m, signals, pts, n_avail, level, level_text, tranches,
                         now.strftime("%Y-%m-%d %H:%M"), Path(args.out))
    print(f"Dashboard: {path}")

    prev_pts = None
    if not args.demo:
        HISTORY.parent.mkdir(parents=True, exist_ok=True)
        hist = pd.read_csv(HISTORY) if HISTORY.exists() else pd.DataFrame(columns=HISTORY_COLS)
        if len(hist):
            prev_pts = int(hist["score"].iloc[-1])
        row = {"timestamp": now.isoformat(timespec="minutes"), "score": pts, "available": n_avail}
        row |= {k: m.get(k) for k in HISTORY_COLS if k not in row}
        pd.concat([hist, pd.DataFrame([row])], ignore_index=True).to_csv(HISTORY, index=False)

    msg = notify.build_message(m, signals, pts, n_avail, level, level_text, tranches,
                               os.getenv("SITE_URL", ""), prev_pts)
    if args.no_notify:
        print(msg)
    else:
        notify.send_telegram(msg)


if __name__ == "__main__":
    main()
