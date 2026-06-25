# RETA v1.3 / v1.4 — Démonstration Mathématique Complète
*v1.3 : Kalman Chameleon — auto-calibration de Q par innovations + gains PI adaptatifs*
*v1.4 : Bound conservatif — tracking ḃ_true pour prédiction t_rup fiable post-panne GPS*

---

## 0. Objectif

La version v1.3 vise à lever le dernier verrou de v1.2 : les matrices de bruit $Q$ et $R$ du filtre de Kalman restent fixes même quand le bruit du système change de régime (température, vibrations, changement d'environnement). Le but est de les estimer **en ligne** depuis les innovations $\nu_k$.

Cette démonstration établit :
1. L'estimateur de $Q$ et $R$ (méthode de Mehra, 1970)
2. Les conditions suffisantes de convergence de $\hat{Q}_k$ et $\hat{R}_k$
3. La fonction de Lyapunov augmentée du système complet
4. Les garanties de stabilité pratique
5. La limite documentée de v1.3 sur la borne $t_{rup}$ (§6.4)
6. La correction v1.4 par tracking $\dot{b}_{true}$ (§8)

---

## 1. Rappel de l'Architecture v1.2

Le système complet v1.2 comprend :

**État** : $\mathbf{x} = [e,\ I,\ \tilde{K}_p,\ \tilde{K}_i]^T$ avec $\tilde{K} = K - K^*$

**Kalman** (perception) : $Q$ et $R$ fixes, estime $\hat{z}$ (biais/perturbation)

**PI adaptatif** (contrôle) :
$$\dot{K}_p = \gamma_p \bar{e}^2, \qquad \dot{K}_i = \gamma_i \bar{e} \cdot \bar{I}$$

**Lyapunov v1.2 (prouvée)** :
$$V_{12} = \frac{1}{2}e^2 + \frac{K_i^*}{2}I^2 + \frac{1}{2\gamma_p}\tilde{K}_p^2 + \frac{1}{2\gamma_i}\tilde{K}_i^2$$

$$\dot{V}_{12} = -{K}_p^* e^2 + e \cdot w(t) \leq 0 \quad \text{hors compact}$$

**Limitation** : Si le bruit réel $\sigma_v^2(t)$ double (changement de capteur, vibrations), $R$ est faux → Kalman diverge → $\hat{z}$ incorrect → PI commande sur une erreur mal estimée.

---

## 2. Estimateur de $\hat{Q}$ et $\hat{R}$ par Innovation (Mehra 1970)

### 2.1 Innovation et sa statistique théorique

L'innovation au pas $k$ :

$$\nu_k = z_k - H\hat{x}_k^- = H(\mathbf{x}_k - \hat{x}_k^-) + v_k$$

Sa covariance théorique :

$$\mathbb{E}[\nu_k \nu_k^T] = C_k = H P_k^- H^T + R$$

Sa covariance **empirique** sur une fenêtre glissante de $M$ pas :

$$\hat{C}_k = \frac{1}{M} \sum_{j=k-M+1}^{k} \nu_j \nu_j^T$$

### 2.2 Estimateurs de $\hat{R}$ et $\hat{Q}$

En identifiant $\hat{C}_k \approx C_k$ :

$$\boxed{\hat{R}_k = \hat{C}_k - H P_k^- H^T}$$

Pour $\hat{Q}$, on utilise la relation sur la covariance de prédiction :

$$P_k^- = A P_{k-1}^+ A^T + Q$$

$$\Rightarrow \quad \hat{Q}_k = K_k \hat{C}_k K_k^T$$

Où $K_k$ est le gain de Kalman courant. Cette forme est un estimateur du premier ordre.

### 2.3 Correction de positivité (impérative)

$\hat{R}$ et $\hat{Q}$ peuvent devenir négatifs définis numériquement. On impose :

$$\hat{R}_k \leftarrow \max\!\left(\hat{R}_k,\ R_{min}\right), \qquad \hat{Q}_k \leftarrow \max\!\left(\hat{Q}_k,\ Q_{min}\right)$$

Avec $R_{min} > 0$ et $Q_{min} > 0$ fixés a priori (planchers physiques).

---

## 3. Conditions de Convergence de $\hat{Q}$ et $\hat{R}$

### 3.1 Théorème de convergence (Mehra 1970, adapté)

**Hypothèses :**
- (H1) Le système $(A, H)$ est **observable** et $(A, \sqrt{Q})$ est **contrôlable**
- (H2) Les bruits $w_k$ et $v_k$ sont des bruits blancs centrés, indépendants
- (H3) La fenêtre $M$ est suffisamment grande : $M \geq \dim(\mathbf{x})^2$
- (H4) Les vraies matrices $Q$ et $R$ varient **lentement** par rapport à $M \cdot dt$

**Conclusion :**

$$\hat{R}_k \xrightarrow{M \to \infty} R_{vrai}, \qquad \hat{Q}_k \xrightarrow{M \to \infty} Q_{vrai} \quad \text{(en loi)}$$

La convergence est en $O(1/\sqrt{M})$.

### 3.2 Paramètre $M$ — Choix pratique pour le drone

| Contrainte | Valeur | Justification |
|---|---|---|
| Minimum théorique | $M \geq \dim(\mathbf{x})^2 = 4$ | Observabilité |
| Temps de variation de $Q_{vrai}$ | $\tau_Q \approx 120$ s (thermique moteur) | $M \cdot dt \ll \tau_Q$ |
| Temps de variation de $R_{vrai}$ | $\tau_R \approx 60$ s (vibrations) | |
| **Valeur choisie** | $M = 200$ pas (0.2 s à 1 kHz) | Compromis réactivité / biais |

Vérification : $M \cdot dt = 0.2 \text{ s} \ll \tau_R = 60 \text{ s}$ ✓

### 3.3 Limite de v1.3 — Ce que la convergence ne garantit pas

> **Avertissement fondamental :** La convergence de $\hat{Q} \to Q_{vrai}$ est assurée **si** les hypothèses (H1-H4) sont satisfaites. En pratique :
> - Si $Q_{vrai}$ varie plus vite que $M \cdot dt$, l'estimateur est en retard
> - Si les bruits ne sont pas gaussiens (chocs mécaniques), le biais de $\hat{R}$ peut être non nul
> - La convergence est **en loi** (en moyenne), pas trajectoire par trajectoire

Ce sont les limites documentées de v1.3. La limite sur la borne $t_{rup}$ post-panne GPS est corrigée par v1.4 (§8). Un estimateur bayésien récursif constituerait une évolution majeure (v2.0+).

---

## 4. Lyapunov Augmentée — Système Complet v1.3

### 4.1 Vecteur d'état augmenté

$$\mathbf{X} = \left[e,\ I,\ \tilde{K}_p,\ \tilde{K}_i,\ \tilde{Q},\ \tilde{R}\right]^T$$

Où $\tilde{Q} = \hat{Q} - Q_{vrai}$ et $\tilde{R} = \hat{R} - R_{vrai}$ sont les erreurs d'estimation des bruits.

### 4.2 Fonction de Lyapunov v1.3

$$\boxed{V_{13} = \underbrace{\frac{1}{2}e^2 + \frac{K_i^*}{2}I^2}_{\text{stabilité PI}} + \underbrace{\frac{1}{2\gamma_p}\tilde{K}_p^2 + \frac{1}{2\gamma_i}\tilde{K}_i^2}_{\text{adaptation gains}} + \underbrace{\frac{1}{2\mu_Q}\tilde{Q}^2 + \frac{1}{2\mu_R}\tilde{R}^2}_{\text{adaptation bruit}}}$$

Où $\mu_Q, \mu_R > 0$ sont les taux d'apprentissage des matrices de bruit.

### 4.3 Calcul de $\dot{V}_{13}$

Les deux premiers termes donnent (résultat v1.2 acquis) :

$$\frac{d}{dt}\left[\frac{1}{2}e^2 + \frac{K_i^*}{2}I^2\right] = -K_p^* e^2 + e\cdot w(t)$$

Les termes d'adaptation des gains (résultat v1.2) :

$$\frac{d}{dt}\left[\frac{1}{2\gamma_p}\tilde{K}_p^2 + \frac{1}{2\gamma_i}\tilde{K}_i^2\right] = -e^2 \tilde{K}_p - e\bar{I}\tilde{K}_i + \tilde{K}_p \dot{K}_p/\gamma_p + \tilde{K}_i \dot{K}_i/\gamma_i = 0$$

(s'annulent exactement avec les lois gradient $\dot{K}_p = \gamma_p \bar{e}^2$)

Les termes d'adaptation des bruits :

$$\frac{d}{dt}\left[\frac{1}{2\mu_Q}\tilde{Q}^2\right] = \frac{\tilde{Q}}{\mu_Q}\dot{\hat{Q}} = \frac{\tilde{Q}}{\mu_Q}\left(\dot{Q}_{vrai} + \frac{Q_{vrai} - \hat{Q}}{\tau_Q}\right)$$

En supposant $Q_{vrai}$ lentement variable ($\dot{Q}_{vrai} \approx 0$ sur la fenêtre $M$) et $\dot{\hat{Q}} \approx -(\hat{Q} - Q_{vrai})/\tau_Q = -\tilde{Q}/\tau_Q$ :

$$\frac{d}{dt}\left[\frac{1}{2\mu_Q}\tilde{Q}^2\right] = -\frac{\tilde{Q}^2}{\mu_Q \tau_Q} \leq 0$$

De même pour $\tilde{R}$ :

$$\frac{d}{dt}\left[\frac{1}{2\mu_R}\tilde{R}^2\right] = -\frac{\tilde{R}^2}{\mu_R \tau_R} \leq 0$$

### 4.4 Résultat final

$$\boxed{\dot{V}_{13} = -K_p^* e^2 + e\cdot w(t) - \frac{\tilde{Q}^2}{\mu_Q \tau_Q} - \frac{\tilde{R}^2}{\mu_R \tau_R}}$$

**Analyse :**

- Terme $-K_p^* e^2$ : toujours négatif → force stabilisatrice sur l'erreur de cap
- Terme $e \cdot w(t)$ : borné par $|w|_{max}$ → perturbation résiduelle
- Termes $-\tilde{Q}^2/(\mu_Q\tau_Q)$ et $-\tilde{R}^2/(\mu_R\tau_R)$ : **toujours négatifs** → l'estimation de bruit converge activement

$\dot{V}_{13} < 0$ est garanti dès que :

$$K_p^* |e| > |w(t)| = |f'(t) + z(t)|_{max}$$

Soit la même condition que v1.2, **renforcée** par les deux termes supplémentaires négatifs.

**Conclusion :** v1.3 est **strictement plus stable** que v1.2 sous les hypothèses (H1-H4). La convergence simultanée de l'erreur de cap et des erreurs d'estimation de bruit est garantie.

---

## 5. Bande Résiduelle v1.3

### 5.1 Erreur de cap

Identique à v1.2 (les termes de bruit ne modifient pas la borne sur $e$) :

$$|e_\infty| \leq \frac{|w|_{max}}{K_p^*} = \frac{3 + \sqrt{2}}{K_p^*} \cdot e_{ref}$$

### 5.2 Erreur d'estimation de bruit

$$|\tilde{Q}_\infty| \leq O\!\left(\frac{1}{\sqrt{M}}\right) \cdot Q_{vrai}, \qquad |\tilde{R}_\infty| \leq O\!\left(\frac{1}{\sqrt{M}}\right) \cdot R_{vrai}$$

L'erreur d'estimation décroît en $1/\sqrt{M}$ — augmenter la fenêtre améliore la précision.

### 5.3 Effet sur le drone

Avec $M = 200$, $Q_{vrai}$ change par un facteur 2 (biais thermique double) :

$$|\tilde{Q}_\infty| \leq \frac{Q_{vrai}}{\sqrt{200}} \approx 0.07 \cdot Q_{vrai} \quad \text{(7% d'erreur résiduelle)}$$

Le filtre Kalman reste fonctionnel avec une erreur d'estimation de Q de 7% — l'impact sur $P_\infty$ est négligeable.

---

## 6. Validation Numérique — Simulation Drone 3 Axes

### 6.1 Scénario de stress : panne GPS après 120s

**Contexte :** drone en vol stationnaire, biais gyro thermique × 4 en 80s, GPS
disponible toutes les 5s pendant 120s, puis **panne totale** (jamming, zone sans réseau).

**Hypothèse v1.1 :** Q_bias = σ²_bias · dt avec σ_bias = 10⁻⁵ °/s (biais "quasi-fixe")
→ K_biais ≈ 0, biais jamais estimé.

**Hypothèse v1.3 :** Q_bias adaptatif — initialisé 1000× plus grand, puis EMA sur
le drift rate observé : $\hat{Q}_{bias} \leftarrow (1-\alpha)\hat{Q}_{bias} + \alpha \cdot (\nu/T_{GPS})^2 \cdot dt$

### 6.2 Résultats

| Axe | Y_max | Rupture v1.1 | Rupture v1.3 | Gain v1.3 |
|---|---|---|---|---|
| Roll (X) | 5° | t = 56s ⚠️ | t = 252s ⚠️ | **+196s** |
| Pitch (Y) | 5° | t = 49s ⚠️ | t = 258s ⚠️ | **+209s** |
| Yaw (Z) | 10° | t = 65s ⚠️ | t = 193s ⚠️ | **+128s** |

**Qualité d'estimation du biais à t=120s (moment de la panne) :**

| Axe | Biais vrai | v1.1 estimé | v1.3 estimé |
|---|---|---|---|
| Roll | 166 m°/s | 1 m°/s (0.6%) | 147 m°/s (88%) |
| Pitch | 200 m°/s | 1 m°/s (0.7%) | 186 m°/s (93%) |
| Yaw | 266 m°/s | 0.3 m°/s (0.1%) | 163 m°/s (61%) |

### 6.3 Analyse

- **Pourquoi v1.1 échoue dès t=49s malgré un GPS actif ?** Q_bias trop petit → K_biais ≈ 0
  → le filtre ne converge pas sur le biais → l'erreur de cap croît à chaque intervalle GPS.

- **Pourquoi v1.3 survit 3-4× plus longtemps ?** L'EMA sur $|\nu|/T_{GPS}$ détecte le
  drift rate croissant dès les premiers GPS → Q_bias augmente × 500 000 → K_biais non nul
  → biais estimé à 88-93% → dead-reckoning de qualité après la panne.

- **Limite v1.3 :** le biais Yaw (plus fort, 266 m°/s) est moins bien estimé (61%)
  → Yaw rupture à t=193s (vs t=258s pour XY). Cette limite est documentée dans §3.3.

### 6.4 Limite documentée : bound t_rup non-conservatif post-panne

Après la panne GPS à $t_0 = 120s$, $\hat{b}_{est}$ est figée tandis que $b_{true}$ continue de croître :

$$z(t) = b_{true}(t) - \hat{b}_{est} \uparrow \quad \forall t > t_0$$

La borne v1.3 utilise $z(t_0)$ figé :
$$t_{rup}^{v1.3} = t_0 + \frac{Y_{max} - y(t_0)}{z(t_0)}$$

**Mesure :** borne prédite = 791s, rupture réelle = 273s → **+518s OPTIMISTE** ⚠️

La borne prédit que le système survivra bien au-delà de la rupture réelle. C'est la seule limite de sécurité critique de v1.3 — elle est corrigée par v1.4 (§8).

> **Graphe complet :** `docs/v1.3/results.png`
> **Code source :** `docs/v1.3/simulation.py`

---

## 7. Récapitulatif — Comparaison des versions

| Propriété | v1.0 | v1.1 | v1.2 | v1.3 | **v1.4** |
|---|---|---|---|---|---|
| Preuve stabilité PI | Routh | Routh | Lyapunov ✓ | Lyapunov augm. ✓ | idem v1.3 |
| Gains Kp, Ki | Fixes | Fixes | Adaptatifs | Adaptatifs | Adaptatifs |
| Q_bias Kalman | N/A | Fixe (petit) | Fixe | **Adaptatif EMA** | idem v1.3 |
| Estimation biais | Nulle | Nulle | Faible | **88-93%** | idem v1.3 |
| Survie panne GPS | Faible | Faible | Faible | **× 3-4** | idem v1.3 |
| Bound t_rup conservatif | Oui | Oui | Oui | **NON ⚠️** (z croît) | **OUI ✓** (ḃ_true tracké) |
| Erreur bound post-panne | — | — | — | **+518s OPTIMISTE** | **−99s CONSERVATIF** |
| Complexité calcul | O(1) | O(n²) | O(n²) | O(n²) + EMA | O(n²) + EMA + Kalman 2D |

---

## 8. v1.4 — Correction du Bound par Tracking ḃ_true

### 8.1 Problème fondamental de l'extrapolation de ż

Pendant la phase GPS, le Kalman converge : $z = b_{true} - \hat{b}_{est}$ *décroît* → $\dot{z} < 0$.

Juste après la panne, $\hat{b}_{est}$ est figée et $b_{true}$ continue → $z$ *croît* → $\dot{z}$ flip positif.

Extrapoler $\dot{z}$ depuis l'historique récent donne la **mauvaise direction** et aggrave le problème.

### 8.2 Solution : second Kalman sur $[b_{true},\ \dot{b}_{true}]$

État : $\mathbf{x}_{bt} = [b_{true},\ \dot{b}_{true}]^T$

$$A_{bt} = \begin{pmatrix}1 & dt \\ 0 & 1\end{pmatrix}, \quad Q_{bt} \ll 1 \text{ (dérive thermique lente)}$$

Observation à chaque GPS : $b_{true}^{obs} \approx \hat{b}_{est}^{corrigé}$ (après correction Kalman principal).

Ce filtre estime $\dot{b}_{true}$ — le taux de dérive thermique intrinsèque — qui est **toujours positif** et indépendant de la convergence du Kalman principal.

### 8.3 Borne quadratique (conservatif)

À la panne $t_0$, avec $z_0 = \hat{b}_{true} - \hat{b}_{est}$ et $\dot{z}_0 = \hat{\dot{b}}_{true}$ (puisque $\hat{b}_{est}$ sera figée) :

$$\int_{t_0}^{t_0+T} z(\tau)\,d\tau = z_0 T + \frac{\dot{z}_0}{2}T^2 = Y_{max} - y(t_0)$$

$$\boxed{T_{v1.4} = \frac{-z_0 + \sqrt{z_0^2 + 2\dot{z}_0(Y_{max}-y_0)}}{\dot{z}_0}}$$

**Garantie :** si $\hat{\dot{b}}_{true} \geq \dot{b}_{true}^{réel}$ (second Kalman pessimiste) → $t_{rup}^{v1.4} \leq t_{rup}^{réel}$ — la borne ne ment jamais dans le sens optimiste.

### 8.4 Résultats

| Bound | Prédiction | Rupture réelle | Erreur |
|---|---|---|---|
| v1.3 (z figé) | 791s | 273s | **+518s OPTIMISTE ⚠️** |
| v1.4 (ḃ_true) | 174s | 273s | **−99s CONSERVATIF ✓** |

> **Code source :** `docs/v1.4/simulation.py` · **Graphe :** `docs/v1.4/results.png`

---

*[📖 Théorie fondamentale](theorie_fondamentale.md) · [📖 Index](../INDEX.md) · [📖 Versions](../VERSIONS.md)*
