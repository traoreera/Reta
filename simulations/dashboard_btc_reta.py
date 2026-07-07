"""
RETA Dashboard — BTC temps réel
Flask backend + HTML/CSS/JS frontend professionnel (light theme)
Lancer : uv run python simulations/dashboard_btc_reta.py
"""

import datetime
import json
import logging
import math
import os
import sys
import threading
import time
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import requests
from flask import Flask, jsonify, render_template_string, request

from reta import RETAReferential

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("reta.dashboard")

app = Flask(__name__)
POSITIONS_FILE = Path("simulations/positions.json")

# ── BYBIT API v5 ─────────────────────────────────────────────────────────────

BYBIT_API_KEY    = os.environ.get("BYBIT_API_KEY", "")
BYBIT_SECRET_KEY = os.environ.get("BYBIT_SECRET_KEY", "")


def _bybit_sign_params(params: dict) -> dict:
    import hashlib
    import hmac

    timestamp = str(int(time.time() * 1000))
    recv_window = "10000"
    query = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    sign_str = timestamp + BYBIT_API_KEY + recv_window + query
    sig = hmac.new(
        BYBIT_SECRET_KEY.encode(), sign_str.encode(), hashlib.sha256
    ).hexdigest()
    params["api_key"] = BYBIT_API_KEY
    params["timestamp"] = timestamp
    params["recv_window"] = recv_window
    params["sign"] = sig
    return params


def _bybit_get(path: str, params: dict):
    params = _bybit_sign_params(params)
    return requests.get(f"https://api.bybit.com{path}", params=params, timeout=15)


def _bybit_post(path: str, params: dict):
    params = _bybit_sign_params(params)
    return requests.post(f"https://api.bybit.com{path}", params=params, timeout=15)


def bybit_futures_positions(symbol="BTCUSDT") -> list[dict]:
    if not BYBIT_API_KEY:
        return []
    try:
        params = {"category": "linear", "symbol": symbol, "limit": 50}
        r = _bybit_get("/v5/position/list", params)
        r.raise_for_status()
        data = r.json()
        if data.get("retCode", -1) != 0:
            log.warning("Bybit positions error: %s", data.get("retMsg", ""))
            return []
        out = []
        for p in data.get("result", {}).get("list", []):
            size = float(p.get("size", 0))
            if abs(size) < 0.001:
                continue
            side = p.get("side", "")
            direction = "LONG" if side == "Buy" else "SHORT"
            entry = float(p.get("avgPrice", 0))
            out.append(
                {
                    "id": f"bybit_{p['symbol']}",
                    "symbol": p["symbol"],
                    "direction": direction,
                    "amount_usd": abs(size) * entry,
                    "leverage": int(float(p.get("leverage", "1"))),
                    "entry_price": entry,
                    "pnl_usd": float(p.get("unrealisedPnl", 0)),
                    "status": "open",
                    "source": "bybit",
                }
            )
        return out
    except Exception as e:
        log.warning("Bybit sync: %s", e)
        return []


def bybit_place_order(direction: str, amount_usd: float, symbol="BTCUSDT"):
    if not BYBIT_API_KEY:
        return {"error": "no_api_key"}
    try:
        cur = fetch_price(symbol)
        qty = str(max(round(amount_usd / cur, 4), 0.001))
        params = {
            "category": "linear",
            "symbol": symbol,
            "side": "Buy" if direction == "LONG" else "Sell",
            "orderType": "Market",
            "qty": qty,
            "timeInForce": "IOC",
            "positionIdx": 0,
        }
        r = _bybit_post("/v5/order/create", params)
        r.raise_for_status()
        data = r.json()
        if data.get("retCode", -1) != 0:
            return {"error": data.get("retMsg", "unknown")}
        return data.get("result", {})
    except Exception as e:
        return {"error": str(e)}


def bybit_close_order(symbol="BTCUSDT"):
    if not BYBIT_API_KEY:
        return {"error": "no_api_key"}
    pos = bybit_futures_positions(symbol)
    for p in pos:
        side = "Sell" if p["direction"] == "LONG" else "Buy"
        try:
            params = {
                "category": "linear",
                "symbol": symbol,
                "side": side,
                "orderType": "Market",
                "qty": str(max(round(p["amount_usd"] / p["entry_price"], 4), 0.001)),
                "timeInForce": "IOC",
                "positionIdx": 0,
                "reduceOnly": True,
            }
            r = _bybit_post("/v5/order/create", params)
            r.raise_for_status()
            data = r.json()
            if data.get("retCode", -1) != 0:
                return {"error": data.get("retMsg", "unknown")}
            return data.get("result", {})
        except Exception as e:
            return {"error": str(e)}
    return {"error": "no_position"}


# ── POSITIONS (persistées en JSON) ────────────────────────────────────────────


def load_positions():
    if POSITIONS_FILE.exists():
        return json.loads(POSITIONS_FILE.read_text())
    return []


def save_positions(positions):
    POSITIONS_FILE.write_text(json.dumps(positions, indent=2))


_positions = load_positions()
_pos_lock = threading.Lock()

# ── AUTO-TRADER CONFIG ─────────────────────────────────────────────────────────

_DEFAULT_SYMBOLS = [
    "BTCUSDT",
    "ETHUSDT",
    "SOLUSDT",
    "XRPUSDT",
    "DOGEUSDT",
    "ADAUSDT",
    "AVAXUSDT",
    "LINKUSDT",
    "DOTUSDT",
    "MATICUSDT",
]

_AUTO_CONFIG = {
    "enabled": os.environ.get("RETA_AUTO_TRADE", "0") == "1",
    "max_risk_pct": float(os.environ.get("RETA_MAX_RISK", "2.0")),
    "capital_usd": float(os.environ.get("RETA_CAPITAL", "1000")),
    "kelly_frac": float(os.environ.get("RETA_KELLY_FRAC", "0.5")),
    "trail_atr_mult": float(os.environ.get("RETA_TRAIL_ATR", "2.0")),
    "trailing_active": True,
    "auto_open": True,
    "symbols": os.environ.get("RETA_SYMBOLS", ",".join(_DEFAULT_SYMBOLS)).split(","),
    "stats": {"trades": 0, "wins": 0, "losses": 0, "pnl_total": 0.0},
    "active_symbol": "BTCUSDT",
}

# ── CACHE GLOBAL ──────────────────────────────────────────────────────────────

_cache = {"symbols": {}, "ts": 0}
CACHE_TTL = 5

# ── BYBIT PUBLIC DATA ─────────────────────────────────────────────────────────

_BYBIT_KLINE_INTERVAL = {"1h": "60", "15m": "15", "4h": "240", "1d": "D"}


def fetch_klines(symbol="BTCUSDT", interval="1h", limit=300):
    bybit_int = _BYBIT_KLINE_INTERVAL.get(interval, "60")
    url = (
        f"https://api.bybit.com/v5/market/kline"
        f"?category=linear&symbol={symbol}&interval={bybit_int}&limit={limit}"
    )
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    data = r.json()
    if data.get("retCode", -1) != 0:
        raise RuntimeError(f"Bybit kline error: {data.get('retMsg', '')}")
    rows = data.get("result", {}).get("list", [])
    times, opens, highs, lows, closes = [], [], [], [], []
    for k in reversed(rows):
        times.append(int(k[0])); opens.append(float(k[1]))
        highs.append(float(k[2])); lows.append(float(k[3]))
        closes.append(float(k[4]))
    return dict(times=times, opens=opens, highs=highs, lows=lows, closes=closes)
    times, opens, highs, lows, closes = [], [], [], [], []
    for k in reversed(rows):
        times.append(int(k[0]))
        opens.append(float(k[1]))
        highs.append(float(k[2]))
        lows.append(float(k[3]))
        closes.append(float(k[4]))
    return dict(times=times, opens=opens, highs=highs, lows=lows, closes=closes)


def fetch_price(symbol="BTCUSDT"):
    try:
        url = f"https://api.bybit.com/v5/market/tickers?category=linear&symbol={symbol}"
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        data = r.json()
        if data.get("retCode", -1) != 0:
            raise RuntimeError(f"Bybit ticker error: {data.get('retMsg', '')}")
        return float(data["result"]["list"][0]["lastPrice"])
    except Exception:
        data = _cache.get("symbols", {}).get(symbol, {})
        prix = data.get("prix", [])
        if prix:
            return float(prix[-1])
        raise


def calc_atr(highs, lows, closes, period=14):
    tr = []
    for i in range(1, len(closes)):
        hl = highs[i] - lows[i]
        hc = abs(highs[i] - closes[i - 1])
        lc = abs(lows[i] - closes[i - 1])
        tr.append(max(hl, hc, lc))
    if len(tr) < period:
        if not tr:
            return 0.0
        return sum(tr) / len(tr)
    atr = sum(tr[:period]) / period
    for i in range(period, len(tr)):
        atr = (atr * (period - 1) + tr[i]) / period
    return atr


def calc_kelly_frac(stats):
    trades = stats.get("trades", 0)
    if trades < 5:
        return 0.25
    wins = stats.get("wins", 0)
    losses = stats.get("losses", 0)

    win_rate = wins / trades if trades else 0.5
    avg_win = 0
    avg_loss = 0

    if wins > 0:
        total_pnl = stats.get("pnl_total", 0.0)
        avg_win = total_pnl / wins
        if losses > 0:
            total_loss_pnl = -total_pnl if total_pnl < 0 else total_pnl * 0.5
            avg_loss = total_loss_pnl / losses
        else:
            avg_loss = avg_win * 0.5
    else:
        avg_win = 1.0
        avg_loss = 1.0

    if avg_loss <= 0:
        avg_loss = avg_win * 0.5

    b = avg_win / avg_loss
    f_star = (win_rate * b - (1 - win_rate)) / b if b > 0 else 0
    return max(0.0, min(f_star, 0.9))


# ── ANALYSE RETA v1.4 ─────────────────────────────────────────────────────────


