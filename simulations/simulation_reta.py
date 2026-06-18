"""
Simulation RETA — Referential Escape Theory by Accumulation
Données réelles : NASA GISS Surface Temperature Analysis (GLOBTemp v4)
https://data.giss.nasa.gov/gistemp/
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from scipy.optimize import brentq
import urllib.request
import io
import csv

# ─────────────────────────────────────────────
# 0. CHARGEMENT DES DONNÉES NASA GISS
# ─────────────────────────────────────────────

NASA_URL = "https://data.giss.nasa.gov/gistemp/tabledata_v4/GLB.Ts+dSST.csv"

def charger_donnees_nasa():
    print("Téléchargement des données NASA GISS...")
    try:
        with urllib.request.urlopen(NASA_URL, timeout=10) as r:
            contenu = r.read().decode("utf-8")
    except Exception as e:
        raise RuntimeError(f"Impossible de télécharger les données NASA : {e}")

    annees, anomalies = [], []
    lecteur = csv.reader(io.StringIO(contenu))
    en_tete_passee = False
    for ligne in lecteur:
        if not ligne:
            continue
        # La ligne d'en-tête contient "Year"
        if ligne[0].strip() == "Year":
            en_tete_passee = True
            continue
        if not en_tete_passee:
            continue
        try:
            annee = int(ligne[0].strip())
            val = ligne[13].strip()  # colonne "J-D" = moyenne annuelle
            if val in ("", "****"):
                continue
            anomalies.append(float(val))
            annees.append(annee)
        except (ValueError, IndexError):
            continue

    print(f"  → {len(annees)} années chargées ({annees[0]}–{annees[-1]})")
    return np.array(annees), np.array(anomalies)

annees, anomalies = charger_donnees_nasa()

# ─────────────────────────────────────────────
# RECALIBRATION — référence 1951–1980 (standard NASA)
# ─────────────────────────────────────────────
# Les données NASA GISS sont déjà exprimées par rapport à 1951-1980 = 0.
# On recentre t=0 sur 1951 et on calibre ε sur la phase d'accélération
# post-1980 (période où la perturbation CO2 est clairement persistante).

ANNEE_ZERO = 1951          # début de la période de référence NASA
ANNEE_CALIB_DEBUT = 1980   # calibration ε sur l'ère post-industrielle accélérée

masque = annees >= ANNEE_ZERO
annees = annees[masque]
anomalies = anomalies[masque]

# t=0 en 1951
t_reel = annees - ANNEE_ZERO
y_reel = anomalies

# Offset préindustriel : la moyenne 1880-1950 est ~-0.3°C dans les données NASA
# donc +2°C préindustriel ≈ +1.7°C dans l'échelle NASA (1951-1980=0)
# et   +1.5°C préindustriel ≈ +1.2°C dans l'échelle NASA
OFFSET_PREINDUSTRIEL = 0.29   # °C — écart entre préindustriel et référence 1951-1980
Y_max_paris2   = 2.0  - OFFSET_PREINDUSTRIEL   # +2°C préindustriel dans échelle NASA
Y_max_paris1p5 = 1.5  - OFFSET_PREINDUSTRIEL   # +1.5°C préindustriel dans échelle NASA

# ─────────────────────────────────────────────
# 1. AJUSTEMENT DU MODÈLE RETA SUR LES DONNÉES
# ─────────────────────────────────────────────
# ε calibré sur la phase d'accélération post-1980

masque_calib = annees >= ANNEE_CALIB_DEBUT
t_calib = t_reel[masque_calib]
y_calib = y_reel[masque_calib]
pente, offset = np.polyfit(t_calib, y_calib, 1)
epsilon = max(pente, 1e-4)

print(f"\nCalibration RETA (référence NASA 1951–1980) :")
print(f"  ε (dérive post-1980)           = {epsilon:.4f} °C/an")
print(f"  Offset préindustriel           = {OFFSET_PREINDUSTRIEL} °C")
print(f"  Y_max +2°C  (échelle NASA)     = {Y_max_paris2:.2f} °C")
print(f"  Y_max +1.5°C (échelle NASA)    = {Y_max_paris1p5:.2f} °C")

# ─────────────────────────────────────────────
# 2. MODÈLE RETA V1.0 — DÉRIVE LIBRE
# ─────────────────────────────────────────────
# Calibration sur la phase "dormante" 1951–1980 (période de référence = régime borné)

masque_borne = annees < ANNEE_CALIB_DEBUT
t_borne = t_reel[masque_borne]
y_borne = y_reel[masque_borne]

A_calib   = np.std(y_borne) * 2             # amplitude de la saturation initiale
tau_calib = max(t_borne[-1] / np.pi, 1.0)   # constante de temps sur la phase bornée
L = A_calib * np.pi / 2                     # asymptote théorique sans perturbation

def y_reta(t, eps=epsilon):
    return A_calib * np.arctan(t / tau_calib) + eps * t

t_pred = np.linspace(0, t_reel[-1] + 80, 600)
y_pred = y_reta(t_pred)

# ─────────────────────────────────────────────
# 3. CALCUL DES POINTS DE RUPTURE
# ─────────────────────────────────────────────

def calculer_rupture(Y_seuil, label=""):
    t_cons = (Y_seuil - L) / epsilon if (Y_seuil - L) > 0 else None
    try:
        f = lambda t: y_reta(t) - Y_seuil
        t_exact = brentq(f, 0, 300) if f(0) < 0 and f(300) > 0 else None
    except ValueError:
        t_exact = None
    annee_rup = ANNEE_ZERO + t_exact if t_exact else None
    print(f"\nSeuil {label} = {Y_seuil:.2f} °C (échelle NASA)")
    if t_cons:
        print(f"  t_rupture conservatif ≥ {t_cons:.1f} ans → {ANNEE_ZERO+t_cons:.0f}")
    if annee_rup:
        print(f"  t_rupture exact       = {t_exact:.1f} ans → {annee_rup:.0f}")
    return t_exact, annee_rup

t_rup_2, annee_rup_2     = calculer_rupture(Y_max_paris2,   "+2°C préindustriel")
t_rup_15, annee_rup_15   = calculer_rupture(Y_max_paris1p5, "+1.5°C préindustriel")

# ─────────────────────────────────────────────
# 4. FILTRE DE KALMAN v1.1
# ─────────────────────────────────────────────
def kalman_reta(y_obs, dt=1.0, Q0=1e-4, R0=1e-2):
    n = len(y_obs)
    y_hat = np.zeros(n)
    z_hat = np.zeros(n)    # dérive estimée
    P = np.eye(2) * 0.1
    x = np.array([y_obs[0], epsilon])

    F = np.array([[1, dt], [0, 1]])
    H = np.array([[1, 0]])
    Q = np.diag([Q0, Q0 * 0.01])
    R = np.array([[R0]])

    for k in range(n):
        # Prédiction
        x = F @ x
        P = F @ P @ F.T + Q
        # Innovation
        nu = y_obs[k] - H @ x
        S = H @ P @ H.T + R
        G = P @ H.T @ np.linalg.inv(S)
        # Mise à jour
        x = x + G.flatten() * nu[0]
        P = (np.eye(2) - G @ H) @ P

        y_hat[k] = x[0]
        z_hat[k] = x[1]

    return y_hat, z_hat

y_kalman, z_kalman = kalman_reta(y_reel)
print(f"\nKalman v1.1 :")
print(f"  ẑ moyen (dérive estimée) = {z_kalman[-10:].mean():.4f} °C/an")

# ─────────────────────────────────────────────
# 5. CORRECTEUR PI v1.0 (SIMULATION)
# ─────────────────────────────────────────────
Y_consigne = Y_max_paris1p5   # +1.5°C préindustriel dans l'échelle NASA
Kp = 0.8
Ki = Kp**2 / 4     # régime critique

dt = 1.0
N_sim = 200
t_sim = np.arange(N_sim) * dt
y_sim = np.zeros(N_sim)
y_sim[0] = y_reel[-1]   # part de l'état actuel
integral_e = 0.0

for k in range(1, N_sim):
    t_k = t_reel[-1] + k
    z_k = z_kalman[-1]   # perturbation estimée par Kalman
    f_prime = A_calib / (tau_calib * (1 + (t_k / tau_calib)**2))
    e_k = y_sim[k-1] - Y_consigne
    integral_e += e_k * dt
    u_k = Kp * e_k + Ki * integral_e
    dy = f_prime + z_k - u_k
    y_sim[k] = y_sim[k-1] + dy * dt

t_stable_theorique = 8 / Kp
print(f"\nCorrecteur PI v1.0 :")
print(f"  Kp={Kp}, Ki={Ki:.4f}")
print(f"  t_stable théorique ≈ {t_stable_theorique:.1f} ans")
print(f"  Consigne Y_c = {Y_consigne} °C")

# ─────────────────────────────────────────────
# 6. VISUALISATIONS
# ─────────────────────────────────────────────
plt.style.use("dark_background")
fig = plt.figure(figsize=(16, 12))
fig.suptitle("RETA — Simulation sur données NASA GISS (Anomalies temp. globale)",
             fontsize=14, fontweight="bold", color="white", y=0.98)

gs = gridspec.GridSpec(3, 2, hspace=0.45, wspace=0.35)

# ── Panneau 1 : Données brutes + modèle RETA v1.0 ──
ax1 = fig.add_subplot(gs[0, :])
ax1.fill_between(annees, y_reel, 0,
                 where=(y_reel >= 0), color="#e74c3c", alpha=0.3, label="Anomalie +")
ax1.fill_between(annees, y_reel, 0,
                 where=(y_reel < 0),  color="#3498db", alpha=0.3, label="Anomalie −")
ax1.plot(annees, y_reel, color="white", lw=0.8, alpha=0.6)
ax1.plot(annees[0] + t_pred, y_pred, color="#f39c12", lw=1.5,
         linestyle="--", label="Modèle RETA v1.0 (dérive libre)")
ax1.plot(annees, y_kalman, color="#2ecc71", lw=1.5, label="Kalman v1.1 (ŷ filtré)")
ax1.axhline(Y_max_paris2, color="#e74c3c", lw=1.2, linestyle=":",
            label=f"Seuil +2°C préind. ({Y_max_paris2:.2f}°C NASA)")
ax1.axhline(Y_max_paris1p5, color="#e67e22", lw=1.2, linestyle=":",
            label=f"Seuil +1.5°C préind. ({Y_max_paris1p5:.2f}°C NASA)")
if annee_rup_15:
    ax1.axvline(annee_rup_15, color="#e67e22", lw=1.5, linestyle="--", alpha=0.8)
    ax1.text(annee_rup_15 + 1, Y_max_paris1p5 + 0.05,
             f"≈{annee_rup_15:.0f}", color="#e67e22", fontsize=9)
if annee_rup_2:
    ax1.axvline(annee_rup_2, color="#e74c3c", lw=1.5, linestyle="--", alpha=0.8)
    ax1.text(annee_rup_2 + 1, Y_max_paris2 + 0.05,
             f"≈{annee_rup_2:.0f}", color="#e74c3c", fontsize=9)
ax1.set_ylabel("Anomalie (°C)", color="white")
ax1.set_xlabel("Année", color="white")
ax1.set_title("Données NASA GISS + Modèle RETA", color="white", fontsize=11)
ax1.legend(fontsize=8, loc="upper left", framealpha=0.3)
ax1.grid(alpha=0.15)

# ── Panneau 2 : Dérive estimée par Kalman (ẑ) ──
ax2 = fig.add_subplot(gs[1, 0])
ax2.plot(annees, z_kalman, color="#2ecc71", lw=1.5)
ax2.axhline(epsilon, color="#f39c12", lw=1, linestyle="--",
            label=f"ε global = {epsilon:.4f} °C/an")
ax2.fill_between(annees, 0, z_kalman, alpha=0.2, color="#2ecc71")
ax2.set_title("ẑ — Dérive estimée (Kalman)", color="white", fontsize=10)
ax2.set_ylabel("°C/an", color="white")
ax2.set_xlabel("Année", color="white")
ax2.legend(fontsize=8, framealpha=0.3)
ax2.grid(alpha=0.15)

# ── Panneau 3 : t_rupture dynamique ──
ax3 = fig.add_subplot(gs[1, 1])
t_rup_dyn_2 = np.where(z_kalman > 1e-6, (Y_max_paris2 - y_kalman) / z_kalman, np.nan)
t_rup_dyn_15 = np.where(z_kalman > 1e-6, (Y_max_paris1p5 - y_kalman) / z_kalman, np.nan)
t_rup_dyn_2  = np.clip(t_rup_dyn_2,  0, 300)
t_rup_dyn_15 = np.clip(t_rup_dyn_15, 0, 300)
annee_rup_dyn_2  = annees + t_rup_dyn_2
annee_rup_dyn_15 = annees + t_rup_dyn_15
ax3.plot(annees, annee_rup_dyn_2,  color="#e74c3c", lw=1.5, label="+2°C préind.")
ax3.plot(annees, annee_rup_dyn_15, color="#e67e22", lw=1.5, label="+1.5°C préind.")
ax3.axhline(2100, color="gray", lw=0.8, linestyle=":", alpha=0.5, label="2100")
ax3.set_title("t_rupture dynamique (Kalman)", color="white", fontsize=10)
ax3.set_ylabel("Année de rupture estimée", color="white")
ax3.set_xlabel("Année courante", color="white")
ax3.legend(fontsize=8, framealpha=0.3)
ax3.grid(alpha=0.15)
valides = annee_rup_dyn_2[~np.isnan(annee_rup_dyn_2)]
ax3.set_ylim(annees[-1], min(valides.max() + 20, 2200) if len(valides) else 2200)

# ── Panneau 4 : Simulation correcteur PI ──
ax4 = fig.add_subplot(gs[2, :])
annees_sim = annees[-1] + t_sim
ax4.plot(annees, y_reel, color="white", lw=0.8, alpha=0.5, label="Données historiques")
ax4.plot(annees, y_kalman, color="#2ecc71", lw=1, alpha=0.7, label="Kalman v1.1")
ax4.plot(annees_sim, y_sim, color="#9b59b6", lw=2, label=f"PI régulé (Kp={Kp}, Ki={Ki:.3f})")
ax4.axhline(Y_consigne, color="#9b59b6", lw=1, linestyle=":",
            label=f"Consigne +1.5°C préind. ({Y_consigne:.2f}°C NASA)")
ax4.axhline(Y_max_paris2, color="#e74c3c", lw=1, linestyle=":",
            label=f"Seuil +2°C préind. ({Y_max_paris2:.2f}°C NASA)")
ax4.fill_between(annees_sim, Y_consigne * 0.95, Y_consigne * 1.05,
                 alpha=0.1, color="#9b59b6", label="Bande ±5%")
t_stable_annee = annees[-1] + t_stable_theorique
ax4.axvline(t_stable_annee, color="#f39c12", lw=1, linestyle="--",
            label=f"t_stable théorique ≈ {t_stable_annee:.0f}")
ax4.set_title(f"Simulation régulation PI — Consigne {Y_consigne}°C (Accord de Paris)",
              color="white", fontsize=10)
ax4.set_ylabel("Anomalie (°C)", color="white")
ax4.set_xlabel("Année", color="white")
ax4.legend(fontsize=8, loc="upper right", framealpha=0.3)
ax4.set_xlim(annees[0], annees_sim[-1])
ax4.grid(alpha=0.15)

plt.savefig("simulation_reta.png", dpi=150, bbox_inches="tight",
            facecolor="#0d1117", edgecolor="none")
print("\nFigure sauvegardée : simulation_reta.png")
plt.show()

# ─────────────────────────────────────────────
# 7. RÉCAPITULATIF NUMÉRIQUE
# ─────────────────────────────────────────────
print("\n" + "="*50)
print("RÉCAPITULATIF RETA")
print("="*50)
print(f"Données    : NASA GISS {annees[0]}–{annees[-1]}")
print(f"ε estimé   : {epsilon:.4f} °C/an")
print(f"L (asympt) : {L:.4f} °C (sans perturbation)")
print(f"Y +1.5°C   : {Y_max_paris1p5:.2f}°C (NASA) → rupture ≈ {annee_rup_15:.0f}" if annee_rup_15 else "")
print(f"Y +2°C     : {Y_max_paris2:.2f}°C (NASA) → rupture ≈ {annee_rup_2:.0f}" if annee_rup_2 else "")
print(f"Y_consigne : {Y_consigne:.2f}°C (NASA) = +1.5°C préind. (Accord de Paris)")
print(f"Kp         : {Kp}   →  t_stable ≈ {t_stable_theorique:.0f} ans ({t_stable_annee:.0f})")
print(f"Ki         : {Ki:.4f} (régime critique Kp²/4)")
if annee_rup_2:
    print(f"\nCondition : t_stable ({t_stable_annee:.0f}) < t_rupture +2°C ({annee_rup_2:.0f}) → {'✓ OK' if t_stable_annee < annee_rup_2 else '✗ MAL DIMENSIONNÉ'}")
