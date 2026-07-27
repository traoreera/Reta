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
from .dispersion import effective_dimension, first_passage_time, is_crisis_regime


class FellerConditionViolated(ValueError):
    """
    n_eff < 2 : la condition de Feller est violée, l'origine devient une
    barrière accessible pour le processus CIR/BESQ sous-jacent. En finance,
    c'est le signal d'une corrélation extrême entre actifs (crash
    systémique) — traité ici comme une exception explicite plutôt que
    masqué par un clamp silencieux à 2.0 (correction du point 1).
    """

    def __init__(self, n_eff_raw: float):
        self.n_eff_raw = n_eff_raw
        super().__init__(
            f"n_eff={n_eff_raw:.3f} < 2 : condition de Feller violée "
            "(corrélation extrême / régime de crise). t_rupture_joint() "
            "n'est pas défini dans ce régime ; voir crisis_fallback= pour "
            "un comportement dégradé explicite plutôt qu'une exception."
        )


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
        """
        Covariance empirique régularisée (shrinkage Ledoit-Wolf) des erreurs
        récentes par axe, pour n_eff.

        Correction (point 2) : `np.cov` brut sur une fenêtre courte
        (window=30 par défaut) est mal conditionné dès que n approche ou
        dépasse la dizaine d'actifs — recommandé T >= 3*n. Le shrinkage
        Ledoit-Wolf mélange la covariance empirique avec une cible
        structurée (proportionnelle à l'identité), ce qui stabilise
        l'estimation sans supposer l'indépendance des axes. Si
        scikit-learn n'est pas installé, on retombe sur `np.cov` brut
        (avec avertissement) plutôt que d'échouer silencieusement.
        """
        histories = [
            np.array([s.e for s in axis.history[-window:]]) for axis in self.axes
        ]
        min_len = min(len(h) for h in histories)
        if min_len < 2:
            return np.eye(self.n)
        stacked = np.stack([h[-min_len:] for h in histories], axis=1)  # (T, n)

        if min_len < 3 * self.n:
            import warnings
            warnings.warn(
                f"_residual_covariance: fenêtre courte ({min_len} obs pour "
                f"{self.n} axes, recommandé >= {3 * self.n}) — n_eff peut "
                "être instable même après shrinkage.",
                stacklevel=2,
            )

        try:
            from sklearn.covariance import LedoitWolf
            return LedoitWolf().fit(stacked).covariance_
        except ImportError:
            import warnings
            warnings.warn(
                "scikit-learn indisponible : _residual_covariance retombe "
                "sur np.cov brut (non régularisé). `pip install scikit-learn` "
                "recommandé pour un n_eff stable en haute dimension.",
                stacklevel=2,
            )
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

    def n_eff_diagnostics(self, n_eff: float | None = None) -> tuple[float, bool]:
        """
        Renvoie (n_eff_brut, crisis_flag) sans aucun clamp — à appeler
        explicitement pour surveiller le régime de corrélation, y compris
        quand t_rupture_joint() est utilisé avec crisis_fallback="clamp".
        """
        n_eff_val = n_eff if n_eff is not None else effective_dimension(self._residual_covariance())
        return n_eff_val, is_crisis_regime(n_eff_val)

    def t_rupture_joint(
        self,
        Y_max: float,
        D: float | None = None,
        n_eff: float | None = None,
        Kp: float | None = None,
        quantile: float = 0.5,
        crisis_fallback: str = "raise",
    ) -> float:
        """
        Premier passage semi-analytique (Bessel/CIR) pour un seuil de norme jointe.

        D, n_eff, Kp sont estimés automatiquement si non fournis :
          - D      : `_estimate_D()` (proxy via R_current des Kalman)
          - n_eff  : participation ratio de la covariance empirique des erreurs
                     (régularisée par shrinkage Ledoit-Wolf, cf. `_residual_covariance`)
          - Kp     : moyenne des Kp courants par axe (régulation supposée isotrope)

        Correction (point 1) : n_eff n'est plus clampé silencieusement à 2.0.
        Si la condition de Feller est violée (n_eff < 2, corrélation extrême /
        régime de crise), le comportement dépend de `crisis_fallback` :
          - "raise" (défaut) : lève `FellerConditionViolated` — le régime
            n'est pas défini pour ce modèle, mieux vaut le savoir.
          - "zero"  : retourne 0.0 (rupture immédiate) — hypothèse
            conservative raisonnable en gestion de risque : n_eff -> 1
            signifie que tous les axes bougent ensemble, donc la marge de
            diversification qui retarde la rupture a disparu.
          - "clamp" : ancien comportement (n_eff force à 2.0) — pour
            compatibilité descendante uniquement, déconseillé en production.
        """
        if not all(axis.history for axis in self.axes):
            raise RuntimeError("t_rupture_joint() nécessite au moins un step() par axe")
        if crisis_fallback not in ("raise", "zero", "clamp"):
            raise ValueError('crisis_fallback doit être "raise", "zero" ou "clamp"')

        r0 = float(np.linalg.norm(self._current_error_vector()))
        D_val = D if D is not None else self._estimate_D()
        n_eff_val = n_eff if n_eff is not None else effective_dimension(self._residual_covariance())
        Kp_val = Kp if Kp is not None else float(np.mean([axis.pi.Kp for axis in self.axes]))

        if is_crisis_regime(n_eff_val):
            if crisis_fallback == "raise":
                raise FellerConditionViolated(n_eff_val)
            elif crisis_fallback == "zero":
                return 0.0
            else:  # "clamp"
                n_eff_val = 2.0

        return first_passage_time(Y_max, r0, n_eff_val, D_val, Kp_val, quantile=quantile)
