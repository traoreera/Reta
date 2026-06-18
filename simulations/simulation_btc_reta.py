"""
Simulation RETA — Marché BTC 2017-2022
Données réelles Yahoo Finance (même source que yfinance).

Modélisation RETA :
  - log-rendement journalier z(t) = perturbation persistante
  - Kalman 1D estime la dérive z(t) et sa vitesse ż(t)
  - Détection automatique des bull-runs : z̄(T) ≥ ε (condition affaiblie)
  - t_rupture RETA ≥ (Y_max − y₀) / ε̄  par cycle
  - Régulateur PI sur la tendance longue terme
"""

import requests
import datetime
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# ── 1. DONNÉES RÉELLES BTC via Yahoo Finance ───────────────────────────────────

def fetch_btc(start: str, end: str) -> tuple[np.ndarray, np.ndarray]:
    """Retourne (timestamps_datetime, closes_usd)."""
    t0 = int(datetime.datetime.strptime(start, "%Y-%m-%d").timestamp())
    t1 = int(datetime.datetime.strptime(end,   "%Y-%m-%d").timestamp())
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/BTC-USD"
           f"?interval=1d&period1={t0}&period2={t1}")
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
    r.raise_for_status()
    result = r.json()["chart"]["result"][0]
    ts  = [datetime.datetime.fromtimestamp(t).date() for t in result["timestamp"]]
    raw = result["indicators"]["quote"][0]["close"]
    # Nettoyer les None (jours fériés / données manquantes)
    closes, dates_clean = [], []
    for d, c in zip(ts, raw):
        if c is not None:
            closes.append(c)
            dates_clean.append(d)
    return np.array(dates_clean), np.array(closes, dtype=float)

print("Téléchargement données BTC 2017-2022...")
dates, prix = fetch_btc("2017-01-01", "2022-12-31")
n = len(prix)
print(f"  {n} jours  |  min=${prix.min():.0f}  max=${prix.max():.0f}")
print(f"  Premier : {dates[0]}  ${prix[0]:.0f}")
print(f"  Dernier : {dates[-1]}  ${prix[-1]:.0f}")

date_nums = mdates.date2num(dates)
t_all     = np.arange(n, dtype=float)

# ── 2. PERTURBATION RETA : log-rendements ─────────────────────────────────────

log_prix    = np.log(prix)
log_returns = np.diff(log_prix, prepend=log_prix[0])   # z(t)

# ── 3. FILTRE DE KALMAN 1D ────────────────────────────────────────────────────
# État [z, ż] — dérive et tendance de la dérive

def kalman_1d(obs: np.ndarray, Q: float = 2e-5, R_mes: float = 5e-4):
    A     = np.array([[1.0, 1.0], [0.0, 1.0]])
    H     = np.array([[1.0, 0.0]])
    Q_mat = np.diag([Q, Q * 0.1])
    R_mat = np.array([[R_mes]])
    x = np.array([obs[0], 0.0])
    P = np.eye(2) * 2.0
    z_est = np.zeros(len(obs))
    p_var = np.zeros(len(obs))
    for k, o in enumerate(obs):
        x = A @ x
        P = A @ P @ A.T + Q_mat
        S = float((H @ P @ H.T + R_mat)[0, 0])
        K = (P @ H.T).flatten() / S
        x = x + K * (o - float((H @ x)[0]))
        P = (np.eye(2) - np.outer(K, H)) @ P
        z_est[k] = x[0]
        p_var[k] = P[0, 0]
    return z_est, p_var

z_kalman, p_var = kalman_1d(log_returns)
P_inf = float(p_var[-300:].mean())

# ── 4. DÉTECTION BULL / BEAR ──────────────────────────────────────────────────

FENETRE   = 60
EPS_BULL  = +0.004
EPS_BEAR  = -0.004
T_CONFIRM = 15

z_moy = np.convolve(z_kalman, np.ones(FENETRE) / FENETRE, mode="same")

phases, compteur, etat = np.zeros(n), 0, 0
for i in range(n):
    if z_moy[i] > EPS_BULL:
        compteur = compteur + 1 if etat != 1 else 0
        if compteur >= T_CONFIRM:
            etat, compteur = 1, 0
    elif z_moy[i] < EPS_BEAR:
        compteur = compteur + 1 if etat != -1 else 0
        if compteur >= T_CONFIRM:
            etat, compteur = -1, 0
    else:
        compteur = 0
    phases[i] = etat

# ── 5. ANALYSE t_rupture PAR BULL-RUN ────────────────────────────────────────

