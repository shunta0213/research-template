"""実験スクリプトのコマンド群を実行・投入するヘルパー。

experiments/<name>/<name>-add-tasks.py から使う。投入先（backend）は次の 3 つ。

- ``"local"``: その場で直列実行する
- ``"pueue"``: 手元のマシンの pueue に 1 コマンド 1 タスクで投入する
- ``"cjob"``: クラスタのジョブキュー cjob に投入する
  （https://github.com/Shu-Tanaka-Group/research-cluster-job-system）

cjob では，複数のコマンド（pueue なら複数のタスクになるもの）を 1 つの cjob タスクにまとめる。
タスクの一覧をタスクファイル（``data/tasks/<group>-<日時>-<id>.json``）に書き出してから
``cjob sweep -n <タスク数> -- python -m src.task_runner <タスクファイル> _INDEX_`` として投入し，
各タスクはまとめたコマンドを workers 個ずつ並列に実行する（タスク内の小さな pueue）。
sweep は何件のタスクを含んでも cjob のジョブ数上限（投入 500 件）に対して 1 件としか数えられない。
"""

import json
import math
import subprocess
import sys
import time
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from src.runs import DATA_ROOT, REPO_ROOT

TASKS_ROOT = DATA_ROOT / "tasks"

Backend = Literal["local", "pueue", "cjob"]


