# Modèle Complet — Drone avec Gyroscope 3 Axes (RETA nD)

**Domaine :** Navigation Inertielle — Extension Dimensionnelle ℝ³
**Version RETA :** v1.4 (Kalman adaptatif + PI multi-axe + bound conservatif ḃ_true)

---

## 0. Contexte Physique

Un drone quadrirotor navigue en espace libre. Son orientation dans l'espace est décrite par les **trois angles d'Euler** :

| Angle | Nom | Axe | Description |
|---|---|---|---|
| $\phi(t)$ | Roll (roulis) | X | Inclinaison gauche/droite |
| $\theta(t)$ | Pitch (tangage) | Y | Inclinaison avant/arrière |
| $\psi(t)$ | Yaw (lacet) | Z | Rotation autour de l'axe vertical |

Le gyroscope MEMS mesure les **vitesses angulaires** $[\dot{\phi},\ \dot{\theta},\ \dot{\psi}]$. L'intégration de ces vitesses donne les angles. Mais le gyroscope accumule un **biais** $b_i$ [°/s] qui s'intègre en erreur d'angle croissante.

---

## 1. Modélisation RETA 3D

### 1.1 Variables d'état par axe

Pour chaque axe $i \in \{x, y, z\}$ (roll, pitch, yaw) :

$$\dot{\phi}_i^{meas}(t) = \dot{\phi}_i^{true}(t) + b_i(t) + \eta_i(t)$$

Où :
- $\dot{\phi}_i^{true}$ : vitesse angulaire vraie
- $b_i(t)$ : biais gyroscope (lentement variable, **persistant**)
- $\eta_i(t)$ : bruit blanc de mesure (centré, filtrable)

L'erreur d'angle accumulée par intégration du biais :

$$e_i(t) = \int_0^t b_i(\tau)\,d\tau$$

### 1.2 Identification des composantes RETA

| Composante RETA | Axe X (Roll) | Axe Y (Pitch) | Axe Z (Yaw) |
|---|---|---|---|
| $f_i(t)$ | $\phi_{ref}(t)$ (cap cible) | $\theta_{ref}(t)$ | $\psi_{ref}(t)$ |
| $z_i(t)$ | $b_x(t)$ [°/s] | $b_y(t)$ [°/s] | $b_z(t)$ [°/s] |
| $y_i(t)$ | $e_x(t) = \int b_x\,d\tau$ [°] | $e_y(t) = \int b_y\,d\tau$ | $e_z(t) = \int b_z\,d\tau$ |
| $Y_{max,i}$ | ±5° (tenue de cap) | ±5° (tenue de cap) | ±10° (navigation) |

### 1.3 Valeurs numériques du gyroscope

On modélise un **gyroscope MEMS de qualité standard** (type ICM-42688-P) :

| Paramètre | Valeur | Unité | Description |
|---|---|---|---|
| Biais initial $b_0$ | ±2 °/h = ±0,00056 °/s | °/s | Offset à froid |
| Instabilité de biais | 3 °/h = 0,00083 °/s | °/s/√h | Allan deviation |
| Bruit de marche angulaire | 0.0028 | °/s/√Hz | Bruit blanc mesure |
| Fréquence d'échantillonnage | 1000 | Hz | dt = 0.001 s |
| Biais effectif modélisé $\bar{b}$ | **0.01 °/s** | °/s | Valeur après 10 min de fonctionnement |

> **Justification de 0.01 °/s :** Le biais démarre à ±0.00056 °/s à froid mais croît lentement sous l'effet de la température (auto-échauffement des moteurs). Après 10 min de vol, le biais thermique s'ajoute : $b_{total} \approx b_0 + \alpha \cdot \Delta T \approx 0.01$ °/s. C'est la valeur conservatrice utilisée.

---

## 2. Calcul des Temps de Rupture par Axe

### 2.1 Formule RETA (condition affaiblie, biais oscillant)

$$t_{\text{rupture},i} \geq \frac{Y_{\max,i} - \frac{\pi}{2}}{\bar{b}_i}$$

> **Note :** $\pi/2 \approx 1.57°$ est le terme $\arctan(\infty)$ du système borné de référence. Pour des angles en degrés, il vaut 1.57°. Ce terme est **négligeable** devant $Y_{max} = 5°$ : il représente 31% de $Y_{max}$, donc on ne peut pas l'ignorer.

### 2.2 Calcul numérique — Borne conservative

