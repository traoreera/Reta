"""
RETA-nD — référentiel n-dimensionnel.

Compose n axes RETA classiques (un `RETAReferential` indépendant par
composante) et ajoute la couche de dispersion (`dispersion.py`) pour le
temps de rupture "norme jointe" (processus de Bessel/CIR).

Deux notions de rupture, à ne pas confondre (cf.
docs/2_extensions_theoriques/extension_dimensionnelle.md §3 et
docs/2_extensions_theoriques/reta_nd_dispersion.md §4) :

- **Pavé** (seuils indépendants par axe) : `t_rupture_box()` — le
  système casse dès qu'UN axe dépasse SON seuil. C'est `min_i(t_rupture_i)`,
  exact dans ce cas. Ex. : drone avec tolérances 5°/5°/10° par axe.

- **Boule/ellipsoïde** (norme jointe) : `t_rupture_joint()` — le système
  casse quand la NORME de l'erreur dépasse un seuil commun. `min_i` est
  alors optimiste (biaisé) ; la borne correcte est le premier passage du
  processus de Bessel(n_eff), approximé ici via le pont CIR.

**Condition de validité de `t_rupture_joint`** (liste de validité,
reta_nd_dispersion.md §4) : régulation isotrope (Kp identique par axe),
bruit résiduel isotrope entre composantes (ou rendu isotrope par
transformation de Mahalanobis), et critère physique de rupture qui est
réellement une norme jointe — pas un pavé. Ne pas l'utiliser hors de ce
périmètre.
"""

from __future__ import annotations

import math

import numpy as np

from .core import RETAReferential
from .dispersion import effective_dimension, first_passage_time


class RETAND:
    """Référentiel RETA-nD : n axes RETA classiques + couche de dispersion."""

    def __init__(
        self,
        n: int,
        Y_max_axes: list[float],
        dt: float = 1.0,
        axis_kwargs: list[dict] | None = None,
    ):
        if len(Y_max_axes) != n:
            raise ValueError("Y_max_axes doit avoir n éléments")
        axis_kwargs = axis_kwargs or [{}] * n
        self.n = n
        self.dt = dt
        self.axes: list[RETAReferential] = [
            RETAReferential(Y_max=Y_max_axes[i], dt=dt, **axis_kwargs[i]) for i in range(n)
        ]

    def reset(self) -> None:
        for axis in self.axes:
            axis.reset()

    def step(self, r_obs: np.ndarray) -> list:
        """Un pas sur toutes les composantes. r_obs : vecteur de n observations."""
        if len(r_obs) != self.n:
            raise ValueError(f"r_obs doit avoir {self.n} composantes")
        return [axis.step(float(r_obs[i])) for i, axis in enumerate(self.axes)]

    def fit(self, observations: np.ndarray) -> list[list]:
        """observations : tableau (T, n). Applique `step` T fois."""
        return [self.step(row) for row in observations]

    # ── Rupture "pavé" (seuils indépendants) ─────────────────────────────

    def t_rupture_box(self) -> float:
        """min_i(t_rupture_i) — exact si le critère de rupture est un pavé."""
        return min(axis.t_rupture() for axis in self.axes)

    # ── Rupture "norme jointe" (Bessel/CIR) ──────────────────────────────

    def _current_error_vector(self) -> np.ndarray:
        return np.array([axis.history[-1].e for axis in self.axes])

    def _residual_covariance(self, window: int = 30) -> np.ndarray:
        """Covariance empirique des erreurs récentes par axe (pour n_eff)."""
        histories = [
            np.array([s.e for s in axis.history[-window:]]) for axis in self.axes
        ]
        min_len = min(len(h) for h in histories)
        if min_len < 2:
            return np.eye(self.n)
        stacked = np.stack([h[-min_len:] for h in histories], axis=1)  # (T, n)
        return np.cov(stacked, rowvar=False)

    def _estimate_D(self) -> float:
        """
        Proxy du coefficient de diffusion D : moyenne du bruit de mesure
        adaptatif (R_current) des Kalman par axe, ramenée à un taux par dt.

        Approximation documentée : D est théoriquement le taux d'accumulation
        de variance du bruit résiduel isotrope ; R_current du Kalman est le
        meilleur proxy disponible sans modèle physique dédié par domaine.
        """
        r_values = [axis.kalman.R_current for axis in self.axes]
        return max(float(np.mean(r_values)) / self.dt, 1e-12)

    def t_rupture_joint(
        self,
        Y_max: float,
        D: float | None = None,
        n_eff: float | None = None,
        Kp: float | None = None,
        quantile: float = 0.5,
    ) -> float:
        """
        Premier passage semi-analytique (Bessel/CIR) pour un seuil de norme jointe.

        D, n_eff, Kp sont estimés automatiquement si non fournis :
          - D      : `_estimate_D()` (proxy via R_current des Kalman)
          - n_eff  : participation ratio de la covariance empirique des erreurs
          - Kp     : moyenne des Kp courants par axe (régulation supposée isotrope)
        """
        if not all(axis.history for axis in self.axes):
            raise RuntimeError("t_rupture_joint() nécessite au moins un step() par axe")

        r0 = float(np.linalg.norm(self._current_error_vector()))
        D_val = D if D is not None else self._estimate_D()
        n_eff_val = n_eff if n_eff is not None else effective_dimension(self._residual_covariance())
        n_eff_val = max(n_eff_val, 2.0)  # condition de Feller (dispersion.cir_params)
        Kp_val = Kp if Kp is not None else float(np.mean([axis.pi.Kp for axis in self.axes]))

        return first_passage_time(Y_max, r0, n_eff_val, D_val, Kp_val, quantile=quantile)
