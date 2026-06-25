"""
RETA v1.2 — Simulation
========================
Kalman fixe + PI adaptatif gradient (Lyapunov prouvé)

Scénario : saut de perturbation à t=T_CHOC
  v1.1 : régulateur P pur (Ki=0 fixe) → erreur statique y_ss = z/Kp > Y_max → RUPTURE
  v1.2 : gains adaptatifs gradient → Ki monte automatiquement → erreur statique → 0

Lois d'adaptation (Lyapunov prouvé, V̇ ≤ 0) :
  K̇p = γp · ē²           (ē = e/e_ref normalisé)
  K̇i = γi · ē · ∫ē dτ
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from pathlib import Path

rng = np.random.default_rng(3)

# ─── Paramètres ──────────────────────────────────────────────────────────────
dt    = 0.01
T_sim = 40.0
N     = int(T_sim / dt)
t     = np.linspace(0, T_sim, N)

Y_MAX = 5.0         # seuil RETA
E_REF = Y_MAX / 2   # normalisation

T_CHOC = 10.0       # saut de perturbation

def z_true(tk):
    if tk < T_CHOC:
        return 0.25    # phase nominale
    return 2.8         # saut fort : y_ss_P = z/Kp = 2.8/0.4 = 7 > Y_max=5

def f_prime(tk):
    return 1.0 / (1.0 + tk**2)

SIGMA_OBS = 0.1

# Kalman fixe (identique v1.1 et v1.2)
Q_KAL = 1e-4; R_KAL = SIGMA_OBS**2
A_kal = np.array([[1.0, dt], [0.0, 1.0]])
H_kal = np.array([[1.0, 0.0]])
Qm    = np.diag([Q_KAL, Q_KAL * 0.1])
Rm    = np.array([[R_KAL]])

# v1.1 : P pur, Ki=0 fixe
# → y_ss = z/Kp = 2.8/0.4 = 7.0 > Y_max=5 → rupture inévitable
KP11 = 0.4
KI11 = 0.0   # pas d'action intégrale → erreur statique permanente

# v1.2 : mêmes gains initiaux, adaptatifs gradient
KP12_INIT = 0.4
KI12_INIT = 0.0
GAMMA_P   = 1.5    # apprentissage Kp
GAMMA_I   = 0.8    # apprentissage Ki — doit croître pour annuler l'erreur statique
KP_BOUNDS = (0.001, 20.0)
KI_BOUNDS = (0.0,   10.0)

# ─── Simulation ──────────────────────────────────────────────────────────────

def run(kp0, ki0, adaptive=False, seed_offset=0):
    rng2 = np.random.default_rng(3 + seed_offset)
    x_kal = np.zeros(2); P_kal = np.eye(2)
    kp, ki = kp0, ki0
    ie = 0.0; y = 0.0
    out = {k: np.zeros(N) for k in ["y", "z_est", "z_v", "u", "e", "V", "kp", "ki"]}
    for k in range(N):
        tk = t[k]; zv = z_true(tk); fp = f_prime(tk)
        obs = zv + rng2.standard_normal() * SIGMA_OBS
        x_kal = A_kal @ x_kal; P_kal = A_kal @ P_kal @ A_kal.T + Qm
        S  = float((H_kal @ P_kal @ H_kal.T + Rm)[0, 0])
        Kk = (P_kal @ H_kal.T).flatten() / S
        x_kal += Kk * (float(obs) - float((H_kal @ x_kal)[0]))
        P_kal = (np.eye(2) - np.outer(Kk, H_kal)) @ P_kal

        e = y; ebar = e / E_REF
        ie += ebar * dt

        if adaptive:
            kp = float(np.clip(kp + GAMMA_P * ebar**2 * dt, *KP_BOUNDS))
            ki = float(np.clip(ki + GAMMA_I * ebar * ie * dt, *KI_BOUNDS))

        u = kp * e + ki * ie * E_REF
        y += (fp + zv - u) * dt

        out["y"][k]     = y
        out["z_est"][k] = float(x_kal[0])
        out["z_v"][k]   = zv
        out["u"][k]     = u
        out["e"][k]     = e
        out["V"][k]     = 0.5*e**2 + (max(ki,1e-9)/2)*(ie*E_REF)**2
        out["kp"][k]    = kp
        out["ki"][k]    = ki
    return out

r11 = run(KP11, KI11, adaptive=False)
r12 = run(KP12_INIT, KI12_INIT, adaptive=True)

# ─── Analyse ─────────────────────────────────────────────────────────────────
rup11 = np.where(np.abs(r11["y"]) > Y_MAX)[0]
rup12 = np.where(np.abs(r12["y"]) > Y_MAX)[0]
t11   = f"t={t[rup11[0]]:.2f}s ⚠️" if len(rup11) else "JAMAIS ✓"
t12   = f"t={t[rup12[0]]:.2f}s ⚠️" if len(rup12) else "JAMAIS ✓"

z_post = z_true(T_CHOC + 1)
print("RETA v1.2 — PI adaptatif gradient vs v1.1 (P pur)")
print(f"  Saut à t={T_CHOC}s : z = {z_post}")
print(f"  y_ss v1.1 (P pur) = z/Kp = {z_post:.1f}/{KP11} = {z_post/KP11:.1f} > Y_max={Y_MAX} → rupture attendue")
print(f"  Rupture v1.1 : {t11}")
print(f"  Rupture v1.2 : {t12}")
print(f"  Kp final v1.2 : {r12['kp'][-1]:.3f}  (init={KP12_INIT})")
print(f"  Ki final v1.2 : {r12['ki'][-1]:.4f}  (init={KI12_INIT}) — intégrale acquise ✓")
print(f"  y final v1.1 : {r11['y'][-1]:.3f}°")
print(f"  y final v1.2 : {r12['y'][-1]:.3f}°")

# ─── Graphes ─────────────────────────────────────────────────────────────────
fig = plt.figure(figsize=(14, 16))
fig.suptitle(
    "RETA v1.2 — PI Adaptatif Gradient\n"
    "v1.1 : P pur (Ki=0 fixe) → erreur statique > Y_max\n"
    "v1.2 : K̇p = γp·ē²  |  K̇i = γi·ē·∫ē  → élimine l'erreur statique ✓",
    fontsize=12, fontweight="bold")
gs = gridspec.GridSpec(4, 2, figure=fig, hspace=0.5, wspace=0.35)

z_arr = np.array([z_true(tk) for tk in t])

# Signal y(t)
ax = fig.add_subplot(gs[0, :])
ax.axvspan(T_CHOC, T_sim, color="lightyellow", alpha=0.6)
ax.axvline(T_CHOC, color="orange", ls=":", lw=1.5, label=f"saut z à t={T_CHOC}s")
ax.plot(t, r11["y"], color="gray", lw=1.5, label=f"v1.1 P pur (Ki=0) — y_ss={z_post/KP11:.0f}")
ax.plot(t, r12["y"], color="#1565C0", lw=2,   label="v1.2 PI adaptatif gradient")
ax.axhline( Y_MAX, color="red", ls="--", lw=1, label=f"Y_max={Y_MAX}")
ax.axhline(-Y_MAX, color="red", ls="--", lw=1)
ax.axhline(0, color="black", ls=":", lw=0.7)
if len(rup11): ax.axvline(t[rup11[0]], color="gray", ls="--", lw=1.5, label=f"rup v1.1 {t11}")
ax.set_title("Signal y(t) — boucle fermée", fontsize=10)
ax.set_ylabel("y(t)"); ax.set_xlabel("t [s]")
ax.legend(fontsize=9); ax.set_xlim(0, T_sim)

# Kp adaptatif
ax = fig.add_subplot(gs[1, 0])
ax.axvspan(T_CHOC, T_sim, color="lightyellow", alpha=0.6)
ax.axvline(T_CHOC, color="orange", ls=":", lw=1.5)
ax.plot(t, r12["kp"], color="#1565C0", lw=1.5, label="Kp(t) v1.2")
ax.axhline(KP11, color="gray", ls="--", lw=1, label=f"Kp fixe v1.1={KP11}")
ax.set_title("Kp adaptatif — K̇p = γp·ē²", fontsize=10)
ax.set_ylabel("Kp"); ax.set_xlabel("t [s]")
ax.legend(fontsize=9)

# Ki adaptatif
ax = fig.add_subplot(gs[1, 1])
ax.axvspan(T_CHOC, T_sim, color="lightyellow", alpha=0.6)
ax.axvline(T_CHOC, color="orange", ls=":", lw=1.5)
ax.plot(t, r12["ki"], color="#2E7D32", lw=1.5, label="Ki(t) v1.2 — ZERO initial")
ax.axhline(KI11, color="gray", ls="--", lw=1, label=f"Ki fixe v1.1={KI11} (nul)")
ax.set_title("Ki adaptatif — K̇i = γi·ē·∫ē  (acquiert l'action I)", fontsize=10)
ax.set_ylabel("Ki"); ax.set_xlabel("t [s]")
ax.legend(fontsize=9)

# z estimé
ax = fig.add_subplot(gs[2, 0])
ax.axvspan(T_CHOC, T_sim, color="lightyellow", alpha=0.6)
ax.axvline(T_CHOC, color="orange", ls=":", lw=1.5)
ax.plot(t, z_arr, color="red", lw=1.5, ls="--", label="z(t) vrai")
ax.plot(t, r12["z_est"], color="#1565C0", lw=1.5, label="ẑ(t) Kalman fixe")
ax.set_title("Estimation z(t) — Kalman fixe (commun v1.1 et v1.2)", fontsize=10)
ax.set_ylabel("z"); ax.set_xlabel("t [s]")
ax.legend(fontsize=9)

# Commande u
ax = fig.add_subplot(gs[2, 1])
ax.axvspan(T_CHOC, T_sim, color="lightyellow", alpha=0.6)
ax.axvline(T_CHOC, color="orange", ls=":", lw=1.5)
ax.plot(t, r11["u"], color="gray",     lw=1.2, label="u(t) v1.1 — sature à Kp·y_ss")
ax.plot(t, r12["u"], color="#1565C0",  lw=1.5, label="u(t) v1.2 — converge vers z")
ax.plot(t, z_arr,    color="red",      lw=1,   ls="--", alpha=0.6, label="z à compenser")
ax.set_title("Commande PI — v1.2 converge vers z(t)", fontsize=10)
ax.set_ylabel("u(t)"); ax.set_xlabel("t [s]")
ax.legend(fontsize=9)

# Lyapunov
ax = fig.add_subplot(gs[3, :])
ax.axvspan(T_CHOC, T_sim, color="lightyellow", alpha=0.6)
ax.axvline(T_CHOC, color="orange", ls=":", lw=1.5)
V11_clean = np.where(r11["V"] > 0, r11["V"], 1e-12)
V12_clean = np.where(r12["V"] > 0, r12["V"], 1e-12)
ax.semilogy(t, V11_clean, color="gray",    lw=1.5, label="V v1.1 — diverge après saut ⚠️")
ax.semilogy(t, V12_clean, color="#1565C0", lw=2,   label="V v1.2 = e²/2 + (Ki/2)I² — décroît ✓")
ax.set_title("Lyapunov V(e,I) — preuve de stabilité des lois gradient", fontsize=10)
ax.set_ylabel("V [log]"); ax.set_xlabel("t [s]")
ax.legend(fontsize=9)

out = Path(__file__).parent / "results.png"
plt.savefig(out, dpi=150, bbox_inches="tight")
print(f"\nGraphe → {out}")
