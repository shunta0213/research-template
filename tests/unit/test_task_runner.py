import json
import subprocess
import sys

from src.tasks import write_task_file

WRITE_THREADS = "import os, sys; open(sys.argv[1], 'w').write(os.environ['OMP_NUM_THREADS'])"


def write_threads(path):
    return [sys.executable, "-c", WRITE_THREADS, str(path)]


def run_task_runner(task_file, *args):
    command = [sys.executable, "-m", "src.task_runner", str(task_file), *args]
    return subprocess.run(command, capture_output=True, text=True, check=False)


def test_runs_all_commands_of_offset_plus_index_task(tmp_path):
    outs = [tmp_path / f"out{i}.txt" for i in range(3)]
    tasks = [[["false"]], [["false"]], [write_threads(out) for out in outs]]
    task_file = tmp_path / "tasks.json"
    write_task_file(task_file, tasks)
    assert json.loads(task_file.read_text()) == tasks

    result = run_task_runner(task_file, "1", "--offset", "1", "--workers", "2", "--threads", "3")
    assert result.returncode == 0
    assert [out.read_text() for out in outs] == ["3", "3", "3"]
    assert "3 ok, 0 failed" in result.stdout


def test_failure_does_not_stop_other_commands(tmp_path):
    out = tmp_path / "out.txt"
    task_file = tmp_path / "tasks.json"
    write_task_file(task_file, [[[sys.executable, "-c", "raise SystemExit(7)"], write_threads(out)]])

    result = run_task_runner(task_file, "0", "--threads", "1")
    assert result.returncode == 1
    assert out.read_text() == "1"
    assert "1 ok, 1 failed" in result.stdout
