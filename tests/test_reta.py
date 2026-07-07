"""Tests unitaires pour les modules RETA."""

import numpy as np
from reta.kalman import Kalman1D, KalmanAdaptive
from reta.core import RETAReferential
from reta.detector import PhaseDetector
from reta.pi import PIRegulator
from reta.fusion import fusion, navigate, ligne_possibilites


# ── Kalman ──────────────────────────────────────────────────────────────

class TestKalman1D:
    def test_batch_shape(self):
        n = 100
        k = Kalman1D()
        z, p = k.batch(np.random.randn(n))
        assert len(z) == n
        assert len(p) == n

    def test_reset_reuse(self):
        k = Kalman1D()
        z1, _ = k.batch(np.random.randn(50))
        z2, _ = k.batch(np.random.randn(50))
        assert len(z1) == 50
        assert len(z2) == 50

    def test_rolling_mean_o1(self):
        x = np.arange(10, dtype=float)
        m = Kalman1D.rolling_mean(x, window=3)
        assert len(m) == 10
        assert m[0] == 0.0
        assert abs(m[-1] - 8.0) < 1e-9


class TestKalmanAdaptive:
    def test_adaptation(self):
        k = KalmanAdaptive(alpha=0.97, beta=0.95)
        k.batch(np.random.randn(100))
        assert k.R_current > 0
        assert k.Q_current > 0
        assert 0 <= k.signal_quality <= 1

    def test_convergent_signal(self):
        k = KalmanAdaptive()
        signal = np.ones(200) * 0.01 + np.random.randn(200) * 0.001
        z, _ = k.batch(signal)
        assert abs(k.z - 0.01) < 0.02

    def test_properties(self):
        k = KalmanAdaptive()
        k.batch(np.random.randn(50))
        assert isinstance(k.z, float)
        assert isinstance(k.dz, float)


# ── Core ────────────────────────────────────────────────────────────────

class TestRETAReferential:
    def test_fit_price(self):
        np.random.seed(0)
        price = 100 + np.cumsum(np.random.randn(200) * 0.5)
        ref = RETAReferential().fit(price)
        assert ref.n == 200
        assert ref.phase in ("BULL", "BEAR", "NEUTRE")
        assert ref.t_rup > 0

    def test_fit_logret(self):
        logret = np.random.randn(100) * 0.01
        ref = RETAReferential().fit(logret, is_price=False)
        assert ref.n == 100

    def test_encode_decode(self):
        np.random.seed(1)
        price = 100 + np.cumsum(np.random.randn(150))
        ref = RETAReferential().fit(price)
        payload = ref.encode()
        restored = RETAReferential.from_encoded(payload)
        assert abs(restored.z_last - ref.z_last) < 1e-8
        assert restored.phase == ref.phase
        assert abs(restored.t_rup - ref.t_rup) < 0.01  # arrondi à 2 décimales

    def test_predict(self):
        ref = RETAReferential().fit(100 + np.cumsum(np.random.randn(100)))
        fut = ref.predict(steps=24)
        assert len(fut) == 24
        assert np.all(fut > 0)

    def test_add_operator(self):
        ref_a = RETAReferential().fit(100 + np.cumsum(np.random.randn(100)))
        ref_b = RETAReferential().fit(np.ones(100))
        fused = ref_a + ref_b
        assert isinstance(fused, RETAReferential)

    def test_version_selection(self):
        ref_v1 = RETAReferential(version="v1.1").fit(np.ones(100))
        ref_v3 = RETAReferential(version="v1.3").fit(np.ones(100))
        assert ref_v1.n == 100
        assert ref_v3.n == 100


# ── Detector ────────────────────────────────────────────────────────────

class TestPhaseDetector:
    def test_bull_detection(self):
        d = PhaseDetector(eps=0.001, t_confirm=3)
        phases = d.batch(np.ones(20) * 0.005)
        assert phases[-1] == "BULL"

    def test_bear_detection(self):
        d = PhaseDetector(eps=0.001, t_confirm=3)
        phases = d.batch(np.ones(20) * -0.005)
        assert phases[-1] == "BEAR"

    def test_neutral_noise(self):
        d = PhaseDetector(eps=0.01, t_confirm=3)
        phases = d.batch(np.random.randn(50) * 0.001)
        assert phases[-1] == "NEUTRE"

    def test_no_false_positive(self):
        d = PhaseDetector(eps=0.01, t_confirm=5)
        phases = d.batch([0.02] * 3 + [-0.02] * 10)
        assert phases[-1] == "BEAR"  # BULL non confirmé → NEUTRE, puis BEAR confirmé


# ── PI ──────────────────────────────────────────────────────────────────

class TestPIRegulator:
    def test_fixed_gains(self):
        pi = PIRegulator(kp=0.1, ki=0.01)
        u = pi.batch(np.ones(50) * 0.5)
        assert len(u) == 50
        assert abs(u[-1]) > 0

    def test_adaptive_gradient(self):
        pi = PIRegulator(adaptive=True, gamma_p=0.5, gamma_i=0.2)
        pi.batch(np.ones(100) * 0.5)
        assert pi.kp > 0.12  # doit avoir augmenté
        assert pi.ki > 0.002

    def test_reset(self):
        pi = PIRegulator()
        pi.batch(np.ones(50))
        assert pi._integral != 0
        pi.reset()
        assert pi._integral == 0.0

    def test_properties(self):
        pi = PIRegulator(kp=0.5, ki=0.01)
        assert pi.t_stable > 0
        assert pi.residual_band > 0
        assert any(r in pi.regime for r in ("sous-amorti", "critique", "sur-amorti"))


# ── Fusion ──────────────────────────────────────────────────────────────

class TestFusion:
    def test_fusion_identity(self):
        ref = RETAReferential().fit(np.ones(200) * 0.01)
        fused = fusion(ref, ref, alpha=0.5)
        assert fused.z_last == ref.z_last

    def test_fusion_bounds(self):
        ref_a = RETAReferential().fit(np.ones(100) * 0.01)
        ref_b = RETAReferential().fit(np.ones(100) * 0.02)
        fused = fusion(ref_a, ref_b, alpha=1)
        assert abs(fused.z_last - ref_a.z_last) < 1e-10
        fused0 = fusion(ref_a, ref_b, alpha=0)
        assert abs(fused0.z_last - ref_b.z_last) < 1e-10

    def test_fusion_invalid_alpha(self):
        ref = RETAReferential().fit(np.ones(100))
        try:
            fusion(ref, ref, alpha=1.5)
            assert False
        except ValueError:
            pass

    def test_navigate(self):
        ref_a = RETAReferential().fit(np.zeros(50))
        ref_b = RETAReferential().fit(np.ones(50) * 0.01)
        diff = navigate(ref_a, ref_b)
        assert len(diff) > 0

    def test_ligne_possibilites(self):
        ref_a = RETAReferential().fit(np.ones(100) * 0.01)
        ref_b = RETAReferential().fit(np.ones(100) * 0.02)
        ligne = ligne_possibilites(ref_a, ref_b, n=10)
        assert len(ligne) == 10
