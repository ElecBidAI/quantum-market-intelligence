import numpy as np
import pytest

from quant_core.simulation import (
    block_bootstrap_paths,
    gbm_paths,
    iid_bootstrap_paths,
    jump_diffusion_paths,
    regime_conditioned_bootstrap_paths,
    student_t_returns,
)
from quant_core.stats import kurtosis


class TestGbmPaths:
    def test_shape_and_starting_value(self):
        paths = gbm_paths(100, 0.05, 0.2, dt=1 / 252, n_steps=10, n_paths=5, seed=1)
        assert paths.shape == (5, 11)
        assert np.all(paths[:, 0] == 100)

    def test_reproducible_with_same_seed(self):
        a = gbm_paths(100, 0.05, 0.2, dt=1 / 252, n_steps=10, n_paths=5, seed=42)
        b = gbm_paths(100, 0.05, 0.2, dt=1 / 252, n_steps=10, n_paths=5, seed=42)
        assert np.array_equal(a, b)

    def test_different_seeds_differ(self):
        a = gbm_paths(100, 0.05, 0.2, dt=1 / 252, n_steps=10, n_paths=5, seed=1)
        b = gbm_paths(100, 0.05, 0.2, dt=1 / 252, n_steps=10, n_paths=5, seed=2)
        assert not np.array_equal(a, b)

    def test_converges_to_theoretical_drift_and_volatility(self):
        # large n_paths + fixed seed keeps this a deterministic (non-flaky),
        # generously-toleranced check of the exact GBM solution's moments.
        paths = gbm_paths(
            100, mu=0.05, sigma=0.2, dt=1 / 252, n_steps=252, n_paths=20_000, seed=123
        )
        log_returns = np.log(paths[:, -1] / 100)
        assert log_returns.mean() == pytest.approx(0.05 - 0.5 * 0.2**2, abs=0.01)
        assert log_returns.std() == pytest.approx(0.2, abs=0.01)

    def test_rejects_invalid_params(self):
        with pytest.raises(ValueError):
            gbm_paths(0, 0.05, 0.2, dt=1, n_steps=1, n_paths=1)
        with pytest.raises(ValueError):
            gbm_paths(100, 0.05, -0.1, dt=1, n_steps=1, n_paths=1)


class TestJumpDiffusionPaths:
    def test_shape_and_starting_value(self):
        paths = jump_diffusion_paths(
            100, 0.05, 0.2, jump_intensity=1.0, jump_mean=-0.02, jump_std=0.05,
            dt=1 / 252, n_steps=10, n_paths=5, seed=1,
        )
        assert paths.shape == (5, 11)
        assert np.all(paths[:, 0] == 100)

    def test_reproducible_with_same_seed(self):
        kwargs = dict(
            s0=100, mu=0.05, sigma=0.2, jump_intensity=1.0, jump_mean=-0.02, jump_std=0.05,
            dt=1 / 252, n_steps=10, n_paths=5, seed=42,
        )
        assert np.array_equal(jump_diffusion_paths(**kwargs), jump_diffusion_paths(**kwargs))

    def test_zero_intensity_converges_like_pure_gbm(self):
        paths = jump_diffusion_paths(
            100, mu=0.05, sigma=0.2, jump_intensity=0.0, jump_mean=-0.5, jump_std=0.5,
            dt=1 / 252, n_steps=252, n_paths=20_000, seed=123,
        )
        log_returns = np.log(paths[:, -1] / 100)
        assert log_returns.mean() == pytest.approx(0.05 - 0.5 * 0.2**2, abs=0.01)

    def test_negative_jump_mean_pulls_drift_down(self):
        paths = jump_diffusion_paths(
            100, mu=0.05, sigma=0.2, jump_intensity=1.0, jump_mean=-0.05, jump_std=0.1,
            dt=1 / 252, n_steps=252, n_paths=20_000, seed=123,
        )
        log_returns = np.log(paths[:, -1] / 100)
        # expected additional drift from jumps ~= jump_intensity * T * jump_mean = 1*1*(-0.05)
        expected = (0.05 - 0.5 * 0.2**2) + (1.0 * 1.0 * -0.05)
        assert log_returns.mean() == pytest.approx(expected, abs=0.02)


