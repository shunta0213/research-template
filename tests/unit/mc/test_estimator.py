import numpy as np
import pytest

from src.mc import count_inside_circle, estimate_pi, sample_points, standard_error


def test_sample_points_shape_range_and_reproducibility():
    points = sample_points(1000, np.random.default_rng(0))
    assert points.shape == (1000, 2)
    assert points.min() >= 0.0 and points.max() < 1.0
    np.testing.assert_array_equal(points, sample_points(1000, np.random.default_rng(0)))


def test_count_inside_circle():
    points = np.array([[0.0, 0.0], [0.5, 0.5], [1.0, 0.0], [0.9, 0.9]])
    assert count_inside_circle(points) == 2  # 境界上の (1, 0) は含めない


def test_estimate_pi():
    assert estimate_pi(785, 1000) == pytest.approx(3.14)


def test_standard_error():
    assert standard_error(2.0, 100) == pytest.approx(4.0 * np.sqrt(0.25 / 100))
    assert standard_error(4.0, 100) == 0.0