def analyse(closes, times, symbol="BTCUSDT"):
    prix = np.array(closes, dtype=float)
    n = len(prix)
    log_prix = np.log(prix)
    log_ret = np.diff(log_prix, prepend=log_prix[0])

    # RETAReferential v1.4 — bound quadratique conservatif
    ref = RETAReferential(
        version="v1.4", delta_log_max=0.20, eps=0.0008, window=24, t_confirm=12
    )
    ref.fit(prix)

    z_est = ref.z_est
    z_moy = ref.z_moy
    p_var = ref.p_var
    phases_arr = ref.phases
    P_inf = ref.P_inf
    log_pred = ref.log_pred
    prix_pred = np.exp(log_pred)
    erreur = (prix - prix_pred) / prix_pred * 100

    # PI sur tendance via reta
    t = np.arange(n, dtype=float)
    coeffs = np.polyfit(t, log_prix, 1)
    tendance = np.polyval(coeffs, t)
    from reta.pi import PIRegulator

    pi = PIRegulator(kp=0.12, ki=0.002, integral_clip=10)
    e_pi = np.zeros(n)
    u_pi = np.zeros(n)
    for i in range(n):
        e_pi[i] = log_prix[i] - tendance[i]
        u_pi[i] = pi.step(e_pi[i])

    # Bull-runs (depuis les phases du RETAReferential)
    bull_zones = []
    i = 0
    while i < n:
        if phases_arr[i] == 1:
            debut = i
            while i < n and phases_arr[i] == 1:
                i += 1
            fin = min(i, n - 1)
            eps_l = max(float(z_moy[debut : fin + 1].mean()), 1e-6)
            ymax_i = debut + int(np.argmax(log_prix[debut : fin + 1]))
            t_r = (log_prix[ymax_i] - log_prix[debut]) / eps_l
            bull_zones.append(
                {
                    "debut_idx": debut,
                    "fin_idx": fin,
                    "t_debut": times[debut],
                    "t_fin": times[fin],
                    "t_rup": round(t_r, 1),
                    "t_reel": fin - debut,
                    "eps": round(eps_l, 6),
                    "prix_pic": round(float(prix[ymax_i]), 2),
                    "ratio": round((fin - debut) / t_r * 100, 1) if t_r > 0 else 0,
                }
            )
        else:
            i += 1

    # Supports/résistances simples
    supports, resistances = [], []
    w = 20
    for j in range(w, n - w):
        if all(prix[j] <= prix[j - k] for k in range(1, w + 1)) and all(
            prix[j] <= prix[j + k] for k in range(1, w + 1)
        ):
            supports.append(round(float(prix[j]), 0))
        if all(prix[j] >= prix[j - k] for k in range(1, w + 1)) and all(
            prix[j] >= prix[j + k] for k in range(1, w + 1)
        ):
            resistances.append(round(float(prix[j]), 0))
    cur = float(prix[-1])
    supports = sorted(supports, key=lambda x: abs(x - cur))[:3]
    resistances = sorted(resistances, key=lambda x: abs(x - cur))[:3]

    # ── PRÉDICTION FUTURE (1h = 60min) ─────────────────────────────────
    pred_1h = float(ref.predict(steps=2)[-1])  # index 0=current, 1=prédiction
    pred_ts = int(times[-1]) + 3600_000  # +1h en ms
    delta_pct_pred = round((pred_1h - float(prix[-1])) / float(prix[-1]) * 100, 2)

    # ── LOG ────────────────────────────────────────────────────────────
    log.info("═" * 60)
    log.info("%s  |  RETA %s", symbol, ref.version)
    log.info(
        "Prix: $%.2f  (%.3f%%)",
        float(prix[-1]),
        float((prix[-1] - prix[-2]) / prix[-2] * 100),
    )
    log.info(
        "Phase: %s  |  z̄=%.6f  |  ż=%.6f  |  ε=%.6f",
        ref.phase,
        ref.z_last,
        getattr(ref, "dz_last", 0.0),
        ref.eps_cur,
    )
    if "v1.4" in ref.version and getattr(ref, "dz_last", 0.0) > 0:
        log.info("Borne: QUADRATIQUE v1.4  |  t_rup ≥ %.1f barres", ref.t_rup)
    else:
        log.info("Borne: LINÉAIRE (ż≤0 ou v1.3)  |  t_rup ≥ %.1f barres", ref.t_rup)
    log.info("Prédiction 1h: $%.2f  (%+.2f%%)", pred_1h, delta_pct_pred)
    log.info(
        "P∞ Kalman: %.6f  |  %d barres analysées  |  %d bull-run(s) détecté(s)",
        P_inf,
        n,
        len(bull_zones),
    )
    log.info("═" * 60)

    return {
        "times": [int(t) for t in times],
        "prix": [round(float(p), 2) for p in prix],
        "prix_pred": [round(float(p), 2) for p in prix_pred],
        "prix_pred_1h": round(pred_1h, 2),
        "time_pred_1h": pred_ts,
        "delta_pct_pred": delta_pct_pred,
        "erreur": [round(float(e), 4) for e in erreur],
        "z_est": [round(float(z), 6) for z in z_est],
        "z_moy": [round(float(z), 6) for z in z_moy],
        "p_var": [round(float(p), 8) for p in p_var],
        "e_pi": [round(float(e), 6) for e in e_pi],
        "u_pi": [round(float(u), 6) for u in u_pi],
        "phases": [int(p) for p in phases_arr],
        "P_inf": round(P_inf, 8),
        "phase": ref.phase,
        "z_last": round(ref.z_last, 6),
        "dz_last": round(getattr(ref, "dz_last", 0.0), 6),
        "version": ref.version,
        "eps_seuil": ref.eps,
        "t_rup": round(ref.t_rup, 1),
        "bull_zones": bull_zones,
        "prix_cur": round(float(prix[-1]), 2),
        "delta_pct": round(float((prix[-1] - prix[-2]) / prix[-2] * 100), 3),
        "supports": sorted(supports, reverse=True),
        "resistances": sorted(resistances),
    }


# ── CACHE THREAD ──────────────────────────────────────────────────────────────


def refresh_cache():
    global _cache
    while True:
        try:
            symbols = _AUTO_CONFIG["symbols"]
            out = {}
            for sym in symbols:
                try:
                    raw = fetch_klines(sym, "1h", 300)
                    result = analyse(raw["closes"], raw["times"], sym)
                    out[sym] = result
                except Exception as e2:
                    log.warning("[cache] %s: %s", sym, e2)
            _cache = {"symbols": out, "ts": time.time()}
        except Exception as e:
            log.warning("[cache] %s", e)
        time.sleep(CACHE_TTL)


threading.Thread(target=refresh_cache, daemon=True).start()
time.sleep(2)
if _AUTO_CONFIG["enabled"]:
    threading.Thread(target=auto_trade_loop, daemon=True).start()
    threading.Thread(target=trailing_stop_loop, daemon=True).start()
    log.info(
        "Auto-Trader RETA actif (%d symboles, risk=%.1f%%, capital=$%.0f, Kelly=%.0f%%, trail=%.1f×ATR)",
        len(_AUTO_CONFIG["symbols"]),
        _AUTO_CONFIG["max_risk_pct"],
        _AUTO_CONFIG["capital_usd"],
        _AUTO_CONFIG["kelly_frac"] * 100,
        _AUTO_CONFIG["trail_atr_mult"],
    )

# ── POSITION P&L ──────────────────────────────────────────────────────────────


def calc_pnl(pos, cur_price):
    if pos["direction"] == "LONG":
        pct = (cur_price - pos["entry_price"]) / pos["entry_price"]
    else:
        pct = (pos["entry_price"] - cur_price) / pos["entry_price"]
    pnl_usd = pct * pos["amount_usd"] * pos["leverage"]
    pnl_pct = pct * pos["leverage"] * 100
    # TP/SL check
    if pos["direction"] == "LONG":
        tp_hit = pos.get("tp") and cur_price >= pos["tp"]
        sl_hit = pos.get("sl") and cur_price <= pos["sl"]
    else:
        tp_hit = pos.get("tp") and cur_price <= pos["tp"]
        sl_hit = pos.get("sl") and cur_price >= pos["sl"]
    return round(pnl_usd, 2), round(pnl_pct, 3), bool(tp_hit), bool(sl_hit)


# ── AUTO-TRADER RETA ─────────────────────────────────────────────────────────


def auto_trade_loop():
    """Agent autonome : analyse RETA → ouvre/ferme positions sur Bybit (multi-symbol)."""
    global _positions, _cache
    last_phase = {sym: None for sym in _AUTO_CONFIG["symbols"]}
    while True:
        time.sleep(10)
        if not _AUTO_CONFIG["enabled"]:
            continue
        caches = _cache.get("symbols", {})
        if not caches:
            continue

        for sym in _AUTO_CONFIG["symbols"]:
            data = caches.get(sym)
            if not data:
                continue

            phase = data.get("phase", "NEUTRE")
            prix = data.get("prix_cur", 0)
            z = data.get("z_last", 0)
            dz = data.get("dz_last", 0)

            with _pos_lock:
                open_pos = [
                    p
                    for p in _positions
                    if p["status"] == "open"
                    and p.get("source") == "auto"
                    and p.get("symbol") == sym
                ]

            # Pas de changement de phase → prochain symbole
            if phase == last_phase[sym]:
                continue
            last_phase[sym] = phase
            log.info("[AUTO] %s | Phase: %s  z̄=%.6f  ż=%.6f", sym, phase, z, dz)

            # Fermer la position opposée si elle existe
            if open_pos:
                pos = open_pos[0]
                if (
                    (phase == "BEAR" and pos["direction"] == "LONG")
                    or (phase == "BULL" and pos["direction"] == "SHORT")
                    or phase == "NEUTRE"
                ):
                    log.info(
                        "[AUTO] %s | Clôture %s (phase → %s)",
                        sym,
                        pos["direction"],
                        phase,
                    )
                    pnl_usd, pnl_pct, _, _ = calc_pnl(pos, prix)
                    pos["status"] = "closed"
                    pos["close_ts"] = int(time.time() * 1000)
                    pos["close_price"] = prix
                    pos["pnl_usd"] = pnl_usd
                    pos["pnl_pct"] = pnl_pct
                    pos["close_reason"] = "phase_change"
                    _AUTO_CONFIG["stats"]["trades"] += 1
                    _AUTO_CONFIG["stats"]["pnl_total"] += pnl_usd
                    if pnl_usd > 0:
                        _AUTO_CONFIG["stats"]["wins"] += 1
                    else:
                        _AUTO_CONFIG["stats"]["losses"] += 1
                    log.info(
                        "[AUTO] P&L: %.2f$ (%.2f%%)  Total: %.2f$  WinRate: %.0f%%",
                        pnl_usd,
                        pnl_pct,
                        _AUTO_CONFIG["stats"]["pnl_total"],
                        _AUTO_CONFIG["stats"]["wins"]
                        / _AUTO_CONFIG["stats"]["trades"]
                        * 100
                        if _AUTO_CONFIG["stats"]["trades"]
                        else 0,
                    )
                    save_positions(_positions)
                    if phase == "NEUTRE":
                        continue

            # Ouvrir une position dans la direction de la phase
            if phase in ("BULL", "BEAR") and not open_pos and _AUTO_CONFIG["auto_open"]:
                # Kelly sizing dynamique
                kelly_f = calc_kelly_frac(_AUTO_CONFIG["stats"])
                kelly_f *= _AUTO_CONFIG["kelly_frac"]
                confidence = (
                    1.0 / (1.0 + abs(data.get("P_inf", 0.0)) * 1000.0)
                    if abs(data.get("P_inf", 0.0)) > 0
                    else 1.0
                )
                risk_pct = _AUTO_CONFIG["max_risk_pct"] * kelly_f * confidence / 100.0
                risk_pct = max(
                    0.01, min(risk_pct, _AUTO_CONFIG["max_risk_pct"] / 100.0)
                )
                risk_usd = (
                    _AUTO_CONFIG["capital_usd"]
                    * risk_pct
                    / max(len(_AUTO_CONFIG["symbols"]), 1)
                )
                direction = "LONG" if phase == "BULL" else "SHORT"

                # Trailing stop : initialiser avec ATR
                trail_distance = 0
                try:
                    klines = fetch_klines(sym, "1h", 20)
                    atr_val = calc_atr(
                        klines["highs"], klines["lows"], klines["closes"], 14
                    )
                    trail_distance = atr_val * _AUTO_CONFIG["trail_atr_mult"]
                except Exception:
                    trail_distance = prix * 0.01

                if direction == "LONG":
                    init_sl = round(prix - trail_distance, 2)
                else:
                    init_sl = round(prix + trail_distance, 2)

                pos = {
                    "id": int(time.time() * 1000) + hash(sym) % 10000,
                    "symbol": sym,
                    "direction": direction,
                    "amount_usd": risk_usd,
                    "leverage": 1,
                    "entry_price": prix,
                    "open_ts": int(time.time() * 1000),
                    "reta_signal": phase,
                    "status": "open",
                    "source": "auto",
                    "sl": init_sl,
                    "trail_high": prix,
                    "trail_low": prix,
                    "trail_active": True,
                }
                if bool(BYBIT_API_KEY):
                    result = bybit_place_order(direction, risk_usd, sym)
                    if "error" in result:
                        log.warning("[AUTO] %s order failed: %s", sym, result["error"])
                        continue
                    pos["entry_price"] = prix
                    pos["order_id"] = result.get("orderId", "")
                with _pos_lock:
                    _positions.append(pos)
                    save_positions(_positions)
                log.info(
                    "[AUTO] %s | Ouverture %s $%.0f (z̄=%.6f, ż=%.6f)",
                    sym,
                    direction,
                    risk_usd,
                    z,
                    dz,
                )


# ── TRAILING STOP LOOP ────────────────────────────────────────────────────────