bull_runs = []
i = 0
while i < n:
    if phases[i] == 1:
        debut = i
        while i < n and phases[i] == 1:
            i += 1
        fin = i
        eps_local = max(z_moy[debut:fin].mean(), 1e-6)
        y0        = log_prix[debut]
        ymax_idx  = debut + np.argmax(log_prix[debut:fin])
        ymax      = log_prix[ymax_idx]
        t_rup     = (ymax - y0) / eps_local
        t_reel    = fin - debut
        bull_runs.append(dict(debut=debut, fin=fin,
                               t_rup=t_rup, t_reel=t_reel, eps=eps_local,
                               prix_debut=prix[debut], prix_max=prix[ymax_idx],
                               date_debut=dates[debut], date_fin=dates[min(fin,n-1)],
                               date_max=dates[ymax_idx]))
    else:
        i += 1

print(f"\nP∞ Kalman : {P_inf:.6f}")
print(f"\n{'Bull-run':<10} {'Début':<12} {'Pic':<12} {'Fin':<12} "
      f"{'Durée':>7} {'t_rup RETA':>11} {'ε̄':>9} {'Prix pic':>10}")
print("-" * 80)
for idx, b in enumerate(bull_runs):
    print(f"  #{idx+1:<7} {str(b['date_debut']):<12} {str(b['date_max']):<12} "
          f"{str(b['date_fin']):<12} {b['t_reel']:>5}j  "
          f"≥{b['t_rup']:>7.0f}j  {b['eps']:>9.5f}  ${b['prix_max']:>9,.0f}")

# ── 6. RÉGULATEUR PI ─────────────────────────────────────────────────────────

coeffs   = np.polyfit(t_all, log_prix, 1)
tendance = np.polyval(coeffs, t_all)

kp, ki, dt = 0.12, 0.002, 1.0
ie_pi = 0.0
u_pi  = np.zeros(n)
e_pi  = np.zeros(n)
for i in range(n):
    e = log_prix[i] - tendance[i]
    ie_pi = np.clip(ie_pi + e * dt, -8.0, 8.0)
    u_pi[i] = kp * e + ki * ie_pi
    e_pi[i] = e

# ── 7. TRACÉ ──────────────────────────────────────────────────────────────────

BG      = "#0d0d1a"
ORANGE  = "#F7931A"
CYAN    = "#00d4ff"
YELLOW  = "#ffcc00"
WHITE   = "#e8e8e8"

fig, axes = plt.subplots(4, 1, figsize=(16, 19), sharex=True)
fig.patch.set_facecolor(BG)
fig.suptitle(
    "RETA — Marché BTC 2017–2022  |  Données réelles Yahoo Finance\n"
    "log-rendement z(t) comme perturbation persistante  ·  Kalman + PI + détection de rupture",
    fontsize=13, fontweight="bold", color=WHITE, y=0.99)

fmt_year  = mdates.YearLocator()
fmt_month = mdates.MonthLocator(bymonth=[1, 4, 7, 10])
fmt_label = mdates.DateFormatter("%Y")

COULEURS_BULL = ["#00ff88", "#00aaff", "#ffaa00", "#ff44ff", "#ff8844"]

def style_ax(ax, title):
    ax.set_facecolor("#12122a")
    ax.set_title(title, color=WHITE, fontsize=10, pad=6)
    ax.tick_params(colors=WHITE, labelsize=8)
    ax.yaxis.label.set_color(WHITE)
    ax.grid(True, alpha=0.15, color="#555")
    for spine in ax.spines.values():
        spine.set_edgecolor("#333")
    ax.xaxis.set_major_locator(fmt_year)
    ax.xaxis.set_minor_locator(fmt_month)
    ax.xaxis.set_major_formatter(fmt_label)

# Panel 1 — Prix BTC + phases + tendance
ax1 = axes[0]
ax1.set_yscale("log")
for i in range(n - 1):
    if phases[i] == 1:
        ax1.axvspan(date_nums[i], date_nums[i+1], alpha=0.13, color="lime",    linewidth=0)
    elif phases[i] == -1:
        ax1.axvspan(date_nums[i], date_nums[i+1], alpha=0.13, color="#ff3030", linewidth=0)

ax1.plot(date_nums, prix,          color=ORANGE, linewidth=1.3, label="Prix BTC (USD)")
ax1.plot(date_nums, np.exp(tendance), color=WHITE, linewidth=1.5,
         linestyle="--", alpha=0.55, label="Tendance RETA (régression log)")

