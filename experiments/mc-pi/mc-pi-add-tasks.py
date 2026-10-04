"""mc-pi.py のパラメータグリッドを実行・投入するスクリプト（local / pueue / cjob）

下の定数を編集してから `uv run python experiments/mc-pi/mc-pi-add-tasks.py` で実行する。
DRY_RUN = True のうちはコマンドを表示するだけなので，件数と内容を確認してから False にする。
"""

import itertools
import sys
from pathlib import Path

from mc_pi_taskio import STORE

from src.tasks import CjobConfig, submit_commands

SCRIPT_DIR = Path(__file__).resolve().parent
TARGET_SCRIPT = SCRIPT_DIR / "mc-pi.py"

# --- パラメータグリッド（走査対象） ---
N_SAMPLES = [10**k for k in range(2, 8)]
SEED = list(range(10))

# --- 実行設定 ---
BACKEND = "local"  # "local"（その場で直列実行）/ "pueue"（手元のマシンで並列）/ "cjob"（クラスタ）
GROUP = "mc-pi"  # pueue のグループ名・cjob のタスクファイル名
PARALLEL = 4  # pueue の同時実行数

# cjob: commands_per_task 個のコマンドを 1 つの cjob タスクにまとめ，タスク内で workers 個ずつ並列に実行する
# （値の決め方は docs/setup.md「cjob」）
CJOB = CjobConfig(
    cpu=4,
    memory="4Gi",  # 1 タスクあたり（1 コマンドのメモリ × workers が目安）
    commands_per_task=20,  # 1 タスクが数時間で終わる程度にまとめる
    workers=4,  # 各コマンドのスレッド数 = cpu // workers
    parallel=10,  # 同時に実行するタスク数
    time_limit="6h",  # sweep 全体（全タスクが終わるまで）の上限
)

DRY_RUN = True  # True のとき実行せずコマンドを表示するだけ
SKIP_EXISTING = True  # 完了済みのランをスキップ


def build_command(n_samples: int, seed: int) -> list[str]:
    return [sys.executable, str(TARGET_SCRIPT), "--n-samples", str(n_samples), "--seed", str(seed)]


def main() -> None:
    commands = []
    n_skipped = 0
    for n_samples, seed in itertools.product(N_SAMPLES, SEED):
        if SKIP_EXISTING and STORE.is_done(STORE.build_params(n_samples=n_samples, seed=seed)):
            n_skipped += 1
            continue
        commands.append(build_command(n_samples, seed))

    print(f"{len(commands)} to run, {n_skipped} skipped (done)")
    submit_commands(commands, backend=BACKEND, group=GROUP, parallel=PARALLEL, dry_run=DRY_RUN, cjob=CJOB)


if __name__ == "__main__":
    main()
