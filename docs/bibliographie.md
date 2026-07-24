# Bibliographie

Cette page regroupe les références théoriques qui sous-tendent les formules et modèles utilisés dans RETA. Les équations propres au projet, comme les bornes de rupture `v1.3/v1.4` ou les lois d’adaptation `Q/R`, restent des dérivations internes construites sur ces bases.

## Références principales

- Kalman, R. E., *A New Approach to Linear Filtering and Prediction Problems* (1960). Base du filtre de Kalman utilisé dans `v1.1` à `v1.4`.
- Kalman, R. E., et Bucy, R. S., *New Results in Linear Filtering and Prediction Theory* (1961). Complète la formulation continue du filtrage linéaire.
- Lyapunov, A. M., *The General Problem of the Stability of Motion* (1892). Source historique de la méthode directe de Lyapunov.
- Routh, E. J., *A Treatise on the Stability of a Given State of Motion* (1877) et Hurwitz, A. (1895). Base du critère Routh-Hurwitz utilisé pour les systèmes linéaires.
- Åström, K. J. et Hägglund, T., *PID Controllers: Theory, Design, and Tuning* (référence de contrôle classique). Appui pour les lois PI et le réglage des gains.

## Données et méthode empirique

- NASA GISS, *GISTEMP v4* : https://data.giss.nasa.gov/gistemp/
- Lenssen, N. et al., *A GISTEMPv4 observational uncertainty ensemble* (2024) : https://doi.org/10.1029/2023JD040179

## Formule → origine

| Formule / bloc | Origine |
|---|---|
| `f(t) = arctan(t)` | Analyse classique ; fonction bornée servant de cas canonique |
| `u(t) = Kp·e(t) + Ki·∫e(t)dt` | Régulation PI classique |
| Recursion Kalman (`predict/update`) | Filtrage récursif linéaire-gaussien |
| `V(e,I) = e²/2 + (Ki/2)I²` | Méthode directe de Lyapunov, adaptée au modèle RETA |
| `\dot V = -Kp e² + e[f'(t)+z(t)]` | Développement RETA de la dynamique fermée |
| Lois `Q/R` adaptatives et borne quadratique `v1.4` | Dérivations internes RETA, fondées sur l’innovation Kalman et une hypothèse de dérive linéaire |

## Références complémentaires

- Aranovskiy, S., Ortega, R., Cisneros, R., *Robust PI Passivity-based Control of Nonlinear Systems* (2015). Utile pour situer le PI robuste.
- Zhao, C. et Guo, L., *On the Capability of PID Control for Nonlinear Uncertain Systems* (2016). Soutien théorique au contrôle PI/PID sur systèmes incertains.
- Baltieri, M., *A Bayesian perspective on classical control* (2020). Intéressant pour les règles d’adaptation de gains.

---

**🔗 Voir aussi** : [Versions RETA](VERSIONS.md) · [Théorie Fondamentale](1_fondamentaux/theorie_fondamentale.md) · [Benchmarks](benchmarks.md)

---

[📖 Index de la Documentation](INDEX.md) · [🏠 Accueil du Projet](../README.md)