def trailing_stop_loop():
    global _positions
    while True:
        time.sleep(5)
        if not _AUTO_CONFIG["enabled"] or not _AUTO_CONFIG["trailing_active"]:
            continue

        with _pos_lock:
            for p in _positions:
                if p["status"] != "open" or p.get("source") != "auto":
                    continue
                if not p.get("trail_active"):
                    continue

                sym = p.get("symbol", "BTCUSDT")
                try:
                    klines = fetch_klines(sym, "1h", 20)
                    atr_val = calc_atr(
                        klines["highs"], klines["lows"], klines["closes"], 14
                    )
                    if atr_val <= 0:
                        continue
                    trail_dist = atr_val * _AUTO_CONFIG["trail_atr_mult"]
                    cur_price = fetch_price(sym)
                except Exception:
                    continue

                trail_high = p.get("trail_high", p["entry_price"])
                trail_low = p.get("trail_low", p["entry_price"])

                if p["direction"] == "LONG":
                    if cur_price > trail_high:
                        trail_high = cur_price
                    p["trail_high"] = trail_high
                    new_sl = round(trail_high - trail_dist, 2)
                    if new_sl > p.get("sl", 0):
                        p["sl"] = new_sl
                    if cur_price <= p["sl"]:
                        log.info(
                            "[TRAIL] STOP HIT %s LONG entry=$%.2f sl=$%.2f cur=$%.2f",
                            sym,
                            p["entry_price"],
                            p["sl"],
                            cur_price,
                        )
                        pnl_usd, pnl_pct, _, _ = calc_pnl(p, cur_price)
                        p["status"] = "closed"
                        p["close_ts"] = int(time.time() * 1000)
                        p["close_price"] = cur_price
                        p["pnl_usd"] = pnl_usd
                        p["pnl_pct"] = pnl_pct
                        p["close_reason"] = "trailing_stop"
                        _AUTO_CONFIG["stats"]["trades"] += 1
                        _AUTO_CONFIG["stats"]["pnl_total"] += pnl_usd
                        if pnl_usd > 0:
                            _AUTO_CONFIG["stats"]["wins"] += 1
                        else:
                            _AUTO_CONFIG["stats"]["losses"] += 1
                        log.info(
                            "[AUTO] P&L: %.2f$ (%.2f%%)  Total: %.2f$  WinRate: %.0f%%",
                            pnl_usd,
                            pnl_pct,
                            _AUTO_CONFIG["stats"]["pnl_total"],
                            _AUTO_CONFIG["stats"]["wins"]
                            / _AUTO_CONFIG["stats"]["trades"]
                            * 100
                            if _AUTO_CONFIG["stats"]["trades"]
                            else 0,
                        )
                        save_positions(_positions)
                else:
                    if cur_price < trail_low:
                        trail_low = cur_price
                    p["trail_low"] = trail_low
                    new_sl = round(trail_low + trail_dist, 2)
                    if new_sl < p.get("sl", 999999):
                        p["sl"] = new_sl
                    if cur_price >= p["sl"]:
                        log.info(
                            "[TRAIL] STOP HIT %s SHORT entry=$%.2f sl=$%.2f cur=$%.2f",
                            sym,
                            p["entry_price"],
                            p["sl"],
                            cur_price,
                        )
                        pnl_usd, pnl_pct, _, _ = calc_pnl(p, cur_price)
                        p["status"] = "closed"
                        p["close_ts"] = int(time.time() * 1000)
                        p["close_price"] = cur_price
                        p["pnl_usd"] = pnl_usd
                        p["pnl_pct"] = pnl_pct
                        p["close_reason"] = "trailing_stop"
                        _AUTO_CONFIG["stats"]["trades"] += 1
                        _AUTO_CONFIG["stats"]["pnl_total"] += pnl_usd
                        if pnl_usd > 0:
                            _AUTO_CONFIG["stats"]["wins"] += 1
                        else:
                            _AUTO_CONFIG["stats"]["losses"] += 1
                        log.info(
                            "[AUTO] P&L: %.2f$ (%.2f%%)  Total: %.2f$  WinRate: %.0f%%",
                            pnl_usd,
                            pnl_pct,
                            _AUTO_CONFIG["stats"]["pnl_total"],
                            _AUTO_CONFIG["stats"]["wins"]
                            / _AUTO_CONFIG["stats"]["trades"]
                            * 100
                            if _AUTO_CONFIG["stats"]["trades"]
                            else 0,
                        )
                        save_positions(_positions)


# ── SYNC THREAD (Bybit → positions.json) ────────────────────────────────────


def sync_bybit_positions():
    global _positions
    while True:
        try:
            bpos = []
            for sym in _AUTO_CONFIG["symbols"]:
                try:
                    bpos.extend(bybit_futures_positions(sym))
                except Exception:
                    continue
            if not bpos:
                time.sleep(30)
                continue
            with _pos_lock:
                manual = [p for p in _positions if p.get("source") != "bybit"]
                _positions = manual + bpos
                save_positions(_positions)
                log.info("Bybit sync: %d position(s) active(s)", len(bpos))
        except Exception as e:
            log.warning("Bybit sync error: %s", e)
        time.sleep(30)


if BYBIT_API_KEY:
    threading.Thread(target=sync_bybit_positions, daemon=True).start()
    log.info(
        "Bybit API connectée — synchronisation active (%d symboles)",
        len(_AUTO_CONFIG["symbols"]),
    )
else:
    log.info("Pas de clé Bybit (BYBIT_API_KEY) — mode manuel")

# ── API ROUTES ────────────────────────────────────────────────────────────────


@app.route("/api/data")
def api_data():
    sym = request.args.get("symbol", _AUTO_CONFIG.get("active_symbol", "BTCUSDT"))
    symbols = _cache.get("symbols", {})
    if not symbols:
        return jsonify({"error": "loading"}), 503
    data = symbols.get(sym)
    if not data:
        return jsonify(
            {"error": f"symbol {sym} not found", "symbols": list(symbols.keys())}
        ), 404
    data["symbols"] = list(symbols.keys())
    data["active_symbol"] = sym
    return jsonify(data)


@app.route("/api/symbols")
def api_symbols():
    return jsonify(
        {
            "symbols": _AUTO_CONFIG["symbols"],
            "active": _AUTO_CONFIG.get("active_symbol", "BTCUSDT"),
        }
    )


@app.route("/api/price")
def api_price():
    try:
        sym = request.args.get("symbol", "BTCUSDT")
        p = fetch_price(sym)
        return jsonify({"price": p, "symbol": sym, "ts": int(time.time() * 1000)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/position/open", methods=["POST"])
def position_open():
    global _positions
    body = request.json
    sym = body.get("symbol", "BTCUSDT")
    caches = _cache.get("symbols", {})
    cur = caches.get(sym, {}).get("prix_cur", 0) if caches else 0
    use_bybit = body.get("use_bybit", True) and bool(BYBIT_API_KEY)
    entry = (
        float(body.get("entry_price") or cur)
        if cur
        else float(body.get("entry_price", 0))
    )

    pos = {
        "id": int(time.time() * 1000),
        "symbol": sym,
        "direction": body["direction"],
        "amount_usd": float(body["amount_usd"]),
        "leverage": float(body.get("leverage", 1)),
        "entry_price": entry,
        "tp": float(body["tp"]) if body.get("tp") not in (None, "", 0) else None,
        "sl": float(body["sl"]) if body.get("sl") not in (None, "", 0) else None,
        "open_ts": int(time.time() * 1000),
        "reta_signal": body.get("reta_signal", "MANUEL"),
        "status": "open",
        "source": "bybit" if use_bybit else "manual",
    }
    if use_bybit:
        result = bybit_place_order(pos["direction"], pos["amount_usd"], sym)
        if "error" in result:
            return jsonify({"error": result["error"]}), 500
        pos["entry_price"] = entry
        pos["order_id"] = result.get("orderId", "")
    with _pos_lock:
        _positions.append(pos)
        save_positions(_positions)
    src = "Bybit" if use_bybit else "Manuelle"
    log.info(
        "Position %s ouverte (%s): %s %s $%.0f x%.0f",
        src,
        sym,
        pos["direction"],
        pos["direction"],
        pos["amount_usd"],
        pos["leverage"],
    )
    return jsonify({"ok": True, "position": pos})


@app.route("/api/position/close/<int:pos_id>", methods=["POST"])
def position_close(pos_id):
    global _positions
    with _pos_lock:
        for p in _positions:
            if p["id"] == pos_id and p["status"] == "open":
                sym = p.get("symbol", "BTCUSDT")
                if p.get("source") == "bybit" and bool(BYBIT_API_KEY):
                    result = bybit_close_order(sym)
                    if "error" in result and "no_position" not in str(result):
                        log.warning("Bybit close error: %s", result["error"])
                cur = _cache.get("symbols", {}).get(sym, {}).get("prix_cur", 0)
                pnl_usd, pnl_pct, _, _ = (
                    calc_pnl(p, cur) if cur else (0, 0, False, False)
                )
                p["status"] = "closed"
                p["close_ts"] = int(time.time() * 1000)
                p["close_price"] = cur if cur else p["entry_price"]
                p["pnl_usd"] = pnl_usd
                p["pnl_pct"] = pnl_pct
                p["close_reason"] = "manual_close"
                save_positions(_positions)
                log.info(
                    "Position fermée: %s %s %s  P&L=%.2f$ (%.2f%%)",
                    sym,
                    p.get("direction", "?"),
                    p.get("source", "?"),
                    pnl_usd,
                    pnl_pct,
                )
                return jsonify({"ok": True, "pnl_usd": pnl_usd, "pnl_pct": pnl_pct})
    return jsonify({"error": "not found"}), 404


@app.route("/api/auto/status")
def auto_status():
    return jsonify(
        {
            "enabled": _AUTO_CONFIG["enabled"],
            "stats": _AUTO_CONFIG["stats"],
            "max_risk_pct": _AUTO_CONFIG["max_risk_pct"],
            "capital_usd": _AUTO_CONFIG["capital_usd"],
            "kelly_frac": _AUTO_CONFIG["kelly_frac"],
            "trail_atr_mult": _AUTO_CONFIG["trail_atr_mult"],
            "auto_open": _AUTO_CONFIG["auto_open"],
            "trailing_active": _AUTO_CONFIG["trailing_active"],
            "symbols": _AUTO_CONFIG["symbols"],
        }
    )


@app.route("/api/auto/config", methods=["GET", "POST"])
def auto_config():
    if request.method == "POST":
        body = request.json
        for key in (
            "max_risk_pct",
            "capital_usd",
            "kelly_frac",
            "trail_atr_mult",
            "auto_open",
            "trailing_active",
        ):
            if key in body:
                if key in ("auto_open", "trailing_active"):
                    _AUTO_CONFIG[key] = bool(body[key])
                else:
                    _AUTO_CONFIG[key] = float(body[key])
        log.info("[AUTO] Config updated: %s", body)
        return jsonify(
            {
                "ok": True,
                "config": {
                    k: _AUTO_CONFIG[k]
                    for k in (
                        "enabled",
                        "max_risk_pct",
                        "capital_usd",
                        "kelly_frac",
                        "trail_atr_mult",
                        "auto_open",
                        "trailing_active",
                        "symbols",
                    )
                },
            }
        )
    return jsonify(
        {
            k: _AUTO_CONFIG[k]
            for k in (
                "enabled",
                "max_risk_pct",
                "capital_usd",
                "kelly_frac",
                "trail_atr_mult",
                "auto_open",
                "trailing_active",
                "symbols",
            )
        }
    )


@app.route("/api/auto/toggle", methods=["POST"])
def auto_toggle():
    _AUTO_CONFIG["enabled"] = not _AUTO_CONFIG["enabled"]
    log.info("[AUTO] Toggled %s", "ON" if _AUTO_CONFIG["enabled"] else "OFF")
    return jsonify({"enabled": _AUTO_CONFIG["enabled"]})


@app.route("/api/position/list")
def position_list():
    caches = _cache.get("symbols", {})
    result = []
    with _pos_lock:
        for p in _positions:
            item = dict(p)
            if p["status"] == "open":
                sym = p.get("symbol", "BTCUSDT")
                cur = caches.get(sym, {}).get("prix_cur", 0)
                if cur:
                    pnl_usd, pnl_pct, tp_hit, sl_hit = calc_pnl(p, cur)
                    item["pnl_usd"] = pnl_usd
                    item["pnl_pct"] = pnl_pct
                    item["tp_hit"] = tp_hit
                    item["sl_hit"] = sl_hit
                    item["cur_price"] = cur
            item["source"] = p.get("source", "manual")
            result.append(item)
    return jsonify(result)


# ── HTML ──────────────────────────────────────────────────────────────────────

HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>RETA · BTC Dashboard</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600;700&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns@3.0.0/dist/chartjs-adapter-date-fns.bundle.min.js"></script>
<style>
/* ── DESIGN TOKENS ─────────────────────────────────────────── */
:root {
  --bg:         #F5F6FA;
  --surface:    #FFFFFF;
  --surface-2:  #F0F1F7;
  --border:     #E4E6F0;
  --border-2:   #CDD0E3;

  --text-1:     #1A1F36;
  --text-2:     #4A5080;
  --text-3:     #8A90B0;

  --orange:     #F7931A;
  --orange-dim: rgba(247,147,26,.12);
  --orange-glow:rgba(247,147,26,.25);

  --reta:       #6C63FF;
  --reta-dim:   rgba(108,99,255,.10);

  --green:      #00A878;
  --green-dim:  rgba(0,168,120,.12);
  --red:        #E53E3E;
  --red-dim:    rgba(229,62,62,.12);
  --yellow:     #D69E2E;
  --yellow-dim: rgba(214,158,46,.12);

  --shadow-sm:  0 1px 4px rgba(26,31,54,.06);
  --shadow-md:  0 4px 20px rgba(26,31,54,.09);
  --shadow-lg:  0 8px 32px rgba(26,31,54,.12);

  --radius:     12px;
  --radius-sm:  8px;

  --mono: 'JetBrains Mono', monospace;
  --sans: 'Inter', system-ui, sans-serif;
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: var(--sans);
  background: var(--bg);
  color: var(--text-1);
  min-height: 100vh;
  font-size: 13.5px;
  line-height: 1.5;
}

/* ── SCROLLBAR ─────────────────────────────────────────────── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--border-2); border-radius: 3px; }

/* ── HEADER ─────────────────────────────────────────────────── */
.header {
  position: sticky; top: 0; z-index: 100;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  box-shadow: var(--shadow-sm);
  display: flex; align-items: center;
  padding: 0 24px; height: 60px; gap: 24px;
}

.header__logo {
  display: flex; align-items: center; gap: 10px;
  font-weight: 800; font-size: 1rem; color: var(--text-1);
  letter-spacing: -.3px; white-space: nowrap;
}
.header__logo-badge {
  background: var(--orange); color: #fff;
  font-size: .65rem; font-weight: 700;
  padding: 2px 7px; border-radius: 20px;
  letter-spacing: .5px;
}

.header__price-block { display: flex; align-items: baseline; gap: 8px; }
.header__price {
  font-family: var(--mono); font-size: 1.5rem; font-weight: 700;
  color: var(--text-1); letter-spacing: -.5px;
  transition: color .3s;
}
.header__delta {
  font-family: var(--mono); font-size: .85rem; font-weight: 600;
  padding: 2px 8px; border-radius: 6px;
}
.delta-up   { background: var(--green-dim); color: var(--green); }
.delta-down { background: var(--red-dim);   color: var(--red);   }

.header__divider { width: 1px; height: 28px; background: var(--border); }

.header__meta { color: var(--text-3); font-size: .75rem; }

.header__live {
  margin-left: auto; display: flex; align-items: center; gap: 8px;
  font-size: .75rem; color: var(--text-3);
}
.pulse-dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: var(--green); flex-shrink: 0;
  animation: pulse-anim 2s ease-in-out infinite;
}
@keyframes pulse-anim {
  0%,100% { box-shadow: 0 0 0 0 rgba(0,168,120,.5); }
  50%      { box-shadow: 0 0 0 5px rgba(0,168,120,0); }
}

/* ── LAYOUT ──────────────────────────────────────────────────── */
.layout {
  display: grid;
  grid-template-columns: 300px 1fr;
  grid-template-rows: auto;
  gap: 0;
  min-height: calc(100vh - 60px);
}

/* ── SIDEBAR ─────────────────────────────────────────────────── */
.sidebar {
  border-right: 1px solid var(--border);
  background: var(--surface);
  position: sticky;
  top: 60px;
  height: calc(100vh - 60px);
  overflow-y: auto;
  overflow-x: hidden;
  padding: 16px 14px 24px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  scrollbar-width: thin;
  scrollbar-color: var(--border-2) transparent;
}

/* Cards dans la sidebar : padding réduit */
.sidebar .card {
  padding: 12px 14px;
  border-radius: 10px;
  width: 100%;
  min-width: 0;
}
.sidebar .card__label { margin-bottom: 10px; }

/* Tous les enfants sidebar bornés */
.sidebar * { min-width: 0; max-width: 100%; }

/* Signal ring compact */
.signal-ring-wrap { gap: 4px; }
#signal-ring-svg  { width: 136px; height: 86px; }

/* KPI rows serrés */
.kpi-row { padding: 7px 10px; }
.kpi-row__label { font-size: .75rem; }
.kpi-row__value { font-size: .81rem; }

/* Levels compacts */
.level-item { padding: 5px 9px; font-size: .75rem; }

/* Formulaire : tout en colonne, jamais 2 colonnes dans sidebar */
.pos-form { gap: 8px; }
.pos-form .field-row {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.field label  { font-size: .71rem; }
.field input  { padding: 7px 9px; font-size: .8rem; width: 100%; }
.dir-btn      { padding: 7px; font-size: .78rem; }
.lev-btns     { flex-wrap: wrap; }
.lev-btn      { flex: 1 1 calc(25% - 4px); min-width: 36px; padding: 5px 2px; font-size: .74rem; }
.reta-suggest { font-size: .74rem; padding: 8px 6px; width: 100%; }
.btn-open     { padding: 10px; font-size: .82rem; width: 100%; }

/* Position cards compacts */
.pos-card-item        { padding: 9px 11px; }
.pos-card-item__rows  { gap: 2px 8px; margin-bottom: 6px; }
.pos-card-item__row span:last-child  { font-size: .72rem; }
.pos-card-item__row span:first-child { font-size: .62rem; }
.btn-close { padding: 5px; font-size: .72rem; width: 100%; }

/* ── MAIN ────────────────────────────────────────────────────── */
.main {
  padding: 20px 24px;
  display: flex; flex-direction: column; gap: 16px;
  overflow-x: hidden;
}

/* ── CARD ────────────────────────────────────────────────────── */
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: var(--shadow-sm);
  padding: 16px 18px;
}
.card--flat { box-shadow: none; }

.card__label {
  font-size: .68rem; font-weight: 600; letter-spacing: .8px;
  text-transform: uppercase; color: var(--text-3);
  display: flex; align-items: center; gap: 6px; margin-bottom: 12px;
}
.card__label-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }

