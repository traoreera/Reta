# RETA en Cybersécurité

## Vue d'ensemble

Les cyberattaques les plus dangereuses sont celles qui **s'accumulent lentement** : exfiltration en faible débit, escalade de privilèges par étapes, poisoning progressif d'un modèle IA. Les systèmes de détection classiques (seuils fixes, règles statiques) sont aveugles à ces dérives cumulatives. RETA détecte l'accumulation **avant** que le seuil critique ne soit atteint.

---

## 1. Exfiltration de Données (Low & Slow)

### Problème
Une exfiltration classique envoie de gros volumes — détectable. L'attaquant moderne exfiltre à très faible débit (quelques Ko/heure) sur des mois. Le cumul est massif mais la signature instantanée est sous le seuil des alertes.

### Modèle RETA

| Variable | Définition concrète |
|---|---|
| $y(t)$ | Volume total exfiltré depuis la compromission |
| $f(t)$ | Trafic sortant légitime attendu (baseline horaire/journalier) |
| $z(t)$ | Débit exfiltré net : $z = \text{débit\_sortant} - \text{baseline}$ [Ko/s] |
| $Y_{max}$ | Volume critique (ex. : 1 Go = toute la base clients) |
| $t_{rupture}$ | Délai avant exfiltration complète si le débit actuel est maintenu |

### Calcul concret

Exfiltration à 5 Ko/heure, baseline 1 Ko/heure, z = 4 Ko/heure = 1,11 μKo/s :

$$t_{rupture} \geq \frac{Y_{max}}{\bar{z}} = \frac{1\,000\,000 \text{ Ko}}{4 \text{ Ko/h}} = 250\,000 \text{ h} \approx 28 \text{ ans}$$

→ Temps suffisant pour détecter et couper, à condition de **voir l'accumulation**.

### Valeur ajoutée RETA
- **Classique :** Alerte sur débit instantané (rate limiting) — manque le faible débit long
- **RETA :** Surveillance du cumul $y(t)$, alerte quand la trajectoire de $y(t)$ est anormale même si $z(t)$ est faible

---

## 2. Escalade de Privilèges par Étapes (APT)

### Problème
Une APT (Advanced Persistent Threat) gagne des droits progressivement : compromission d'un compte standard → pivot latéral → droits admin local → compromission du contrôleur de domaine. Chaque étape individuelle peut sembler légitime.

### Modèle RETA

| Variable | Définition concrète |
|---|---|
| $y(t)$ | Score de "surface de contrôle" de l'attaquant : somme pondérée des droits acquis |
| $z(t)$ | Taux d'acquisition de droits : nouvelles permissions / heure |
| $Y_{max}$ | Score correspondant aux droits admin domaine |
| $t_{rupture}$ | Délai avant compromission totale si la progression actuelle continue |

### Scoring RETA multi-vecteur (Extension nD)

Chaque vecteur d'escalade est une dimension :

$$\mathbf{y}(t) = \begin{pmatrix} y_{réseau} \\ y_{identité} \\ y_{données} \\ y_{infrastructure} \end{pmatrix}$$

$$t_{rupture,global} = \min_i\left(t_{rupture,i}\right)$$

Le premier axe à atteindre $Y_{max}$ détermine le vecteur d'attaque critique.

### Valeur ajoutée RETA
- **Classique :** SIEM avec règles de corrélation figées — aveugle aux nouvelles séquences
- **RETA :** Modélisation de la trajectoire de compromission, prédiction du vecteur final

---

## 3. DDoS par Épuisement Progressif des Ressources

### Problème
Un DDoS de type "slow loris" ou "connection exhaustion" n'envoie pas un flood massif — il ouvre des milliers de connexions à faible débit qui s'accumulent jusqu'à l'épuisement du pool de connexions du serveur.

### Modèle RETA

| Variable | Définition concrète |
|---|---|
| $y(t)$ | Nombre de connexions "zombie" cumulées |
| $z(t)$ | Taux net d'ouverture de connexions malveillantes : $z = \lambda_{open} - \lambda_{close}$ |
| $Y_{max}$ | Pool maximum de connexions du serveur (ex. : 10 000) |
| $t_{rupture}$ | Délai avant saturation du pool |

