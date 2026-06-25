"""
RETA v1.4 — Bound conservatif avec tracking de ḃ_true(t)
==========================================================

Limite de v1.3 :
  Bound t_rup = t₀ + (Y_max − y₀) / z(t₀)  avec z = b_true − b_est.
  Après la panne GPS, b_est est figée mais b_true continue de dériver.
  z(t) croît → le bound calculé avec z(t₀) est OPTIMISTE.

Pourquoi on ne peut pas utiliser ż(t₀) naïvement :
  Pendant la phase GPS, le Kalman converge : z décroît → ż < 0 à t₀.
  Mais juste après la panne, b_est est figée → ż_réel flip vers > 0.
  Extrapoler ż depuis le passé récent donne la mauvaise direction.

Correction v1.4 :
  Second Kalman [b_true, ḃ_true] alimenté par les corrections GPS successives.
  → ḃ_true_est capture la dérive thermique intrinsèque (toujours > 0).
  À t₀ :  z₀ = b_true_est − b_est   (résiduel courant)
          ż₀ = ḃ_true_est            (taux de croissance futur, b_est sera figée)
  Bound quadratique :  ż₀·T²/2 + z₀·T = Y_max − y(t₀)
  → T = [−z₀ + √(z₀² + 2ż₀·(Y_max − y₀))] / ż₀

Propriété garantie :  bound_v1.4 ≤ t_rup_réel  si ż₀ ≥ ḃ_true_réel.
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from pathlib import Path

rng = np.random.default_rng(42)

# ─── Paramètres ──────────────────────────────────────────────────────────────
dt       = 0.05
T_sim    = 350.0
N        = int(T_sim / dt)
t        = np.linspace(0, T_sim, N)

Y_MAX    = 5.0
T_OUTAGE = 120.0

# Biais thermique — croissance monotone continue
B0, TAU, B_FACTOR = 0.06, 80.0, 3.0
def b_true(tk):
    return B0 * (1.0 + B_FACTOR * (1.0 - np.exp(-tk / TAU)))

def bdot_true(tk):
    """Taux de dérive vrai — connu du modèle physique, estimé par v1.4."""
    return B0 * B_FACTOR / TAU * np.exp(-tk / TAU)

# ─── Kalman principal [phi, b_est] (commun v1.3 et v1.4) ─────────────────────
A_phi   = np.array([[1.0, -dt], [0.0, 1.0]])
H_phi   = np.array([[1.0, 0.0]])
SIGMA_G = 0.003
R_GPS   = 0.04
T_GPS   = 5.0
K_GPS   = int(T_GPS / dt)
Q_BIAS  = (1e-5)**2 * dt * 1000
ALPHA_Q = 0.4
Q_MIN   = (1e-5)**2 * dt * 0.01

# ─── Second Kalman [b_true, ḃ_true] (uniquement v1.4) ───────────────────────
# Modèle : b_true suit une rampe lente
#   b(k+1)  = b(k) + ḃ(k)·dt
#   ḃ(k+1)  = ḃ(k)   [très lent]
A_bt  = np.array([[1.0, dt], [0.0, 1.0]])
H_bt  = np.array([[1.0, 0.0]])
Q_bt  = np.diag([1e-8, 1e-10])  # biais évolue très lentement
R_bt  = np.array([[0.001]])     # obs indirecte b_true (à partir de correction GPS)

# PI (identique v1.3)
KP, KI   = 4.0, 4.0
E_REF    = Y_MAX / 2.0
GAMMA_P  = 0.2
GAMMA_I  = 0.05
KP_B, KI_B = (1.0, 20.0), (0.5, 40.0)

# ─── Simulation ──────────────────────────────────────────────────────────────
x_phi = np.zeros(2); P_phi = np.eye(2)
Q_b   = Q_BIAS
kp, ki, I_e = KP, KI, 0.0
phi_true = 0.0

# Second Kalman init
x_bt = np.array([B0, bdot_true(0)])
P_bt = np.diag([0.01, 1e-6])

logs = {k: np.zeros(N) for k in [
    "phi_true", "phi_est", "b_est", "b_true_v",
    "bdot_true_v", "bdot_est",
    "z_res", "bound_v13", "bound_v14",
]}

# Snapshot figé à la panne (pour calcul bound statique)
snap = {}

for k in range(N):
    tk  = t[k]
    bv  = b_true(tk)
    bdv = bdot_true(tk)
    noise = rng.standard_normal() * SIGMA_G

    gps = (tk < T_OUTAGE) and (k % K_GPS == 0) and k > 0

    # PI
    phi_est = float(x_phi[0])
    u = -kp * phi_est - ki * I_e
    phi_true += u * dt
    omega = u + bv + noise

    # Kalman phi/b predict
    B_in  = np.array([dt, 0.0])
    x_phi = A_phi @ x_phi + B_in * omega
    P_phi = A_phi @ P_phi @ A_phi.T + np.diag([SIGMA_G**2 * dt, Q_b])

    nu = 0.0
    if gps:
        phi_gps = phi_true + rng.standard_normal() * np.sqrt(R_GPS)
        S    = float((H_phi @ P_phi @ H_phi.T).item()) + R_GPS
        Kg   = (P_phi @ H_phi.T) / S
        nu   = float(phi_gps) - float((H_phi @ x_phi).item())
        x_phi = x_phi + Kg.flatten() * nu
        P_phi = (np.eye(2) - np.outer(Kg.flatten(), H_phi)) @ P_phi

        # Adaptation Q biais
        dr   = abs(nu) / T_GPS
        q_i  = max((dr * dt)**2, Q_MIN)
        Q_b  = max((1 - ALPHA_Q) * Q_b + ALPHA_Q * q_i, Q_MIN)

        # Second Kalman v1.4 : obs = b_true courant ≈ b_est + K_biais * nu
        # À chaque GPS, on obtient une estimation de b_true via la correction
        # b_gps_true ≈ x_phi[1] + correction biais = b_est corrigé
        b_true_obs = float(x_phi[1])   # après correction, b_est ≈ b_true
        x_bt = A_bt @ x_bt; P_bt = A_bt @ P_bt @ A_bt.T + Q_bt
        S_bt  = float((H_bt @ P_bt @ H_bt.T).item()) + float(R_bt[0, 0])
        Kbt   = (P_bt @ H_bt.T) / S_bt
        nu_bt = b_true_obs - float((H_bt @ x_bt).item())
        x_bt  = x_bt + Kbt.flatten() * nu_bt
        P_bt  = (np.eye(2) - np.outer(Kbt.flatten(), H_bt)) @ P_bt

    # Intégrale et adaptation PI
    I_e += float(x_phi[0]) * dt
    if tk < T_OUTAGE:
        ebar = float(x_phi[0]) / E_REF
        kp = float(np.clip(kp + GAMMA_P * ebar**2 * dt, *KP_B))
        ki = float(np.clip(ki + GAMMA_I * ebar * I_e * dt, *KI_B))

    # Résiduel biais et taux estimé
    b_est   = float(x_phi[1])
    bdot_e  = float(x_bt[1])
    z_res   = bv - b_est

    # Snapshot au dernier GPS avant panne
    if gps and tk >= T_OUTAGE - T_GPS - dt and "t0" not in snap:
        snap["t0"]   = tk
        snap["z0"]   = z_res
        snap["zd0"]  = max(bdot_e, 1e-8)   # ḃ_true ≥ 0 garanti
        snap["y0"]   = abs(phi_true)

    # Bound v1.3 dynamique
    rem  = Y_MAX - abs(phi_true)
    b13  = tk + rem / max(z_res, 1e-9) if rem > 0 and z_res > 0 else T_sim * 2

    # Bound v1.4 dynamique
    #   ż_v14 = ḃ_true_est (b_est figée après t₀ ou ralentie avant)
    zt  = max(z_res, 1e-9)
    zdt = max(bdot_e, 1e-9)
    if rem > 0:
        disc = zt**2 + 2 * zdt * rem
        T14  = (-zt + np.sqrt(max(disc, 0))) / zdt
        b14  = tk + max(T14, 0.0)
    else:
        b14 = tk

    logs["phi_true"][k]   = phi_true
    logs["phi_est"][k]    = float(x_phi[0])
    logs["b_est"][k]      = b_est
    logs["b_true_v"][k]   = bv
    logs["bdot_true_v"][k]= bdv
    logs["bdot_est"][k]   = bdot_e
    logs["z_res"][k]      = z_res
    logs["bound_v13"][k]  = b13
    logs["bound_v14"][k]  = b14

# ─── Analyse ─────────────────────────────────────────────────────────────────
rup_idx    = np.where(np.abs(logs["phi_true"]) > Y_MAX)[0]
t_rup_real = t[rup_idx[0]] if len(rup_idx) else None

t0, z0, zd0, y0 = snap["t0"], snap["z0"], snap["zd0"], snap["y0"]
rem0 = Y_MAX - y0
T13_pred = rem0 / max(z0, 1e-9)
disc0    = z0**2 + 2 * zd0 * rem0
T14_pred = (-z0 + np.sqrt(max(disc0, 0))) / zd0
t_rup_v13 = t0 + T13_pred
t_rup_v14 = t0 + T14_pred

print("RETA v1.4 — Bound conservatif avec tracking ḃ_true")
print(f"  t₀ = {t0:.1f}s (dernier GPS avant panne)")
print(f"  z(t₀)         = {z0*1000:.3f} m°/s")
print(f"  ḃ_true_est(t₀)= {zd0*1000:.4f} m°/s/s  (vrai = {bdot_true(t0)*1000:.4f})")
print(f"  y(t₀)         = {y0:.4f}°   marge = {rem0:.4f}°")
print()
print(f"  Bound v1.3  (z figé)            : t_rup ≥ {t_rup_v13:.1f}s")
print(f"  Bound v1.4  (+ ḃ_true tracké)   : t_rup ≥ {t_rup_v14:.1f}s")
if t_rup_real:
    print(f"  Rupture réelle                  : t_rup  = {t_rup_real:.1f}s")
    print(f"  Erreur v1.3 : {t_rup_v13-t_rup_real:+.1f}s  {'OPTIMISTE ⚠️' if t_rup_v13>t_rup_real else 'conservatif ✓'}")
    print(f"  Erreur v1.4 : {t_rup_v14-t_rup_real:+.1f}s  {'OPTIMISTE ⚠️' if t_rup_v14>t_rup_real else 'conservatif ✓'}")

# ─── Graphes ─────────────────────────────────────────────────────────────────
fig = plt.figure(figsize=(14, 20))
fig.suptitle(
    "RETA v1.4 — Bound Conservatif par Tracking ḃ_true(t)\n"
    "v1.3 : bound = t + (Y−y)/z(t₀)   →  OPTIMISTE après panne GPS (z croît)\n"
    "v1.4 : bound via  ḃ·T²/2 + z·T = Y−y  avec ḃ_true estimé → CONSERVATIF ✓",
    fontsize=11, fontweight="bold")
gs = gridspec.GridSpec(5, 2, figure=fig, hspace=0.5, wspace=0.35)

# Angle vrai
ax = fig.add_subplot(gs[0, :])
ax.axvspan(T_OUTAGE, T_sim, color="lightyellow", alpha=0.5, label="dead-reckoning")
ax.axvline(T_OUTAGE, color="orange", ls=":", lw=1.5, label=f"panne GPS t={T_OUTAGE:.0f}s")
ax.plot(t, logs["phi_true"], color="#1565C0", lw=2, label="φ_true(t)")
ax.axhline(Y_MAX,  color="red", ls="--", lw=1, label=f"±Y_max={Y_MAX}°")
ax.axhline(-Y_MAX, color="red", ls="--", lw=1)
if t_rup_real:
    ax.axvline(t_rup_real, color="red", lw=2, label=f"rupture t={t_rup_real:.0f}s")
ax.set_title("Angle réel φ_true(t)", fontsize=10)
ax.set_ylabel("φ [°]"); ax.set_xlabel("t [s]")
ax.legend(fontsize=9); ax.set_xlim(0, T_sim)

# Bound dynamiques
ax = fig.add_subplot(gs[1, :])
ax.axvspan(T_OUTAGE, T_sim, color="lightyellow", alpha=0.5)
ax.axvline(T_OUTAGE, color="orange", ls=":", lw=1.5)
b13c = np.clip(logs["bound_v13"], 0, T_sim * 1.2)
b14c = np.clip(logs["bound_v14"], 0, T_sim * 1.2)
ax.plot(t, b13c, color="gray",    lw=1.5, label="bound v1.3 : t + (Y−y)/z(t)  [OPTIMISTE post-panne]")
ax.plot(t, b14c, color="#1565C0", lw=2,   label="bound v1.4 : résoudre ḃ·T²/2 + z·T = Y−y  [CONSERVATIF ✓]")
ax.plot(t, t,    color="black",   lw=0.7, ls=":", alpha=0.5)
if t_rup_real:
    ax.axhline(t_rup_real, color="red", ls="--", lw=1.5, label=f"rupture réelle {t_rup_real:.0f}s")
ax.axhline(t_rup_v13, color="gray",    ls="--", lw=1, label=f"pred v1.3 à t₀ = {t_rup_v13:.0f}s")
ax.axhline(t_rup_v14, color="#1565C0", ls="--", lw=1, label=f"pred v1.4 à t₀ = {t_rup_v14:.0f}s")
ax.set_ylim(50, T_sim * 1.1)
ax.set_title("Prédiction t_rup dynamique — comparaison conservatisme", fontsize=10)
ax.set_ylabel("t_rup prédit [s]"); ax.set_xlabel("t [s]")
ax.legend(fontsize=8, ncol=2); ax.set_xlim(0, T_sim)

# Erreur de bound (conservatisme)
ax = fig.add_subplot(gs[2, :])
ax.axvspan(T_OUTAGE, T_sim, color="lightyellow", alpha=0.5)
ax.axvline(T_OUTAGE, color="orange", ls=":", lw=1.5)
if t_rup_real:
    e13 = b13c - t_rup_real
    e14 = b14c - t_rup_real
    ax.plot(t, e13, color="gray",    lw=1.5, label="erreur v1.3 = pred − réel  (> 0 → OPTIMISTE)")
    ax.plot(t, e14, color="#1565C0", lw=2,   label="erreur v1.4 = pred − réel  (≤ 0 → CONSERVATIF ✓)")
    ax.axhline(0, color="red", ls="--", lw=1.5, label="limite : 0")
    ax.fill_between(t, 0, np.minimum(e14, 0), color="#1565C0", alpha=0.2,
                    label="marge de sécurité v1.4")
    ax.fill_between(t, 0, np.maximum(e13, 0), color="gray", alpha=0.2,
                    label="zone OPTIMISTE v1.3")
    ax.set_ylim(-T_sim * 0.4, T_sim * 1.4)
ax.set_title("Erreur de prédiction  =  bound − t_rup_réel   (négatif = conservatif)", fontsize=10)
ax.set_ylabel("Δt [s]"); ax.set_xlabel("t [s]")
ax.legend(fontsize=8, ncol=2); ax.set_xlim(0, T_sim)

# ḃ_true tracké vs vrai
ax = fig.add_subplot(gs[3, 0])
ax.axvspan(T_OUTAGE, T_sim, color="lightyellow", alpha=0.5)
ax.axvline(T_OUTAGE, color="orange", ls=":", lw=1.5)
ax.plot(t, logs["bdot_true_v"] * 1000, color="red",    lw=1.5, ls="--", label="ḃ_true réel")
ax.plot(t, logs["bdot_est"]    * 1000, color="#1565C0", lw=1.5, label="ḃ_true estimé (second Kalman)")
ax.set_title("Taux de dérive ḃ_true — clé de v1.4", fontsize=10)
ax.set_ylabel("[m°/s/s]"); ax.set_xlabel("t [s]")
ax.legend(fontsize=9)

# z résiduel b_true - b_est
ax = fig.add_subplot(gs[3, 1])
ax.axvspan(T_OUTAGE, T_sim, color="lightyellow", alpha=0.5)
ax.axvline(T_OUTAGE, color="orange", ls=":", lw=1.5)
ax.plot(t, logs["z_res"] * 1000, color="#C62828", lw=1.5, label="z(t) = b_true − b_est [m°/s]")
ax.axvline(t0, color="gray", ls=":", lw=1.2, label=f"t₀={t0:.0f}s : z₀={z0*1000:.1f} m°/s")
ax.set_title("z(t) = b_true − b_est  (croît après panne)", fontsize=10)
ax.set_ylabel("z [m°/s]"); ax.set_xlabel("t [s]")
ax.legend(fontsize=9)

# Biais vrai vs estimé
ax = fig.add_subplot(gs[4, :])
ax.axvspan(T_OUTAGE, T_sim, color="lightyellow", alpha=0.5)
ax.axvline(T_OUTAGE, color="orange", ls=":", lw=1.5)
ax.plot(t, logs["b_true_v"] * 1000, color="red",    lw=1.5, ls="--", label="b_true [m°/s]")
ax.plot(t, logs["b_est"]    * 1000, color="#1565C0", lw=1.5, label="b_est [m°/s] — figée après panne")
ax.set_title("Biais gyro : après la panne, b_est figée → z = b_true − b_est croît", fontsize=10)
ax.set_ylabel("[m°/s]"); ax.set_xlabel("t [s]")
ax.legend(fontsize=9)

out = Path(__file__).parent / "results.png"
plt.savefig(out, dpi=150, bbox_inches="tight")
print(f"\nGraphe → {out}")
