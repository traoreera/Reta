# RETA — Probabilité de Mutation entre Référentiels (v2.0)
*Du calcul booléen vers la logique probabiliste de transition dimensionnelle*

> **Corrections v2.0 :**
> 1. **Variance temporelle** : La probabilité $P(A \to B \mid t)$ utilisait $P_\infty$ (variance asymptotique fixe) au dénominateur, ce qui contredit le Théorème 1 d'`extension_dimensionnelle.md` où l'erreur de reconstruction croît en $\sqrt{t \cdot P_{00}}$. La variance doit être dynamique : $\sigma^2(t) = t \cdot (P_{00,A} + P_{00,B})$ (→ corrige la contradiction interne entre les deux documents).
> 2. **Normalisation N-aire documentée** : Le passage de $N(N-1)/2$ probabilités par paires à une distribution sur $N$ référentiels nécessite une softmax des scores $\Delta_i$. La formule manquante est maintenant explicite (§3).
> 3. **Terminologie corrigée** : « Réversible » → « Asymétrique » (la définition standard de la réversibilité est l'inverse). $E[T] = 1/\max(dP/dt)$ n'est pas une identité valide → remplacée par la formule de premier passage du mouvement brownien avec dérive (loi inverse-gaussienne).
> 4. **Tableau §2.2 recalculé** avec la variance temporelle correcte.

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

### 2.1 Formulation (corrigée v2.0)

La divergence accumulée $\Delta_{AB}(t) = \int_0^t (z_B - z_A)\,d\tau$
représente la "distance" entre les deux référentiels au temps t.

> **⚠️ Correction v2.0 — Variance dynamique :** La version v1.0 utilisait une variance fixe $P_\infty$ au dénominateur. C'est incohérent avec le Théorème 1 d'`extension_dimensionnelle.md` ($\S8$), qui établit que l'erreur de reconstruction croît en $\sqrt{t \cdot P_{00}}$ — un résultat cohérent avec une marche aléatoire. Utiliser $P_\infty$ dès $t=0$ sous-estime artificiellement l'incertitude et pousse $P(A \to B) \to 1$ trop vite. La variance correcte est **proportionnelle au temps** :

$$\boxed{P(A \to B \mid t) = \Phi\!\left(\frac{\Delta_{AB}(t)}{\sqrt{t \cdot (P_{00,A} + P_{00,B})}}\right)}$$

où :
- $\Phi$ est la fonction de répartition normale (CDF)
- $P_{00,A}, P_{00,B}$ sont les variances d'estimation Kalman (avant convergence complète) pour chaque référentiel
- $t \cdot (P_{00,A} + P_{00,B})$ est la variance cumulée de la divergence — elle croît linéairement avec le temps
- $\Delta_{AB}(t)$ — divergence accumulée entre A et B

**Pourquoi cette correction est nécessaire :**
- À $t=0$, la variance est nulle → $P(A \to B) = 0,5$ (superposition maximale, inchangé).
- À $t$ grand, le dénominateur croît en $\sqrt{t}$ tandis que $\Delta_{AB}(t)$ croît en $t$ → la probabilité tend encore vers 1, mais **plus lentement** qu'avec $P_\infty$ fixe.
- La formule est cohérente avec le Théorème 1 d'`extension_dimensionnelle.md` et avec l'interprétation physique : l'incertitude sur la divergence augmente avec le temps (marche aléatoire).

### 2.2 Évolution observée (recalculée v2.0)

Pour ε_A = 0,58, ε_B = 1,20 (ε_delta = 0,62), $P_{00,A} + P_{00,B} = 0{,}4316$ :

| t (s) | Δ_AB(t) | σ(t) = √[t·P_sum] | P(A→B) | P(reste A) | Interprétation |
|---:|---:|---:|---:|---:|---|
| 0,00 | 0,0000 | 0,000 | 0,5000 | 0,5000 | superposition maximale |
| 1,00 | 0,9218 | 0,657 | 0,9197 | 0,0803 | mutation probable |
| 2,00 | 1,7821 | 0,929 | 0,9727 | 0,0273 | quasi-muté |
| 3,00 | 2,5986 | 1,138 | 0,9889 | 0,0111 | mutation presque certaine |
| 5,00 | 4,3200 | 1,469 | 0,9984 | 0,0016 | convergence |
| 10,00 | 8,7000 | 2,078 | 1,0000 | 0,0000 | muté |

> **Note :** La convergence vers $P=1$ est plus lente qu'avec $P_\infty$ fixe (où $P=1{,}0000$ était atteint dès $t=3$s). Ce comportement est physiquement plus réaliste : l'incertitude sur la divergence accumulée croît avec le temps, donc la certitude de mutation met plus de temps à s'établir. Les écarts au tableau original sont faibles à court terme ($t \leq 2$s) mais deviennent significatifs à mesure que $t$ grandit.

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

## 3. Distribution sur un Groupe de N Référentiels (v2.0)

### 3.0 Normalisation N-aire (formule documentée)

> **⚠️ Correction v2.0 :** La version v1.0 présentait un tableau de probabilités sur 5 référentiels sans expliquer comment passer des $N(N-1)/2$ probabilités par paires à une distribution normalisée. Cette étape est maintenant explicite.

On dispose des perturbations $\varepsilon_i$ de chaque référentiel $R_i$. On définit un **score cumulé** par référentiel :

$$\Delta_i(t) = \int_0^t \bigl(z_i(\tau) - z_{\text{courant}}(\tau)\bigr)\,d\tau$$

La distribution de probabilité sur les $N$ référentiels est obtenue par **softmax des scores normalisés** :

$$\boxed{P_i(t) = \frac{\exp\!\bigl(\Delta_i(t) / \sigma(t)\bigr)}{\sum_{j=1}^N \exp\!\bigl(\Delta_j(t) / \sigma(t)\bigr)}}$$

où $\sigma(t) = \sqrt{t \cdot P_{00}}$ est l'écart-type dynamique (cf. §2.1). Cette softmax est la généralisation naturelle de la CDF normale $\Phi$ au cas $N$-aire : pour $N=2$, on retrouve $P(A\to B) = \Phi(\Delta_{AB}/\sigma)$.

> **Alternative (non documentée dans la v1.0 mais possible) :** Résoudre un système de cohérence de type « pairwise comparison → global ranking », analogue aux méthodes de Bradley-Terry. La softmax ci-dessus est retenue pour sa simplicité et son lien direct avec la formulation binaire.

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

La dérivée dP/dt prédit la mutation **avant** qu'elle se produise (formule complète au §6 avec la variance temporelle corrigée) :

$$\frac{dP}{dt} = \frac{z_B - z_A}{\sigma(t)} \cdot \phi\!\left(\frac{\Delta(t)}{\sigma(t)}\right) - \frac{\Delta(t)}{2t\,\sigma(t)} \cdot \phi\!\left(\frac{\Delta(t)}{\sigma(t)}\right), \quad \sigma(t) = \sqrt{t \cdot (P_{00,A}+P_{00,B})}$$

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

$$M_{ij}(t) = P(R_i \to R_j \mid t) = \Phi\!\left(\frac{\Delta_{ij}(t)}{\sqrt{t \cdot (P_{00,i}+P_{00,j})}}\right)$$

La matrice de transition M(t) est **calculable à tout instant** depuis :
- Les perturbations zᵢ, zⱼ (connues ou estimées par Kalman)
- Les variances Kalman P₀₀,i, P₀₀,j (évoluent avec le temps — voir §2.1 pour la justification du passage de P∞ fixe à la variance temporelle)

### 5.1 Propriétés de la chaîne (corrigées v2.0)

- **Asymétrique** : P(A→B) ≠ P(B→A) en général (asymétrie des perturbations)
  > **Correction terminologique :** La v1.0 utilisait « réversible ». Dans la théorie des chaînes de Markov, une chaîne est réversible si elle satisfait le bilan détaillé $\pi_i M_{ij} = \pi_j M_{ji}$, ce qui implique une symétrie dans les transitions à l'équilibre. Ce n'est pas le cas ici. Le terme correct est **asymétrique** (ou non-réversible).
- **Contrôlable** : le PI modifie les Δᵢⱼ → pilote les probabilités de transition
- **Prédictible** : M(t) est déterministe si les zᵢ sont connues
- **Temps de premier passage** (formule corrigée) :

  $$\mathbb{E}[T_{A\to B}] = \frac{\Delta_{AB}(t)}{\varepsilon_\delta^2} \quad \text{(loi inverse-gaussienne)}$$

  > **Correction v2.0 :** La formule $1/\max_t(dP/dt)$ n'est une identité mathématique valide pour **aucune** loi de probabilité standard. La bonne formule découle du fait que $P(A\to B \mid t)$ est la CDF d'un premier passage de mouvement brownien avec dérive : le temps de premier passage suit une **loi inverse-gaussienne** $\text{IG}(\mu = \Delta_{AB}/\varepsilon_\delta, \lambda = \Delta_{AB}^2/\sigma^2)$, dont l'espérance est donnée ci-dessus. Voir `../bibliographie.md` pour les références.

---

## 6. Formules Opérationnelles

$$\boxed{
\begin{aligned}
&\textbf{Probabilité de mutation (v2.0) :} \\
&\quad P(A \to B \mid t) = \Phi\!\left(\frac{\int_0^t (z_B-z_A)\,d\tau}{\sqrt{t \cdot (P_{00,A}+P_{00,B})}}\right) \\[6pt]
&\textbf{Taux de mutation :} \\
&\quad \frac{dP}{dt} = \frac{z_B - z_A}{\sqrt{t \cdot P_{\text{sum}}}} \cdot \phi\!\left(\frac{\Delta(t)}{\sqrt{t \cdot P_{\text{sum}}}}\right) - \frac{\Delta(t)}{2 t \sqrt{t \cdot P_{\text{sum}}}} \cdot \phi\!\left(\frac{\Delta(t)}{\sqrt{t \cdot P_{\text{sum}}}}\right) \\[6pt]
&\textbf{Distribution N-aire (softmax) :} \\
&\quad P_i(t) = \frac{\exp\!\bigl(\Delta_i(t) / \sqrt{t \cdot P_{00}}\bigr)}{\sum_j \exp\!\bigl(\Delta_j(t) / \sqrt{t \cdot P_{00}}\bigr)} \\[6pt]
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

---

**📂 Section 2 — Extensions Théoriques**
[Extension Dimensionnelle](extension_dimensionnelle.md) · [Logique Probabiliste](logique_probabiliste.md)

**🔗 Voir aussi** : [Théorie Fondamentale](../1_fondamentaux/theorie_fondamentale.md) · [Réponses aux Critiques](../1_fondamentaux/reponses_critiques.md) · [Fusion de Référentiels](../3_technique/fusion_referentiels.md) · [Efficience Mémoire](../3_technique/efficience_memoire.md)

---

[📖 Index de la Documentation](../INDEX.md) · [🏠 Accueil du Projet](../../README.md)
