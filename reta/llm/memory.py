"""
RETA Memory — Signature compacte d'un tour de conversation.

Modèle (doc : memoire_llm.md section 2) :
  Tour 0  →  intention initiale = arctan(t)           [ℝ¹]
  Tour k  →  + ∫zₖ dτ  (expansion)   ou              [ℝᵏ⁺¹]
             − ∫uₖ dτ  (contraction PI)

Stockage :
  Classique : O(n × k)   — reduplique tout le passé
  RETA      : O(n + k·s) — état courant + k signatures de s tokens

Chaque TurnSignature coûte s ≈ 15 tokens (εᵢ, type, Δy, ts).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


TourType = Literal["expansion", "contraction", "stabilisation"]


@dataclass
class TurnSignature:
    """
    Signature compacte d'un tour de conversation.
    Équivalent à s ≈ 15 tokens (doc efficience_memoire.md §1).

    expansion    : nouveau contexte, question   → +∫zₖ dτ  ouvre ℝᵏ⁺¹
    contraction  : correction, contradiction    → −∫uₖ dτ  PI referme la dérive
    stabilisation: confirmation, accord         → Δy → 0   maintient le référentiel
    """
    turn_id:   int
    tour_type: TourType
    eps:       float      # ε_i — perturbation minimale garantie sur ce tour
    z_mean:    float      # z̄_i — perturbation moyenne (Kalman)
    delta_y:   float      # Δy_i = ∫zᵢ dτ ≈ z̄_i × durée — contribution nette
    ts:        datetime   = field(default_factory=datetime.utcnow)
    label:     str        = ""   # étiquette optionnelle (sujet, intent, etc.)

    # Taille en tokens équivalents (approximation doc)
    TOKEN_SIZE: int = field(default=15, init=False, repr=False)

    def is_expansion(self) -> bool:
        return self.tour_type == "expansion"

    def is_contraction(self) -> bool:
        return self.tour_type == "contraction"

    def encode(self) -> dict:
        return {
            "turn_id":   self.turn_id,
            "type":      self.tour_type,
            "eps":       round(self.eps,     8),
            "z_mean":    round(self.z_mean,  8),
            "delta_y":   round(self.delta_y, 8),
            "ts":        self.ts.isoformat(),
            "label":     self.label,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "TurnSignature":
        return cls(
            turn_id   = d["turn_id"],
            tour_type = d["type"],
            eps       = d["eps"],
            z_mean    = d["z_mean"],
            delta_y   = d["delta_y"],
            ts        = datetime.fromisoformat(d["ts"]),
            label     = d.get("label", ""),
        )

    def __repr__(self) -> str:
        sign = "+" if self.tour_type == "expansion" else ("-" if self.tour_type == "contraction" else "~")
        return (f"Turn#{self.turn_id} [{self.tour_type[:3].upper()}] "
                f"{sign}Δy={self.delta_y:+.5f}  ε={self.eps:.5f}  z̄={self.z_mean:.5f}")


@dataclass
class ConversationMemory:
    """
    Mémoire RETA d'une conversation complète.

    Stocke :
      - y_current : état courant compressé (vecteur de dim fixe → scalaire ici)
      - signatures : liste des TurnSignature (une par tour)

    Coût : O(n + k·s) au lieu de O(n·k) en classique.
    """
    session_id:  str
    y_current:   float = 0.0       # état courant yₖ (dimension fixe)
    signatures:  list[TurnSignature] = field(default_factory=list)
    n_tokens:    int = 1000        # taille d'un tour (tokens) — paramètre doc

    @property
    def k(self) -> int:
        """Nombre de tours."""
        return len(self.signatures)

    def add_turn(self, sig: TurnSignature) -> None:
        """Ajoute un tour et met à jour y_current."""
        if sig.tour_type == "expansion":
            self.y_current += sig.delta_y
        elif sig.tour_type == "contraction":
            self.y_current -= abs(sig.delta_y)   # PI inverse
        # stabilisation : y_current inchangé
        self.signatures.append(sig)

    def get_turn(self, turn_id: int) -> TurnSignature | None:
        for s in self.signatures:
            if s.turn_id == turn_id:
                return s
        return None

    def encode(self) -> dict:
        return {
            "session_id":  self.session_id,
            "y_current":   round(self.y_current, 8),
            "k":           self.k,
            "signatures":  [s.encode() for s in self.signatures],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ConversationMemory":
        mem = cls(session_id=d["session_id"], y_current=d["y_current"])
        for sd in d.get("signatures", []):
            mem.signatures.append(TurnSignature.from_dict(sd))
        return mem