class TestStudentTReturns:
    def test_shape_and_reproducibility(self):
        a = student_t_returns(df=5, loc=0.0, scale=1.0, n=100, seed=1)
        b = student_t_returns(df=5, loc=0.0, scale=1.0, n=100, seed=1)
        assert a.shape == (100,)
        assert np.array_equal(a, b)

    def test_converges_to_theoretical_mean(self):
        sample = student_t_returns(df=5, loc=0.03, scale=1.0, n=50_000, seed=7)
        assert sample.mean() == pytest.approx(0.03, abs=0.02)

    def test_has_fatter_tails_than_normal(self):
        # same sample size and scale; a low-df Student-t must show materially
        # higher excess kurtosis than a normal sample.
        rng_seed = 7
        t_sample = student_t_returns(df=3, loc=0.0, scale=1.0, n=20_000, seed=rng_seed)
        normal_sample = np.random.default_rng(rng_seed).standard_normal(20_000)
        assert kurtosis(t_sample.tolist()) > kurtosis(normal_sample.tolist()) + 1.0

    def test_rejects_invalid_params(self):
        with pytest.raises(ValueError):
            student_t_returns(df=0, loc=0, scale=1, n=10)
        with pytest.raises(ValueError):
            student_t_returns(df=5, loc=0, scale=0, n=10)


class TestIidBootstrapPaths:
    def test_deterministic_small_example(self):
        result = iid_bootstrap_paths([10.0, 20.0, 30.0], path_length=2, n_paths=1, seed=0)
        assert result.tolist() == [[30.0, 20.0]]

    def test_every_value_comes_from_the_original_set(self):
        original = [1.0, 2.0, 3.0, 4.0]
        result = iid_bootstrap_paths(original, path_length=50, n_paths=10, seed=5)
        assert np.all(np.isin(result, original))

    def test_shape(self):
        result = iid_bootstrap_paths([1.0, 2.0, 3.0], path_length=7, n_paths=4, seed=1)
        assert result.shape == (4, 7)

    def test_reproducible_with_same_seed(self):
        a = iid_bootstrap_paths([1.0, 2.0, 3.0], path_length=5, n_paths=3, seed=9)
        b = iid_bootstrap_paths([1.0, 2.0, 3.0], path_length=5, n_paths=3, seed=9)
        assert np.array_equal(a, b)

    def test_rejects_empty_returns(self):
        with pytest.raises(ValueError):
            iid_bootstrap_paths([], path_length=1, n_paths=1)


class TestBlockBootstrapPaths:
    def test_shape(self):
        result = block_bootstrap_paths(
            [1.0, 2.0, 3.0, 4.0, 5.0], block_size=2, path_length=5, n_paths=3, seed=1
        )
        assert result.shape == (3, 5)

    def test_every_block_is_a_real_contiguous_subsequence(self):
        original = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]
        block_size = 3
        result = block_bootstrap_paths(
            original, block_size=block_size, path_length=9, n_paths=20, seed=3
        )
        possible_blocks = [
            tuple(original[i : i + block_size]) for i in range(len(original) - block_size + 1)
        ]
        for row in result:
            for start in range(0, len(row) - block_size + 1, block_size):
                block = tuple(row[start : start + block_size])
                assert block in possible_blocks

    def test_rejects_block_size_larger_than_series(self):
        with pytest.raises(ValueError):
            block_bootstrap_paths([1.0, 2.0], block_size=5, path_length=3, n_paths=1)


class TestRegimeConditionedBootstrapPaths:
    def test_only_draws_from_the_target_regime(self):
        returns = [0.1, 0.2, 0.3, -0.5, -0.6, -0.7]
        labels = ["bull", "bull", "bull", "bear", "bear", "bear"]
        result = regime_conditioned_bootstrap_paths(
            returns, labels, "bull", path_length=20, n_paths=5, seed=1
        )
        assert np.all(result > 0)  # only the positive ("bull") returns should ever appear
        assert np.all(np.isin(result, [0.1, 0.2, 0.3]))

    def test_rejects_regime_with_no_matching_returns(self):
        with pytest.raises(ValueError):
            regime_conditioned_bootstrap_paths(
                [0.1, 0.2], ["bull", "bull"], "bear", path_length=1, n_paths=1
            )

    def test_rejects_mismatched_lengths(self):
        with pytest.raises(ValueError):
            regime_conditioned_bootstrap_paths(
                [0.1, 0.2], ["bull"], "bull", path_length=1, n_paths=1
            )
