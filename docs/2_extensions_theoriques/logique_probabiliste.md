# RETA — Probabilité de Mutation entre Référentiels
*Du calcul booléen vers la logique probabiliste de transition dimensionnelle*

---

## 1. Le Problème du Calcul Booléen

La vision classique d'un système est binaire :

```
Référentiel A  ──→  [condition vraie/fausse]  ──→  Référentiel B
```

Soit le système est en A, soit il est en B. Aucune nuance.

**Ce que RETA révèle :** un système ne *bascule* pas entre référentiels.
Il **dérive** vers un nouveau référentiel avec une probabilité qui croît
de façon continue et calculable. La transition est un processus, pas un événement.

---

## 2. La Probabilité de Mutation

### 2.1 Formulation

La divergence accumulée $\Delta_{AB}(t) = \int_0^t (z_B - z_A)\,d\tau$
représente la "distance" entre les deux référentiels au temps t.

La probabilité que le système ait muté vers B à l'instant t :

$$\boxed{P(A \to B \mid t) = \Phi\!\left(\frac{\Delta_{AB}(t)}{\sqrt{P_\infty}}\right)}$$

où :
- $\Phi$ est la fonction de répartition normale (CDF)
- $\sqrt{P_\infty} = 0{,}657$ — incertitude Kalman sur la divergence
- $\Delta_{AB}(t)$ — divergence accumulée entre A et B

### 2.2 Évolution observée

Pour ε_A = 0,58, ε_B = 1,20 (ε_delta = 0,62) :

| t (s) | Δ_AB(t) | P(A→B) | P(reste A) | Entropie H | État |
|---:|---:|---:|---:|---:|---|
| 0,00 | 0,0000 | 0,5000 | 0,5000 | 1,000 | superposition maximale |
| 1,00 | 0,9218 | 0,9197 | 0,0803 | 0,403 | mutation probable |
| 2,00 | 1,7821 | 0,9967 | 0,0033 | 0,032 | quasi-muté |
| 3,00 | 2,5986 | 1,0000 | 0,0000 | 0,001 | muté en B |

> **Observation clé :** à t = 0, le système est en **superposition** des deux
> référentiels (P = 0,5 chacun). La mutation n'est pas un saut — c'est une
> convergence probabiliste pilotée par la divergence accumulée.

### 2.3 Taux de mutation dP/dt

| t (s) | P(mut) | dP/dt | État système |
|---:|---:|---:|---|
| 0,00 | 0,5000 | 0,000 | ⚠ zone critique (superposition) |
| 0,50 | 0,6815 | 0,363 | → mutation probable |
| 1,00 | 0,8273 | 0,292 | ✓ muté en B |
| 1,50 | 0,9216 | 0,188 | ✓ stabilisation |
| 2,00 | 0,9705 | 0,098 | ✓ convergé |
| 3,00 | 0,9977 | 0,014 | ✓ état pur B |

Le taux dP/dt est maximal à t = 0 puis décroît — la mutation est une **sigmoid dans le temps**,
pas un échelon.

---

## 3. Distribution sur un Groupe de N Référentiels

Pour un groupe de N référentiels, le système n'est pas *dans un* référentiel —
il est décrit par une **distribution de probabilité** sur tous :

$$\psi(t) = \sum_{i=1}^{N} P_i(t) \cdot y_{R_i}(t) \quad \text{avec} \quad \sum_i P_i(t) = 1$$

### 3.1 Évolution de la distribution (groupe de 5 référentiels)

Référentiel courant : Texte (ε = 0,50)

| t (s) | Texte | Image | Audio | Temporel | Spatial |
|---:|---:|---:|---:|---:|---:|
| 0,5 | 0,1706 | 0,2014 | 0,1861 | **0,2306** | 0,2114 |
| 1,0 | 0,1509 | 0,2040 | 0,1781 | **0,2472** | 0,2199 |
| 2,0 | 0,1299 | 0,2128 | 0,1756 | **0,2509** | 0,2307 |
| 4,0 | 0,1169 | 0,2258 | 0,1916 | 0,2337 | **0,2320** |
| 7,0 | 0,1125 | 0,2249 | 0,2126 | 0,2250 | **0,2250** |

Le référentiel avec la plus grande perturbation (Temporel, ε = 1,10) attire d'abord
le système. Puis la distribution se stabilise vers un équilibre.

### 3.2 Entropie de Shannon — mesure de superposition

$$H(t) = -\sum_{i=1}^{N} P_i(t) \cdot \log_2 P_i(t)$$

| N référentiels | H_max | Signification |
|---:|---:|---|
| 2 | 1,000 bit | superposition binaire |
| 3 | 1,585 bits | superposition ternaire |
| 5 | 2,322 bits | superposition quintuple |
| 10 | 3,322 bits | superposition décuple |
| 20 | 4,322 bits | très haute incertitude référentielle |

- **H = 0** : état pur — le système est entièrement dans un référentiel
- **H = H_max** : superposition totale — tous les référentiels équiprobables
- **H décroissant** : le système converge vers un référentiel dominant

> **H est la mesure de la "distance à la décision".**
> Un système à haute entropie référentielle est en zone de mutation maximale.

