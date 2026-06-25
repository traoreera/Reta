# RETA en Intelligence Artificielle & LLM

## Vue d'ensemble

Les systèmes d'IA accumulent plusieurs types de dérives : dérive sémantique dans les conversations longues, dégradation des performances sous distribution shift, accumulation de biais au fil du fine-tuning. RETA fournit un cadre formel pour détecter, quantifier et corriger ces dérives.

---

## 1. Dérive Sémantique dans les Conversations Longues (LLM)

### Problème
Un LLM en conversation longue s'éloigne progressivement du sujet initial. Le modèle "oublie" le contexte initial (window overflow), ou l'utilisateur introduit des digressions qui accumulent une dérive thématique. La conversation devient incohérente au bout de $k$ tours.

### Modèle RETA

| Variable | Définition concrète |
|---|---|
| $y(t)$ | Distance sémantique au sujet initial (embedding cosine distance) |
| $f(t)$ | Trajectoire idéale : distance nulle si le sujet est maintenu |
| $z(t)$ | Taux de dérive par tour : $z_k = \lVert \text{embed}(\text{tour}_k) - \text{embed}(\text{sujet\_initial})\rVert$ |
| $Y_{max}$ | Seuil d'incohérence thématique (ex. : distance cosine > 0.4) |
| $t_{rupture}$ | Tour $k^*$ à partir duquel la conversation dérive irrémédiablement |

### Compression RETA de la mémoire (implémentée dans ce projet)

Au lieu de stocker $k$ tours complets en O(n·k) tokens :

$$\text{TurnSignature}_k = (\varepsilon_k,\ \text{type},\ \Delta y_k,\ z̄_k,\ \text{label})$$

Coût : **15 tokens** par tour, compression **236× à k=25**.

La reconstruction exacte est garantie à : erreur ≤ $P_\infty \cdot k = 0{,}4316 \cdot k$.

### Correcteur PI dans ce contexte

Quand la dérive $y(t) > Y_c$ (seuil de rappel thématique) :

$$u_k = K_p \cdot (y_k - Y_c) + K_i \sum_{j=0}^{k} (y_j - Y_c)$$

Le modèle injecte une instruction de recadrage dans le system prompt : "Rappel : le sujet initial est X".

### Valeur ajoutée RETA
- **Classique :** Résumé manuel, truncation de contexte, RAG — réactifs
- **RETA :** Prédiction du tour de rupture, injection préventive du correcteur avant la dérive

---

## 2. Distribution Shift et Dégradation des Modèles en Production

### Problème
Un modèle déployé en production observe une dégradation progressive de ses performances quand la distribution des données entrantes s'éloigne de la distribution d'entraînement. Ce phénomène est continu et insidieux.

### Modèle RETA

| Variable | Définition concrète |
|---|---|
| $y(t)$ | Métrique de performance courante (F1, AUC, accuracy) — en dégradation |
| $f(t)$ | Performance basale attendue (stable sur distribution d'entraînement) |
| $z(t)$ | Taux de distribution shift : $z = \text{PSI}(P_{train}, P_t)$ (Population Stability Index) |
| $Y_{max}$ | Seuil de performance minimale acceptable (ex. : F1 < 0.7 → retrait du modèle) |
| $t_{rupture}$ | Date estimée de dépassement du seuil $Y_{max}$ |

### Calcul du PSI comme perturbation z(t)

$$\text{PSI} = \sum_{i=1}^{n} (P_{actual,i} - P_{expected,i}) \cdot \ln\left(\frac{P_{actual,i}}{P_{expected,i}}\right)$$

- PSI < 0.1 : pas de drift significatif ($z < \varepsilon$)
- 0.1 < PSI < 0.25 : drift modéré (signal d'alerte)
- PSI > 0.25 : drift sévère, $t_{rupture}$ proche

### Correcteur PI dans ce contexte

$$u(t) = K_p \cdot (\text{PSI}(t) - \text{PSI}_{cible}) + K_i \int \text{PSI}\,d\tau$$

Actions du correcteur (par ordre de Ki croissant) :
1. Recalibration des seuils de décision
2. Re-pondération des features
3. Fine-tuning sur données récentes
4. Réentraînement complet

### Valeur ajoutée RETA
- **Classique :** Monitoring avec alertes réactives (performance déjà dégradée)
- **RETA :** $t_{rupture}$ estimé des semaines à l'avance, budget de réentraînement planifiable

---

## 3. Accumulation de Biais lors du Fine-Tuning Continu (RLHF / DPO)

### Problème
Un modèle soumis à du fine-tuning continu (RLHF, DPO, online learning) accumule des biais cumulatifs qui peuvent mener à un collapse catastrophique (reward hacking, mode collapse, oubli catastrophique).

### Modèle RETA

| Variable | Définition concrète |
|---|---|
| $y(t)$ | Divergence KL entre le modèle courant et le modèle de référence : $D_{KL}(M_t \| M_0)$ |
| $z(t)$ | Taux d'accumulation de biais par epoch : $z = \mathbb{E}[\Delta D_{KL}]$ par epoch |
| $Y_{max}$ | Seuil de divergence tolérable avant dégradation des capacités générales |
| $t_{rupture}$ | Nombre d'epochs avant collapse |

### Correcteur PI dans ce contexte

Le correcteur implémente un **KL penalty dynamique** :

$$u(t) = K_p \cdot D_{KL}(M_t \| M_{ref}) + K_i \int D_{KL}\,d\tau$$

C'est exactement le terme de régularisation KL de PPO/DPO, mais avec des gains adaptatifs auto-réglés.

### Valeur ajoutée RETA
- **Classique :** KL penalty fixe dans PPO — souvent mal calibré
- **RETA :** Gains Kp et Ki auto-adaptés (v1.2/v1.3) selon la vitesse de drift

---

## 4. Dérive de Prompt et Jailbreak Cumulatif

### Problème
Un attaquant peut induire une dérive comportementale progressive en soumettant une séquence de prompts qui, individuellement, semblent innocents mais accumulent un biais dans le comportement du modèle.

### Modèle RETA

| Variable | Définition concrète |
|---|---|
| $y(t)$ | Score de sécurité de la réponse (détecteur d'alignement) |
| $z(t)$ | Taux de drift comportemental par prompt : variation du score de sécurité |
| $Y_{max}$ | Seuil de comportement non-aligné |
| $t_{rupture}$ | Nombre de turns avant que le modèle produise une réponse non-alignée |

### Valeur ajoutée RETA
- **Classique :** Classifieur binaire sur chaque réponse — aveugle à l'accumulation
- **RETA :** Détecte la trajectoire cumulative, alerte avant le jailbreak effectif

---

## Tableau Récapitulatif

| Application IA | $y(t)$ | $z(t)$ | $Y_{max}$ | Correcteur PI |
|---|---|---|---|---|
| Dérive sémantique LLM | Distance thématique | Drift par tour | Seuil incohérence | Injection rappel contexte |
| Distribution shift | F1 / AUC courant | PSI distribution | F1 minimum | Recalibration / retrain |
| Biais fine-tuning | $D_{KL}(M_t \| M_0)$ | ΔKL par epoch | Divergence max | KL penalty adaptatif |
| Jailbreak cumulatif | Score alignement | Drift comportemental | Seuil non-aligné | Recadrage system prompt |

---

*[📖 Index domaines](README.md) · [📖 Index global](../INDEX.md)*