/* ── SIGNAL RING ─────────────────────────────────────────────── */
.signal-ring-wrap {
  display: flex; flex-direction: column; align-items: center; gap: 6px;
}
#signal-ring-svg { width: 160px; height: 100px; overflow: visible; }

.ring-track { fill: none; stroke: var(--bg); stroke-width: 10; }
.ring-bear  { fill: none; stroke: var(--red);    stroke-width: 10; stroke-linecap: round; }
.ring-neutral{ fill: none; stroke: var(--yellow); stroke-width: 10; stroke-linecap: round; }
.ring-bull  { fill: none; stroke: var(--green);  stroke-width: 10; stroke-linecap: round; }
.ring-needle { stroke-linecap: round; transition: transform .6s cubic-bezier(.34,1.56,.64,1); }

.signal-label {
  font-size: .72rem; font-weight: 600; letter-spacing: 1px;
  text-transform: uppercase; padding: 3px 12px;
  border-radius: 20px;
}
.signal-label.bull { background: var(--green-dim); color: var(--green); }
.signal-label.bear { background: var(--red-dim);   color: var(--red);   }
.signal-label.neutral { background: var(--yellow-dim); color: var(--yellow); }

.signal-z {
  font-family: var(--mono); font-size: .9rem; font-weight: 600;
  color: var(--text-1);
}

/* ── RANGE SLIDER ────────────────────────────────────────────── */
input[type=range] {
  -webkit-appearance: none; appearance: none;
  height: 4px; border-radius: 2px; background: var(--border);
  outline: none; margin: 4px 0;
}
input[type=range]::-webkit-slider-thumb {
  -webkit-appearance: none; appearance: none;
  width: 14px; height: 14px; border-radius: 50%;
  background: var(--orange); cursor: pointer;
  border: 2px solid #fff; box-shadow: 0 1px 4px rgba(0,0,0,.15);
}
input[type=checkbox] { accent-color: var(--orange); }

/* ── KPI STACK ───────────────────────────────────────────────── */
.kpi-stack { display: flex; flex-direction: column; gap: 2px; }
.kpi-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 9px 12px; border-radius: var(--radius-sm);
  transition: background .15s;
}
.kpi-row:hover { background: var(--surface-2); }
.kpi-row__label { font-size: .78rem; color: var(--text-2); }
.kpi-row__value { font-family: var(--mono); font-size: .85rem; font-weight: 600; color: var(--text-1); }
.kpi-row__value.green { color: var(--green); }
.kpi-row__value.red   { color: var(--red);   }
.kpi-row__value.orange{ color: var(--orange);}

/* ── SUPPORT / RÉSISTANCE ────────────────────────────────────── */
.level-list { display: flex; flex-direction: column; gap: 4px; }
.level-item {
  display: flex; justify-content: space-between; align-items: center;
  padding: 6px 10px; border-radius: 6px; font-family: var(--mono);
  font-size: .78rem;
}
.level-item.res { background: var(--red-dim); color: var(--red); }
.level-item.sup { background: var(--green-dim); color: var(--green); }
.level-item__tag { font-size: .65rem; opacity: .7; letter-spacing: .5px; }

/* ── POSITION FORM ───────────────────────────────────────────── */
.pos-form { display: flex; flex-direction: column; gap: 10px; }

.dir-toggle { display: flex; gap: 6px; }
.dir-btn {
  flex: 1; padding: 8px; border-radius: var(--radius-sm);
  border: 1.5px solid var(--border); background: transparent;
  font-family: var(--sans); font-size: .8rem; font-weight: 600;
  cursor: pointer; transition: all .15s; color: var(--text-2);
}
.dir-btn.long.active  { border-color: var(--green); background: var(--green-dim); color: var(--green); }
.dir-btn.short.active { border-color: var(--red);   background: var(--red-dim);   color: var(--red);   }
.dir-btn:hover:not(.active) { background: var(--surface-2); }

.field { display: flex; flex-direction: column; gap: 4px; }
.field label { font-size: .72rem; color: var(--text-3); font-weight: 500; }
.field input {
  padding: 8px 10px; border-radius: var(--radius-sm);
  border: 1.5px solid var(--border); background: var(--surface);
  font-family: var(--mono); font-size: .83rem; color: var(--text-1);
  outline: none; transition: border-color .15s;
}
.field input:focus { border-color: var(--orange); }

.field-row { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }

.lev-btns { display: flex; gap: 4px; }
.lev-btn {
  flex: 1; padding: 6px 4px; text-align: center;
  border: 1.5px solid var(--border); border-radius: 6px;
  font-size: .75rem; font-weight: 600; cursor: pointer;
  background: transparent; color: var(--text-2); transition: all .15s;
}
.lev-btn.active { border-color: var(--orange); background: var(--orange-dim); color: var(--orange); }

.reta-suggest {
  padding: 7px; background: var(--reta-dim);
  border: 1px solid var(--reta); border-radius: var(--radius-sm);
  color: var(--reta); font-size: .75rem; font-weight: 500;
  cursor: pointer; text-align: center; transition: background .15s;
}
.reta-suggest:hover { background: rgba(108,99,255,.18); }

.btn-open {
  padding: 11px; border-radius: var(--radius-sm);
  border: none; font-family: var(--sans);
  font-size: .85rem; font-weight: 700; cursor: pointer;
  transition: all .15s; letter-spacing: .3px;
}
.btn-open.long  { background: var(--green); color: #fff; }
.btn-open.short { background: var(--red);   color: #fff; }
.btn-open:hover { opacity: .88; transform: translateY(-1px); box-shadow: var(--shadow-md); }
.btn-open:active{ transform: translateY(0); }

/* ── OPEN POSITIONS ──────────────────────────────────────────── */
.pos-list { display: flex; flex-direction: column; gap: 8px; }
.pos-card-item {
  border: 1.5px solid var(--border); border-radius: var(--radius-sm);
  padding: 10px 12px; background: var(--surface);
}
.pos-card-item.profit { border-color: rgba(0,168,120,.3); background: rgba(0,168,120,.03); }
.pos-card-item.loss   { border-color: rgba(229,62,62,.3); background: rgba(229,62,62,.03); }

.pos-card-item__header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 6px;
}
.pos-card-item__dir {
  font-size: .7rem; font-weight: 700; padding: 2px 8px;
  border-radius: 4px; letter-spacing: .5px;
}
.pos-card-item__dir.long  { background: var(--green-dim); color: var(--green); }
.pos-card-item__dir.short { background: var(--red-dim);   color: var(--red);   }
.pos-card-item__pnl {
  font-family: var(--mono); font-size: .9rem; font-weight: 700;
}
.pos-card-item__pnl.up   { color: var(--green); }
.pos-card-item__pnl.down { color: var(--red);   }

.pos-card-item__rows { display: grid; grid-template-columns: 1fr 1fr; gap: 3px 10px; margin-bottom: 8px; }
.pos-card-item__row { display: flex; flex-direction: column; gap: 1px; }
.pos-card-item__row span:first-child { font-size: .65rem; color: var(--text-3); }
.pos-card-item__row span:last-child  { font-family: var(--mono); font-size: .75rem; color: var(--text-1); }

.btn-close {
  width: 100%; padding: 6px; border: 1px solid var(--border);
  border-radius: 6px; background: transparent; font-size: .75rem;
  font-weight: 600; cursor: pointer; color: var(--text-2);
  transition: all .15s;
}
.btn-close:hover { border-color: var(--red); color: var(--red); background: var(--red-dim); }

.tp-sl-hit {
  font-size: .68rem; padding: 2px 6px; border-radius: 4px;
  font-weight: 700; letter-spacing: .5px;
}
.tp-hit { background: var(--green-dim); color: var(--green); }
.sl-hit { background: var(--red-dim);   color: var(--red);   }

/* ── CHARTS ──────────────────────────────────────────────────── */
.chart-wrap { position: relative; }
.chart-main  { height: 280px; }
.chart-sm    { height: 160px; }
.chart-xs    { height: 140px; }

.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; }

