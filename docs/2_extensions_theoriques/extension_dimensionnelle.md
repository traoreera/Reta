# RETA — Extension Dimensionnelle Bidirectionnelle (v2.0)
*Expansion ℝⁿ → ℝⁿ⁺ᵏ et contraction ℝⁿ → ℝⁿ⁻ᵏ par perturbations persistantes*

> **Corrections v2.0 :**
> 1. Distinction explicite entre dimension physique `n` et composantes actives `k` (→ corrige la confusion « métaphore vs algèbre », voir note §1).
> 2. Régime stochastique ajouté : quand le bruit résiduel n'est pas négligeable, le temps de rupture global n'est pas `min_i(t_rupture,i)` mais le premier passage d'un processus de Bessel(`n`) (→ corrige le biais optimiste sous bruit isotrope, voir §3).
> 3. Bornes et périmètre de validité clarifiés pour chaque régime.

---

## 1. Principe Fondamental

La théorie RETA (décrite dans `../1_fondamentaux/theorie_fondamentale.md`) établit qu'un système borné en 1D échappe à ses limites sous perturbation persistante. Ce document généralise ce mécanisme à n dimensions et introduit la **procédure inverse par substitution**.

**Définition 1 (Expansion dimensionnelle — sens info-géométrique) :**
Soit $y_1 \in C(\mathbb{R}^+)$ un signal unidimensionnel — par exemple $y_1(t) = \arctan(t)$. On appelle **expansion dimensionnelle par la perturbation** $z_i$ l'opération :

$$T_{z_i} : y_i \mapsto y_{i+1}, \quad y_{i+1}(t) = y_i(t) + \int_0^t z_i(\tau)\,d\tau$$

L'opérateur $T_{z_i}$ est une translation non-linéaire dans l'espace des fonctions intégrables. La famille $\{T_{z_i}\}_{i=1}^k$ est commutative : $T_{z_i} \circ T_{z_j} = T_{z_j} \circ T_{z_i}$ pour $i \neq j$.

> **⚠️ Précision terminologique (correction v2.0) :** Ici, « dimension » désigne une **composante fonctionnelle active** dans l'espace des signaux, pas une dimension physique de l'espace ambiant. Un drone a toujours 3 axes physiques (roll, pitch, yaw), mais si une perturbation $z_i(t) \geq \varepsilon_i$ n'est présente que sur 2 axes, alors $k=2$ composantes sont actives alors que $n=3$ dimensions physiques existent. Le Lemme 1 ci-dessous utilise $k$ pour les composantes actives, $n$ pour la dimension physique fixe. Les deux ne sont pas interchangeables.

**Définition 2 (Contraction par substitution) :**
Soit $\hat{z}_i$ une estimation de $z_i$ (par mesure directe ou filtre de Kalman). On appelle **contraction dimensionnelle** l'opération inverse :

$$T_{\hat{z}_i}^{-1} : y_{i+1} \mapsto \hat{y}_i, \quad \hat{y}_i(t) = y_{i+1}(t) - \int_0^t \hat{z}_i(\tau)\,d\tau$$

La contraction est exacte ($\hat{y}_i = y_i$) si $\hat{z}_i = z_i$ p.p. L'erreur de reconstruction est bornée par $\|z_i - \hat{z}_i\|_{L^1}$, elle-même majorée par la variance du filtre de Kalman.

**Lemme 1 (Espace effectif — distinguer $n$ et $k$) :**
Soit $n$ le nombre de dimensions physiques du système (fixe), et $k \leq n$ le nombre de composantes où une perturbation $z_i(t) \geq \varepsilon_i > 0$ est active. Alors le système évolue dans un espace de **rang effectif** $n$, dont $k$ directions sont non-bornées :

$$y_{n}(t) = y_{n-k}(t) + \sum_{i=1}^k \int_0^t z_i(\tau)\,d\tau \notin B_{Y_{\max}} \text{ pour } t \to \infty$$

Aucune fonction de Lyapunov ne peut confiner le système dans une boule de ℝⁿ si $k \geq 1$. Le cas $k = n$ redonne la version originale du lemme. **Cette distinction est cruciale** : ajouter une perturbation ne crée pas une nouvelle dimension algébrique (on reste dans ℝⁿ), mais active une direction existante qui devient divergente.

---

## 2. L'Expansion Dimensionnelle (ℝ¹ → ℝⁿ)

### 2.1 Mécanisme

