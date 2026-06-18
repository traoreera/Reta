# Théorie de l'Évasion Référentielle par Accumulation
*Synthèse complète — Version corrigée et annotée*

---

## Hypothèse Générale

> « Un système dynamique initialement borné dans un espace fini peut s'échapper de ses limites et tendre vers l'infini si on lui insuffle une **perturbation persistante** strictement positive et persistante dans le temps. L'intégration temporelle de cette perturbation détruit l'asymptote d'origine, transformant le temps en facteur déterminant de la trajectoire. Cette dynamique permet à la fois de prédire le point de rupture du système et de concevoir une force artificielle de régulation capable d'annuler la dérive. »

> **Note terminologique :** Le terme "bruit" (stochastique) a été remplacé par **perturbation persistante bornée inférieurement**, car z(t) est déterministe (z(t) ≥ ε > 0 à tout instant).

---

## 1. Le Système Initial Bloqué (sans perturbation)

La fonction de base f(t) est strictement croissante mais piégée par une limite finie L.

**Exemple canonique :** f(t) = arctan(t)

$$\lim_{t \to +\infty} f(t) = L = \frac{\pi}{2}$$

**Interprétation :** f'(t) → 0 quand t → +∞. Le système « s'endort » et sa dynamique devient négligeable.

---

## 2. Le Système Libre Perturbé — Prédiction de la dérive

### 2.1 Condition nécessaire de dérive

$$z(t) \geq \varepsilon > 0 \quad \forall t \geq 0$$

**Justification :** si z(t) ≥ ε > 0, alors par comparaison avec ∫ε dτ = ε·t → +∞, l'intégrale ∫z(τ)dτ diverge (critère de Cauchy). La condition d'évasion est validée.

#### Classes de systèmes où cette condition est physiquement garantie

| Système | Justification de z(t) ≥ ε |
|---|---|
| Dérive thermique unidirectionnelle | 2ème loi thermodynamique (irréversible) |
| Inflation économique structurelle | Données historiques : toutes économies stables |
| Accumulation buffer (système actif) | Débit entrant > 0 par conception |
| Dégradation batterie / composant | Irréversibilité physique |
| Vent latéral dominant | Flux atmosphérique moyen (condition affaiblie) |

**Systèmes hors-cadre** (RETA non applicable directement) :
- Turbulence oscillante de moyenne nulle
- Bruit gaussien centré (E[z] = 0)
- Perturbations négatives dominantes (contraction nette)

#### Condition affaiblie pour systèmes à oscillations

Lorsque z(t) oscille mais reste positive en moyenne, on substitue la condition stricte par :

$$\bar{z}(T) = \frac{1}{T}\int_0^T z(t)\,dt \geq \varepsilon > 0$$

Le temps de rupture s'exprime alors avec la perturbation moyenne : $t_{\text{rup}} \geq (Y_{\max} - 1{,}57)/\bar{z}$.

### 2.2 Perturbation déterministe périodique choisie

$$z(t) = 2 + \sin(t) + \cos(t)$$

- Valeur minimale de sin(t) + cos(t) : −√2 ≈ −1,41
- Constante de surélévation : 2
- **ε garanti :** ε = 2 − √2 ≈ **0,59 > 0** ✓

### 2.3 Modèle continu

$$y(t) = f(t) + \int_{0}^{t} z(\tau) \, d\tau$$

### 2.4 Calcul analytique de la trajectoire libre

$$\int_{0}^{t} 2 \, d\tau = 2t$$

$$\int_{0}^{t} \sin(\tau) \, d\tau = 1 - \cos(t)$$

$$\int_{0}^{t} \cos(\tau) \, d\tau = \sin(t)$$

**Équation maîtresse de la dérive :**

$$\boxed{y(t) = \arctan(t) + 2t + \sin(t) - \cos(t) + 1}$$

### 2.5 Modèle discret (étape par étape)

$$y_{n+1} = y_n + [f_{n+1} - f_n] + z_{n+1}$$

$$y_n = f_n + \sum_{k=1}^{n} z_k$$

### 2.6 Vitesse de dérive

$$\frac{dy}{dt} = \frac{1}{1+t^2} + 2 + \cos(t) - \sin(t)$$