@dataclass(frozen=True)
class CjobConfig:
    """cjob への投入設定（値の決め方は docs/setup.md「cjob」）。

    cpu・memory・gpu は 1 タスクあたりの量。1 タスクは workers 個のコマンドを同時に実行するので，
    memory は「1 コマンドのメモリ × workers」を目安にする。各コマンドのスレッド数は cpu // workers。
    """

    cpu: int = 1
    memory: str = "1Gi"
    commands_per_task: int = 1  # 1 つの cjob タスクにまとめるコマンド数（の上限）
    workers: int = 1  # タスク内で同時に実行するコマンド数
    parallel: int = 10  # 同時に実行するタスク数（cjob sweep --parallel）
    time_limit: str = "1d"  # sweep 全体（全タスクが終わるまで）の上限。秒数か "6h"・"1d" などの表記
    flavor: str | None = None  # None のとき cjob のデフォルト（`cjob flavor list` で確認）
    gpu: int = 0
    max_tasks_per_job: int | None = None  # 1 つの sweep に入れるタスク数の上限（time_limit に収まるよう分割）

    @property
    def threads(self) -> int:
        return max(1, self.cpu // self.workers)


def submit_commands(
    commands: Sequence[Sequence[str]],
    backend: Backend,
    group: str,
    parallel: int,
    dry_run: bool,
    cjob: CjobConfig | None = None,
) -> None:
    """commands を backend で実行・投入する。dry_run=True のときは実行せず内容を表示するだけ。

    group は pueue のグループ名・cjob のタスクファイル名に使う。parallel は pueue の同時実行数
    （cjob の同時実行タスク数は cjob.parallel）。
    """
    if not commands:
        print("nothing to submit")
        return
    if backend == "local":
        _run_local(commands, dry_run)
    elif backend == "pueue":
        _submit_pueue(commands, group, parallel, dry_run)
    elif backend == "cjob":
        _submit_cjob(commands, group, cjob or CjobConfig(), dry_run)
    else:
        raise ValueError(f"unknown backend: {backend!r}")


def _print_dry_run(commands: Sequence[Sequence[str]], backend: str) -> None:
    for command in commands:
        print(" ".join(command))
    print(f"[dry-run] {len(commands)} command(s) via {backend}")


def _run_local(commands: Sequence[Sequence[str]], dry_run: bool) -> None:
    if dry_run:
        _print_dry_run(commands, "local")
        return
    for i, command in enumerate(commands, start=1):
        print(f"[{i}/{len(commands)}] {' '.join(command)}")
        subprocess.run(command, cwd=REPO_ROOT, check=True)


# --- pueue ---


def setup_pueue_group(group: str, parallel: int) -> None:
    """pueue のグループを（無ければ）作り，並列実行数を設定する。"""
    existing = json.loads(
        subprocess.run(["pueue", "group", "--json"], capture_output=True, text=True, check=True).stdout
    )
    if group not in existing:
        subprocess.run(["pueue", "group", "add", group], check=True)
    subprocess.run(["pueue", "parallel", str(parallel), "--group", group], check=True)


def _submit_pueue(commands: Sequence[Sequence[str]], group: str, parallel: int, dry_run: bool) -> None:
    if dry_run:
        _print_dry_run(commands, f"pueue (group={group!r}, parallel={parallel})")
        return
    setup_pueue_group(group, parallel)
    for command in commands:
        subprocess.run(
            ["pueue", "add", "--group", group, "--working-directory", str(REPO_ROOT), "--", *command],
            check=True,
            stdout=subprocess.DEVNULL,
        )
    print(f"[pueue] enqueued {len(commands)} command(s) to group {group!r} (parallel={parallel})")


# --- cjob ---


def group_commands(commands: Sequence[Sequence[str]], commands_per_task: int) -> list[list[Sequence[str]]]:
    """commands を 1 タスク commands_per_task 個以下にまとめる。

    グリッド順に区切ると重いパラメータ点が同じタスクに偏るので，飛び飛びに配る
    （タスク i にコマンド i, i + n_tasks, i + 2 n_tasks, ...）。
    """
    n_tasks = math.ceil(len(commands) / commands_per_task)
    return [list(commands[i::n_tasks]) for i in range(n_tasks)]


def new_task_file_path(group: str) -> Path:
    return TASKS_ROOT / f"{group}-{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}.json"


def write_task_file(path: Path, tasks: Sequence[Sequence[Sequence[str]]]) -> None:
    """tasks（タスクごとのコマンドのリスト）をタスクファイルに書き出す。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([[list(command) for command in task] for task in tasks], indent=1))


def build_cjob_sweep_commands(task_file: Path, n_tasks: int, config: CjobConfig) -> list[list[str]]:
    """task_file の n_tasks 個のタスクを実行する cjob sweep コマンド（max_tasks_per_job ごとに分割）。"""
    chunk_size = config.max_tasks_per_job or n_tasks
    sweeps = []
    for offset in range(0, n_tasks, chunk_size):
        n = min(chunk_size, n_tasks - offset)
        sweep = ["cjob", "sweep", "-n", str(n), "--parallel", str(min(config.parallel, n))]
        sweep += ["--cpu", str(config.cpu), "--memory", config.memory, "--time-limit", config.time_limit]
        if config.flavor is not None:
            sweep += ["--flavor", config.flavor]
        if config.gpu:
            sweep += ["--gpu", str(config.gpu)]
        sweep += ["--", sys.executable, "-m", "src.task_runner", str(task_file), "_INDEX_", "--offset", str(offset)]
        sweep += ["--workers", str(config.workers), "--threads", str(config.threads)]
        sweeps.append(sweep)
    return sweeps


def _submit_cjob(commands: Sequence[Sequence[str]], group: str, config: CjobConfig, dry_run: bool) -> None:
    tasks = group_commands(commands, config.commands_per_task)
    task_file = new_task_file_path(group)
    sweeps = build_cjob_sweep_commands(task_file, len(tasks), config)

    print(
        f"[cjob] {len(commands)} command(s) -> {len(tasks)} task(s) of <= {config.commands_per_task} command(s) "
        f"(cpu={config.cpu}, workers={config.workers}, threads={config.threads}) in {len(sweeps)} sweep job(s)"
    )
    if dry_run:
        print(f"[dry-run] would write {task_file} and submit:")
        for sweep in sweeps:
            print("  " + " ".join(sweep))
        return
    write_task_file(task_file, tasks)
    for sweep in sweeps:
        subprocess.run(sweep, cwd=REPO_ROOT, check=True)
    print(f"[cjob] submitted; task file: {task_file}")
