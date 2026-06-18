# Analyse de la Théorie RETA
*Referential Escape Theory by Accumulation — Analyse complète v1.3*

---

## 1. Vue d'ensemble de la théorie

RETA modélise un phénomène précis : **un système dynamiquement borné qui échappe à ses limites sous l'effet d'une perturbation persistante**. La clé est que la perturbation n'a pas besoin d'être grande — elle doit seulement être strictement positive à tout instant (z(t) ≥ ε > 0). Le temps fait le reste par intégration cumulative.

### Ce que RETA apporte par rapport au contrôle classique

| Approche classique | RETA |
|---|---|
| Réagit quand la limite est atteinte | Prédit **quand** la limite sera atteinte |
| Modélise l'état présent | Modélise la **trajectoire vers la rupture** |
| PID à gains fixes | PI auto-adaptatif + estimation Kalman |

---

## 2. Architecture de la théorie (structure en couches)

```
┌─────────────────────────────────────────────┐
│  COUCHE 4 — Décision / Alarme               │
│  t_montée < t_stable < t_rupture ?          │
│  Alarme à 0.8 · t_rupture                   │
└────────────────┬────────────────────────────┘
                 │
┌────────────────▼────────────────────────────┐
│  COUCHE 3 — Auto-Tuning des gains (v1.2)    │
│  K̇p = γp · (|e| − θ)                       │
│  K̇i = γi · |e| · sgn(∫e)                  │
└────────────────┬────────────────────────────┘
                 │
┌────────────────▼────────────────────────────┐
│  COUCHE 2 — Contrôle (PI)                   │
│  u(t) = Kp(t)·ê(t) + Ki(t)·∫ê(τ)dτ        │
│  Entrée : ŷ_kalman (pas y brut)             │
└────────────────┬────────────────────────────┘
                 │
┌────────────────▼────────────────────────────┐
│  COUCHE 1 — Perception (Kalman)             │
│  Estime ŷ et ẑ depuis y_mesuré bruité      │
│  Modèle d'état : x = [y, z]^T              │
└────────────────┬────────────────────────────┘
                 │
┌────────────────▼────────────────────────────┐
│  COUCHE 0 — Système physique                │
│  y(t) = arctan(t) + ∫z(τ)dτ               │
└─────────────────────────────────────────────┘
```

---

## 3. Analyse des équations clés

### 3.1 Équation maîtresse de dérive (système libre)

$$y(t) = \arctan(t) + 2t + \sin(t) - \cos(t) + 1$$

**Décomposition des termes :**

| Terme | Nature | Comportement à long terme |
|---|---|---|
| arctan(t) | Système initial borné | Sature vers π/2 ≈ 1,57 — devient négligeable |
| 2t | Dérive linéaire (intégrale de la composante constante de z) | **Terme dominant** — croissance illimitée |
| sin(t) − cos(t) | Oscillation intégrée | Amplitude √2, moyenne nulle — ne contribue pas à l'évasion |
| +1 | Constante d'intégration | Décalage initial fixe |

**Conclusion :** À long terme, le système est **linéairement divergent** avec une vitesse moyenne de 2 et une oscillation d'amplitude √2 superposée. L'asymptote de arctan(t) est détruite dès t > quelques secondes.

### 3.2 Calcul du point de rupture

L'équation exacte est transcendante (pas de solution analytique fermée) :

$$Y_{max} = \arctan(t_r) + 2t_r + \sin(t_r) - \cos(t_r) + 1$$

La borne conservative (z = ε constant, scénario pessimiste garanti) :

$$t_{rupture} \geq \frac{Y_{max} - \frac{\pi}{2}}{\varepsilon} = \frac{Y_{max} - 1{,}57}{0{,}59}$$

**Pourquoi cette borne est utile en pratique :** elle ne nécessite pas de connaître la forme exacte de z(t), seulement son minimum garanti ε. C'est une **garantie de sécurité**, pas une prédiction précise.

**Pour une prédiction précise :** utiliser scipy.optimize.brentq sur l'équation transcendante (voir section 6).

### 3.3 Le correcteur PI

$$u(t) = K_p \cdot e(t) + K_i \int_0^t e(\tau)\,d\tau$$

**Pourquoi PI et non P seul ?**
- Le terme P seul ne peut pas annuler une dérive permanente (erreur résiduelle en régime stationnaire).
- Le terme I accumule l'erreur passée et génère une force opposée à la dérive cumulative de z(t) — c'est un "anti-z" par construction.

