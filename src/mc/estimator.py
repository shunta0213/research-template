"""モンテカルロ法による π の推定（テンプレートの例題。実際の研究の問題ロジックに置き換える）。

単位正方形 [0, 1)^2 に一様に点を打ち，四分円 x^2 + y^2 < 1 に入る割合 p から π ≈ 4p とする。
"""

import numpy as np


def sample_points(n_samples: int, rng: np.random.Generator) -> np.ndarray:
    """単位正方形内の一様乱数点。shape (n_samples, 2)。"""
    return rng.random((n_samples, 2))


def count_inside_circle(points: np.ndarray) -> int:
    """原点中心・半径 1 の円の内側にある点の数。"""
    return int(np.count_nonzero(np.sum(points**2, axis=1) < 1.0))


def estimate_pi(n_inside: int, n_samples: int) -> float:
    return 4.0 * n_inside / n_samples


def standard_error(pi_hat: float, n_samples: int) -> float:
    """推定値 pi_hat の標準誤差 4 sqrt(p (1 - p) / n)（p = pi_hat / 4）。"""
    p = pi_hat / 4.0
    return 4.0 * float(np.sqrt(p * (1.0 - p) / n_samples))
