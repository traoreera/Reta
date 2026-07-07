"""
Kalman — estimateur de la perturbation persistante z(t) et de sa vitesse ż(t).

État : x = [z, ż]
  z  = perturbation courante (log-rendement lissé)
  ż  = vitesse de dérive

Modèle :
  x_{k+1} = A x_k + bruit processus (Q)
  y_k     = H x_k + bruit mesure    (R)

A = [[1, 1],   H = [[1, 0]]
     [0, 1]]

Versions (doc : theorie_fondamentale.md) :

  Kalman1D        — v1.1 : Q et R fixes, Riccati standard
  KalmanAdaptive  — v1.3 : Q et R auto-ajustés depuis les innovations νₖ

    Adaptation R (bruit mesure) :
      R̂ₖ = α·R̂ₖ₋₁ + (1−α)·(νₖ² + H·Pₖ|ₖ₋₁·Hᵀ)
      → Si le signal est bruité, R monte → filtre plus prudent

    Adaptation Q (bruit processus) :
      Q̂ₖ = β·Q̂ₖ₋₁ + (1−β)·Gₖ·νₖ²·Gₖᵀ   où Gₖ = gain Kalman
      → Si le modèle RETA dévie, Q monte → plus de flexibilité

    Cycle v1.3 (doc §11.2) :
      1. Ajuster R (clarté du signal)
      2. Ajuster Q (validité du modèle)
      3. Extraire [ẑ, ż] optimal
      4. Calculer réponse PI adaptée
      5. Prédire t_rupture auto-calibré
"""

from __future__ import annotations
import numpy as np


