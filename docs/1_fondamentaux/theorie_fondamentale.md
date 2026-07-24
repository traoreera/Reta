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

**Lemme 1 (généralisation de la fonction de base) :**
Soit $f \in C^1(\mathbb{R}^+)$ telle que $\lim_{t\to\infty} f(t) = L < \infty$ et $\lim_{t\to\infty} f'(t) = 0$. Alors pour toute perturbation $z(t) \geq \varepsilon > 0$ :

$$y(t) = f(t) + \int_0^t z(\tau)\,d\tau \sim \int_0^t z(\tau)\,d\tau \quad \text{quand } t \to \infty$$

et le temps de rupture $t_{rup}$ vérifie $t_{rup} = (Y_{\max} - L)/\varepsilon$ en borne conservative, **indépendamment du choix de $f$**. L'exemple $\arctan(t)$ est un cas particulier avec $L = \pi/2$ et $\|f'\|_\infty = 1$.

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

**Hypothèse préalable :** On suppose que la perturbation $z(t)$ est uniformément bornée supérieurement :
$$\exists Z_{\max} > 0 \ \text{tel que} \ |z(t)| \leq Z_{\max} \ \forall t \geq 0$$
Cette hypothèse est physique : aucune perturbation réelle n'est infinie. La borne doit être estimée à partir du système cible. La fonction $f'(t) = \frac{1}{1+t^2}$ est quant à elle bornée par $\|f'\|_\infty = 1$.

### 6.1 Fonction de transfert en boucle fermée (transformée de Laplace)

$$H(s) = \frac{K_p \cdot s + K_i}{s^2 + K_p \cdot s + K_i}$$

**Condition de stabilité (critère de Routh) :**

$$K_p > 0 \quad \text{et} \quad K_i > 0$$

Les pôles sont à partie réelle strictement négative si et seulement si ces deux conditions sont vérifiées.

### 6.2 Approche de Lyapunov — Stabilité ISS (Input-to-State Stability)

On pose le vecteur d'état augmenté $[e(t),\ I(t)]$ avec $I(t) = \int_0^t e(\tau)\,d\tau$, de sorte que $\dot{I}(t) = e(t)$.

**Fonction de Lyapunov candidate :**

$$V(e, I) = \frac{1}{2}e(t)^2 + \frac{K_i}{2}I(t)^2$$

$V$ est définie positive car $K_i > 0$.

> **Note :** Le coefficient de $I^2$ est $K_i/2$, et non $K_i/(2K_p)$. Ce choix est précisément celui qui annule les termes croisés dans $\dot{V}$ (voir calcul ci-dessous).

**Calcul de $\dot{V}$ :**

La dynamique de l'erreur découle de l'équation du système régulé (section 4.3) :

$$\dot{e}(t) = \dot{y}(t) = f'(t) + z(t) - K_p\,e(t) - K_i\,I(t)$$

Donc ($\dot{I} = e$) :

