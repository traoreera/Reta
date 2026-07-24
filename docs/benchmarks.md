# RETA Benchmarks

This benchmark suite uses NASA GISTEMP v4 annual surface temperature anomalies as a real drift source. The raw annual series is transformed into a positive disturbance stream so that the RETA assumptions stay consistent: persistent drift, bounded base signal, and threshold-crossing prediction.

## Why NASA GISTEMP

- It is public, versioned, and updated regularly.
- It contains a long enough time series to test online estimation.
- Its warming trend gives RETA a realistic cumulative signal instead of a toy-only curve.

## Benchmark Design

The script in `benchmarks/nasa_gistemp_reta.py` evaluates the four versioned RETA stacks on the same source stream:

- `v1.1`: fixed Kalman + fixed PI.
- `v1.2`: fixed Kalman + adaptive PI.
- `v1.3`: adaptive Kalman Q + adaptive PI, with a data gap to test recovery.
- `v1.4`: `v1.3` plus a conservative quadratic rupture bound.

The benchmark reports:

- level tracking RMSE
- disturbance estimation RMSE
- threshold-bound error
- conservatism rate for `v1.4`
- control effort

## Run

```bash
uv run python benchmarks/nasa_gistemp_reta.py
```

Artifacts are written under `benchmarks/results/`.

## How to Read the Results

- `v1.1` is the baseline.
- `v1.2` should reduce post-shift error by adapting the PI gains.
- `v1.3` should recover better through missing data and changing noise.
- `v1.4` should keep the rupture bound on the safe side of the real crossing.

---

**🔗 Voir aussi** : [Versions RETA](VERSIONS.md) · [Théorie Fondamentale](1_fondamentaux/theorie_fondamentale.md) · [Bibliographie](bibliographie.md)

---

[📖 Index de la Documentation](INDEX.md) · [🏠 Accueil du Projet](../README.md)
