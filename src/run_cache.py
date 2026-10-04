"""analysis 用ノートブックで，run ディレクトリ（input.npz / output.npz）を集計した
DataFrame を 1 つの .npz ファイルにキャッシュするためのヘルパー。

キャッシュは自動では更新しない。`refresh` 引数で更新のタイミングを明示的に指定する。

- ``refresh=False``: キャッシュがあればそれを使う（無ければ全 run を読み込んで作成）
- ``refresh="new"``: キャッシュに無い run ディレクトリだけを読み込んで追記する
- ``refresh=True``: 全 run を読み直してキャッシュを作り直す
"""

import os
import pickle
import time
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any, Literal

import numpy as np
import pandas as pd

_COLUMN_PREFIX = "col:"


def _scan_run_dirs(data_dir: Path) -> list[Path]:
    return sorted(Path(e.path) for e in os.scandir(data_dir) if e.is_dir())


def _load_rows(run_dirs: list[Path], loader: Callable[[Path], dict | None]) -> tuple[list[dict], list[str]]:
    """loader を並列に適用し，(読み込めた行, 読み込めた run ディレクトリ名) を返す。"""
    if not run_dirs:
        return [], []
    with ProcessPoolExecutor(max_workers=min(32, os.cpu_count() or 4)) as executor:
        rows = list(executor.map(loader, run_dirs, chunksize=64))
    loaded = [(row, run_dir.name) for row, run_dir in zip(rows, run_dirs) if row is not None]
    return [row for row, _ in loaded], [name for _, name in loaded]


def _column_to_array(values: pd.Series) -> np.ndarray:
    """DataFrame の列を npz に保存できる配列に変換する。配列・tuple を要素に持つ列は object 配列にする。"""
    items = values.tolist()
    if any(isinstance(v, (np.ndarray, tuple, list)) for v in items):
        arr = np.empty(len(items), dtype=object)
        arr[:] = items
        return arr
    if items and all(isinstance(v, str) for v in items):
        return np.array(items, dtype=str)
    return values.to_numpy()


def _save_cache(cache_path: Path, df: pd.DataFrame, run_dirs: list[str], data_dir: Path) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    arrays = {f"{_COLUMN_PREFIX}{col}": _column_to_array(df[col]) for col in df.columns}
    arrays["__columns__"] = np.array(list(df.columns), dtype=str)
    arrays["__run_dirs__"] = np.array(run_dirs, dtype=str)
    arrays["__data_dir__"] = np.array(str(data_dir.resolve()))
    arrays["__created_at__"] = np.array(time.strftime("%Y-%m-%d %H:%M:%S"))
    # 書き込み途中で中断しても既存のキャッシュが壊れないように，一時ファイル経由で置き換える
    tmp_path = cache_path.with_name(cache_path.name + ".tmp")
    with open(tmp_path, "wb") as f:
        np.savez(f, **arrays)
    tmp_path.replace(cache_path)


def _read_cache(cache_path: Path) -> tuple[pd.DataFrame, list[str], str]:
    with np.load(cache_path, allow_pickle=True) as data:
        columns = data["__columns__"].tolist()
        df = pd.DataFrame({col: data[f"{_COLUMN_PREFIX}{col}"] for col in columns}, columns=columns)
        run_dirs = data["__run_dirs__"].tolist()
        created_at = str(data["__created_at__"])
    return df, run_dirs, created_at


def load_runs_cached(
    data_dir: str | Path,
    loader: Callable[[Path], dict | None],
    cache_path: str | Path,
    refresh: bool | Literal["new"] = False,
) -> pd.DataFrame:
    """data_dir 以下の各 run ディレクトリに loader を適用した DataFrame を，キャッシュ付きで返す。

    loader は run ディレクトリを受け取り 1 行分の dict（読み込めない場合は None）を返す関数。
    並列実行のため pickle 可能（ノートブックでトップレベル定義された関数など）である必要がある。
    """
    data_dir = Path(data_dir)
    cache_path = Path(cache_path)
    all_run_dirs = _scan_run_dirs(data_dir)

    if refresh is True or not cache_path.exists():
        rows, run_dirs = _load_rows(all_run_dirs, loader)
        df = pd.DataFrame(rows)
        _save_cache(cache_path, df, run_dirs, data_dir)
        print(f"[cache] built {cache_path} ({len(run_dirs)} runs)")
        return df

    df, cached_run_dirs, created_at = _read_cache(cache_path)
    cached = set(cached_run_dirs)
    uncached_run_dirs = [d for d in all_run_dirs if d.name not in cached]

    if refresh == "new":
        rows, run_dirs = _load_rows(uncached_run_dirs, loader)
        if rows:
            df = pd.concat([df, pd.DataFrame(rows)], ignore_index=True)
            # 全読み込みと同じく run ディレクトリ名の順に並べ直す
            names = cached_run_dirs + run_dirs
            order = np.argsort(names, kind="stable")
            df = df.iloc[order].reset_index(drop=True)
            _save_cache(cache_path, df, [names[i] for i in order], data_dir)
        print(f"[cache] added {len(run_dirs)} runs to {cache_path} (total {len(cached_run_dirs) + len(run_dirs)} runs)")
        return df

    print(f"[cache] loaded {cache_path} ({len(cached_run_dirs)} runs, created at {created_at})")
    if uncached_run_dirs:
        print(
            f"[cache] {len(uncached_run_dirs)} run dirs in {data_dir} are not cached (new or incomplete); "
            'set refresh="new" to add them'
        )
    return df


def _file_signature(paths: list[Path]) -> list[tuple[str, int, int]]:
    return [(str(p.resolve()), p.stat().st_mtime_ns, p.stat().st_size) for p in paths]


def load_derived_cached(
    cache_path: str | Path,
    build: Callable[[], Any],
    depends_on: list[str | Path],
    refresh: bool = False,
) -> Any:
    """build() の結果（pickle 可能な任意のオブジェクト）を cache_path にキャッシュして返す。

    load_runs_cached のキャッシュから計算した結合・集計結果など，作成に時間がかかる派生データ用。
    depends_on に挙げたファイル（元キャッシュなど）の更新時刻・サイズが保存時と異なれば自動で作り直す。
    ``refresh=True`` なら常に作り直す（build の中身を変えたときなど）。
    """
    cache_path = Path(cache_path)
    signature = _file_signature([Path(p) for p in depends_on])

    if not refresh and cache_path.exists():
        with open(cache_path, "rb") as f:
            cached = pickle.load(f)
        if cached["signature"] == signature:
            print(f"[cache] loaded {cache_path} (created at {cached['created_at']})")
            return cached["value"]
        print(f"[cache] {cache_path} is stale (dependencies changed); rebuilding")

    value = build()
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = cache_path.with_name(cache_path.name + ".tmp")
    with open(tmp_path, "wb") as f:
        pickle.dump(
            {"signature": signature, "created_at": time.strftime("%Y-%m-%d %H:%M:%S"), "value": value},
            f,
            protocol=pickle.HIGHEST_PROTOCOL,
        )
    tmp_path.replace(cache_path)
    print(f"[cache] built {cache_path}")
    return value