**Axe X (Roll) — $Y_{max} = 5°$, $\bar{b}_x = 0.01$ °/s :**

$$t_{\text{rupture},x} \geq \frac{5 - 1.57}{0.01} = \frac{3.43}{0.01} = \mathbf{343 \text{ s} \approx 5 \text{ min } 43 \text{ s}}$$

**Axe Y (Pitch) — $Y_{max} = 5°$, $\bar{b}_y = 0.01$ °/s :**

$$t_{\text{rupture},y} \geq \frac{5 - 1.57}{0.01} = \mathbf{343 \text{ s}} \quad \text{(symétrique à X)}$$

**Axe Z (Yaw) — $Y_{max} = 10°$, $\bar{b}_z = 0.015$ °/s :**

> Le yaw est plus critique : le biais magnétique s'ajoute au biais gyroscope. On prend $\bar{b}_z = 0.015$ °/s.

$$t_{\text{rupture},z} \geq \frac{10 - 1.57}{0.015} = \frac{8.43}{0.015} = \mathbf{562 \text{ s} \approx 9 \text{ min } 22 \text{ s}}$$

### 2.3 Rupture globale du système

$$\boxed{t_{\text{rupture,global}} = \min(343,\ 343,\ 562) = 343 \text{ s} \approx 5 \text{ min } 43 \text{ s}}$$

**Interprétation :** Sans correction, le drone perd son cap précis en **moins de 6 minutes** sur les axes Roll et Pitch. C'est le premier axe à atteindre $Y_{max} = 5°$ qui déclenche l'alarme.

### 2.4 Valeur exacte (Newton-Raphson)

L'équation transcendante exacte pour l'axe X :

$$e_x(t) = \arctan(t) + \bar{b}_x \cdot t = Y_{max,x}$$
$$\arctan(t) + 0.01 \cdot t = 5$$

Résolution numérique :

| t [s] | arctan(t) [°] | 0.01·t [°] | Total [°] |
|---|---|---|---|
| 200 | 1.366 | 2.000 | 3.366 |
| 300 | 1.418 | 3.000 | 4.418 |
| 350 | 1.428 | 3.500 | 4.928 |
| 360 | 1.430 | 3.600 | 5.030 ✓ |

$$\boxed{t_{exact,x} = 358 \text{ s} \approx 5 \text{ min } 58 \text{ s}}$$

**Écart borne conservative / valeur exacte :**

$$\text{Ratio} = \frac{358}{343} = 1.04 \times \quad \text{(seulement 4% pessimiste ici)}$$

> L'écart est bien inférieur au facteur 4× de l'exemple canonique car $\bar{b} = 0.01$ est beaucoup plus petit que $\varepsilon_{canon} = 0.59$. Plus le biais est faible, plus le terme $\arctan(t)$ devient négligeable et plus la borne est précise.

---

## 3. Filtre de Kalman 3D (v1.1)

### 3.1 Modèle d'état par axe

Vecteur d'état pour chaque axe $i$ :

$$\mathbf{x}_i = \begin{pmatrix} \phi_i \\ b_i \end{pmatrix} \quad \text{(angle + biais)}$$

Équations d'état (discrètes, dt = 0.001 s) :

$$\mathbf{x}_i[k+1] = \underbrace{\begin{pmatrix} 1 & -dt \\ 0 & 1 \end{pmatrix}}_{A} \mathbf{x}_i[k] + \underbrace{\begin{pmatrix} dt \\ 0 \end{pmatrix}}_{B} \dot{\phi}_i^{meas}[k] + \mathbf{w}_i[k]$$