$$\dot{V} = e\,\dot{e} + K_i\,I\,\dot{I} = e\bigl[f'(t) + z(t) - K_p\,e - K_i\,I\bigr] + K_i\,I\,e$$

Les termes croisés s'annulent exactement : $-K_i\,e\,I + K_i\,I\,e = 0$. Il reste :

$$\boxed{\dot{V} = -K_p\,e^2 + e\bigl[f'(t) + z(t)\bigr]}$$

**Analyse ISS (stabilité entrée-état) :**

Soit $w(t) = f'(t) + z(t)$. Par hypothèse, $|w(t)| \leq \|f'\|_\infty + Z_{\max} = 1 + Z_{\max}$.

En complétant le carré :

$$\dot{V} = -K_p\,e^2 + e\,w \leq -K_p|e|^2 + |e|(1 + Z_{\max})$$

$$\dot{V} \leq -|e|\bigl(K_p|e| - (1 + Z_{\max})\bigr)$$

$\dot{V} < 0$ est garanti dès que :

$$|e| > \frac{1 + Z_{\max}}{K_p}$$

**Conclusion (stabilité ISS) :** L'erreur converge vers une **bande résiduelle** bornée :

$$\boxed{|e(t)| \leq \frac{1 + Z_{\max}}{K_p} \quad \text{(à long terme)}}$$

Plus $K_p$ est grand, plus cette bande se resserre. Le système est **stable au sens ISS** (Input-to-State Stability) : l'erreur est bornée par la perturbation normalisée par $K_p$, et tend vers 0 si $K_p \to \infty$ ou si la perturbation s'annule.

> **Note :** La stabilité asymptotique stricte ($e \to 0$) n'est pas garantie tant que $z(t) > 0$, ce qui est cohérent avec la nature de la perturbation persistante — le correcteur PI *compense* la dérive mais ne l'annule pas à chaque instant. Le formalisme ISS remplace l'estimation ad-hoc précédente ($3+\sqrt{2}$) par une expression générale dépendant de $Z_{\max}$, qui doit être identifié par analyse du système ou via le Kalman adaptatif (v1.3).

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

La version implémentée (cf. `reta/kalman.py`) estime non pas $y$ mais la perturbation $z$ et sa dérivée $\dot{z}$. Soit le vecteur d'état $x = [z,\ \dot{z}]^T$.

**Modèle de marche aléatoire avec vitesse (position-velocity) :**

$$x_{k+1} = \begin{pmatrix} 1 & \Delta t \\ 0 & 1 \end{pmatrix} x_k + w_k, \qquad w_k \sim \mathcal{N}(0, Q)$$

**Observation :** on mesure directement le log-rendement $r_k = \log(p_k/p_{k-1})$, qui approxime $z_k$ :

$$r_k = \begin{pmatrix} 1 & 0 \end{pmatrix} x_k + v_k, \qquad v_k \sim \mathcal{N}(0, R)$$

**Justification :** On ne filtre pas $y$ (la position) mais $z$ (la pente), car :
- $z$ est la quantité physiquement significative pour la détection de tendance et le calcul de $t_{rup}$
- Le modèle position-vitesse sur $z$ permet d'estimer $\dot{z}$, nécessaire à la borne conservative v1.4
- L'erreur d'estimation sur $y$ s'obtient par intégration de $\hat{z}$, avec variance $P_{00}$ bornée

**Observabilité :** Le rang de la matrice d'observabilité $\mathcal{O} = [H;\ HA]^T$ est 2 (plein rang), donc l'état $[z,\ \dot{z}]$ est observable dès que $R$ est finie.

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

**Normalisation préalable (impérative pour la portabilité) :**

Les lois d'adaptation opèrent sur l'erreur **normalisée** $\bar{e}(t) = e(t)/e_{ref}$ et l'intégrale normalisée $\bar{I}(t) = I(t)/e_{ref}$, où $e_{ref}$ est une erreur de référence caractéristique du système (ex. : 10 % de $Y_{max}$). Cette normalisation rend $\bar{e}$ sans dimension et les taux $\gamma_p$, $\gamma_i$ purement en $[\text{gain}/\text{s}]$, indépendants de l'unité de $e$.

$$\bar{e}(t) = \frac{e(t)}{e_{ref}}, \quad \bar{\theta} = \frac{\theta}{e_{ref}}, \quad e_{ref} > 0$$

### 10.2 Lois d'adaptation

Deux familles de lois sont disponibles, avec des propriétés de stabilité différentes :

#### Lois heuristiques v1.2 (réactivité élevée, stabilité non prouvée)

**1. Adaptation de $K_i$ — Réaction à la persistance de l'erreur :**

$$\dot{K_i}(t) = \gamma_i \cdot |\bar{e}(t)| \cdot \text{sgn}\left(\int_0^t \bar{e}(\tau)\,d\tau\right)$$

**2. Adaptation de $K_p$ — Gestion de la nervosité :**

$$\dot{K_p}(t) = \gamma_p \cdot (|\bar{e}(t)| - \bar{\theta})$$

*Logique :*
- Si $|\bar{e}(t)| > \bar{\theta}$ : $K_p$ augmente → réaction plus agressive.
- Si $|\bar{e}(t)| < \bar{\theta}$ : $K_p$ diminue → amortissement progressif.

> **Avertissement :** Ces lois sont **heuristiques**. Le critère de Routh ne s'applique plus
> ($K_p(t)$ varie). La stabilité doit être vérifiée par simulation. Utiliser en priorité
> les lois gradient ci-dessous si la garantie de stabilité est requise.

#### Lois gradient (prouvables par Lyapunov + Barbalat — recommandées)

$$\boxed{\dot{K}_p = \gamma_p \cdot \bar{e}^2, \qquad \dot{K}_i = \gamma_i \cdot \bar{e} \cdot \int_0^t \bar{e}\,d\tau}$$

**Preuve de convergence :**

Soit le candidat de Lyapunov $V = \frac{1}{2}e^2 + \frac{1}{2\gamma_p}\tilde{K}_p^2 + \frac{1}{2\gamma_i}\tilde{K}_i^2$ où $\tilde{K}_p = K_p - K_p^*$ et $\tilde{K}_i = K_i - K_i^*$ sont les écarts à des gains cibles inconnus mais constants. En dérivant et en choisissant les lois d'adaptation pour annuler les termes en $\tilde{K}_p$ et $\tilde{K}_i$ :

$$\dot{V} = -K_p^* e^2 + e \cdot w(t)$$

où $w(t) = f'(t) + z(t)$ est l'entrée perturbatrice totale. Puisque $w(t)$ est borné ($|w| \leq 1 + Z_{\max}$), $\dot{V} \leq 0$ hors d'un compact contenant $e=0$. Donc $e$, $\tilde{K}_p$, $\tilde{K}_i$ sont uniformément bornés (UB).

De plus, $\dot{V} \leq -K_p^* e^2 + |e|(1+Z_{\max})$ implique $e \in L^2 \cap L^\infty$ et $\dot{e} \in L^\infty$. Par le **lemme de Barbalat**, $\lim_{t\to\infty} e(t) = 0$. Les gains convergent vers leurs valeurs cibles $K_p^*$, $K_i^*$ qui dépendent de l'amplitude de $w(t)$.

> **Note :** Contrairement à la preuve antérieure, Barbalat établit la convergence **asymptotique** ($e \to 0$) et non pas seulement une borne. La contrepartie est que cette preuve suppose $w(t)$ suffisamment régulier ($\dot{w} \in L^\infty$), ce qui est vérifié si $z(t)$ est $C^1$.

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
On utilise la séquence d'innovation $\nu_k = r_k - H\hat{x}_{k|k-1}$ (où $r_k$ est le log-rendement mesuré) pour ajuster les matrices de covariance. L'ordre ci-dessous est **impératif** (cf. `reta/kalman.py`, méthode `KalmanAdaptive.update`) :

1. **Prédire** l'état et la covariance : $x_{pred} = A \cdot x_{k-1}$, $P_{pred} = A \cdot P_{k-1} \cdot A^T + Q_{k-1}$

2. **Adapter R** (bruit de mesure) avant le gain :
$$\hat{R}_k = \alpha \cdot \hat{R}_{k-1} + (1-\alpha) \cdot (\nu_k^2 + H P_{pred} H^T)$$
*Si l'innovation est grande, $R$ augmente → le filtre fait plus confiance au modèle qu'à la mesure.*

3. **Calculer le gain** avec le $R$ adapté :
$$S_k = H P_{pred} H^T + \hat{R}_k, \qquad K_k = P_{pred} H^T / S_k$$

4. **Corriger** l'état : $x_k = x_{pred} + K_k \cdot \nu_k$, $P_k = (I - K_k H) P_{pred}$

5. **Adapter Q** (bruit de processus) après correction, en utilisant le $K_k$ déjà calculé (pas d'équation implicite) :
$$\hat{Q}_k = \beta \cdot \hat{Q}_{k-1} + (1-\beta) \cdot \text{tr}\bigl(K_k \cdot \nu_k^2 \cdot K_k^T\bigr)$$
*Note : on prend la trace du produit scalaire $\|K_k\|^2 \cdot \nu_k^2$, pas le produit matriciel complet — cela évite la croissance non-bornée de $Q$.*

6. **Mettre à jour** $Q_k = \text{diag}([\hat{Q}_k,\ \hat{Q}_k \cdot 0.1])$ pour propager la covariance du modèle.

> **Propriété :** Cette séquence est explicite (pas d'équation implicite $Q = f(K(Q))$). Chaque pas est $O(n^2)$ avec $n=2$, donc négligeable en pratique.

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
| v1.4 | Conservative RETA | Bound t_rup conservatif via tracking ḃ_true |

---

*Document de référence théorique — voir [docs/VERSIONS.md](../VERSIONS.md) pour les simulations et résultats par version.*

## Références
- Bibliographie centrale : [docs/bibliographie.md](../bibliographie.md)

---

**📂 Section 1 — Fondamentaux**
[Théorie Fondamentale](theorie_fondamentale.md) · [Analyse Complète](analyse_complete.md) · [Réponses aux Critiques](reponses_critiques.md) · [Démonstration v1.3](reta_v13_demonstration.md)

**🔗 Voir aussi** : [Extension Dimensionnelle](../2_extensions_theoriques/extension_dimensionnelle.md) · [Logique Probabiliste](../2_extensions_theoriques/logique_probabiliste.md) · [Fusion de Référentiels](../3_technique/fusion_referentiels.md)

---

[📖 Index de la Documentation](../INDEX.md) · [🏠 Accueil du Projet](../../README.md)
