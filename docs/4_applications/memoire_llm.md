# RETA — Mémoire LLM par Navigation Dimensionnelle (v2.0 — usage requalifié)
*Compression de contexte et changement de référentiel sans surcoût en tokens*

> ## ⚠️ Avertissement de portée (v2.0 — Critique 11, `reponses_critiques.md`)
>
> **Ce document contenait une erreur de fond, corrigée ici.** Les versions antérieures
> affirmaient qu'un LLM avec "mémoire RETA" pouvait reconstruire l'intégralité du
> contenu d'une conversation passée **sans relire un seul token**, avec une erreur
> bornée par une variance Kalman constante $P_\infty$.
>
> **C'est faux pour du texte libre.** Le filtre de Kalman utilisé a un état à 2 degrés
> de liberté $[z,\dot z]$ ; il ne peut reconstruire que ce qui est observable dans un
> système linéaire à 2 dimensions. Un tour de conversation porte potentiellement des
> milliers de bits d'information non redondante (faits, noms, contraintes numériques).
> Une signature de 15 tokens ne peut pas les contenir — ce serait une violation de
> borne de Shannon, pas une compression sans perte. Le facteur de gain annoncé
> (2020×, voir `../3_technique/efficience_memoire.md`) est arithmétiquement correct
> **étant donné les hypothèses**, mais les hypothèses supposent implicitement que le
> contenu réel est bas-dimensionnel — ce qui n'est pas démontré et n'est vrai pour
> aucune conversation en langage libre.
>
> **Ce qui reste valide, reformulé ci-dessous (§9) :** utiliser RETA pour **détecter
> une dérive thématique** (une métrique scalaire ou bas-dimensionnelle explicite,
> comme dans `../6_domaines_application/ia_llm.md` §1) est une application légitime.
> Utiliser RETA pour **reconstruire le contenu exact** d'un tour passé sans le stocker
> ne l'est pas. Le reste de ce document (§1-8) est conservé tel quel **à titre
> d'archive de l'erreur d'origine** — chaque affirmation de reconstruction fidèle
> doit être lue avec cette réserve.
>
> Voir `../2_extensions_theoriques/reta_nd_dispersion.md` §5 pour la dérivation
> complète, et §9 ci-dessous pour la reformulation honnête de cette application.

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

## 9. Reformulation Honnête (v2.0) — Ce que RETA-LLM peut réellement faire

Les sections 1-8 ci-dessus décrivent une **architecture de compression avec
reconstruction fidèle**, qui ne tient pas (Critique 11). Voici la version qui tient :

### 9.1 Usage valide : détection de dérive, pas reconstruction

RETA reste utile pour suivre une **métrique scalaire ou bas-dimensionnelle explicite**
de la conversation — pas pour encoder son contenu intégral :

$$y(t) = \text{distance sémantique au sujet initial (ex. : 1 − similarité cosine)}$$

$$z(t) = \text{taux de dérive par tour}, \qquad t_{\text{rupture}} = \text{tour où } y(t) > Y_{max}$$

C'est exactement l'usage documenté dans `../6_domaines_application/ia_llm.md` §1, à
condition d'en retirer l'affirmation de reconstruction exacte (voir la correction
apportée à ce fichier).

### 9.2 Ce qui reste stocké : rien de plus qu'un signal de surveillance

| Ce que RETA-LLM peut fournir | Ce qu'il ne peut pas fournir |
|---|---|
| Une alerte de dérive thématique avant qu'elle devienne incohérente | Le contenu exact d'un tour passé non stocké par ailleurs |
| Un score de dérive comportementale (alignement, cf. §4 de `ia_llm.md`) | Une compression sans perte du texte de la conversation |
| Une mesure de dimension effective $n_{\text{eff}}$ de l'espace d'embedding (cf. `reta_nd_dispersion.md` §5.2) pour calibrer les seuils d'alerte | Une "fenêtre de contexte infinie à coût constant" |

### 9.3 Piste de validation

Avant toute réutilisation de ce document pour une implémentation réelle : mesurer
$n_{\text{eff}}$ sur des embeddings réels de conversation, et vérifier si le taux de
dérive observé est cohérent avec $n_{\text{eff}} \cdot D \cdot t$ (loi de dispersion,
`reta_nd_dispersion.md` §1). Voir `../6_domaines_application/ia_llm_drift_monitoring.md`
pour la version applicative complète de cette reformulation.

---

**📂 Section 4 — Applications**
[Index](index.md) · [Mémoire LLM](memoire_llm.md)

**🔗 Voir aussi** : [Efficience Mémoire](../3_technique/efficience_memoire.md) · [Extension Dimensionnelle](../2_extensions_theoriques/extension_dimensionnelle.md) · [Réponses aux Critiques](../1_fondamentaux/reponses_critiques.md)

---

[📖 Index de la Documentation](../INDEX.md) · [🏠 Accueil du Projet](../../README.md)
