"""
RETAReferential — référentiel RETA complet.

y(t) = arctan(t) + ∫₀ᵗ z(τ) dτ

Un référentiel encapsule :
  - la perturbation estimée z(t) via Kalman
  - la phase courante (BULL / BEAR / NEUTRE)
  - le temps de rupture t_rup
  - l'encodage compact (4 scalaires) pour DB / LLM
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass, field
from typing import Literal

from .kalman import Kalman1D, KalmanAdaptive


Phase = Literal["BULL", "BEAR", "NEUTRE"]


@dataclass
class RETAReferential:
    # Version RETA (doc theorie_fondamentale.md §récapitulatif)
    # "v1.1" : Kalman fixe + PI fixe
    # "v1.2" : Kalman fixe + PI gradient (adaptive=True dans PIRegulator)
    # "v1.3" : KalmanAdaptive (Q,R auto) + PI gradient
    # "v1.4" : KalmanAdaptive + bound quadratique conservatif via ż
    version: str = "v1.4"

    # Paramètres Kalman
    Q: float = 2e-5
    R: float = 5e-4
    # Paramètres adaptatifs v1.3 / v1.4
    kalman_alpha: float = 0.97
    kalman_beta:  float = 0.95

    # Paramètres détection phase
    eps: float = 0.0008
    window: int = 24          # barres pour z_moy
    t_confirm: int = 12       # barres de confirmation

    # Paramètre bound v1.4
    delta_log_max: float = 0.20   # horizon max en log-space (ex: 20%)

    # Résultats (remplis par fit)
    z_est:  np.ndarray = field(default_factory=lambda: np.array([]))
    z_moy:  np.ndarray = field(default_factory=lambda: np.array([]))
    p_var:  np.ndarray = field(default_factory=lambda: np.array([]))
    log_pred: np.ndarray = field(default_factory=lambda: np.array([]))
    phases:   np.ndarray = field(default_factory=lambda: np.array([]))

    # Résumé scalaire
    phase:  Phase = "NEUTRE"
    z_last: float = 0.0
    eps_cur: float = 0.0
    t_rup:  float = 0.0
    P_inf:  float = 0.0
    n:      int   = 0

    # Série source (log-prix ou log-rendements)
    _log_prix: np.ndarray = field(default_factory=lambda: np.array([]), repr=False)

    # ── Fit ───────────────────────────────────────────────────────────────────

    def fit(self, series: np.ndarray, is_price: bool = True) -> "RETAReferential":
        """
        Ajuste le référentiel sur une série.

        series   : prix (is_price=True) ou log-rendements (is_price=False)
        Retourne : self (chainable)
        """
        prices = np.asarray(series, dtype=float)
        if is_price:
            log_prix  = np.log(prices)
            log_ret   = np.diff(log_prix, prepend=log_prix[0])
        else:
            log_ret   = prices
            log_prix  = np.cumsum(log_ret)

        self.n         = len(log_ret)
        self._log_prix = log_prix

        # Kalman — v1.1 fixe, v1.3 adaptatif, v1.4 adaptatif + ż
        is_v14 = self.version == "v1.4"
        if self.version in ("v1.3", "v1.4"):
            kalman = KalmanAdaptive(
                Q=self.Q, R=self.R,
                alpha=self.kalman_alpha, beta=self.kalman_beta,
            )
        else:
            kalman = Kalman1D(Q=self.Q, R=self.R)
        self.z_est, self.p_var = kalman.batch(log_ret)
        self._kalman = kalman
        self.P_inf = float(self.p_var[-min(60, self.n // 4):].mean())
        self.dz_last = float(kalman.dz) if hasattr(kalman, "dz") else 0.0

        # Moyenne glissante causale
        self.z_moy = Kalman1D.rolling_mean(self.z_est, self.window)

        # Prédiction accumulée (recalibration toutes les `window` barres)
        self.log_pred = self._build_prediction(log_prix)

        # Détection de phase (machine d'état avec hysteresis)
        self.phases = self._detect_phases()

        # Résumé scalaire
        self.z_last  = float(self.z_moy[-1])
        self.eps_cur = self.eps
        _phase_int   = int(self.phases[-1])
        self.phase   = "BULL" if _phase_int == 1 else ("BEAR" if _phase_int == -1 else "NEUTRE")

        # t_rup — v1.4 quadratique, sinon linéaire
        if is_v14 and self.dz_last > 0:
            # z0·T + ½·ż·T² = Δlog_max  → T = (-z0 + √(z0² + 2·ż·Δ)) / ż
            z0 = self.z_last
            dz = self.dz_last
            disc = z0 ** 2 + 2.0 * dz * self.delta_log_max
            if disc > 0:
                self.t_rup = (-z0 + np.sqrt(disc)) / max(dz, 1e-12)
            else:
                self.t_rup = self.delta_log_max / max(abs(z0), 1e-8)
        else:
            # Formule linéaire v1.1–v1.3
            self.t_rup = self.delta_log_max / max(abs(self.z_last), 1e-8)

        return self

    # ── Prédiction ────────────────────────────────────────────────────────────

    def _build_prediction(self, log_prix: np.ndarray) -> np.ndarray:
        """Accumule z_moy avec recalibration périodique pour éviter la dérive."""
        lp = np.zeros(self.n)
        lp[0] = log_prix[0]
        for i in range(1, self.n):
            if i % self.window == 0:
                lp[i] = log_prix[i]          # ancrage au vrai prix
            else:
                lp[i] = lp[i - 1] + self.z_moy[i]
        return lp

    def predict(self, steps: int = 24) -> np.ndarray:
        """Prédit `steps` barres dans le futur depuis z_last."""
        future = np.zeros(steps)
        future[0] = self._log_prix[-1] if len(self._log_prix) else 0.0
        for i in range(1, steps):
            future[i] = future[i - 1] + self.z_last
        return np.exp(future)

    # ── Détection de phase ────────────────────────────────────────────────────

    def _detect_phases(self) -> np.ndarray:
        phases = np.zeros(self.n)
        cpt, etat = 0, 0
        for i in range(self.n):
            z = self.z_moy[i]
            if z > self.eps:
                cpt = cpt + 1 if etat != 1 else 0
                if cpt >= self.t_confirm:
                    etat, cpt = 1, 0
            elif z < -self.eps:
                cpt = cpt + 1 if etat != -1 else 0
                if cpt >= self.t_confirm:
                    etat, cpt = -1, 0
            else:
                cpt = 0
            phases[i] = etat
        return phases

    # ── Encodage compact (DB / LLM) ───────────────────────────────────────────

    def encode(self) -> dict:
        """Scalaires du référentiel pour stockage DB / LLM (JSON-friendly)."""
        return {
            "eps":     float(round(self.eps_cur, 8)),
            "z_last":  float(round(self.z_last, 8)),
            "dz_last": float(round(getattr(self, "dz_last", 0.0), 8)),
            "t_rup":   float(round(self.t_rup,  2)),
            "phase":   self.phase,
            "P_inf":   float(round(self.P_inf,  8)),
            "n":       int(self.n),
            "version": self.version,
        }

    @classmethod
    def from_encoded(cls, payload: dict) -> "RETAReferential":
        """
        Reconstruit un référentiel minimal depuis un payload DB.
        z_est / z_moy / p_var ne sont pas disponibles — uniquement
        les scalaires de résumé (suffisant pour fusion et navigation O(1)).
        """
        ref          = cls(eps=payload.get("eps", 0.0008), version=payload.get("version", "v1.4"))
        ref.z_last   = payload["z_last"]
        ref.dz_last  = payload.get("dz_last", 0.0)
        ref.eps_cur  = payload["eps"]
        ref.t_rup    = payload["t_rup"]
        ref.phase    = payload["phase"]
        ref.P_inf    = payload.get("P_inf", 0.0)
        ref.n        = payload.get("n", 0)
        ref.z_moy    = np.array([ref.z_last])
        ref.z_est    = np.array([ref.z_last])
        return ref

    # ── Opérateur ⊕ ───────────────────────────────────────────────────────────

    def __add__(self, other: "RETAReferential") -> "RETAReferential":
        """Fusion équilibrée : α=0.5. Utiliser fusion() pour un α personnalisé."""
        from .fusion import fusion
        return fusion(self, other, alpha=0.5)

    def __repr__(self) -> str:
        kalman_info = ""
        if self.version in ("v1.3", "v1.4") and hasattr(self, "_kalman"):
            k = self._kalman
            kalman_info = f", R={k.R_current:.2e}, Q={k.Q_current:.2e}, quality={k.signal_quality:.3f}"
        dz_info = f", dz={self.dz_last:.6f}" if "v1.4" in self.version else ""
        return (f"RETAReferential({self.version}, phase={self.phase}, "
                f"z_last={self.z_last:.6f}, eps={self.eps_cur:.6f}, "
                f"t_rup={self.t_rup:.1f}, n={self.n}{dz_info}{kalman_info})")
