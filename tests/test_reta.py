"""Tests unitaires — cœur RETA classique (v1.4) et RETA-nD."""

import math

import numpy as np
import pytest

from reta.kalman import Kalman1D, KalmanAdaptive
from reta.pi import PIRegulator
from reta.core import RETAReferential
from reta.dispersion import (
    effective_dimension,
    cir_params,
    transition_cdf,
    first_passage_time,
)
from reta.nd import RETAND


# ── Kalman ────────────────────────────────────────────────────────────────

class TestKalman1D:
    def test_batch_shape(self):
        n = 100
        k = Kalman1D()
        z, p = k.batch(np.random.randn(n))
        assert len(z) == n
        assert len(p) == n

    def test_converges_to_constant_signal(self):
        k = Kalman1D(Q=1e-3, R=1e-3)
        signal = np.ones(500) * 0.02
        z, _ = k.batch(signal)
        assert abs(z[-1] - 0.02) < 1e-2

    def test_rolling_mean(self):
        x = np.arange(10, dtype=float)
        m = Kalman1D.rolling_mean(x, window=3)
        assert len(m) == 10
        assert m[0] == 0.0
        assert abs(m[-1] - 8.0) < 1e-9


class TestKalmanAdaptive:
    def test_adaptation_positive(self):
        k = KalmanAdaptive()
        k.batch(np.random.randn(100) * 0.01)
        assert k.R_current > 0
        assert k.Q_current > 0
        assert 0 <= k.signal_quality <= 1

    def test_converges_to_ramp(self):
        np.random.seed(0)
        n = 300
        true_z = 0.01 + 0.0002 * np.arange(n)
        obs = true_z + np.random.randn(n) * 0.002
        k = KalmanAdaptive()
        z, _ = k.batch(obs)
        assert abs(z[-1] - true_z[-1]) < 0.02
        assert k.dz > 0  # doit détecter la pente positive


# ── PI ────────────────────────────────────────────────────────────────────

class TestPIRegulator:
    def test_zero_error_no_command(self):
        pi = PIRegulator(adaptive=False)
        assert pi.step(0.0) == 0.0

    def test_gains_stay_bounded(self):
        pi = PIRegulator(Kp_max=5.0, Ki_max=5.0, gamma_p=10.0, gamma_i=10.0)
        for _ in range(1000):
            pi.step(1.0)
        assert pi.Kp <= 5.0
        assert pi.Ki <= 5.0

    def test_regulation_reduces_error_over_time(self):
        pi = PIRegulator(Kp=3.0, Ki=1.0, e_ref=1.0)
        y = 5.0
        errors = []
        for _ in range(200):
            e = y
            u = pi.step(e, dt=0.05)
            y += (0.5 - u) * 0.05  # perturbation constante 0.5, contrée par u
            errors.append(abs(e))
        assert errors[-1] < errors[0]


# ── Core (RETA classique v1.4) ──────────────────────────────────────────

class TestRETAReferential:
    def test_fit_returns_history(self):
        np.random.seed(1)
        obs = np.ones(150) * 0.05 + np.random.randn(150) * 0.01
        ref = RETAReferential(Y_max=10.0, dt=1.0)
        history = ref.fit(obs)
        assert len(history) == 150
        assert ref.t == 150.0

    def test_t_rupture_positive_for_positive_drift(self):
        np.random.seed(2)
        # Drift modeste, peu de pas : la marge jusqu'à Y_max reste positive
        # à la fin de la fenêtre observée (rupture prédite, mais future).
        obs = np.ones(60) * 0.05 + np.random.randn(60) * 0.005
        ref = RETAReferential(Y_max=10.0, adaptive_pi=False, Kp0=0.0, Ki0=0.0)
        ref.fit(obs)
        assert ref.history[-1].y_open < ref.Y_max
        t_rup = ref.t_rupture()
        assert t_rup > ref.t  # rupture dans le futur

    def test_t_rupture_falls_back_to_linear_when_dz_zero(self):
        ref = RETAReferential(Y_max=10.0, adaptive_pi=False, Kp0=0.0, Ki0=0.0)
        obs = np.ones(100) * 0.1
        ref.fit(obs)
        t_rup = ref.t_rupture()
        assert math.isfinite(t_rup)

    def test_t_rupture_requires_step(self):
        ref = RETAReferential(Y_max=10.0)
        with pytest.raises(RuntimeError):
            ref.t_rupture()

    def test_command_opposes_positive_error(self):
        """
        u(t) = Kp·e + Ki·∫e avec Kp, Ki > 0 et e > 0 persistant → u > 0,
        donc y_real = y_open − u est tiré vers le bas (sens de la correction,
        cf. théorie_fondamentale.md §4.4 "contre-force dynamique").
        Note : e(t) est défini sur la trajectoire libre y_open (pas de
        feedback de y_real dans e), fidèle à l'équation §4.1/§4.3 — donc
        u croît sans jamais se stabiliser ici, contrairement à un vrai
        asservissement en boucle fermée sur la sortie régulée.
        """
        np.random.seed(3)
        obs = np.ones(100) * 0.05 + np.random.randn(100) * 0.005
        ref = RETAReferential(Y_max=1000.0, Yc=0.0, Kp0=5.0, Ki0=2.0, adaptive_pi=False)
        history = ref.fit(obs)
        last = history[-1]
        assert last.e > 0
        assert last.u > 0
        assert last.y_real < last.y_open

    def test_adaptive_gains_grow_under_persistent_error(self):
        """Loi gradient : K̇p = γp·ē² >= 0 toujours → Kp ne peut que croître (hors saturation)."""
        ref = RETAReferential(Y_max=1000.0, Yc=0.0, Kp0=1.0, Ki0=0.5, adaptive_pi=True)
        Kp0 = ref.pi.Kp
        ref.fit(np.ones(50) * 0.05)
        assert ref.pi.Kp >= Kp0


