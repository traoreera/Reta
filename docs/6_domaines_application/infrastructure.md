# RETA en Infrastructure & Logistique

## Vue d'ensemble

Les systèmes d'infrastructure accumulent des contraintes silencieuses : dette technique, stock excédentaire, congestion réseau, vieillissement de pipeline. La rupture arrive rarement de façon soudaine — elle est toujours précédée d'une accumulation longue et observable. RETA transforme cette observable en prédiction actionnable.

---

## 1. Supply Chain — Effet Bullwhip

### Problème
L'effet Bullwhip est une amplification des variations de demande le long d'une chaîne d'approvisionnement. Chaque maillon accumule du stock "préventif" qui dépasse la demande réelle, créant une sur-accumulation explosive en bout de chaîne.

### Modèle RETA

| Variable | Définition concrète |
|---|---|
| $y(t)$ | Stock accumulé au niveau $n$ de la chaîne |
| $f(t)$ | Stock optimal théorique (demande lissée par filtre de Kalman) |
| $z(t)$ | Amplification : $z = \sigma_{commandes,n} / \sigma_{demande,finale}$ — ratio bullwhip |
| $Y_{max}$ | Capacité d'entrepôt ou seuil d'immobilisation de capital |
| $t_{rupture}$ | Délai avant saturation ou rupture de flux |

### Correcteur PI dans ce contexte

$$u(t) = K_p \cdot (S(t) - S_{cible}) + K_i \int (S(\tau) - S_{cible})\,d\tau$$

$u(t)$ = ajustement des commandes passées au fournisseur. Le filtre Kalman v1.1 sépare la demande réelle du bruit de commande.

### Valeur ajoutée RETA
- **Classique :** Point de commande fixe (ROP), EOQ — ne s'adapte pas au bullwhip dynamique
- **RETA :** Lissage actif des commandes, prédiction de la date de saturation d'entrepôt

---

## 2. Réseau Électrique — Accumulation de Déséquilibre Fréquentiel

### Problème
La fréquence du réseau (50 Hz en Europe) dévie sous l'effet d'un déséquilibre production-consommation. L'accumulation du déséquilibre (Area Control Error, ACE) dépasse les limites de stabilité si non corrigée.

### Modèle RETA

| Variable | Définition concrète |
|---|---|
| $y(t)$ | ACE cumulé [MW·s] — énergie de déséquilibre accumulée |
| $f(t)$ | ACE nul (réseau équilibré) |
| $z(t)$ | Déséquilibre instantané : $z = P_{consommation}(t) - P_{production}(t)$ [MW] |
| $Y_{max}$ | Limite de stabilité : ACE > 3000 MW·s → risque de délestage |
| $t_{rupture}$ | Délai avant délestage automatique |

### Correcteur PI (AGC — Automatic Generation Control)

C'est précisément ce que fait l'AGC : boucle PI sur l'ACE. RETA ajoute la **prédiction de rupture** :

$$t_{rupture} \geq \frac{3000 \text{ MW·s}}{\bar{z}(t)}$$

Si $t_{rupture} < 60$ s → activation de la réserve secondaire. Si $t_{rupture} < 15$ s → délestage préventif.

### Valeur ajoutée RETA
- **Classique :** AGC réactif (corrige après déviation observée)
- **RETA :** Précharge de réserve avant que la déviation ne devienne critique

---

## 3. Réseau Informatique — Congestion et Buffer Overflow

### Problème
Un routeur accumule des paquets dans ses buffers quand le débit entrant dépasse la capacité de traitement. L'accumulation mène à un buffer overflow et à la perte de paquets.

### Modèle RETA

| Variable | Définition concrète |
|---|---|
| $y(t)$ | Occupancy du buffer [paquets ou Mbytes] |
| $z(t)$ | Débit net : $z = \lambda_{entrant} - \mu_{traitement}$ [Mbps] |
| $Y_{max}$ | Capacité maximale du buffer |
| $t_{rupture}$ | Délai avant buffer overflow et perte de paquets |

