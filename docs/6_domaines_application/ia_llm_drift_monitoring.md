# RETA-nD — Surveillance de Dérive sur Embeddings LLM (v1.5)
*Version corrigée et honnête de l'application mémoire LLM — détection, pas reconstruction*

**Domaine :** IA / LLM — Espace d'embedding en haute dimension
**Remplace l'usage « reconstruction » de** `../4_applications/memoire_llm.md` (§1-8, archivé)
**S'appuie sur :** `../2_extensions_theoriques/reta_nd_dispersion.md`

---

## 0. Ce que ce document fait et ne fait pas

- **Fait :** propose un cadre RETA-nD pour détecter et alerter sur une dérive
  sémantique anormale dans une conversation ou un flux d'embeddings, avec une
  quantification honnête des marges d'erreur.
- **Ne fait pas :** ne prétend pas reconstruire le contenu textuel d'un tour passé, ni
  compresser une conversation sans perte. Voir Critique 11 (`../1_fondamentaux/reponses_critiques.md`).

---

## 1. Modèle RETA-nD du problème

| Variable | Définition |
|---|---|
| $\mathbf{e}(t) \in \mathbb{R}^n$ | Écart de l'embedding conversationnel courant par rapport à un ancrage (embedding du sujet initial, ou centroïde d'une fenêtre de référence) |
| $n$ | Dimension nominale de l'espace d'embedding (ex. 768, 4096) |
| $n_{\text{eff}}$ | Dimension **effective** (participation ratio, §2) — presque toujours $\ll n$ |
| $D$ | Coefficient de diffusion du bruit résiduel par tour (à calibrer empiriquement) |
| $Y_{max}$ | Seuil de dérive tolérée (rayon de tolérance sémantique) |
| $r(t) = \|\mathbf{e}(t)\|$ | Norme de la dérive cumulée |

---

## 2. Étape 1 — Mesurer la dimension effective (obligatoire avant tout calcul)

$$n_{\text{eff}} = \frac{(\operatorname{tr}\Sigma)^2}{\operatorname{tr}(\Sigma^2)}$$

où $\Sigma$ est la matrice de covariance empirique des embeddings sur une fenêtre de
$M$ tours passés (participation ratio, standard en analyse d'anisotropie des
représentations transformers). C'est un calcul purement a posteriori sur des
embeddings déjà produits — **aucune modification du modèle n'est nécessaire**.

> **Pourquoi c'est indispensable :** utiliser la dimension nominale $n$ (ex. 4096)
> au lieu de $n_{\text{eff}}$ dans les formules ci-dessous surestimerait fortement le
> taux de dilution du signal de dérive, à cause de l'anisotropie connue des espaces
> d'embedding (variance concentrée sur peu de directions).

---

## 3. Étape 2 — Modèle de dérive et seuil d'alerte

Sous hypothèse de bruit résiduel isotrope dans le sous-espace effectif :

$$\langle r^2(t)\rangle \sim n_{\text{eff}} \cdot D \cdot t + \|\bar{\mathbf{z}}\|^2 t^2$$

où $\bar{\mathbf{z}}$ est une dérive déterministe moyenne (ex. digression thématique
volontaire et soutenue). Le seuil d'alerte se déclenche quand :

$$r(t) > Y_{max} \quad\Leftrightarrow\quad t > t_{\text{alerte}}$$

résolu numériquement (pas de forme fermée générale avec les deux termes combinés).

**Cas particulier sans dérive déterministe** ($\bar{\mathbf{z}} = 0$) : $r(t)$ est un
processus de Bessel de dimension $n_{\text{eff}}$ (cf. `reta_nd_dispersion.md` §1),
pour lequel des résultats de premier passage sont disponibles en forme close.

---

## 4. Étape 3 — Correcteur PI sur la norme (recadrage préventif)

$$u(t) = K_p \cdot (r(t) - Y_c) + K_i\!\int_0^t (r(\tau)-Y_c)\,d\tau$$

Quand $u(t)$ dépasse un seuil, injecter une instruction de recadrage ("rappel : le
sujet initial est X") — mécanisme identique à celui déjà documenté dans
`ia_llm.md` §1, mais appliqué à la norme $r(t)$ en dimension $n_{\text{eff}}$ plutôt
qu'à une distance cosine scalaire brute (qui est une projection 1D valide mais plus
pauvre que la norme complète du sous-espace effectif).

---

## 5. Ce qui est stocké — et ce qui ne l'est pas

| Élément | Stocké ? | Rôle |
|---|---|---|
| Vecteur d'ancrage (sujet initial) | Oui — 1 vecteur | Référence de dérive |
| $r(t)$, historique des normes | Oui — 1 scalaire par tour | Signal de surveillance |
| $\Sigma$ (covariance glissante) | Oui — matrice $n\times n$ ou approximation low-rank | Calcul de $n_{\text{eff}}$ |
| Contenu textuel des tours passés | **Non remplacé** — reste stocké par les moyens classiques (fenêtre, RAG, résumé) | RETA-nD ne s'y substitue pas |

C'est la différence structurante avec `memoire_llm.md` v1.0 : **rien ici ne prétend
remplacer le stockage du contenu**, seulement ajouter un signal de surveillance
au-dessus.

---

## 6. Hypothèse falsifiable à tester

> Le taux de dérive sémantique observé empiriquement sur des conversations longues
> réelles est-il cohérent avec $\langle r^2(t)\rangle \propto n_{\text{eff}} \cdot D
> \cdot t$ ? Si oui, la force entropique $(n_{\text{eff}}-1)D/r$ fournit une explication
> géométrique (et non purement sémantique) du phénomène de "dérive de sujet" en
> conversation longue — un modèle sans ancrage dérive plus vite si $n_{\text{eff}}$ est
> grand, indépendamment du contenu.

**Protocole de test suggéré :** sur un corpus de conversations de longueur variable,
mesurer $n_{\text{eff}}$ (fenêtre glissante) et $r(t)$ (distance à l'ancrage initial),
puis vérifier la loi d'échelle en régression. Non encore réalisé — à documenter comme
résultat empirique séparé si validé.

---

## 7. Tableau récapitulatif

| Grandeur | Formule | Statut |
|---|---|---|
| Dimension effective | $n_{\text{eff}} = (\operatorname{tr}\Sigma)^2/\operatorname{tr}(\Sigma^2)$ | Mesurable, obligatoire |
| Dérive attendue (bruit seul) | $\langle r^2(t)\rangle = n_{\text{eff}} D t$ | Dérivé de la dispersion |
| Seuil d'alerte | $r(t) > Y_{max}$ | Opérationnel |
| Correcteur | $u(t) = K_p(r-Y_c) + K_i\int(r-Y_c)d\tau$ | Identique au PI RETA standard |
| Reconstruction de contenu | — | **Hors de portée**, cf. Critique 11 |

---

**📂 Section 6 — Domaines d'Application**
[Index](README.md) · [IA & LLM](ia_llm.md) · [Mémoire LLM (archive corrigée)](../4_applications/memoire_llm.md)

**🔗 Voir aussi** : [RETA-nD / Dispersion](../2_extensions_theoriques/reta_nd_dispersion.md) ·
[Réponses aux Critiques](../1_fondamentaux/reponses_critiques.md)

---

[📖 Index de la Documentation](../INDEX.md) · [🏠 Accueil du Projet](../../README.md)
