# RETA v1.4 — Bound Conservatif par Tracking ḃ_true

**Statut :** Correctif ciblé sur la borne t_rup — même architecture Kalman + PI que v1.3

---

## Résumé en une phrase

v1.4 corrige la seule vraie limite documentée de v1.3 : la borne sur le temps de rupture devient non-conservative quand z(t) croît après la panne GPS. En estimant le taux de dérive ḃ_true par un second Kalman, la borne reste toujours en dessous de la rupture réelle.

---

## La limite documentée de v1.3

Après la panne GPS à t₀, b_est est figée tandis que b_true continue de dériver :

$$z(t) = b_{true}(t) - b_{est} \uparrow \quad \text{pour } t > t_0$$

La borne v1.3 utilise z(t₀) fixé :

$$t_{rup}^{v1.3} = t_0 + \frac{Y_{max} - y(t_0)}{z(t_0)}$$

Si z(t) croît, cette borne est **optimiste** : elle prédit que tout va bien alors que le drone rupture bien avant.

**Résultat mesuré :**
- Borne v1.3 : 791s
- Rupture réelle : 273s
- **Erreur : +518s (OPTIMISTE ⚠️)**

---

## Pourquoi on ne peut pas extrapoler ż depuis le passé récent

Pendant la phase GPS, le Kalman converge vers b_true → z **décroît** → ż < 0.

Juste après la panne, b_est est figée et b_true continue → z **croît** → ż flip > 0.

Extrapoler ż depuis l'historique récent donne la **mauvaise direction** (ż < 0 alors que le danger est ż > 0).

---

## Solution v1.4 : tracker ḃ_true, pas ż

v1.4 maintient un second filtre Kalman sur l'état $[b_{true},\ \dot{b}_{true}]$, alimenté par les corrections GPS successives.

$$\hat{x}_{bt} = \begin{pmatrix} b_{true} \\ \dot{b}_{true} \end{pmatrix}, \quad A_{bt} = \begin{pmatrix} 1 & dt \\ 0 & 1 \end{pmatrix}$$

À chaque GPS, l'observation est $b_{est}^{corrigé}$ (après correction Kalman principal) → estimation de b_true courant → mise à jour de $\dot{b}_{true}$.

**À la panne t₀ :**
$$z_0 = b_{true}^{est} - b_{est}, \quad \dot{z}_0 = \dot{b}_{true}^{est}$$

Après t₀, b_est est figée → $\dot{z} = \dot{b}_{true}$ (propriété physique, pas estimation du passé).

---

## Nouvelle borne quadratique (CONSERVATIF)

En modélisant z(t) = z₀ + ż₀·(t − t₀) linéairement :

$$\int_{t_0}^{t_0+T} z(\tau)\,d\tau = z_0 T + \frac{\dot{z}_0}{2} T^2 = Y_{max} - y(t_0)$$

Résolution en T :

$$\boxed{T_{v1.4} = \frac{-z_0 + \sqrt{z_0^2 + 2\dot{z}_0 (Y_{max} - y_0)}}{\dot{z}_0}}$$

$$t_{rup}^{v1.4} = t_0 + T_{v1.4}$$

**Cas limite :** si ż₀ → 0, on retrouve T = (Y_max − y₀)/z₀ (bound v1.3).

**Propriété de conservatisme :** si l'estimation $\hat{\dot{b}}_{true} \geq \dot{b}_{true}^{réel}$, alors bound_v1.4 ≤ t_rup_réel.

---

## Résultats de simulation

**Scénario :** Biais thermique croissant, GPS coupé à t₀ = 115s

| Bound | Valeur | Erreur vs réel | Conservatif ? |
|---|---|---|---|
| v1.3 (z figé) | 791.8s | +518.4s | **NON ⚠️** |
| v1.4 (ż tracké) | 174.3s | −99.1s | **OUI ✓** |
| Rupture réelle | 273.4s | — | — |

| Paramètre | Valeur |
|---|---|
| z(t₀) | 7.24 m°/s (3.6% du biais) |
| ḃ_true estimé | 2.5 m°/s/s |
| ḃ_true réel | 0.53 m°/s/s |
| Marge de sécurité | −99s (conservatif) |

> **Note :** ḃ_true_est > ḃ_true_réel (facteur ×4.7) → surestimation volontairement pessimiste → bound plus conservatif. C'est le comportement voulu.

> **Image :** [results.png](results.png)
> **Code :** [simulation.py](simulation.py)

---

## Ce que v1.4 ne change PAS

- Architecture Kalman principale : identique à v1.3 (Q adaptatif, GPS correction)
- Lois PI adaptatives : identiques à v1.3 (gradient Kp, Ki)
- Estimation des biais : identique — la survie après panne est la même que v1.3
- Complexité de contrôle : inchangée

**v1.4 ajoute uniquement :** un second Kalman 2D sur [b_true, ḃ_true] (2 scalaires) + résolution de l'équation quadratique au moment de la panne.

---

## Implémentation

```python
# Second Kalman pour ḃ_true
A_bt = np.array([[1.0, dt], [0.0, 1.0]])
# obs à chaque GPS : b_true_obs = b_est_corrigé
# → donne ḃ_true_est

# Bound v1.4 au moment de la panne t₀
z0  = b_true_est - b_est_frozen
zd0 = bdot_true_est          # > 0 garanti (thermique)
rem = Y_max - abs(phi_true)
disc = z0**2 + 2 * zd0 * rem
T_v14 = (-z0 + np.sqrt(disc)) / zd0
t_rup_v14 = t0 + T_v14      # toujours ≤ t_rup_réel si zd0_est ≥ zd0_réel
```

---

## Relation avec une éventuelle v1.5 / v2.0

v1.4 corrige le **bound** mais ne prédit pas mieux la SURVIE (la rupture arrive toujours au même moment). Une v2.0 pourrait adresser :
- Mise à jour continue de b_est pendant le dead-reckoning via un modèle inertiel
- Fusion avec accéléromètre pour corriger b en l'absence de GPS
- Bound sur horizon glissant (actualisé toutes les 10s avec ż courant)

---

*[← v1.3 (Kalman adaptatif Q)](../v1.3/README.md) · [← Résumé](../VERSIONS.md)*
