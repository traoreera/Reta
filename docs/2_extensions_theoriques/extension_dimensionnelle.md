# RETA — Extension Dimensionnelle Bidirectionnelle
*Expansion ℝⁿ → ℝⁿ⁺ᵏ et contraction ℝⁿ → ℝⁿ⁻ᵏ par perturbations persistantes*

---

## 1. Principe Fondamental

La théorie RETA (décrite dans `../1_fondamentaux/theorie_fondamentale.md`) établit qu'un système borné en 1D échappe à ses limites sous perturbation persistante. Ce document généralise ce mécanisme à n dimensions et introduit la **procédure inverse par substitution**.

**Définition 1 (Expansion dimensionnelle) :**
Soit $y_1 \in C(\mathbb{R}^+)$ un signal unidimensionnel — par exemple $y_1(t) = \arctan(t)$. On appelle **expansion dimensionnelle par la perturbation** $z_i$ l'opération :

$$T_{z_i} : y_i \mapsto y_{i+1}, \quad y_{i+1}(t) = y_i(t) + \int_0^t z_i(\tau)\,d\tau$$

L'opérateur $T_{z_i}$ est une translation non-linéaire dans l'espace des fonctions intégrables. La famille $\{T_{z_i}\}_{i=1}^k$ est commutative : $T_{z_i} \circ T_{z_j} = T_{z_j} \circ T_{z_i}$ pour $i \neq j$.

**Définition 2 (Contraction par substitution) :**
Soit $\hat{z}_i$ une estimation de $z_i$ (par mesure directe ou filtre de Kalman). On appelle **contraction dimensionnelle** l'opération inverse :

$$T_{\hat{z}_i}^{-1} : y_{i+1} \mapsto \hat{y}_i, \quad \hat{y}_i(t) = y_{i+1}(t) - \int_0^t \hat{z}_i(\tau)\,d\tau$$

La contraction est exacte ($\hat{y}_i = y_i$) si $\hat{z}_i = z_i$ p.p. L'erreur de reconstruction est bornée par $\|z_i - \hat{z}_i\|_{L^1}$, elle-même majorée par la variance du filtre de Kalman.

**Lemme 1 (Espace effectif) :**
Un système en ℝⁿ soumis à $k$ perturbations persistantes $z_i(t) \geq \varepsilon_i > 0$ indépendantes évolue dans un espace de dimension $n + k$ au sens où $y_{n+k}(t) = y_n(t) + \sum_{i=1}^k \int_0^t z_i(\tau)\,d\tau$ n'est pas borné dans ℝⁿ (aucune fonction de Lyapunov ne peut le confiner dans une boule de ℝⁿ pour $t \to \infty$).

---

## 2. L'Expansion Dimensionnelle (ℝ¹ → ℝⁿ)

### 2.1 Mécanisme

Chaque perturbation persistante z_i(t) ≥ εᵢ > 0 **ouvre une nouvelle dimension** :

$$y_1(t) = \underbrace{\arctan(t)}_{\text{base bornée}} + \int_0^t z_1(\tau)\,d\tau$$

$$y_2(t) = y_1(t) + \int_0^t z_2(\tau)\,d\tau$$

$$\vdots$$

$$y_n(t) = y_{n-1}(t) + \int_0^t z_n(\tau)\,d\tau$$

### 2.2 Règle générale

$$\boxed{\mathbb{R}^n + k \text{ perturbations persistantes} \;\rightarrow\; \mathbb{R}^{n+k}}$$

Le coût computationnel de chaque expansion est **O(n)** — une intégrale, pas une multiplication matricielle.

> **Périmètre de validité :** La condition $z_i(t) \geq \varepsilon_i > 0$ est requise pour garantir l'expansion.
> Pour les systèmes où $z_i$ oscille (turbulence, vent avec rafales), la condition affaiblie
> $\bar{z}_i(T) \geq \varepsilon_i$ sur la moyenne temporelle suffit — le t_rupture est alors calculé
> avec la perturbation moyenne $\bar{z}_i$.

**Application au cas nD — Condition affaiblie par dimension :**