/* ── COMMENTARY ──────────────────────────────────────────────── */
.commentary {
  border-left: 3px solid var(--reta);
  background: var(--reta-dim); border-radius: 0 6px 6px 0;
  padding: 9px 12px; font-size: .78rem; color: var(--text-2);
  line-height: 1.6; margin-top: 10px;
}
.commentary.good   { border-color: var(--green);  background: var(--green-dim);  }
.commentary.warn   { border-color: var(--yellow); background: var(--yellow-dim); }
.commentary.danger { border-color: var(--red);    background: var(--red-dim);    }
.commentary b { color: var(--text-1); }

/* ── LEGEND ROW ──────────────────────────────────────────────── */
.legend-row {
  display: flex; flex-wrap: wrap; gap: 12px;
  margin-top: 8px;
}
.leg { display: flex; align-items: center; gap: 5px;
       font-size: .72rem; color: var(--text-3); }
.leg-line { width: 16px; height: 2px; border-radius: 1px; }
.leg-dash { width: 16px; height: 2px; border-radius: 1px;
            background: repeating-linear-gradient(90deg,currentColor 0,currentColor 4px,transparent 4px,transparent 7px); }

/* ── TABLE ───────────────────────────────────────────────────── */
.tbl-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: .78rem; }
th {
  text-align: left; padding: 8px 12px;
  border-bottom: 2px solid var(--border);
  color: var(--text-3); font-weight: 600;
  font-size: .68rem; letter-spacing: .5px; text-transform: uppercase;
  white-space: nowrap;
}
td { padding: 9px 12px; border-bottom: 1px solid var(--border); }
tr:last-child td { border-bottom: none; }
tr:hover td { background: var(--surface-2); }
.badge {
  display: inline-block; padding: 2px 8px; border-radius: 20px;
  font-size: .68rem; font-weight: 700; letter-spacing: .3px;
}
.badge-ok     { background: var(--green-dim);  color: var(--green); }
.badge-warn   { background: var(--yellow-dim); color: var(--yellow);}
.badge-danger { background: var(--red-dim);    color: var(--red);   }

/* ── FORMULA ─────────────────────────────────────────────────── */
.formula {
  font-family: var(--mono); font-size: .75rem;
  background: var(--surface-2); border: 1px solid var(--border);
  border-radius: var(--radius-sm); padding: 8px 12px;
  color: var(--reta); margin: 4px 0;
}

/* ── TOAST ───────────────────────────────────────────────────── */
#toast {
  position: fixed; bottom: 24px; right: 24px; z-index: 999;
  background: var(--text-1); color: #fff;
  padding: 12px 18px; border-radius: var(--radius-sm);
  font-size: .82rem; font-weight: 500;
  box-shadow: var(--shadow-lg);
  transform: translateY(80px); opacity: 0;
  transition: all .3s cubic-bezier(.34,1.56,.64,1);
  pointer-events: none;
}
#toast.show { transform: translateY(0); opacity: 1; }
#toast.good { background: var(--green); }
#toast.bad  { background: var(--red);   }

