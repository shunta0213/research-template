# AGENTS.md

このリポジトリで作業する AI エージェント（Claude Code・Codex など）への指示。
人間向けの説明は `README.md` と `docs/`。ここにはエージェントが作業前に知っておくべきことだけを書く。

## このリポジトリ

研究用リポジトリ（[research-template](https://github.com/shunta0213/research-template) から作成）。
「実験を回す → 結果を集計・可視化する → 記録を残す」を再現できる形で回す。

| 知りたいこと | 読むもの |
|---|---|
| 実験の追加・実行・データ管理・規約 | `docs/development.md`（迷ったらまずここ） |
| 各実験のパラメータと保存キー | `docs/experiments-io.md` |
| なぜこの方式なのか | `docs/decisions.md` |
| 初期設定（pueue・cjob・DVC） | `docs/setup.md` |
| スクリプトの使い方 | `scripts/README.md` |

## コマンド

```bash
uv sync                          # 環境構築
uv run pytest                    # テスト（-m unit / -m e2e で絞れる）
uv run ruff check . && uv run ruff format --check .
uv run python experiments/<name>/<name>.py --help
```

- Python は必ず `uv run` 経由で実行する（`.venv`）。`pip install` はしない。依存の追加は `uv add <pkg>`
- 作業を終える前に `uv run pytest` と `uv run ruff check .` を通す

## 構成の要点

- `src/`: 共通ロジック。`from src.<pkg> import ...` で import する（editable install）。`tests/unit/` が同じ構造をミラーする
- `experiments/<name>/`: 1 実験 1 フォルダで 3 ファイル（`<name>.py` 計算本体・`<name>_taskio.py` の `RunStore`・
  `<name>-add-tasks.py` 投入）。新しい実験は `experiments/mc-pi/` を手本にする
- `data/runs/<name>/<hash>/{input,output}.npz`: 1 パラメータ点の結果。`<hash>` は `RunStore.param_types` の
  パラメータから決まる。**`output.npz` があれば完了**
- `analysis/<name>/`: 集計・作図のノートブックと `figs/`。集計は `src.run_cache.load_runs_cached` でキャッシュする
- `data/`・`cache/`・`tmp/`・`.secrets/` は git 管理外

## 守ること

### データを壊さない

- 既存の実験の `param_types` の**項目・順序・型を変えない**（hash が変わり既存データと対応しなくなる）。
  結果に影響するパラメータを足すときは `<name>-v2` の新しい実験にし，`docs/decisions.md` に理由を書く
- `data/`・`archive/data-*`・`cache/` のファイルを削除・上書きしない（`cache/` の作り直しはユーザーが `refresh` で指示したときだけ）
- 実験スクリプトの保存先を `src.runs.RunStore` 以外の方法で作らない

### 確認してから行う（計算資源・外部サービス・取り消せない操作）

次はユーザーの明示的な指示があるまで実行しない。指示があっても内容（件数・リソース・送り先）を示してから行う。

- add-tasks を `DRY_RUN = False` で実行すること（pueue・cjob への投入，ローカルでの大量実行）。
  `DRY_RUN = True` での確認は自由に行ってよい
- `cjob` のジョブ操作（`cjob sweep`・`cancel`・`delete` など。`cjob list`・`status`・`logs` の参照はよい）
- `dvc push`・`dvc pull`・`git push`・`gh repo create` など外部への送信
- `scripts/setup_dvc.sh`・`scripts/archive_data.sh`・`scripts/restore_data.sh` の実行

### 秘密情報

- `.secrets/` と `.dvc/config.local` は読まない・表示しない・コミットしない
- 鍵やトークンをコード・ノート・コミットメッセージに書かない

### 研究の記録として正しくする

- 計算結果の数値を推測で書かない。ノートや文書では図のパスや run の hash で参照する
- テストを通すためにテストや許容誤差を緩めない。物理的・数値的に正しいかが疑わしいときはユーザーに伝える
- 失敗した試み・やめた方針も，頼まれたら `notes/` に残す（消さない）

## 変更したら更新するもの

| 変更 | 更新するもの |
|---|---|
| 実験の追加・パラメータや保存キーの変更 | `docs/experiments-io.md` |
| 方式・データ形式・ハッシュ対象の決定や変更 | `docs/decisions.md` の先頭に追記 |
| `src/` にモジュールを追加 | `tests/unit/` の同じ階層にテスト |
| スクリプトのオプションの変更 | `scripts/README.md` |

詳しくは `docs/development.md`「記録を残す」。

## コーディング規約

- 各関数は単一の責務。計算ステップが複数あれば関数を分ける
- 呼び出し元が計算できるものは返さない（次のステップに必要なものだけを返す）
- 特定のライブラリに依存する関数は名前にサフィックスを付ける（例: `build_hamiltonian_qutip`）
- 型ヒントを付ける。docstring・コメントは日本語で，周りのコードの書き方（句読点「，」「。」）に合わせる
- 行の長さは 120（ruff）
- ノートブックには計算ロジックを書かず `src/` に置く。`load_runs_cached` の loader はモジュールのトップレベル関数にする
  （ノートブック内で定義した関数は macOS の spawn 方式の並列実行で pickle できない）

## テンプレートの保守（テンプレート専用）

この節はテンプレート（research-template）自体を編集するときだけ使う。プロジェクトの初期化時に削除される。

- プロジェクトでは不要な説明は，見出しの末尾に「（テンプレート専用）」を付けた `##` 節に書く
  （`scripts/init_project.sh` がその節を削除する）。HTML コメントのマーカーは整形で消えるので使わない
- テンプレートのスクリプト（`new_project.sh`・`init_project.sh` など）を変えたら，一時ディレクトリで
  `RESEARCH_TEMPLATE_REPO=file://<clone> scripts/new_project.sh <tmp>/<name>` を実行し，作られたプロジェクトで
  テストが通ること・テンプレート専用の節が消えることを確認する
- `main` に push すると，次に URL から作るプロジェクトに反映される。push はユーザーの指示があるときだけ