Chaque perturbation persistante z_i(t) ≥ εᵢ > 0 **ouvre une nouvelle dimension** :

$$y_1(t) = \underbrace{\arctan(t)}_{\text{base bornée}} + \int_0^t z_1(\tau)\,d\tau$$

$$y_2(t) = y_1(t) + \int_0^t z_2(\tau)\,d\tau$$

$$\vdots$$

$$y_n(t) = y_{n-1}(t) + \int_0^t z_n(\tau)\,d\tau$$

### 2.2 Règle générale (version corrigée v2.0)

$$\boxed{\text{ℝⁿ avec } k \leq n \text{ perturbations actives} \;\rightarrow\; k \text{ directions divergentes dans ℝⁿ}}$$

Le coût computationnel de chaque expansion est **O(k)** — une intégrale par composante active, pas de multiplication matricielle.

> **Périmètre de validité :** La condition $z_i(t) \geq \varepsilon_i > 0$ est requise pour garantir l'expansion.
> Pour les systèmes où $z_i$ oscille (turbulence, vent avec rafales), la condition affaiblie
> $\bar{z}_i(T) \geq \varepsilon_i$ sur la moyenne temporelle suffit — le t_rupture est alors calculé
> avec la perturbation moyenne $\bar{z}_i$.

**Application au cas nD — Deux régimes :**

La formule de $t_{\text{rupture global}}$ change selon qu'on est en régime déterministe ou stochastique :

| Régime | Condition | Formule de $t_{\text{rupture}}$ |
|--------|-----------|-------------------------------|
| **Déterministe pur** $^\dagger$ | $z_i$ connus exactement, pas de bruit résiduel | $t_{\text{global}} = \min_i\left(\dfrac{Y_{\max,i} - \pi/2}{\bar{z}_i(T)}\right)$ |
| **Stochastique isotrope** $^\ddagger$ | bruit résiduel $\sim \mathcal{N}(0,D)$ par composante | premier passage du processus de Bessel($n$) (cf. §3 ci-dessous) |

> $^\dagger$ La borne $t_{\text{global}} = \min_i$ est correcte quand les $z_i$ sont déterministes et connus exactement. C'est le cas des perturbations modélisées (dérive thermique, inflation, accumulation buffer). Elle est aussi utilisable comme borne conservative grossière dans tous les cas.
>
> $^\ddagger$ Dès qu'une composante stochastique résiduelle persiste (mesure bruitée, Kalman non convergé), le $ \min_i$ sous-estime systématiquement le vrai temps de rupture : la probabilité qu'au moins un axe dépasse son seuil croît avec $n$ (fléau de la dimension appliqué au premier passage). La correction via Bessel($n$) est développée au §3.

**Condition affaiblie classique (déterministe oscillant) :**

Pour une dimension $i$ où $z_i$ oscille mais reste positive en moyenne :

$$t_{\text{rupture},i} \geq \frac{Y_{\max,i} - \frac{\pi}{2}}{\bar{z}_i(T)}, \quad \bar{z}_i(T) = \frac{1}{T}\int_0^T z_i(\tau)\,d\tau$$

> **Condition suffisante :** $\bar{z}_i(T) \geq \varepsilon_i > 0$ pour tout $i$ actif.
> Si une composante $i_0$ vérifie $\bar{z}_{i_0}(T) \leq 0$, cette direction est **hors-cadre RETA** :
> la dérive n'y est pas persistante et le modèle ne s'applique pas sur cet axe.

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

## 3. Le Temps de Rupture par Dimension (v2.0)

Le calcul de $t_{\text{rupture}}$ dépend du régime. Deux cas sont à distinguer.

### 3.1 Régime déterministe (perturbations connues exactement)

Chaque composante active $i$ a son propre temps de rupture :

$$t_{\text{rupture},i} \geq \frac{Y_{\max,i} - \frac{\pi}{2}}{\varepsilon_i}$$

La rupture globale du système survient au **minimum** des composantes actives ($k \leq n$) :

$$\boxed{t_{\text{rupture global}} = \min_{i=1}^k\left(t_{\text{rupture},i}\right)}$$

