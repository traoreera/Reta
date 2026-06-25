# Index de la Documentation RETA

Bienvenue dans l'index central de la **Referential Escape Theory by Accumulation (RETA)**. Ce document sert de point d'entrée pour naviguer dans l'ensemble des travaux théoriques et techniques.

---

## 🧭 Plan de Navigation

### [1. Fondamentaux](./1_fondamentaux/theorie_fondamentale.md)
*Le cœur de la théorie : définitions, équations maîtresses et analyses critiques.*
- [Théorie Fondamentale](./1_fondamentaux/theorie_fondamentale.md) : Le document de référence (v1.3).
- [Analyse Complète](./1_fondamentaux/analyse_complete.md) : Vue d'ensemble et architecture en couches.
- [Réponses aux Critiques](./1_fondamentaux/reponses_critiques.md) : Traitement des objections formelles.

### [2. Extensions Théoriques](./2_extensions_theoriques/extension_dimensionnelle.md)
*Généralisations mathématiques et nouvelles logiques.*
- [Extension Dimensionnelle](./2_extensions_theoriques/extension_dimensionnelle.md) : Expansion ℝⁿ et procédures inverses.
- [Logique Probabiliste](./2_extensions_theoriques/logique_probabiliste.md) : Probabilités de mutation entre référentiels.

### [3. Technique & Implémentation](./3_technique/methodologie.md)
*Protocoles de mise en œuvre et réglages fins.*
- [Méthodologie d'Implémentation](./3_technique/methodologie.md) : Protocole standard de déploiement.
- [Paramétrage Kalman](./3_technique/parametrage_kalman.md) : Dérivation des matrices Q & R.
- [Fusion de Référentiels](./3_technique/fusion_referentiels.md) : Addition de référentiels et lignes de possibilités.
- [Efficience Mémoire](./3_technique/efficience_memoire.md) : Analyse quantitative de la mémoire RETA.
- [Manuel de Survie](./3_technique/manuel_de_survie.md) : Fiche technique pour déploiement autonome.

### [4. Applications Pratiques](./4_applications/index.md)
*Domaines d'application concrets.*
- [Index des Applications](./4_applications/index.md) : IA, Électronique, Finance.
- [Mémoire LLM](./4_applications/memoire_llm.md) : Navigation dimensionnelle pour les contextes longs.

### [5. Vision Stratégique](./5_strategie/vision_strategique.md)
*Positionnement et avenir du système.*
- [Vision Stratégique](./5_strategie/vision_strategique.md) : Le problème de l'asymptote trompeuse.
- [Survie et Avenir](./5_strategie/survie_et_avenir.md) : Analyse de viabilité structurelle.

### [6. Domaines d'Application](./6_domaines_application/README.md)
*Cartographie détaillée de tous les domaines où RETA intervient.*
- [Finance & Marchés](./6_domaines_application/finance.md) : Portefeuilles, crypto, drawdown, volatilité.
- [Intelligence Artificielle & LLM](./6_domaines_application/ia_llm.md) : Dérive sémantique, distribution shift, fine-tuning, jailbreak.
- [Systèmes Physiques](./6_domaines_application/physique.md) : Thermique, navigation inertielle, fatigue mécanique, batterie.
- [Cybersécurité](./6_domaines_application/cybersecurite.md) : Exfiltration L&S, APT, DDoS, poisoning IA, vulnerability debt.
- [Santé & Biomédical](./6_domaines_application/sante.md) : Glycémie, pharmacocinétique, fatigue opérateur, oncologie, IRC.
- [Infrastructure & Logistique](./6_domaines_application/infrastructure.md) : Supply chain, réseau électrique, congestion, corrosion, dette technique.
- [Sciences Sociales & Comportement](./6_domaines_application/social.md) : Polarisation, réputation, cohésion équipe, propagation virale, dette souveraine.

---

### [Versions RETA](./VERSIONS.md)
*Implémentations progressives avec simulations et preuves par version.*
- [v1.1 — Kalman fixe + PI fixe](./v1.1/README.md) : Version de référence, Routh-Hurwitz + Lyapunov.
- [v1.2 — PI adaptatif gradient](./v1.2/README.md) : K̇p = γp·ē², K̇i = γi·ē·∫ē — survie aux sauts de perturbation.
- [v1.3 — Kalman adaptatif + PI adaptatif](./v1.3/README.md) : Q adaptatif par innovations GPS, ×3.7 survie en dead-reckoning.
- [v1.4 — Bound conservatif ḃ_true](./v1.4/README.md) : Corrige la limite de v1.3 — bound t_rup reste sous la rupture réelle même quand z croît.
- [Résumé comparatif](./VERSIONS.md) : Tableau, architecture, preuves Lyapunov par version.

---

### [Bibliographie](./bibliographie.md)
*Références théoriques, sources de données et correspondance formule → origine.*

---

### [Benchmarks NASA](./benchmarks.md)
*Benchmark GISTEMP v4 pour `v1.1` à `v1.4` avec résultats reproductibles.*

---

## 🛠 Outils & Simulations
Chaque version possède sa propre simulation autonome dans `docs/v1.X/simulation.py`.

---
[🏠 Retour à l'accueil](../../README.md)