### Correcteur PI dans ce contexte

$$u(t) = K_p \cdot (N_{conn}(t) - N_{cible}) + K_i \int \Delta N_{conn}\,d\tau$$

Actions : réduction de timeout, activation de rate limiting adaptatif, blocage préventif des IP lentes.

### Valeur ajoutée RETA
- **Classique :** Seuil fixe sur le nombre de connexions — alerte après saturation
- **RETA :** Prédiction de $t_{rupture}$ avec 10 à 30 minutes d'avance

---

## 4. Poisoning de Modèle IA en Production (Adversarial Drift)

### Problème
Un attaquant soumettant des données corrompues au fil du temps peut piloter la dérive d'un modèle en ligne learning. Le poisoning est progressif et non détectable requête par requête.

### Modèle RETA

| Variable | Définition concrète |
|---|---|
| $y(t)$ | Divergence du modèle par rapport à son état sain : $D_{KL}(M_t \| M_0)$ |
| $z(t)$ | Taux de corruption injecté : portion de données empoisonnées × impact sur les poids |
| $Y_{max}$ | Seuil de divergence au-delà duquel le comportement est compromis |
| $t_{rupture}$ | Délai avant compromission fonctionnelle du modèle |

### Valeur ajoutée RETA
- **Classique :** Validation périodique sur jeu de test propre — détection retardée
- **RETA :** Monitoring continu de $D_{KL}$, $t_{rupture}$ mis à jour à chaque batch d'entraînement

---

## 5. Accumulation de Vulnérabilités (Vulnerability Debt)

### Problème
Une organisation accumule des CVE non patchées. La surface d'attaque croît de façon persistante avec chaque nouvelle vulnérabilité non corrigée. Un attaquant qui observe cette accumulation sait qu'une exploitation est imminente.

### Modèle RETA

| Variable | Définition concrète |
|---|---|
| $y(t)$ | Score CVSS cumulé non patché (somme des scores de toutes les CVE ouvertes) |
| $z(t)$ | Taux d'accumulation : nouvelles CVE critiques / semaine × score moyen |
| $Y_{max}$ | Seuil d'acceptabilité de risque (défini par la politique de sécurité) |
| $t_{rupture}$ | Délai avant dépassement du seuil de risque acceptable |

### Valeur ajoutée RETA
- **Classique :** Dashboard de vulnérabilités statique, priorité CVSS fixe
- **RETA :** Prédiction dynamique du "quand" le risque devient inacceptable, ordonnancement du patch plan en conséquence

---

## Tableau Récapitulatif

| Application | $y(t)$ | $z(t)$ | $Y_{max}$ | Correcteur PI |
|---|---|---|---|---|
| Exfiltration L&S | Volume exfiltré | Débit net suspect | Volume critique | Throttling / coupure flux |
| Escalade APT | Score droits acquis | Taux acquisition droits | Admin domaine | Révocation préventive droits |
| DDoS slow | Connexions zombie | λ_open − λ_close | Pool max connexions | Rate limiting adaptatif |
| Poisoning IA | $D_{KL}$ modèle | Taux corruption | Seuil divergence | Rollback / quarantaine données |
| Vulnerability debt | Score CVSS cumulé | Nouvelles CVE/semaine | Seuil risque politique | Patch plan prioritisé |

---

**📂 Section 6 — Domaines d'Application**
[Index](README.md) · [Finance](finance.md) · [IA & LLM](ia_llm.md) · [Physique](physique.md) · [Cybersécurité](cybersecurite.md) · [Santé](sante.md) · [Infrastructure](infrastructure.md) · [Social](social.md)

**🔗 Voir aussi** : [Théorie Fondamentale](../1_fondamentaux/theorie_fondamentale.md) · [Extension Dimensionnelle](../2_extensions_theoriques/extension_dimensionnelle.md)

---

[📖 Index de la Documentation](../INDEX.md) · [🏠 Accueil du Projet](../../README.md)
