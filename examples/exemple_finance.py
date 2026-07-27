"""
A executer apres examples/fetch_binance.py (qui genere returns.csv).
    python examples/exemple_finance.py
"""
import numpy as np
import pandas as pd

from reta.nd import RETAND
from reta.finance import radius_series_from_returns, calibrate_cir_mle, first_passage_time_mc

WINDOW = 90
Y_MAX = 0.15

def main():
    returns = pd.read_csv("returns.csv", index_col=0, parse_dates=True)
    window = returns.values[-WINDOW:]

    nd = RETAND(n=window.shape[1], Y_max_axes=[Y_MAX] * window.shape[1])
    for row in window:
        nd.step(row)

    n_eff, crisis = nd.n_eff_diagnostics()
    print(f"n_eff = {n_eff:.2f} (crisis={crisis})")

    r_series = radius_series_from_returns(window - window.mean(axis=0))
    cal = calibrate_cir_mle(r_series, dt=1.0, n_eff=max(n_eff, 2.0))
    print(f"Kp={cal.Kp:.4f} D={cal.D:.4f} (converged={cal.converged})")

    result = first_passage_time_mc(Y_MAX, float(r_series[-1]), max(n_eff, 2.0), cal.D, cal.Kp,
                                    dt=1.0, t_max=500, n_paths=20_000)
    print(f"Temps de rupture median (Monte Carlo) = {result['median_fpt']:.1f} periodes")

if __name__ == "__main__":
    main()
