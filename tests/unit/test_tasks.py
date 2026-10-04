import sys

import pytest

import src.tasks
from src.tasks import CjobConfig, build_cjob_sweep_commands, group_commands, submit_commands


def test_group_commands_interleaves_and_respects_limit():
    commands = [[str(i)] for i in range(5)]
    tasks = group_commands(commands, commands_per_task=4)
    assert tasks == [[["0"], ["2"], ["4"]], [["1"], ["3"]]]  # 2 タスクに飛び飛びに配る（4 + 1 にしない）
    assert group_commands(commands, commands_per_task=1) == [[c] for c in commands]
    assert group_commands(commands, commands_per_task=10) == [commands]


def test_cjob_sweep_single_job(tmp_path):
    task_file = tmp_path / "tasks.json"
    config = CjobConfig(cpu=8, memory="16Gi", workers=4, parallel=10, time_limit="6h")
    (sweep,) = build_cjob_sweep_commands(task_file, 5, config)
    assert sweep[:6] == ["cjob", "sweep", "-n", "5", "--parallel", "5"]  # parallel はタスク数で頭打ち
    assert sweep[sweep.index("--cpu") + 1] == "8"
    assert sweep[sweep.index("--memory") + 1] == "16Gi"
    assert sweep[sweep.index("--time-limit") + 1] == "6h"
    assert "--flavor" not in sweep and "--gpu" not in sweep

    command = sweep[sweep.index("--") + 1 :]
    assert command == [
        sys.executable, "-m", "src.task_runner", str(task_file), "_INDEX_",
        "--offset", "0", "--workers", "4", "--threads", "2",
    ]  # fmt: skip


def test_cjob_sweep_split_by_max_tasks_per_job(tmp_path):
    sweeps = build_cjob_sweep_commands(tmp_path / "tasks.json", 5, CjobConfig(max_tasks_per_job=2))
    assert [s[s.index("-n") + 1] for s in sweeps] == ["2", "2", "1"]
    assert [s[s.index("--offset") + 1] for s in sweeps] == ["0", "2", "4"]


def test_cjob_sweep_optional_flags(tmp_path):
    config = CjobConfig(cpu=2, flavor="gpu", gpu=1)
    (sweep,) = build_cjob_sweep_commands(tmp_path / "tasks.json", 3, config)
    assert sweep[sweep.index("--flavor") + 1] == "gpu"
    assert sweep[sweep.index("--gpu") + 1] == "1"


def test_cjob_dry_run_writes_nothing(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(src.tasks, "TASKS_ROOT", tmp_path / "tasks")
    commands = [["echo", str(i)] for i in range(6)]
    submit_commands(commands, backend="cjob", group="g", parallel=1, dry_run=True, cjob=CjobConfig(commands_per_task=4))
    assert not (tmp_path / "tasks").exists()
    out = capsys.readouterr().out
    assert "6 command(s) -> 2 task(s)" in out
    assert "cjob sweep -n 2" in out


def test_submit_nothing(capsys):
    submit_commands([], backend="cjob", group="g", parallel=1, dry_run=False)
    assert "nothing to submit" in capsys.readouterr().out


def test_unknown_backend():
    with pytest.raises(ValueError, match="unknown backend"):
        submit_commands([["echo"]], backend="slurm", group="g", parallel=1, dry_run=True)
