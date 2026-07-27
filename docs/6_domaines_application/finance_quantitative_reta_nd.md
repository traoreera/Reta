# RETA-nD applique a la gestion de risque financier — extension experimentale

> AVERTISSEMENT : experimental, non valide sur donnees de marche reelles.
> Valide uniquement sur donnees CIR synthetiques (parametres connus a
> priori). Voir docs/6_domaines_application/finance.md pour le rappel de
> l'hypothese z(t) >= eps qui limite le coeur scalaire (non applicable ici :
> cette extension porte sur la dispersion, pas la derive nette).

## Ce qui a change dans le code (integre directement, pas un module a part)

| Point | Fichier | Changement |
|---|---|---|
| 1 | `reta/nd.py`, `reta/dispersion.py` | `n_eff` n'est plus clampe a 2.0 silencieusement. `is_crisis_regime()` + `FellerConditionViolated` + `RETAND.n_eff_diagnostics()` + `t_rupture_joint(..., crisis_fallback="raise"/"zero"/"clamp")` |
| 2 | `reta/nd.py` (`_residual_covariance`) | Shrinkage Ledoit-Wolf (scikit-learn), fallback `np.cov` avec avertissement si indisponible, avertissement si fenetre < 3n |
| 3 | `reta/finance.py` (nouveau) | `calibrate_cir_mle(radius_series, dt, n_eff)` — MLE de (D, Kp) sur khi-deux non centree |
| 4 | `reta/finance.py` (nouveau) | `first_passage_time_mc(...)` — premier passage par simulation EXACTE (barriere absorbante), corrige le biais de `dispersion.first_passage_time` |

## Validation (donnees synthetiques)

- **n_eff** : 3 actifs independants -> n_eff ~ 2,79 ; 3 actifs quasi-identiques -> n_eff ~ 1,00 (mesure directe, formule confirmee).
- **MLE (point 3)**, 1 trajectoire CIR connue (Kp=0.15, D=0.02, dt=0.1, 2000 pas) : retrouve Kp~0.118, D~0.019 — ordre de grandeur correct sur trajectoire unique.
- **Biais du point 4** : pour n_eff=2.5, D=0.02, Kp=0.10, Y_max=1.0, r0=0.3 — `first_passage_time` (analytique, sans barriere) predit un temps de rupture **infini**, alors que la simulation Monte Carlo (avec barriere) montre que **100% des trajectoires rompent**, en mediane a t=15,9. Ce n'est pas un biais marginal : c'est une erreur qualitative des que theta < Y_max.

## Utilisation

```python
from reta.nd import RETAND, FellerConditionViolated
from reta.finance import radius_series_from_returns, calibrate_cir_mle, first_passage_time_mc

nd = RETAND(n=20, Y_max_axes=[Y_MAX]*20)
for row in returns_window:
    nd.step(row)

n_eff, crisis = nd.n_eff_diagnostics()
if crisis:
    # correlation extreme : traiter explicitement plutot que de laisser
    # t_rupture_joint() lever FellerConditionViolated par defaut
    ...
```

Voir `examples/fetch_binance.py` (panier de 20 paires USDT, pagination
complete, reseau Binance requis — non testable depuis ce sandbox) et
`examples/exemple_finance.py` pour le pipeline complet.

**Non teste sur donnees reelles a ce stade.**

---

[Index de la Documentation](../INDEX.md)
