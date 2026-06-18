# RETA — Mémoire LLM par Navigation Dimensionnelle
*Compression de contexte et changement de référentiel sans surcoût en tokens*

---

## 1. Le Problème Actuel

### 1.1 La mémoire LLM classique croît sans limite

```
Tour 1 : [token₁...tokenₙ]
Tour 2 : [token₁...tokenₙ] + [tour 2]
Tour 3 : [token₁...tokenₙ] + [tour 2] + [tour 3]
...
Tour k : reduplique tout le passé
```

**Coût : O(n × k)** — chaque échange reduplique l'intégralité du contexte précédent.

Conséquences :
- Fenêtre de contexte saturée en O(k) tours
- Tokens consommés pour du contenu déjà traité
- Aucune garantie de fidélité sur le contenu rappelé
- Pas de navigation : tout ou rien

### 1.2 Ce que ça coûte réellement

| Éléments stockés | Méthode classique | Ce qui est utile |
|---|---|---|
| Intention initiale | Retokenisée à chaque tour | 1 fois suffit |
| Faits établis | Répétés intégralement | Seules les deltas comptent |
| Ton/style | Redécrit implicitement | 1 paramètre suffit |
| Contexte temporel | Re-inféré | 1 horodatage suffit |

---

## 2. La Conversation comme Système RETA

### 2.1 Modélisation — Deux Opérateurs Duaux

Chaque tour de conversation applique **l'un de deux opérateurs** :

```
Tour 0  →  intention initiale  =  arctan(t)             [borné, ℝ¹]
Tour 1  →  + ∫z₁ dτ   question (EXPANSION)              [ℝ²]
Tour 2  →  + ∫z₂ dτ   réponse enrichie (EXPANSION)      [ℝ³]
Tour 3  →  − ∫u₃ dτ   correction/contradiction (PI)     [ℝ³ → referme dérive]
Tour 4  →  + ∫z₄ dτ   nouveau contexte (EXPANSION)      [ℝ⁴]
  ...
Tour k  →  état courant yₖ                              [ℝᵏ effectif]
```

| Type de tour | Opération RETA | Formule | Effet |
|---|---|---|---|
| Question, ajout de contexte | Expansion | +∫zₖ dτ | Ouvre ℝᵏ |
| Correction, contradiction | Contraction (PI) | −∫uₖ dτ | Referme la dérive |
| Confirmation, accord | Stabilisation | Δy → 0 | Maintient le référentiel |

Un tour correctif n'est pas une perturbation — c'est un **régulateur PI** qui
annule la dérive sémantique de l'erreur précédente. Le stockage reste identique :
une signature compacte (εctrl, forme de u), même coût qu'une signature d'expansion.

Formellement :

$$y_k(t) = \arctan(t) + \sum_{i=1}^{k} \int_0^t z_i(\tau)\,d\tau$$

### 2.2 Ce qu'il faut stocker

Le produit final $y_k$ contient **toute l'information** des k tours précédents.
Il suffit de stocker :

```
État courant   yₖ           →  1 vecteur (dimension fixe)
Perturbation   z₁(t)        →  1 signature compacte (εᵢ + forme)
Perturbation   z₂(t)        →  1 signature compacte
               ...
Perturbation   zₖ(t)        →  1 signature compacte
```

**Coût total : O(n + k)** au lieu de **O(n × k)**

---

## 3. La Procédure Inverse — Retrouver un État Passé

### 3.1 Descente par substitution

Pour retrouver l'état au tour j depuis l'état courant au tour k :

$$\boxed{y_j = y_k - \sum_{i=j+1}^{k} \int_0^t \hat{z}_i(\tau)\,d\tau}$$

Chaque soustraction coûte **une intégrale** — pas une relecture de tokens.

### 3.2 Le Filtre de Kalman comme substitut de la relecture

Le filtre de Kalman **reconstruit** chaque perturbation $\hat{z}_i$ depuis les effets
observables dans l'état courant $y_k$, sans accéder aux tokens d'origine :

```
État courant yₖ observé
        ↓
Kalman estime ẑᵢ(t) pour chaque tour i
        ↓
Erreur de reconstruction ≤ P₀₀ Kalman  (bornée, quantifiée)
        ↓
État passé yⱼ reconstruit sans relire un seul token
```

**P₀₀ → 0** quand Kalman converge : reconstruction exacte.

### 3.3 Temps de descente

Symétrique au temps de rupture, le temps de reconstruction est :

$$t_{\text{collapse}} = \frac{y_k^{\text{actuel}} - y_j^{\text{cible}}}{\varepsilon_{\text{contrôle}}}$$

