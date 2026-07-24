# RETA — Efficience du Système de Mémoire (v2.0 — chiffres à lire sous réserve, voir bandeau)
*Analyse quantitative : mémoire classique vs mémoire RETA par navigation dimensionnelle*

> ## ⚠️ Portée des chiffres ci-dessous (v2.0 — Critique 11, `../1_fondamentaux/reponses_critiques.md`)
>
> Tous les gains chiffrés ci-dessous (48× à 31 281×) sont **arithmétiquement corrects
> étant donné les hypothèses n=1000, s=15**. Mais ces hypothèses supposent implicitement
> que le contenu d'un tour de conversation est compressible sans perte dans une
> signature de 15 tokens — ce qui revient à supposer qu'il est engendré par le système
> linéaire-gaussien à 2 états $[z,\dot z]$ utilisé pour le modéliser. Pour du texte
> libre, cette hypothèse est fausse : un tour de 1000 tokens porte potentiellement
> ~17 000 bits d'information ; une signature de 15 tokens en porte ~255. Les chiffres
> de ce document restent utiles pour dimensionner un **signal de dérive scalaire**
> (cf. `../4_applications/memoire_llm.md` §9), pas pour évaluer un système de mémoire
> conversationnelle à reconstruction fidèle. Voir aussi `n_eff` dans
> `../2_extensions_theoriques/reta_nd_dispersion.md` §5.2, qui quantifie l'écart entre
> la dimension du signal réellement suivi (ici 2) et la dimension effective du contenu
> sémantique réel (plusieurs centaines).

---

## 1. Hypothèses de Calcul

| Paramètre | Valeur | Description |
|---|---|---|
| n | 1 000 tokens | Taille d'un tour de conversation |
| s | 15 tokens | Taille d'une signature de perturbation (εᵢ + forme) |
| k | variable | Nombre de tours |
| dt | 0,05 s | Pas d'intégration Kalman |
| ε | 0,5858 | Perturbation minimale RETA (2 − √2) |

**Coût de stockage :**

$$C_{\text{classique}} = n \cdot \frac{k(k+1)}{2} \quad \text{(somme des tours)}$$

$$C_{\text{RETA}} = n + k \cdot s \quad \text{(état courant + k signatures)}$$

---

## 2. Comparaison de Stockage

| k tours | Classique (tokens) | RETA (tokens) | Ratio | Économie |
|---:|---:|---:|---:|---:|
| 10 | 55 000 | 1 150 | **48×** | 97,91 % |
| 50 | 1 275 000 | 1 750 | **729×** | 99,86 % |
| 100 | 5 050 000 | 2 500 | **2 020×** | 99,95 % |
| 500 | 125 250 000 | 8 500 | **14 735×** | 99,99 % |
| 1 000 | 500 500 000 | 16 000 | **31 281×** | ≈ 100 % |

> **RETA est plus efficace dès le 2ème tour.**
> Seuil d'avantage : k > n/(n−s) = **1,015 tours** — immédiat.

---

## 3. Convergence Kalman — Erreur de Reconstruction

Le filtre de Kalman 1D (état [z, ż]) converge en quelques dizaines de pas vers
une **variance plancher P∞ constante**, indépendante de k :

| Étape Kalman | P₀₀ (variance) |
|---|---|
| Initiale | 5,0000 |
| 10 pas | 0,4378 |
| 50 pas | 0,4343 |
| **Convergée P∞** | **0,4316** |

Une fois convergé, **l'erreur de reconstruction ne croît plus avec k**.
C'est la différence fondamentale avec la mémoire classique qui se dégrade linéairement.

---

## 4. Efficience de Reconstruction

Pour retrouver le tour j depuis l'état courant au tour k = 100 :

| Descente | Ops RETA | Ops classique | Gain | Erreur max |
|---|---:|---:|---:|---:|
| j = 99 → k = 100 | 4 | 1 000 | **250×** | 0,4316 |
| j = 90 → k = 100 | 40 | 10 000 | **250×** | 4,316 |
| j = 75 → k = 100 | 100 | 25 000 | **250×** | 10,79 |
| j = 50 → k = 100 | 200 | 50 000 | **250×** | 21,58 |
| j = 0  → k = 100 | 400 | 100 000 | **250×** | 43,16 |

Le gain de **250×** en retrieval est constant, quelle que soit la profondeur de descente.
Il vient directement du rapport n/4 : un tour coûte n tokens à relire classiquement,
4 opérations matricielles (Kalman 2×2) en RETA.

---

## 5. Efficience Globale η

$$\eta = \frac{\text{information utile}}{\text{coût total}}$$

**Classique :**

$$\eta_{\text{classique}}(k) = \frac{1}{k} \quad \text{(dégradation linéaire)}$$

À k = 100 tours : η = 0,01 → **99 % du coût est de la redondance**.

**RETA :**

$$\eta_{\text{RETA}} = 1 - \frac{P_\infty}{\varepsilon} = 1 - \frac{0{,}4316}{0{,}5858} = \mathbf{0{,}2631}$$

**Constant, indépendant de k.**

$$\boxed{\frac{\eta_{\text{RETA}}}{\eta_{\text{classique}}(k=100)} = 26{,}3\times}$$

