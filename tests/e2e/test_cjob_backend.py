"""backend="cjob" での投入を，cjob sweep をその場で直列実行する偽の cjob コマンドで通しで検査する。

例題（mc-pi）に依存しないよう，各コマンドはファイルを 1 つ書くだけの Python にしている。
"""

import json
import os
import stat
import sys

import src.tasks
from src.tasks import CjobConfig, submit_commands

FAKE_CJOB = """#!/usr/bin/env bash
# cjob sweep -n N [options] -- command... を，_INDEX_ を 0..N-1 に置き換えて直列実行する
echo "$*" >> "$FAKE_CJOB_LOG"
[[ "$1" == "sweep" ]] || exit 2
shift
while [[ "$1" != "--" ]]; do
  if [[ "$1" == "-n" ]]; then n="$2"; fi
  shift
done
shift
for ((i = 0; i < n; i++)); do
  "${@//_INDEX_/$i}" || exit $?
done
"""

WRITE_THREADS = "import os, sys; open(sys.argv[1], 'w').write(os.environ['OMP_NUM_THREADS'])"


def test_cjob_backend_runs_all_commands(tmp_path, monkeypatch):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake = bin_dir / "cjob"
    fake.write_text(FAKE_CJOB)
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    log = tmp_path / "cjob.log"

    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("FAKE_CJOB_LOG", str(log))
    monkeypatch.setattr(src.tasks, "TASKS_ROOT", tmp_path / "tasks")

    outs = [tmp_path / f"out{i}.txt" for i in range(5)]
    commands = [[sys.executable, "-c", WRITE_THREADS, str(out)] for out in outs]
    # 1 タスク 4 コマンドまで → 5 コマンドは 2 タスク（3 + 2）。1 sweep 1 タスクに分割して 2 回投入
    config = CjobConfig(cpu=2, commands_per_task=4, workers=2, max_tasks_per_job=1)
    submit_commands(commands, backend="cjob", group="test", parallel=1, dry_run=False, cjob=config)

    invocations = log.read_text().splitlines()
    assert len(invocations) == 2
    assert all("--cpu 2" in line and "--workers 2 --threads 1" in line for line in invocations)
    (task_file,) = (tmp_path / "tasks").glob("test-*.json")
    assert [len(task) for task in json.loads(task_file.read_text())] == [3, 2]
    assert [out.read_text() for out in outs] == ["1"] * 5