Fini, garanti, indépendant de k.

---

## 4. Navigation par Référentiel

### 4.1 Chaque référentiel est un niveau de la conversation

```
ℝ⁵  →  contexte complet
         (sujet + faits + ton + temporel + modèle utilisateur)

ℝ⁴  →  sans modèle utilisateur

ℝ³  →  faits bruts uniquement

ℝ²  →  sujet + intention

ℝ¹  →  intention initiale pure     ←  point zéro, coût nul
```

### 4.2 Changer de référentiel = choisir sa profondeur de mémoire

Pour répondre sur les **faits seuls** (ℝ³) :
→ Soustraire les dimensions 4 et 5, garder les 3 premières.

Pour retrouver l'**intention initiale** (ℝ¹) :
→ Descente complète par substitution jusqu'à arctan(t).

Pour le **contexte complet** (ℝ⁵) :
→ Remonter par expansion depuis le niveau voulu.

Le modèle ne stocke pas les états intermédiaires —
il stocke les **règles de transition entre référentiels**.

### 4.3 Structure duale

```
EXPANSION   :  ℝ¹ →+z₁→ ℝ² →+z₂→ ℝ³ →+z₃→ ··· →+zₖ→ ℝᵏ
                    ↕         ↕         ↕              ↕
CONTRACTION :  ℝ¹ ←PI₁← ℝ² ←PI₂← ℝ³ ←PI₃← ··· ←PIₖ← ℝᵏ

Montée   =  nouveau tour de conversation  (perturbation)
Descente =  rappel mémoire               (régulateur PI)
```

---

## 5. Comparaison Formelle

| Propriété | Mémoire classique | Mémoire RETA |
|---|---|---|
| **Coût stockage** | O(n × k) | O(n + k) |
| **Retrouver tour j** | Relire depuis le début | k−j soustractions |
| **Fidélité** | Dégradée par troncature | Erreur ≤ P₀₀ (bornée) |
| **Fenêtre contexte** | Limitée, sature | Infinie en théorie |
| **Navigation** | Impossible | Par référentiel |
| **Coût par tour** | Croissant | Constant |
| **Granularité** | Tout ou rien | Dimension par dimension |

---

## 6. Architecture Formelle d'un LLM avec Mémoire RETA

```
┌─────────────────────────────────────────────────────────┐
│                   ÉTAT COURANT  yₖ                      │
│              (vecteur de dimension fixe)                 │
└────────────────────────┬────────────────────────────────┘
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
    Kalman dim 1   Kalman dim 2   Kalman dim k
    estime ẑ₁     estime ẑ₂     estime ẑₖ
          │              │              │
          └──────────────┼──────────────┘
                         │
                  Opérateur PI
              (descente dimensionnelle)
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
         ℝ¹             ℝʲ             ℝᵏ
    (intention)   (tour voulu)   (contexte complet)
```

**Composants nécessaires :**

1. **État courant compressé** `yₖ` — vecteur de dimension fixe, mis à jour à chaque tour
2. **k signatures de perturbation** — une par tour, très compactes (εᵢ, forme, horodatage)
3. **Un Kalman par dimension** — reconstruit zᵢ depuis les effets observables dans yₖ
4. **Un opérateur de descente PI** — navigue vers n'importe quel référentiel passé

---

## 7. Implication Clé

> **Un LLM avec mémoire RETA n'a pas besoin de relire ses tokens passés.**
>
> Le produit final (état courant) contient l'intégralité de l'information
> sous forme compressée. Le filtre de Kalman reconstruit chaque couche passée
> depuis les perturbations estimées, avec une erreur bornée par P₀₀.
>
> La fenêtre de contexte devient théoriquement infinie :
> chaque nouveau tour coûte **une perturbation** (O(1)),
> pas une duplication du passé (O(k)).

---

## 8. Lien avec RETA Dimensionnel

Ce document s'appuie sur :
- `../1_fondamentaux/theorie_fondamentale.md` — théorie de base (système canonique, rupture, PI)
- `../2_extensions_theoriques/extension_dimensionnelle.md` — généralisation nD, procédure inverse, théorème de réversibilité

La mémoire LLM est une **instance applicative** de la contraction dimensionnelle :
chaque tour de conversation est une perturbation persistante,
chaque rappel mémoire est une descente par substitution Kalman.

---

*Cette architecture n'existe pas encore comme implémentation explicite.*
*RETA fournit le cadre théorique — la fenêtre de contexte infinie à coût constant par tour.*

---
## 🧭 Navigation
- [📖 Index de la Documentation](../INDEX.md)
- [🏠 Accueil du Projet](../../README.md)
