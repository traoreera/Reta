# RETA — Corrections et Ajouts v1.5
*Changelog consolidé — intégration de la théorie de dispersion en dimension n*

---

## Résumé

Cette version ajoute **RETA-nD** (théorie de dispersion en dimension $n$ : bruit
isotrope, force entropique géométrique, processus de Bessel) et corrige **six failles**
identifiées par examen critique du corpus complet (Critiques 6-11, en plus des
Critiques 1-5 déjà traitées en v2.0).

---

## Fichiers ajoutés

| Fichier | Contenu |
|---|---|
| `2_extensions_theoriques/reta_nd_dispersion.md` | Théorie complète : rappel dispersion, formule RETA avant/après, tableau "corrigé/pas corrigé", liste de validité par domaine, section embeddings LLM |
| `6_domaines_application/ia_llm_drift_monitoring.md` | Application honnête aux embeddings LLM : dimension effective, détection de dérive, hypothèse falsifiable — remplace l'usage "reconstruction" de `memoire_llm.md` |
| `CORRECTIONS_v1.5.md` | Ce document |

## Fichiers modifiés

| Fichier | Modification | Critique traitée |
|---|---|---|
| `1_fondamentaux/reponses_critiques.md` | Ajout des Critiques 6 à 11 | — |
| `2_extensions_theoriques/extension_dimensionnelle.md` | Distinction $n$/$k$ ; deux régimes (déterministe/stochastique) pour $t_{rupture,global}$ ; condition de validité du $\min_i$ | Critiques 6, 7 |
| `2_extensions_theoriques/logique_probabiliste.md` | Variance temporelle $\sigma^2(t)=t(P_{00,A}+P_{00,B})$ au lieu de $P_\infty$ fixe ; normalisation N-aire documentée ; terminologie "réversible"→"asymétrique" | Critiques 8, 9, 10 |
| `4_applications/memoire_llm.md` | Bandeau d'avertissement ; §9 ajouté (reformulation honnête) ; §1-8 conservés comme archive de l'erreur d'origine | Critique 11 |
| `3_technique/efficience_memoire.md` | Bandeau précisant la portée des chiffres de compression (corrects arithmétiquement, invalides comme garantie de reconstruction) | Critique 11 |
| `6_domaines_application/ia_llm.md` | §1 corrigé : "signal de dérive" au lieu de "reconstruction exacte" | Critique 11 |
| `INDEX.md` | Liens vers les nouveaux documents, annotations de statut | — |
| `VERSIONS.md` | Ligne v1.5 ajoutée au tableau comparatif | — |

## Ce qui n'a pas été modifié

- `1_fondamentaux/theorie_fondamentale.md`, `analyse_complete.md`, `reta_v13_demonstration.md` : le cœur scalaire de RETA (v1.0-v1.4) reste valide tel quel — c'est le cas particulier $n=1$ de RETA-nD.
- `6_domaines_application/exemples/drone_gyroscope_3d.md` : le $\min_i$ y est **correct** (seuils indépendants par axe = pavé, pas norme jointe) — aucune correction nécessaire, confirmé par la liste de validité.
- `ia_llm.md` §2-4 (distribution shift, fine-tuning, jailbreak) : usages scalaires légitimes (PSI, KL, score d'alignement), non concernés par la Critique 11.
- `3_technique/parametrage_kalman.md`, `3_technique/fusion_referentiels.md`, `3_technique/methodologie.md`, `3_technique/manuel_de_survie.md`, `5_strategie/*`, `6_domaines_application/{finance,physique,cybersecurite,sante,infrastructure,social}.md`, `benchmarks.md`, `bibliographie.md`, `v1.1/` à `v1.4/` : non revus en détail dans cette passe — aucune faille de même nature identifiée à ce stade, mais pas d'audit exhaustif effectué.

## Principe directeur des corrections

Deux types de correction ont été appliqués, à ne pas confondre :

1. **Corrections géométriques** (Critiques 6, 7, 8) : la dispersion en dimension $n$
   apporte une formule quantitativement meilleure. Ces corrections sont des
   remplacements directs.
2. **Correction de portée** (Critique 11) : la dispersion explique *pourquoi* une
   affirmation était trop forte, sans fournir de solution de remplacement au même
   niveau d'ambition. Ici, la correction consiste à **retirer la promesse invalide**
   et à conserver l'usage plus restreint qui, lui, tient (détection de dérive).

Les Critiques 9 et 10 sont des corrections indépendantes de la dispersion (lacune de
formulation, erreur terminologique) — traitées pour la cohérence du corpus mais sans
lien avec RETA-nD.

---

[📖 Index de la Documentation](./INDEX.md) · [🏠 Accueil du Projet](../README.md)
