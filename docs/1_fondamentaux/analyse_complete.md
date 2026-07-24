# Analyse de la Théorie RETA
*Referential Escape Theory by Accumulation — Analyse complète v2.0*

---

> **Statut des sections :**
> -  Validé mathématiquement
> -  Valide sous hypothèses précisées
> - À valider par simulation

---

## 1. Vue d'ensemble de la théorie

RETA modélise un phénomène précis : **un système dynamiquement borné qui échappe à ses
limites sous l'effet d'une perturbation persistante**. La clé est que la perturbation
n'a pas besoin d'être grande — elle doit seulement être strictement positive à tout
instant (z(t) ≥ ε > 0). Le temps fait le reste par intégration cumulative.

### Ce que RETA apporte par rapport au contrôle classique

| Approche classique | RETA |
|---|---|
| Réagit quand la limite est atteinte | Prédit **quand** la limite sera atteinte |
| Modélise l'état présent | Modélise la **trajectoire vers la rupture** |
| PID à gains fixes | PI auto-adaptatif (gradient) + estimation Kalman |
| Alarme sur seuil fixe | Chronomètre de rupture dynamique mis à jour en continu |

---

## 2. Architecture de la théorie (structure en couches)

```
┌─────────────────────────────────────────────┐
│  COUCHE 4 — Décision / Alarme               │
│  t_montée < t_stable < t_rupture ?          │
│  Alarme précoce  à 0.6 · t_rupture_exact    │
│  Alarme critique à 0.8 · t_rupture_exact    │
└────────────────┬────────────────────────────┘
                 │
┌────────────────▼────────────────────────────┐
│  COUCHE 3 — Auto-Tuning des gains (v1.2)    │
│  K̇p = γp · ē²          (gradient, prouvé)  │
│  K̇i = γi · ē · ∫ē dτ  (gradient, prouvé)  │
│  ē = e / e_ref  (normalisée, sans dim.)     │
└────────────────┬────────────────────────────┘
                 │
┌────────────────▼────────────────────────────┐
│  COUCHE 2 — Contrôle (PI)                   │
│  u(t) = Kp(t)·ē(t)·e_ref + Ki(t)·∫ē·e_ref │
│  Entrée : ŷ_kalman (pas y brut)             │
└────────────────┬────────────────────────────┘
                 │
┌────────────────▼────────────────────────────┐
│  COUCHE 1 — Perception (Kalman)             │
│  Estime ŷ et ẑ depuis y_mesuré bruité      │
│  Modèle d'état : x = [y, z]ᵀ              │
│  v1.3 : Q et R auto-adaptatifs via νk      │
└────────────────┬────────────────────────────┘
                 │
┌────────────────▼────────────────────────────┐
│  COUCHE 0 — Système physique                │
│  y(t) = arctan(t) + ∫z(τ)dτ               │
│  z(t) ≥ ε > 0 garanti                      │
└─────────────────────────────────────────────┘
```

---

## 3. Analyse des équations clés

### 3.1 Équation maîtresse de dérive (système libre) 

$$y(t) = \arctan(t) + 2t + \sin(t) - \cos(t) + 1$$

**Vérification initiale :** y(0) = 0 + 0 + 0 − 1 + 1 = **0** 

**Décomposition des termes :**

| Terme | Nature | Comportement à long terme |
|---|---|---|
| arctan(t) | Système initial borné | Sature vers π/2 ≈ 1,57 — négligeable pour t > 5 |
| 2t | Dérive linéaire (intégrale de la composante constante de z) | **Terme dominant** — croissance illimitée |
| sin(t) − cos(t) | Oscillation intégrée | Amplitude √2 ≈ 1,41, moyenne nulle |
| +1 | Constante d'intégration (−cos(0) = −(−1) = ... attention ci-dessous) | Décalage initial |

> **Note sur la constante +1 :** Elle provient de ∫₀ᵗ sin(τ)dτ = 1 − cos(t),
> évalué en t=0 : 1 − cos(0) = 1 − 1 = 0, et ∫₀ᵗ cos(τ)dτ = sin(t),
> évalué en t=0 : sin(0) = 0. La constante +1 vient uniquement de
> ∫₀ᵗ sin(τ)dτ|_{constante} = [−cos(τ)]₀ᵗ qui donne +1 à t=0 d'intégration.
> Vérification numérique conseillée pour confirmer y(0) = 0.