Équation de mesure (capteur d'angle externe : GPS/magnéto, recalage toutes les $T_{GPS}$ secondes) :

$$z_i[k] = \underbrace{\begin{pmatrix} 1 & 0 \end{pmatrix}}_{H} \mathbf{x}_i[k] + v_i[k]$$

### 3.2 Matrices de bruit

**Bruit de processus $Q_i$** (marche aléatoire du biais) :

$$Q_i = \begin{pmatrix} \sigma_{\phi}^2 \cdot dt & 0 \\ 0 & \sigma_b^2 \cdot dt \end{pmatrix} = \begin{pmatrix} (0.0028)^2 \cdot 0.001 & 0 \\ 0 & (0.00083)^2 \cdot 0.001 \end{pmatrix}$$

$$Q_x = Q_y = \begin{pmatrix} 7.84 \times 10^{-9} & 0 \\ 0 & 6.89 \times 10^{-10} \end{pmatrix}$$

**Bruit de mesure $R_i$** (GPS/capteur externe d'orientation) :

$$R_x = R_y = (0.5°)^2 = 0.25 \text{ deg}^2 \quad \text{(GPS basique)}$$
$$R_z = (2.0°)^2 = 4.0 \text{ deg}^2 \quad \text{(magnétomètre moins précis)}$$

### 3.3 Convergence de $P_\infty$ par axe

La variance de l'erreur d'estimation converge vers (solution de l'équation de Riccati) :

$$P_\infty = \frac{Q_{11} + \sqrt{Q_{11}^2 + 4 R \cdot Q_{22}}}{2}$$

**Axe X/Y :**
$$P_{\infty,x} = \frac{7.84 \times 10^{-9} + \sqrt{(7.84 \times 10^{-9})^2 + 4 \times 0.25 \times 6.89 \times 10^{-10}}}{2}$$
$$P_{\infty,x} \approx \sqrt{R \cdot Q_{22}} = \sqrt{0.25 \times 6.89 \times 10^{-10}} = 1.31 \times 10^{-5} \text{ deg}^2$$

**Écart-type d'estimation :** $\sigma_{\hat{\phi}_x} = \sqrt{P_{\infty,x}} \approx \mathbf{0.0036°}$ — très précis.

**Axe Z (magnéto) :**
$$P_{\infty,z} = \sqrt{4.0 \times 6.89 \times 10^{-10}} = 5.25 \times 10^{-5} \text{ deg}^2$$
$$\sigma_{\hat{\psi}_z} = \sqrt{P_{\infty,z}} \approx \mathbf{0.0072°}$$

### 3.4 Gain de Kalman stationnaire

$$K_{\infty,i} = \frac{P_{\infty,i}}{P_{\infty,i} + R_i}$$

**Axe X :** $K_{\infty,x} = \frac{1.31 \times 10^{-5}}{1.31 \times 10^{-5} + 0.25} \approx 5.25 \times 10^{-5}$ → poids très faible sur la mesure GPS (gyro fiable à court terme)

**Axe Z :** $K_{\infty,z} \approx 1.31 \times 10^{-5}$ → encore plus faible (magnéto moins précis)

---

## 4. Correcteur PI 3D (v1.1)

### 4.1 Architecture multi-axe découplée

Les trois axes sont découplés pour un drone quadrirotor (approximation valide en petits angles) :

$$u_x(t) = K_{p,x} \cdot \bar{e}_x(t) + K_{i,x} \int_0^t \bar{e}_x(\tau)\,d\tau$$
$$u_y(t) = K_{p,y} \cdot \bar{e}_y(t) + K_{i,y} \int_0^t \bar{e}_y(\tau)\,d\tau$$
$$u_z(t) = K_{p,z} \cdot \bar{e}_z(t) + K_{i,z} \int_0^t \bar{e}_z(\tau)\,d\tau$$

Où $\bar{e}_i = e_i / e_{ref,i}$ avec $e_{ref} = Y_{max}/2 = 2.5°$ (normalisation).

### 4.2 Dimensionnement des gains

**Objectif :** Temps de stabilisation $t_{stable} = 2$ s (bien inférieur à $t_{rupture} = 343$ s).

$$K_{p,x} = K_{p,y} = \frac{8}{t_{stable}} = \frac{8}{2} = 4.0$$

$$K_{i,x} = K_{i,y} = \frac{K_p^2}{4} = \frac{16}{4} = 4.0 \quad \text{(régime critique)}$$

**Axe Z (yaw) — Dynamique plus lente :**

Le yaw est contrôlé par la différence de couple des hélices, dynamique plus lente. On cible $t_{stable,z} = 5$ s :

$$K_{p,z} = \frac{8}{5} = 1.6, \quad K_{i,z} = \frac{1.6^2}{4} = 0.64$$

### 4.3 Bande résiduelle garantie

$$|e_i(t \to \infty)| \leq \frac{3 + \sqrt{2}}{K_{p,i}} \cdot e_{ref,i}$$

**Axe X/Y :**
$$|e_{x,\infty}| \leq \frac{4.41}{4.0} \times 2.5° = 2.76° \quad \text{(sous } Y_{max} = 5° \text{ ✓)}$$

**Axe Z :**
$$|e_{z,\infty}| \leq \frac{4.41}{1.6} \times 5° = 13.8° \quad \text{(dépasse } Y_{max} = 10° \text{ ⚠️)}$$

> **Problème détecté axe Z :** Avec $K_{p,z} = 1.6$, la bande résiduelle théorique dépasse $Y_{max}$. Il faut soit augmenter $K_{p,z}$, soit réduire $Y_{max,z}$.
>
> **Correction :** Prendre $K_{p,z} = 5$, $K_{i,z} = 6.25$ avec $t_{stable,z} = 1.6$ s.
>
> $$|e_{z,\infty}| \leq \frac{4.41}{5} \times 5° = 4.41° < 10° \quad \text{✓}$$

### 4.4 Action du correcteur sur les moteurs

$$\begin{pmatrix} \Omega_1^2 \\ \Omega_2^2 \\ \Omega_3^2 \\ \Omega_4^2 \end{pmatrix} = \underbrace{\frac{mg}{4k}}_{\text{hover}} + \underbrace{M^{-1}}_{4\times3} \begin{pmatrix} u_x \\ u_y \\ u_z \end{pmatrix}$$

Où $M$ est la matrice d'allocation des moteurs, $k$ la constante de poussée, $\Omega_i$ les vitesses de rotation des hélices.

---

## 5. Simulation Complète — Code Python

```python
import numpy as np
from scipy.linalg import solve_discrete_are

# ─── Paramètres physiques du drone ───────────────────────────────────────────
dt       = 0.001          # [s] pas d'intégration (1 kHz)
T_sim    = 600            # [s] durée simulation (10 minutes)
N        = int(T_sim/dt)
t        = np.linspace(0, T_sim, N)

# Biais gyroscope [°/s] — modèle thermique croissant
def bias(t, b0, tau_thermal=120):
    """Biais croissant par auto-échauffement."""
    return b0 * (1 + 0.5*(1 - np.exp(-t/tau_thermal)))

b0_xy = 0.005    # [°/s] biais initial axe X et Y
b0_z  = 0.008    # [°/s] biais initial axe Z (magnéto additif)

# Seuils de rupture [°]
Y_max = np.array([5.0, 5.0, 10.0])   # [roll, pitch, yaw]
e_ref = Y_max / 2                      # [2.5, 2.5, 5.0] normalisation

# ─── Kalman — matrices par axe ────────────────────────────────────────────────
sigma_angle = 0.0028    # [°/√Hz] bruit mesure gyro
sigma_bias  = 0.00083   # [°/s/√h] instabilité biais

Q_base = np.diag([sigma_angle**2 * dt, sigma_bias**2 * dt])
R_mes  = np.array([0.25, 0.25, 4.0])   # [deg²] variance mesure externe par axe
H      = np.array([[1.0, 0.0]])
A      = np.array([[1, -dt], [0, 1]])

# Calcul P_inf par résolution de l'équation de Riccati discrète
P_inf = []
K_inf = []
for Ri in R_mes:
    Pi = solve_discrete_are(A.T, H.T, Q_base, np.array([[Ri]]))
    S  = H @ Pi @ H.T + Ri
    Ki = Pi @ H.T / S
    P_inf.append(Pi)
    K_inf.append(Ki.flatten())

print("P_inf estimé par axe [deg²] :")
for i, name in enumerate(['Roll (X)', 'Pitch (Y)', 'Yaw (Z)']):
    print(f"  {name} : P00={P_inf[i][0,0]:.2e}  σ_angle={np.sqrt(P_inf[i][0,0])*1000:.3f} m°")

# ─── PI gains ────────────────────────────────────────────────────────────────
Kp = np.array([4.0,  4.0,  5.0])    # [roll, pitch, yaw]
Ki = np.array([4.0,  4.0,  6.25])

# ─── État initial ─────────────────────────────────────────────────────────────
phi_true  = np.zeros(3)   # angles vrais [roll, pitch, yaw] en °
phi_est   = np.zeros(3)   # angles estimés par Kalman
bias_est  = np.zeros(3)   # biais estimés par Kalman
P_kalman  = [Q_base.copy() for _ in range(3)]
I_err     = np.zeros(3)   # intégrateur PI
phi_ref   = np.zeros(3)   # cap de référence (maintien de position)

# Buffers
traj_phi_true = np.zeros((N, 3))
traj_phi_est  = np.zeros((N, 3))
traj_error    = np.zeros((N, 3))
traj_bias_est = np.zeros((N, 3))
traj_u        = np.zeros((N, 3))
traj_V        = np.zeros((N, 3))   # Lyapunov par axe

# GPS recalage toutes les 1 s
T_GPS = 1.0
k_GPS = int(T_GPS / dt)

# ─── Boucle de simulation ─────────────────────────────────────────────────────
for k in range(N):
    tk = t[k]

    # Biais vrais (non connus du filtre)
    b_true = np.array([
        bias(tk, b0_xy),
        bias(tk, b0_xy * 1.1),   # Pitch légèrement plus fort
        bias(tk, b0_z)
    ])

    # Vitesse angulaire mesurée (vraie + biais + bruit)
    noise = np.random.randn(3) * 0.0028
    dphi_meas = np.zeros(3) + b_true + noise   # vol stationnaire (dphi_true = 0)

    for i in range(3):
        # ── Prédiction Kalman ──
        x_pred = A @ np.array([phi_est[i], bias_est[i]]) + np.array([dt, 0]) * dphi_meas[i]
        P_pred = A @ P_kalman[i] @ A.T + Q_base

        # ── Correction Kalman (si recalage GPS disponible) ──
        if k % k_GPS == 0:
            S_k  = H @ P_pred @ H.T + R_mes[i]
            K_k  = (P_pred @ H.T) / S_k
            innov = phi_true[i] + np.random.randn() * np.sqrt(R_mes[i]) - x_pred[0]
            x_upd = x_pred + K_k.flatten() * innov
            P_kalman[i] = (np.eye(2) - np.outer(K_k.flatten(), H)) @ P_pred
        else:
            x_upd = x_pred
            P_kalman[i] = P_pred

        phi_est[i]  = x_upd[0]
        bias_est[i] = x_upd[1]

        # ── Correcteur PI (sur erreur normalisée) ──
        err_i  = phi_est[i] - phi_ref[i]
        e_bar  = err_i / e_ref[i]
        I_err[i] += e_bar * dt
        u_i    = (Kp[i] * e_bar + Ki[i] * I_err[i]) * e_ref[i]

        # ── Dynamique drone : correction appliquée aux angles ──
        dphi_true_i  = b_true[i] - u_i    # biais - correction
        phi_true[i] += dphi_true_i * dt

        # ── Lyapunov V = e²/2 + (Ki/2)·I² ──
        traj_V[k, i] = 0.5 * err_i**2 + (Ki[i]/2) * (I_err[i] * e_ref[i])**2

        traj_u[k, i] = u_i

    traj_phi_true[k] = phi_true.copy()
    traj_phi_est[k]  = phi_est.copy()
    traj_error[k]    = phi_true - phi_ref
    traj_bias_est[k] = bias_est.copy()

# ─── Analyse des résultats ───────────────────────────────────────────────────
print("\n=== RÉSULTATS SIMULATION ===\n")

axes = ['Roll (X)', 'Pitch (Y)', 'Yaw (Z)']
for i, name in enumerate(axes):
    e_max   = np.max(np.abs(traj_error[:, i]))
    e_final = np.mean(np.abs(traj_error[int(0.9*N):, i]))
    crossed = np.where(np.abs(traj_error[:, i]) > Y_max[i])[0]
    t_cross = t[crossed[0]] if len(crossed) > 0 else None

    print(f"Axe {name} :")
    print(f"  Erreur max        : {e_max:.4f}°")
    print(f"  Erreur résiduelle : {e_final:.4f}°  (bande théorique ≤ {4.41/Kp[i]*e_ref[i]:.3f}°)")
    print(f"  Rupture Y_max={Y_max[i]}° : {'JAMAIS ✓' if t_cross is None else f'à t={t_cross:.1f}s ⚠️'}")
    print(f"  Biais estimé final: {bias_est[i]*1000:.3f} m°/s  (vrai: {b_true[i]*1000:.3f} m°/s)")
    print()
```

---

## 6. Résultats Attendus

### 6.1 Sans correcteur PI (gyro seul)

| Axe | t_rupture conservatif | t_exact | Erreur à 10 min |
|---|---|---|---|
| Roll (X) | 343 s (5'43") | 358 s (5'58") | **+6.03°** (dépasse Y_max) |
| Pitch (Y) | 343 s | 358 s | **+6.03°** (dépasse Y_max) |
| Yaw (Z) | 562 s (9'22") | 598 s | +8.99° (proche Y_max) |

→ Sans Kalman ni PI, le drone perd son cap précis en moins de 6 minutes.

### 6.2 Avec Kalman v1.1 seul (pas de PI)

Kalman estime et soustrait le biais :
- Erreur d'estimation du biais : $\sigma_b \approx 0.001$ °/s
- Erreur résiduelle après correction gyro : $\sigma_\phi \approx 0.0036°$ à court terme
- Mais sans PI : erreur résiduelle croît encore à $\approx 0.1°/h$ (biais résiduel × temps)

### 6.3 Avec Kalman + PI (RETA v1.1)

| Axe | Erreur résiduelle | Stabilisation | Rupture |
|---|---|---|---|
| Roll (X) | ≤ 2.76° | t_stable = 2 s | **JAMAIS** ✓ |
| Pitch (Y) | ≤ 2.76° | t_stable = 2 s | **JAMAIS** ✓ |
| Yaw (Z) | ≤ 4.41° | t_stable = 1.6 s | **JAMAIS** ✓ |

Le drone maintient son cap indéfiniment avec une erreur bornée.

### 6.4 Vérification Lyapunov

La fonction $V_i(t) = \frac{1}{2}e_i^2 + \frac{K_{i,i}}{2}I_i^2$ doit décroître après $t_{stable}$ :

| Phase | Comportement de $V_i$ |
|---|---|
| $t < t_{stable} = 2$ s | Croissance (transitoire) |
| $t > t_{stable}$ | Décroissance monotone → plancher résiduel |
| $t \to \infty$ | $V_i \to \frac{1}{2}e_{res}^2$ (bande résiduelle) |

---

## 7. Synthèse RETA 3D

### 7.1 Tableau récapitulatif complet

| Grandeur | Axe X (Roll) | Axe Y (Pitch) | Axe Z (Yaw) |
|---|---|---|---|
| Biais $\bar{b}_i$ | 0.010 °/s | 0.011 °/s | 0.015 °/s |
| Seuil $Y_{max,i}$ | 5° | 5° | 10° |
| $t_{rup}$ conservatif | **343 s** | 343 s | 562 s |
| $t_{rup}$ exact | **358 s** | 358 s | 598 s |
| $K_{p,i}$ | 4.0 | 4.0 | 5.0 |
| $K_{i,i}$ | 4.0 | 4.0 | 6.25 |
| $t_{stable,i}$ | 2 s | 2 s | 1.6 s |
| Bande résiduelle $|e_{i,\infty}|$ | ≤ 2.76° | ≤ 2.76° | ≤ 4.41° |
| $P_{\infty,i}$ [deg²] | 1.31×10⁻⁵ | 1.31×10⁻⁵ | 5.25×10⁻⁵ |
| $\sigma_{\hat{\phi}_i}$ | 0.0036° | 0.0036° | 0.0072° |

### 7.2 Hiérarchie des temps

$$\underbrace{t_{stable} = 2\text{s}}_{\text{PI corrige}} \ll \underbrace{t_{exact} = 358\text{s}}_{\text{rupture sans PI}} \ll \underbrace{T_{vol} = 600\text{s}}_{\text{durée vol}}$$

Le correcteur PI agit **179× plus vite** que la rupture — marge de sécurité très confortable.

### 7.3 Axe critique global

$$i^* = \arg\min_i\ t_{\text{rupture},i} = \text{Roll (X) ou Pitch (Y)} \quad \Rightarrow \quad t_{\text{rupture,global}} = 343 \text{ s}$$

L'axe critique est Roll ou Pitch (symétrique). C'est le premier axe à surveiller en cas de dégradation du correcteur.

---

## 8. Extension v1.3 — Kalman Adaptatif

En vol réel, la dynamique du biais change avec la température :

$$\dot{Q}(t) = \gamma_Q \cdot \nu_k \nu_k^T - Q(t) \cdot \lambda$$
$$\dot{R}(t) = \gamma_R \cdot (\nu_k^2 - H P_k^- H^T) - R(t) \cdot \lambda$$

Où $\nu_k = z_k - H\hat{x}_k^-$ est l'innovation. La version v1.3 auto-calibre $Q$ et $R$ en temps réel, ce qui est critique quand les moteurs chauffent et modifient le biais thermique en vol.

---

*[📖 Index exemples](../README.md) · [📖 Systèmes physiques](../physique.md) · [📖 Index global](../../INDEX.md)*
