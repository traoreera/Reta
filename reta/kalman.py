"""
Filtres de Kalman RETA — estimation de l'état [z, ż].

Cf. docs/1_fondamentaux/theorie_fondamentale.md §8 (modèle position-vitesse)
et §11.1 (séquence d'adaptation Q/R par innovation).

Modèle d'espace d'état commun aux deux filtres :

    x_{k+1} = A x_k + w_k,   A = [[1, dt], [0, 1]],   w_k ~ N(0, Q)
    r_k     = H x_k + v_k,   H = [1, 0],              v_k ~ N(0, R)

x = [z, ż] : la perturbation et sa dérivée. On observe r_k (ex. un
log-rendement), qui approxime z_k directement.
"""

from __future__ import annotations

import numpy as np


class Kalman1D:
    """Kalman à gains fixes (Q, R constants) sur l'état [z, ż]."""

    def __init__(self, Q: float = 2e-5, R: float = 5e-4, dt: float = 1.0):
        self.dt = dt
        self.A = np.array([[1.0, dt], [0.0, 1.0]])
        self.H = np.array([[1.0, 0.0]])
        self.Q = np.diag([Q, Q * 0.1])
        self.R = np.array([[R]])
        self.x = np.zeros((2, 1))
        self.P = np.eye(2) * 1.0

    def reset(self, x0: float = 0.0, dz0: float = 0.0) -> None:
        self.x = np.array([[x0], [dz0]])
        self.P = np.eye(2) * 1.0

    def update(self, r_k: float) -> tuple[float, float]:
        """Un pas prédiction + correction. Retourne (z_hat, dz_hat)."""
        x_pred = self.A @ self.x
        P_pred = self.A @ self.P @ self.A.T + self.Q

        S = self.H @ P_pred @ self.H.T + self.R
        K = P_pred @ self.H.T @ np.linalg.inv(S)

        innovation = r_k - (self.H @ x_pred)[0, 0]
        self.x = x_pred + K * innovation
        self.P = (np.eye(2) - K @ self.H) @ P_pred

        return float(self.x[0, 0]), float(self.x[1, 0])

    def batch(self, observations: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Applique `update` séquentiellement. Retourne (z_hat[], P00[])."""
        n = len(observations)
        z_hat = np.empty(n)
        p00 = np.empty(n)
        for k, r_k in enumerate(observations):
            self.update(float(r_k))
            z_hat[k] = self.x[0, 0]
            p00[k] = self.P[0, 0]
        return z_hat, p00

    @property
    def z(self) -> float:
        return float(self.x[0, 0])

    @property
    def dz(self) -> float:
        return float(self.x[1, 0])

    @staticmethod
    def rolling_mean(x: np.ndarray, window: int) -> np.ndarray:
        """Moyenne mobile causale (O(1) par pas), utilisée pour z̄(T)."""
        out = np.empty(len(x))
        cumsum = 0.0
        for i, v in enumerate(x):
            cumsum += v
            if i >= window:
                cumsum -= x[i - window]
            out[i] = cumsum / min(i + 1, window)
        return out


class KalmanAdaptive(Kalman1D):
    """
    Kalman auto-adaptatif (Q, R) — v1.3/v1.4 "Caméléon".

    Séquence impérative (theorie_fondamentale.md §11.1) :
      1. prédire
      2. adapter R depuis l'innovation (avant le gain)
      3. calculer le gain avec R adapté
      4. corriger l'état
      5. adapter Q depuis l'innovation déjà utilisée (pas d'équation implicite)
    """

    def __init__(
        self,
        Q_init: float = 2e-5,
        R_init: float = 5e-4,
        alpha: float = 0.97,
        beta: float = 0.95,
        dt: float = 1.0,
    ):
        super().__init__(Q=Q_init, R=R_init, dt=dt)
        self.alpha = alpha
        self.beta = beta
        self.R_current = R_init
        self.Q_current = Q_init

    def update(self, r_k: float) -> tuple[float, float]:
        x_pred = self.A @ self.x
        P_pred = self.A @ self.P @ self.A.T + self.Q

        innovation = r_k - (self.H @ x_pred)[0, 0]

        # 2. Adapter R avant le gain
        HPHt = float((self.H @ P_pred @ self.H.T)[0, 0])
        R_inst = innovation**2 + HPHt
        self.R_current = self.alpha * self.R_current + (1 - self.alpha) * R_inst
        self.R = np.array([[max(self.R_current, 1e-12)]])

        # 3. Gain avec R adapté
        S = self.H @ P_pred @ self.H.T + self.R
        K = P_pred @ self.H.T @ np.linalg.inv(S)

        # 4. Correction
        self.x = x_pred + K * innovation
        self.P = (np.eye(2) - K @ self.H) @ P_pred

        # 5. Adapter Q après correction (trace du produit scalaire, pas la matrice complète)
        K_norm_sq = float((K.T @ K)[0, 0])
        Q_inst = K_norm_sq * innovation**2
        self.Q_current = self.beta * self.Q_current + (1 - self.beta) * Q_inst
        self.Q = np.diag([max(self.Q_current, 1e-15), max(self.Q_current, 1e-15) * 0.1])

        return float(self.x[0, 0]), float(self.x[1, 0])

    @property
    def signal_quality(self) -> float:
        """Proportion de variance expliquée par le modèle vs le bruit, dans [0, 1]."""
        total = self.Q_current + self.R_current
        if total <= 0:
            return 0.0
        return float(np.clip(self.Q_current / total, 0.0, 1.0))
