"""
RETA — Fusion de Référentiels : BTC (données brutes) ⊕ ZIP (signature compressée)
Doc source : docs/RETA_fusion_referentiels.md

Pipeline :
  RETA(données_brutes) ──┐
                          ├──⊕(α)──→ référentiel fusionné ──→ DB simulée ──→ LLM/capteur
  RETA(zip/résumé 24h) ──┘

Démontre :
  1. Construction des deux référentiels A et B via Kalman
  2. Fusion paramétrée α ∈ [0, 1]
  3. Ligne de possibilités (famille continue de référentiels)
  4. Divergence systématique Δ_AB(t) — prédictible, pas du bruit
  5. Stockage DB simulé : 4 scalaires au lieu de 300 points
  6. Navigation O(1) entre référentiels via Δz
"""

import requests, datetime, json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

# ── 1. DONNÉES BTC VIA BINANCE ────────────────────────────────────────────────

def fetch_klines(interval="1h", limit=300):
    url = (f"https://api.binance.com/api/v3/klines"
           f"?symbol=BTCUSDT&interval={interval}&limit={limit}")
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    times, closes = [], []
    for k in r.json():
        times.append(datetime.datetime.fromtimestamp(k[0]/1000))
        closes.append(float(k[4]))
    return np.array(times), np.array(closes)

print("Téléchargement BTC (Binance 1h × 300)...")
times, prix = fetch_klines()
n = len(prix)
print(f"  {n} barres  |  ${prix.min():.0f} → ${prix.max():.0f}")

log_prix = np.log(prix)
log_ret  = np.diff(log_prix, prepend=log_prix[0])

# ── 2. KALMAN 1D ──────────────────────────────────────────────────────────────

def kalman_1d(obs, Q=2e-5, R_mes=5e-4):
    A = np.array([[1.,1.],[0.,1.]]); H = np.array([[1.,0.]])
    Qm = np.diag([Q, Q*.1]); Rm = np.array([[R_mes]])
    x = np.array([obs[0], 0.]); P = np.eye(2)*2.
    z_est = np.zeros(len(obs)); p_var = np.zeros(len(obs))
    for k, o in enumerate(obs):
        x = A@x; P = A@P@A.T + Qm
        S = float((H@P@H.T + Rm)[0,0])
        K = (P@H.T).flatten()/S
        x = x + K*(o - float((H@x)[0]))
        P = (np.eye(2) - np.outer(K,H))@P
        z_est[k] = x[0]; p_var[k] = P[0,0]
    return z_est, p_var

def roll_mean(x, w):
    return np.array([x[max(0,i-w+1):i+1].mean() for i in range(len(x))])

# ── RÉFÉRENTIEL A : données brutes horaires ────────────────────────────────────
z_A, p_A = kalman_1d(log_ret)
eps_A     = float(np.abs(z_A).mean())
z_A_moy   = roll_mean(z_A, 24)

# ── RÉFÉRENTIEL B : zip = résumé 24h sous-échantillonné ──────────────────────
STRIDE  = 24
idx_zip = np.arange(0, n, STRIDE)
z_zip   = np.array([log_ret[i:i+STRIDE].mean() for i in idx_zip])

# Ré-interpoler B sur la grille horaire pour la fusion
z_B_raw = np.interp(np.arange(n), idx_zip, z_zip)
z_B, _  = kalman_1d(z_B_raw)
z_B_moy = roll_mean(z_B, 24)
eps_B   = float(np.abs(z_B).mean())

print(f"\nRéférentiel A (brut 1h)  : ε_A = {eps_A:.6f}  |  {n} points")
print(f"Référentiel B (zip 24h)  : ε_B = {eps_B:.6f}  |  {len(z_zip)} points → interpolé {n}")

# ── 3. FUSION PARAMÉTRÉE ──────────────────────────────────────────────────────

ALPHAS = [0.0, 0.25, 0.50, 0.75, 1.0]

