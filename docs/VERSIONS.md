# RETA — Résumé comparatif des versions

> **RETA** (Référentiel d'Estimation des Temps d'Accumulation) est un framework de détection et prévention de rupture pour systèmes dynamiques perturbés.

---

## Tableau comparatif

| Critère | v1.1 | v1.2 | v1.3 | v1.4 |
|---|---|---|---|---|
| **Kalman** | Q, R fixes | Q, R fixes | **Q adaptatif** (innovations GPS) | idem v1.3 |
| **PI** | Kp, Ki fixes | **Kp, Ki adaptatifs** (gradient) | Kp, Ki adaptatifs | idem v1.3 |
| **Preuve stabilité** | Routh-Hurwitz + Lyapunov | Lyapunov gradient | Lyapunov augmenté | idem v1.3 |
| **Erreur statique** | Permanente si Ki=0 | Éliminée | Éliminée | Éliminée |
| **Biais gyro estimé** | 0.6% à t=120s | 0.6% (Kalman fixe) | **91-103%** à t=120s | idem v1.3 |
| **Survie après panne GPS** | t ≈ 56s ⚠️ | t ≈ 56s ⚠️ | t ≈ 266-276s ✓ | idem v1.3 |
| **Bound t_rup conservatif** | Oui | Oui | **NON ⚠️** (z croît post-panne) | **OUI ✓** (ḃ_true tracké) |
| **Erreur bound post-panne** | — | — | +518s OPTIMISTE | **−99s CONSERVATIF** |
| **Complexité** | O(n²) | O(n²) + PI | O(n²) + Q + PI | O(n²) + Q + PI + Kalman 2D |
| **Usage type** | Calibrage connu | Perturbation variable | Biais variable + GPS outage | Idem + prédiction t_rup fiable |

---

## Architecture par version

```
v1.1 ─────────────────────────────────────────────────────────────
  obs → [Kalman Q,R fixes] → ẑ(t) → [PI Kp,Ki fixes] → u(t)

v1.2 ─────────────────────────────────────────────────────────────
  obs → [Kalman Q,R fixes] → ẑ(t) → [PI Kp↑,Ki↑] → u(t)
                                           ↑
                                    γp·ē², γi·ē·∫ē

v1.3 ─────────────────────────────────────────────────────────────
  obs → [Kalman Q↑ innovations] → ẑ(t) → [PI Kp↑,Ki↑] → u(t)
             ↑                                  ↑
      |ν|/T_GPS → Q_biais               γp·ē², γi·ē·∫ē

v1.4 ─────────────────────────────────────────────────────────────
  obs → [Kalman Q↑ innovations] → ẑ(t) → [PI Kp↑,Ki↑] → u(t)
             ↑                                  ↑
      |ν|/T_GPS → Q_biais               γp·ē², γi·ē·∫ē
      ↓ (à chaque GPS)
  [Kalman 2D : b_true, ḃ_true] → ḃ_est → bound quadratique t_rup
```

---

## Scénario de différenciation

### v1.1 vs sans PI (référence)
- z(t) croissant modéré, Y_max = 8
- Sans PI : rupture à t = 15.49s
- Avec PI v1.1 : JAMAIS ✓
- → **v1.1 justifie le correcteur PI**

### v1.1 vs v1.2 (saut de perturbation)
- Saut z : 0.25 → 2.8 à t=10s, Y_max = 5
- v1.1 (P pur Ki=0) : y_ss = 7.0 > 5 → rupture t=12.84s ⚠️
- v1.2 (PI adaptatif) : Ki acquiert 0→0.8, y→0 → JAMAIS ✓
- → **v1.2 justifie l'adaptation des gains**

### v1.1 vs v1.3 (panne GPS, biais thermique)
- GPS coupé à t=120s, biais croît B0 × 4
- v1.1 : b_est ≈ 0% → rupture Roll à t=56s après panne
- v1.3 : b_est ≈ 91% → rupture Roll à t=266s (+210s)
- → **v1.3 justifie l'adaptation Kalman**

### v1.3 vs v1.4 (précision du bound)
- Même scénario drone, même survie
- v1.3 : bound = 791s, rupture réelle = 273s → **+518s OPTIMISTE** ⚠️
- v1.4 : bound = 174s, rupture réelle = 273s → **−99s CONSERVATIF** ✓
- → **v1.4 justifie le tracking de ḃ_true**