/* ── LOADER ──────────────────────────────────────────────────── */
#loader {
  position: fixed; inset: 0; background: var(--surface);
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  z-index: 999; gap: 16px;
}
.spinner {
  width: 40px; height: 40px;
  border: 3px solid var(--border);
  border-top-color: var(--orange);
  border-radius: 50%;
  animation: spin .7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ── EMPTY STATE ─────────────────────────────────────────────── */
.empty-state {
  text-align: center; padding: 20px 12px;
  color: var(--text-3); font-size: .8rem;
}
.empty-state__icon { font-size: 1.8rem; margin-bottom: 6px; }

/* ── FOOTER ──────────────────────────────────────────────────── */
footer {
  text-align: center; padding: 14px;
  border-top: 1px solid var(--border);
  font-size: .72rem; color: var(--text-3);
  background: var(--surface);
}
</style>
</head>
<body>

<div id="loader">
  <div class="spinner"></div>
  <div style="color:var(--text-3);font-size:.85rem">Connexion Bybit · Analyse RETA…</div>
</div>
<div id="toast"></div>

<!-- HEADER -->
<header class="header">
  <div class="header__logo">
    <svg width="22" height="22" viewBox="0 0 22 22"><circle cx="11" cy="11" r="11" fill="#F7931A"/><text x="11" y="15.5" text-anchor="middle" fill="#fff" font-size="13" font-weight="800">₿</text></svg>
    RETA <span class="header__logo-badge">LIVE</span>
  </div>
  <div class="header__divider"></div>
  <div class="header__price-block">
    <span class="header__price" id="hdr-price">—</span>
    <span class="header__delta" id="hdr-delta">—</span>
  </div>
  <div class="header__divider"></div>
  <div class="header__meta">Bybit · 1h</div>
  <select id="sym-select" onchange="switchSymbol(this.value)" style="font-family:var(--mono);font-size:.78rem;padding:3px 8px;border:1px solid var(--border);border-radius:6px;background:var(--surface);color:var(--text-1);outline:none;cursor:pointer"></select>
  <div class="header__live">
    <div class="pulse-dot"></div>
    <span id="hdr-update">—</span>
  </div>
</header>

<!-- LAYOUT -->
<div class="layout">

  <!-- ── SIDEBAR ─────────────────────────────────────────────── -->
  <aside class="sidebar">

    <!-- Signal Ring -->
    <div class="card">
      <div class="card__label">
        <div class="card__label-dot" style="background:var(--reta)"></div>
        Signal RETA
      </div>
      <div class="signal-ring-wrap">
        <svg id="signal-ring-svg" viewBox="-10 -10 200 120">
          <!-- Arc track -->
          <path id="ring-track"  class="ring-track" />
          <!-- Colored arcs: bear / neutral / bull -->
          <path id="ring-bear"    class="ring-bear"    />
          <path id="ring-neutral" class="ring-neutral" />
          <path id="ring-bull"    class="ring-bull"    />
          <!-- Needle -->
          <line id="ring-needle" x1="90" y1="90" x2="90" y2="22"
                stroke="var(--text-1)" stroke-width="3" class="ring-needle"
                style="transform-origin:90px 90px" />
          <circle cx="90" cy="90" r="5" fill="var(--text-1)"/>
          <!-- Labels -->
          <text x="12" y="95" fill="var(--red)"    font-size="9" font-family="Inter" font-weight="600">BEAR</text>
          <text x="72" y="18" fill="var(--text-3)" font-size="9" font-family="Inter" font-weight="600" text-anchor="middle">0</text>
          <text x="155" y="95" fill="var(--green)"  font-size="9" font-family="Inter" font-weight="600" text-anchor="end">BULL</text>
        </svg>
        <span class="signal-label neutral" id="sig-label">NEUTRE</span>
        <span class="signal-z" id="sig-z">z̄ = 0.000000</span>
      </div>
    </div>

    <!-- KPIs -->
    <div class="card">
      <div class="card__label">
        <div class="card__label-dot" style="background:var(--orange)"></div>
        Indicateurs RETA
      </div>
      <div class="kpi-stack">
        <div class="kpi-row"><span class="kpi-row__label">P∞ Kalman</span><span class="kpi-row__value" id="kpi-pinf">—</span></div>
        <div class="kpi-row"><span class="kpi-row__label">t_rupture ≥</span><span class="kpi-row__value orange" id="kpi-trup">—</span></div>
        <div class="kpi-row"><span class="kpi-row__label">Erreur prédiction</span><span class="kpi-row__value" id="kpi-err">—</span></div>
        <div class="kpi-row"><span class="kpi-row__label">ε seuil</span><span class="kpi-row__value" id="kpi-eps">0.004</span></div>
        <div class="kpi-row"><span class="kpi-row__label">Barres analysées</span><span class="kpi-row__value" id="kpi-bars">—</span></div>
      </div>
    </div>

    <!-- Auto-Trader RETA -->
    <div class="card" id="auto-card">
      <div class="card__label">
        <div class="card__label-dot" style="background:var(--orange)"></div>
        Auto-Trader RETA
      </div>
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">
        <span id="auto-status-badge" class="signal-label neutral" style="font-size:.7rem;padding:2px 8px">OFF</span>
        <button id="auto-toggle-btn" class="btn-open long" style="width:auto;padding:4px 14px;font-size:.75rem" onclick="toggleAuto()">ACTIVER</button>
      </div>
      <div id="auto-stats" style="font-size:.75rem;color:var(--text-2);margin-bottom:8px">
        Trades: <b id="auto-trades">0</b> ·
        Wins: <b id="auto-wins" style="color:var(--green)">0</b> ·
        Losses: <b id="auto-losses" style="color:var(--red)">0</b> ·
        WR: <b id="auto-wr">0%</b><br>
        P&L: <b id="auto-pnl" style="color:var(--text-1)">$0</b>
      </div>
      <div class="field-row" style="gap:4px;margin-bottom:6px">
        <div class="field" style="flex:1">
          <label>Risque max %</label>
          <input id="cfg-risk" type="range" min="0.5" max="10" step="0.5" value="2"
                 oninput="updateAutoConfig()" style="width:100%">
          <span id="cfg-risk-val" style="font-size:.7rem;color:var(--text-3)">2.0%</span>
        </div>
        <div class="field" style="flex:1">
          <label>Kelly frac</label>
          <input id="cfg-kelly" type="range" min="0" max="1" step="0.05" value="0.5"
                 oninput="updateAutoConfig()" style="width:100%">
          <span id="cfg-kelly-val" style="font-size:.7rem;color:var(--text-3)">0.50</span>
        </div>
      </div>
      <div class="field-row" style="gap:4px;margin-bottom:6px">
        <div class="field" style="flex:1">
          <label>Trail ATR mult</label>
          <input id="cfg-trail" type="range" min="0.5" max="5" step="0.5" value="2"
                 oninput="updateAutoConfig()" style="width:100%">
          <span id="cfg-trail-val" style="font-size:.7rem;color:var(--text-3)">2.0×</span>
        </div>
        <div class="field" style="flex:1;display:flex;align-items:flex-end;gap:4px;padding-top:14px">
          <label style="font-size:.65rem;white-space:nowrap">Trailing</label>
          <input id="cfg-trail-active" type="checkbox" checked onchange="updateAutoConfig()">
          <label style="font-size:.65rem;white-space:nowrap">Auto-open</label>
          <input id="cfg-auto-open" type="checkbox" checked onchange="updateAutoConfig()">
        </div>
      </div>
      <div style="font-size:.65rem;color:var(--text-3);margin-top:4px" id="auto-version"></div>
    </div>

    <!-- Niveaux -->
    <div class="card">
      <div class="card__label">
        <div class="card__label-dot" style="background:var(--red)"></div>
        Résistances / Supports
      </div>
      <div class="level-list" id="level-list">
        <div class="empty-state"><div class="empty-state__icon">📊</div>Chargement…</div>
      </div>
    </div>

    <!-- Position form -->
    <div class="card">
      <div class="card__label">
        <div class="card__label-dot" style="background:var(--green)"></div>
        Ouvrir une position
      </div>
      <div class="pos-form">
        <div class="dir-toggle">
          <button class="dir-btn long active" id="btn-long" onclick="setDir('LONG')">▲ LONG</button>
          <button class="dir-btn short" id="btn-short" onclick="setDir('SHORT')">▼ SHORT</button>
        </div>

        <div class="field">
          <label>Montant (USD)</label>
          <input id="f-amount" type="number" placeholder="1000" value="1000" min="1">
        </div>

        <div class="field">
          <label>Levier</label>
          <div class="lev-btns">
            <button class="lev-btn active" onclick="setLev(this,1)">1×</button>
            <button class="lev-btn"        onclick="setLev(this,2)">2×</button>
            <button class="lev-btn"        onclick="setLev(this,5)">5×</button>
            <button class="lev-btn"        onclick="setLev(this,10)">10×</button>
          </div>
        </div>

        <div class="field-row">
          <div class="field">
            <label>Prix entrée (vide = marché)</label>
            <input id="f-entry" type="number" placeholder="Marché">
          </div>
          <div class="field">
            <label>&nbsp;</label>
            <button class="reta-suggest" onclick="retaSuggest()">⚡ Suggérer RETA</button>
          </div>
        </div>

        <div class="field-row">
          <div class="field">
            <label>Take Profit</label>
            <input id="f-tp" type="number" placeholder="Ex: 72000">
          </div>
          <div class="field">
            <label>Stop Loss</label>
            <input id="f-sl" type="number" placeholder="Ex: 60000">
          </div>
        </div>

        <button class="btn-open long" id="btn-open-pos" onclick="openPosition()">Ouvrir LONG</button>
      </div>
    </div>

    <!-- Positions ouvertes -->
    <div class="card">
      <div class="card__label">
        <div class="card__label-dot" style="background:var(--orange)"></div>
        Positions ouvertes
      </div>
      <div class="pos-list" id="pos-list">
        <div class="empty-state">
          <div class="empty-state__icon">📭</div>
          Aucune position ouverte
        </div>
      </div>
    </div>

  </aside>

  <!-- ── MAIN ──────────────────────────────────────────────────── -->
  <main class="main">

    <!-- Chart 1 : Prix réel vs RETA -->
    <div class="card">
      <div class="card__label">
        <div class="card__label-dot" style="background:var(--orange)"></div>
        Prix <span id="chart-sym">BTC</span> réel vs Prédiction RETA — dérive Kalman accumulée
      </div>
      <div class="chart-wrap chart-main"><canvas id="chart-price"></canvas></div>
      <div class="legend-row">
        <div class="leg"><div class="leg-line" style="background:var(--orange)"></div>Prix réel</div>
        <div class="leg"><div class="leg-dash" style="color:var(--reta)"></div>Prédiction RETA ŷ(t)</div>
        <div class="leg"><div class="leg-line" style="background:rgba(0,168,120,.4);height:10px;border-radius:2px"></div>Zone BULL</div>
        <div class="leg"><div class="leg-line" style="background:rgba(229,62,62,.35);height:10px;border-radius:2px"></div>Zone BEAR</div>
      </div>
      <div class="commentary" id="com-price"></div>
    </div>

    <!-- Charts 2 col -->
    <div class="grid-2">
      <div class="card">
        <div class="card__label">
          <div class="card__label-dot" style="background:var(--red)"></div>
          Erreur (%) réel vs RETA
        </div>
        <div class="chart-wrap chart-sm"><canvas id="chart-err"></canvas></div>
        <div class="commentary warn" id="com-err" style="margin-top:8px;font-size:.75rem"></div>
      </div>
      <div class="card">
        <div class="card__label">
          <div class="card__label-dot" style="background:var(--reta)"></div>
          Perturbation z(t) — Kalman
        </div>
        <div class="chart-wrap chart-sm"><canvas id="chart-z"></canvas></div>
        <div class="commentary" id="com-z" style="margin-top:8px;font-size:.75rem"></div>
      </div>
    </div>

    <!-- Charts 3 col -->
    <div class="grid-3">
      <div class="card">
        <div class="card__label">
          <div class="card__label-dot" style="background:var(--yellow)"></div>
          Régulateur PI
        </div>
        <div class="chart-wrap chart-xs"><canvas id="chart-pi"></canvas></div>
      </div>
      <div class="card">
        <div class="card__label">
          <div class="card__label-dot" style="background:#9B59B6"></div>
          Variance Kalman P₀₀(t)
        </div>
        <div class="chart-wrap chart-xs"><canvas id="chart-var"></canvas></div>
      </div>
      <div class="card">
        <div class="card__label">
          <div class="card__label-dot" style="background:var(--orange)"></div>
          Histogramme P&L positions
        </div>
        <div class="chart-wrap chart-xs"><canvas id="chart-pnl"></canvas></div>
      </div>
    </div>

    <!-- Bull-runs table -->
    <div class="card">
      <div class="card__label">
        <div class="card__label-dot" style="background:var(--green)"></div>
        Cycles BULL détectés — analyse t_rupture RETA
      </div>
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>#</th><th>Début</th><th>Pic prix</th>
              <th>Durée réelle</th><th>t_rupture RETA ≥</th>
              <th>Ratio</th><th>ε̄ moyen</th><th>Verdict</th>
            </tr>
          </thead>
          <tbody id="bull-tbody"></tbody>
        </table>
      </div>
      <div class="formula" style="margin-top:12px">
        t_rupture ≥ (ln P_max − ln P₀) / ε̄ &nbsp;·&nbsp;
        Ratio &lt; 100% → rupture prématurée (news / macro)
      </div>
    </div>

    <!-- Historique positions -->
    <div class="card" id="history-card" style="display:none">
      <div class="card__label">
        <div class="card__label-dot" style="background:var(--text-3)"></div>
        Historique des positions clôturées
      </div>
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr><th>Dir.</th><th>Entrée</th><th>Sortie</th><th>Montant</th><th>Levier</th><th>P&L $</th><th>P&L %</th><th>Signal</th></tr>
          </thead>
          <tbody id="hist-tbody"></tbody>
        </table>
      </div>
    </div>

    <!-- Formules -->
    <div class="card">
      <div class="card__label">
        <div class="card__label-dot" style="background:var(--reta)"></div>
        Théorie RETA appliquée
      </div>
      <div class="grid-2" style="gap:8px">
        <div>
          <div class="formula">z(t) = ln P(t) − ln P(t−1)   [perturbation]</div>
          <div class="formula">z̄(T) ≥ ε → bull-run confirmé</div>
          <div class="formula">t_rup ≥ (ln P_max − ln P₀) / ε̄</div>
        </div>
        <div>
          <div class="formula">ŷ(t) = ŷ(t−1) + ẑ(t)   [prédiction RETA]</div>
          <div class="formula">Erreur = (P_réel − ŷ) / ŷ × 100%</div>
          <div class="formula">u(t) = Kp·e + Ki·∫e dτ   [PI]</div>
        </div>
      </div>
    </div>

  </main>
</div>

<footer>
  RETA Dashboard · Bybit Perpetual · Rafraîchissement 60s · données 5s ·
  <span id="ft-bars">—</span> barres · v2.0
</footer>

<script>
// ── UTILS ──────────────────────────────────────────────────────────────────
const $ = id => document.getElementById(id);
const fmt  = (n,d=0) => n==null?'—':Number(n).toLocaleString('fr-FR',{maximumFractionDigits:d});
const fmtP = n => '$'+fmt(n,0);
const fmtTs = ts => new Date(ts).toLocaleString('fr-FR',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'});

let _charts  = {};
let _dir     = 'LONG';
let _lev     = 1;
let _data    = null;

function toast(msg, type='') {
  const el = $('toast');
  el.textContent = msg;
  el.className   = 'show ' + type;
  setTimeout(() => el.className = '', 2800);
}

// ── SIGNAL RING ────────────────────────────────────────────────────────────

/* Semi-circle arc: 180° from 210° to 30° (going left→up→right)
   Center (90,90), radius 70, viewBox "-10 -10 200 120"  */
const CX=90, CY=90, R=70;
const DEG_START = 210;  // full bear
const DEG_END   = 330;  // full bull  (210 + 120 each side = 330)
const TOTAL_DEG = 120;  // each side

function degToRad(d) { return d * Math.PI / 180; }
function arcPoint(deg) {
  const r = degToRad(deg);
  return [CX + R*Math.cos(r), CY + R*Math.sin(r)];
}
function arcPath(startDeg, endDeg) {
  const [x1,y1] = arcPoint(startDeg);
  const [x2,y2] = arcPoint(endDeg);
  const large    = Math.abs(endDeg - startDeg) > 180 ? 1 : 0;
  return `M ${x1} ${y1} A ${R} ${R} 0 ${large} 1 ${x2} ${y2}`;
}

// Draw static arcs once
(function initRing() {
  $('ring-track').setAttribute('d',    arcPath(210, 330));
  $('ring-bear').setAttribute('d',     arcPath(210, 255));   // left third
  $('ring-neutral').setAttribute('d',  arcPath(255, 285));   // middle
  $('ring-bull').setAttribute('d',     arcPath(285, 330));   // right third
})();

function updateRing(zLast, eps) {
  // Map z ∈ [-eps*3, +eps*3] → angle ∈ [210°, 330°]
  const clamp = Math.max(-eps*3, Math.min(eps*3, zLast));
  const ratio = (clamp + eps*3) / (eps*6);  // 0..1
  const angle = 210 + ratio * 120;
  $('ring-needle').style.transform = `rotate(${angle - 270}deg)`;
  $('sig-z').textContent = 'z̄ = ' + (zLast >= 0 ? '+' : '') + zLast.toFixed(6);

  const label = $('sig-label');
  if (zLast > eps) {
    label.textContent = 'BULL'; label.className = 'signal-label bull';
  } else if (zLast < -eps) {
    label.textContent = 'BEAR'; label.className = 'signal-label bear';
  } else {
    label.textContent = 'NEUTRE'; label.className = 'signal-label neutral';
  }
}

// ── CHART HELPERS ──────────────────────────────────────────────────────────

const GRID_COLOR  = '#E4E6F0';
const TICK_COLOR  = '#8A90B0';
const TICK_STYLE  = { color: TICK_COLOR, font: { size: 10, family: 'JetBrains Mono' } };
const GRID_STYLE  = { color: GRID_COLOR };

const BASE_OPTS = {
  animation: false, responsive: true, maintainAspectRatio: false,
  interaction: { mode: 'index', intersect: false },
  plugins: {
    legend: { display: false },
    tooltip: {
      backgroundColor: '#fff', titleColor: '#1A1F36',
      bodyColor: '#4A5080', borderColor: '#E4E6F0', borderWidth: 1,
      titleFont: { family: 'JetBrains Mono', size: 11 },
      bodyFont:  { family: 'JetBrains Mono', size: 11 },
      padding: 10,
    }
  },
  scales: {
    x: {
      type: 'time',
      time: { unit: 'day', displayFormats: { day:'dd/MM', hour:'HH:mm' } },
      grid: GRID_STYLE, ticks: TICK_STYLE,
    },
    y: { grid: GRID_STYLE, ticks: TICK_STYLE }
  }
};

function mkChart(id, cfg) {
  if (_charts[id]) _charts[id].destroy();
  _charts[id] = new Chart($(id).getContext('2d'), cfg);
}

// ── PRICE CHART ────────────────────────────────────────────────────────────

function buildPrice(d) {
  const T = d.times.map(t => new Date(t));
  // Ajouter timestamp prédiction 1h
  const Tpred = new Date(d.time_pred_1h);
  const T_all = [...T, Tpred];

  const prix_ext  = [...d.prix, null];
  const pred_ext  = [...d.prix_pred, null];
  // Ligne de prédiction : dernier point connu → prédiction
  const pred_line = [];
  for (let i = 0; i < d.prix.length; i++) pred_line.push(null);
  pred_line.push(d.prix_pred_1h);

  mkChart('chart-price', {
    type: 'line',
    data: {
      labels: T_all,
      datasets: [
        {
          label:'Prix réel', data: prix_ext,
          borderColor:'#F7931A', borderWidth:2, pointRadius:0,
          tension:.2, fill:false, order:1,
        },
        {
          label:'RETA ŷ(t)', data: pred_ext,
          borderColor:'#6C63FF', borderWidth:1.5,
          borderDash:[6,3], pointRadius:0, tension:.2, fill:false, order:2,
        },
        {
          label:'Prédiction 1h', data: pred_line,
          borderColor:'#00FF88', borderWidth:2.5,
          borderDash:[4,4], pointRadius:[...Array(d.prix.length).fill(0), 7],
          pointBackgroundColor: [...Array(d.prix.length).fill('transparent'), '#00FF88'],
          pointBorderColor: ['transparent', '#00FF88'],
          pointBorderWidth: 2,
          tension:0, fill:false, order:0,
        },
      ]
    },
    options: {
      ...BASE_OPTS,
      scales: {
        ...BASE_OPTS.scales,
        y: {
          ...BASE_OPTS.scales.y,
          ticks: { ...TICK_STYLE, callback: v => '$'+fmt(v,0) }
        }
      },
      plugins: {
        ...BASE_OPTS.plugins,
        tooltip: {
          ...BASE_OPTS.plugins.tooltip,
          callbacks: {
            label: ctx => {
              if (ctx.datasetIndex === 0)
                return '  Réel : $' + fmt(ctx.raw,0);
              if (ctx.datasetIndex === 2)
                return '  Prédiction 1h : $' + fmt(ctx.raw,0) + '  (' + (d.delta_pct_pred >= 0 ? '+' : '') + d.delta_pct_pred + '%)';
              const e = d.erreur[ctx.dataIndex];
              return '  RETA : $' + fmt(ctx.raw,0) + '  (' + (e>0?'+':'') + e.toFixed(2) + '%)';
            }
          }
        }
      }
    }
  });
}

// ── ERROR CHART ────────────────────────────────────────────────────────────

function buildErr(d) {
  const T   = d.times.map(t => new Date(t));
  const pos = d.erreur.map(e => e > 0 ? e : 0);
  const neg = d.erreur.map(e => e < 0 ? e : 0);
  mkChart('chart-err', {
    type:'bar', data:{
      labels:T,
      datasets:[
        { data:pos, backgroundColor:'rgba(229,62,62,.55)', borderWidth:0, label:'Surévalué' },
        { data:neg, backgroundColor:'rgba(0,168,120,.55)', borderWidth:0, label:'Sous-évalué' },
      ]
    },
    options: {
      ...BASE_OPTS,
      scales: {
        x: { ...BASE_OPTS.scales.x, stacked:true },
        y: { ...BASE_OPTS.scales.y, stacked:true,
             ticks: { ...TICK_STYLE, callback: v => v.toFixed(1)+'%' } }
      }
    }
  });
}

// ── Z CHART ────────────────────────────────────────────────────────────────

function buildZ(d) {
  const T = d.times.map(t => new Date(t));
  mkChart('chart-z', {
    type:'line', data:{
      labels:T,
      datasets:[
        { label:'ẑ Kalman', data:d.z_est, borderColor:'rgba(108,99,255,.5)', borderWidth:1, pointRadius:0, tension:.3, fill:false },
        { label:'z̄ moy 24h', data:d.z_moy, borderColor:'#F7931A', borderWidth:2, pointRadius:0, tension:.4, fill:false },
      ]
    },
    options: {
      ...BASE_OPTS,
      scales: {
        ...BASE_OPTS.scales,
        y: { ...BASE_OPTS.scales.y, ticks:{ ...TICK_STYLE, callback:v=>v.toFixed(4) } }
      }
    }
  });
}

// ── PI CHART ───────────────────────────────────────────────────────────────

function buildPi(d) {
  const T = d.times.map(t => new Date(t));
  mkChart('chart-pi', {
    type:'line', data:{
      labels:T,
      datasets:[
        { label:'e(t)', data:d.e_pi, borderColor:'#D69E2E', borderWidth:1.2,
          pointRadius:0, tension:.3,
          fill:{ target:'origin', above:'rgba(229,62,62,.08)', below:'rgba(0,168,120,.08)' } },
        { label:'u(t)', data:d.u_pi, borderColor:'#9B59B6', borderWidth:1.5,
          pointRadius:0, tension:.3, fill:false },
      ]
    },
    options: { ...BASE_OPTS }
  });
}

// ── VARIANCE CHART ─────────────────────────────────────────────────────────

function buildVar(d) {
  const T = d.times.map(t => new Date(t));
  mkChart('chart-var', {
    type:'line', data:{
      labels:T,
      datasets:[{
        label:'P₀₀(t)', data:d.p_var,
        borderColor:'#9B59B6', borderWidth:1.2, pointRadius:0, tension:.3,
        fill:{ target:'origin', above:'rgba(155,89,182,.10)' },
      }]
    },
    options: {
      ...BASE_OPTS,
      scales: {
        ...BASE_OPTS.scales,
        y: { ...BASE_OPTS.scales.y, ticks:{ ...TICK_STYLE, callback:v=>v.toExponential(1) } }
      }
    }
  });
}

// ── PNL CHART ──────────────────────────────────────────────────────────────

function buildPnl(positions) {
  const closed = positions.filter(p => p.status === 'closed');
  if (!closed.length) {
    if (_charts['chart-pnl']) { _charts['chart-pnl'].destroy(); delete _charts['chart-pnl']; }
    return;
  }
  const labels = closed.map((_,i) => '#'+(i+1));
  const data   = closed.map(p => p.pnl_usd);
  const colors = data.map(v => v >= 0 ? 'rgba(0,168,120,.7)' : 'rgba(229,62,62,.7)');
  mkChart('chart-pnl', {
    type:'bar', data:{
      labels, datasets:[{ label:'P&L ($)', data, backgroundColor:colors, borderRadius:4 }]
    },
    options: {
      ...BASE_OPTS,
      scales: {
        x: { ...BASE_OPTS.scales.x, type:'category',
             ticks:{ ...TICK_STYLE } },
        y: { ...BASE_OPTS.scales.y,
             ticks:{ ...TICK_STYLE, callback:v=>'$'+fmt(v,0) } }
      }
    }
  });
}

// ── COMMENTAIRES ───────────────────────────────────────────────────────────

function buildCommentaries(d) {
  const phase = d.phase;
  const z     = d.z_last;
  const err   = d.erreur[d.erreur.length-1];
  const trup  = d.t_rup;
  const eps   = d.eps_seuil;

  const predStr = d.prix_pred_1h
    ? ` Prédiction 1h: <b>$${fmt(d.prix_pred_1h,0)}</b> (${d.delta_pct_pred >= 0 ? '+' : ''}${d.delta_pct_pred}%)`
    : '';

  let priceClass = 'commentary';
  let priceMsg   = '';
  if (phase === 'BULL') {
    priceClass += ' good';
    priceMsg = `<b>Phase BULL confirmée.</b> z̄(t) = ${z.toFixed(5)} > ε. Rupture estimée ≥ <b>${Math.round(trup)} barres</b>.${predStr}`;
  } else if (phase === 'BEAR') {
    priceClass += ' danger';
    priceMsg = `<b>Phase BEAR active.</b> z̄(t) = ${z.toFixed(5)} < −ε. Prédiction RETA suit la contraction.${predStr}`;
  } else {
    priceClass += ' warn';
    priceMsg = `<b>Consolidation — z̄(t) ≈ 0.</b> Attendre z̄ > ${eps} (BULL) ou < −${eps} (BEAR).${predStr}`;
  }
  $('com-price').className = priceClass;
  $('com-price').innerHTML = priceMsg;

  let errClass = 'commentary ';
  let errMsg   = '';
  if (Math.abs(err) < 2) {
    errClass += 'good';
    errMsg = `<b>Calibration RETA précise (${err>0?'+':''}${err.toFixed(2)}%).</b> Réel et RETA alignés. Le modèle est dans sa zone de confiance — signaux fiables.`;
  } else if (err > 0) {
    errClass += 'warn';
    errMsg = `<b>Prix réel au-dessus de RETA (+${err.toFixed(2)}%).</b> Deux lectures : momentum plus fort que modélisé (continuer LONG), ou mean-reversion à venir (le réel revient vers RETA). Surveiller z̄(t).`;
  } else {
    errClass += 'danger';
    errMsg = `<b>Prix réel sous RETA (${err.toFixed(2)}%).</b> Sous-performance → possible BEAR non encore détecté. Si l'erreur négative s'accentue, le modèle va détecter la phase BEAR à la prochaine fenêtre.`;
  }
  $('com-err').className = errClass;
  $('com-err').innerHTML = errMsg;

  let zMsg = '';
  if (z > eps) {
    zMsg = `<b>Dérive positive confirmée (z̄ = +${z.toFixed(5)}).</b> Chaque barre ajoute +${(z*100).toFixed(3)}% en moyenne. Kalman P∞ = ${d.P_inf.toFixed(6)} — variance stabilisée → estimation fiable.`;
  } else if (z < -eps) {
    zMsg = `<b>Dérive négative (z̄ = ${z.toFixed(5)}).</b> Pression vendeuse persistante. Continuer SHORT ou sortir LONG.`;
  } else {
    zMsg = `<b>z̄ ≈ 0 — pas de tendance franche.</b> Kalman P∞ = ${d.P_inf.toFixed(6)} convergé. Le marché est en équilibre momentané.`;
  }
  $('com-z').innerHTML = zMsg;
}

// ── NIVEAUX ────────────────────────────────────────────────────────────────

function buildLevels(d) {
  const cur  = d.prix_cur;
  let html   = '';
  d.resistances.slice(0,3).forEach(r => {
    const pct = ((r - cur)/cur*100).toFixed(1);
    html += `<div class="level-item res">
      <span>${fmtP(r)}</span>
      <span class="level-item__tag">RES +${pct}%</span></div>`;
  });
  // current
  html += `<div class="level-item" style="background:var(--orange-dim);color:var(--orange);font-weight:700">
    <span>${fmtP(cur)}</span><span class="level-item__tag">ACTUEL</span></div>`;
  d.supports.slice(0,3).forEach(s => {
    const pct = ((cur - s)/cur*100).toFixed(1);
    html += `<div class="level-item sup">
      <span>${fmtP(s)}</span>
      <span class="level-item__tag">SUP −${pct}%</span></div>`;
  });
  $('level-list').innerHTML = html;
}

// ── BULL TABLE ─────────────────────────────────────────────────────────────

function buildBullTable(d) {
  let html = '';
  d.bull_zones.forEach((b,i) => {
    let badge = '';
    if (b.ratio < 70)
      badge = `<span class="badge badge-danger">Prématurée ${b.ratio}%</span>`;
    else if (b.ratio < 100)
      badge = `<span class="badge badge-warn">Partielle ${b.ratio}%</span>`;
    else
      badge = `<span class="badge badge-ok">Dans la borne</span>`;
    html += `<tr>
      <td><b>#${i+1}</b></td>
      <td>${fmtTs(b.t_debut)}</td>
      <td style="font-family:var(--mono);font-weight:600">${fmtP(b.prix_pic)}</td>
      <td>${b.t_reel}h</td>
      <td>≥ ${Math.round(b.t_rup)}h</td>
      <td style="font-family:var(--mono)">${b.ratio}%</td>
      <td style="font-family:var(--mono)">${b.eps}</td>
      <td>${badge}</td>
    </tr>`;
  });
  $('bull-tbody').innerHTML = html || `<tr><td colspan="8" style="text-align:center;color:var(--text-3);padding:20px">Aucun bull-run détecté sur la période</td></tr>`;
}

// ── KPIs ───────────────────────────────────────────────────────────────────

function updateKPIs(d) {
  $('kpi-pinf').textContent = d.P_inf.toFixed(6);
  $('kpi-trup').textContent = '≥ ' + Math.round(d.t_rup) + ' barres';
  const e = d.erreur[d.erreur.length-1];
  $('kpi-err').textContent  = (e>0?'+':'') + e.toFixed(2) + '%';
  $('kpi-err').className    = 'kpi-row__value ' + (Math.abs(e)<2?'green': e>0?'orange':'red');
  $('kpi-bars').textContent = d.times.length;
  $('ft-bars').textContent  = d.times.length + ' barres';
}

// ── POSITIONS UI ───────────────────────────────────────────────────────────

function setDir(dir) {
  _dir = dir;
  ['long','short'].forEach(d => {
    const btn = $('btn-'+d);
    btn.classList.toggle('active', d.toUpperCase() === dir);
  });
  const btn = $('btn-open-pos');
  btn.textContent = dir === 'LONG' ? 'Ouvrir LONG ▲' : 'Ouvrir SHORT ▼';
  btn.className   = 'btn-open ' + dir.toLowerCase();
}

function setLev(el, val) {
  _lev = val;
  document.querySelectorAll('.lev-btn').forEach(b => b.classList.remove('active'));
  el.classList.add('active');
}

function retaSuggest() {
  if (!_data) return;
  const phase = _data.phase;
  const cur   = _data.prix_cur;
  const eps   = _data.eps_seuil;

  if (phase === 'BULL') {
    setDir('LONG');
    // TP = prix actuel + 5 × t_rup estimé en prix
    const tp = Math.round(cur * 1.08 / 100) * 100;
    const sl = Math.round(cur * 0.95 / 100) * 100;
    $('f-tp').value = tp;
    $('f-sl').value = sl;
    toast('⚡ RETA suggère LONG · TP +8% · SL −5%', 'good');
  } else if (phase === 'BEAR') {
    setDir('SHORT');
    const tp = Math.round(cur * 0.92 / 100) * 100;
    const sl = Math.round(cur * 1.05 / 100) * 100;
    $('f-tp').value = tp;
    $('f-sl').value = sl;
    toast('⚡ RETA suggère SHORT · TP −8% · SL +5%', 'bad');
  } else {
    toast('⚡ RETA : neutre — attendre signal clair', '');
  }
}

async function openPosition() {
  const amount = parseFloat($('f-amount').value);
  if (!amount || amount <= 0) { toast('Montant invalide', 'bad'); return; }
  const entry = $('f-entry').value.trim() !== '' ? parseFloat($('f-entry').value) : null;
  const tp    = $('f-tp').value.trim()    !== '' ? parseFloat($('f-tp').value)    : null;
  const sl    = $('f-sl').value.trim()    !== '' ? parseFloat($('f-sl').value)    : null;
  const phase = _data?.phase || 'MANUEL';

  try {
    const r = await fetch('/api/position/open', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({
        direction: _dir, amount_usd: amount, leverage: _lev,
        entry_price: entry, tp, sl, reta_signal: phase,
        symbol: _activeSymbol,
      })
    });
    const j = await r.json();
    if (j.ok) {
      toast(`✓ Position ${_dir} ouverte à $${fmt(j.position.entry_price,0)}`, 'good');
      refreshPositions();
    }
  } catch(e) { toast('Erreur ouverture position', 'bad'); }
}

async function closePosition(id) {
  const r = await fetch(`/api/position/close/${id}`, { method:'POST' });
  const j = await r.json();
  if (j.ok) {
    const sign = j.pnl_usd >= 0 ? '+' : '';
    toast(`Position clôturée · P&L ${sign}$${fmt(j.pnl_usd,2)} (${sign}${j.pnl_pct.toFixed(2)}%)`,
          j.pnl_usd >= 0 ? 'good' : 'bad');
    refreshPositions();
  }
}

async function refreshPositions() {
  const r = await fetch('/api/position/list');
  const positions = await r.json();

  const open   = positions.filter(p => p.status === 'open');
  const closed = positions.filter(p => p.status === 'closed');

  // Positions ouvertes
  if (!open.length) {
    $('pos-list').innerHTML = `<div class="empty-state"><div class="empty-state__icon">📭</div>Aucune position ouverte</div>`;
  } else {
    $('pos-list').innerHTML = open.map(p => {
      const profit = p.pnl_usd >= 0;
      const sign   = p.pnl_usd >= 0 ? '+' : '';
      const tpBadge = p.tp_hit ? `<span class="tp-sl-hit tp-hit">TP ✓</span>` : '';
      const slBadge = p.sl_hit ? `<span class="tp-sl-hit sl-hit">SL ✗</span>` : '';
      const srcBadge = p.source === 'bybit'
        ? `<span style="font-size:.6rem;background:#5B5CFF;color:#fff;padding:1px 6px;border-radius:4px;font-weight:600;margin-left:6px">BYB</span>`
        : `<span style="font-size:.6rem;background:var(--surface-2);color:var(--text-3);padding:1px 6px;border-radius:4px;margin-left:6px">MANU</span>`;
      return `
      <div class="pos-card-item ${profit?'profit':'loss'}">
        <div class="pos-card-item__header">
          <span><span class="pos-card-item__dir ${p.direction.toLowerCase()}">${p.direction} ${p.leverage}×</span><span style="font-family:var(--mono);font-size:.68rem;color:var(--text-2);margin-left:4px">${p.symbol || 'BTCUSDT'}</span>${srcBadge}</span>
          <span class="pos-card-item__pnl ${profit?'up':'down'}">${sign}$${fmt(p.pnl_usd,2)}</span>
        </div>
        <div class="pos-card-item__rows">
          <div class="pos-card-item__row"><span>Entrée</span><span>$${fmt(p.entry_price,0)}</span></div>
          <div class="pos-card-item__row"><span>Actuel</span><span>$${fmt(p.cur_price,0)}</span></div>
          <div class="pos-card-item__row"><span>Montant</span><span>$${fmt(p.amount_usd,0)}</span></div>
          <div class="pos-card-item__row"><span>P&L %</span><span style="color:${profit?'var(--green)':'var(--red)'}">${sign}${p.pnl_pct.toFixed(2)}%</span></div>
          ${p.tp ? `<div class="pos-card-item__row"><span>TP</span><span>$${fmt(p.tp,0)} ${tpBadge}</span></div>` : ''}
          ${p.sl ? `<div class="pos-card-item__row"><span>SL</span><span>$${fmt(p.sl,0)} ${slBadge}</span></div>` : ''}
        </div>
        <button class="btn-close" onclick="closePosition(${p.id})">Clôturer la position</button>
      </div>`;
    }).join('');
  }

  // Historique
  if (closed.length) {
    $('history-card').style.display = 'block';
    $('hist-tbody').innerHTML = closed.reverse().map(p => {
      const sign  = p.pnl_usd >= 0 ? '+' : '';
      const color = p.pnl_usd >= 0 ? 'var(--green)' : 'var(--red)';
      return `<tr>
        <td><span class="pos-card-item__dir ${p.direction.toLowerCase()}" style="font-size:.68rem;padding:2px 7px;border-radius:4px;font-weight:700;${p.direction==='LONG'?'background:var(--green-dim);color:var(--green)':'background:var(--red-dim);color:var(--red)'}">${p.direction}</span></td>
        <td style="font-family:var(--mono)">$${fmt(p.entry_price,0)}</td>
        <td style="font-family:var(--mono)">$${fmt(p.close_price,0)}</td>
        <td style="font-family:var(--mono)">$${fmt(p.amount_usd,0)}</td>
        <td>${p.leverage}×</td>
        <td style="font-family:var(--mono);color:${color};font-weight:600">${sign}$${fmt(p.pnl_usd,2)}</td>
        <td style="font-family:var(--mono);color:${color}">${sign}${p.pnl_pct.toFixed(2)}%</td>
        <td><span class="badge ${p.reta_signal==='BULL'?'badge-ok':p.reta_signal==='BEAR'?'badge-danger':'badge-warn'}">${p.reta_signal}</span></td>
      </tr>`;
    }).join('');
  }

  buildPnl(positions);
}

// ── LIVE PRICE ──────────────────────────────────────────────────────────────

let _prevPrice = 0;
async function updateLivePrice() {
  try {
    const r = await fetch('/api/price?symbol=' + _activeSymbol);
    const j = await r.json();
    if (!j.price) return;
    const el    = $('hdr-price');
    const color = j.price >= _prevPrice ? 'var(--green)' : 'var(--red)';
    el.textContent  = '$' + Number(j.price).toLocaleString('fr-FR',{maximumFractionDigits:0});
    el.style.color  = color;
    setTimeout(() => el.style.color = 'var(--text-1)', 1200);
    _prevPrice = j.price;
    $('hdr-update').textContent = 'Màj ' + new Date().toLocaleTimeString('fr-FR');
  } catch {}
}

// ── SYMBOL SELECTOR ────────────────────────────────────────────────────────────

let _activeSymbol = 'BTCUSDT';

async function fetchSymbols() {
  try {
    const r = await fetch('/api/symbols');
    const j = await r.json();
    const sel = $('sym-select');
    sel.innerHTML = j.symbols.map(s =>
      `<option value="${s}" ${s === j.active ? 'selected' : ''}>${s.replace('USDT','')}</option>`
    ).join('');
  } catch {}
}

function switchSymbol(sym) {
  _activeSymbol = sym;
  render();
}

// ── AUTO-TRADER UI ────────────────────────────────────────────────────────────

async function fetchAutoStatus() {
  try {
    const r = await fetch('/api/auto/config');
    const c = await r.json();
    $('auto-status-badge').textContent = c.enabled ? 'ACTIF' : 'OFF';
    $('auto-status-badge').className = 'signal-label ' + (c.enabled ? 'bull' : 'neutral');
    $('auto-toggle-btn').textContent = c.enabled ? 'DÉSACTIVER' : 'ACTIVER';
    $('auto-toggle-btn').className = 'btn-open ' + (c.enabled ? 'short' : 'long');
    $('auto-toggle-btn').style.width = 'auto';
    $('auto-toggle-btn').style.padding = '4px 14px';
    $('auto-toggle-btn').style.fontSize = '.75rem';
    $('auto-version').textContent = 'RETA v1.4 · ' + (c.symbols ? c.symbols.length + ' symboles' : '10 symboles') + ' · Kelly · Trail ATR';
    $('cfg-risk').value = c.max_risk_pct;
    $('cfg-risk-val').textContent = c.max_risk_pct.toFixed(1) + '%';
    $('cfg-kelly').value = c.kelly_frac;
    $('cfg-kelly-val').textContent = c.kelly_frac.toFixed(2);
    $('cfg-trail').value = c.trail_atr_mult;
    $('cfg-trail-val').textContent = c.trail_atr_mult.toFixed(1) + '\u00d7';
    $('cfg-trail-active').checked = c.trailing_active;
    $('cfg-auto-open').checked = c.auto_open;
  } catch {}
}

async function fetchAutoStats() {
  try {
    const r = await fetch('/api/auto/status');
    const s = await r.json();
    const st = s.stats;
    $('auto-trades').textContent = st.trades;
    $('auto-wins').textContent = st.wins;
    $('auto-losses').textContent = st.losses;
    $('auto-wr').textContent = st.trades ? (st.wins/st.trades*100).toFixed(0) + '%' : '—';
    const pnl = st.pnl_total;
    $('auto-pnl').textContent = (pnl >= 0 ? '+' : '') + '$' + Number(Math.abs(pnl)).toLocaleString('fr-FR',{maximumFractionDigits:2});
    $('auto-pnl').style.color = pnl >= 0 ? 'var(--green)' : 'var(--red)';
  } catch {}
}

async function toggleAuto() {
  await fetch('/api/auto/toggle', { method:'POST' });
  fetchAutoStatus();
  toast('Auto-Trader ' + ($('auto-status-badge').textContent === 'ACTIF' ? 'activé' : 'désactivé'), '');
}

let _autoConfigTimer = null;
async function updateAutoConfig() {
  if (_autoConfigTimer) clearTimeout(_autoConfigTimer);
  _autoConfigTimer = setTimeout(async () => {
    const body = {
      max_risk_pct:   parseFloat($('cfg-risk').value),
      kelly_frac:     parseFloat($('cfg-kelly').value),
      trail_atr_mult: parseFloat($('cfg-trail').value),
      trailing_active: $('cfg-trail-active').checked,
      auto_open:      $('cfg-auto-open').checked,
    };
    $('cfg-risk-val').textContent = body.max_risk_pct.toFixed(1) + '%';
    $('cfg-kelly-val').textContent = body.kelly_frac.toFixed(2);
    $('cfg-trail-val').textContent = body.trail_atr_mult.toFixed(1) + '\u00d7';
    await fetch('/api/auto/config', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify(body),
    });
  }, 300);
}