def build_fusion(alpha, za=z_A_moy, zb=z_B_moy):
    z_f = alpha * za + (1 - alpha) * zb
    log_f = np.zeros(n); log_f[0] = log_prix[0]
    for i in range(1, n):
        log_f[i] = log_f[i-1] + z_f[i]
    eps_f = alpha * eps_A + (1 - alpha) * eps_B
    return z_f, np.exp(log_f), eps_f

fusions = {a: build_fusion(a) for a in ALPHAS}

# Ligne de possibilités continue (100 α)
alphas_cont = np.linspace(0, 1, 100)
eps_ligne   = [a * eps_A + (1-a) * eps_B for a in alphas_cont]
trup_ligne  = [0.20 / max(e, 1e-8) for e in eps_ligne]

# ── 4. DIVERGENCE SYSTÉMATIQUE Δ_AB(t) ───────────────────────────────────────
delta_z   = z_B_moy - z_A_moy
delta_acc = np.cumsum(delta_z)

eps_delta   = abs(eps_B - eps_A)
t_rup_delta = abs(delta_acc[-1]) / eps_delta if eps_delta > 1e-8 else float("inf")

print(f"\nDivergence Δ_AB finale : {delta_acc[-1]:.6f}")
print(f"ε_Δ = |ε_B − ε_A|      : {eps_delta:.6f}")
print(f"t_rup divergence        : {t_rup_delta:.1f} barres")

# ── 5. NAVIGATION O(1) : A → B via Δz ────────────────────────────────────────
log_A = np.zeros(n); log_A[0] = log_prix[0]
for i in range(1, n): log_A[i] = log_A[i-1] + z_A_moy[i]

log_B_nav    = log_A + delta_acc        # O(1)
log_B_direct = np.zeros(n); log_B_direct[0] = log_prix[0]
for i in range(1, n): log_B_direct[i] = log_B_direct[i-1] + z_B_moy[i]

err_nav = np.abs(log_B_nav - log_B_direct).max()
print(f"\nNavigation O(1) A→B : erreur max = {err_nav:.2e}  ✅")

# ── 6. STOCKAGE DB SIMULÉ ─────────────────────────────────────────────────────
def db_encode(z_moy, eps, alpha, label):
    return {
        "label":    label,
        "alpha":    round(alpha, 3),
        "eps":      round(eps, 8),
        "z_last":   round(float(z_moy[-1]), 8),
        "t_rup_h":  round(0.20 / max(eps, 1e-8), 1),
        "stocke":   "4 scalaires",
        "ratio_x":  round(n / 4, 0),
    }

db = [
    db_encode(z_A_moy, eps_A, 1.0, "REF_A_brut"),
    db_encode(z_B_moy, eps_B, 0.0, "REF_B_zip"),
    db_encode(build_fusion(0.5)[0], eps_A*0.5+eps_B*0.5, 0.5, "REF_FUSION_α0.5"),
]

print("\n── Stockage DB simulé ──────────────────────────────────────────────────")
print(f"{'Label':<22} {'α':>5} {'ε':>10} {'z_last':>10} {'t_rup':>8} {'ratio':>8}")
print("-" * 70)
for row in db:
    print(f"{row['label']:<22} {row['alpha']:>5.2f} {row['eps']:>10.6f} "
          f"{row['z_last']:>10.6f} {row['t_rup_h']:>8.1f}h  {row['ratio_x']:>5.0f}×")

# ── 7. TRACÉ ──────────────────────────────────────────────────────────────────

BG      = "#F5F6FA"
SURFACE = "#FFFFFF"
ORANGE  = "#F7931A"
RETA_C  = "#6C63FF"
GREEN   = "#00A878"
RED     = "#E53E3E"
GRAY    = "#8A90B0"
TEXT    = "#1A1F36"

ALPHA_COLORS = {0.0: "#E53E3E", 0.25: "#D69E2E", 0.50: "#6C63FF",
                0.75: "#00A878", 1.0: "#2B6CB0"}

