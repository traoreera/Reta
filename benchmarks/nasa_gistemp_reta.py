"""
NASA GISTEMP RETA Benchmark
===========================

Benchmarks the four RETA versions on a single NASA GISTEMP v4 temperature
anomaly stream. The raw annual anomalies are converted into a positive drift
signal, then each version is evaluated on:

  - level tracking RMSE
  - threshold-crossing prediction error
  - control effort
  - conservatism of the rupture bound (v1.4)

Outputs:
  - benchmarks/results/nasa_gistemp_reta_bench.json
  - benchmarks/results/nasa_gistemp_reta_bench.md
  - benchmarks/results/nasa_gistemp_reta_bench.png
"""

from __future__ import annotations

import argparse
import csv
import io
import json
from dataclasses import dataclass
from pathlib import Path
import urllib.request

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

NASA_URL = "https://data.giss.nasa.gov/gistemp/tabledata_v4/GLB.Ts+dSST.csv"
DATA_DIR = Path(__file__).with_name("data")
RESULTS_DIR = Path(__file__).with_name("results")
CACHE_PATH = DATA_DIR / "GLB.Ts+dSST.csv"


@dataclass(frozen=True)
class VersionSpec:
    name: str
    adaptive_pi: bool
    adaptive_q: bool
    gap_start: int | None = None
    gap_end: int | None = None
    conservative_bound: bool = False
    label: str = ""


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def download_nasa_csv(refresh: bool = False) -> str:
    if CACHE_PATH.exists() and not refresh:
        return CACHE_PATH.read_text(encoding="utf-8")

    print("Downloading NASA GISTEMP v4 data...")
    with urllib.request.urlopen(NASA_URL, timeout=30) as response:
        text = response.read().decode("utf-8")
    CACHE_PATH.write_text(text, encoding="utf-8")
    return text


def parse_gistemp_annual_series(csv_text: str) -> tuple[np.ndarray, np.ndarray]:
    years: list[int] = []
    anomalies: list[float] = []
    reader = csv.reader(io.StringIO(csv_text))
    header_seen = False

    for row in reader:
        if not row:
            continue
        if row[0].strip() == "Year":
            header_seen = True
            continue
        if not header_seen:
            continue
        try:
            year = int(row[0].strip())
            annual = row[13].strip()
            if annual in {"", "****"}:
                continue
            years.append(year)
            anomalies.append(float(annual))
        except (ValueError, IndexError):
            continue

    if not years:
        raise RuntimeError("No annual GISTEMP values could be parsed.")

    years_array = np.asarray(years, dtype=int)
    anomalies_array = np.asarray(anomalies, dtype=float)
    mask = years_array >= 1951
    return years_array[mask], anomalies_array[mask]


def build_drift_stream(anomalies: np.ndarray) -> np.ndarray:
    diffs = np.diff(anomalies, prepend=anomalies[0])
    positive_drift = np.maximum(diffs, 0.0)
    level_term = np.maximum(anomalies - anomalies.min(), 0.0)
    z_true = 0.018 + 0.75 * positive_drift + 0.02 * level_term
    return np.clip(z_true, 1e-4, None)


def base_drift(year_index: int) -> float:
    return 0.015 / (1.0 + (year_index / 28.0) ** 2)


def kalman_predict(x: np.ndarray, p: np.ndarray, q_level: float, q_slope: float) -> tuple[np.ndarray, np.ndarray]:
    dt = 1.0
    a = np.array([[1.0, dt], [0.0, 1.0]])
    q = np.diag([q_level, q_slope])
    x_pred = a @ x
    p_pred = a @ p @ a.T + q
    return x_pred, p_pred


def kalman_update(x: np.ndarray, p: np.ndarray, observation: float, r: float) -> tuple[np.ndarray, np.ndarray, float]:
    h = np.array([[1.0, 0.0]])
    s = float((h @ p @ h.T).item()) + r
    k = (p @ h.T).flatten() / s
    innovation = float(observation) - float((h @ x).item())
    x_upd = x + k * innovation
    p_upd = (np.eye(2) - np.outer(k, h)) @ p
    return x_upd, p_upd, innovation


