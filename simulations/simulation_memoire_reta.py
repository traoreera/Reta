"""
Simulation RETA — Mémoire contextuelle LLM
Démontre sur une conversation de 10 tours :
  - Accumulation y_k (expansion dimensionnelle)
  - Correction PI (tour correctif)
  - Navigation vers un état passé (descente Kalman)
  - Comparaison coût O(n×k) classique vs O(n+k) RETA
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.patches as mpatches

# ── PARAMÈTRES ────────────────────────────────────────────────────────────────

np.random.seed(42)
K = 10          # nombre de tours
N = 60          # durée d'un tour (τ)
τ  = np.linspace(0, 1, N)

# ── CONVERSATION SIMULÉE ──────────────────────────────────────────────────────

# Chaque tour a un type et une perturbation z_k(τ)
tours = [
    {"type": "INIT",       "label": "Intention initiale",         "z":  0.0,  "couleur": "#8A90B0"},
    {"type": "EXPANSION",  "label": "Q1 : Qu'est-ce que RETA ?",  "z": +0.18, "couleur": "#6C63FF"},
    {"type": "EXPANSION",  "label": "R1 : Théorie de l'échappée", "z": +0.22, "couleur": "#6C63FF"},
    {"type": "EXPANSION",  "label": "Q2 : Applications LLM ?",    "z": +0.15, "couleur": "#6C63FF"},
    {"type": "CORRECTION", "label": "R2 : Correction (PI) — mauvais contexte", "z": -0.35, "couleur": "#E53E3E"},
    {"type": "EXPANSION",  "label": "Q3 : Exemple Bitcoin ?",     "z": +0.20, "couleur": "#6C63FF"},
    {"type": "EXPANSION",  "label": "R3 : Bull-run 2020-2021",    "z": +0.14, "couleur": "#6C63FF"},
    {"type": "EXPANSION",  "label": "Q4 : Dashboard temps réel ?","z": +0.25, "couleur": "#6C63FF"},
    {"type": "EXPANSION",  "label": "R4 : Flask + Chart.js",      "z": +0.19, "couleur": "#6C63FF"},
    {"type": "CORRECTION", "label": "R5 : Rappel tour 2 (PI)",    "z": -0.10, "couleur": "#E53E3E"},
]

# Perturbation de base : arctan(t) borné
y_base = np.arctan(τ * 3)   # f(t) = arctan(t), système canonique RETA

# ── CONSTRUCTION DES ÉTATS y_k ────────────────────────────────────────────────

# z_k(τ) = amplitude * (1 + 0.3*sin(k*π*τ))  — forme de perturbation persistante
def make_z(amplitude, k):
    return amplitude * (1 + 0.3 * np.sin((k+1) * np.pi * τ))

y_states = [y_base.copy()]   # y_0 = état initial
z_sigs   = []                # signatures stockées
y_k = y_base.copy()

for k, t in enumerate(tours[1:], start=1):
    z_k = make_z(t["z"], k)
    z_sigs.append({
        "k":      k,
        "eps":    t["z"],          # signature compacte = juste l'amplitude + forme
        "type":   t["type"],
    })
    y_k = y_k + np.cumsum(z_k) / N   # y_k = y_{k-1} + ∫z_k dτ
    y_states.append(y_k.copy())

# ── FILTRE DE KALMAN — reconstruction d'un état passé ─────────────────────────
# Démonstration : retrouver y_2 (après tour 2) depuis y_k actuel

def kalman_reconstruct(y_current, z_sigs, target_tour):
    """Descend de y_k à y_{target} en soustrayant les perturbations estimées."""
    y = y_current.copy()
    for sig in reversed(z_sigs):
        if sig["k"] <= target_tour:
            break
        # Kalman estime ẑ_i depuis la signature stockée (ε_i + forme)
        z_estim = make_z(sig["eps"], sig["k"])
        y = y - np.cumsum(z_estim) / N
    return y

y_reconstruit = kalman_reconstruct(y_states[-1], z_sigs, target_tour=2)
y_cible       = y_states[2]   # état réel au tour 2

erreur_kalman = np.abs(y_reconstruit - y_cible).mean()

# ── COÛT MÉMOIRE : classique vs RETA ──────────────────────────────────────────

k_vals      = np.arange(1, 51)
cout_classique = N * k_vals          # O(n × k)
cout_reta      = N + k_vals          # O(n + k)
gain           = cout_classique / cout_reta

# ── AFFICHAGE ─────────────────────────────────────────────────────────────────

BG      = "#F5F6FA"
SURFACE = "#FFFFFF"
TEXT1   = "#1A1F36"
TEXT2   = "#4A5080"
ORANGE  = "#F7931A"
PURPLE  = "#6C63FF"
GREEN   = "#00A878"
RED     = "#E53E3E"
YELLOW  = "#D69E2E"

fig = plt.figure(figsize=(18, 14), facecolor=BG)
fig.suptitle(
    "RETA — Mémoire Contextuelle LLM  |  10 tours de conversation",
    fontsize=14, fontweight="bold", color=TEXT1, y=0.98)

gs = gridspec.GridSpec(3, 2, figure=fig, hspace=0.45, wspace=0.35,
                       left=0.07, right=0.97, top=0.94, bottom=0.06)

def style(ax, title):
    ax.set_facecolor(SURFACE)
    ax.set_title(title, color=TEXT1, fontsize=10, fontweight="bold", pad=8)
    ax.tick_params(colors=TEXT2, labelsize=8)
    ax.grid(True, alpha=0.15, color="#C0C4D8")
    for spine in ax.spines.values():
        spine.set_edgecolor("#D0D4E8")
    ax.xaxis.label.set_color(TEXT2)
    ax.yaxis.label.set_color(TEXT2)

# ── Panel 1 : États y_k au fil des tours ──────────────────────────────────────
ax1 = fig.add_subplot(gs[0, :])
style(ax1, "Accumulation dimensionnelle y_k — chaque tour ajoute ∫z_k dτ")

colors_line = [t["couleur"] for t in tours]
alpha_vals  = np.linspace(0.25, 1.0, len(y_states))
for k, (y, col, alph, t) in enumerate(zip(y_states, colors_line, alpha_vals, tours)):
    lw = 2.0 if k in (0, len(y_states)-1) else 1.0
    ax1.plot(τ, y, color=col, alpha=float(alph), linewidth=lw,
             label=f"Tour {k} — {t['label']}" if k <= 5 else "")

# Annoter tour 0 et tour final
ax1.annotate("y₀ = arctan(t)\n[ℝ¹ — intention initiale]",
             xy=(τ[-1], y_states[0][-1]), xytext=(0.75, y_states[0][-1] - 0.3),
             fontsize=8, color=TEXT2,
             arrowprops=dict(arrowstyle="->", color=TEXT2, lw=0.8))
ax1.annotate(f"y_{K-1} [ℝ{K}]\nContexte complet",
             xy=(τ[-1], y_states[-1][-1]), xytext=(0.7, y_states[-1][-1] + 0.15),
             fontsize=8, color=PURPLE, fontweight="bold",
             arrowprops=dict(arrowstyle="->", color=PURPLE, lw=0.8))

# Marquer les tours correctifs
for k, t in enumerate(tours):
    if t["type"] == "CORRECTION" and k < len(y_states):
        y_val = y_states[k][N//2]
        ax1.scatter([τ[N//2]], [y_val], color=RED, s=60, zorder=5)
        ax1.annotate(f"PI ↓\n{t['label'][:20]}",
                     xy=(τ[N//2], y_val), xytext=(τ[N//2] - 0.25, y_val + 0.2),
                     fontsize=7.5, color=RED,
                     arrowprops=dict(arrowstyle="->", color=RED, lw=0.7))

ax1.set_xlabel("τ (temps normalisé sur un tour)")
ax1.set_ylabel("État sémantique y(τ)")
ax1.legend(loc="upper left", fontsize=7.5, ncol=2,
           facecolor=SURFACE, edgecolor="#D0D4E8", labelcolor=TEXT1)

# ── Panel 2 : Amplitudes des perturbations ────────────────────────────────────
ax2 = fig.add_subplot(gs[1, 0])
style(ax2, "Perturbations z_k par tour — signatures compactes stockées")

eps_vals = [t["z"] for t in tours[1:]]
bar_cols = [t["couleur"] for t in tours[1:]]
bar_labels = [f"T{k+1}" for k in range(len(tours)-1)]
bars = ax2.bar(bar_labels, eps_vals, color=bar_cols, alpha=0.85, edgecolor=SURFACE, linewidth=1.2)

ax2.axhline(0, color=TEXT2, linewidth=0.8, linestyle="--", alpha=0.5)
ax2.axhline(+0.004, color=GREEN, linewidth=1.0, linestyle=":", alpha=0.7, label="ε seuil BULL")
ax2.axhline(-0.004, color=RED,   linewidth=1.0, linestyle=":", alpha=0.7, label="ε seuil BEAR")
for bar, val in zip(bars, eps_vals):
    ax2.text(bar.get_x() + bar.get_width()/2, val + (0.01 if val >= 0 else -0.02),
             f"{val:+.2f}", ha="center", fontsize=7.5, color=TEXT1)
ax2.set_ylabel("Amplitude ε")
ax2.set_xlabel("Tour k")
legend_exp  = mpatches.Patch(color=PURPLE, alpha=0.85, label="Expansion (+z_k)")
legend_corr = mpatches.Patch(color=RED,    alpha=0.85, label="Correction PI (−u_k)")
ax2.legend(handles=[legend_exp, legend_corr], fontsize=8,
           facecolor=SURFACE, edgecolor="#D0D4E8", labelcolor=TEXT1)

# ── Panel 3 : Navigation Kalman — retrouver y_2 ────────────────────────────────
ax3 = fig.add_subplot(gs[1, 1])
style(ax3, f"Navigation Kalman — retrouver tour 2 depuis tour {K-1}")

ax3.plot(τ, y_states[2],       color=ORANGE, linewidth=2.0, label="y₂ réel (cible)")
ax3.plot(τ, y_reconstruit,     color=PURPLE, linewidth=1.8, linestyle="--",
         label=f"y₂ reconstruit Kalman\n(erreur moy = {erreur_kalman:.6f})")
ax3.plot(τ, y_states[-1],      color=TEXT2,  linewidth=1.0, alpha=0.4,
         label=f"y_{K-1} courant (état actuel)")

ax3.fill_between(τ, y_states[2], y_reconstruit, alpha=0.15, color=RED,
                 label=f"|erreur| = {erreur_kalman:.2e}")
ax3.set_xlabel("τ")
ax3.set_ylabel("État y(τ)")
ax3.legend(fontsize=7.5, facecolor=SURFACE, edgecolor="#D0D4E8", labelcolor=TEXT1)

# Annotation
ax3.annotate(f"Descente : {K-1} → 2\n= {K-3} soustractions\n(pas de relecture tokens)",
             xy=(0.5, y_reconstruit[N//2]),
             xytext=(0.1, y_reconstruit[N//2] + 0.4),
             fontsize=8, color=PURPLE, fontweight="bold",
             arrowprops=dict(arrowstyle="->", color=PURPLE, lw=0.8))

# ── Panel 4 : Coût mémoire O(n×k) vs O(n+k) ──────────────────────────────────
ax4 = fig.add_subplot(gs[2, 0])
style(ax4, "Coût mémoire — classique O(n×k) vs RETA O(n+k)")

ax4.plot(k_vals, cout_classique, color=RED,    linewidth=2.0, label="Classique : O(n×k)")
ax4.plot(k_vals, cout_reta,      color=GREEN,  linewidth=2.0, label="RETA : O(n+k)")
ax4.fill_between(k_vals, cout_reta, cout_classique, alpha=0.12, color=GREEN,
                 label="Gain RETA")
ax4.set_xlabel("Nombre de tours k")
ax4.set_ylabel("Tokens stockés (n=60)")
ax4.legend(fontsize=8, facecolor=SURFACE, edgecolor="#D0D4E8", labelcolor=TEXT1)
ax4.set_ylim(0)

# ── Panel 5 : Gain multiplicatif ──────────────────────────────────────────────
ax5 = fig.add_subplot(gs[2, 1])
style(ax5, "Gain RETA multiplicatif = n×k / (n+k)")

ax5.plot(k_vals, gain, color=PURPLE, linewidth=2.2)
ax5.fill_between(k_vals, 1, gain, alpha=0.15, color=PURPLE)
ax5.axhline(1, color=TEXT2, linewidth=0.8, linestyle="--", alpha=0.5)

# Annoter quelques valeurs clés
for k_mark in [10, 25, 50]:
    g = N * k_mark / (N + k_mark)
    ax5.annotate(f"k={k_mark}\n×{g:.1f}",
                 xy=(k_mark, g), xytext=(k_mark + 1, g - 2),
                 fontsize=8, color=PURPLE,
                 arrowprops=dict(arrowstyle="->", color=PURPLE, lw=0.7))

ax5.set_xlabel("Nombre de tours k")
ax5.set_ylabel("Gain multiplicatif (×)")
ax5.set_ylim(0)

# ── RÉSUMÉ CONSOLE ────────────────────────────────────────────────────────────

print("\n" + "="*65)
print("  RETA — MÉMOIRE CONTEXTUELLE LLM : RÉSULTATS")
print("="*65)
print(f"\n{'Tour':<6} {'Type':<12} {'ε_k':>8}  {'y_k(1)':.>12}  Coût classique")
print("-"*60)
cout_cumul = 0
for k, (t, y) in enumerate(zip(tours, y_states)):
    cout_cumul += N
    print(f"  {k:<4} {t['type']:<12} {t['z']:>+7.2f}  {y[-1]:>+10.4f}  "
          f"{N}×{k} = {N*k:>4} tokens")

print(f"\n  Coût classique total (k=10) : {N*K} tokens")
print(f"  Coût RETA total    (k=10) : {N} (état) + {K-1} (signatures) = {N+K-1} tokens")
print(f"  Gain                       : ×{N*K/(N+K-1):.1f}")
print(f"\n  Navigation Kalman tour {K-1} → tour 2 :")
print(f"    Erreur de reconstruction : {erreur_kalman:.2e}  (≈ 0 : reconstruction exacte)")
print(f"    Coût : {K-3} soustractions (vs relire {N*(K-2)} tokens)")
print()

out = "simulations/simulation_memoire_reta.png"
plt.savefig(out, dpi=150, bbox_inches="tight", facecolor=BG)
print(f"  Graphique → {out}")
plt.show()
