"""
RETA-nD — couche de dispersion (processus de Bessel / pont CIR).

Cf. docs/2_extensions_theoriques/reta_nd_dispersion.md et
docs/2_extensions_theoriques/extension_dimensionnelle.md §3.2.

Le processus radial régulé (bruit isotrope + force entropique géométrique
+ régulation proportionnelle isotrope Kp) est :

    dr = [(n_eff - 1)·D / r  -  Kp·r] dt  +  √(2D) dW_t

**Pont CIR (fait central de ce module) :** en posant X = r², la formule
d'Itô donne exactement un processus de Cox-Ingersoll-Ross (1985) :

    dX = κ(θ - X) dt + σ√X dW,   κ = 2·Kp,  θ = 2·n_eff·D / κ,  σ = 2√(2D)

Ceci permet d'utiliser la densité de transition connue du CIR (khi-deux
décentrée) pour calculer P(r(t) < Y_max) **sans simulation Monte Carlo** —
c'est l'approximation "semi-analytique" retenue ici.

**Limite du cas Kp = 0** (pas de régulation, RETA-nD "pur") : κ → 0, θ → ∞
mais κθ = 2·n_eff·D reste fini. Le CIR dégénère vers un processus de Bessel
au carré (BESQ) de dimension n_eff, dont la transition est le cas limite
exact de la formule CIR (implémenté séparément ci-dessous, pas par κ→0
numérique).

**Avertissement méthodologique :** `transition_cdf` est la loi de X(t) SANS
barrière absorbante. L'utiliser comme proxy de P(pas encore rompu) sous-estime
légèrement le vrai temps de premier passage (les trajectoires qui ont déjà
franchi Y_max puis sont "redescendues" comptent à tort comme non-rompues).
C'est l'approximation semi-analytique standard — une dérivation exacte du
premier passage nécessiterait l'inversion de la transformée de Laplace du
temps d'atteinte (non implémentée, cf. reta_nd_dispersion.md §6).
"""

from __future__ import annotations

import math

import numpy as np
from scipy.optimize import brentq
from scipy.stats import ncx2


def effective_dimension(cov: np.ndarray) -> float:
    """
    Dimension effective (participation ratio) d'une matrice de covariance Σ.

        n_eff = (tr Σ)² / tr(Σ²)

    Cf. reta_nd_dispersion.md §5.2. Toujours ≤ n (dimension nominale) ;
    égal à n seulement si Σ est isotrope (proportionnelle à l'identité).
    """
    cov = np.asarray(cov, dtype=float)
    tr = np.trace(cov)
    tr_sq = np.trace(cov @ cov)
    if tr_sq <= 0:
        return 0.0
    return float(tr**2 / tr_sq)


def is_crisis_regime(n_eff: float) -> bool:
    """
    True si la condition de Feller (n_eff >= 2) est violée : l'origine
    devient une barrière accessible pour le processus CIR/BESQ sous-jacent
    à `t_rupture_joint`. En contexte financier, n_eff < 2 signale une
    corrélation extrême entre actifs (perte de diversification, crash
    systémique) — c'est un signal en soi, pas seulement une contrainte
    numérique à contourner (cf. RETAND._residual_covariance).
    """
    return n_eff < 2.0


def cir_params(n_eff: float, D: float, Kp: float) -> tuple[float, float, float]:
    """Convertit (n_eff, D, Kp) en paramètres CIR (kappa, theta, sigma)."""
    if n_eff < 2:
        raise ValueError(
            f"n_eff={n_eff} < 2 : condition de Feller violée (le processus "
            "radial atteint 0 avec probabilité positive, hors du cadre RETA-nD)"
        )
    kappa = 2.0 * Kp
    sigma = 2.0 * math.sqrt(2.0 * D)
    theta = math.inf if kappa == 0 else 2.0 * n_eff * D / kappa
    return kappa, theta, sigma


def transition_cdf(x: float, t: float, x0: float, n_eff: float, D: float, Kp: float) -> float:
    """
    P(X(t) <= x | X(0) = x0) où X = r², pour le pont CIR défini ci-dessus.

    Cas Kp > 0 : formule CIR standard (khi-deux décentrée non-centrale).
    Cas Kp = 0 : limite exacte (BESQ de dimension n_eff), pas une limite numérique.
    """
    if t <= 0:
        return 1.0 if x0 <= x else 0.0

    kappa, _theta, sigma = cir_params(n_eff, D, Kp)
    sigma_sq = sigma**2

    if Kp == 0.0:
        # Limite BESQ exacte (κ → 0, κθ = 2 n_eff D fixé)
        c = sigma_sq * t / 4.0
        df = n_eff
        nc = 4.0 * x0 / (sigma_sq * t) if x0 > 0 else 0.0
    else:
        emkt = math.exp(-kappa * t)
        c = sigma_sq * (1.0 - emkt) / (4.0 * kappa)
        df = 4.0 * kappa * _theta / sigma_sq  # = n_eff (κθ = 2·n_eff·D est constant par construction)
        nc = (4.0 * kappa * x0 * emkt) / (sigma_sq * (1.0 - emkt)) if x0 > 0 else 0.0

    if c <= 0:
        return 1.0 if x0 <= x else 0.0
    return float(ncx2.cdf(x / c, df, nc))


def survival_probability(Y_max: float, t: float, r0: float, n_eff: float, D: float, Kp: float) -> float:
    """P(r(t) < Y_max | r(0) = r0) — approximation semi-analytique (voir avertissement du module)."""
    return transition_cdf(Y_max**2, t, r0**2, n_eff, D, Kp)


def first_passage_time(
    Y_max: float,
    r0: float,
    n_eff: float,
    D: float,
    Kp: float = 0.0,
    quantile: float = 0.5,
    t_search_max: float = 1e9,
) -> float:
    """
    Estimation semi-analytique du temps de rupture t_rupture^Bessel(n).

    Défini comme le temps t tel que P(r(t) < Y_max) = quantile (par défaut,
    le temps médian de rupture). Résolu par recherche de racine sur
    `survival_probability`, sans simulation de trajectoires.

    Retourne +inf si le système est régulé (Kp > 0) et que la probabilité de
    survie ne descend jamais sous `quantile` (régime stable : Y_max est hors
    d'atteinte à ce niveau de confiance).
    """
    if Y_max <= r0:
        return 0.0

    def f(t: float) -> float:
        return survival_probability(Y_max, t, r0, n_eff, D, Kp) - quantile

    if f(t_search_max) > 0:
        return math.inf  # jamais de rupture à ce quantile dans l'horizon exploré

    # Recherche de borne haute par doublement, puis bissection.
    t_lo, t_hi = 1e-6, 1.0
    while f(t_hi) > 0 and t_hi < t_search_max:
        t_lo = t_hi
        t_hi *= 2.0

    if f(t_hi) > 0:
        return math.inf

    return float(brentq(f, t_lo, t_hi, xtol=1e-6))
