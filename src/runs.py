"""実験パラメータと run ディレクトリ（data/runs/<experiment>/<hash>/）を結び付けるユーティリティ。

各実験の taskio モジュール（experiments/<name>/<name>_taskio.py）が ``RunStore`` を 1 つ定義し，
計算本体（<name>.py）とタスク投入（<name>-add-tasks.py）の両方から import する。
同じパラメータからは常に同じハッシュ・同じディレクトリが得られる。

- ハッシュ対象: ``param_types`` に挙げたパラメータ（結果に影響するもの）のみ
- 記録用: ``save_input`` の ``extra`` に渡したもの（input.npz には保存されるがハッシュには影響しない）
- 完了判定: ``output.npz`` の有無（一時ファイル経由で書くため，途中で落ちたランは未完了として残る）

データの置き場所は環境変数 ``DATA_ROOT`` で変更できる（外付けディスク・計算機のスクラッチ領域など）。
"""

from __future__ import annotations

import os
import pickle
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass
from hashlib import blake2b
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = Path(os.environ.get("DATA_ROOT", REPO_ROOT / "data"))
RUNS_ROOT = DATA_ROOT / "runs"

INPUT_FILE = "input.npz"
OUTPUT_FILE = "output.npz"


def params_hash(params: dict[str, Any]) -> str:
    hasher = blake2b(digest_size=16)
    hasher.update(pickle.dumps(params))
    return hasher.hexdigest()


def git_commit() -> str:
    """REPO_ROOT の HEAD のコミットハッシュ。未コミットの変更があれば末尾に "-dirty" を付ける。"""
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return f"{commit}-dirty" if status.strip() else commit


def _savez_atomic(path: Path, **arrays: Any) -> None:
    # 書き込み途中で中断しても壊れたファイルが残らないように，一時ファイル経由で置き換える
    tmp_path = path.with_name(path.name + ".tmp")
    with open(tmp_path, "wb") as f:
        np.savez(f, **arrays)
    tmp_path.replace(path)


def _load_npz(path: Path) -> dict[str, Any]:
    with np.load(path, allow_pickle=False) as data:
        return {key: data[key].item() if data[key].ndim == 0 else data[key] for key in data.files}


def load_run(run_dir: Path) -> dict[str, Any] | None:
    """run ディレクトリの input.npz と output.npz を 1 つの dict にまとめる（未完了なら None）。

    0 次元配列は Python のスカラーに変換する。src.run_cache.load_runs_cached の loader に
    そのまま渡せる（モジュールのトップレベル関数なので並列実行時も pickle できる）。
    """
    output_path = Path(run_dir) / OUTPUT_FILE
    if not output_path.exists():
        return None
    return {"run_dir": Path(run_dir).name, **_load_npz(Path(run_dir) / INPUT_FILE), **_load_npz(output_path)}


@dataclass(frozen=True)
class RunStore:
    """1 つの実験の run ディレクトリ群を扱う。

    param_types はパラメータ名 → 正規化する型。結果に影響するパラメータのみを挙げる
    （ここに挙げた順でハッシュされるため，順序を変えると既存データのハッシュが変わる）。
    """

    experiment: str
    param_types: dict[str, Callable[[Any], Any]]
    root: Path = RUNS_ROOT

    @property
    def data_dir(self) -> Path:
        return self.root / self.experiment

    def build_params(self, **kwargs: Any) -> dict[str, Any]:
        """kwargs から正規化済みのパラメータ dict を作る（キー順は param_types 順で固定）。"""
        missing = [key for key in self.param_types if key not in kwargs]
        unknown = [key for key in kwargs if key not in self.param_types]
        if missing or unknown:
            raise ValueError(f"missing parameter(s): {missing}, unknown parameter(s): {unknown}")
        return {key: caster(kwargs[key]) for key, caster in self.param_types.items()}

    def run_dir(self, params: dict[str, Any]) -> Path:
        return self.data_dir / params_hash(params)

    def is_done(self, params: dict[str, Any]) -> bool:
        return (self.run_dir(params) / OUTPUT_FILE).exists()

    def save_input(self, params: dict[str, Any], **extra: Any) -> Path:
        """パラメータと記録用の値（extra）を input.npz に保存し，run ディレクトリを返す。"""
        run_dir = self.run_dir(params)
        run_dir.mkdir(parents=True, exist_ok=True)
        _savez_atomic(
            run_dir / INPUT_FILE,
            params_hash=params_hash(params),
            git_commit=git_commit(),
            started_at=time.strftime("%Y-%m-%d %H:%M:%S"),
            **params,
            **extra,
        )
        return run_dir

    def save_output(self, params: dict[str, Any], **outputs: Any) -> Path:
        run_dir = self.run_dir(params)
        _savez_atomic(run_dir / OUTPUT_FILE, **outputs)
        return run_dir
