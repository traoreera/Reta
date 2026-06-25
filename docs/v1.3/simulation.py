"""
RETA v1.3 — Boucle de contrôle fermée correcte
=================================================

Modèle physique :
  phi_true(t+dt) = phi_true(t) + u(t)·dt       [drone bascule selon la commande]
  u(t)           = -Kp·phi_est - Ki·∫phi_est    [PI sur angle ESTIMÉ]
  omega_meas     = u(t) + b_true + bruit_g      [gyro mesure taux angulaire + biais]
  phi_est_pred   = phi_est + (omega_meas - b_est)·dt  [Kalman intègre]
  GPS (si dispo) : corrige phi_est ← phi_true + bruit_gps

Accumulation RETA :
  Si b_est ≈ b_true → phi_est ≈ phi_true → PI correct → phi_true → 0 ✓
  Si b_est ≠ b_true → phi_est dérive → PI sur-corrige → phi_true diverge

  y(t)  = phi_true  (erreur RÉELLE, pas estimée)
  z(t)  = b_true − b_est  (perturbation non compensée → accumulation RETA)
  ẏ     = −Kp·y − Ki·I + z(t) + bruit

Scénario : GPS toutes 5s pendant 120s, puis panne totale (dead-reckoning)
  v1.1 : Q_bias << vrai → K_biais ≈ 0 → b_est ne converge pas → z(t) grand → rupture
  v1.3 : Q_bias adaptatif → b_est converge → z(t) petit → PI tient plus longtemps
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from pathlib import Path

rng = np.random.default_rng(42)

# ─── Paramètres physiques ─────────────────────────────────────────────────────
dt    = 0.05        # [s]
T_sim = 300.0       # [s]
N     = int(T_sim / dt)
t     = np.linspace(0, T_sim, N)

# Biais gyro thermique [°/s]
B0       = np.array([0.05, 0.06, 0.08])
TAU      = 80.0
B_FACTOR = 3.0    # biais final = B0 × 4

def true_bias(tk):
    return B0 * (1.0 + B_FACTOR * (1.0 - np.exp(-tk / TAU)))

# Seuils RETA sur l'angle RÉEL
Y_MAX = np.array([5.0, 5.0, 10.0])
E_REF = Y_MAX / 2.0

# Bruit
SIGMA_ANGLE = 0.0028   # bruit gyro [°/√Hz]
R_TRUE_BASE = np.array([0.04, 0.04, 0.25])   # variance GPS [°²]

# GPS : disponible toutes 5s de t=0 à T_OUTAGE, puis coupé
T_GPS_NORMAL = 5.0
K_GPS        = int(T_GPS_NORMAL / dt)
T_OUTAGE     = 120.0

# ─── Kalman ──────────────────────────────────────────────────────────────────
# État : x = [phi_est, b_est]
# Modèle : phi_est(t+dt) = phi_est(t) + (omega_meas - b_est)*dt
#           b_est(t+dt)  = b_est(t)
# où omega_meas = u + b_true + noise = -Kp*phi_est - Ki*I_e + b_true + noise
A   = np.array([[1.0, -dt], [0.0, 1.0]])   # F : phi -= b_est*dt
H   = np.array([[1.0, 0.0]])               # GPS mesure phi_true directement

Q_ANGLE     = SIGMA_ANGLE**2 * dt
Q_BIAS_V11  = (1e-5)**2 * dt               # hypothèse naïve : biais fixe
Q_BIAS_V13  = Q_BIAS_V11 * 1000.0          # a priori conservateur v1.3
Q_MIN       = Q_BIAS_V11 * 0.01
ALPHA_Q     = 0.4

# ─── Gains PI ────────────────────────────────────────────────────────────────
KP0 = np.array([4.0, 4.0, 5.0])
KI0 = np.array([4.0, 4.0, 6.25])
KP_BOUNDS = (1.0, 20.0)
KI_BOUNDS = (0.5, 40.0)
GAMMA_P = 0.2
GAMMA_I = 0.05

# ─── Fonctions Kalman ────────────────────────────────────────────────────────

def kalman_predict(x, P, omega_meas, Q_b):
    """Prédiction avec mesure de taux angulaire (omega = u + bruit + biais)."""
    # phi_pred = phi_est + (omega_meas - b_est)*dt = phi_est + omega_meas*dt - b_est*dt
    # Note: A = [[1,-dt],[0,1]], B = [dt, 0] (pas besoin d'un B séparé ici)
    # On intègre omega_meas directement : phi_pred = phi + omega_meas*dt - b_est*dt
    B_in = np.array([dt, 0.0])  # contribution de omega_meas
    x_p  = A @ x + B_in * omega_meas
    Q    = np.diag([Q_ANGLE, Q_b])
    P_p  = A @ P @ A.T + Q
    return x_p, P_p

def kalman_update(x_p, P_p, phi_gps, R_s):
    S  = float((H @ P_p @ H.T).item()) + R_s
    K  = (P_p @ H.T) / S
    nu = float(phi_gps) - float((H @ x_p).item())
    x  = x_p + K.flatten() * nu
    P  = (np.eye(2) - np.outer(K.flatten(), H)) @ P_p
    return x, P, K.flatten(), nu

# ─── État initial ─────────────────────────────────────────────────────────────

def make_state(q_bias_init):
    return {
        "phi_true" : np.zeros(3),   # angle RÉEL du drone
        "x_est"    : [np.zeros(2) for _ in range(3)],
        "P"        : [np.diag([Q_ANGLE, q_bias_init]) for _ in range(3)],
        "I_e"      : np.zeros(3),   # intégrale de phi_est (pour PI)
        "Kp"       : KP0.copy(),
        "Ki"       : KI0.copy(),
        "Q_bias"   : [q_bias_init] * 3,
    }

s11 = make_state(Q_BIAS_V11)   # v1.1 : Q_bias fixe et petit
s13 = make_state(Q_BIAS_V13)   # v1.3 : Q_bias adaptatif, initialisé grand

# ─── Buffers ─────────────────────────────────────────────────────────────────
logs = {k: np.zeros((N, 3)) for k in
        ["phi_true11", "phi_true13", "phi_est11", "phi_est13",
         "b_est11", "b_est13", "b_true", "Q_bias13", "Kp13", "Ki13", "u11", "u13"]}

# ─── Boucle ──────────────────────────────────────────────────────────────────
print("RETA v1.3 — Boucle fermée | Panne GPS à t=120s")
print(f"  dt={dt}s | T={T_sim}s | GPS/{T_GPS_NORMAL}s → panne à t={T_OUTAGE}s")
print(f"  Biais B0×{1+B_FACTOR:.0f} (TAU={TAU}s)\n")

for k in range(N):
    tk    = t[k]
    b_v   = true_bias(tk)
    noise = rng.standard_normal(3) * SIGMA_ANGLE

    gps_avail = (tk < T_OUTAGE) and (k % K_GPS == 0) and (k > 0)

    for i in range(3):
        phi_true11 = s11["phi_true"][i]
        phi_true13 = s13["phi_true"][i]

        # ── Commande PI (sur angle ESTIMÉ) ──
        phi_est11 = float(s11["x_est"][i][0])
        phi_est13 = float(s13["x_est"][i][0])

        u11 = -s11["Kp"][i] * phi_est11 - s11["Ki"][i] * s11["I_e"][i]
        u13 = -s13["Kp"][i] * phi_est13 - s13["Ki"][i] * s13["I_e"][i]

        # ── Physique : le drone bascule selon u ──
        s11["phi_true"][i] = phi_true11 + u11 * dt
        s13["phi_true"][i] = phi_true13 + u13 * dt

        # ── Mesure gyro : taux angulaire = u + biais_vrai + bruit ──
        omega11 = u11 + b_v[i] + noise[i]   # gyro v1.1 (même gyro physique)
        omega13 = u13 + b_v[i] + noise[i]   # gyro v1.3

        # ── Prédiction Kalman ──
        x11, P11 = kalman_predict(s11["x_est"][i], s11["P"][i], omega11, s11["Q_bias"][i])
        x13, P13 = kalman_predict(s13["x_est"][i], s13["P"][i], omega13, s13["Q_bias"][i])

        # ── Correction GPS ──
        if gps_avail:
            phi_gps11 = s11["phi_true"][i] + rng.standard_normal() * np.sqrt(R_TRUE_BASE[i])
            phi_gps13 = s13["phi_true"][i] + rng.standard_normal() * np.sqrt(R_TRUE_BASE[i])

            x11, P11, K11, nu11 = kalman_update(x11, P11, phi_gps11, R_TRUE_BASE[i])
            x13, P13, K13, nu13 = kalman_update(x13, P13, phi_gps13, R_TRUE_BASE[i])

            # Adaptation Q_bias v1.3 : drift rate = |ν| / T_GPS
            drift_r = abs(nu13) / T_GPS_NORMAL
            q_inst  = max((drift_r * dt)**2, Q_MIN)
            s13["Q_bias"][i] = (1-ALPHA_Q) * s13["Q_bias"][i] + ALPHA_Q * q_inst
            s13["Q_bias"][i] = max(s13["Q_bias"][i], Q_MIN)

        s11["x_est"][i] = x11;  s11["P"][i] = P11
        s13["x_est"][i] = x13;  s13["P"][i] = P13

        # ── Intégrale PI ──
        s11["I_e"][i] += float(x11[0]) * dt
        s13["I_e"][i] += float(x13[0]) * dt

        # ── Adaptation gains v1.3 (phase GPS uniquement) ──
        if tk < T_OUTAGE:
            ebar13 = float(x13[0]) / E_REF[i]
            s13["Kp"][i] = np.clip(s13["Kp"][i] + GAMMA_P * ebar13**2 * dt, *KP_BOUNDS)
            s13["Ki"][i] = np.clip(s13["Ki"][i] + GAMMA_I * ebar13 * s13["I_e"][i] * dt, *KI_BOUNDS)

        # ── Logs ──
        logs["phi_true11"][k, i] = s11["phi_true"][i]
        logs["phi_true13"][k, i] = s13["phi_true"][i]
        logs["phi_est11"][k, i]  = float(x11[0])
        logs["phi_est13"][k, i]  = float(x13[0])
        logs["b_est11"][k, i]    = float(x11[1])
        logs["b_est13"][k, i]    = float(x13[1])
        logs["b_true"][k, i]     = b_v[i]
        logs["Q_bias13"][k, i]   = s13["Q_bias"][i]
        logs["Kp13"][k, i]       = s13["Kp"][i]
        logs["Ki13"][k, i]       = s13["Ki"][i]
        logs["u11"][k, i]        = u11
        logs["u13"][k, i]        = u13

# ─── Résultats ───────────────────────────────────────────────────────────────
labels = ["Roll (X)", "Pitch (Y)", "Yaw (Z)"]

print("=" * 70)
print(f"  Erreur RÉELLE (phi_true) — boucle fermée avec correcteur PI")
print("=" * 70)
print(f"{'Axe':<12} {'v1.1 max':>10} {'v1.3 max':>10}  Rupture v1.1   Rupture v1.3")
print("-" * 70)
for i, name in enumerate(labels):
    y11  = logs["phi_true11"][:, i]
    y13  = logs["phi_true13"][:, i]
    m11  = np.max(np.abs(y11))
    m13  = np.max(np.abs(y13))
    idx11 = np.where(np.abs(y11) > Y_MAX[i])[0]
    idx13 = np.where(np.abs(y13) > Y_MAX[i])[0]
    r11   = f"t={t[idx11[0]]:.0f}s ⚠️" if len(idx11) else "JAMAIS ✓"
    r13   = f"t={t[idx13[0]]:.0f}s ⚠️" if len(idx13) else "JAMAIS ✓"
    print(f"{name:<12} {m11:>9.3f}° {m13:>9.3f}°  {r11:<14} {r13}")

print()
for i, name in enumerate(labels):
    bv  = true_bias(T_OUTAGE)[i]
    be11 = logs["b_est11"][int(T_OUTAGE/dt), i]
    be13 = logs["b_est13"][int(T_OUTAGE/dt), i]
    q13  = logs["Q_bias13"][-1, i]
    kp   = logs["Kp13"][-1, i]
    ki   = logs["Ki13"][-1, i]
    print(f"{name} — biais à panne t={T_OUTAGE:.0f}s :")
    print(f"  vrai={bv*1000:.1f}m°/s | v1.1={be11*1000:.1f}m°/s | v1.3={be13*1000:.1f}m°/s")
    print(f"  Q_bias v1.3={q13:.1e} (×{q13/Q_BIAS_V11:.0f} vs v1.1)")
    print(f"  Gains PI v1.3 : Kp={kp:.2f}  Ki={ki:.2f}")

# ─── Graphes ─────────────────────────────────────────────────────────────────
colors = ["#1565C0", "#2E7D32", "#BF360C"]
fig = plt.figure(figsize=(16, 20))
fig.suptitle(
    "RETA v1.3 — Boucle fermée (PI + Kalman adaptatif)\n"
    f"Panne GPS à t={T_OUTAGE:.0f}s | Erreur mesurée sur phi_RÉEL (pas estimé)",
    fontsize=12, fontweight="bold")
gs = gridspec.GridSpec(5, 3, figure=fig, hspace=0.5, wspace=0.35)

for i in range(3):
    # Angle réel phi_true
    ax = fig.add_subplot(gs[0, i])
    ax.axvspan(T_OUTAGE, T_sim, color="lightyellow", alpha=0.5)
    ax.axvline(T_OUTAGE, color="orange", ls=":", lw=1.5, label=f"panne GPS")
    ax.plot(t, logs["phi_true11"][:, i], color="gray", lw=1, alpha=0.8, label="v1.1 φ_réel")
    ax.plot(t, logs["phi_true13"][:, i], color=colors[i], lw=1.5, label="v1.3 φ_réel")
    ax.axhline( Y_MAX[i], color="red", ls="--", lw=0.8)
    ax.axhline(-Y_MAX[i], color="red", ls="--", lw=0.8)
    ax.set_title(f"Angle réel — {labels[i]}", fontsize=9)
    ax.set_ylabel("φ_réel [°]"); ax.set_xlabel("t [s]")
    ax.legend(fontsize=7); ax.set_xlim(0, T_sim)

    # Angle estimé vs réel (v1.3)
    ax = fig.add_subplot(gs[1, i])
    ax.axvspan(T_OUTAGE, T_sim, color="lightyellow", alpha=0.5)
    ax.axvline(T_OUTAGE, color="orange", ls=":", lw=1.5)
    ax.plot(t, logs["phi_true13"][:, i], color=colors[i], lw=2, label="φ_réel v1.3")
    ax.plot(t, logs["phi_est13"][:, i], color=colors[i], lw=1, ls="--", alpha=0.6, label="φ_estimé v1.3")
    ax.plot(t, logs["phi_true11"][:, i], color="gray", lw=1, alpha=0.5, label="φ_réel v1.1")
    ax.set_title(f"Réel vs estimé — {labels[i]}", fontsize=9)
    ax.set_ylabel("Angle [°]"); ax.set_xlabel("t [s]")
    ax.legend(fontsize=7); ax.set_xlim(0, T_sim)

    # Biais vrai vs estimé
    ax = fig.add_subplot(gs[2, i])
    b_v = np.array([true_bias(tk)[i]*1000 for tk in t])
    ax.axvspan(T_OUTAGE, T_sim, color="lightyellow", alpha=0.5)
    ax.axvline(T_OUTAGE, color="orange", ls=":", lw=1.5)
    ax.plot(t, b_v, color="red", lw=1.5, ls="--", label="biais vrai")
    ax.plot(t, logs["b_est11"][:, i]*1000, color="gray", alpha=0.7, lw=1, label="v1.1 b̂")
    ax.plot(t, logs["b_est13"][:, i]*1000, color=colors[i], lw=1.5, label="v1.3 b̂")
    ax.set_title(f"Biais estimé — {labels[i]}", fontsize=9)
    ax.set_ylabel("Biais [m°/s]"); ax.set_xlabel("t [s]")
    ax.legend(fontsize=7); ax.set_xlim(0, T_sim)

    # Q_bias adaptatif
    ax = fig.add_subplot(gs[3, i])
    ax.axvspan(T_OUTAGE, T_sim, color="lightyellow", alpha=0.5)
    ax.axvline(T_OUTAGE, color="orange", ls=":", lw=1.5)
    ax.semilogy(t, logs["Q_bias13"][:, i], color=colors[i], lw=1.5, label="Q_bias v1.3")
    ax.axhline(Q_BIAS_V11, color="gray", ls="--", lw=1, label=f"Q_bias v1.1 (fixe)")
    ax.set_title(f"Q_bias — {labels[i]}", fontsize=9)
    ax.set_ylabel("Q [°²/s]"); ax.set_xlabel("t [s]")
    ax.legend(fontsize=7); ax.set_xlim(0, T_sim)

    # Commande PI
    ax = fig.add_subplot(gs[4, i])
    ax.axvspan(T_OUTAGE, T_sim, color="lightyellow", alpha=0.5)
    ax.axvline(T_OUTAGE, color="orange", ls=":", lw=1.5)
    ax.plot(t, logs["u11"][:, i], color="gray", lw=1, alpha=0.8, label="u(t) v1.1")
    ax.plot(t, logs["u13"][:, i], color=colors[i], lw=1.5, label="u(t) v1.3")
    ax.set_title(f"Commande PI — {labels[i]}", fontsize=9)
    ax.set_ylabel("u [°/s]"); ax.set_xlabel("t [s]")
    ax.legend(fontsize=7); ax.set_xlim(0, T_sim)

out = Path(__file__).parent / "results.png"
plt.savefig(out, dpi=150, bbox_inches="tight")
print(f"\nGraphe → {out}")
