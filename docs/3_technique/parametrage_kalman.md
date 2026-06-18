# Paramétrage Mathématique de Kalman (Q & R)
**Projet : Referential Escape Theory by Accumulation (RETA)**

Pour éviter de "flancher" au Niveau 2 (Perception), les matrices **Q** et **R** ne doivent pas être choisies au hasard. Elles peuvent être dérivées de la physique de votre système.

---

## 1. Détermination de R (Bruit de Mesure)
La matrice **R** représente l'incertitude de vos capteurs ou de votre flux de données (ex: prix BTC).

*   **Méthode Mathématique :** Calculez la variance de la mesure sur un échantillon stable (quand le système ne bouge pas).
*   **Formule :** $R = \sigma_v^2 = \frac{1}{N} \sum (y_i - \bar{y})^2$
*   **Signification :** Plus le capteur est "bruyant", plus $R$ est grand, et plus Kalman fera confiance au modèle RETA plutôt qu'à la mesure instantanée.

---

## 2. Détermination de Q (Bruit de Processus)
La matrice **Q** représente l'imperfection de votre modèle RETA (ce que les équations ne voient pas). Dans RETA, on considère que la dérive $z(t)$ peut varier subitement (accélération aléatoire).

### Modèle "Discrete White Noise"
Si on suppose que la dérive $z$ subit des variations aléatoires de variance $\sigma_a^2$ (en unités/s²), alors la matrice Q pour l'état $[y, z]^T$ est :

$$\mathbf{Q} = \sigma_a^2 \cdot \begin{pmatrix} \frac{\Delta t^4}{4} & \frac{\Delta t^3}{2} \\ \frac{\Delta t^3}{2} & \Delta t^2 \end{pmatrix}$$

*   **Comment trouver $\sigma_a$ ?** C'est la "nervosité" maximale attendue de votre perturbation. 
    *   *Exemple Missile :* L'intensité maximale d'une rafale de vent.
    *   *Exemple Finance :* La volatilité historique du marché.

---

## 3. Le Ratio Critique : Q / R
Le comportement de RETA-Kalman dépend du ratio entre ces deux matrices :

1.  **Si Q ≪ R :** Le filtre est "Lent". Il considère que le modèle est très fiable et que la mesure est très mauvaise. Il lisse énormément mais peut rater un changement brusque.
2.  **Si Q ≫ R :** Le filtre est "Rapide". Il suit la mesure de très près. Il est réactif mais laisse passer beaucoup de bruit.

---

## 4. Application Pratique au Modèle RETA
Pour votre simulation, si vous connaissez votre fréquence d'échantillonnage $\Delta t$ :

1.  **Mesurez** l'écart-type du bruit de vos données ($\sigma_v$).
2.  **Estimez** la variation maximale de dérive par seconde ($\sigma_a$).
3.  **Injectez** ces valeurs dans les matrices.

**Résultat :** Votre perception est mathématiquement optimisée. Vous ne "flanchez" plus par manque de clarté, car le gain de Kalman $K$ s'auto-ajuste pour trouver le point d'équilibre parfait entre votre théorie et la réalité.

---
## 🧭 Navigation
- [📖 Index de la Documentation](../INDEX.md)
- [🏠 Accueil du Projet](../../README.md)
