# RETA v1.1 — Kalman Fixe + PI Fixe

**Statut :** Version de référence — stable, prouvable, déployable

---

## Résumé en une phrase

v1.1 est la fondation mathématique de RETA : un filtre Kalman à matrices fixes estime la perturbation persistante z(t), et un correcteur PI à gains fixes maintient le signal sous le seuil Y_max.

---

## Modèle mathématique

### Signal RETA
$$y(t) = \arctan(t) + \int_0^t z(\tau)\,d\tau + \text{termes oscillants}$$

### Perturbation estimée (Kalman)
État : $\mathbf{x} = [z, \dot{z}]^T$

$$\mathbf{x}_{k+1} = A\mathbf{x}_k + w_k, \quad A = \begin{pmatrix}1&1\\0&1\end{pmatrix}$$

$$y_k = H\mathbf{x}_k + v_k, \quad H = [1\ 0]$$

**Q et R fixes** — calibrés une fois, ne changent pas en vol.

### Correcteur PI
$$u(t) = K_p \cdot e(t) + K_i \int_0^t e(\tau)\,d\tau$$

**Gains fixes** $K_p, K_i$ — déterminés à la conception.

### Lyapunov (preuve de stabilité)
$$V(e, I) = \frac{1}{2}e^2 + \frac{K_i}{2}I^2$$

$$\dot{V} = -K_p \cdot e^2 + e \cdot [f'(t) + z(t)] \leq 0 \quad \text{hors compact}$$

Les termes croisés $-K_i eI + K_i Ie = 0$ s'annulent **exactement** grâce au coefficient $K_i/2$.

### Borne RETA sur le temps de rupture
$$t_{rup} \geq \frac{Y_{max} - \pi/2}{\bar{z}(T)}$$

- **Conservative** (pessimiste d'un facteur ~4×) — sûre pour la planification
- **Pratique** : si $\bar{z}(T)$ croît, recalculer à chaque pas

---

## Propriétés

| Propriété | Valeur |
|---|---|
| Stabilité | Routh-Hurwitz (gains fixes) + Lyapunov (prouvé) |
| Bande résiduelle | $\|e(\infty)\| \leq (3+\sqrt{2})/K_p \approx 4.41/K_p$ |
| Temps de stabilisation | $t_{stable} \approx 8/K_p$ |
| Riccati P∞ | Converge vers $P_\infty$ — variance minimale garantie |
| Complexité | $O(n^2)$ par pas Kalman |

---

## Limites

- **Q, R fixes** : si le bruit du système change (vibrations, température), les estimations se dégradent
- **Kp, Ki fixes** : si la perturbation z(t) croît au-delà de la capacité du PI, il n'y a pas d'adaptation automatique
- **Erreur statique** : un PI avec $K_i = 0$ (régulateur P pur) laisse une erreur statique permanente pour des perturbations constantes

---

## Résultats de simulation

**Scénario :** z(t) croissant (biais thermique modéré), Y_max = 8, T_sim = 30s

| Mesure | Valeur |
|---|---|
| Rupture sans PI | t = 15.49s ⚠️ |
| Rupture avec PI v1.1 | **JAMAIS ✓** |
| Borne RETA prédite | t_rup ≥ 16.29s |
| Bande résiduelle | \|e(∞)\| ≤ 2.94 |
| Kp | 1.5 |
| Ki | 0.2 |

> **Image :** [results.png](results.png)
> **Code :** [simulation.py](simulation.py)

---

## Implémentation Python

```python
from reta.kalman import Kalman1D
from reta.pi import PIRegulator

kalman = Kalman1D(Q=2e-5, R=5e-4)   # matrices fixes
pi     = PIRegulator(kp=1.5, ki=0.2) # gains fixes

for obs in signal:
    z_est = kalman.update(obs)
    u = pi.step(error=y_current, dt=dt)
```

---

## Quand utiliser v1.1 ?

- ✓ Environnement stable et bien caractérisé (bruit connu)
- ✓ Ressources de calcul limitées (embarqué, temps réel serré)
- ✓ Certification formelle requise (preuves mathématiques disponibles)
- ✗ Bruit variable ou perturbations imprévues → passer à v1.3

---

*[→ v1.2 (PI adaptatif)](../v1.2/README.md) · [→ v1.3 (Kalman adaptatif)](../v1.3/README.md) · [→ Résumé](../VERSIONS.md)*

[📖 Index de la Documentation](../INDEX.md) · [🏠 Accueil du Projet](../../README.md)