# Annoter chaque bull-run
for idx, b in enumerate(bull_runs):
    c = COULEURS_BULL[idx % len(COULEURS_BULL)]
    mid_idx = (b["debut"] + b["fin"]) // 2
    ax1.annotate(
        f"Bull #{idx+1}\n${b['prix_max']:,.0f}\nt_rup≥{b['t_rup']:.0f}j",
        xy=(date_nums[b["debut"] + (b["fin"]-b["debut"])//4], b["prix_debut"]),
        xytext=(date_nums[mid_idx], b["prix_max"] * 1.8),
        fontsize=7.5, color=c, ha="center",
        arrowprops=dict(arrowstyle="->", color=c, lw=0.8),
        bbox=dict(boxstyle="round,pad=0.25", facecolor=BG, alpha=0.8, edgecolor=c)
    )

ax1.set_ylabel("Prix USD (échelle log)")
ax1.set_ylim(500, 500_000)
ax1.legend(loc="upper left", fontsize=8, facecolor=BG, labelcolor=WHITE)
style_ax(ax1, "Prix BTC — Phases Bull (vert) / Bear (rouge) détectées par RETA  |  Condition : z̄(T) ≥ ε")

# Panel 2 — Perturbation z(t)
ax2 = axes[1]
ax2.plot(date_nums, log_returns, color="#666", linewidth=0.4, alpha=0.7, label="z(t) brut")
ax2.plot(date_nums, z_kalman,   color=CYAN,   linewidth=1.0, label=f"ẑ(t) Kalman  (P∞={P_inf:.5f})")
ax2.plot(date_nums, z_moy,      color="#ff6b35", linewidth=1.8, label=f"z̄(t) moyenne {FENETRE}j")
ax2.axhline( EPS_BULL, color="lime",    linewidth=1.2, linestyle="--", alpha=0.8, label=f"ε_bull = +{EPS_BULL}")
ax2.axhline( EPS_BEAR, color="#ff3030", linewidth=1.2, linestyle="--", alpha=0.8, label=f"ε_bear = {EPS_BEAR}")
ax2.axhline(0, color=WHITE, linewidth=0.5, linestyle=":", alpha=0.35)
ax2.set_ylabel("Log-rendement z(t)")
ax2.set_ylim(-0.45, 0.45)
ax2.legend(loc="upper right", fontsize=7.5, facecolor=BG, labelcolor=WHITE, ncol=2)
style_ax(ax2, "Perturbation z(t) — estimation Kalman et zones de rupture RETA")

# Panel 3 — Erreur PI
ax3 = axes[2]
ax3.fill_between(date_nums, e_pi, 0, where=e_pi > 0,
                 alpha=0.45, color="#ff4444", label="Au-dessus tendance (surachat)")
ax3.fill_between(date_nums, e_pi, 0, where=e_pi < 0,
                 alpha=0.45, color="#4488ff", label="En-dessous tendance (survente)")
ax3.plot(date_nums, e_pi, color=WHITE,  linewidth=0.6, alpha=0.5)
ax3.plot(date_nums, u_pi, color=YELLOW, linewidth=1.3, label=f"Signal PI u(t)  (Kp={kp}, Ki={ki})")
ax3.axhline(0, color=WHITE, linewidth=0.5, linestyle=":", alpha=0.35)
ax3.set_ylabel("Écart à la tendance (log)")
ax3.legend(loc="upper left", fontsize=8, facecolor=BG, labelcolor=WHITE)
style_ax(ax3, f"Régulateur PI RETA — Détection surachat/survente  |  t_stable ≈ {8/kp:.0f} jours")

# Panel 4 — Temps de rupture par bull-run
ax4 = axes[3]
ax4.set_yscale("log")
ax4.plot(date_nums, prix, color=ORANGE, linewidth=1.0, alpha=0.4)

for idx, b in enumerate(bull_runs):
    c = COULEURS_BULL[idx % len(COULEURS_BULL)]
    d0, d1 = date_nums[b["debut"]], date_nums[min(b["fin"], n-1)]
    ax4.axvspan(d0, d1, alpha=0.25, color=c, linewidth=0)
    mid   = (d0 + d1) / 2
    y_pos = b["prix_debut"] * 1.3
    ax4.text(mid, y_pos,
             f"Bull #{idx+1}\n"
             f"t_reel = {b['t_reel']}j\n"
             f"t_rup RETA ≥ {b['t_rup']:.0f}j\n"
             f"ε̄ = {b['eps']:.5f}",
             fontsize=7.5, color=c, ha="center", va="bottom",
             bbox=dict(boxstyle="round,pad=0.3", facecolor=BG, alpha=0.75, edgecolor=c))

ax4.set_ylabel("Prix USD (échelle log)")
ax4.set_ylim(500, 500_000)
style_ax(ax4, "Temps de rupture RETA par bull-run : t_rupture ≥ (log P_max − log P₀) / ε̄")

plt.tight_layout(rect=[0, 0, 1, 0.98])
out = "simulations/simulation_btc_reta.png"
plt.savefig(out, dpi=150, bbox_inches="tight", facecolor=BG)
print(f"\nGraphique sauvegardé → {out}")
plt.show()