> **Note — Valeur exacte vs borne conservative :**
> La borne $t \geq (Y_{\max} - 1{,}57)/\varepsilon$ est pessimiste par construction.
> Pour $Y_{\max} = 10$, $\varepsilon = 0{,}59$ : borne = **14,28 s**.
> La valeur exacte (Newton-Raphson sur l'équation transcendante) : **t = 3,66 s**.
> La borne sert à la **certification de sécurité** ; la valeur exacte à la **prédiction nominale**.

### 3.2 Régime stochastique (bruit résiduel isotrope) — correction Bessel

Quand un bruit résiduel $\xi_i(t) \sim \mathcal{N}(0, D)$ s'ajoute indépendamment sur chaque composante, la **norme** $r(t) = \|y(t)\|$ suit un **processus de Bessel** de dimension $n$ :

$$dr = \frac{(n-1)D}{r}\,dt + \|z(t)\|\,dt + \sqrt{2D}\,dW_t$$

Le terme $(n-1)D/r$ est une **force entropique radiale** : purement géométrique (volume de la coquille sphérique en dimension $n$), elle pousse le système vers l'extérieur indépendamment de toute perturbation $z_i$.

Le temps de premier passage de $r(0) = r_0$ à $r = Y_{\max}$ est le véritable $t_{\text{rupture}}$ :

$$\boxed{t_{\text{rupture}}^{\text{Bessel}}(n) = \mathbb{E}\bigl[\inf\{t \geq 0 : r(t) \geq Y_{\max}\}\bigr]}$$

**Propriété fondamentale :** Pour tout $n \geq 2$,

$$\mathbb{E}\bigl[t_{\text{rupture}}^{\text{Bessel}}(n)\bigr] \;<\; \min_{i=1}^n\bigl(\mathbb{E}[t_{\text{rupture},i}]\bigr)$$

L'écart grandit avec $n$. C'est le **fléau de la dimension** appliqué au premier passage : en dimension $n \geq 2$, le système global casse **avant** la plus précoce des ruptures individuelles prédites par axe, parce que la norme累计 plus vite que chaque composante prise isolément.

> **Exemple — Drone 3 axes (v1.3 §6) :** Dans la simulation actuelle, Roll casse à $t=252$s, Pitch à $t=258$s, Yaw à $t=193$s. Le $t_{\text{rupture}}$ réel (norme d'attitude 3D) est **inférieur à 193s** — le minimum des trois est déjà un biais optimiste. La correction Bessel($n=3$) donne la borne correcte.

> **Condition d'application :** Bruits indépendants et de variance comparable entre axes. Si les axes sont corrélés (couplage aérodynamique entre roll et pitch), remplacer $n$ par la **dimension effective** $n_{\text{eff}} = (\operatorname{tr} \Sigma)^2 / \operatorname{tr}(\Sigma^2)$ (participation ratio de la matrice de covariance), avec $n_{\text{eff}} \leq n$. Sans cette correction, la pénalité Bessel surestime l'effet dimensionnel pour des données corrélées.

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
| Activer composante $i$ | $y_i = y_{i-1} + \int z_i\,dt$ | O(k) | $z_i \geq \varepsilon > 0$ |
| Désactiver composante $i$ | $y_{i-1} = y_i - \int \hat{z}_i\,dt$ | O(k) | $\hat{z}_i$ observable |
| $t_{\text{rup}}$ déterministe | $\min_i\bigl((Y_{\max,i} - \pi/2)/\varepsilon_i\bigr)$ | O(1) | $z_i$ connus exactement |
| $t_{\text{rup}}$ stochastique | Premier passage Bessel($n$) | numérique | bruit isotrope |
| $t_{\text{col}}$ | $\Delta y / \varepsilon_{\text{ctrl}}$ | O(1) | symétrique |
| Erreur résiduelle | $\leq P_{00}$ Kalman | — | Kalman convergé |

---

*Ce document étend `../1_fondamentaux/theorie_fondamentale.md` vers la généralisation n-dimensionnelle.*
*La théorie de base (système canonique, PI, trois temps caractéristiques) reste inchangée.*
---

**📂 Section 2 — Extensions Théoriques**
[Extension Dimensionnelle](extension_dimensionnelle.md) · [Logique Probabiliste](logique_probabiliste.md)

**🔗 Voir aussi** : [Théorie Fondamentale](../1_fondamentaux/theorie_fondamentale.md) · [Fusion de Référentiels](../3_technique/fusion_referentiels.md) · [Efficience Mémoire](../3_technique/efficience_memoire.md)

---

[📖 Index de la Documentation](../INDEX.md) · [🏠 Accueil du Projet](../../README.md)
