"""
RETA -- Referential Escape Theory by Accumulation.

Trois couches :
  - `reta.core`, `reta.kalman`, `reta.pi`   : RETA classique (v1.4 scalaire)
  - `reta.dispersion`, `reta.nd`             : RETA-nD (couche de dispersion)
  - `reta.finance`                           : extension experimentale --
    calibration MLE (D, Kp) et premier passage par simulation exacte pour
    un usage en gestion de risque financier. Non validee sur donnees
    reelles a ce stade -- voir
    docs/6_domaines_application/finance_quantitative_reta_nd.md

Cf. docs/INDEX.md pour la documentation theorique complete.
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
    is_crisis_regime,
)
from .nd import RETAND, FellerConditionViolated
from .finance import (
    log_returns_from_prices,
    radius_series_from_returns,
    calibrate_cir_mle,
    CIRCalibrationResult,
    first_passage_time_mc,
)

__all__ = [
    "RETAReferential",
    "StepResult",
    "Kalman1D",
    "KalmanAdaptive",
    "PIRegulator",
    "RETAND",
    "FellerConditionViolated",
    "effective_dimension",
    "cir_params",
    "transition_cdf",
    "survival_probability",
    "first_passage_time",
    "first_passage_time_mc",
    "is_crisis_regime",
    "log_returns_from_prices",
    "radius_series_from_returns",
    "calibrate_cir_mle",
    "CIRCalibrationResult",
]
