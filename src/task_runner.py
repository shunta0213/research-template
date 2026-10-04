"""cjob sweep の 1 タスクとして実行され，タスクファイルの (offset + index) 番目のタスクを実行する。

src/tasks.py が作る cjob sweep コマンドから呼ばれる（直接使うことはない）::

    cjob sweep -n 10 -- python -m src.task_runner data/tasks/<file>.json _INDEX_ --offset 0 --workers 8 --threads 1

1 タスクは複数のコマンドからなり，それらを workers 個ずつ並列に実行する（タスク内の小さな pueue）。
各コマンドの BLAS/OpenMP 系のスレッド数は --threads に揃える。失敗したコマンドがあっても残りは実行し，
最後に 1 つでも失敗していれば終了コード 1 で終わる（失敗分は add-tasks の再実行で投入し直せる）。
"""

import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

THREAD_ENV_VARS = ["OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMBA_NUM_THREADS"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="タスクファイルの 1 タスク（複数のコマンド）を実行する")
    parser.add_argument("task_file", type=Path, help="タスク（コマンド = argv のリスト のリスト）の JSON 配列")
    parser.add_argument("index", type=int, help="cjob sweep の _INDEX_")
    parser.add_argument("--offset", type=int, default=0, help="index に足す値（sweep を分割したとき用）")
    parser.add_argument("--workers", type=int, default=1, help="同時に実行するコマンド数")
    parser.add_argument("--threads", type=int, default=None, help="各コマンドの BLAS/OpenMP 系のスレッド数")
    return parser.parse_args()


def run_command(label: str, command: list[str], env: dict[str, str]) -> int:
    print(f"[{label}] start: {' '.join(command)}", flush=True)
    start = time.perf_counter()
    returncode = subprocess.run(command, env=env, check=False).returncode
    print(f"[{label}] exit={returncode} ({time.perf_counter() - start:.1f} s)", flush=True)
    return returncode


def main() -> None:
    args = parse_args()
    tasks = json.loads(args.task_file.read_text())
    task_index = args.offset + args.index
    commands = tasks[task_index]

    env = dict(os.environ)
    if args.threads is not None:
        env.update({name: str(args.threads) for name in THREAD_ENV_VARS})

    print(
        f"[task {task_index}/{len(tasks)}] {len(commands)} command(s), workers={args.workers}, threads={args.threads}",
        flush=True,
    )
    start = time.perf_counter()
    labels = [f"{task_index}.{i}" for i in range(len(commands))]
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        returncodes = list(executor.map(run_command, labels, commands, [env] * len(commands)))

    n_failed = sum(code != 0 for code in returncodes)
    print(
        f"[task {task_index}] done: {len(commands) - n_failed} ok, {n_failed} failed "
        f"({(time.perf_counter() - start) / 3600:.2f} h)",
        flush=True,
    )
    sys.exit(1 if n_failed else 0)


if __name__ == "__main__":
    main()