### Correcteur PI (Active Queue Management)

RED (Random Early Detection) et CoDel sont des correcteurs PI implicites sur l'occupancy du buffer. RETA formalise le calcul de $t_{rupture}$ pour déclencher le drop préventif avant saturation.

---

## 4. Infrastructure Pétrolière / Gazière — Corrosion de Pipeline

### Problème
La corrosion d'un pipeline est un processus d'accumulation irréversible. L'épaisseur de paroi diminue à chaque unité de temps, et la rupture par perforation arrive quand l'épaisseur résiduelle passe sous un seuil minimal.

### Modèle RETA

| Variable | Définition concrète |
|---|---|
| $y(t)$ | Épaisseur perdue depuis l'installation [mm] |
| $z(t)$ | Taux de corrosion : $z = k \cdot C_{H_2S}^{\alpha} \cdot T^{\beta}$ [mm/an] (modèle de de Waard) |
| $Y_{max}$ | Épaisseur initiale − épaisseur minimale de sécurité [mm] |
| $t_{rupture}$ | Durée de vie résiduelle du pipeline |

### Correcteur PI dans ce contexte

$u(t)$ = intensité de courant de protection cathodique. Le correcteur ajuste la protection en fonction de la vitesse de corrosion estimée par Kalman.

### Valeur ajoutée RETA
- **Classique :** Inspection périodique (pig), décision rétrospective sur mesure d'épaisseur
- **RETA :** Prédiction continue de la durée de vie, optimisation du planning d'inspection

---

## 5. Dette Technique Logicielle

### Problème
La dette technique s'accumule à chaque sprint : code non refactorisé, tests manquants, dépendances obsolètes. Au-delà d'un seuil, la vélocité de l'équipe s'effondre.

### Modèle RETA

| Variable | Définition concrète |
|---|---|
| $y(t)$ | Score de dette technique [SonarQube debt en jours-homme] |
| $f(t)$ | Niveau de dette cible (budget de refacto inclus dans la vélocité) |
| $z(t)$ | Accumulation nette : $z = \text{dette\_créée} - \text{dette\_remboursée}$ [j/sprint] |
| $Y_{max}$ | Seuil où la vélocité chute de 50% |
| $t_{rupture}$ | Nombre de sprints avant effondrement de la vélocité |

### Valeur ajoutée RETA
- **Classique :** Métriques de dette statiques, décision de refacto subjective
- **RETA :** Prédiction du sprint où la dette devient bloquante, budgétisation préventive du remboursement

---

## Tableau Récapitulatif

| Application | $y(t)$ | $z(t)$ | $Y_{max}$ | Correcteur PI |
|---|---|---|---|---|
| Effet Bullwhip | Stock maillon n | Amplification commandes | Capacité entrepôt | Lissage commandes fournisseur |
| Réseau électrique | ACE cumulé [MW·s] | Déséquilibre P-C | 3000 MW·s | AGC réserve secondaire |
| Buffer réseau | Occupancy buffer | λ_entrant − μ | Capacité buffer | Active Queue Management |
| Corrosion pipeline | Épaisseur perdue | Taux corrosion | Seuil sécurité | Protection cathodique |
| Dette technique | SonarQube debt [j-h] | Nette par sprint | Seuil vélocité | Budget refacto préventif |

---

**📂 Section 6 — Domaines d'Application**
[Index](README.md) · [Finance](finance.md) · [IA & LLM](ia_llm.md) · [Physique](physique.md) · [Cybersécurité](cybersecurite.md) · [Santé](sante.md) · [Infrastructure](infrastructure.md) · [Social](social.md)

**🔗 Voir aussi** : [Théorie Fondamentale](../1_fondamentaux/theorie_fondamentale.md) · [Extension Dimensionnelle](../2_extensions_theoriques/extension_dimensionnelle.md)

---

[📖 Index de la Documentation](../INDEX.md) · [🏠 Accueil du Projet](../../README.md)
