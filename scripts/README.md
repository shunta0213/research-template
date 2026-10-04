# scripts

補助スクリプトの使い方。どれもリポジトリ直下から `scripts/<name>.sh` で実行する（どこから実行しても
リポジトリ直下を基準に動く）。`-h` で簡単な使い方が出る。

| スクリプト | 用途 | 対話形式 |
|---|---|---|
| [`setup_dvc.sh`](#setup_dvcsh) | DVC の remote（Google Drive，API 経由）を設定する | ○ |
| [`archive_data.sh`](#archive_datash) | `data/` のスナップショットを作り，DVC で追跡する | − |
| [`restore_data.sh`](#restore_datash) | スナップショットを `data/` に展開する（無ければ Google Drive から取得） | − |

`_common.sh` は各スクリプトが読み込む共通の関数で，単体では実行しない。

**対話形式**: 対話形式に対応したスクリプトは，必要な引数を付けずに実行すると質問形式になる。
質問の `[...]` は既定値で，空欄のまま Enter を押すとそれが使われる。パスの先頭の `~` はホームディレクトリに展開される。
端末以外（パイプ・CI など）から実行するときは，引数をすべて指定する。

## setup_dvc.sh

DVC の remote `gdrive`（Google Drive，Google Drive API 経由）を設定する。事前に Google 側の準備
（[docs/setup.md](../docs/setup.md)「4.1・4.2」：Drive API・サービスアカウントの鍵・共有ドライブのフォルダ）をしておく。
新しい環境（2 台目の PC・クラスタの Notebook）でも，clone した後にこれを実行する。

```bash
scripts/setup_dvc.sh                                                         # 対話形式
scripts/setup_dvc.sh --folder-id <ID> --key <KEY.json>                       # サービスアカウント（推奨）
scripts/setup_dvc.sh --key <KEY.json>                                        # 2 台目以降（フォルダ ID は設定済み）
scripts/setup_dvc.sh --folder-id <ID> --client-id <ID> --client-secret <SECRET>   # 自前の OAuth クライアント
```

| オプション | 内容 | 保存先 |
|---|---|---|
| `--folder-id ID` | Google Drive のフォルダ ID（`https://drive.google.com/drive/folders/<ID>` の URL のままでもよい）。設定済みなら省略可 | `.dvc/config`（git 管理） |
| `--key PATH` | サービスアカウントの鍵（JSON）。`.secrets/gdrive-service-account.json` にコピーされる | 鍵: `.secrets/`，場所: `.dvc/config.local`（どちらも git 管理外） |
| `--client-id ID` | 自前の OAuth クライアント ID（共有ドライブが使えないとき。`--key` の代わり） | `.dvc/config` |
| `--client-secret SECRET` | OAuth クライアントシークレット | `.dvc/config.local` |

やること:

1. DVC が無ければ（または pyOpenSSL が古くて壊れていれば）`uv tool install --force "dvc[gdrive]" --with "pyopenssl>=24.2"` で入れる
2. フォルダ ID を `.dvc/config` に書く
3. 鍵を `.secrets/gdrive-service-account.json`（ディレクトリ 700・ファイル 600）にコピーし，`.dvc/config.local` から
   相対パスで参照する（リポジトリを移動しても使える）。ダウンロードした元の鍵は消してよい
4. `dvc ls-url remote://gdrive` で Google Drive のフォルダに接続できるか確認する
5. `.dvc/config` が変わったら，コミットするよう表示する（自動ではコミットしない）

接続できないときは，フォルダ ID・共有ドライブのメンバーにサービスアカウントのメールアドレスが入っているか・
鍵が正しいかを確認する。

## archive_data.sh

`data/` の各サブディレクトリを `archive/data-<今日の日付>/<サブディレクトリ>.tar.zst` に圧縮し，
DVC があれば `dvc add` で追跡する。`data/` は読むだけで変更しない。

```bash
scripts/archive_data.sh
git commit -m "Archive data snapshot data-YYYYMMDD" archive/data-YYYYMMDD.dvc
dvc push archive/data-YYYYMMDD.dvc            # Google Drive へ送信
```

- 同じ日に再実行すると，既にあるアーカイブはスキップし，新しいサブディレクトリだけ追加する
- 各アーカイブのエントリ数を `data/` 側と照合し，`SHA256SUMS` を作る
- 環境変数 `DATA_ROOT` を設定していれば，`data/` の代わりにそこをアーカイブする
- `dvc add` の後のコミットと `dvc push` は自分で行う（実行後に表示される）

## restore_data.sh

スナップショットを `data/` に展開する。スナップショットが手元に無ければ `dvc pull` で Google Drive から取ってくる。

```bash
scripts/restore_data.sh data-YYYYMMDD                 # 全サブディレクトリ
scripts/restore_data.sh data-YYYYMMDD runs inputs     # 指定したサブディレクトリだけ
```

- 展開前に `SHA256SUMS` で整合性を確認する
- `data/` に同じ名前のディレクトリが既にあるものは上書きせずスキップする（置き換えたいときは先に移動・削除する）
- 使えるスナップショットは `ls archive/*.dvc` で確認できる

## テンプレート専用のスクリプト（テンプレート専用）

次の 2 つはテンプレートからプロジェクトを作るためのもので，プロジェクトの初期化時に削除される
（この節も，見出しが「（テンプレート専用）」で終わるので削除される）。

| スクリプト | 用途 | 対話形式 |
|---|---|---|
| [`new_project.sh`](#new_projectsh) | テンプレートから新しいプロジェクトを作る（URL から直接実行できる） | ○ |
| [`init_project.sh`](#init_projectsh) | テンプレートのコピーをその場でプロジェクトとして初期化する | ○ |

### new_project.sh

テンプレートをコピーして新しい研究プロジェクトを作る。作ったプロジェクトにはコピーされない。

```bash
# URL から（テンプレートを手元に置かなくてよい）
bash <(curl -fsSL https://raw.githubusercontent.com/shunta0213/research-template/main/scripts/new_project.sh)            # 対話形式
bash <(curl -fsSL https://raw.githubusercontent.com/shunta0213/research-template/main/scripts/new_project.sh) <作成先> [オプション]

# テンプレートを clone 済みなら
research-template/scripts/new_project.sh                     # 対話形式
research-template/scripts/new_project.sh <作成先> [オプション]  # 引数指定
```

| 引数・オプション | 内容 |
|---|---|
| `<作成先>` | 作るディレクトリ。**ディレクトリ名がプロジェクト名になる**（英数字と `. _ -` のみ）。既に存在するとエラー |
| `--description TEXT` | `pyproject.toml` の `description`（と GitHub のリポジトリの説明）に入る一行説明 |
| `--folder-id ID` | DVC の設定もするときの Google Drive のフォルダ ID（フォルダの URL でもよい） |
| `--key PATH` | DVC の設定もするときのサービスアカウントの鍵（JSON）。`--folder-id` と一緒に指定する |
| `--github OWNER` | GitHub の `OWNER/<プロジェクト名>` にリポジトリを作って push する（要 `gh auth login`）。既にあるとエラー |
| `--public` | `--github` のリポジトリを public にする（省略時は private） |

| 環境変数 | 内容 |
|---|---|
| `RESEARCH_TEMPLATE_REPO` | URL から実行したときに clone するテンプレート（既定: `https://github.com/shunta0213/research-template.git`）。fork したテンプレートを使うとき |

やること:

1. URL から実行したとき（テンプレートの外から実行したとき）は，テンプレートの最新の main を一時ディレクトリに
   `git clone --depth 1` し，その中の `new_project.sh` で以下を行う（一時ディレクトリは終了時に消える）。
   `curl ... | bash` の形で実行したときも，質問の答えは端末から読む
2. 入力を確認する（作成先が既にある・GitHub に同名のリポジトリがある・鍵が無い，ならここで止まり，何も作らない）
3. テンプレートを作成先にコピーする。次のものはコピーしない:
   `.git`・`.venv`・キャッシュ類（`__pycache__`・`.pytest_cache`・`htmlcov` など）・`data/` の中身（README 以外）・
   `cache/` と `tmp/` の中身・`archive/data-*`・`.secrets/`・`.dvc/config.local`・このスクリプト
4. 作成先で [`init_project.sh`](#init_projectsh) を実行する（名前の書き換え → `uv sync` → テスト → 最初のコミット）
5. `--folder-id` と `--key` があれば [`setup_dvc.sh`](#setup_dvcsh) を実行し，`.dvc/config` をコミットする
6. `--github` があれば `gh repo create OWNER/<プロジェクト名> --source <作成先> --push` で GitHub に作って push する

5・6 が失敗してもプロジェクトは作られる（後から `scripts/setup_dvc.sh`・`gh repo create` でやり直せる）。

例:

```bash
URL=https://raw.githubusercontent.com/shunta0213/research-template/main/scripts/new_project.sh

# 対話形式
bash <(curl -fsSL $URL)

# DVC・GitHub は後でする
bash <(curl -fsSL $URL) ~/research/my-study --description "研究の一行説明"

# DVC の設定と GitHub（private）まで一度に
bash <(curl -fsSL $URL) ~/research/my-study --description "研究の一行説明" \
    --folder-id "https://drive.google.com/drive/folders/1AbC..." --key ~/Downloads/<key>.json \
    --github shunta0213
```

### init_project.sh

テンプレートのコピーを，その場で新しい研究プロジェクトとして初期化する。GitHub の「Use this template」で
作ったリポジトリを clone した直後に使う（`new_project.sh` も内部でこれを呼ぶ）。初期化が終わると
このスクリプト自身も削除される。

```bash
scripts/init_project.sh                                              # 対話形式
scripts/init_project.sh [--name NAME] [--description TEXT] --yes     # 引数指定（質問なし）
```

| オプション | 内容 |
|---|---|
| `--name NAME` | プロジェクト名（英数字と `. _ -` のみ）。省略するとリポジトリのディレクトリ名 |
| `--description TEXT` | `pyproject.toml` の `description` に入る一行説明 |
| `--yes` | 質問・確認をせずに実行する（端末以外から実行するときは必須） |

やること:

1. `pyproject.toml` の `name`・`description` と `README.md` の見出しを書き換える
2. Markdown の見出しが「（テンプレート専用）」で終わる `##` 節（README の「新しいプロジェクトを作る」，この節など）を
   次の `##` 見出しの手前まで削除し，`new_project.sh` と `init_project.sh` を削除する
3. git リポジトリでなければ `git init` する（GitHub から clone した場合はそのまま使う）
4. `uv sync` → `uv run pytest` → コミット（`Initialize <name> from research-template`）。**push はしない**

安全のため，`pyproject.toml` の `name` が `research-template` でない（初期化済み）とき，
およびプロジェクト名が `research-template` のとき（テンプレート自身）はエラーで止まる。

テンプレートにプロジェクトでは不要な説明を足すときは，見出しの末尾に「（テンプレート専用）」を付けた `##` 節にする。

例:

```bash
gh repo create <owner>/my-study --private --template shunta0213/research-template --clone
cd my-study
scripts/init_project.sh
git push
```
