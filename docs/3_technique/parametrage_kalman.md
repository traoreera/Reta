# Paramétrage Mathématique de Kalman (Q & R)
**Projet : Referential Escape Theory by Accumulation (RETA)**

RETA utilise maintenant deux filtres Kalman distincts selon la version déployée. Ce document couvre leur paramétrage.

---

## 1. Kalman Principal — Estimation de l'état [φ, b]

### R — Bruit de mesure GPS

**Méthode :** variance empirique sur des mesures statiques (drone posé, système stable).

$$R = \sigma_v^2 = \frac{1}{N} \sum (y_i - \bar{y})^2$$

**Valeurs typiques drone :**
- GPS standard : $R \approx 0.04\ °^2$ ($\sigma \approx 0.2°$)
- GPS dégradé : $R \approx 0.25\ °^2$ ($\sigma \approx 0.5°$)
- IMU seule : aucune correction GPS → $R$ inutilisé

**Signification :** plus le capteur est bruyant, plus $R$ est grand, plus le Kalman fait confiance au modèle plutôt qu'à la mesure instantanée.

### Q — Bruit de processus biais (v1.1 vs v1.3)

**v1.1 (Q fixe) :** hypothèse biais quasi-constant.

$$Q_{bias}^{v1.1} = \sigma_{bias}^2 \cdot dt, \quad \sigma_{bias} \approx 10^{-5}\ °/s$$

→ $K_{bias} \approx 0$ → biais jamais estimé → 0.6% de précision à t=120s.

**v1.3 (Q adaptatif) :** détection du drift rate depuis les innovations GPS.

$$\text{drift\_rate} = \frac{|\nu_k|}{T_{GPS}}, \quad Q_{bias}^{inst} = (\text{drift\_rate} \cdot dt)^2$$

$$Q_{bias}(t+dt) = (1-\alpha)\,Q_{bias}(t) + \alpha\,Q_{bias}^{inst}$$

Initialisation conservatrice : $Q_{bias}^{init} = Q_{bias}^{v1.1} \times 1000$.

→ Convergence biais à **88-93%** à t=120s.

### Ratio critique Q/R

| Ratio | Comportement | Usage |
|---|---|---|
| Q ≪ R | Filtre lent, lisse, peut rater les sauts | v1.1 biais stable |
| Q ≫ R | Filtre rapide, réactif, plus bruyant | Démarrage v1.3 |
| Q adaptatif | Réactivité calibrée selon le drift observé | **v1.3 et v1.4** |

---

## 2. Second Kalman — Tracking de ḃ_true (v1.4 uniquement)

Ce filtre estime le taux de dérive thermique intrinsèque du biais gyro.

**État :** $\mathbf{x}_{bt} = [b_{true},\ \dot{b}_{true}]^T$

**Modèle de transition (rampe lente) :**

$$A_{bt} = \begin{pmatrix}1 & dt \\ 0 & 1\end{pmatrix}, \quad Q_{bt} = \text{diag}(10^{-8},\ 10^{-10})$$

$Q_{bt}$ très petit car la dérive thermique est lisse (constante de temps ~80s).

**Observation à chaque GPS :** $b_{true}^{obs} \approx \hat{b}_{est}$ après correction GPS (la correction GPS aligne $\hat{b}_{est}$ vers $b_{true}$).

$$R_{bt} = 10^{-3}\ (°/s)^2$$

**Initialisation :** $\mathbf{x}_{bt}^{(0)} = [B_0,\ \dot{b}_{init}]^T$ où $\dot{b}_{init}$ peut être zéro (convergera rapidement).

**Propriété clé :** $\hat{\dot{b}}_{true} > 0$ garanti (drift thermique positif) — à l'inverse de ż qui peut être négatif pendant la phase de convergence GPS.

---

## 3. Paramétrage PI Adaptatif (v1.2+)

**Gains initiaux :** $K_p^{(0)}, K_i^{(0)}$ dimensionnés pour la perturbation nominale.

**Lois d'adaptation (gradient) :**

$$\dot{K}_p = \gamma_p \bar{e}^2, \quad \dot{K}_i = \gamma_i \bar{e}\cdot\bar{I}, \quad \bar{e} = e / e_{ref}$$

**Réglage pratique :**

| Paramètre | Rôle | Valeur drone |
|---|---|---|
| $e_{ref} = Y_{max}/2$ | Normalisation erreur | 2.5° |
| $\gamma_p$ | Vitesse d'apprentissage Kp | 0.2 |
| $\gamma_i$ | Vitesse d'apprentissage Ki | 0.05 |
| $K_p \in [1, 20]$ | Bornes Kp | Physiques |
| $K_i \in [0.5, 40]$ | Bornes Ki | Physiques |

---

## 4. Récapitulatif par version

| Composant | v1.1 | v1.2 | v1.3 | v1.4 |
|---|---|---|---|---|
| R GPS | Fixe | Fixe | Fixe | Fixe |
| Q biais | Fixe petit | Fixe | **Adaptatif EMA** | Adaptatif EMA |
| PI | Fixe | **Gradient** | Gradient | Gradient |
| Second Kalman ḃ_true | — | — | — | **[b_true, ḃ_true]** |

---

**📂 Section 3 — Technique & Implémentation**
[Méthodologie](methodologie.md) · [Paramétrage Kalman](parametrage_kalman.md) · [Fusion de Référentiels](fusion_referentiels.md) · [Efficience Mémoire](efficience_memoire.md) · [Manuel de Survie](manuel_de_survie.md)

**🔗 Voir aussi** : [Théorie Fondamentale](../1_fondamentaux/theorie_fondamentale.md) · [Extension Dimensionnelle](../2_extensions_theoriques/extension_dimensionnelle.md) · [Versions RETA](../VERSIONS.md)

---

[📖 Index de la Documentation](../INDEX.md) · [🏠 Accueil du Projet](../../README.md)