---

## 6. Tableau de Synthèse

| Métrique | Classique | RETA | Gain |
|---|---:|---:|---:|
| Stockage (k = 100) | 100 000 tokens | 2 500 tokens | **40×** |
| Retrieval (50 tours) | 50 000 ops | 200 ops | **250×** |
| Total conversation 100t | 5 050 000 tokens | 2 500 tokens | **2 020×** |
| Erreur reconstruction | non bornée | ≤ P∞ = 0,4316 | **garanti** |
| Dégradation avec k | linéaire (1/k) | nulle (P∞ constant) | **∞×** |
| Seuil d'avantage | — | dès le tour 2 | — |

---

## 7. Formules Opérationnelles

**Compression :**

$$R(k) = \frac{n \cdot k(k+1)/2}{n + k \cdot s} \approx \frac{nk}{2s} \quad (k \gg 1)$$

Pour n = 1 000, s = 15, k = 100 : **R = 2 020×**

**Erreur de reconstruction au tour j depuis k :**

$$\varepsilon_{\text{rec}}(j, k) \leq P_\infty \cdot (k - j)$$

**Temps de descente :**

$$t_{\text{collapse}}(j, k) = \frac{y_k - y_j}{\varepsilon_{\text{ctrl}}}$$

**Efficience RETA (invariante) :**

$$\eta_{\text{RETA}} = 1 - \frac{P_\infty}{\varepsilon} = 1 - \frac{\sqrt{Q \cdot R_{\text{mes}}}}{\varepsilon}$$

Améliorer η revient à **réduire le bruit de mesure** R_mes ou **augmenter la perturbation
minimale garantie** ε — deux paramètres physiquement contrôlables.

---

## 8. Conditions Limites

### 8.1 Quand RETA est optimal

- Conversations longues (k > 10)
- Perturbations à faible bruit de mesure (R_mes petit → P∞ petit)
- Signatures compactes (s ≪ n)

### 8.2 Quand l'erreur devient significative

L'erreur cumulée $P_\infty \cdot (k - j)$ dépasse un seuil acceptable Δ_max quand :

$$k - j > \frac{\Delta_{\max}}{P_\infty} = \frac{\Delta_{\max}}{0{,}4316}$$

Pour Δ_max = 10 (erreur de 1 % sur n = 1 000) : descente valide sur **23 tours** max.

Solution : **points de contrôle** (checkpoints) tous les 20 tours — réinitialisation
de la variance à P₀ = 0 sans coût mémoire supplémentaire.

### 8.3 Comparaison finale avec les méthodes existantes

| Méthode | Complexité stockage | Fidélité | Navigation |
|---|---|---|---|
| Fenêtre glissante | O(n × w) | Partielle (troncature) | Non |
| RAG (retrieval) | O(n × k) + index | Approximée | Par similarité |
| Résumé récursif | O(n × log k) | Dégradée | Non |
| **RETA** | **O(n + k·s)** | **≤ P∞ (garantie)** | **Par référentiel** |

---

## 9. Trois Régimes de Mémoire RETA

Le gain dépend de la politique de récupération appliquée. Trois régimes doivent
être distingués :

| Régime | Usage | Gain (k=100) | Erreur |
|---|---|---:|---|
| **Travail courant** (k−j ≤ 23) | Mémoire de session récente | **2 020×** | ≤ P∞ × 23 = 9,9 |
| **Historique fidèle** (checkpoint C=20) | Rappel exact de tout tour j | **673×** | 0 (exact) |
| **Archive longue** (k → ∞, sans checkpoint) | Tendances, pas faits précis | O(k)× | croissante |

**Coût des checkpoints :** `n` tokens par snapshot. Pour k = 100 tours, C = 20 :
seulement **5 snapshots supplémentaires** — négligeable sur l'ensemble.

> **Le gain de 2 020× est réel pour la mémoire de travail récente** (< 23 tours),
> avec une erreur de reconstruction bornée par P∞ × distance = 0,4316 × (k−j).
>
> Pour la mémoire exacte sur tout l'historique, les checkpoints donnent un gain
> réel de **400–700×** selon la fréquence — encore très significatif.
>
> L'efficience η = 0,263 est invariante avec k —
> là où la mémoire classique voit η → 0 à mesure que k croît.
>
> Le système devient plus efficace que la mémoire classique
> dès le **2ème tour de conversation**, sans paramètre à ajuster.

---
---

**📂 Section 3 — Technique & Implémentation**
[Méthodologie](methodologie.md) · [Paramétrage Kalman](parametrage_kalman.md) · [Fusion de Référentiels](fusion_referentiels.md) · [Efficience Mémoire](efficience_memoire.md) · [Manuel de Survie](manuel_de_survie.md)

**🔗 Voir aussi** : [Théorie Fondamentale](../1_fondamentaux/theorie_fondamentale.md) · [Extension Dimensionnelle](../2_extensions_theoriques/extension_dimensionnelle.md) · [Mémoire LLM](../4_applications/memoire_llm.md)

---

[📖 Index de la Documentation](../INDEX.md) · [🏠 Accueil du Projet](../../README.md)
