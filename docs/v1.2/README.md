# RETA v1.2 — Kalman Fixe + PI Adaptatif Gradient

**Statut :** Extension de v1.1 — même Kalman, gains PI auto-réglés par descente de gradient

---

## Résumé en une phrase

v1.2 conserve le filtre Kalman fixe de v1.1 mais remplace les gains PI constants par des lois d'adaptation gradient qui augmentent automatiquement Kp et Ki lorsque l'erreur s'accroît, garantissant la stabilité par Lyapunov même après un saut de perturbation.

---

## Problème résolu par v1.2

Avec un régulateur P pur (Ki = 0) à gains fixes, la perturbation constante z entraîne une **erreur statique permanente** :

$$y_{ss} = \frac{z}{K_p}$$

Si $z$ augmente soudainement (choc, changement d'environnement), $y_{ss}$ peut dépasser $Y_{max}$ — rupture RETA.

v1.2 acquiert automatiquement l'action intégrale manquante en adaptant Ki depuis 0.

---

## Lois d'adaptation (Lyapunov)

### Loi Kp
$$\dot{K}_p = \gamma_p \cdot \bar{e}^2, \quad \bar{e} = \frac{e}{e_{ref}}$$

- Kp croît proportionnellement au carré de l'erreur normalisée
- Kp ne peut que croître (amortissement garanti)

### Loi Ki
$$\dot{K}_i = \gamma_i \cdot \bar{e} \cdot \int \bar{e}\,d\tau$$

- Ki croît quand l'erreur et son intégrale sont de même signe (erreur persistante)
- Ki reste bornée par la contrainte $K_i \in [K_{i,min}, K_{i,max}]$

### Preuve de stabilité (Lyapunov augmenté)
$$V(e, I) = \frac{1}{2}e^2 + \frac{K_i(t)}{2}I^2$$

$$\dot{V} = -K_p(t)\cdot e^2 + e\cdot[f'(t)+z(t)] + \underbrace{\dot{K}_i \frac{I^2}{2}}_{\geq 0}$$

- Le terme positif $\dot{K}_i I^2/2$ est borné car $K_i$ converge
- $\dot{V} \leq 0$ **hors compact** $\mathcal{C}$ défini par l'amplitude de $f'(t)+z(t)$
- Stabilité asymptotique globale par théorème de LaSalle

---

## Scénario de démonstration

| Phase | t ∈ [0, 10s] | t ∈ [10s, 40s] |
|---|---|---|
| Perturbation z | 0.25 (nominale) | **2.8** (saut ×11) |
| y_ss v1.1 (P pur) | 0.625 ✓ | **7.0 > Y_max=5 ⚠️** |
| y_ss v1.2 (PI adaptatif) | → 0 | **→ 0** ✓ |

---

## Résultats

| Mesure | v1.1 (P pur, Ki=0) | v1.2 (PI adaptatif) |
|---|---|---|
| Rupture après saut | t = 12.84s ⚠️ | **JAMAIS ✓** |
| Kp après saut | 0.4 (fixe) | 1.476 (adapté) |
| Ki après saut | 0.0 (nul fixe) | 0.796 (acquis ✓) |
| y final | 7.002° (bloqué sur y_ss) | 0.000° (zéro ✓) |
| V Lyapunov | diverge | décroît ✓ |

> **Image :** [results.png](results.png)
> **Code :** [simulation.py](simulation.py)

---

## Mécanisme clé : acquisition de l'action intégrale

Le point central de v1.2 est que **Ki part de zéro** et monte automatiquement :

```
Ki(0) = 0  →  Ki(15s) ≈ 0.8
```

C'est la loi d'adaptation $\dot{K}_i = \gamma_i \bar{e} \cdot I$ qui agit en boucle positive sur l'erreur persistante. Une fois Ki > 0, le correcteur élimine l'erreur statique, l'erreur décroît, et Ki se stabilise.

---

## Limites de v1.2

- **Kalman toujours fixe** : si la qualité des mesures change (bruit GPS variable), Q̂ et R̂ ne s'adaptent pas → estimation de z dégradée
- **Risque de windup** : sans borne sur $I$, l'intégrale peut saturer avant que les gains s'adaptent
- **Transitoire après saut** : un pic d'erreur existe pendant 2-3s après le saut avant que le PI ait convergé

---

## Implémentation Python

```python
from reta.pi import PIRegulator

pi = PIRegulator(kp=0.4, ki=0.0, mode="adaptive_gradient")
# pi.gamma_p = 1.5
# pi.gamma_ki = 0.8
# pi.kp_bounds = (0.001, 20.0)
# pi.ki_bounds = (0.0, 10.0)

for obs in signal:
    u = pi.step(error=y_current, dt=dt)
    # pi.kp et pi.ki augmentent automatiquement
```

---

## Quand utiliser v1.2 ?

- ✓ Environnement variable mais bruit GPS/IMU stable (Kalman fixe OK)
- ✓ Perturbations à saut : choc thermique, changement de masse, turbulence soudaine
- ✓ Ressources de calcul modérées (pas d'adaptation Kalman)
- ✗ Bruit de mesure variable → passer à v1.3

---

*[← v1.1 (PI fixe)](../v1.1/README.md) · [→ v1.3 (Kalman adaptatif)](../v1.3/README.md) · [→ Résumé](../VERSIONS.md)*
