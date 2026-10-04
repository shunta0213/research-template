"""experiments/mc-pi/mc-pi.py を実際に実行し，保存されたデータを検査する。

DATA_ROOT を一時ディレクトリに向けるので，リポジトリの data/ には書き込まない。
"""

import os
import subprocess
import sys

import numpy as np

from src.runs import REPO_ROOT, RunStore, load_run

SCRIPT = REPO_ROOT / "experiments" / "mc-pi" / "mc-pi.py"


def run_script(data_root, *args):
    env = {**os.environ, "DATA_ROOT": str(data_root)}
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], env=env, capture_output=True, text=True, check=True
    ).stdout


def test_mc_pi_saves_run_and_skips_when_done(tmp_path):
    store = RunStore(experiment="mc-pi", param_types={"n_samples": int, "seed": int}, root=tmp_path / "runs")
    params = store.build_params(n_samples=100_000, seed=0)

    run_script(tmp_path, "--n-samples", "100000", "--seed", "0")
    row = load_run(store.run_dir(params))
    assert row is not None
    assert row["n_samples"] == 100_000 and row["seed"] == 0
    assert abs(row["pi_hat"] - np.pi) < 5 * row["std_error"]

    assert "skip (done)" in run_script(tmp_path, "--n-samples", "100000", "--seed", "0")