**Condition de stabilité (critère de Routh) :** Kp > 0 et Ki > 0.

**Réglage recommandé :**
- Fixer la contrainte sur t_stable : `Kp = 8 / t_stable_cible`
- Choisir Ki pour le régime (sous-amorti : Ki > Kp²/4, sur-amorti : Ki < Kp²/4)

---

## 4. Analyse de l'extension Kalman (v1.1)

### 4.1 Justification

Sans Kalman, le correcteur PI agit sur y(t) bruité — risque de réactions parasites aux oscillations de mesure. Le filtre Kalman résout deux problèmes simultanément :

1. **Débruitage de y** : sépare la tendance (dérive réelle) du bruit de mesure
2. **Estimation de z** : infère la perturbation non-mesurée depuis les variations de y

### 4.2 Modèle d'espace d'état

$$x_k = \begin{pmatrix} y_k \\ z_k \end{pmatrix}, \quad A = \begin{pmatrix} 1 & \Delta t \\ 0 & 1 \end{pmatrix}$$

**Interprétation :** z est modélisé comme une **marche aléatoire** (z_{k+1} ≈ z_k + bruit processus). C'est approprié si z varie lentement par rapport à Δt.

**Limitation :** Si z(t) est fortement oscillant (comme sin(t) + cos(t) avec Δt grand), le modèle de Kalman sous-estime les variations. Deux options :
- Réduire Δt (augmenter la fréquence d'échantillonnage)
- Enrichir le modèle d'état (ajouter dz/dt comme 3ème état)

### 4.3 Impact sur t_rupture

Avec Kalman, t_rupture est calculé avec ẑ estimé au lieu de ε conservateur :

$$t_{rupture} \approx \frac{Y_{max} - \hat{y}_{kalman}}{\hat{z}_{kalman}}$$

**Avantage :** prédiction dynamique mise à jour à chaque pas, bien plus précise que la borne statique.

---

## 5. Analyse de cohérence et points d'attention

### 5.1 Incohérence de numérotation

Le document saute de la **section 6** (Stabilité) directement à la **section 8** (Kalman) — la **section 7** est absente dans la version actuelle. À vérifier si contenu manquant.

### 5.2 Équation du système régulé (section 4.3)

$$y_{réel}(t) = f(t) + \int_0^t z(\tau)\,d\tau - K_p \cdot e(t) - K_i \int_0^t e(\tau)\,d\tau$$

**Remarque :** Cette équation mélange la trajectoire libre et l'action de commande dans une même expression. Elle est correcte en représentation continue, mais suppose que u(t) agit directement en soustraction sur y — ce qui implique que le système est à **gain unitaire**. En simulation, il faut définir explicitement la dynamique du système physique (comment u(t) est appliqué).

### 5.3 Lyapunov (section 6.2)

La fonction candidate V(e) = e²/2 est présentée mais la démonstration de dV/dt < 0 n'est pas complétée dans le document. Pour la compléter :

$$\frac{dV}{dt} = e(t) \cdot \dot{e}(t)$$

Il faut exprimer ė(t) en fonction de z(t) et u(t) pour conclure.

---

## 6. Feuille de route simulation

### Priorité 1 — Validation du modèle libre

```python
import numpy as np
import matplotlib.pyplot as plt

t = np.linspace(0, 20, 1000)
y = np.arctan(t) + 2*t + np.sin(t) - np.cos(t) + 1

# Vérifier : y atteint Y_max=10 avant t_rupture conservateur (14.28s) ?
```

### Priorité 2 — t_rupture précis par résolution numérique

```python
from scipy.optimize import brentq

Y_max = 10
f = lambda t: np.arctan(t) + 2*t + np.sin(t) - np.cos(t) + 1 - Y_max
t_rupture_exact = brentq(f, 0, 20)
# Comparer avec borne conservative : (10 - 1.57) / 0.59 ≈ 14.28
```

### Priorité 3 — Simulation du système régulé (PI discret)

Implémentation Euler avec pas Δt :

```python
# État initial
y, integral_e = 0.0, 0.0
Kp, Ki = 2.0, 0.5
Y_c = 5.0  # consigne

for k in range(N):
    z_k = 2 + np.sin(t[k]) + np.cos(t[k])
    e_k = y - Y_c
    integral_e += e_k * dt
    u_k = Kp * e_k + Ki * integral_e
    dy = (1/(1+t[k]**2)) + z_k - u_k
    y += dy * dt
```

### Priorité 4 — Extension Kalman

Implémenter le filtre avec `filterpy` ou manuellement avec les équations de prédiction/correction.

---

## 7. Analyse de la couche Auto-Adaptive (v1.2)

### 7.1 Lois d'adaptation

**Adaptation de Ki (réaction à la persistance de l'erreur) :**

$$\dot{K_i}(t) = \gamma_i \cdot |e(t)| \cdot \text{sgn}\left(\int e\right)$$

Logique : si l'erreur est grande et que l'intégrale est positive (le système est resté trop longtemps au-dessus de la consigne), Ki augmente pour forcer le retour. Si l'intégrale change de signe (dépassement), Ki peut se réduire pour éviter l'oscillation.

**Adaptation de Kp (gestion de la nervosité) :**

$$\dot{K_p}(t) = \gamma_p \cdot (|e(t)| - \theta)$$

- Si |e| > θ : Kp augmente → réaction plus agressive
- Si |e| < θ : Kp diminue → amortissement, évite le surdépassement
- θ est le seuil de tolérance (bande morte)

### 7.2 Points d'attention critiques

**Stabilité du système adaptatif**

L'ajout de lois d'adaptation rend la stabilité bien plus difficile à prouver. Le critère de Routh (section 6.1) ne s'applique plus car Kp et Ki varient dans le temps — la fonction de transfert H(s) n'est plus LTI (Linear Time-Invariant).

Pour prouver la stabilité de v1.2, il faudra soit :
- Une analyse de Lyapunov étendue avec V(e, Kp, Ki) — beaucoup plus complexe
- Une analyse par simulation (domaine de stabilité empirique en fonction de γp, γi, θ)

**Risque d'emballement des gains**

Sans contrainte de saturation, Kp et Ki peuvent diverger si l'erreur persiste. En pratique, il faut ajouter :

$$K_p \in [K_{p,min},\ K_{p,max}], \quad K_i \in [K_{i,min},\ K_{i,max}]$$

**Choix des learning rates (γp, γi)**

Paramètres les plus sensibles de v1.2. Trop grands → oscillations des gains, instabilité. Trop petits → adaptation trop lente, gain de v1.2 nul par rapport à v1.1.

### 7.3 Pipeline complet v1.2

```
y_mesuré(k)
    │
    ▼
[Kalman] ──→ ŷ_k, ẑ_k
    │
    ├──→ t_rupture = (Y_max − ŷ_k) / ẑ_k  [alarme si t_rupture < seuil]
    │
    ▼
e_k = ŷ_k − Y_c
    │
    ├──→ [Auto-tuning] : met à jour Kp(k+1), Ki(k+1)
    │
    ▼
u_k = Kp(k)·e_k + Ki(k)·∫e  [correcteur PI avec gains variables]
    │
    ▼
système physique → y(k+1)
```

---

## 8. Analyse de la v1.3 — Chameleon RETA

### 8.1 Principe : clore la boucle sur la perception elle-même

Les versions précédentes adaptaient l'**action** (Kp, Ki) mais laissaient la **perception** (les matrices Q et R du filtre Kalman) fixes. La v1.3 ferme la dernière boucle ouverte : le filtre lui-même se recalibre en observant ses propres erreurs de prédiction (l'innovation νk).

### 8.2 Innovation νk — le signal de diagnostic central

$$\nu_k = y_{mesuré,k} - H\hat{x}_{k|k-1}$$

C'est l'écart entre ce que le filtre **prédisait** voir et ce qu'il a **réellement** vu. En régime normal, νk doit être un bruit blanc de moyenne nulle. Si νk présente une tendance ou une variance anormale, c'est le signe que Q ou R est mal calibré.

| Symptôme sur νk | Interprétation | Action corrective |
|---|---|---|
| Variance de νk augmente | Le capteur est plus bruité | Augmenter R |
| νk biaisé (moyenne ≠ 0) | Le modèle RETA dévie de la réalité | Augmenter Q |
| νk trop petite, filtre "rigide" | R sous-estimé, filtre trop confiant | Diminuer R |

### 8.3 Lois d'adaptation des matrices

**Adaptation de R (bruit de mesure) — lissage exponentiel :**

$$\hat{R}_k = \alpha \hat{R}_{k-1} + (1-\alpha)(\nu_k \nu_k^T + H P_{k|k-1} H^T)$$

- α ∈ [0,1] : facteur d'oubli. α proche de 1 → mémoire longue (lent). α proche de 0 → réactif mais instable.
- Le terme `H P H^T` retire la contribution propre du filtre pour isoler le vrai bruit de mesure.

**Adaptation de Q (bruit de processus) :**

$$\hat{Q}_k = \beta \hat{Q}_{k-1} + (1-\beta)(G_k \nu_k \nu_k^T G_k^T)$$

- Gk est le gain de Kalman courant.
- Logique : si le modèle est pris par surprise (νk grand), Q augmente pour que le filtre "lâche prise" sur son modèle et suive mieux les données.

### 8.4 Cycle complet v1.3 (5 étapes)

```
┌─────────────────────────────────────────────────────┐
│  ÉTAPE 1 — Évaluer la clarté du signal              │
│  νk = y_mesuré − H·x̂_pred                          │
│  → Ajuster R̂k (bruit capteur)                      │
└──────────────────────────┬──────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────┐
│  ÉTAPE 2 — Évaluer la validité du modèle RETA       │
│  → Ajuster Q̂k (dérive du modèle)                   │
└──────────────────────────┬──────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────┐
│  ÉTAPE 3 — Extraire l'état optimal                  │
│  Kalman(Q̂k, R̂k) → [ŷk, ẑk]                        │
└──────────────────────────┬──────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────┐
│  ÉTAPE 4 — Calculer la réponse adaptée              │
│  Ajuster Kp(t), Ki(t) via lois v1.2                 │
│  u_k = Kp·(ŷ − Yc) + Ki·∫(ŷ − Yc)dτ               │
└──────────────────────────┬──────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────┐
│  ÉTAPE 5 — Prédire la rupture auto-calibrée         │
│  t_rupture ≈ (Y_max − ŷk) / ẑk                     │
│  Alarme si t_rupture < seuil                        │
└─────────────────────────────────────────────────────┘
```

### 8.5 Points d'attention critiques v1.3

**Stabilité encore plus difficile à prouver**

Avec Q et R dynamiques, le gain de Kalman Gk varie à chaque pas — le filtre n'est plus un filtre de Kalman standard (il devient un filtre adaptatif de type AKF). La convergence de Pk vers zéro n'est plus garantie. Il faut vérifier empiriquement que Pk reste borné.

**Initialisation et phase d'apprentissage**

Les premières secondes sont critiques : Q et R partent de valeurs initiales arbitraires. Pendant cette phase, les estimations ŷ et ẑ sont peu fiables, donc t_rupture peut être faux. Il faut définir une **période de chauffe** (warm-up) avant d'activer l'alarme.

**Interaction entre les 4 paramètres adaptatifs**

Kp, Ki, Q, R s'influencent mutuellement en boucle fermée. Un Q qui augmente → ẑ plus volatile → t_rupture instable → Kp réagit plus fort → erreur change → Ki s'adapte. Risque de cycles parasites. À surveiller en simulation.

**Choix des facteurs d'oubli α et β**

Paramètres les plus sensibles de v1.3 (rôle analogue à γp, γi de v1.2). Recommandation de départ : α ≈ 0.95-0.99, β ≈ 0.90-0.98.

---

## 9. Synthèse des versions

| Version | Nom | Gains PI | Kalman Q, R | Déploiement |
|---|---|---|---|---|
| v1.0 | RETA Pur | Fixes | Sans Kalman | Paramétrage manuel complet |
| v1.1 | RETA-Kalman | Fixes | Fixes | Paramétrage manuel complet |
| v1.2 | Adaptive RETA | Auto-adaptatifs (γp, γi, θ) | Fixes | Paramétrage Q, R manuel |
| v1.3 | Chameleon RETA | Auto-adaptatifs | Auto-adaptatifs (α, β) | Zero-config après warm-up |

**Progression de l'autonomie :** v1.0 demande tout au concepteur → v1.3 n'a besoin que des limites physiques (Y_max, Yc) et des facteurs d'oubli (α, β).

---

*Analyse basée sur ebauche.md — Version complète avec sections 1-11*

---
## 🧭 Navigation
- [📖 Index de la Documentation](../INDEX.md)
- [🏠 Accueil du Projet](../../README.md)
