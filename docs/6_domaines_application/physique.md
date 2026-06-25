# RETA en Systèmes Physiques

## Vue d'ensemble

Les systèmes physiques sont le berceau naturel de RETA : la mécanique, la thermodynamique et l'aérospatiale produisent des dérives persistantes par accumulation de forces, de chaleur, et d'impulsions. La théorie du contrôle classique (PI, Kalman) est native à ces domaines — RETA en est une extension prédictive.

---

## 1. Dérive Thermique — Composants Électroniques

### Problème
Un composant électronique en fonctionnement voit sa température augmenter continûment. L'accumulation de chaleur dégrade les performances (résistance, fréquence d'horloge) et mène à la défaillance si la dissipation est insuffisante.

### Modèle RETA

| Variable | Définition concrète |
|---|---|
| $f(t)$ | Température ambiante stable (référentiel thermique idéal) |
| $z(t)$ | Puissance dissipée / capacité thermique : $z = P_{dissipée} / C_{thermique}$ [°C/s] |
| $y(t)$ | Température courante du composant |
| $Y_{max}$ | Température de junction maximale (ex. : 125°C pour CMOS) |
| $t_{rupture}$ | Temps avant dépassement de $T_{junction,max}$ |

### Calcul concret

CPU dissipant 95W, capacité thermique 45 J/°C, T_ambiante = 25°C, T_max = 105°C :

$$z = \frac{95}{45} \approx 2{,}11 \text{ °C/s}$$
$$t_{rupture} \geq \frac{105 - 25 - 1{,}57}{2{,}11} \approx 37 \text{ s} \quad \text{(sans ventilateur)}$$

### Correcteur PI dans ce contexte

Le correcteur pilote la vitesse du ventilateur :

$$u(t) = K_p \cdot (T(t) - T_{cible}) + K_i \int (T(\tau) - T_{cible})\,d\tau$$

$u(t)$ = commande PWM du fan (0% à 100%). La loi Kalman v1.1 filtre les lectures thermiques bruitées du capteur.

### Valeur ajoutée RETA
- **Classique :** Courbe fan prédéfinie (BIOS) — réactive, souvent trop tardive ou trop bruyante
- **RETA :** Anticipation de la charge thermique, commande anticipée avant le throttling

---

## 2. Navigation Inertielle — Dérive des Gyroscopes (IMU)

### Problème
Un gyroscope MEMS accumule une erreur de mesure (drift de biais) qui s'intègre en erreur de position. Sur un drone ou un missile, quelques degrés/heure de drift se traduisent en kilomètres d'erreur de position.

### Modèle RETA

| Variable | Définition concrète |
|---|---|
| $y(t)$ | Erreur de cap accumulée (angle intégré du biais gyro) |
| $z(t)$ | Biais du gyroscope : $z = b_{gyro}$ [°/s] — persistant et lentement variable |
| $Y_{max}$ | Erreur de position maximale tolérable (ex. : ±10° pour maintien de cap) |
| $t_{rupture}$ | Temps avant dépassement de l'erreur de cap maximale |

### Modèle RETA multi-axe (Extension nD)

Le cas 3D est une application directe de l'extension dimensionnelle :

$$\mathbf{y}(t) = \begin{pmatrix} \theta_x \\ \theta_y \\ \theta_z \end{pmatrix}, \quad \mathbf{z}(t) = \begin{pmatrix} b_x \\ b_y \\ b_z \end{pmatrix}$$

$$t_{rupture,global} = \min\left(\frac{Y_{max,x}}{\bar{b}_x},\ \frac{Y_{max,y}}{\bar{b}_y},\ \frac{Y_{max,z}}{\bar{b}_z}\right)$$

### Correcteur PI + Kalman (usage natif)

C'est exactement le filtre complémentaire / filtre de Kalman standard utilisé en navigation inertielle. RETA formalise la couche de **prédiction de rupture** qui manque aux implémentations classiques.

### Valeur ajoutée RETA
- **Classique :** Filtre Kalman qui corrige la dérive — mais sans prédire quand elle devient critique
- **RETA :** Alarme anticipée "recalage GPS nécessaire dans X secondes avant perte de précision"

> **Exemple complet :** Voir [drone_gyroscope_3d.md](exemples/drone_gyroscope_3d.md) — modèle RETA v1.1 complet avec calculs numériques sur les 3 axes (Roll, Pitch, Yaw), filtre Kalman, correcteur PI, et code Python de simulation.

