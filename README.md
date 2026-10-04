# research-template

研究用リポジトリのテンプレート。「実験を回す → 結果を集計・可視化する → 記録を残す」を
再現できる形で回すためのフォルダ構成と共通ユーティリティをまとめたもの。
例題としてモンテカルロ法による π の推定（`mc-pi`）が一通り実装されている。

## 前提

uv・git・pueue（手元）・cjob（クラスタ）・zstd が使えること。DVC は `scripts/setup_dvc.sh` が uv のツールとして入れる。
詳細は [docs/setup.md](docs/setup.md)「前提」。

## 新しいプロジェクトを作る（テンプレート専用）

テンプレートのリポジトリ: <https://github.com/shunta0213/research-template>

次の 3 通りのどれかで作る。どの方法でも `scripts/init_project.sh` が

- `pyproject.toml` の `name`・`description` と README の見出しをプロジェクト名に書き換える
- テンプレート専用の部分（見出しが「（テンプレート専用）」の節）とテンプレート専用のスクリプトを削除する
- `uv sync` → `uv run pytest` → 最初のコミット

を行う。スクリプトの詳しい使い方は [scripts/README.md](scripts/README.md)。

### A. URL から対話形式で作る（おすすめ）

テンプレートを手元に置いていなくても，次の 1 行で始められる。

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/shunta0213/research-template/main/scripts/new_project.sh)
```

スクリプトがテンプレートを一時ディレクトリに `git clone` し，作成先・一行説明・DVC の設定をするか・
GitHub にリポジトリを作るかを順に聞いてくる（一時ディレクトリは終了時に消える）。
DVC の設定をする場合は，先に [docs/setup.md](docs/setup.md)「4.1・4.2」の Google 側の準備
（フォルダとサービスアカウントの鍵）をしておく。GitHub にリポジトリを作るには `gh` にログインしておく。

```
[new_project] downloading template: https://github.com/shunta0213/research-template.git
research-template から新しい研究プロジェクトを作ります（Ctrl-C で中止）

作成先ディレクトリ（ディレクトリ名がプロジェクト名になる。例: ~/research/my-study）: ~/research/my-study
プロジェクトの一行説明（空欄可）: 制約付き組合せ最適化での量子アニーリングのサンプリングの偏り
...
続けて DVC の設定もしますか [y/N]: y
Google Drive のフォルダの URL または ID: https://drive.google.com/drive/folders/1AbC...
サービスアカウントの鍵（JSON）のパス: ~/Downloads/my-gcp-project-123abc.json

GitHub にこのプロジェクトのリポジトリを作って push しますか [y/N]: y
GitHub のアカウントまたは organization [shunta0213]:
public にしますか（N なら private） [y/N]:
...
できたプロジェクト: /Users/you/research/my-study
GitHub: https://github.com/shunta0213/my-study (private)
```

`curl ... | bash` の形でも動く（質問の答えは端末から読む）。テンプレートを clone 済みなら
`research-template/scripts/new_project.sh` を直接実行しても同じ。

### B. 引数で指定して作る

質問なしで最後まで実行する。スクリプトから呼ぶときや，同じ設定で何度も作るとき向け。

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/shunta0213/research-template/main/scripts/new_project.sh) \
    ~/research/my-study \
    --description "研究の一行説明" \
    --folder-id <FOLDER_ID> --key ~/Downloads/<key>.json \
    --github shunta0213                 # DVC・GitHub はどちらも省略可（後から setup_dvc.sh・gh repo create でもよい）
```

`--github` で作るリポジトリは private。public にするときは `--public` も付ける。

### C. GitHub のテンプレートリポジトリから作る

GitHub 上でリポジトリを作ってから clone して初期化する。GitHub の画面で作りたいとき向け。

```bash
gh repo create <owner>/my-study --private --template shunta0213/research-template --clone
#   または https://github.com/shunta0213/research-template の「Use this template」→ 作ったリポジトリを git clone
cd my-study
scripts/init_project.sh            # 対話形式。質問なしなら --name my-study --description "..." --yes
git push
scripts/setup_dvc.sh               # DVC（Google Drive）の設定（対話形式）
git commit -m "Set DVC remote" .dvc/config && git push
```

`init_project.sh` は初期化のコミットを作るだけで push はしないので，内容を確認してから `git push` する。

### テンプレート自体を更新する

テンプレートの改善は <https://github.com/shunta0213/research-template> に push する。A・B は実行のたびに
最新の main を clone するので，次に作るプロジェクトから反映される（作成済みのプロジェクトには反映されない）。

## はじめかた

