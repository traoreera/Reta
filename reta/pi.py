"""
Correcteur PI adaptatif RETA — lois gradient prouvables par Lyapunov + Barbalat.

Cf. docs/1_fondamentaux/theorie_fondamentale.md §10.2 et
docs/1_fondamentaux/reponses_critiques.md Critiques 1 et 5.

    u(t) = Kp·e(t) + Ki·∫e(τ)dτ

Lois gradient (recommandées, stables) :
    K̇p = γp · ē²
    K̇i = γi · ē · Ī            avec ē = e / e_ref, Ī = ∫ē dτ

Saturation impérative : Kp, Ki restent dans des bornes strictement positives
pour éviter la perte de réactivité (borne basse) et l'emballement (borne haute).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PIRegulator:
    Kp: float = 2.0
    Ki: float = 1.0

    gamma_p: float = 0.2
    gamma_i: float = 0.05
    e_ref: float = 1.0

    Kp_min: float = 1e-3
    Kp_max: float = 1e3
    Ki_min: float = 1e-3
    Ki_max: float = 1e3

    adaptive: bool = True

    _integral: float = 0.0
    _integral_norm: float = 0.0  # Ī = ∫ē dτ

    def reset(self) -> None:
        self._integral = 0.0
        self._integral_norm = 0.0

    def step(self, error: float, dt: float = 1.0) -> float:
        """Un pas de régulation. Retourne u(t). Met à jour Kp, Ki si adaptive."""
        e_bar = error / self.e_ref
        self._integral += error * dt
        self._integral_norm += e_bar * dt

        u = self.Kp * error + self.Ki * self._integral

        if self.adaptive:
            dKp = self.gamma_p * e_bar**2
            dKi = self.gamma_i * e_bar * self._integral_norm
            self.Kp = min(max(self.Kp + dKp * dt, self.Kp_min), self.Kp_max)
            self.Ki = min(max(self.Ki + dKi * dt, self.Ki_min), self.Ki_max)

        return u

    @property
    def integral(self) -> float:
        return self._integral
