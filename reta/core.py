"""
RETA classique (v1.4) — cœur scalaire.

Cf. docs/1_fondamentaux/theorie_fondamentale.md (équations maîtresses) et
docs/v1.4/README.md (bound conservatif par tracking ż).

Modèle :
    y(t)      = f(t) + ∫ z(τ) dτ                      (trajectoire libre)
    e(t)      = y(t) − Y_consigne
    u(t)      = Kp·e(t) + Ki·∫e(τ)dτ                   (PI adaptatif)
    y_réel(t) = y(t) − u(t)                            (trajectoire régulée)

z(t) et ż(t) sont estimés en continu par un KalmanAdaptive sur les
observations r_k (une mesure qui approxime z directement, ex. un
log-rendement). Le temps de rupture utilise la borne quadratique v1.4 :

    T = (−z0 + √(z0² + 2·ż0·(Y_max − y0))) / ż0
    t_rupture = t_now + T

qui se réduit à la borne linéaire v1.0 (T = (Y_max−y0)/z0) quand ż0 → 0.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable

import numpy as np

from .kalman import KalmanAdaptive
from .pi import PIRegulator


@dataclass
class StepResult:
    t: float
    z_hat: float
    dz_hat: float
    y_open: float      # trajectoire libre y(t) = f(t) + ∫z
    e: float            # erreur y_open - Yc
    u: float             # commande PI
    y_real: float       # trajectoire régulée y_open - u
    Kp: float
    Ki: float


class RETAReferential:
    """Référentiel RETA scalaire, version v1.4 (Kalman adaptatif + PI gradient + bound conservatif)."""

    def __init__(
        self,
        Y_max: float,
        Yc: float = 0.0,
        f0: Callable[[float], float] | None = math.atan,
        dt: float = 1.0,
        Q_init: float = 2e-5,
        R_init: float = 5e-4,
        kalman_alpha: float = 0.97,
        kalman_beta: float = 0.95,
        Kp0: float = 2.0,
        Ki0: float = 1.0,
        gamma_p: float = 0.2,
        gamma_i: float = 0.05,
        e_ref: float | None = None,
        adaptive_pi: bool = True,
    ):
        self.Y_max = Y_max
        self.Yc = Yc
        self.f0 = f0
        self.dt = dt

        self.kalman = KalmanAdaptive(
            Q_init=Q_init, R_init=R_init, alpha=kalman_alpha, beta=kalman_beta, dt=dt
        )
        self.pi = PIRegulator(
            Kp=Kp0,
            Ki=Ki0,
            gamma_p=gamma_p,
            gamma_i=gamma_i,
            e_ref=e_ref if e_ref is not None else max(abs(Y_max - Yc), 1e-9),
            adaptive=adaptive_pi,
        )

        self.t: float = 0.0
        self._y_acc: float = 0.0  # ∫ z_hat dτ accumulé
        self.history: list[StepResult] = []

    def reset(self) -> None:
        self.kalman.reset()
        self.pi.reset()
        self.t = 0.0
        self._y_acc = 0.0
        self.history.clear()

    def step(self, r_obs: float) -> StepResult:
        """Un pas : observation r_obs (mesure approximant z) → StepResult."""
        z_hat, dz_hat = self.kalman.update(r_obs)
        self._y_acc += z_hat * self.dt
        self.t += self.dt

        base = self.f0(self.t) if self.f0 is not None else 0.0
        y_open = base + self._y_acc
        e = y_open - self.Yc
        u = self.pi.step(e, self.dt)
        y_real = y_open - u

        result = StepResult(
            t=self.t, z_hat=z_hat, dz_hat=dz_hat, y_open=y_open, e=e, u=u,
            y_real=y_real, Kp=self.pi.Kp, Ki=self.pi.Ki,
        )
        self.history.append(result)
        return result

    def fit(self, observations: np.ndarray) -> list[StepResult]:
        """Applique `step` séquentiellement sur un tableau d'observations."""
        return [self.step(float(r)) for r in observations]

    def t_rupture(self, epsilon_floor: float = 1e-9) -> float:
        """
        Borne conservative v1.4 (quadratique, extrapolation via ż).

        Retourne +inf si le modèle linéaire actuel (z0, ż0) ne prédit jamais
        d'atteindre Y_max (ż0 < 0 assez fort pour que le discriminant soit négatif).
        """
        if not self.history:
            raise RuntimeError("t_rupture() nécessite au moins un step()")

        last = self.history[-1]
        z0, zd0, y0 = last.z_hat, last.dz_hat, last.y_open
        rem = self.Y_max - y0

        if rem <= 0:
            return last.t  # déjà rompu

        if abs(zd0) < epsilon_floor:
            # fallback v1.0 : borne linéaire
            if z0 <= epsilon_floor:
                return math.inf
            return last.t + rem / z0

        disc = z0**2 + 2 * zd0 * rem
        if disc < 0:
            return math.inf  # tendance décroissante trop forte : pas de rupture prédite

        T = (-z0 + math.sqrt(disc)) / zd0
        if T < 0:
            return math.inf
        return last.t + T