---

## 3. Fatigue Mécanique — Structures sous Contraintes Cycliques

### Problème
Une structure métallique soumise à des cycles de contrainte accumule des dommages (modèle de Palmgren-Miner). L'accumulation est persistante : il n'y a pas de "récupération" de fatigue à froid.

### Modèle RETA

| Variable | Définition concrète |
|---|---|
| $y(t)$ | Fraction de durée de vie consommée : $D = \sum n_i / N_i \in [0, 1]$ |
| $z(t)$ | Taux de dommage par cycle : $z = \frac{1}{N_i} \cdot f_{cycle}$ [1/s] |
| $Y_{max}$ | $D = 1$ — rupture par fatigue |
| $t_{rupture}$ | Durée de vie résiduelle prédite |

### Calcul RETA

$$t_{rupture} \geq \frac{1 - D_{courant} - 1{,}57/N_{total}}{\bar{z}}$$

La borne conservative est ici utile pour **dimensionnement de sécurité** (facteur de sécurité inclus).

### Valeur ajoutée RETA
- **Classique :** Tableaux S-N de Wöhler, calcul de durée de vie à l'état neuf — pas temps réel
- **RETA :** Monitoring en temps réel de $D(t)$, prédiction de $t_{rupture}$ mis à jour à chaque cycle

---

## 4. Propulsion et Carburant — Gestion de la Consommation

### Problème
Un véhicule consomme du carburant de façon persistante. La consommation n'est jamais nulle en fonctionnement ($z(t) > 0$). La question est : **quand arrive la panne sèche ?**

### Modèle RETA

| Variable | Définition concrète |
|---|---|
| $y(t)$ | Carburant consommé depuis le départ |
| $f(t)$ | Consommation idéale (vitesse constante, route plate) |
| $z(t)$ | Surcharge de consommation : trafic, vent de face, climatisation, altitude |
| $Y_{max}$ | Capacité totale du réservoir |
| $t_{rupture}$ | Autonomie réelle restante |

### Correcteur PI dans ce contexte

Le correcteur pilote la stratégie de conduite :

$$u(t) = K_p \cdot (\text{niveau actuel} - \text{niveau cible}) + K_i \int \Delta\text{niveau}\,d\tau$$

Actions : réduction de vitesse, coupure climatisation, recherche de station. Le système Kalman filtre la sonde à carburant (souvent très bruitée).

---

## 5. Vieillissement de Batterie (Li-ion)

### Problème
La capacité d'une batterie Li-ion se dégrade irréversiblement à chaque cycle. L'accumulation de dégradation est strictement monotone ($z > 0$).

### Modèle RETA

| Variable | Définition concrète |
|---|---|
| $y(t)$ | Perte de capacité accumulée en % (State of Health dégradé) |
| $z(t)$ | Taux de dégradation par cycle : $z = \alpha \cdot \text{profondeur\_décharge} + \beta \cdot T_{charge}$ |
| $Y_{max}$ | 20% de perte de capacité = fin de vie batterie (critère industriel) |
| $t_{rupture}$ | Nombre de cycles avant fin de vie |

### Valeur ajoutée RETA
- **Classique :** BMS basé sur l'état de charge (SoC) — ignore le vieillissement cumulatif
- **RETA :** State of Health (SoH) prédit, alerte de remplacement anticipée

---

## Tableau Récapitulatif

| Application | $y(t)$ | $z(t)$ | $Y_{max}$ | Correcteur PI |
|---|---|---|---|---|
| Dérive thermique CPU | Température composant | Puissance / C_th | T_junction max | PWM ventilateur |
| Navigation inertielle | Erreur de cap | Biais gyroscope | Erreur cap max | Correction GPS/magnéto |
| Fatigue mécanique | Dommage Miner | Taux dommage/cycle | D = 1 (rupture) | Réduction charge cyclique |
| Carburant véhicule | Carburant consommé | Surcharge conso | Capacité réservoir | Stratégie conduite |
| Batterie Li-ion | Perte capacité SoH | Dégradation/cycle | 20% perte | Gestion profondeur décharge |

---

*[📖 Index domaines](README.md) · [📖 Index global](../INDEX.md)*
