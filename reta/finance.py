"""
RETA-nD -- extension finance (points 3 et 4, cf. echange utilisateur sur
l'application au risque de portefeuille).

Ce module ne depend d'aucune source de donnees precise (Binance ou
ailleurs) : il attend un tableau numpy de rendements ou de rayons deja
calcules. La recuperation des donnees (ex. via ccxt) se fait en dehors
(voir exemples/fetch_binance.py).

  - calibrate_cir_mle : point 3, calibration MLE de (D, Kp) sur une serie
    radiale reelle, n_eff etant fixe separement (cf. nd.RETAND.n_eff_diagnostics).
  - first_passage_time_mc : point 4, corrige le biais de `first_passage_time`
    (dispersion.py), qui ignore la barriere absorbante -- estimation par
    simulation EXACTE (tirages directs dans la loi de transition khi-deux
    non centree a chaque pas, pas de biais de discretisation d'Euler).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize
from scipy.stats import ncx2

from .dispersion import cir_params, is_crisis_regime


def log_returns_from_prices(prices: np.ndarray) -> np.ndarray:
    """Convertit une serie de prix (1D) en log-rendements."""
    prices = np.asarray(prices, dtype=float)
    if np.any(prices <= 0):
        raise ValueError("log_returns_from_prices necessite des prix strictement positifs")
    return np.diff(np.log(prices))


def radius_series_from_returns(returns: np.ndarray) -> np.ndarray:
    """r(t) = ||rendements(t)|| a partir d'un tableau (T, n) multi-actifs."""
    returns = np.asarray(returns, dtype=float)
    if returns.ndim == 1:
        return np.abs(returns)
    return np.linalg.norm(returns, axis=1)


def _cir_transition_logpdf(
    x_next: np.ndarray, x_prev: np.ndarray, dt: float, n_eff: float, D: float, Kp: float
) -> np.ndarray:
    """Log-densite de transition CIR/BESQ, vectorisee."""
    if Kp == 0.0:
        sigma_sq = (2.0 * math.sqrt(2.0 * D)) ** 2
        c = sigma_sq * dt / 4.0
        df = n_eff
        nc = np.where(x_prev > 0, 4.0 * x_prev / (sigma_sq * dt), 0.0)
    else:
        kappa, theta, sigma = cir_params(n_eff, D, Kp)
        sigma_sq = sigma**2
        emkt = math.exp(-kappa * dt)
        c = sigma_sq * (1.0 - emkt) / (4.0 * kappa)
        df = 4.0 * kappa * theta / sigma_sq
        nc = np.where(x_prev > 0, (4.0 * kappa * x_prev * emkt) / (sigma_sq * (1.0 - emkt)), 0.0)

    if c <= 0:
        return np.full_like(x_next, -np.inf)
    return ncx2.logpdf(x_next / c, df, nc) - math.log(c)


@dataclass
class CIRCalibrationResult:
    D: float
    Kp: float
    n_eff_used: float
    log_likelihood: float
    n_observations: int
    crisis_regime: bool
    converged: bool


def calibrate_cir_mle(
    radius_series: np.ndarray,
    dt: float,
    n_eff: float,
    D0: float = 1e-4,
    Kp0: float = 0.1,
) -> CIRCalibrationResult:
    """
    Calibre (D, Kp) par maximum de vraisemblance sur une serie de rayons
    r(t), pour n_eff FIXE (estime a part -- cf. RETAND.n_eff_diagnostics,
    qui applique deja le shrinkage Ledoit-Wolf du point 2).

    n_eff n'est volontairement PAS calibre ici : c'est une quantite
    geometrique (participation ratio de la covariance), pas un parametre
    de diffusion -- les melanger dans une meme optimisation MLE creerait
    une confusion entre correlation structurelle et dynamique de diffusion.
    """
    r = np.asarray(radius_series, dtype=float)
    if len(r) < 20:
        raise ValueError("calibrate_cir_mle recommande au moins 20 observations")

    x = r**2
    x_prev, x_next = x[:-1], x[1:]

    def neg_log_likelihood(log_params: np.ndarray) -> float:
        D_val, Kp_val = np.exp(log_params)
        ll = _cir_transition_logpdf(x_next, x_prev, dt, n_eff, D_val, Kp_val)
        if not np.all(np.isfinite(ll)):
            return 1e10
        return float(-np.sum(ll))

    x0 = np.log([D0, Kp0])
    res = minimize(neg_log_likelihood, x0, method="Nelder-Mead",
                    options={"xatol": 1e-8, "fatol": 1e-8, "maxiter": 5000})
    D_hat, Kp_hat = np.exp(res.x)

    return CIRCalibrationResult(
        D=float(D_hat), Kp=float(Kp_hat), n_eff_used=float(n_eff),
        log_likelihood=float(-res.fun), n_observations=len(x_next),
        crisis_regime=is_crisis_regime(n_eff), converged=bool(res.success),
    )


