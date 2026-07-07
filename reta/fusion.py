"""
Fusion de référentiels RETA — opérateur ⊕

y_{A⊕B}(t) = α·y_A(t) + (1−α)·y_B(t)
z_{A⊕B}    = α·z_A    + (1−α)·z_B      (linéarité de l'intégrale)
ε_{A⊕B}    = α·ε_A    + (1−α)·ε_B

Navigation O(1) entre deux référentiels :
  Δz_{A→B} = z_B − z_A
  y_B = y_A + ∫Δz dτ   (une soustraction + une somme cumulée)

Doc source : docs/RETA_fusion_referentiels.md
"""

from __future__ import annotations
import numpy as np
from .core import RETAReferential


def fusion(
    A: RETAReferential,
    B: RETAReferential,
    alpha: float = 0.5,
) -> RETAReferential:
    """
    Fusionne deux référentiels avec le paramètre α ∈ [0, 1].
    α=1 → pur A   |   α=0 → pur B   |   α=0.5 → équilibré

    Fonctionne sur des référentiels complets (avec z_moy) ou
    sur des référentiels reconstruits depuis DB (scalaires uniquement).
    """
    if not 0.0 <= alpha <= 1.0:
        raise ValueError(f"alpha doit être dans [0, 1], reçu {alpha}")

    ref = RETAReferential(eps=alpha * A.eps_cur + (1 - alpha) * B.eps_cur)

    # ── Cas 1 : les deux référentiels ont leurs séries complètes ──────────────
    if len(A.z_moy) > 1 and len(B.z_moy) > 1:
        n = min(len(A.z_moy), len(B.z_moy))
        z_f = alpha * A.z_moy[:n] + (1 - alpha) * B.z_moy[:n]

        log_f = np.zeros(n)
        # Ancrage sur A si disponible, sinon zéro
        log_f[0] = A._log_prix[0] if len(A._log_prix) > 0 else 0.0
        for i in range(1, n):
            log_f[i] = log_f[i - 1] + z_f[i]

        ref.z_moy    = z_f
        ref.z_est    = z_f
        ref.log_pred = log_f
        ref.n        = n
        ref.z_last   = float(z_f[-1])

    # ── Cas 2 : référentiels scalaires (depuis DB) ────────────────────────────
    else:
        ref.z_last = alpha * A.z_last + (1 - alpha) * B.z_last
        ref.z_moy  = np.array([ref.z_last])
        ref.z_est  = np.array([ref.z_last])
        ref.n      = max(A.n, B.n)

    ref.eps_cur = alpha * A.eps_cur + (1 - alpha) * B.eps_cur
    ref.t_rup   = 0.20 / max(abs(ref.z_last), 1e-8)
    ref.P_inf   = alpha * A.P_inf + (1 - alpha) * B.P_inf

    # Phase de la fusion : on combine les signaux
    a_int = {"BULL": 1, "BEAR": -1, "NEUTRE": 0}[A.phase]
    b_int = {"BULL": 1, "BEAR": -1, "NEUTRE": 0}[B.phase]
    combined = alpha * a_int + (1 - alpha) * b_int
    ref.phase = "BULL" if combined > 0.3 else ("BEAR" if combined < -0.3 else "NEUTRE")

    return ref


def navigate(A: RETAReferential, B: RETAReferential) -> np.ndarray:
    """
    Calcule Δz_{A→B} = z_B − z_A et retourne la divergence accumulée.
    O(1) — pas de recalcul Kalman.

    Retourne : delta_acc (même longueur que min(len(A.z_moy), len(B.z_moy)))
    """
    n = min(len(A.z_moy), len(B.z_moy))
    if n <= 1:
        # Scalaires uniquement → divergence scalaire
        return np.array([B.z_last - A.z_last])
    delta_z = B.z_moy[:n] - A.z_moy[:n]
    return np.cumsum(delta_z)


def ligne_possibilites(
    A: RETAReferential,
    B: RETAReferential,
    n: int = 20,
) -> list[RETAReferential]:
    """
    Retourne la famille continue de référentiels entre A et B.
    L = { y_α : α ∈ [0, 1] }  —  `n` points échantillonnés.
    """
    alphas = np.linspace(0.0, 1.0, n)
    return [fusion(A, B, alpha=float(a)) for a in alphas]
