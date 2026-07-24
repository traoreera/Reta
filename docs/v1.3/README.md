# RETA v1.3 — Kalman Adaptatif Q + PI Adaptatif Gradient

**Statut :** Version complète — boucle fermée correcte, scénario drone GPS-outage validé

---

## Résumé en une phrase

v1.3 combine l'adaptation Q du filtre Kalman (via les innovations GPS) avec l'adaptation des gains PI, permettant d'estimer correctement un biais gyro croissant et de survivre 3 à 4× plus longtemps en dead-reckoning après une panne GPS.

---

## Problème résolu par v1.3

Dans v1.1 et v1.2, la matrice Q du Kalman est fixe et très petite (hypothèse biais constant). Si le biais gyro dérive thermiquement :

- Kalman suppose biais stable → gain K_biais ≈ 0
- b_est ne converge pas → z(t) = b_true − b_est reste grand
- PI corrige sur estimation erronée → phi_true diverge
- **Rupture RETA accélérée**

v1.3 adapte Q_biais en temps réel depuis les innovations GPS, ce qui permet de corriger b_est avant la panne.

---

## Physique correcte de la boucle fermée

La simulation implémente la physique réelle du drone :

```
phi_true(t+dt) = phi_true(t) + u(t)·dt        [drone bascule physiquement]
u(t)           = -Kp·phi_est - Ki·∫phi_est     [PI sur angle ESTIMÉ]
omega_meas     = u(t) + b_true + bruit         [gyro mesure taux réel]
phi_est_pred   = phi_est + (omega_meas - b_est)·dt
```

**Bug dans v1.1/v1.2 évité** : phi_true n'est PAS fixé à 0. Le PI agit physiquement sur le drone, et le gyro mesure le taux angulaire réel incluant la commande.

---

## Adaptation Q par innovations GPS

À chaque correction GPS, le résidu d'innovation $\nu$ encode la dérive biais :

$$\text{drift\_rate} = \frac{|\nu|}{T_{GPS}}$$

$$Q_{biais}^{inst} = (\text{drift\_rate} \cdot dt)^2$$

$$Q_{biais}(t+dt) = (1-\alpha)\,Q_{biais}(t) + \alpha\,Q_{biais}^{inst}$$

- Si le biais dérive rapidement : $|\nu|$ grand → $Q_{biais}$ monte → gain Kalman monte → b_est converge
- Si le biais est stable : $|\nu|$ petit → $Q_{biais}$ reste bas → filtre stable

### Lyapunov augmenté (Q adaptatif)

$$V = \frac{1}{2}\phi_{est}^2 + \frac{1}{2\lambda_1}\tilde{Q}^2 + \frac{K_i}{2}I^2$$

$$\dot{V} \leq -\epsilon \|\phi_{est}\|^2 + C_z \quad \forall t$$

où $C_z$ dépend de $\|z\|$ = biais résiduel. Si z → 0 (b_est → b_true), $\dot{V}$ → négatif.

---

## Scénario de validation

| Phase | t ∈ [0, 120s] | t ∈ [120s, 300s] |
|---|---|---|
| GPS | Toutes les 5s | **COUPÉ (dead-reckoning)** |
| Biais vrai | B0 × 1 à B0 × 4 (drift thermique) | Continue à croître |
| v1.1 : b_est | Converge lentement (0.6% à 120s) | Figée → z(t) >> 0 |
| v1.3 : b_est | Converge (91-103% à 120s) | Figée mais proche b_true |

---

## Résultats

| Axe | v1.1 rupture | v1.3 rupture | Gain |
|---|---|---|---|
| Roll (X) | t = 56s ⚠️ | t = 266s ⚠️ | **+210s (+3.7×)** |
| Pitch (Y) | t = 49s ⚠️ | t = 276s ⚠️ | **+227s (+4.6×)** |
| Yaw (Z) | t = 65s ⚠️ | **JAMAIS ✓** | **∞** |

**Biais estimé à t=120s (moment de la panne GPS) :**

| Axe | v1.1 b_est | v1.3 b_est | b_true | Ratio v1.3 |
|---|---|---|---|---|
| X | ~1 m°/s | ~152 m°/s | ~167 m°/s | 91% |
| Y | ~1 m°/s | ~180 m°/s | ~200 m°/s | 90% |
| Z | ~1 m°/s | ~360 m°/s | ~350 m°/s | 103% |

> **Image :** [results.png](results.png)
> **Code :** [simulation.py](simulation.py)

---

## Limite documentée : borne RETA non-conservative après panne GPS

Après la panne GPS, b_est est figée mais b_true continue à croître :

$$z(t) = b_{true}(t) - b_{est} \uparrow \quad \text{après } t_0$$

La borne v1.3 avec $z(t_0)$ figé :
$$t_{rup}^{v1.3} = t_0 + \frac{Y_{max} - y(t_0)}{z(t_0)}$$

**Mesure sur scénario drone :** borne prédite = 791s, rupture réelle = 273s → **+518s OPTIMISTE** ⚠️

Cette limite est la seule faille de sécurité critique de v1.3 — elle peut laisser croire que le système survivra alors que la rupture est imminente.

**Correction : [v1.4](../v1.4/README.md)** — second Kalman sur $[b_{true}, \dot{b}_{true}]$ + borne quadratique → erreur **−99s CONSERVATIF** ✓

---

## Paramètres critiques

```python
Q_BIAS_V11  = (1e-5)**2 * dt   # v1.1 : fixe et trop petit
Q_BIAS_V13  = Q_BIAS_V11 * 1000  # v1.3 : a priori conservateur
ALPHA_Q     = 0.4              # EMA d'adaptation Q

T_GPS_NORMAL = 5.0             # période GPS [s]
T_OUTAGE     = 120.0           # instant panne [s]
```

---

## Implémentation Python

```python
from reta.kalman import KalmanAdaptive
from reta.pi import PIRegulator

kalman = KalmanAdaptive(q_bias_init=Q_BIAS_V13, alpha_q=0.4)
pi     = PIRegulator(kp=4.0, ki=4.0, mode="adaptive_gradient")

for obs in signal:
    z_est = kalman.predict(omega_meas)
    if gps_available:
        z_est = kalman.update(phi_gps, R)
    u = pi.step(error=phi_est, dt=dt)
```

---

## Quand utiliser v1.3 ?

- ✓ **Drone en vol réel** avec biais gyro thermique (décollage → conditions chaudes)
- ✓ **Scenarios de panne GPS** : vol en tunnel, zone urbaine dense, jamming
- ✓ **Contrainte de temps** : v1.3 donne 3-4× plus de temps pour récupérer
- ✗ Temps réel ultra-serré (adaptation Q coûte 2 multiplications par axe par GPS)

---

*[← v1.2 (PI adaptatif)](../v1.2/README.md) · [← v1.1 (référence)](../v1.1/README.md) · [→ v1.4 (bound conservatif)](../v1.4/README.md) · [→ Résumé global](../VERSIONS.md)*

[📖 Index de la Documentation](../INDEX.md) · [🏠 Accueil du Projet](../../README.md)