fig = plt.figure(figsize=(18, 20), facecolor=BG)
gs  = gridspec.GridSpec(4, 2, figure=fig, hspace=0.45, wspace=0.32,
                        left=0.07, right=0.97, top=0.94, bottom=0.05)

t_ax = np.arange(n)

def style(ax, title):
    ax.set_facecolor(SURFACE)
    ax.set_title(title, color=TEXT, fontsize=9.2, fontweight="600", pad=7)
    ax.tick_params(colors=GRAY, labelsize=8)
    ax.grid(True, alpha=0.22, color=GRAY, linewidth=0.5)
    for sp in ax.spines.values():
        sp.set_edgecolor("#D0D4E8"); sp.set_linewidth(0.7)

fig.suptitle(
    "RETA — Fusion de Référentiels  ·  RETA(données brutes) ⊕ RETA(zip 24h)\n"
    "y_fusion(α) = α·y_A + (1−α)·y_B    |    Navigation O(1) via Δz    |    DB : 4 scalaires / référentiel",
    fontsize=12, fontweight="bold", color=TEXT, y=0.97)

# Panel 1 — Prix réel + ligne de possibilités (5 fusions)
ax1 = fig.add_subplot(gs[0, :])
ax1.plot(t_ax, prix, color=ORANGE, lw=2, label="Prix réel BTC", zorder=5)
for alpha, (z_f, prix_f, eps_f) in fusions.items():
    lbl = f"α={alpha:.2f}  ε={eps_f:.5f}"
    ax1.plot(t_ax, prix_f, color=ALPHA_COLORS[alpha], lw=1.3,
             linestyle="--" if alpha not in (0.0, 1.0) else "-",
             alpha=0.85, label=lbl)
ax1.set_ylabel("Prix USD", color=TEXT, fontsize=8)
ax1.legend(loc="upper left", fontsize=7.5, ncol=3,
           facecolor=SURFACE, edgecolor="#D0D4E8", labelcolor=TEXT)
style(ax1, "Ligne de possibilités — α=0 (zip pur, rouge) → α=1 (brut pur, bleu foncé)")

# Panel 2 — z_A vs z_B
ax2 = fig.add_subplot(gs[1, 0])
ax2.plot(t_ax, z_A_moy, color=ORANGE, lw=1.3, label="z̄_A (brut 1h)")
ax2.plot(t_ax, z_B_moy, color=RED,    lw=1.3, label="z̄_B (zip 24h)")
ax2.axhline(0, color=GRAY, lw=0.5, ls=":")
ax2.set_ylabel("z̄(t)", color=TEXT, fontsize=8)
ax2.legend(fontsize=8, facecolor=SURFACE, edgecolor="#D0D4E8", labelcolor=TEXT)
style(ax2, "Perturbations z̄_A et z̄_B — les deux référentiels source")

# Panel 3 — Divergence systématique
ax3 = fig.add_subplot(gs[1, 1])
ax3.fill_between(t_ax, delta_acc, 0, where=delta_acc >= 0, alpha=0.3, color=GREEN)
ax3.fill_between(t_ax, delta_acc, 0, where=delta_acc <  0, alpha=0.3, color=RED)
ax3.plot(t_ax, delta_acc, color=RETA_C, lw=1.8, label="Δ_AB(t) = ∫(z_B−z_A)dτ")
ax3.axhline(0, color=GRAY, lw=0.5, ls=":")
ax3.set_ylabel("Divergence accumulée", color=TEXT, fontsize=8)
ax3.legend(fontsize=8, facecolor=SURFACE, edgecolor="#D0D4E8", labelcolor=TEXT)
style(ax3, f"Divergence systématique (prédictible)  |  t_rup_Δ ≈ {t_rup_delta:.0f} barres")