```bash
uv sync                                            # 環境構築（src は editable install される）
uv run pytest                                      # テスト
uv run python experiments/mc-pi/mc-pi.py --n-samples 100000 --seed 0   # 1 ラン実行
uv run python experiments/mc-pi/mc-pi-add-tasks.py # パラメータスイープ（DRY_RUN を False にしてから）
```

その後 `analysis/mc-pi/mc-pi-analysis.ipynb` で集計・作図する。

スイープの投入先は add-tasks の `BACKEND` で選ぶ：`"local"`（直列実行）、`"pueue"`（手元のマシンで並列実行）、
`"cjob"`（クラスタ。[research-cluster-job-system](https://github.com/Shu-Tanaka-Group/research-cluster-job-system)）。
cjob では複数のコマンド（pueue なら複数のタスクになるもの）を 1 タスクにまとめて投入する。
データのスナップショットは DVC で Google Drive に保存する。

| ドキュメント                                           | 内容                                                 |
| ------------------------------------------------ | -------------------------------------------------- |
| [docs/setup.md](docs/setup.md)                   | 初期設定（pueue・cjob のパラメータ・DVC と Google Drive）のチェックリスト |
| [docs/development.md](docs/development.md)       | 日々の使い方（実験の追加・実行・データ管理・テスト・コーディング規約）                |
| [scripts/README.md](scripts/README.md)           | スクリプトの使い方（DVC の設定・データのアーカイブと復元）                    |
| [docs/experiments-io.md](docs/experiments-io.md) | 各実験のパラメータと保存データのキー                                 |
| [docs/decisions.md](docs/decisions.md)           | 設計判断ログ                                             |
| [AGENTS.md](AGENTS.md)・[CLAUDE.md](CLAUDE.md)     | AI エージェント（Claude Code・Codex など）への指示。`.claude/` に Claude Code の設定とスキル |

## フォルダ構成

| フォルダ           | 内容                                                                         | git |
| -------------- | -------------------------------------------------------------------------- | --- |
| `src/`         | 問題・手法の共通ロジック（ライブラリ）と共通ユーティリティ                                              | ○   |
| `experiments/` | 実験パイプライン（1 実験 1 フォルダ：計算本体・taskio・タスク投入）                                    | ○   |
| `analysis/`    | 結果の集計・可視化ノートブックと図（1 実験 1 フォルダ ＋ `compare/`）                                | ○   |
| `benchmark/`   | 実行時間・メモリなど計算性能の計測                                                          | ○   |
| `tests/`       | `src/` をミラーした単体テスト（`unit/`）と実験スクリプトの通しテスト（`e2e/`）                          | ○   |
| `docs/`        | 初期設定・開発ガイド・実験の入出力仕様・設計判断ログ                                                 | ○   |
| `notes/`       | 研究ノート（日付ごとの作業記録）                                                           | ○   |
| `refs/`        | 参考文献（`references.bib`。PDF は git 管理外）                                       | ○   |
| `scripts/`     | 補助スクリプト（DVC の設定・データのアーカイブと復元。[scripts/README.md](scripts/README.md)）       | ○   |
| `archive/`     | 使わなくなったコード（`code-<日付>/`）とデータのスナップショット（`data-<日付>/`、DVC で Google Drive に保存） | △   |
| `data/`        | 実験結果（`runs/<実験名>/<hash>/`）、外部入力（`inputs/`）、cjob のタスクファイル（`tasks/`）         | ×   |
| `cache/`       | 集計結果のキャッシュ（消しても `data/` から再生成できる）                                          | ×   |
| `tmp/`         | 使い捨ての作業用ノートブックなど                                                           | ×   |
| `.claude/`     | Claude Code の共有設定（`settings.json`）とスキル（`skills/`）。指示本体は `AGENTS.md`                | ○   |
| `.secrets/`    | 秘密情報（DVC 用の Google Drive の鍵。`scripts/setup_dvc.sh` が置く）                    | ×   |

## データの流れ

```
experiments/<name>/<name>-add-tasks.py   パラメータグリッドを投入（local / pueue / cjob）
        │
        ▼
experiments/<name>/<name>.py             1 パラメータ点を計算
        │   <name>_taskio.py がパラメータ → hash を決める
        ▼
data/runs/<name>/<hash>/{input,output}.npz
        │
        ▼
analysis/<name>/*.ipynb                  集計（cache/ にキャッシュ）→ figs/ に作図
        │
        ▼
notes/YYYY-MM-DD.md                      何を見て何を考えたかを記録（図・hash へのリンク）

data/ ──scripts/archive_data.sh──▶ archive/data-<日付>/ ──dvc push──▶ Google Drive
```

詳細は [docs/development.md](docs/development.md) を参照。