**Conclusion asymptotique :** À long terme le système est **linéairement divergent**
avec vitesse moyenne 2 et oscillation d'amplitude √2 superposée.

### 3.2 Calcul du point de rupture 

#### Valeur exacte (à utiliser pour tout dimensionnement)

L'équation est transcendante — pas de solution analytique :

$$Y_{\max} = \arctan(t_r) + 2t_r + \sin(t_r) - \cos(t_r) + 1$$

**Résolution numérique obligatoire :**

```python
from scipy.optimize import brentq
import numpy as np

def y_libre(t):
    return np.arctan(t) + 2*t + np.sin(t) - np.cos(t) + 1

Y_max = 10
t_rupture_exact = brentq(lambda t: y_libre(t) - Y_max, 0, 50)
# Résultat : t_rupture_exact ≈ 3.66 s
```

#### Borne conservative (certification only) 

$$t_{\text{rupture}} \geq \frac{Y_{\max} - 1{,}57}{0{,}59} \approx 14{,}4 \text{ s pour } Y_{\max}=10$$

>  **ÉCART FACTEUR ~4 avec la valeur exacte (3,66 s).**
> Usage autorisé : certification worst-case uniquement.
> Usage interdit : alarmes, dimensionnement de correcteur, prédiction nominale.

### 3.3 Le correcteur PI 

$$u(t) = K_p \cdot e(t) + K_i \int_0^t e(\tau)\,d\tau$$

**Pourquoi PI et non P seul ?**

Le terme P seul ne peut pas annuler une dérive permanente (erreur résiduelle en régime
stationnaire). Le terme I accumule l'erreur passée et génère une force opposée à la
dérive cumulative de z(t) — c'est un "anti-z" par construction.

**Condition de stabilité (critère de Routh, gains fixes) :** Kp > 0 et Ki > 0.

**Réglage recommandé :**
- Fixer la contrainte sur t_stable : `Kp = 8 / t_stable_cible`
- Ki sous-amorti : Ki > Kp²/4 — Ki critique : Ki = Kp²/4 — Ki sur-amorti : Ki < Kp²/4

**En v1.2 (gains adaptatifs) :** utiliser les lois gradient avec erreur normalisée
ē = e/e_ref. Kp et Ki fixés comme valeurs initiales, puis auto-adaptés.

---

## 4. Analyse de l'extension Kalman (v1.1) 

### 4.1 Justification

Sans Kalman, le correcteur PI agit sur y(t) bruité — risque de réactions parasites
aux oscillations de mesure. Le filtre Kalman résout deux problèmes :

1. **Débruitage de y** : sépare la tendance réelle du bruit de mesure
2. **Estimation de z** : infère la perturbation non-mesurée depuis les variations de y

### 4.2 Modèle d'espace d'état 

$$x_k = \begin{pmatrix} y_k \\ z_k \end{pmatrix}, \quad A = \begin{pmatrix} 1 & \Delta t \\ 0 & 1 \end{pmatrix}, \quad H = \begin{pmatrix} 1 & 0 \end{pmatrix}$$

**Observabilité :** rang([Hᵀ, AᵀHᵀ]) = 2 → système observable → convergence Kalman garantie 

**Modèle de z :** marche aléatoire (z_{k+1} ≈ z_k + bruit). Approprié si z varie
lentement par rapport à Δt.

**Limitation connue :** Si z(t) est fortement oscillant avec Δt grand, le modèle
sous-estime les variations. Solutions : réduire Δt ou enrichir le modèle (3ème état dz/dt).

### 4.3 Impact sur t_rupture 

Avec Kalman, t_rupture est calculé dynamiquement :

$$t_{\text{rupture}} \approx \frac{Y_{\max} - \hat{y}_{\text{Kalman}}}{\hat{z}_{\text{Kalman}}}$$

**Avantage :** prédiction mise à jour à chaque pas, bien plus précise que la borne
statique. Nécessite que ẑ_Kalman ait convergé (après ~50 pas).

---

## 5. Analyse de cohérence et points d'attention

### 5.1 Incohérence de numérotation — RÉSOLUE 

La version précédente sautait de la section 6 à la section 8.
La v2.0 de `theorie_fondamentale.md` corrige la numérotation :
sections 1→11 continues, sans saut.

### 5.2 Équation du système régulé 

$$y_{\text{réel}}(t) = f(t) + \int_0^t z(\tau)\,d\tau - K_p \cdot e(t) - K_i \int_0^t e(\tau)\,d\tau$$

