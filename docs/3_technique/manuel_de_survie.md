# RETA v1.4 : Manuel de Survie & Fiche Technique
**Projet : Referential Escape Theory by Accumulation (RETA)**

Ce document est le guide de déploiement du système RETA. Il transforme la théorie mathématique en entité de contrôle autonome capable de survivre en environnement hostile — et de **prédire avec garantie de conservatisme** le moment de rupture.

---

## 1. Identité du Système

RETA v1.4 est un système auto-adaptatif à quatre couches :

| Couche | Rôle | Nouveauté v1.4 |
|---|---|---|
| **Kalman Q adaptatif** | Estimation biais à 88-93% avant panne GPS | — (v1.3) |
| **PI gradient** | Annulation dérive même après saut | — (v1.2) |
| **Kalman ḃ_true** | Tracking taux de dérive thermique | **Nouveau v1.4** |
| **Bound quadratique** | Prédiction t_rup toujours conservatif | **Nouveau v1.4** |

---

## 2. Les 4 Piliers de l'Autonomie

### I. Perception HD (Kalman Q Adaptatif — v1.3)
- Nettoie le signal et estime la dérive invisible $b_{est}$
- Auto-calibre $Q_{bias}$ via $|\nu|/T_{GPS}$ (drift rate d'innovation)
- Converge à 88-93% du biais vrai avant panne GPS

### II. Poigne d'Acier (PI Adaptatif — v1.2)
- Annule la dérive par accumulation
- Adapte $K_p$ et $K_i$ via gradient ($\dot{K}_p = \gamma_p \bar{e}^2$, $\dot{K}_i = \gamma_i \bar{e}\cdot\bar{I}$)
- Survit aux sauts de perturbation (z : 0.25 → 2.8, v1.1 rupture, v1.4 JAMAIS ✓)

### III. Tracker Thermique (Second Kalman ḃ_true — v1.4)
- État : $[b_{true},\ \dot{b}_{true}]^T$ — mis à jour à chaque GPS
- Capture le taux de dérive thermique intrinsèque (toujours positif)
- Critique : pendant la phase GPS, ż *décroît* (Kalman converge). Après GPS, ż *flip positif*. Extrapoler ż depuis le passé donne la mauvaise direction — seul ḃ_true est fiable.

### IV. L'Oracle Conservatif (Bound Quadratique — v1.4)
À la panne GPS (t₀), résoudre :

$$\dot{z}_0 \cdot \frac{T^2}{2} + z_0 \cdot T = Y_{max} - y(t_0)$$

$$\boxed{t_{rup} \leq t_0 + \frac{-z_0 + \sqrt{z_0^2 + 2\dot{z}_0(Y_{max}-y_0)}}{\dot{z}_0}}$$

**Garantie :** bound ≤ rupture réelle si estimation ḃ_true pessimiste ✓

---

## 3. Protocole de Déploiement

1. **Définir** : $f(t)$ (trajectoire idéale) + $Y_{max}$ (seuil de rupture)
2. **Initialiser** : $Q_{bias} = Q_{bias,0} \times 1000$ (a priori conservateur), second Kalman $[b_0, \dot{b}_0]$
3. **Phase GPS** (0 → T_outage) : Q_bias adapte, ḃ_true tracké, PI apprend
4. **Panne GPS** (t₀) : figer $\hat{b}_{est}$, calculer bound quadratique, activer alarme
5. **Dead-reckoning** : PI continue sur $\hat{\phi}_{est}$, bound mis à jour dynamiquement

---

## 4. Règles de Sécurité

| Danger | Symptôme | Réponse RETA |
|---|---|---|
| **Biais thermique croissant** | $\nu_k$ s'agrandit à chaque GPS | Q_bias ↑ automatiquement → $K_{bias}$ ↑ → convergence |
| **Panne GPS** | Plus de corrections disponibles | Bound quadratique activé — alarme conservatif ✓ |
| **z croît post-panne** | $b_{true}$ dérive, $\hat{b}_{est}$ figée | ḃ_true tracké → bound reste valide |
| **Bound v1.3 optimiste** | Prédit survie → rupture réelle avant | **Remplacé par bound v1.4 — erreur : +518s → −99s** |
| **Saut de perturbation** | Erreur explose soudainement | $K_p, K_i$ adaptent → retour à 0 ✓ |

---

## 5. Comparaison Versions — Choix de Déploiement

| Scénario | Version recommandée |
|---|---|
| Environnement stable, GPS permanent | v1.1 (simple, certifiable) |
| Perturbations variables, pas de GPS | v1.2 (PI adaptatif suffisant) |
| Biais thermique + GPS outage prévisible | v1.3 (estimation biais) |
| **Biais thermique + GPS outage + sécurité critique** | **v1.4 (bound conservatif garanti)** |

---

## 6. Synthèse Technique

- **Version courante :** 1.4
- **Architecture :** Boucle fermée stochastique adaptative + bound quadratique
- **Domaines :** Drone, navigation inertielle, finance, LLM, infrastructure
- **Propriété clé :** le bound ne ment jamais — il prédit toujours avant la rupture réelle

---

*RETA v1.4 : Prédire l'inévitable pour mieux l'annuler — avec garantie de conservatisme.*

---

## Navigation
- [📖 Index de la Documentation](../INDEX.md)
- [📖 Versions](../VERSIONS.md)
- [🏠 Accueil du Projet](../../README.md)
