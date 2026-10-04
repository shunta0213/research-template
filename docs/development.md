# 開発ガイド

## プロジェクト構成

```
src/                        共通ロジック（editable install され，どこからでも `from src... import` できる）
  runs.py                   パラメータ ⇄ run ディレクトリ（hash）の対応，input/output の保存・読み込み
  tasks.py                  コマンド群の実行・投入（local / pueue / cjob）
  task_runner.py            cjob sweep の各タスクとして，まとめたコマンドを並列に実行する
  run_cache.py              run ディレクトリ群を集計した DataFrame のキャッシュ
  mc/                       問題ロジックの例（モンテカルロ法による π の推定）
    estimator.py

experiments/                実験パイプライン（1 実験 1 フォルダ）
  mc-pi/
    mc-pi.py                計算本体（CLI。1 回の実行 = 1 パラメータ点）
    mc_pi_taskio.py         パラメータ ⇄ 保存先ディレクトリの対応（RunStore を 1 つ定義）
    mc-pi-add-tasks.py      パラメータスイープの実行・投入（local / pueue / cjob）

analysis/                   集計・可視化（1 実験 1 フォルダ。複数実験の比較は compare/）
  mc-pi/
    mc-pi-analysis.ipynb
    figs/

data/                       実験結果（.gitignore 対象）
  inputs/                   外部から持ってきたデータ・問題インスタンス
  runs/mc-pi/<hash>/{input,output}.npz
  tasks/<group>-<日時>-<id>.json   cjob に投入したタスク（コマンドのまとまり）の一覧

archive/data-<日付>/        data/ の圧縮スナップショット（DVC で Google Drive に保存）
archive/data-<日付>.dvc     ↑ の DVC ポインタ（git 管理）

tests/                      src/ をミラーする
  unit/test_runs.py   ←→    src/runs.py
  unit/test_tasks.py  ←→    src/tasks.py
  unit/test_task_runner.py ←→ src/task_runner.py
  unit/mc/test_estimator.py ←→ src/mc/estimator.py
  e2e/test_mc_pi_pipeline.py   experiments/mc-pi/mc-pi.py を実際に実行して検査
  e2e/test_cjob_backend.py     偽の cjob コマンドで cjob への投入（タスクへのまとめ・並列実行）を通しで検査
```

## 実験のデータ管理

### run ディレクトリ

1 回の実行（1 パラメータ点）の結果は `data/runs/<実験名>/<hash>/` に保存する。

- `<hash>` は「結果に影響するパラメータ」だけから決まる（`RunStore.param_types`）。
  同じパラメータで再実行すると同じディレクトリになるので，スイープを中断・追加しても重複しない。
- `input.npz`: パラメータ＋記録用の値（`params_hash`，`git_commit`，`started_at`，`save_input` の `extra`）
- `output.npz`: 計算結果。一時ファイル経由で書くので，**`output.npz` があれば完了**とみなせる
- `git_commit` には実行時のコミットが入る（未コミットの変更があると `-dirty` が付く）。
  論文に使う結果はコミット済みのコードで計算し直すこと。

各実験のパラメータ・保存キーは `docs/experiments-io.md` にまとめる。

### パラメータを変えるとき

- 結果に影響するパラメータを**追加**する → `param_types` に追加すると全 hash が変わるので，
  実験名を `<name>-v2` にして別フォルダ・別データにする（旧データと混ぜない）。
- 記録用（結果に影響しない）値は `save_input(params, key=value)` の `extra` に渡す。
- 方式を変えた理由は `docs/decisions.md` に残す。

### データの置き場所

環境変数 `DATA_ROOT` を設定すると `data/` の代わりにそこを使う（外付けディスク・計算機のスクラッチ領域）。
cjob で実行するときは，ジョブから見える共有ストレージ（ホームディレクトリなど）を指すこと。

## 実験を実行する（local / pueue / cjob）

`experiments/<name>/<name>-add-tasks.py` の先頭の定数で投入先を選ぶ。完了済みのパラメータ点は
投入前にスキップされ，実験スクリプト自身も完了済みならスキップするので，何度投入し直しても重複しない。

