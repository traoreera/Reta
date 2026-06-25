"""
RETA v1.1 — Simulation de référence
=====================================
Kalman fixe (Q, R constants) + Correcteur PI fixe (Kp, Ki constants)

Scénario : perturbation z(t) croissante (biais thermique ou dérive financière)
  - Signal : y(t) = arctan(t) + ∫z(τ)dτ  (théorie RETA)
  - Kalman  : estime z(t) depuis les observations bruitées
  - PI      : corrige u(t) = Kp·e + Ki·∫e — maintient y(t) < Y_max
  - RETA    : prédit t_rup ≥ (Y_max − π/2) / z̄

Résultat attendu :
  - Sans PI : rupture à t_rup ≈ (Y_max − π/2)/z̄ (borne conservative)
  - Avec PI : rupture retardée ou évitée si Kp·e > z(t)
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from pathlib import Path

rng = np.random.default_rng(0)

# ─── Paramètres ──────────────────────────────────────────────────────────────
dt    = 0.01
T_sim = 30.0
N     = int(T_sim / dt)
t     = np.linspace(0, T_sim, N)

Y_MAX = 8.0         # seuil de rupture
E_REF = Y_MAX / 2   # normalisation erreur

# z(t) = perturbation RETA — croissante puis se stabilise
def z_true(tk):
    return 0.3 + 0.05 * tk * np.exp(-tk / 8)   # pic à t≈8s

# Signal RETA théorique : y(t) = arctan(t) + 2t + sin(t) - cos(t) + 1
# Dans la simulation on suit l'accumulation directe de z
def f_prime(tk):
    return 1.0 / (1.0 + tk**2)   # dérivée de arctan

# Bruit mesure
SIGMA_OBS = 0.2

# Kalman v1.1 : Q, R fixes
Q_KAL = 1e-4   # bruit processus
R_KAL = SIGMA_OBS**2
A_kal = np.array([[1.0, dt], [0.0, 1.0]])
H_kal = np.array([[1.0, 0.0]])
Qm    = np.diag([Q_KAL, Q_KAL * 0.1])
Rm    = np.array([[R_KAL]])

# PI v1.1 : gains fixes
KP = 1.5
KI = 0.2

# ─── Simulation ──────────────────────────────────────────────────────────────

# État Kalman : x = [z_est, dz_est]
x_kal = np.array([0.0, 0.0])
P_kal = np.eye(2) * 1.0

# État PI
integral_e = 0.0

# État système
y = 0.0   # signal RETA (boucle ouverte)
y_pi = 0.0   # signal RETA avec PI

logs = {k: np.zeros(N) for k in ["y_open", "y_pi", "z_est", "z_vrai",
                                   "u_pi", "e", "V", "t_rup_est"]}

for k in range(N):
    tk = t[k]
    z_v = z_true(tk)
    fp  = f_prime(tk)

    # ── Observation bruitée de z ──
    obs = z_v + rng.standard_normal() * SIGMA_OBS

    # ── Kalman v1.1 ──
    x_kal = A_kal @ x_kal
    P_kal = A_kal @ P_kal @ A_kal.T + Qm
    S     = float((H_kal @ P_kal @ H_kal.T + Rm)[0, 0])
    K_k   = (P_kal @ H_kal.T).flatten() / S
    innov = float(obs) - float((H_kal @ x_kal)[0])
    x_kal = x_kal + K_k * innov
    P_kal = (np.eye(2) - np.outer(K_k, H_kal)) @ P_kal
    z_est = float(x_kal[0])

    # ── Signal boucle ouverte ──
    y += (fp + z_v) * dt
    logs["y_open"][k] = y

    # ── Erreur et PI v1.1 ──
    e = y_pi   # erreur = position courante (référence = 0)
    integral_e += e * dt
    u = KP * e + KI * integral_e

    # ── Signal avec PI ──
    y_pi += (fp + z_v - u) * dt
    logs["y_pi"][k]  = y_pi

    # ── Prédiction t_rup RETA ──
    z_bar = max(z_est, 1e-6)
    t_rup_est = (Y_MAX - np.pi/2) / z_bar   # borne conservative
    logs["z_est"][k]     = z_est
    logs["z_vrai"][k]    = z_v
    logs["u_pi"][k]      = u
    logs["e"][k]         = e
    logs["t_rup_est"][k] = tk + t_rup_est   # temps absolu prédit

    # Lyapunov V = e²/2 + (KI/2)·I²
    logs["V"][k] = 0.5 * e**2 + (KI/2) * integral_e**2

# ─── Analyse ─────────────────────────────────────────────────────────────────
rup_open = np.where(np.abs(logs["y_open"]) > Y_MAX)[0]
rup_pi   = np.where(np.abs(logs["y_pi"])   > Y_MAX)[0]
t_rup_open = f"t={t[rup_open[0]]:.2f}s ⚠️" if len(rup_open) else "JAMAIS ✓"
t_rup_pi   = f"t={t[rup_pi[0]]:.2f}s ⚠️"   if len(rup_pi)   else "JAMAIS ✓"

z_bar_global = np.mean(logs["z_vrai"])
t_rup_reta   = (Y_MAX - np.pi/2) / z_bar_global

print("RETA v1.1 — Résultats")
print(f"  z̄ = {z_bar_global:.4f} | Y_max = {Y_MAX}°")
print(f"  Borne RETA : t_rup ≥ {t_rup_reta:.2f}s")
print(f"  Rupture sans PI : {t_rup_open}")
print(f"  Rupture avec PI : {t_rup_pi}")
print(f"  Kp = {KP}  Ki = {KI}")
print(f"  Bande résiduelle : |e(∞)| ≤ {(3+2**0.5)/KP:.3f}")

# ─── Graphes ─────────────────────────────────────────────────────────────────
fig = plt.figure(figsize=(14, 12))
fig.suptitle("RETA v1.1 — Kalman fixe + PI fixe\n"
             f"Q={Q_KAL:.0e} | R={R_KAL:.0e} | Kp={KP} | Ki={KI}",
             fontsize=13, fontweight="bold")
gs = gridspec.GridSpec(3, 2, figure=fig, hspace=0.45, wspace=0.35)

# Signal
ax = fig.add_subplot(gs[0, :])
ax.plot(t, logs["y_open"], color="gray", lw=1.5, ls="--", label="y(t) sans PI")
ax.plot(t, logs["y_pi"],   color="#1565C0", lw=2, label="y(t) avec PI v1.1")
ax.axhline( Y_MAX, color="red", ls="--", lw=1, label=f"Y_max={Y_MAX}")
ax.axhline(-Y_MAX, color="red", ls="--", lw=1)
ax.axhline(0, color="black", ls=":", lw=0.7)
if len(rup_open): ax.axvline(t[rup_open[0]], color="gray", ls=":", lw=1.2, label=f"rupture sans PI")
ax.set_title("Signal RETA y(t) — boucle ouverte vs PI v1.1", fontsize=10)
ax.set_ylabel("y(t)"); ax.set_xlabel("t [s]")
ax.legend(fontsize=9); ax.set_xlim(0, T_sim)

# z estimé vs vrai
ax = fig.add_subplot(gs[1, 0])
ax.plot(t, logs["z_vrai"], color="red", lw=1.5, ls="--", label="z(t) vrai")
ax.plot(t, logs["z_est"],  color="#1565C0", lw=1.5, label="ẑ(t) Kalman v1.1")
ax.fill_between(t, logs["z_est"], logs["z_vrai"], alpha=0.1, color="blue", label="erreur estim.")
ax.set_title("Estimation z(t) — Kalman v1.1 (Q,R fixes)", fontsize=10)
ax.set_ylabel("z"); ax.set_xlabel("t [s]")
ax.legend(fontsize=9)

# Commande PI
ax = fig.add_subplot(gs[1, 1])
ax.plot(t, logs["u_pi"], color="#2E7D32", lw=1.5, label="u(t) = Kp·e + Ki·∫e")
ax.plot(t, logs["z_vrai"], color="red", lw=1, ls="--", alpha=0.7, label="z(t) à compenser")
ax.set_title("Commande PI v1.1 (gains fixes)", fontsize=10)
ax.set_ylabel("u(t)"); ax.set_xlabel("t [s]")
ax.legend(fontsize=9)

# Lyapunov
ax = fig.add_subplot(gs[2, 0])
ax.semilogy(t, logs["V"] + 1e-12, color="#BF360C", lw=1.5, label="V(e,I) = e²/2 + (Ki/2)I²")
ax.set_title("Lyapunov V(e,I) — décroissance hors compact", fontsize=10)
ax.set_ylabel("V [log]"); ax.set_xlabel("t [s]")
ax.legend(fontsize=9)

# Prédiction t_rup
ax = fig.add_subplot(gs[2, 1])
ax.plot(t, logs["t_rup_est"], color="#7B1FA2", lw=1.5, label="t_rup prédit (borne RETA)")
ax.axhline(T_sim, color="gray", ls=":", lw=1, label="fin simulation")
if len(rup_pi):
    ax.axhline(t[rup_pi[0]], color="red", ls="--", lw=1, label="rupture réelle PI")
ax.set_title("Prédiction t_rup = t + (Y_max−π/2)/ẑ", fontsize=10)
ax.set_ylabel("t_rup prédit [s]"); ax.set_xlabel("t [s]")
ax.legend(fontsize=9); ax.set_ylim(0, T_sim * 2)

out = Path(__file__).parent / "results.png"
plt.savefig(out, dpi=150, bbox_inches="tight")
print(f"\nGraphe → {out}")