def conservative_bound(level: float, slope: float, slope_rate: float, y_max: float) -> float:
    rem = y_max - level
    if rem <= 0:
        return 0.0
    slope = max(slope, 1e-8)
    slope_rate = max(slope_rate, 1e-8)
    disc = slope ** 2 + 2.0 * slope_rate * rem
    return max((-slope + np.sqrt(max(disc, 0.0))) / slope_rate, 0.0)


def run_version(
    years: np.ndarray,
    anomalies: np.ndarray,
    drift: np.ndarray,
    spec: VersionSpec,
    seed: int,
) -> dict:
    rng = np.random.default_rng(seed)

    y_target = 0.55
    y_max = 1.20
    obs_sigma = 0.015
    q_level = 1e-4
    q_slope = 1e-3 if not spec.adaptive_q else 5e-4
    r_meas = obs_sigma ** 2
    q_min = 1e-6
    q_ema = 0.35
    gamma_p = 0.18
    gamma_i = 0.035
    kp = 0.18
    ki = 0.022
    kp_bounds = (0.04, 0.9)
    ki_bounds = (0.0, 0.18)

    x = np.array([drift[0], 0.0], dtype=float)
    p = np.diag([0.08, 0.02])
    slope_x = np.array([drift[0], 0.0], dtype=float)
    slope_p = np.diag([0.08, 0.02])

    y = 0.0
    integral_e = 0.0
    pred_remaining: list[float] = []
    actual_remaining: list[float] = []
    y_hist: list[float] = []
    z_true_hist: list[float] = []
    z_obs_hist: list[float] = []
    z_est_hist: list[float] = []
    z_rate_hist: list[float] = []
    kp_hist: list[float] = []
    ki_hist: list[float] = []
    u_hist: list[float] = []
    q_hist: list[float] = []

    for idx, year in enumerate(years):
        z_true = float(drift[idx])
        z_obs = z_true + rng.normal(0.0, obs_sigma)
        observed = True
        if spec.gap_start is not None and spec.gap_end is not None:
            if spec.gap_start <= year <= spec.gap_end:
                observed = False

        x, p = kalman_predict(x, p, q_level, q_slope)
        innovation = 0.0
        if observed:
            x, p, innovation = kalman_update(x, p, z_obs, r_meas)
            if spec.adaptive_q:
                q_inst = max((abs(innovation) / 4.0) ** 2, q_min)
                q_slope = (1.0 - q_ema) * q_slope + q_ema * q_inst
                q_slope = max(q_slope, q_min)

        z_est = float(x[0])
        z_rate = float(x[1])

        if spec.conservative_bound:
            slope_x, slope_p = kalman_predict(slope_x, slope_p, 1e-6, 1e-5)
            if observed:
                slope_x, slope_p, _ = kalman_update(slope_x, slope_p, z_est, 0.0025)
            z_rate_bound = max(float(slope_x[1]) * 1.25, 1e-8)
        else:
            z_rate_bound = max(z_rate, 1e-8)

        e = y - y_target
        e_norm = e / y_max
        integral_e += e_norm

        if spec.adaptive_pi:
            kp = float(np.clip(kp + gamma_p * (e_norm ** 2), *kp_bounds))
            ki = float(np.clip(ki + gamma_i * e_norm * integral_e, *ki_bounds))

        u = kp * e + ki * integral_e
        y += base_drift(idx) + z_true - u

        if spec.conservative_bound:
            pred = conservative_bound(y, z_est, z_rate_bound, y_max)
        else:
            pred = max((y_max - y) / max(z_est, 1e-8), 0.0)

        pred_remaining.append(pred)
        y_hist.append(y)
        z_true_hist.append(z_true)
        z_obs_hist.append(z_obs if observed else np.nan)
        z_est_hist.append(z_est)
        z_rate_hist.append(z_rate)
        kp_hist.append(kp)
        ki_hist.append(ki)
        u_hist.append(u)
        q_hist.append(q_slope)

    y_arr = np.asarray(y_hist)
    rupture_idx = np.where(np.abs(y_arr) >= y_max)[0]
    rupture_year = int(years[rupture_idx[0]]) if len(rupture_idx) else int(years[-1])
    rupture_reached = len(rupture_idx) > 0

    for year in years:
        if year > rupture_year:
            actual_remaining.append(0.0)
        else:
            actual_remaining.append(float(rupture_year - year))

    valid = np.asarray(years) < rupture_year
    pred_arr = np.asarray(pred_remaining)[valid]
    actual_arr = np.asarray(actual_remaining)[valid]
    z_true_arr = np.asarray(z_true_hist)
    z_est_arr = np.asarray(z_est_hist)

    rmse_y = float(np.sqrt(np.mean((y_arr - y_target) ** 2)))
    mae_bound = float(np.mean(np.abs(pred_arr - actual_arr))) if len(pred_arr) else 0.0
    signed_bound = float(np.mean(pred_arr - actual_arr)) if len(pred_arr) else 0.0
    conservatism_rate = float(np.mean(pred_arr <= actual_arr)) if len(pred_arr) else 0.0
    control_effort = float(np.trapz(np.abs(u_hist), dx=1.0))
    est_rmse = float(np.sqrt(np.mean((z_est_arr - z_true_arr) ** 2)))
    peak_overshoot = float(np.max(np.abs(y_arr) - y_max))

    gap_recovery = None
    if spec.gap_start is not None and spec.gap_end is not None:
        post_gap = np.where(np.asarray(years) > spec.gap_end)[0]
        if len(post_gap):
            errors = np.abs(z_est_arr[post_gap] - z_true_arr[post_gap])
            stable = np.where(errors < 0.01)[0]
            if len(stable):
                gap_recovery = int(years[post_gap[stable[0]]])

    return {
        "spec": spec,
        "years": years.tolist(),
        "y": y_arr.tolist(),
        "z_true": z_true_arr.tolist(),
        "z_obs": z_obs_hist,
        "z_est": z_est_arr.tolist(),
        "z_rate": z_rate_hist,
        "u": u_hist,
        "kp": kp_hist,
        "ki": ki_hist,
        "q_slope": q_hist,
        "pred_remaining": pred_remaining,
        "actual_remaining": actual_remaining,
        "rupture_year": rupture_year,
        "rupture_reached": rupture_reached,
        "metrics": {
            "rmse_y": rmse_y,
            "est_rmse": est_rmse,
            "mae_bound": mae_bound,
            "signed_bound": signed_bound,
            "conservatism_rate": conservatism_rate,
            "control_effort": control_effort,
            "peak_overshoot": peak_overshoot,
            "gap_recovery_year": gap_recovery,
        },
    }