// ── MAIN RENDER ─────────────────────────────────────────────────────────────

async function render() {
  try {
    const r = await fetch('/api/data?symbol=' + _activeSymbol);
    const d = await r.json();
    if (d.error) return;
    _data = d;

    buildPrice(d);
    buildErr(d);
    buildZ(d);
    buildPi(d);
    buildVar(d);
    updateKPIs(d);
    updateRing(d.z_last, d.eps_seuil);
    buildCommentaries(d);
    buildLevels(d);
    buildBullTable(d);

    const dlt = d.delta_pct;
    $('hdr-price').textContent  = '$' + fmt(d.prix_cur, 0);
    $('hdr-delta').textContent  = (dlt >= 0 ? '+' : '') + dlt.toFixed(3) + '%';
    $('hdr-delta').className    = 'header__delta ' + (dlt >= 0 ? 'delta-up' : 'delta-down');
    if (d.active_symbol) $('chart-sym').textContent = d.active_symbol.replace('USDT','');

    $('loader').style.display = 'none';
  } catch(e) { console.error(e); }
}

// ── BOOT ────────────────────────────────────────────────────────────────────

fetchSymbols();
render();
refreshPositions();
fetchAutoStatus();
fetchAutoStats();
setInterval(render,            5_000);
setInterval(updateLivePrice,   5_000);
setInterval(refreshPositions,  5_000);
setInterval(fetchAutoStats,    5_000);
setInterval(fetchSymbols,     30_000);
</script>
</body>
</html>"""


@app.route("/")
def index():
    return render_template_string(HTML)


if __name__ == "__main__":
    print("╔══════════════════════════════════════════╗")
    print("║  RETA Dashboard · BTC Live               ║")
    print("║  http://localhost:5000                   ║")
    print("╚══════════════════════════════════════════╝")
    app.run(host="0.0.0.0", port=5000, debug=True)