Pour un système à $n$ dimensions avec perturbations oscillantes, on définit la moyenne temporelle sur une fenêtre $T$ :

$$\bar{z}_i(T) = \frac{1}{T}\int_0^T z_i(\tau)\,d\tau, \quad i = 1, \ldots, n$$

Le temps de rupture par dimension devient alors :

$$t_{\text{rupture},i} \geq \frac{Y_{\max,i} - \frac{\pi}{2}}{\bar{z}_i(T)}$$

Et la rupture globale au premier dépassement :

$$\boxed{t_{\text{rupture global}} = \min_i\left(\frac{Y_{\max,i} - \frac{\pi}{2}}{\bar{z}_i(T)}\right)}$$

> **Condition suffisante pour la validité :** $\bar{z}_i(T) \geq \varepsilon_i > 0$ pour tout $i$.
> Si une dimension $i_0$ vérifie $\bar{z}_{i_0}(T) \leq 0$, cette dimension est **hors-cadre RETA** :
> la dérive n'est pas persistante et le modèle ne s'applique pas sur cet axe.
> Le système reste analysable sur les $n-1$ autres dimensions.

### 2.3 Table d'expansion

| Perturbation ajoutée | Référentiel atteint | Ce qui émerge |
|---|---|---|
| z₁(t) ≥ ε₁ | ℝ² | trajectoire plane |
| z₂(t) ≥ ε₂ | ℝ³ | volume, profondeur |
| z₃(t) ≥ ε₃ | ℝ⁴ | normale de surface |
| z₄(t) ≥ ε₄ | ℝ⁵ | luminance, couleur |
| z₅(t) ≥ ε₅ | ℝ⁶ | champ de matériaux |

Chaque dimension **n'existe pas avant que sa perturbation ne la force à exister**.

---

## 3. Le Temps de Rupture par Dimension

Chaque dimension i a son propre temps de rupture :

$$t_{\text{rupture},i} \geq \frac{Y_{\max,i} - \frac{\pi}{2}}{\varepsilon_i}$$

La rupture globale du système survient au **minimum** :

$$\boxed{t_{\text{rupture global}} = \min_i\left(t_{\text{rupture},i}\right)}$$