Quand t → +∞, le terme 1/(1+t²) → 0 :

$$\frac{dy}{dt} \xrightarrow{t \to +\infty} 2 + \cos(t) - \sin(t)$$

**Interprétation :** à long terme, c'est la perturbation z(t) qui gouverne seule la dynamique. Le terme 2t domine avec une vitesse moyenne de 2, sur laquelle se superpose une oscillation permanente d'amplitude √2 (car max|cos(t) − sin(t)| = √(1²+1²) = √2).

---

## 3. Calcul du Point de Rupture Physique

Soit Y_max la borne physique maximale tolérée. Le temps critique t_rupture vérifie l'équation transcendante :

$$Y_{max} = \arctan(t_{rupture}) + 2t_{rupture} + \sin(t_{rupture}) - \cos(t_{rupture}) + 1$$

**Estimation conservatrice de sécurité** (z = ε constant, borne pessimiste garantie) :

$$t_{rupture} \geq \frac{Y_{max} - \frac{\pi}{2}}{\varepsilon} = \frac{Y_{max} - 1{,}57}{0{,}59}$$

**Application numérique pour Y_max = 10 :**

$$t_{rupture} \geq \frac{10 - 1{,}57}{0{,}59} \approx \mathbf{14{,}28 \text{ secondes}}$$

> **Remarque :** Cette borne est conservative. Le système réel atteint Y_max plus tôt, car z(t) oscille souvent au-dessus de ε.

---

## 4. Le Système Contrôlé — Régulation par correcteur PI

### 4.1 Définition de l'erreur

$$\text{Erreur}(t) = y(t) - Y_{consigne}$$

### 4.2 Correcteur PI (version corrigée)

$$\boxed{u(t) = K_p \cdot \text{Erreur}(t) + K_i \int_{0}^{t} \text{Erreur}(\tau) \, d\tau}$$

- **Kp** : gain proportionnel — réaction immédiate à l'erreur courante
- **Ki** : gain intégral — correction de l'erreur accumulée dans le temps

> **Correction apportée :** Le correcteur I pur (Kp=0) de l'ébauche initiale a été remplacé par un correcteur PI. Le correcteur I seul est lent et sujet à l'emballement intégral (integrator windup).

### 4.3 Équation maîtresse globale (système régulé)

$$\boxed{y_{réel}(t) = f(t) + \int_{0}^{t} z(\tau) \, d\tau - K_p \cdot \text{Erreur}(t) - K_i \int_{0}^{t} \text{Erreur}(\tau) \, d\tau}$$

### 4.4 Concept de Contre-Force Dynamique (Analysie de la Stabilisation)

Pour stabiliser un système en constante évasion, RETA ne se contente pas de réagir aux écarts ; elle génère une **contre-force dynamique** qui annule la source de la dérive.

#### L'Analogie du Vent de Face
Imaginez un avion volant face à un vent de face constant et puissant (le "bruit d'accumulation" $\int z(\tau) d\tau$) :
*   **Sans RETA** : Le vent ralentit l'avion, puis le fait reculer. L'erreur s'accumule jusqu'à la rupture ($t_{rupture}$).
*   **Avec RETA** : 
    *   Le terme **Proportionnel ($K_p$)** détecte l'écart de position et ajuste les gaz instantanément.
    *   Le terme **Intégral ($K_i$)** mesure la force cumulée du vent. Il apprend sa persistance et finit par commander une poussée moteur qui devient l'image miroir exacte de la force du vent.

