"""
RETA — Referential Escape Theory by Accumulation.

Deux couches :
  - `reta.core`, `reta.kalman`, `reta.pi`   : RETA classique (v1.4 scalaire)
  - `reta.dispersion`, `reta.nd`             : RETA-nD (couche de dispersion)

Cf. docs/INDEX.md pour la documentation théorique complète.
"""

from .core import RETAReferential, StepResult
from .kalman import Kalman1D, KalmanAdaptive
from .pi import PIRegulator
from .dispersion import (
    effective_dimension,
    cir_params,
    transition_cdf,
    survival_probability,
    first_passage_time,
)
from .nd import RETAND

__all__ = [
    "RETAReferential",
    "StepResult",
    "Kalman1D",
    "KalmanAdaptive",
    "PIRegulator",
    "RETAND",
    "effective_dimension",
    "cir_params",
    "transition_cdf",
    "survival_probability",
    "first_passage_time",
]