**Hypothèse implicite confirmée :** u(t) agit directement en soustraction sur ẏ(t)
(gain unitaire du système physique). Si le gain est G ≠ 1, remplacer Kp → Kp/G,
Ki → Ki/G. Cette hypothèse doit être vérifiée pour chaque application.

### 5.3 Lyapunov — CORRIGÉE 

La version précédente omettait le terme Ki·eI·(1−Kp)/Kp dans V̇.

**Forme correcte de V̇ :**

$$\dot{V} = -K_p e^2 + e[f'(t) + z(t)] + K_i eI \cdot \frac{1-K_p}{K_p}$$

Le terme résiduel est nul uniquement si Kp = 1. Pour minimiser son impact,
choisir Kp proche de 1 ou l'absorber dans la borne de stabilité pratique.

La conclusion reste **stabilité pratique (Ultimate Boundedness)** : l'erreur converge
vers une bande résiduelle bornée, dont la taille dépend de Kp, Ki et z_max.

### 5.4 Lois d'adaptation — problème de dimensions RÉSOLU 

Les lois d'adaptation utilisent désormais l'erreur normalisée ē = e/e_ref.
Les paramètres γp et γi sont sans dimension et portables entre systèmes.
Voir `theorie_fondamentale.md` §9.2 et `reponses_critiques.md` Critique 5.

---

## 6. Feuille de route simulation 🔬

### Priorité 1 — Validation du modèle libre

```python
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import brentq

t = np.linspace(0, 20, 10000)
y = np.arctan(t) + 2*t + np.sin(t) - np.cos(t) + 1

# Rupture exacte
Y_max = 10
t_exact = brentq(lambda t: np.arctan(t) + 2*t + np.sin(t) - np.cos(t) + 1 - Y_max, 0, 20)
t_borne = (Y_max - np.pi/2) / (2 - np.sqrt(2))

print(f"t_rupture exact  : {t_exact:.3f} s")
print(f"t_rupture borne  : {t_borne:.3f} s")
print(f"Facteur d'écart  : {t_borne/t_exact:.1f}×")
# Attendu : exact ≈ 3.66 s, borne ≈ 14.4 s, écart ≈ 3.9×
```

### Priorité 2 — Système régulé PI discret

```python
import numpy as np

# Paramètres
dt = 0.05   # pas d'intégration unifié avec Kalman (20 Hz)
N = int(20 / dt)
t = np.linspace(0, 20, N)
Y_max, Y_c = 10.0, 5.0
e_ref = Y_c  # normalisation

# Réglage : t_stable cible = 2s < t_rupture_exact = 3.66s
t_stable_cible = 2.0
Kp = 8 / t_stable_cible   # = 4.0
Ki = Kp**2 / 4             # = 4.0 (régime critique)

# État initial
y, I_e = 0.0, 0.0
traj_y, traj_e, traj_V = [], [], []

for k in range(N):
    z_k = 2 + np.sin(t[k]) + np.cos(t[k])
    f_dot = 1 / (1 + t[k]**2)

    e_k = y - Y_c
    e_bar = e_k / e_ref          # erreur normalisée
    I_e += e_bar * dt

    u_k = (Kp * e_bar + Ki * I_e) * e_ref

    dy = f_dot + z_k - u_k
    y += dy * dt

    # Lyapunov V = e²/2 + (Ki/2)·I²  (coefficient correct — annule les termes croisés)
    V = 0.5 * e_k**2 + (Ki / 2) * (I_e * e_ref)**2

    traj_y.append(y)
    traj_e.append(e_k)
    traj_V.append(V)

# Vérifier : y reste sous Y_max, V décroît, |e| → bande résiduelle
```

### Priorité 3 — Validation Kalman et convergence P∞

```python
import numpy as np

# Paramètres Kalman
dt = 0.05
sigma_v = 0.1    # bruit de mesure
sigma_a = 0.5    # nervosité de z

Q = sigma_a**2 * np.array([[dt**4/4, dt**3/2],
                             [dt**3/2, dt**2]])
R = sigma_v**2
H = np.array([[1, 0]])

# État et covariance initiaux
x_hat = np.array([0.0, 2.0])  # [y, z]
P = np.eye(2) * 5.0
A = np.array([[1, dt], [0, 1]])

P_hist = []
for k in range(500):
    # Prédiction
    x_pred = A @ x_hat
    P_pred = A @ P @ A.T + Q

    # Innovation et gain
    nu = y_mesure[k] - H @ x_pred   # y_mesure à fournir
    S = H @ P_pred @ H.T + R
    G = P_pred @ H.T / S

    # Correction
    x_hat = x_pred + G.flatten() * nu
    P = (np.eye(2) - np.outer(G.flatten(), H)) @ P_pred

    P_hist.append(P[0, 0])

# Vérifier convergence vers P_inf ≈ 0.4316
```

### Priorité 4 — Auto-adaptation v1.2 (lois gradient)

```python
# Comparaison heuristique vs gradient sur changement de régime brutal (z double à t=10s)
# Métriques : V(t), Kp(t), Ki(t), erreur résiduelle
```

### Priorité 5 — Kalman adaptatif v1.3

```python
# Vérifier que P_k reste borné, Q_hat et R_hat convergent
# Tester sur signal avec bruit non-stationnaire (bruit qui double à t=10s)
```

---

## 7. Analyse de la couche Auto-Adaptive (v1.2)

### 7.1 Lois d'adaptation — Version corrigée v2.0

**Erreur normalisée (obligatoire) :**

$$\bar{e}(t) = \frac{e(t)}{e_{\text{ref}}}$$

**Lois gradient (recommandées en production)  :**

$$\dot{K}_p(t) = \gamma_p \cdot \bar{e}^2(t)$$

$$\dot{K}_i(t) = \gamma_i \cdot \bar{e}(t) \cdot \int_0^t \bar{e}(\tau)\,d\tau$$

**Lois heuristiques (prototypage uniquement)  :**

$$\dot{K}_p(t) = \gamma_p \cdot (|\bar{e}(t)| - \theta)$$

$$\dot{K}_i(t) = \gamma_i \cdot |\bar{e}(t)| \cdot \text{sgn}\left(\int_0^t \bar{e}(\tau)\,d\tau\right)$$

### 7.2 Points d'attention critiques

**Stabilité :** Les lois gradient sont prouvées stables par Lyapunov (voir
`reponses_critiques.md` Critique 1). Les lois heuristiques sont documentées
comme heuristiques non prouvées.

**Saturation impérative :**

$$K_p \in [K_{p,\min},\ K_{p,\max}], \quad K_i \in [K_{i,\min},\ K_{i,\max}]$$

**Choix des learning rates :** γp et γi sont sans dimension après normalisation.
Point de départ recommandé : γp ∈ [0,1 ; 1,0], γi ∈ [0,05 ; 0,5].
Trop grands → oscillations des gains. Trop petits → adaptation trop lente.

### 7.3 Pipeline complet v1.2 

```
y_mesuré(k)
    │
    ▼
[Kalman] ──→ ŷk, ẑk
    │
    ├──→ t_rupture = (Y_max − ŷk) / ẑk  [alarme si t_rupture < seuil]
    │
    ▼
ēk = (ŷk − Yc) / e_ref
    │
    ├──→ [Auto-tuning gradient] : Kp(k+1) = sat(Kp(k) + γp·ēk²·dt)
    │                             Ki(k+1) = sat(Ki(k) + γi·ēk·Ik·dt)
    │
    ▼
u_k = [Kp(k)·ēk + Ki(k)·Ik] · e_ref
    │
    ▼
système physique → y(k+1)
```

---

## 8. Analyse de la v1.3 — Chameleon RETA

### 8.1 Principe

Les versions précédentes adaptaient l'**action** (Kp, Ki) mais laissaient la
**perception** (Q, R du filtre Kalman) fixes. La v1.3 ferme la dernière boucle :
le filtre se recalibre en observant ses propres erreurs de prédiction (l'innovation νk).

### 8.2 Innovation νk — signal de diagnostic central 

$$\nu_k = y_{\text{mesuré},k} - H\hat{x}_{k|k-1}$$

En régime normal, νk doit être un bruit blanc de moyenne nulle.

| Symptôme sur νk | Interprétation | Action corrective |
|---|---|---|
| Variance(νk) augmente | Capteur plus bruité | Augmenter R |
| νk biaisé (moyenne ≠ 0) | Modèle RETA dévie | Augmenter Q |
| νk trop petite | R sous-estimé, filtre rigide | Diminuer R |

### 8.3 Lois d'adaptation des matrices 

**Adaptation de R :**

$$\hat{R}_k = \alpha \hat{R}_{k-1} + (1-\alpha)(\nu_k \nu_k^T + H P_{k|k-1} H^T)$$

**Adaptation de Q :**

$$\hat{Q}_k = \beta \hat{Q}_{k-1} + (1-\beta)(G_k \nu_k \nu_k^T G_k^T)$$

**Facteurs d'oubli recommandés :** α ∈ [0,95 ; 0,99], β ∈ [0,90 ; 0,98].

### 8.4 Points d'attention v1.3 

**Convergence de Pk non garantie :** Avec Q et R dynamiques, le filtre devient
un AKF (Adaptive Kalman Filter). Vérifier empiriquement que Pk reste borné.

**Période de chauffe :** Définir une période de warm-up (≥ 50 pas) avant
d'activer les alarmes t_rupture.

**Interactions entre les 4 paramètres adaptatifs :** Q↑ → ẑ volatile →
t_rupture instable → Kp réagit → ... Surveiller les cycles parasites en simulation.

**Choix de α et β :** Paramètres les plus sensibles de v1.3.
α proche de 1 = mémoire longue (lent). α proche de 0 = réactif mais instable.

### 8.5 Cycle complet v1.3 

```
y_mesuré(k)
    │
    ▼
νk = y_mesuré − H·x̂_pred
    ├──→ [Adapter R̂k]  : R̂k = α·R̂(k-1) + (1-α)·(νk·νkᵀ + H·Pk|k-1·Hᵀ)
    └──→ [Adapter Q̂k]  : Q̂k = β·Q̂(k-1) + (1-β)·(Gk·νk·νkᵀ·Gkᵀ)
    │
    ▼
[Kalman(Q̂k, R̂k)] → ŷk, ẑk
    │
    ├──→ t_rupture = (Y_max − ŷk) / ẑk  [alarme si t_rupture < seuil, après warm-up]
    │
    ▼
ēk = (ŷk − Yc) / e_ref
    │
    ├──→ [Auto-tuning gradient] → Kp(k+1), Ki(k+1)
    │
    ▼
u_k = [Kp(k)·ēk + Ki(k)·Ik] · e_ref
    │
    ▼
système physique → y(k+1)
```

---

## 9. Synthèse des versions 

| Version | Nom | Gains PI | Kalman Q, R | Déploiement |
|---|---|---|---|---|
| v1.0 | RETA Pur | Fixes | Sans Kalman | Paramétrage manuel complet |
| v1.1 | RETA-Kalman | Fixes | Fixes | Q, R manuels |
| v1.2 | Adaptive RETA | Auto-adaptatifs gradient (γp, γi, e_ref) | Fixes | Q, R manuels |
| v1.3 | Chameleon RETA | Auto-adaptatifs | Auto-adaptatifs (α, β) | Zéro-config après warm-up |

**Progression de l'autonomie :** v1.0 demande tout → v1.3 ne demande que
Y_max, Yc, e_ref, α, β (et une période de warm-up).

---

## Annexe — Résumé des corrections v2.0

| Section | Problème v1.x | Correction v2.0 |
|---|---|---|
| §3.2 | Borne conservative présentée sans avertissement | Avertissement facteur ~4, usage limité à certification |
| §5.3 | Terme Ki·eI·(1−Kp)/Kp absent de V̇ | Forme correcte documentée |
| §7.1 | Lois d'adaptation sans normalisation | Erreur normalisée ē = e/e_ref introduite |
| §7.1 | γp, γi avec problème de dimensions | Résolu par normalisation |
| §8.5 | Cycle v1.3 sans mention warm-up | Période de chauffe ajoutée explicitement |
| Numérotation | Section 7 manquante dans v1.x | Numérotation continue 1→9 |

---
*Analyse basée sur theorie_fondamentale.md v2.0*

---

**📂 Section 1 — Fondamentaux**
[Théorie Fondamentale](theorie_fondamentale.md) · [Analyse Complète](analyse_complete.md) · [Réponses aux Critiques](reponses_critiques.md) · [Démonstration v1.3](reta_v13_demonstration.md)

**🔗 Voir aussi** : [Extension Dimensionnelle](../2_extensions_theoriques/extension_dimensionnelle.md) · [Logique Probabiliste](../2_extensions_theoriques/logique_probabiliste.md)

---

[📖 Index de la Documentation](../INDEX.md) · [🏠 Accueil du Projet](../../README.md)