#### Neutralisation Mathématique
À l'équilibre stable, l'action du régulateur annule mathématiquement l'intégrale de la perturbation :
$$\underbrace{K_i \int \text{Erreur}(\tau) \, d\tau}_{\text{Contre-force}} \approx \underbrace{\int z(\tau) \, d\tau}_{\text{Force d'évasion}}$$

Le système ne "stagne" pas passivement ; il maintient activement sa position en développant une force opposée identique à la poussée qui tente de le faire sortir de ses bornes. C'est ce qui permet à RETA de stabiliser des systèmes intrinsèquement divergents.

---

## 5. Les Trois Temps Caractéristiques du Système

### 5.1 Temps de montée (t_montée)

Temps pour passer de 10% à 90% de la consigne Y_c :

$$\Delta t_{montée} = t_{90\%} - t_{10\%}$$

avec y(t₁₀%) = 0,1·Y_c et y(t₉₀%) = 0,9·Y_c.

Approximation rapide (régime dominé par 2t) :

$$t_{montée} \approx \frac{0{,}8 \cdot Y_c}{2} = 0{,}4 \cdot Y_c$$

### 5.2 Temps de stabilisation (t_stable)

Temps pour que l'erreur reste dans la bande de ±5% autour de Y_c :

$$|y(t) - Y_c| \leq 0{,}05 \cdot Y_c \quad \forall t \geq t_{stable}$$

Les pôles de la fonction de transfert en boucle fermée (correcteur PI) :

$$s_{1,2} = \frac{-K_p \pm \sqrt{K_p^2 - 4K_i}}{2}$$

Règle des 4 constantes de temps (critère standard en automatique) :

$$t_{stable} \approx \frac{8}{K_p}$$

### 5.3 Temps de rupture (t_rupture)

Voir section 3. Rappel de la borne conservatrice :

$$t_{rupture} \geq \frac{Y_{max} - 1{,}57}{\varepsilon}$$

### 5.4 Tableau de synthèse opérationnel

| Temps | Formule | Dépend de | Utilité pratique |
|---|---|---|---|
| t_montée | ≈ 0,4 · Y_c / c | Consigne, vitesse c | Dimensionner la réactivité |
| t_stable | ≈ 8 / Kp | Gain proportionnel Kp | Régler le correcteur PI |
| t_rupture | ≥ (Y_max − 1,57) / ε | Borne physique, ε | Sécurité, alarme préventive |

**Condition de bon dimensionnement :**

$$t_{montée} < t_{stable} < t_{rupture}$$

> Si cet ordre n'est pas respecté, le système est mal dimensionné.

---

## 6. Preuve de Stabilité du Système Régulé

### 6.1 Fonction de transfert en boucle fermée (transformée de Laplace)

$$H(s) = \frac{K_p \cdot s + K_i}{s^2 + K_p \cdot s + K_i}$$

**Condition de stabilité (critère de Routh) :**

$$K_p > 0 \quad \text{et} \quad K_i > 0$$

Les pôles sont à partie réelle strictement négative si et seulement si ces deux conditions sont vérifiées.

### 6.2 Approche de Lyapunov (pour cas non-linéaire)

On pose le vecteur d'état augmenté $[e(t),\ I(t)]$ avec $I(t) = \int_0^t e(\tau)\,d\tau$, de sorte que $\dot{I}(t) = e(t)$.

**Fonction de Lyapunov candidate :**

$$V(e, I) = \frac{1}{2}e(t)^2 + \frac{K_i}{2K_p}I(t)^2$$

$V$ est définie positive car $K_p > 0$ et $K_i > 0$.

**Calcul de $\dot{V}$ :**

La dynamique de l'erreur découle de l'équation du système régulé (section 4.3) :

$$\dot{e}(t) = \dot{y}(t) = f'(t) + z(t) - K_p\,e(t) - K_i\,I(t)$$

Donc :

$$\dot{V} = e\,\dot{e} + \frac{K_i}{K_p}I\,\dot{I} = e\bigl[f'(t) + z(t) - K_p\,e - K_i\,I\bigr] + \frac{K_i}{K_p}I\,e$$

Les termes $-K_i\,e\,I$ et $+\frac{K_i}{K_p}I\,e$ ne se simplifient pas complètement ; en développant :

$$\boxed{\dot{V} = -K_p\,e^2 + e\bigl[f'(t) + z(t)\bigr]}$$

**Analyse de stabilité pratique :**

Le terme $-K_p e^2$ est toujours négatif. Le terme $e[f'(t) + z(t)]$ est borné car $f'(t) = \frac{1}{1+t^2} \leq 1$ et $z(t)$ est borné supérieurement par $z_{max} = 2 + \sqrt{2}$.

$\dot{V} < 0$ est garanti dès que :

$$K_p|e| > |f'(t) + z(t)| \leq 1 + z_{max} = 3 + \sqrt{2} \approx 4{,}41$$

$$\Rightarrow \quad |e| > \frac{3 + \sqrt{2}}{K_p}$$

**Conclusion (stabilité pratique) :** L'erreur converge vers une **bande résiduelle** bornée :

$$|e(t)| \leq \frac{3 + \sqrt{2}}{K_p} \quad \text{(à long terme)}$$

Plus $K_p$ est grand, plus cette bande se resserre. Le système est **pratiquement stable** (Ultimate Boundedness) : l'erreur ne converge pas nécessairement vers zéro exact, mais reste confinée dans un voisinage de zéro dont la taille est inversement proportionnelle à $K_p$.

> **Note :** La stabilité asymptotique stricte ($e \to 0$) n'est pas garantie tant que $z(t) > 0$, ce qui est cohérent avec la nature de la perturbation persistante — le correcteur PI *compense* la dérive mais ne l'annule pas à chaque instant.

---

## 7. Stratégie Opérationnelle — RETA Pur (v1.0)

Cette section définit le protocole de déploiement du système de base (sans Kalman, sans auto-adaptation), dans un environnement où z(t) est mesurable ou estimable analytiquement.

### 7.1 Procédure de dimensionnement

Avant tout déploiement, calculer les trois temps caractéristiques dans l'ordre suivant :

1. **Calculer $t_{rupture}$** (contrainte physique non négociable) :
$$t_{rupture} \geq \frac{Y_{max} - 1{,}57}{\varepsilon}$$

2. **Fixer $t_{stable}$** (contrainte opérationnelle) puis en déduire $K_p$ :
$$K_p = \frac{8}{t_{stable}}$$

3. **Choisir $K_i$** selon le régime souhaité :

| Régime | Condition | Comportement |
|---|---|---|
| Sous-amorti (rapide, oscillant) | $K_i > \frac{K_p^2}{4}$ | Atteint $Y_c$ vite, dépasse puis revient |
| Critique (optimal) | $K_i = \frac{K_p^2}{4}$ | Atteint $Y_c$ sans dépassement, le plus vite possible |
| Sur-amorti (lent, sans oscillation) | $K_i < \frac{K_p^2}{4}$ | Approche $Y_c$ lentement, aucun dépassement |

4. **Vérifier l'ordre de viabilité :**
$$t_{montée} < t_{stable} < t_{rupture}$$
Si cette condition n'est pas satisfaite, le système est mal dimensionné — reprendre depuis l'étape 2 avec un $t_{stable}$ plus petit.

### 7.2 Planification des alarmes

Une fois les temps validés, définir deux seuils d'alerte préventive :

- **Alarme précoce** à $t = 0{,}6 \cdot t_{rupture}$ : signal d'avertissement, intervention non urgente.
- **Alarme critique** à $t = 0{,}8 \cdot t_{rupture}$ : intervention immédiate requise avant rupture.

### 7.3 Limites de v1.0

- z(t) doit être connu à l'avance (forme analytique ou mesure directe).
- Tout bruit de mesure sur $y(t)$ dégrade la qualité de l'erreur et donc l'efficacité du PI.
- Les gains $K_p$ et $K_i$ sont fixes : si z(t) change de régime, le correcteur devient sous-optimal.

→ Ces limites motivent l'introduction du filtre de Kalman (v1.1) et de l'auto-adaptation (v1.2).

---

## 8. Extension Stochastique — Couche d'Estimation Optimale (Kalman)

Dans un environnement réel (bruit de mesure, incertitude), le système ne peut pas se baser sur la mesure brute $y_{mesuré}$. On insère un **Filtre de Kalman** entre la mesure et le contrôleur RETA.

### 8.1 Pourquoi cette couche ?
1. **Filtrage du Bruit :** Élimine les "fake moves" (volatilité court terme).
2. **Estimation de la Dérive invisible :** Kalman estime $\hat{z}(t)$ même s'il n'est pas mesuré directement.
3. **Optimisation du t_rupture :** La prédiction devient stable et basée sur une tendance filtrée.

### 8.2 Modèle d'Espace d'État RETA
Soit le vecteur d'état $x = [y, z]^T$. Le modèle discret est :

$$x_{k+1} = \begin{pmatrix} 1 & \Delta t \\ 0 & 1 \end{pmatrix} x_k + \begin{pmatrix} \Delta f \\ 0 \end{pmatrix} + w_k$$

L'observation est : $y_{mesuré} = \begin{pmatrix} 1 & 0 \end{pmatrix} x_k + v_k$

### 8.3 Intégration dans la boucle de contrôle
Le correcteur PI n'agit plus sur $y(t) - Y_c$, mais sur l'état estimé :
$$\boxed{u(t) = K_p( \hat{y}_{kalman} - Y_c ) + K_i \int ( \hat{y}_{kalman} - Y_c ) d\tau}$$

---

## 9. Stratégie Opérationnelle (Mise à jour)

1. **Filtrer** la donnée entrante via Kalman pour obtenir $\hat{y}$ et $\hat{z}$ stables.
2. **Calculer** $t_{rupture}$ en utilisant $\hat{z}$ estimé par Kalman.
3. **Réguler** via le PI en utilisant $\hat{y}$ comme référence de position.

---

## 10. Auto-Adaptation Dynamique des Gains (v1.2)

Dans des scénarios de haute volatilité ou de changement de régime (ex : passage d'un air dense à un air raréfié pour un missile, changement de tendance de marché), des gains $K_p$ et $K_i$ fixes deviennent sous-optimaux ou instables. La version 1.2 introduit une couche d'auto-tuning qui ajuste les gains en temps réel en fonction de la performance observée du système.

### 10.1 Principe de l'Auto-Correction

Le correcteur PI v1.2 ne dispose plus de gains constants. Kp(t) et Ki(t) sont des **variables d'état** qui évoluent selon des lois d'adaptation pilotées par l'erreur courante et son histoire.

Soient $\gamma_p > 0$ et $\gamma_i > 0$ les taux d'apprentissage (*learning rates*) et $\theta > 0$ un seuil de tolérance (*bande morte*).

### 10.2 Lois d'adaptation

Deux familles de lois sont disponibles, avec des propriétés de stabilité différentes :

#### Lois heuristiques v1.2 (réactivité élevée, stabilité non prouvée)

**1. Adaptation de $K_i$ — Réaction à la persistance de l'erreur :**

$$\dot{K_i}(t) = \gamma_i \cdot |e(t)| \cdot \text{sgn}\left(\int_0^t e(\tau)\,d\tau\right)$$

**2. Adaptation de $K_p$ — Gestion de la nervosité :**

$$\dot{K_p}(t) = \gamma_p \cdot (|e(t)| - \theta)$$

*Logique :*
- Si $|e(t)| > \theta$ : $K_p$ augmente → réaction plus agressive.
- Si $|e(t)| < \theta$ : $K_p$ diminue → amortissement progressif.

> **Avertissement :** Ces lois sont **heuristiques**. Le critère de Routh ne s'applique plus
> ($K_p(t)$ varie). La stabilité doit être vérifiée par simulation. Utiliser en priorité
> les lois gradient ci-dessous si la garantie de stabilité est requise.

#### Lois gradient (prouvables par Lyapunov — recommandées)

Avec le candidat de Lyapunov $V = \frac{1}{2}e^2 + \frac{1}{2\gamma_p}\tilde{K}_p^2 + \frac{1}{2\gamma_i}\tilde{K}_i^2$ (où $\tilde{K} = K - K^*$) :

$$\boxed{\dot{K}_p = \gamma_p \cdot e^2, \qquad \dot{K}_i = \gamma_i \cdot e \cdot \int_0^t e\,d\tau}$$

Ces lois annulent les termes croisés dans $\dot{V}$, donnant :

$$\dot{V} = -K_p^* e^2 + e \cdot w(t)$$

Pour $K_p^* > |w|_{\max}$ et perturbation bornée, $\dot{V} < 0$ hors d'un compact → **stabilité asymptotique garantie**.

### 10.3 Contraintes de saturation (impératives)

Sans bornes sur les gains, les lois d'adaptation peuvent diverger si l'erreur persiste durablement. Il faut imposer :

$$K_p \in [K_{p,min},\ K_{p,max}], \quad K_i \in [K_{i,min},\ K_{i,max}]$$

En pratique : $K_{p,min} > 0$ (jamais nul pour éviter la perte de réactivité), $K_{i,min} > 0$ (jamais nul pour conserver la correction intégrale).

### 10.4 Avantages et limites

| | v1.1 (Kalman, gains fixes) | v1.2 heuristique | v1.2 gradient |
|---|---|---|---|
| Changement de régime de z(t) | Correcteur sous-optimal | Auto-correction rapide | Auto-correction prouvée |
| Stabilité prouvable | Oui (Routh) | Non — H(s) non-LTI | Oui (Lyapunov) |
| Paramètres à régler | $K_p$, $K_i$, Q, R | + $\gamma_p$, $\gamma_i$, $\theta$ | + $\gamma_p$, $\gamma_i$, $K^*$ |

> **Note sur la stabilité :** Les lois heuristiques (Kṗ = γp(|e|−θ)) offrent une bonne
> réactivité pratique mais ne sont pas prouvées stables au sens de Lyapunov. Les lois
> gradient (Kṗ = γp·e²) sont formellement prouvées stables sous perturbation bornée.
> Recommandation : utiliser les lois gradient en production, les lois heuristiques
> uniquement si la vitesse d'adaptation prime sur la garantie formelle.

→ La limite restante de v1.2 est que les matrices Q et R du filtre Kalman restent fixes. Ce dernier verrou est levé en v1.3.

---

## 11. Le Système Caméléon — Auto-Paramétrage Intégral (v1.3)

La version 1.3 fusionne l'auto-adaptation des gains (v1.2) avec l'auto-ajustement des matrices de bruit du Filtre de Kalman. Le système recalibre sa perception ($Q, R$) et sa réaction ($K_p, K_i$) en temps réel.

### 11.1 Auto-Ajustement de la Perception (Adaptive Kalman)
On utilise la séquence d'innovation $\nu_k = y_{mesuré, k} - H\hat{x}_{k|k-1}$ pour ajuster les matrices de covariance.

1. **Adaptation de R (Bruit de Mesure) :**
$$\hat{R}_k = \alpha \hat{R}_{k-1} + (1-\alpha)(\nu_k \nu_k^T + H P_{k|k-1} H^T)$$
*Si le bruit de marché ou de capteur augmente, $R$ grimpe, rendant le filtre plus "prudent".*

2. **Adaptation de Q (Bruit de Processus) :**
$$\hat{Q}_k = \beta \hat{Q}_{k-1} + (1-\beta)(G_k \nu_k \nu_k^T G_k^T)$$
*Où $G_k$ est le gain de Kalman. Si le modèle RETA dévie systématiquement, $Q$ augmente pour redonner de la flexibilité au modèle.*

### 11.2 Synergie Totale : Perception-Action-Adaptation
Le cycle v1.3 est le suivant :
1. **Évaluer la clarté** du signal (Ajuster $R$).
2. **Évaluer la validité** du modèle RETA (Ajuster $Q$).
3. **Extraire l'état** optimal $[\hat{y}, \hat{z}]$.
4. **Calculer la réponse** adaptée (Ajuster $K_p, K_i$).
5. **Prédire la rupture** avec une précision auto-calibrée.

### 11.3 Résilience Ultime
Un système v1.3 peut être déployé sans paramétrage préalable. Il "apprend" la physique de son environnement et les statistiques du bruit par simple observation des premières secondes de fonctionnement.

---

## Récapitulatif des versions

| Version | Nom | Capacité |
|---|---|---|
| v1.0 | RETA Pur | Modélisation accumulation et PI |
| v1.1 | RETA-Kalman | Fusion Perception/Action (Anti-bruit) |
| v1.2 | Adaptive RETA | Auto-correction des gains (Self-Tuning) |
| v1.3 | Chameleon RETA | Auto-paramétrage intégral (Q, R, Kp, Ki) |

---

*Document en cours — système complet*
---
## 🧭 Navigation
- [📖 Index de la Documentation](../INDEX.md)
- [🏠 Accueil du Projet](../../README.md)
