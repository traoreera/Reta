"""
A exécuter chez toi (l'accès api.binance.com est bloqué dans le sandbox Claude).

    pip install ccxt pandas
    python fetch_binance.py

Récupère l'historique complet (avec pagination) pour les 20 paires USDT,
alignées à partir de 2021-01-01, et sauvegarde prices.csv / returns.csv.
"""

import time

import ccxt
import pandas as pd

SYMBOLS = [
    "BTC/USDT", "ETH/USDT", "BNB/USDT", "LTC/USDT", "NEO/USDT",
    "ADA/USDT", "XRP/USDT", "XMR/USDT", "ETC/USDT", "VET/USDT",
    "LINK/USDT", "DOGE/USDT", "TRX/USDT", "DOT/USDT", "UNI/USDT",
    "AVAX/USDT", "SOL/USDT", "ATOM/USDT", "NEAR/USDT", "MATIC/USDT",
]
TIMEFRAME = "1h"          # microstructure trop bruitée en 1m/5m (cf. point 3)
START = "2021-01-01T00:00:00Z"   # 1ere date ou les 20 paires ont un historique complet
PAGE_LIMIT = 1000          # max par requete Binance


def fetch_full_history(exchange, symbol: str, timeframe: str, since_iso: str) -> pd.Series:
    """Pagine tant qu'il reste des bougies a recuperer (fetch_ohlcv ne renvoie
    que PAGE_LIMIT bougies par appel -- indispensable ici vu la profondeur
    demandee, ~48 000 bougies en 1h depuis 2021)."""
    since = exchange.parse8601(since_iso)
    now = exchange.milliseconds()
    all_rows = []

    while since < now:
        batch = exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=PAGE_LIMIT)
        if not batch:
            break
        all_rows.extend(batch)
        last_ts = batch[-1][0]
        if last_ts <= since:  # securite anti-boucle infinie
            break
        since = last_ts + 1
        time.sleep(exchange.rateLimit / 1000)  # respecter le rate limit Binance

    df = pd.DataFrame(all_rows, columns=["ts", "open", "high", "low", "close", "volume"])
    df["datetime"] = pd.to_datetime(df["ts"], unit="ms")
    df = df.drop_duplicates(subset="ts").set_index("datetime")
    return df["close"]


def fetch_universe(symbols=SYMBOLS, timeframe=TIMEFRAME, since_iso=START):
    exchange = ccxt.binance()
    exchange.enableRateLimit = True

    data = {}
    for symbol in symbols:
        print(f"Telechargement {symbol} ({timeframe}, depuis {since_iso})...")
        data[symbol] = fetch_full_history(exchange, symbol, timeframe, since_iso)

    prices_df = pd.DataFrame(data).dropna()
    returns_df = prices_df.pct_change().dropna()
    return prices_df, returns_df


if __name__ == "__main__":
    prices_df, returns_df = fetch_universe()
    prices_df.to_csv("prices.csv")
    returns_df.to_csv("returns.csv")
    print(f"{len(returns_df)} observations x {returns_df.shape[1]} actifs -> returns.csv")
    print(returns_df.tail())
