#!/usr/bin/env python3
"""
Pipeline : Binance → RETA-ND → HTML/CSS
"""
from __future__ import annotations

import json
import math
import os
import sys
import time
import webbrowser
from pathlib import Path

import numpy as np
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from reta.nd import RETAND


# ── 1. Binance ──────────────────────────────────────────────────────────────

BINANCE_BASE = "https://api.binance.com"


def fetch_klines(symbol: str = "BTCUSDT", interval: str = "1h", limit: int = 100) -> np.ndarray:
    """Récupère les close prices depuis Binance."""
    resp = requests.get(
        f"{BINANCE_BASE}/api/v3/klines",
        params={"symbol": symbol, "interval": interval, "limit": limit},
        timeout=15,
    )
    resp.raise_for_status()
    closes = np.array([float(k[4]) for k in resp.json()])  # index 4 = close
    return closes


def fetch_ticker(symbol: str = "BTCUSDT") -> dict:
    """Prix et variation 24h."""
    resp = requests.get(
        f"{BINANCE_BASE}/api/v3/ticker/24hr",
        params={"symbol": symbol},
        timeout=15,
    )
    resp.raise_for_status()
    d = resp.json()
    return {
        "symbol": d["symbol"],
        "price": float(d["lastPrice"]),
        "change_24h": float(d["priceChange"]),
        "change_percent": float(d["priceChangePercent"]),
        "high": float(d["highPrice"]),
        "low": float(d["lowPrice"]),
        "volume": float(d["volume"]),
    }


# ── 2. RETA-ND ──────────────────────────────────────────────────────────────

def run_reta_pipeline(closes: np.ndarray) -> list[dict]:
    """Log-rendements → RETA-ND → résultats structurés."""
    log_returns = np.diff(np.log(closes))  # r_k ~ z

    # RETA-ND à 2 axes (ex. tendance + volatilité)
    nd = RETAND(
        n=2,
        Y_max_axes=[0.05, 0.03],
        dt=1.0,
    )

    # On prépare 2 observations par pas : log-return + |log-return|
    obs = np.column_stack([log_returns, np.abs(log_returns)])
    results = nd.fit(obs)

    rows = []
    for i, step_results in enumerate(results):
        rows.append({
            "step": i,
            "z1": step_results[0].z_hat,
            "dz1": step_results[0].dz_hat,
            "y1": step_results[0].y_open,
            "y1_real": step_results[0].y_real,
            "e1": step_results[0].e,
            "z2": step_results[1].z_hat,
            "dz2": step_results[1].dz_hat,
            "y2": step_results[1].y_open,
            "y2_real": step_results[1].y_real,
            "e2": step_results[1].e,
            "u1": step_results[0].u,
            "u2": step_results[1].u,
        })
    return rows


# ── 3. HTML/CSS ─────────────────────────────────────────────────────────────

HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Binance → RETA-ND</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: system-ui, -apple-system, sans-serif;
    background: #0f1117;
    color: #e4e6ed;
    padding: 24px;
  }}
  h1 {{ font-size: 1.5rem; margin-bottom: 8px; }}
  .sub {{ color: #888; font-size: 0.85rem; margin-bottom: 24px; }}

  /* ticker cards */
  .ticker-grid {{
    display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 12px; margin-bottom: 28px;
  }}
  .card {{
    background: #1a1d27; border-radius: 10px; padding: 16px;
    border: 1px solid #2a2d37;
  }}
  .card .label {{ font-size: 0.75rem; color: #888; text-transform: uppercase; }}
  .card .value {{ font-size: 1.2rem; font-weight: 600; margin-top: 4px; }}
  .up {{ color: #22c55e; }} .dn {{ color: #ef4444; }}

  /* table */
  .table-wrap {{
    overflow-x: auto; border-radius: 10px;
    border: 1px solid #2a2d37; background: #1a1d27;
  }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.8rem; }}
  th {{
    text-align: left; padding: 10px 12px;
    background: #22253a; color: #999;
    position: sticky; top: 0; white-space: nowrap;
  }}
  td {{ padding: 8px 12px; border-top: 1px solid #2a2d37; }}
  tr:hover td {{ background: #25283f; }}
  .num {{ font-family: "JetBrains Mono", "Fira Code", monospace; text-align: right; }}
  .pos {{ color: #22c55e; }} .neg {{ color: #ef4444; }}
</style>
</head>
<body>
  <h1>Binance → RETA-ND</h1>
  <p class="sub">{symbol} · {interval} · {nrows} pas · {timestamp}</p>

  <div class="ticker-grid">
    <div class="card">
      <div class="label">Prix</div>
      <div class="value">{price}</div>
    </div>
    <div class="card">
      <div class="label">Variation 24h</div>
      <div class="value {change_cls}">{change_24h} ({change_percent}%)</div>
    </div>
    <div class="card">
      <div class="label">Plus haut 24h</div>
      <div class="value">{high}</div>
    </div>
    <div class="card">
      <div class="label">Plus bas 24h</div>
      <div class="value">{low}</div>
    </div>
    <div class="card">
      <div class="label">Volume 24h</div>
      <div class="value">{volume}</div>
    </div>
  </div>

  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>#</th>
          <th>z₁</th><th>ż₁</th><th>y₁</th><th>y₁ᵣ</th><th>e₁</th>
          <th>z₂</th><th>ż₂</th><th>y₂</th><th>y₂ᵣ</th><th>e₂</th>
        </tr>
      </thead>
      <tbody>
{rows}
      </tbody>
    </table>
  </div>
</body>
</html>"""


def fmt(val: float, dec: int = 6) -> str:
    cls = "pos" if val >= 0 else "neg"
    return f'<span class="{cls}">{val:.{dec}f}</span>'


def build_html(symbol: str, interval: str, ticker: dict, rows: list[dict]) -> str:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    nrows = len(rows)
    pct = ticker["change_percent"]
    change_cls = "up" if pct >= 0 else "dn"

    row_html = ""
    for r in rows:
        row_html += (
            f"<tr>"
            f"<td>{r['step']}</td>"
            f"<td class=\"num\">{fmt(r['z1'])}</td>"
            f"<td class=\"num\">{fmt(r['dz1'])}</td>"
            f"<td class=\"num\">{fmt(r['y1'])}</td>"
            f"<td class=\"num\">{fmt(r['y1_real'])}</td>"
            f"<td class=\"num\">{fmt(r['e1'])}</td>"
            f"<td class=\"num\">{fmt(r['z2'])}</td>"
            f"<td class=\"num\">{fmt(r['dz2'])}</td>"
            f"<td class=\"num\">{fmt(r['y2'])}</td>"
            f"<td class=\"num\">{fmt(r['y2_real'])}</td>"
            f"<td class=\"num\">{fmt(r['e2'])}</td>"
            f"</tr>\n"
        )

    return HTML_TEMPLATE.format(
        symbol=symbol,
        interval=interval,
        nrows=nrows,
        timestamp=ts,
        price=f"${ticker['price']:,.2f}",
        change_24h=f"{ticker['change_24h']:+.2f}",
        change_percent=f"{ticker['change_percent']:+.2f}",
        change_cls=change_cls,
        high=f"${ticker['high']:,.2f}",
        low=f"${ticker['low']:,.2f}",
        volume=f"{ticker['volume']:,.0f}",
        rows=row_html,
    )


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    symbol = sys.argv[1] if len(sys.argv) > 1 else "BTCUSDT"
    interval = sys.argv[2] if len(sys.argv) > 2 else "1h"
    limit = int(sys.argv[3]) if len(sys.argv) > 3 else 50

    print(f" Binance {symbol} ({interval}, limit={limit})…")
    ticker = fetch_ticker(symbol)
    closes = fetch_klines(symbol, interval, limit)
    print(f"   {len(closes)} closes récupérées")

    print(" RETA-ND…")
    rows = run_reta_pipeline(closes)

    html = build_html(symbol, interval, ticker, rows)
    out = Path("/tmp/binance_reta_output.html")
    out.write_text(html, encoding="utf-8")

    print(f" HTML → {out}")
    webbrowser.open(out.as_uri())


if __name__ == "__main__":
    main()