---

## Progression des preuves de stabilité

### v1.1 — Lyapunov classique
$$V_{11} = \frac{1}{2}e^2 + \frac{K_i}{2}I^2, \quad \dot{V}_{11} = -K_p e^2 + eF(t)$$

### v1.2 — Lyapunov avec adaptation
$$V_{12} = V_{11} + \frac{1}{2\gamma_p}\tilde{K}_p^2 + \frac{1}{2\gamma_i}\tilde{K}_i^2$$

$$\dot{V}_{12} \leq -e^2 + C_{perturbation}$$

### v1.3 — Lyapunov augmenté (Q + PI)
$$V_{13} = \frac{1}{2}\phi_{est}^2 + \frac{1}{2\lambda}\tilde{Q}^2 + \frac{K_i}{2}I^2$$

$$\dot{V}_{13} \leq -\epsilon\|\phi_{est}\|^2 + C_z, \quad C_z \to 0 \text{ si } b_{est} \to b_{true}$$

### v1.4 — Borne quadratique conservatrice
Pas de nouvelle preuve Lyapunov (contrôle identique à v1.3). Ajout de la garantie sur la borne :

$$t_{rup}^{v1.4} = t_0 + \frac{-z_0 + \sqrt{z_0^2 + 2\dot{z}_0(Y_{max}-y_0)}}{\dot{z}_0}$$

**Garantie (avec condition) :** La borne est conservative si $\ddot{z}(t) \leq 0$ pour tout $t \geq t_0$ (dérive concave ou linéaire). Sous cette condition, si $\hat{\dot{b}}_{true} \geq \dot{b}_{true}^{réel}$ (second Kalman sur-estime la dérive), alors $t_{rup}^{v1.4} \leq t_{rup}^{réel}$.

**Justification :** L'équation $z_0 T + \frac{1}{2}\dot{z}_0 T^2 = \Delta Y_{\max}$ suppose $\dot{z}$ constant. Si $\ddot{z} > 0$ (dérive convexe), $\int_0^T z(t)\,dt > z_0 T + \frac{1}{2}\dot{z}_0 T^2$, donc la rupture réelle survient plus tôt → borne optimiste.

**En pratique :** Pour les systèmes dissipatifs (thermique, fatigue mécanique, dégradation batterie), $\ddot{z} \leq 0$ est physiquement vérifié. Pour les systèmes à dérive instable ($\ddot{z} > 0$ possible), activer une alarme quand $\hat{\dot{z}}_{k+1} > \hat{\dot{z}}_k$ sur une fenêtre de confirmation.

---

## Borne RETA par version

| Version | Formule | Post-panne GPS |
|---|---|---|
| v1.1–v1.3 | $t_0 + (Y_{max}-y_0)/z(t_0)$ | **OPTIMISTE si ż > 0** |
| v1.4 | $t_0 + T$ où $\dot{z}T^2/2 + zT = Y_{max}-y_0$ | **CONSERVATIF ✓** |

---

## Contenu des dossiers

```
docs/
├── VERSIONS.md       ← ce fichier
├── v1.1/
│   ├── README.md     ← Kalman fixe + PI fixe, Routh-Hurwitz
│   ├── simulation.py
│   └── results.png
├── v1.2/
│   ├── README.md     ← PI adaptatif gradient, Lyapunov
│   ├── simulation.py
│   └── results.png
├── v1.3/
│   ├── README.md     ← Kalman adaptatif Q, boucle fermée
│   ├── simulation.py ← simulation drone 3D
│   └── results.png
└── v1.4/
    ├── README.md     ← bound conservatif ḃ_true, équation quadratique
    ├── simulation.py ← démo limit v1.3 + correction v1.4
    └── results.png
```

---

## Références

- Théorie RETA : [docs/1_fondamentaux/reta_v13_demonstration.md](./1_fondamentaux/reta_v13_demonstration.md)
- Bibliographie centrale : [docs/bibliographie.md](./bibliographie.md)
- Benchmarks NASA : [docs/benchmarks.md](./benchmarks.md)
- Code production : [reta/](../reta/)
  - `kalman.py` : `Kalman1D` (v1.1) + `KalmanAdaptive` (v1.3)
  - `pi.py` : `PIRegulator` (fixe, gradient, heuristique)
  - `core.py` : `RETAReferential` — point d'entrée principal