> **Note — Valeur exacte vs borne conservative :**
> La borne $t \geq (Y_{\max} - 1{,}57)/\varepsilon$ est pessimiste par construction.
> Pour $Y_{\max} = 10$, $\varepsilon = 0{,}59$ : borne = **14,28 s**.
> La valeur exacte (Newton-Raphson sur l'équation transcendante) : **t = 3,66 s**.
> La borne sert à la **certification de sécurité** ; la valeur exacte à la **prédiction nominale**.

---

## 4. La Procédure Inverse — Contraction (ℝⁿ → ℝⁿ⁻¹)

### 4.1 Principe de substitution

Si l'expansion est :

$$y_n(t) = y_{n-1}(t) + \int_0^t z_n(\tau)\,d\tau$$

Alors la **contraction par substitution** est :

$$\boxed{y_{n-1}(t) = y_n(t) - \int_0^t \hat{z}_n(\tau)\,d\tau}$$

où $\hat{z}_n$ est l'estimation de la perturbation (exacte ou par Kalman).

### 4.2 Condition de validité physique

La procédure inverse est valide si et seulement si :

1. **Observabilité** : $z_n(t)$ est mesurable ou estimable → filtre de Kalman
2. **Causalité** : $t_{\text{collapse}} < t_{\text{observation}}$ (on agit avant de perdre le signal)
3. **Persistance de la correction** : la force d'annulation $u(t) \geq \varepsilon_{\text{ctrl}} > 0$

Le temps de descente (symétrique au t_rupture) :

$$t_{\text{collapse}} = \frac{y_n^{\text{actuel}} - y_{n-1}^{\text{cible}}}{\varepsilon_{\text{contrôle}}}$$

### 4.3 Chaîne de descente complète

```
ℝ⁵  →  - ∫ẑ₅ dt  →  ℝ⁴   (supprimer luminance)
ℝ⁴  →  - ∫ẑ₄ dt  →  ℝ³   (supprimer normale)
ℝ³  →  - ∫ẑ₃ dt  →  ℝ²   (supprimer profondeur Z)
ℝ²  →  - ∫ẑ₂ dt  →  ℝ¹   (supprimer dérive X)
ℝ¹  →  arctan(t)  →  ℝ¹   (système borné d'origine récupéré)
```

Chaque étape coûte une soustraction et une intégrale — **même complexité que la montée**.

---

## 5. Structure Duale — L'Espace Vectoriel RETA

```
EXPANSION   :  ℝ¹ →+z₁→ ℝ² →+z₂→ ℝ³ →+z₃→ ··· →+zₙ→ ℝⁿ
                    ↕         ↕         ↕              ↕
CONTRACTION :  ℝ¹ ←PI₁← ℝ² ←PI₂← ℝ³ ←PI₃← ··· ←PIₙ← ℝⁿ
```

Le **correcteur PI est l'opérateur de descente dimensionnelle** :

$$u_i(t) = K_p \cdot e_i(t) + K_i \int_0^t e_i(\tau)\,d\tau$$

Il annule la perturbation z_i dans la dimension i, refermant cette dimension sans affecter les autres. Chaque régulateur PI est **local à sa dimension**.

> **Symétrie fondamentale :** Perturbation (montée) et régulation PI (descente)
> sont deux opérations duales sur le même espace. RETA est fermé sous ces deux opérations.

---

## 6. Le Filtre de Kalman comme Opérateur de Substitution

Le Kalman n'est pas seulement un estimateur de bruit — c'est le **mécanisme qui rend la contraction praticable** :

```
Système observé en ℝⁿ
        ↓
Kalman estime ẑₙ(t) avec variance P₀₀
        ↓
Substitution : y_{n-1} = yₙ - ∫ẑₙ dt
        ↓
Erreur de reconstruction ≤ P₀₀  (bornée, quantifiée)
        ↓
Retour en ℝⁿ⁻¹ avec précision garantie
```

La variance Kalman P₀₀ devient l'**erreur maximale de reconstruction dimensionnelle**.
Quand P₀₀ → 0 (Kalman convergé), la contraction est exacte.

---

## 7. Applications de la Symétrie Expansion/Contraction

### 7.1 Rendu graphique O(k·n) au lieu de O(n²)

```python
def reta_render(t, perturbations, consignes, kp, ki, dt):
    """
    Construit un point en ℝᵏ depuis ℝ¹ par k perturbations successives.
    Complexité : O(k) par frame — pas de matrice.
    """
    y = math.atan(t)   # base bornée ℝ¹
    coords = []
    ie = 0.0
    for z_i, c_i in zip(perturbations, consignes):
        e   = y - c_i
        ie += e * dt
        u   = kp*e + ki*ie     # PI : maintient dans le référentiel
        y  += (z_i - u) * dt   # perturbation nette
        coords.append(y)
    return coords              # [x, y, z, normale, luminance, ...]
```

**Niveau de détail naturel** : une dimension n'est rendue que si sa perturbation z_i est active.
Hors champ → pas de perturbation → pas de calcul.

### 7.2 Compression de signal nD → kD

Un signal en ℝⁿ mesuré peut être représenté par :
- k scalaires εᵢ (amplitudes des perturbations dominantes)
- k temps de rupture t_{rupture,i}
- 1 système de base arctan(t)

Reconstruction exacte si Kalman est convergé. **Compression causale avec garantie d'erreur**.

### 7.3 Physique — Analogie avec le Groupe de Renormalisation

Le groupe de renormalisation en physique quantique intègre les degrés de liberté haute énergie pour obtenir une **théorie effective en dimension inférieure**. RETA présente une analogie structurelle (intégration/soustraction d'une dimension), mais **ce n'est pas une équivalence formelle** — le groupe de renormalisation opère sur des champs quantiques via des intégrales de chemin, tandis que RETA opère sur des signaux déterministes via des intégrales de Riemann.

| Groupe de renormalisation (analogie) | RETA |
|---|---|
| Intégrer les modes haute énergie | Soustraire ∫ẑₙ dt |
| Théorie effective à basse énergie | Système en ℝⁿ⁻¹ |
| Point fixe du groupe | Système borné arctan(t) |
| Couplages résiduels | Variance Kalman P₀₀ |

> **Note :** Il s'agit d'une analogie conceptuelle, pas d'une dérivation mathématique. Les deux formalismes partagent l'idée de réduction dimensionnelle par intégration, mais les mécanismes sous-jacents sont distincts.

### 7.4 Intelligence Artificielle — Réduction d'embedding

Un embedding LLM en ℝ⁵¹² peut être réduit à ℝᵏ (k ≪ 512) en identifiant les k directions de dérive persistante (les k perturbations dominantes) et en les soustrayant séquentiellement.

Différence avec l'ACP classique :
- ACP : optimise la variance globale, pas de sens causal
- RETA : chaque direction supprimée a un **temps de rupture** et une **force de perturbation** physiquement interprétables

---

## 8. Théorème de Réversibilité RETA

**Théorème 1 (Réversibilité) :**
Soit $y_n(t) = f(t) + \sum_{i=1}^n \int_0^t z_i(\tau)\,d\tau$ où $f \in C^1$ vérifie $\lim_{t\to\infty} f(t) < \infty$ et $z_i(t) \geq \varepsilon_i > 0$ pour $i = 1,\ldots,n$. Alors pour tout $k \leq n$, il existe une procédure de contraction $C_k$ telle que :

$$C_k(y_n) = y_n - \sum_{i=n-k+1}^n \int_0^t \hat{z}_i(\tau)\,d\tau = y_{n-k} + \sum_{i=n-k+1}^n \int_0^t (z_i - \hat{z}_i)(\tau)\,d\tau$$

avec les propriétés suivantes :

1. **Convergence :** Si $\hat{z}_i$ est fourni par un filtre de Kalman convergé ($P_{00,i} \to 0$ quand $t \to \infty$), alors $\|C_k(y_n) - y_{n-k}\|_\infty \to 0$.
2. **Borne d'erreur :** Pour un horizon fini $T$, l'erreur de reconstruction vérifie :
   $$\bigl\|C_k(y_n) - y_{n-k}\bigr\|_{L^\infty[0,T]} \leq \sum_{i=n-k+1}^n \sqrt{T \cdot P_{00,i}}$$
3. **Complexité :** Chaque contraction coûte une soustraction et une intégration ($O(1)$ par pas de temps). La famille $\{C_k\}_{k=1}^n$ est commutative.
4. **Condition suffisante de contraction exacte :** Si $P_{00,i} = 0$ pour tout $i > n-k$, alors $C_k(y_n) = y_{n-k}$ presque partout.

---

## 9. Résumé Opérationnel

| Opération | Formule | Coût | Condition |
|---|---|---|---|
| Ouvrir dimension i | $y_i = y_{i-1} + \int z_i\,dt$ | O(n) | $z_i \geq \varepsilon > 0$ |
| Fermer dimension i | $y_{i-1} = y_i - \int \hat{z}_i\,dt$ | O(n) | $\hat{z}_i$ observable |
| Temps d'ouverture | $t_{\text{rup}} \geq (Y_{\max} - 1{,}57)/\varepsilon$ | O(1) | borne conservative |
| Temps d'ouverture exact | Newton-Raphson sur équation transcendante | O(iter) | solution nominale |
| Temps de fermeture | $t_{\text{col}} = \Delta y / \varepsilon_{\text{ctrl}}$ | O(1) | symétrique |
| Erreur résiduelle | $\leq P_{00}$ Kalman | — | Kalman convergé |

---

*Ce document étend `../1_fondamentaux/theorie_fondamentale.md` vers la généralisation n-dimensionnelle.*
*La théorie de base (système canonique, PI, trois temps caractéristiques) reste inchangée.*

---
## 🧭 Navigation
- [📖 Index de la Documentation](../INDEX.md)
- [🏠 Accueil du Projet](../../README.md)