| `BACKEND` | 実行場所 | 単位 |
|---|---|---|
| `"local"` | その場で直列実行 | 1 コマンドずつ |
| `"pueue"` | 手元のマシンの pueue（`PARALLEL` 並列） | 1 コマンド = 1 pueue タスク |
| `"cjob"` | クラスタのジョブキュー [cjob](https://github.com/Shu-Tanaka-Group/research-cluster-job-system) | `commands_per_task` 個のコマンドをまとめて 1 タスク |

小さく試すときは local / pueue，本番のスイープは cjob，という使い分けを想定している。
cjob の初期設定（パラメータの決め方）は `docs/setup.md` を参照。

### クラスタ（cjob）で実行する

JupyterHub の Notebook（cjob が使える環境）で `BACKEND = "cjob"` にして add-tasks を実行する。

```
add-tasks.py（pueue なら 1 コマンド 1 タスクになるコマンド群）
     │
     ▼  commands_per_task 個ずつ 1 つの cjob タスクにまとめる（飛び飛びに配る）
data/tasks/<group>-<日時>-<id>.json      [[コマンド, コマンド, ...], [...], ...]  ← 1 要素 = 1 タスク
     │
     ▼
cjob sweep -n <タスク数> --parallel <parallel> --cpu <cpu> --memory <memory> --time-limit <time_limit> \
    -- python -m src.task_runner <タスクファイル> _INDEX_ --workers <workers> --threads <cpu // workers>
     │
     ▼  各タスク（= cpu コアを確保した 1 つの実行環境）の中で
src/task_runner.py が _INDEX_ 番目のタスクのコマンドを workers 個ずつ並列に実行（タスク内の小さな pueue）
```

- 1 コマンドごとに cjob のタスクを立てると，コンテナの起動などのオーバーヘッドが計算時間より大きくなりやすい。
  そのため複数のコマンドを 1 タスクにまとめる。まとめる数（`commands_per_task`）は実験ごとに決める
- まとめるときはグリッドの順に区切らず，タスク i にコマンド i, i + タスク数, i + 2 × タスク数, ... を配る。
  重いパラメータ点（大きい N・T など）が 1 つのタスクに偏らず，各タスクの所要時間がそろいやすい
- cjob はジョブ投入時の作業ディレクトリ・環境変数・仮想環境をそのまま引き継ぐので，
  コマンドは手元と同じ `.venv` の Python で実行される
- `time_limit` は sweep 全体（全タスクが終わるまで）にかかり，消費量としても計上される。
  sweep が長くなりすぎるときは `max_tasks_per_job` で sweep を分割する
- sweep は何件のタスクを含んでも cjob のジョブ数上限（投入 500 件・同時実行 32 件）に対して 1 件と数えられる

運用:

- 進捗は `cjob list`，各タスクのログは `cjob logs <job-id> --index <i>`。
  ログには各コマンドの開始・終了コード・所要時間と，タスク全体の所要時間が出るので，
  `commands_per_task` や `time_limit` の見直しに使う
- コマンドが失敗しても同じタスクの残りのコマンドは実行され，タスクは終了コード 1（FAILED）で終わる
- タイムアウトや失敗で残ったパラメータ点は，同じ add-tasks を再実行すれば未完了の分だけ投入される

## データのアーカイブ（DVC + Google Drive）

`data/` は git 管理外なので，節目ごとに圧縮スナップショットを作り，DVC で Google Drive に保存する。
`data/runs/` は小さなファイルが大量にあり，Google Drive の API はファイル単位でレート制限がかかるため，
`data/` を直接 DVC で追跡せず，サブディレクトリごとの `tar.zst` にまとめたものを追跡する。

```bash
scripts/archive_data.sh                                  # archive/data-<日付>/ を作って dvc add
git commit -m "Archive data snapshot data-20261004" archive/data-20261004.dvc
dvc push archive/data-20261004.dvc                       # Google Drive へ送信

scripts/restore_data.sh data-20261004 [runs ...]         # 無ければ dvc pull して data/ に展開
```

DVC と Google Drive（API 経由）の初期設定は `docs/setup.md` を参照。

## 新しい実験を追加する

1. 問題・手法のロジックを `src/<package>/` に書き，`tests/unit/<package>/` にテストを書く
2. `experiments/mc-pi/` をコピーして `experiments/<name>/` を作り，ファイル名とパラメータを置き換える
   - `<name>_taskio.py`: `RunStore(experiment="<name>", param_types={...})`
   - `<name>.py`: argparse → `build_params` → `is_done` ならスキップ → `save_input` → 計算 → `save_output`
   - `<name>-add-tasks.py`: 先頭の定数でグリッドと投入先（`BACKEND`）・リソースを指定する
     （cjob の `CJOB` の決め方は `docs/setup.md`「3.2」）
3. `docs/experiments-io.md` にパラメータと保存キーを追記する
4. `analysis/<name>/` にノートブックを作る（`load_runs_cached(RUNS_ROOT / "<name>", load_run, ...)`）

## テスト・カバレッジ

```bash
uv run pytest            # 全テスト（htmlcov/ にカバレッジ）
uv run pytest -m unit    # 単体テストのみ
```

`tests/unit/` と `tests/e2e/` のテストにはディレクトリ名のマーカーが自動で付く（`tests/conftest.py`）。
e2e テストは `DATA_ROOT` を一時ディレクトリに向けて実行するので `data/` を汚さない。

## コーディング規約

### 責務の分離

各関数は単一の責務を持つ。計算ステップが複数あるなら，それぞれを独立した関数に分ける。

### 戻り値の最小化

呼び出し元が自分で計算できるものは返さない。「これがないと次のステップができない」ものだけを返す。

### 関数名にライブラリ名を含める

実装が特定のライブラリに依存する関数はサフィックスで明示する（例: `build_hamiltonian_qutip`）。

### ノートブック

- 計算ロジックはノートブックに書かず `src/` に置く。ノートブックは集計・作図・動作確認だけ
- `load_runs_cached` の loader はモジュールのトップレベル関数にする（ノートブック内で定義した関数は
  macOS のデフォルトである spawn 方式の並列実行では pickle できない）
- 図はノートブックと同じフォルダの `figs/` に保存する