def simulate_cir_paths_exact(
    X0: float, kappa: float, theta: float, sigma: float,
    dt: float, n_steps: int, n_paths: int, rng: np.random.Generator,
) -> np.ndarray:
    """Simulation EXACTE de trajectoires CIR (tirage direct khi-deux non
    centre a chaque pas -- pas de biais de discretisation d'Euler)."""
    emkt = math.exp(-kappa * dt)
    c = sigma**2 * (1.0 - emkt) / (4.0 * kappa)
    df = 4.0 * kappa * theta / sigma**2

    X = np.full(n_paths, X0, dtype=float)
    paths = np.empty((n_paths, n_steps + 1))
    paths[:, 0] = X0
    for k in range(1, n_steps + 1):
        nc = (4.0 * kappa * X * emkt) / (sigma**2 * (1.0 - emkt))
        X = c * ncx2.rvs(df, nc, random_state=rng)
        paths[:, k] = X
    return paths


def first_passage_time_mc(
    Y_max: float, r0: float, n_eff: float, D: float, Kp: float,
    dt: float = 0.1, t_max: float = 200.0, n_paths: int = 20_000, seed: int = 0,
) -> dict:
    """
    Estime la distribution du VRAI premier temps de passage (avec barriere
    absorbante), par simulation exacte -- corrige le biais de
    `dispersion.first_passage_time` (probabilite marginale a T fixe, sans
    barriere), qui peut sous-estimer le risque de facon QUALITATIVE : dans
    certains regimes (theta < Y_max), il predit "jamais de rupture" (temps
    infini) alors que la rupture est en realite quasi certaine.

    Attention couts de calcul : precision proportionnelle a n_paths et a
    1/dt (contrairement a la methode analytique, instantanee).
    """
    kappa = 2.0 * Kp if Kp > 0 else 1e-8
    sigma = 2.0 * math.sqrt(2.0 * D)
    theta = 2.0 * n_eff * D / kappa if Kp > 0 else 1e12

    rng = np.random.default_rng(seed)
    n_steps = int(t_max / dt)
    X0, X_max = r0**2, Y_max**2

    paths = simulate_cir_paths_exact(X0, kappa, theta, sigma, dt, n_steps, n_paths, rng)
    crossed = paths >= X_max
    never_crossed = ~crossed.any(axis=1)
    first_idx = np.argmax(crossed, axis=1).astype(float)
    first_idx[never_crossed] = np.nan
    fpt = first_idx * dt
    valid = ~np.isnan(fpt)

    if valid.sum() == 0:
        return {"median_fpt": math.inf, "p_ever_crossed": 0.0,
                "n_paths": n_paths, "censored_fraction": 1.0}

    return {
        "median_fpt": float(np.median(fpt[valid])),
        "q10_fpt": float(np.quantile(fpt[valid], 0.10)),
        "q90_fpt": float(np.quantile(fpt[valid], 0.90)),
        "p_ever_crossed_by_t_max": float(valid.mean()),
        "censored_fraction": float(never_crossed.mean()),
        "n_paths": n_paths,
    }
