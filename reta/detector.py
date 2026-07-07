"""
PhaseDetector — machine d'état BULL / BEAR / NEUTRE avec hysteresis.

Règle :
  - z̄(t) > +ε  pendant T_CONFIRM barres → BULL
  - z̄(t) < -ε  pendant T_CONFIRM barres → BEAR
  - sinon       → NEUTRE (ou état précédent si pas confirmé)

Le T_CONFIRM évite les faux signaux sur des pics momentanés.
"""

from __future__ import annotations
from typing import Literal

Phase = Literal["BULL", "BEAR", "NEUTRE"]

_INT_TO_PHASE: dict[int, Phase] = {1: "BULL", -1: "BEAR", 0: "NEUTRE"}
_PHASE_TO_INT: dict[Phase, int] = {"BULL": 1, "BEAR": -1, "NEUTRE": 0}


class PhaseDetector:
    def __init__(self, eps: float = 0.0008, t_confirm: int = 12):
        self.eps       = eps
        self.t_confirm = t_confirm
        self._etat     = 0    # état confirmé : 1 / -1 / 0
        self._cpt      = 0    # compteur de confirmation en cours

    def update(self, z_moy: float) -> Phase:
        """Met à jour avec z̄ courant. Retourne la phase confirmée."""
        if z_moy > self.eps:
            self._cpt = self._cpt + 1 if self._etat != 1 else 0
            if self._cpt >= self.t_confirm:
                self._etat, self._cpt = 1, 0
        elif z_moy < -self.eps:
            self._cpt = self._cpt + 1 if self._etat != -1 else 0
            if self._cpt >= self.t_confirm:
                self._etat, self._cpt = -1, 0
        else:
            self._cpt = 0

        return _INT_TO_PHASE[self._etat]

    def batch(self, z_moy_series) -> list[Phase]:
        """Traite une série complète. Réinitialise l'état interne."""
        self.reset()
        return [self.update(float(z)) for z in z_moy_series]

    def reset(self) -> None:
        self._etat = 0
        self._cpt  = 0

    @property
    def phase(self) -> Phase:
        return _INT_TO_PHASE[self._etat]

    @property
    def phase_int(self) -> int:
        return self._etat

    def __repr__(self) -> str:
        return f"PhaseDetector(phase={self.phase}, cpt={self._cpt}/{self.t_confirm})"
