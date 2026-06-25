# Benchmarks

This folder contains the NASA-based RETA benchmark harness.

## Dataset

- Source: NASA GISTEMP v4 annual surface temperature anomalies.
- Download URL: `https://data.giss.nasa.gov/gistemp/tabledata_v4/GLB.Ts+dSST.csv`
- The script caches the CSV in `benchmarks/data/GLB.Ts+dSST.csv`.

## Script

Run the benchmark with:

```bash
uv run python benchmarks/nasa_gistemp_reta.py
```

Optional refresh:

```bash
uv run python benchmarks/nasa_gistemp_reta.py --refresh
```

## Version Mapping

- `v1.1`: fixed Kalman + fixed PI baseline.
- `v1.2`: fixed Kalman + adaptive PI.
- `v1.3`: adaptive Kalman Q + adaptive PI, with an observation gap from 2005 to 2010.
- `v1.4`: same as `v1.3`, plus a conservative quadratic rupture bound.

## Outputs

The script writes its artifacts to `benchmarks/results/`:

- `nasa_gistemp_reta_bench.json`
- `nasa_gistemp_reta_bench.md`
- `nasa_gistemp_reta_bench.png`