def write_report(years: np.ndarray, anomalies: np.ndarray, drift: np.ndarray, results: list[dict]) -> None:
    summary_json = RESULTS_DIR / "nasa_gistemp_reta_bench.json"
    summary_md = RESULTS_DIR / "nasa_gistemp_reta_bench.md"
    summary_png = RESULTS_DIR / "nasa_gistemp_reta_bench.png"

    payload = {
        "source": NASA_URL,
        "years": [int(years[0]), int(years[-1])],
        "versions": [
            {
                "name": item["spec"].name,
                "metrics": item["metrics"],
                "rupture_year": item["rupture_year"],
                "rupture_reached": item["rupture_reached"],
            }
            for item in results
        ],
    }
    summary_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = [
        "# NASA GISTEMP RETA Benchmark",
        "",
        f"- Source: `{NASA_URL}`",
        f"- Cache: `{CACHE_PATH}`",
        f"- Window: {int(years[0])} to {int(years[-1])}",
        "",
        "## Version Summary",
        "",
        "| Version | Rupture year | RMSE(y) | Est RMSE(z) | Bound MAE | Conservatism | Control effort |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for item in results:
        m = item["metrics"]
        lines.append(
            f"| {item['spec'].name} | {item['rupture_year']} | {m['rmse_y']:.4f} | {m['est_rmse']:.4f} | "
            f"{m['mae_bound']:.4f} | {m['conservatism_rate']:.3f} | {m['control_effort']:.3f} |"
        )
    lines += [
        "",
        "## Notes",
        "",
        "- `v1.1`: fixed Kalman + fixed PI.",
        "- `v1.2`: fixed Kalman + adaptive PI.",
        "- `v1.3`: adaptive Kalman Q + adaptive PI, with an observation gap from 2005 to 2010.",
        "- `v1.4`: same as v1.3 plus a conservative quadratic rupture bound using a slope tracker.",
    ]
    summary_md.write_text("\n".join(lines), encoding="utf-8")

    fig, axes = plt.subplots(4, 1, figsize=(14, 18), sharex=True)
    fig.suptitle("NASA GISTEMP RETA Benchmark", fontsize=14, fontweight="bold")

    axes[0].plot(years, anomalies, color="#1f77b4", lw=1.5)
    axes[0].set_title("NASA annual anomalies (GISTEMP v4)")
    axes[0].set_ylabel("anomaly")

    axes[1].plot(years, drift, color="#d62728", lw=1.5, label="z true")
    for item in results:
        axes[1].plot(years, item["z_est"], lw=1.0, label=item["spec"].name)
    axes[1].set_title("Disturbance estimation")
    axes[1].set_ylabel("z")
    axes[1].legend(fontsize=8, ncol=2)

    for item in results:
        axes[2].plot(years, item["y"], lw=1.3, label=item["spec"].name)
    axes[2].axhline(1.20, color="red", ls="--", lw=1, label="Y_max")
    axes[2].axhline(0.55, color="gray", ls=":", lw=1, label="target")
    axes[2].set_title("Closed-loop response")
    axes[2].set_ylabel("y")
    axes[2].legend(fontsize=8, ncol=2)

    for item in results:
        axes[3].plot(years, item["pred_remaining"], lw=1.3, label=item["spec"].name)
    axes[3].set_title("Predicted remaining time to threshold")
    axes[3].set_ylabel("years")
    axes[3].set_xlabel("year")
    axes[3].legend(fontsize=8, ncol=2)

    plt.tight_layout()
    plt.savefig(summary_png, dpi=160, bbox_inches="tight")
    print(f"Wrote {summary_json}")
    print(f"Wrote {summary_md}")
    print(f"Wrote {summary_png}")


def main() -> None:
    parser = argparse.ArgumentParser(description="NASA GISTEMP RETA benchmark")
    parser.add_argument("--refresh", action="store_true", help="re-download the NASA CSV")
    args = parser.parse_args()

    ensure_dirs()
    csv_text = download_nasa_csv(refresh=args.refresh)
    years, anomalies = parse_gistemp_annual_series(csv_text)
    drift = build_drift_stream(anomalies)

    specs = [
        VersionSpec(
            name="v1.1",
            adaptive_pi=False,
            adaptive_q=False,
            label="fixed Kalman + fixed PI",
        ),
        VersionSpec(
            name="v1.2",
            adaptive_pi=True,
            adaptive_q=False,
            label="fixed Kalman + adaptive PI",
        ),
        VersionSpec(
            name="v1.3",
            adaptive_pi=True,
            adaptive_q=True,
            gap_start=2005,
            gap_end=2010,
            label="adaptive Kalman Q + adaptive PI + outage",
        ),
        VersionSpec(
            name="v1.4",
            adaptive_pi=True,
            adaptive_q=True,
            gap_start=2005,
            gap_end=2010,
            conservative_bound=True,
            label="v1.3 + conservative quadratic bound",
        ),
    ]

    results = []
    for idx, spec in enumerate(specs):
        results.append(run_version(years, anomalies, drift, spec, seed=42 + idx))

    write_report(years, anomalies, drift, results)

    print("\nBenchmark summary")
    for item in results:
        m = item["metrics"]
        print(
            f"{item['spec'].name}: rupture={item['rupture_year']} "
            f"rmse_y={m['rmse_y']:.4f} est_rmse={m['est_rmse']:.4f} "
            f"bound_mae={m['mae_bound']:.4f} conservatism={m['conservatism_rate']:.3f}"
        )


if __name__ == "__main__":
    main()
