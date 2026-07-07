"""
RETA LLM Utils — Utilitaires de mémoire pour les LLMs.

Toutes les formules sont fidèles à :
  docs/3_technique/efficience_memoire.md
  docs/4_applications/memoire_llm.md

Formules clés :
  C_classique(n, k) = n · k(k+1)/2
  C_RETA(n, k, s)   = n + k·s
  R(k)              = C_classique / C_RETA  ≈ nk / 2s  pour k >> 1

  ε_rec(j, k)       = P∞ · (k − j)          # erreur reconstruction
  t_collapse(y_k, y_j, ε_ctrl) = (y_k − y_j) / ε_ctrl
  η_RETA            = 1 − P∞ / ε            # efficience invariante
  η_classique(k)    = 1 / k                  # dégradation linéaire
"""

from __future__ import annotations

import math
from typing import Sequence

from .memory import TurnSignature, ConversationMemory


# ── Formules d'efficience (doc §1, §5, §7) ───────────────────────────────────

def storage_classical(n: int, k: int) -> int:
    """
    Coût de stockage classique : O(n × k).
    C_classique = n · k(k+1)/2  (somme des tours 1..k)
    """
    return n * k * (k + 1) // 2


def storage_reta(n: int, k: int, s: int = 15) -> int:
    """
    Coût de stockage RETA : O(n + k·s).
    C_RETA = n + k·s  (état courant + k signatures de s tokens)
    """
    return n + k * s


def compression_ratio(n: int, k: int, s: int = 15) -> float:
    """
    Ratio de compression R(k) = C_classique / C_RETA.
    Approximation pour k >> 1 : R ≈ nk / 2s
    RETA est plus efficace dès k > n/(n−s) ≈ 1,015 tours (doc §2).
    """
    c_reta = storage_reta(n, k, s)
    if c_reta == 0:
        return float("inf")
    return storage_classical(n, k) / c_reta


def reconstruction_error(P_inf: float, k: int, j: int) -> float:
    """
    Erreur de reconstruction au tour j depuis l'état courant au tour k.
    ε_rec(j, k) ≤ P∞ · (k − j)    (doc §7)

    Valide tant que k−j ≤ Δ_max / P∞ (≈ 23 tours pour Δ_max=10, P∞=0.4316).
    Au-delà : utiliser des checkpoints (doc §8.2).
    """
    if j > k:
        raise ValueError(f"j={j} doit être ≤ k={k}")
    return P_inf * (k - j)


def t_collapse(y_k: float, y_j: float, eps_ctrl: float) -> float:
    """
    Temps de descente pour retrouver l'état y_j depuis y_k.
    t_collapse = (y_k − y_j) / ε_ctrl    (doc §3.3)

    Fini, garanti, indépendant de k.
    """
    if eps_ctrl <= 0:
        raise ValueError("eps_ctrl doit être > 0")
    return (y_k - y_j) / eps_ctrl


def efficiency_eta(P_inf: float, eps: float) -> float:
    """
    Efficience RETA — invariante avec k.
    η_RETA = 1 − P∞/ε    (doc §5)

    η_classique(k) = 1/k  → 0 quand k → ∞.
    η_RETA est constant.

    Améliorer η : réduire R_mes (bruit mesure) ou augmenter ε.
    """
    if eps <= 0:
        raise ValueError("eps doit être > 0")
    return 1.0 - P_inf / eps


def eta_gain_over_classical(P_inf: float, eps: float, k: int) -> float:
    """
    Rapport η_RETA / η_classique(k).
    Pour k=100, P∞=0.4316, ε=0.5858 → 26.3× (doc §5).
    """
    eta_r = efficiency_eta(P_inf, eps)
    eta_c = 1.0 / k if k > 0 else float("inf")
    return eta_r / eta_c if eta_c > 0 else float("inf")


# ── Reconstruction de trajectoire (doc §3.1) ─────────────────────────────────

def reconstruct_at(
    memory: ConversationMemory,
    target_turn: int,
) -> float:
    """
    Retrouve l'état y_j au tour target_turn depuis l'état courant y_k.

    Descente par substitution :
      y_j = y_k − Σ_{i=j+1}^{k} Δy_i    (doc §3.1)

    Coût : k−j soustractions (vs relire k−j tours entiers en classique).
    """
    k = memory.k
    if target_turn < 0 or target_turn > k:
        raise ValueError(f"target_turn={target_turn} hors de [0, {k}]")
    if target_turn == k:
        return memory.y_current

    y = memory.y_current
    # Soustraire les tours de target_turn+1 jusqu'à k (ordre inverse)
    for sig in reversed(memory.signatures[target_turn:]):
        if sig.tour_type == "expansion":
            y -= sig.delta_y
        elif sig.tour_type == "contraction":
            y += abs(sig.delta_y)   # inverse du PI
    return y


