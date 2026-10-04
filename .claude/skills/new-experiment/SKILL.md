---
name: new-experiment
description: 新しい実験を追加する（src/ の問題ロジックとテスト，experiments/<name>/ の 3 ファイル，analysis/<name>/ のノートブック，docs/experiments-io.md）。「実験を追加」「新しい実験」「〜を計算するパイプラインを作りたい」と言われたときに使う。
---

# 新しい実験を追加する

`experiments/mc-pi/` を手本に，1 実験 1 フォルダの構成で新しい実験を追加する。
規約の詳細は `docs/development.md`「新しい実験を追加する」と `AGENTS.md`。

## 1. 決めることをユーザーに確認する

書き始める前に，次がはっきりしていなければユーザーに聞く（推測で決めない）。

- 実験名 `<name>`（英小文字とハイフン。例: `qa-gbp`）。既存の `experiments/` と重複しないこと
- **ハッシュ対象のパラメータ**（結果に影響するもの）と型 → `RunStore.param_types`
- **記録用の値**（結果に影響しないもの: 許容誤差，出力の刻み数など）→ `save_input(params, ...)` の `extra`
- 保存する出力（`output.npz` のキー）
- 計算ロジックを置く `src/<pkg>/`（既存のパッケージに足すか，新しく作るか）

既存の実験に結果に影響するパラメータを足したいだけなら，その実験を変えずに `<name>-v2` を作る（`docs/decisions.md` に理由）。

## 2. 問題ロジックとテスト

- `src/<pkg>/<module>.py` に計算ロジックを書く。関数は単一の責務，戻り値は最小限，
  ライブラリ依存の関数には `_qutip` などのサフィックス（`AGENTS.md`「コーディング規約」）
- `src/<pkg>/__init__.py` で公開する関数を並べる
- `tests/unit/<pkg>/test_<module>.py`（と `__init__.py`）を同じ階層に作る。小さな入力で厳密に分かる値・
  性質（対称性・保存量・境界）を確かめる

## 3. experiments/<name>/ の 3 ファイル

`experiments/mc-pi/` の 3 ファイルをコピーし，ファイル名・中身を置き換える。

- `<name_snake>_taskio.py`: `STORE = RunStore(experiment="<name>", param_types={...})`
- `<name>.py`: argparse（ハッシュ対象 + 記録用）→ `STORE.build_params(...)` → `STORE.is_done` ならスキップ →
  `STORE.save_input(params, **記録用)` → 計算（`src/` の関数を呼ぶだけ）→ `STORE.save_output(params, ...)`。
  `elapsed_sec` も保存する
- `<name>-add-tasks.py`: パラメータグリッドの定数，`build_command`，`BACKEND = "local"`，`DRY_RUN = True`，
  `CJOB = CjobConfig(...)`。`GROUP` は `<name>`
- docstring の説明・`data/runs/<name>/` などの名前を残さず置き換える（`mc-pi` が残っていないか grep で確認）

## 4. ドキュメントと解析

- `docs/experiments-io.md` に `## <name>` の節を追加する（ハッシュ対象は太字，input/output のキーの表）
- `analysis/<name>/<name>-analysis.ipynb` を作る（`analysis/mc-pi/` を手本に，
  `load_runs_cached(RUNS_ROOT / "<name>", load_run, REPO_ROOT / "cache" / "<name>.npz", refresh="new")`）。
  図は `analysis/<name>/figs/`

## 5. 確認する

```bash
uv run pytest
uv run ruff check . && uv run ruff format --check .
DATA_ROOT=$(mktemp -d) uv run python experiments/<name>/<name>.py <小さいパラメータ>   # 1 点だけ。data/ を汚さない
uv run python experiments/<name>/<name>-add-tasks.py                                   # DRY_RUN = True のままで件数を確認
```

- 1 点の実行で `output.npz` ができること，2 回目は `skip (done)` になることを確かめる
- **`DRY_RUN = False` での実行（本番のスイープ・pueue・cjob への投入）はしない**。ユーザーに件数と投入先を伝えて任せる

## 6. 報告する

追加したファイル，ハッシュ対象のパラメータ，dry run での件数，ユーザーが次にやること（グリッドの確認・投入）を伝える。