# Panel 4 — Ligne de possibilités ε / t_rup vs α
ax4a = fig.add_subplot(gs[2, 0])
ax4b = ax4a.twinx()
ax4a.plot(alphas_cont, eps_ligne,  color=ORANGE, lw=2, label="ε_fusion(α)")
ax4b.plot(alphas_cont, trup_ligne, color=RETA_C, lw=2, ls="--", label="t_rup(α)")
# points clés
for a in ALPHAS:
    ef = a*eps_A + (1-a)*eps_B
    ax4a.scatter([a], [ef], color=ALPHA_COLORS[a], s=50, zorder=5)
ax4a.set_xlabel("α  (0 = zip pur, 1 = brut pur)", color=TEXT, fontsize=8)
ax4a.set_ylabel("ε_fusion", color=ORANGE, fontsize=8)
ax4b.set_ylabel("t_rup (barres)", color=RETA_C, fontsize=8)
ax4a.tick_params(axis='y', colors=ORANGE)
ax4b.tick_params(axis='y', colors=RETA_C)
l1,lb1 = ax4a.get_legend_handles_labels()
l2,lb2 = ax4b.get_legend_handles_labels()
ax4a.legend(l1+l2, lb1+lb2, fontsize=8, facecolor=SURFACE,
            edgecolor="#D0D4E8", labelcolor=TEXT)
style(ax4a, "Ligne de possibilités continue — ε et t_rup en fonction de α")

# Panel 5 — Navigation O(1) A→B
ax5 = fig.add_subplot(gs[2, 1])
ax5.plot(t_ax, np.exp(log_B_direct), color=RED,    lw=1.8,
         label="y_B direct (Kalman complet)")
ax5.plot(t_ax, np.exp(log_B_nav),    color=GREEN,  lw=1.2,
         ls="--", label=f"y_B via Δz O(1)  |  err_max={err_nav:.1e}")
ax5.set_ylabel("Prix USD", color=TEXT, fontsize=8)
ax5.legend(fontsize=8, facecolor=SURFACE, edgecolor="#D0D4E8", labelcolor=TEXT)
style(ax5, "Navigation O(1) : y_B = y_A + ∫Δz dτ  (vs recalcul Kalman complet)")

# Panel 6 — Ratio compression DB
ax6 = fig.add_subplot(gs[3, :])
labels6  = [r["label"] for r in db]
ratios6  = [r["ratio_x"] for r in db]
colors6  = [ALPHA_COLORS[r["alpha"]] for r in db]
bars6    = ax6.barh(labels6, ratios6, color=colors6, alpha=0.82, height=0.45)
for bar, row in zip(bars6, db):
    x = bar.get_width()
    ax6.text(x + 1.5, bar.get_y() + bar.get_height()/2,
             f"4 scalaires (ε, z_last, t_rup, α)  vs  {n} floats bruts  →  {x:.0f}× compression\n"
             f"LLM reçoit : ε={row['eps']:.6f}  z_last={row['z_last']:.6f}  t_rup={row['t_rup_h']:.1f}h",
             va="center", color=TEXT, fontsize=8)
ax6.set_xlabel("Ratio de compression (n_points / 4 scalaires)", color=TEXT, fontsize=8)
ax6.set_xlim(0, max(ratios6) * 1.55)
style(ax6, "Stockage DB — ce qu'un LLM ou capteur reçoit : 4 scalaires par référentiel")

out = "simulations/simulation_fusion_reta.png"
plt.savefig(out, dpi=150, bbox_inches="tight", facecolor=BG)
print(f"\nGraphique → {out}")
plt.show()

# ── Résumé JSON (ce qui va en DB / vers le LLM) ───────────────────────────────
print("\n── Payload DB → LLM ────────────────────────────────────────────────────")
print(json.dumps(db, indent=2))
print(f"\n{n} points bruts → 4 scalaires  →  {n//4}× compression par référentiel")
print(f"Navigation A→B O(1) — erreur numérique : {err_nav:.2e}")