---

## 4. Pourquoi c'est Crucial

### 4.1 Remplacement de la logique booléenne

| Logique booléenne | Logique probabiliste RETA |
|---|---|
| Le système est en A OU en B | P(A) + P(B) + ... = 1 |
| La transition est instantanée | La transition est une sigmoid en t |
| Pas de zone intermédiaire | Zone de superposition calculable |
| Aucune prédiction de timing | t_mutation estimable depuis dP/dt |
| Tout ou rien | Chaque référentiel contribue à P_i |

### 4.2 Prédiction de mutation avant qu'elle arrive

La dérivée dP/dt prédit la mutation **avant** qu'elle se produise :

$$\frac{dP}{dt} = \frac{\varepsilon_\delta}{\sqrt{P_\infty}} \cdot \phi\!\left(\frac{\Delta(t)}{\sqrt{P_\infty}}\right)$$

où φ est la densité normale (PDF). Le maximum de dP/dt arrive **avant** P = 0,5 —
on peut sonner l'alarme avant la mutation effective.

### 4.3 Le Régulateur PI comme force anti-mutation

Le PI maintient le système dans son référentiel courant en **annulant la divergence** :

$$u(t) = K_p \cdot \Delta(t) + K_i \int \Delta(\tau)\,d\tau$$

$$\Rightarrow \Delta_{\text{net}}(t) \to 0 \quad \Rightarrow \quad P(A \to B \mid t) \to 0{,}5$$

Le PI **fige la probabilité de mutation à 0,5** — le système reste en superposition
contrôlée, sans basculer vers un nouveau référentiel non voulu.

Pour forcer une mutation vers B intentionnellement :
désactiver le PI sur la dimension B → la divergence s'accumule → P(A→B) → 1.

---

## 5. Chaîne de Markov des Référentiels

Les N référentiels forment une **chaîne de Markov** où les probabilités de
transition sont données par RETA :

$$M_{ij}(t) = P(R_i \to R_j \mid t) = \Phi\!\left(\frac{\Delta_{ij}(t)}{\sqrt{P_\infty}}\right)$$

La matrice de transition M(t) est **calculable à tout instant** depuis :
- Les perturbations zᵢ, zⱼ (connues ou estimées par Kalman)
- La variance Kalman P∞ (constante une fois convergée)

### 5.1 Propriétés de la chaîne

- **Réversible** : P(A→B) ≠ P(B→A) en général (asymétrie des perturbations)
- **Contrôlable** : le PI modifie les Δᵢⱼ → pilote les probabilités de transition
- **Prédictible** : M(t) est déterministe si les zᵢ sont connues
- **Temps de premier passage** : $\mathbb{E}[T_{A\to B}] = 1/\max_t(dP_{AB}/dt)$

---

## 6. Formules Opérationnelles

$$\boxed{
\begin{aligned}
&\textbf{Probabilité de mutation :} \\
&\quad P(A \to B \mid t) = \Phi\!\left(\frac{\int_0^t (z_B-z_A)\,d\tau}{\sqrt{P_\infty}}\right) \\[6pt]
&\textbf{Taux de mutation :} \\
&\quad \frac{dP}{dt} = \frac{(z_B - z_A)}{\sqrt{P_\infty}} \cdot \phi\!\left(\frac{\Delta(t)}{\sqrt{P_\infty}}\right) \\[6pt]
&\textbf{Entropie référentielle :} \\
&\quad H(t) = -\sum_i P_i(t)\log_2 P_i(t) \in [0,\, \log_2 N] \\[6pt]
&\textbf{État du système :} \\
&\quad \psi(t) = \sum_i P_i(t) \cdot y_{R_i}(t)
\end{aligned}
}$$

---

## 7. Synthèse — Ce que ça Change

> **Un système RETA n'est jamais dans un seul référentiel.**
> Il est décrit à tout instant par une distribution de probabilités sur
> l'ensemble des référentiels accessibles.
>
> La mutation n'est pas un événement discret — c'est un processus continu
> piloté par la divergence accumulée, mesurable par le taux dP/dt,
> contrôlable par le régulateur PI, et prédictible avant qu'il se produise.
>
> Remplacer le calcul booléen par cette logique probabiliste donne accès à :
> - La **zone de superposition** (H proche de H_max) : instabilité référentielle
> - Le **moment optimal de mutation** (pic de dP/dt) : décision proactive
> - La **chaîne de Markov** des référentiels : navigation probabiliste du groupe
> - Le **contrôle de H** par PI : maintien ou libération intentionnelle d'un référentiel

---

*Lire en parallèle :*
- *`../3_technique/fusion_referentiels.md` — addition de référentiels et lignes de possibilités*
- *`../2_extensions_theoriques/extension_dimensionnelle.md` — expansion nD et contraction*
- *`../3_technique/efficience_memoire.md` — analyse quantitative*
- *`../1_fondamentaux/theorie_fondamentale.md` — théorie de base*

---
## 🧭 Navigation
- [📖 Index de la Documentation](../INDEX.md)
- [🏠 Accueil du Projet](../../README.md)