def reconstruct_trajectory(memory: ConversationMemory) -> list[float]:
    """
    Reconstruit tous les états y_0, y_1, ..., y_k depuis les signatures.
    Retourne la trajectoire complète.
    """
    states = [0.0]   # y_0 = arctan(0) = 0 (intention initiale)
    y = 0.0
    for sig in memory.signatures:
        if sig.tour_type == "expansion":
            y += sig.delta_y
        elif sig.tour_type == "contraction":
            y -= abs(sig.delta_y)
        states.append(y)
    return states


# ── Fusion de mémoires (doc fusion_referentiels.md §5.1) ─────────────────────

def merge_memories(
    memories: Sequence[ConversationMemory],
    weights: Sequence[float] | None = None,
) -> ConversationMemory:
    """
    Fusionne N mémoires de conversation en un référentiel unique.

    y_fusion = Σ wᵢ · yᵢ    (fusion linéaire, poids normalisés)
    ε_fusion = Σ wᵢ · εᵢ

    Applications : ensemble de contextes LLM, multi-session, multi-agent.
    """
    if not memories:
        raise ValueError("Au moins une mémoire requise")

    n = len(memories)
    if weights is None:
        weights = [1.0 / n] * n
    else:
        total = sum(weights)
        weights = [w / total for w in weights]

    y_fused = sum(w * m.y_current for w, m in zip(weights, memories))
    fused = ConversationMemory(
        session_id=f"fusion_{'_'.join(m.session_id for m in memories)}",
        y_current=y_fused,
        n_tokens=memories[0].n_tokens,
    )
    return fused


# ── Formatage pour injection dans prompt LLM (doc §4, §6) ────────────────────

def to_prompt_context(
    memory: ConversationMemory,
    P_inf: float = 0.4316,
    last_n: int = 5,
) -> str:
    """
    Génère un bloc de contexte compact pour injection dans le system prompt.
    Encode l'état courant + les dernières signatures sans relire les tokens.

    Format cible : s ≈ 15 tokens par ligne → coût total O(n + k·s).
    """
    k   = memory.k
    eta = efficiency_eta(P_inf, eps=0.5858) if P_inf > 0 else 0.0
    lines = [
        f"[RETA-MEMORY session={memory.session_id}]",
        f"  État courant y_{k} = {memory.y_current:+.5f}",
        f"  Tours total  k = {k}  |  η = {eta:.3f}  |  P∞ = {P_inf:.4f}",
    ]

    if memory.signatures:
        lines.append(f"  Derniers tours (k−{min(last_n, k)}..k) :")
        for sig in memory.signatures[-last_n:]:
            sign = "▲" if sig.tour_type == "expansion" else ("▼" if sig.tour_type == "contraction" else "─")
            lines.append(
                f"    {sign} Tour#{sig.turn_id} [{sig.tour_type[:3].upper()}] "
                f"Δy={sig.delta_y:+.5f}  ε={sig.eps:.5f}"
                + (f"  [{sig.label}]" if sig.label else "")
            )

    if k > 0:
        err = reconstruction_error(P_inf, k, max(0, k - last_n))
        lines.append(f"  Erreur reconstruction derniers {last_n} tours ≤ {err:.4f}")

    lines.append("[/RETA-MEMORY]")
    return "\n".join(lines)


# ── Détection de rupture mémoire (doc §8.2) ───────────────────────────────────

def needs_checkpoint(
    memory: ConversationMemory,
    P_inf: float = 0.4316,
    delta_max: float = 10.0,
) -> bool:
    """
    Retourne True si un checkpoint est nécessaire.
    Condition : k − j_dernier_checkpoint > Δ_max / P∞ ≈ 23 tours (doc §8.2).
    """
    if P_inf <= 0:
        return False
    max_depth = delta_max / P_inf
    return memory.k > max_depth


def efficiency_report(n: int, k: int, P_inf: float, eps: float, s: int = 15) -> str:
    """Rapport d'efficience complet (reproduit le tableau doc §6)."""
    c_c = storage_classical(n, k)
    c_r = storage_reta(n, k, s)
    r   = compression_ratio(n, k, s)
    eta = efficiency_eta(P_inf, eps)
    gain = eta_gain_over_classical(P_inf, eps, k)

    return (
        f"── Rapport RETA Efficience (n={n}, k={k}, s={s}) ──────────────\n"
        f"  Stockage classique : {c_c:>12,} tokens\n"
        f"  Stockage RETA      : {c_r:>12,} tokens\n"
        f"  Ratio compression  : {r:>11.0f}×\n"
        f"  η_RETA             : {eta:>11.4f}  (invariant avec k)\n"
        f"  η_classique(k={k:3d}) : {1/k:>11.4f}  (dégradation 1/k)\n"
        f"  Gain η             : {gain:>11.1f}×\n"
        f"  Erreur rec. 1 tour : {P_inf:>11.4f}  (P∞ = {P_inf})\n"
        f"  Checkpoint requis  : {'OUI (k > 23)' if k > 23 else 'NON'}\n"
        f"─────────────────────────────────────────────────────────────────"
    )
