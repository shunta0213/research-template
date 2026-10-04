"""モンテカルロ法による π の推定（1 回の実行 = 1 パラメータ点）

結果は data/runs/mc-pi/<hash>/{input,output}.npz に保存する（docs/experiments-io.md 参照）。
"""

import argparse
import time

import numpy as np
from mc_pi_taskio import STORE

from src.mc import count_inside_circle, estimate_pi, sample_points, standard_error


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="モンテカルロ法による π の推定")
    parser.add_argument("--n-samples", type=int, required=True, help="サンプル点の数")
    parser.add_argument("--seed", type=int, required=True, help="乱数シード")
    parser.add_argument("--overwrite", action="store_true", help="完了済みのランも計算し直す")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    params = STORE.build_params(n_samples=args.n_samples, seed=args.seed)
    if STORE.is_done(params) and not args.overwrite:
        print(f"skip (done): {STORE.run_dir(params)}")
        return

    STORE.save_input(params)

    start = time.perf_counter()
    rng = np.random.default_rng(params["seed"])
    n_inside = count_inside_circle(sample_points(params["n_samples"], rng))
    pi_hat = estimate_pi(n_inside, params["n_samples"])
    elapsed_sec = time.perf_counter() - start

    run_dir = STORE.save_output(
        params,
        n_inside=n_inside,
        pi_hat=pi_hat,
        std_error=standard_error(pi_hat, params["n_samples"]),
        elapsed_sec=elapsed_sec,
    )
    print(f"pi_hat={pi_hat:.6f} ({elapsed_sec:.3f} s) -> {run_dir}")


if __name__ == "__main__":
    main()