# ── Dispersion (RETA-nD) ─────────────────────────────────────────────────

class TestDispersion:
    def test_effective_dimension_isotropic(self):
        cov = np.eye(5)
        assert abs(effective_dimension(cov) - 5.0) < 1e-9

    def test_effective_dimension_anisotropic_less_than_n(self):
        cov = np.diag([10.0, 0.01, 0.01, 0.01])
        n_eff = effective_dimension(cov)
        assert 1.0 <= n_eff < 4.0

    def test_cir_params_feller_violation_raises(self):
        with pytest.raises(ValueError):
            cir_params(n_eff=1.5, D=0.1, Kp=1.0)

    def test_transition_cdf_is_valid_probability(self):
        p = transition_cdf(x=4.0, t=1.0, x0=1.0, n_eff=3.0, D=0.1, Kp=0.0)
        assert 0.0 <= p <= 1.0

    def test_transition_cdf_degenerate_at_t0(self):
        assert transition_cdf(x=5.0, t=0.0, x0=1.0, n_eff=3.0, D=0.1, Kp=0.0) == 1.0
        assert transition_cdf(x=0.5, t=0.0, x0=1.0, n_eff=3.0, D=0.1, Kp=0.0) == 0.0

    def test_first_passage_finite_for_pure_diffusion(self):
        t_rup = first_passage_time(Y_max=5.0, r0=0.5, n_eff=3.0, D=0.5, Kp=0.0)
        assert math.isfinite(t_rup)
        assert t_rup > 0

    def test_first_passage_zero_if_already_past_threshold(self):
        assert first_passage_time(Y_max=1.0, r0=2.0, n_eff=3.0, D=0.5, Kp=0.0) == 0.0

    def test_first_passage_slower_with_regulation(self):
        """Kp > 0 doit repousser (ou infinir) la rupture par rapport à Kp = 0."""
        t_free = first_passage_time(Y_max=5.0, r0=0.5, n_eff=3.0, D=0.3, Kp=0.0)
        t_regulated = first_passage_time(Y_max=5.0, r0=0.5, n_eff=3.0, D=0.3, Kp=0.5)
        assert t_regulated > t_free


# ── RETA-nD end-to-end ────────────────────────────────────────────────────

class TestRETAND:
    def test_step_and_box_rupture(self):
        np.random.seed(4)
        n = 3
        rnd = RETAND(n=n, Y_max_axes=[5.0, 5.0, 8.0])
        T = 40
        obs = np.ones((T, n)) * 0.05 + np.random.randn(T, n) * 0.005
        history = rnd.fit(obs)
        assert len(history) == T
        assert math.isfinite(rnd.t_rupture_box())

    def test_joint_rupture_shorter_than_box_under_isotropic_noise(self):
        """
        Cf. Critique 7 / reta_nd_dispersion.md : sous seuil de norme jointe et
        bruit isotrope, le premier passage Bessel doit être <= min_i(t_rupture_i)
        (biais optimiste du pavé confirmé géométriquement : boule ⊂ pavé).
        """
        np.random.seed(5)
        n = 3
        Y_max_axes = [5.0, 5.0, 5.0]
        rnd = RETAND(n=n, Y_max_axes=Y_max_axes, axis_kwargs=[
            {"adaptive_pi": False, "Kp0": 0.0, "Ki0": 0.0} for _ in range(n)
        ])
        T = 60
        drift = 0.05
        obs = np.ones((T, n)) * drift + np.random.randn(T, n) * 0.01
        rnd.fit(obs)

        t_box = rnd.t_rupture_box()
        t_joint = rnd.t_rupture_joint(Y_max=5.0, Kp=0.0)

        assert math.isfinite(t_box)
        assert math.isfinite(t_joint)
        assert t_joint <= t_box
