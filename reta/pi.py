"""
PIRegulator — régulateur PI pour stabiliser la dérive RETA.

u(t) = Kp · e(t) + Ki · ∫₀ᵗ e(τ) dτ

Versions (doc : theorie_fondamentale.md section 10) :

  v1.0 — gains fixes (Kp, Ki constants)
  v1.1 — identique v1.0, utilisé avec Kalman en amont
  v1.2 heuristique — K̇p = γp·(|e|−θ),  K̇i = γi·|e|·sgn(∫e)
                     Réactif, non garanti stable (non-LTI)
  v1.2 gradient    — K̇p = γp·e²,  K̇i = γi·e·∫e
                     Stabilité asymptotique garantie par Lyapunov (recommandé)

Temps caractéristiques (section 5.2) :
  t_stable ≈ 8 / Kp
  Condition : t_montee < t_stable < t_rupture

Condition de stabilité (Routh) : Kp > 0 et Ki > 0
Bande résiduelle (Lyapunov) : |e(∞)| ≤ (3 + √2) / Kp ≈ 4.41 / Kp

Doc : docs/1_fondamentaux/theorie_fondamentale.md — sections 4, 5, 6, 10
"""

from __future__ import annotations
import math
import numpy as np


class PIRegulator:
    def __init__(
        self,
        kp: float = 0.12,
        ki: float = 0.002,
        integral_clip: float = 10.0,
        # v1.2 gradient (recommandé — Lyapunov stable)
        adaptive: bool = False,
        gamma_p: float = 0.50,
        gamma_i: float = 0.20,
        kp_min: float = 1e-4,
        kp_max: float = 10.0,
        ki_min: float = 1e-6,
        ki_max: float = 1.0,
        # v1.2 heuristique (non recommandé en production)
        heuristic: bool = False,
        theta: float = 0.05,   # bande morte pour K̇p heuristique
    ):
        self.kp            = kp
        self.ki            = ki
        self.integral_clip = integral_clip
        self.adaptive      = adaptive
        self.heuristic     = heuristic
        self.gamma_p       = gamma_p
        self.gamma_i       = gamma_i
        self.kp_min        = kp_min
        self.kp_max        = kp_max
        self.ki_min        = ki_min
        self.ki_max        = ki_max
        self.theta         = theta

        self._integral = 0.0
        self._u        = 0.0

    def step(self, error: float, dt: float = 1.0) -> float:
        """Un pas de régulation. Retourne u(t)."""
        self._integral = float(np.clip(
            self._integral + error * dt,
            -self.integral_clip,
            self.integral_clip,
        ))

        if self.adaptive:
            # Lois gradient v1.2 — Lyapunov stable (recommandé)
            # K̇p = γp · e²
            # K̇i = γi · e · ∫e dτ
            self.kp = float(np.clip(
                self.kp + self.gamma_p * error ** 2 * dt,
                self.kp_min, self.kp_max,
            ))
            self.ki = float(np.clip(
                self.ki + self.gamma_i * error * self._integral * dt,
                self.ki_min, self.ki_max,
            ))
        elif self.heuristic:
            # Lois heuristiques v1.2 — réactif, non garanti stable
            # K̇p = γp · (|e| − θ)
            # K̇i = γi · |e| · sgn(∫e)
            self.kp = float(np.clip(
                self.kp + self.gamma_p * (abs(error) - self.theta) * dt,
                self.kp_min, self.kp_max,
            ))
            sgn_integral = math.copysign(1.0, self._integral) if self._integral != 0 else 0.0
            self.ki = float(np.clip(
                self.ki + self.gamma_i * abs(error) * sgn_integral * dt,
                self.ki_min, self.ki_max,
            ))

        self._u = self.kp * error + self.ki * self._integral
        return self._u

    def batch(self, errors: np.ndarray, dt: float = 1.0) -> np.ndarray:
        """Traite une série d'erreurs. Réinitialise l'état interne."""
        self.reset()
        return np.array([self.step(float(e), dt) for e in errors])

    def reset(self) -> None:
        self._integral = 0.0
        self._u        = 0.0

    @property
    def t_stable(self) -> float:
        """Temps de stabilisation estimé : t_stable ≈ 8 / Kp (section 5.2)."""
        return 8.0 / self.kp if self.kp > 0 else float("inf")

    @property
    def residual_band(self) -> float:
        """Bande résiduelle Lyapunov : |e(∞)| ≤ (3 + √2) / Kp (section 6.2)."""
        return (3.0 + math.sqrt(2.0)) / self.kp if self.kp > 0 else float("inf")

    @property
    def regime(self) -> str:
        """Régime d'amortissement selon Ki vs Kp²/4 (section 7.1)."""
        threshold = self.kp ** 2 / 4.0
        if self.ki > threshold:
            return "sous-amorti (rapide, oscillant)"
        elif abs(self.ki - threshold) < 1e-9:
            return "critique (optimal)"
        else:
            return "sur-amorti (lent, sans oscillation)"

    @property
    def signal(self) -> float:
        return self._u

    @property
    def integral(self) -> float:
        return self._integral

    def __repr__(self) -> str:
        mode = "gradient" if self.adaptive else ("heuristique" if self.heuristic else "fixe")
        return (f"PIRegulator(kp={self.kp:.4f}, ki={self.ki:.4f}, mode={mode}, "
                f"t_stable={self.t_stable:.1f}, u={self._u:.6f})")