class Kalman1D:
    def __init__(self, Q: float = 2e-5, R: float = 5e-4):
        self.Q = Q
        self.R = R
        self._A  = np.array([[1.0, 1.0], [0.0, 1.0]])
        self._H  = np.array([[1.0, 0.0]])
        self._Qm = np.diag([Q, Q * 0.1])
        self._Rm = np.array([[R]])
        self._x  = None
        self._P  = None

    def reset(self, z0: float = 0.0) -> None:
        self._x = np.array([z0, 0.0])
        self._P = np.eye(2) * 2.0

    def update(self, obs: float) -> float:
        """Met à jour avec une nouvelle observation. Retourne z_est."""
        if self._x is None:
            self.reset(obs)
            return obs

        x, P = self._x, self._P
        x = self._A @ x
        P = self._A @ P @ self._A.T + self._Qm

        S = float((self._H @ P @ self._H.T + self._Rm)[0, 0])
        K = (P @ self._H.T).flatten() / S
        innov = obs - float((self._H @ x)[0])
        x = x + K * innov
        P = (np.eye(2) - np.outer(K, self._H)) @ P

        self._x, self._P = x, P
        return float(x[0])

    def batch(self, series: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Traite une série complète. Retourne (z_est, p_var)."""
        self.reset(float(series[0]))
        z_est = np.zeros(len(series))
        p_var = np.zeros(len(series))
        for k, o in enumerate(series):
            z_est[k] = self.update(float(o))
            p_var[k] = float(self._P[0, 0])
        return z_est, p_var

    @property
    def z(self) -> float:
        """Estimation courante de z."""
        return float(self._x[0]) if self._x is not None else 0.0

    @property
    def dz(self) -> float:
        """Estimation courante de ż (vitesse de dérive)."""
        return float(self._x[1]) if self._x is not None else 0.0

    @property
    def P_inf(self) -> float | None:
        """Variance de Riccati courante sur z."""
        return float(self._P[0, 0]) if self._P is not None else None

    @staticmethod
    def rolling_mean(z_est: np.ndarray, window: int = 24) -> np.ndarray:
        """Moyenne glissante causale O(n) via somme cumulée."""
        cum = np.cumsum(z_est)
        out = np.empty(len(z_est))
        for i in range(len(z_est)):
            left = max(0, i - window + 1)
            out[i] = (cum[i] - cum[left - 1]) / (i - left + 1) if left > 0 else cum[i] / (i + 1)
        return out


class KalmanAdaptive(Kalman1D):
    """
    Kalman v1.3 — Chameleon RETA.

    Q et R s'auto-ajustent depuis la séquence d'innovation νₖ = y_mesuré − H·x̂ₖ|ₖ₋₁
    Le système "apprend" la physique de son environnement sans paramétrage préalable.

    Paramètres :
      alpha  : fenêtre exponentielle pour R  (0.95–0.99 recommandé)
      beta   : fenêtre exponentielle pour Q  (0.90–0.98 recommandé)
      R_min  : plancher de R (évite sur-confiance)
      Q_min  : plancher de Q (évite rigidité totale du modèle)

    Doc : theorie_fondamentale.md §11
    """

    def __init__(
        self,
        Q: float = 2e-5,
        R: float = 5e-4,
        alpha: float = 0.97,   # fenêtre adaptation R
        beta:  float = 0.95,   # fenêtre adaptation Q
        R_min: float = 1e-6,
        Q_min: float = 1e-8,
    ):
        super().__init__(Q=Q, R=R)
        self.alpha  = alpha
        self.beta   = beta
        self.R_min  = R_min
        self.Q_min  = Q_min
        self._R_hat = R       # R courant auto-ajusté
        self._Q_hat = Q       # Q courant auto-ajusté
        self._innov_sq = 0.0  # innovation² lissée (pour monitoring)

    def update(self, obs: float) -> float:
        """
        Un pas Kalman adaptatif v1.3.
        Cycle : Adapter R → Adapter Q → Prédire → Corriger.
        """
        if self._x is None:
            self.reset(obs)
            self._R_hat = self.R
            self._Q_hat = self.Q
            return obs

        # ── Prédiction ────────────────────────────────────────────────────
        x_pred = self._A @ self._x
        P_pred = self._A @ self._P @ self._A.T + self._Qm

        # ── Innovation ────────────────────────────────────────────────────
        innov = obs - float((self._H @ x_pred)[0])
        HP_HT = float((self._H @ P_pred @ self._H.T)[0, 0])

        # ── 1. Adapter R (bruit mesure) ───────────────────────────────────
        # R̂ₖ = α·R̂ₖ₋₁ + (1−α)·(νₖ² + H·Pₖ|ₖ₋₁·Hᵀ)
        self._R_hat = max(
            self.alpha * self._R_hat + (1 - self.alpha) * (innov ** 2 + HP_HT),
            self.R_min,
        )
        self._Rm = np.array([[self._R_hat]])

        # ── Gain Kalman avec R adapté ─────────────────────────────────────
        S = HP_HT + self._R_hat
        K = (P_pred @ self._H.T).flatten() / S

        # ── Correction ────────────────────────────────────────────────────
        x = x_pred + K * innov
        P = (np.eye(2) - np.outer(K, self._H)) @ P_pred

        # ── 2. Adapter Q (bruit processus) ────────────────────────────────
        # Q̂ₖ = β·Q̂ₖ₋₁ + (1−β)·Gₖ·νₖ²·Gₖᵀ
        outer_K = np.outer(K, K) * innov ** 2
        Q_update = self.beta * self._Q_hat + (1 - self.beta) * float(np.trace(outer_K))
        self._Q_hat = max(Q_update, self.Q_min)
        self._Qm    = np.diag([self._Q_hat, self._Q_hat * 0.1])

        self._innov_sq = self.alpha * self._innov_sq + (1 - self.alpha) * innov ** 2
        self._x, self._P = x, P
        return float(x[0])

    @property
    def R_current(self) -> float:
        """R auto-ajusté courant."""
        return self._R_hat

    @property
    def Q_current(self) -> float:
        """Q auto-ajusté courant."""
        return self._Q_hat

    @property
    def signal_quality(self) -> float:
        """
        Qualité du signal ∈ [0, 1].
        Proche de 1 → signal clair (R petit).
        Proche de 0 → signal bruité (R grand).
        """
        return 1.0 / (1.0 + self._R_hat / self.R_min)

    def __repr__(self) -> str:
        return (f"KalmanAdaptive(z={self.z:.6f}, dz={self.dz:.6f}, "
                f"R={self._R_hat:.2e}, Q={self._Q_hat:.2e}, "
                f"quality={self.signal_quality:.3f})")
