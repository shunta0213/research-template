# 初期設定

新しい研究プロジェクトを始めるときに一度だけ行う作業。上から順に進める。
使い方（日々の運用）は [docs/development.md](development.md)，スクリプトの使い方は [scripts/README.md](../scripts/README.md) を参照。

## 前提

このテンプレートは次のツールが使えることを前提にしている（インストール手順はここでは扱わない）。

| ツール | 使う場所 | 用途 |
|---|---|---|
| [uv](https://docs.astral.sh/uv/) | 手元・クラスタ | Python 環境（`uv sync`・`uv run`）と DVC のインストール |
| git | 手元・クラスタ | コード管理（`input.npz` に実行時のコミットを記録する） |
| [pueue](https://github.com/Nukesor/pueue) | 手元 | 手元のマシンでの並列実行（デーモン `pueued` が起動していること） |
| [cjob](https://github.com/Shu-Tanaka-Group/research-cluster-job-system) | クラスタ（JupyterHub の Notebook） | クラスタへのジョブ投入 |
| zstd | 手元・クラスタ | データのスナップショットの圧縮（`scripts/archive_data.sh`） |

DVC はプロジェクトの依存に入れず，「4. データのアーカイブ」の `scripts/setup_dvc.sh` が uv のツールとして入れる。

## 1. プロジェクトを作る

プロジェクトはテンプレート（<https://github.com/shunta0213/research-template>）の README
「新しいプロジェクトを作る」の方法で作る。いちばん簡単なのは次の 1 行（対話形式）:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/shunta0213/research-template/main/scripts/new_project.sh)
```

名前の書き換え・`uv sync`・テスト・最初のコミット（と，選んだ場合は DVC の設定・GitHub へのリポジトリ作成）まではスクリプトが行う。

プロジェクトを作った後に手で行うこと:

- [ ] `README.md` の概要を自分の研究の説明に書き換える
- [ ] GitHub にリポジトリを作っていなければ作って push する（`gh repo create <owner>/<project> --private --source . --push`）
- [ ] 自分の最初の実験が動いたら，例題を消す
  - `src/mc/`，`experiments/mc-pi/`，`analysis/mc-pi/`
  - `tests/unit/mc/`，`tests/e2e/test_mc_pi_pipeline.py`
  - `docs/experiments-io.md` の mc-pi の節
- [ ] `docs/decisions.md` のテンプレート由来の項目は残すか消すか決める（残すと方式の理由を後から追える）

## 2. 手元の並列実行（pueue）

- [ ] `pueue status` でデーモンが動いていることを確認する
- [ ] add-tasks の `PARALLEL` を決める: 物理コア数 ÷ 1 コマンドのスレッド数

## 3. クラスタ（cjob）

[research-cluster-job-system](https://github.com/Shu-Tanaka-Group/research-cluster-job-system) のクラスタで実行するための設定。
以下は JupyterHub の Notebook（ジョブを投入する環境）で行う。

### 3.1 環境の準備

- [ ] ホームディレクトリ以下にリポジトリを clone して `uv sync`
- [ ] データの置き場所がジョブから見えることを確認する。デフォルトの `<repo>/data` はホームディレクトリ以下なので
  そのままでよい。`DATA_ROOT` を設定する場合は共有ストレージを指すこと
- [ ] `cjob flavor list` と `cjob flavor info <flavor>` で，使う flavor の **TASK LIMIT**（1 タスクで指定できる
  CPU・メモリの上限）と QUOTA を控える。`cjob usage` で自分の割り当ても確認する
- [ ] 秘密情報を環境変数に入れている場合は，ジョブに送られないよう除外する:
  `cjob config add env exclude <変数名>`（cjob は投入時の環境変数をすべてジョブに引き継ぐ）

### 3.2 `CjobConfig` を決める

cjob では，複数のコマンド（pueue なら複数のタスクになるもの）を 1 つの cjob タスクにまとめて投入する
（仕組みは `docs/development.md`「クラスタ（cjob）で実行する」）。各実験の add-tasks の `CJOB` で次を決める。

| 設定 | 例 | 決め方 |
|---|---|---|
| スレッド数（`cpu // workers`） | 1 | 1 コマンドが BLAS/OpenMP の複数スレッドで速くなるか。小さい問題のスイープなら 1 |
| `cpu` | 8–16 | TASK LIMIT 以内。大きいほど 1 タスクで多くのコマンドを同時に流せる |
| `workers` | `cpu // スレッド数` | タスク内で同時に実行するコマンド数 |
| `memory` | `"16Gi"` | 1 コマンドのピークメモリ × `workers` × 1.2 程度 |
| `commands_per_task` | 50 | 1 タスクにまとめるコマンド数。1 タスクの所要時間 ≈ 1 コマンドの時間 × `commands_per_task` / `workers` が数時間程度になるように |
| `parallel` | 4–10 | 同時に動かすタスク数。同時に `parallel × cpu` コアを使う。使いすぎると公平性のため優先度が下がる |
| `time_limit` | `"12h"` | sweep 全体の上限。タスク数 / `parallel` × 1 タスクの所要時間 に余裕を持たせる。短すぎると打ち切られ，長すぎると消費量として計上される |
| `max_tasks_per_job` | `None` | `time_limit` が長くなりすぎる（目安 1 日超）ときに sweep を分割する |

手順:

1. **ざっくり測る**: 小さいグリッドを `BACKEND = "local"` か `"pueue"` で流し，1 コマンドがだいたい何分か
   （`output.npz` の `elapsed_sec` や pueue の表示）と，メモリのピーク（Linux なら
   `/usr/bin/time -v uv run python experiments/<name>/<name>.py ...` の `Maximum resident set size`）を見る
2. **値を決める**: 上の表に沿って `cpu`・`workers`・`memory`・`commands_per_task`・`time_limit` を決める。
   コマンドごとの所要時間が大きく違うスイープでも，コマンドは飛び飛びに配られるので，平均的な時間で考えればよい
3. **dry run で確認する**: `BACKEND = "cjob"`，`DRY_RUN = True` で add-tasks を実行し，タスク数と sweep の数を見る
4. **小さく投入する**: グリッドを 1–2 タスク分に絞って `DRY_RUN = False` で投入し，
   `cjob logs <job-id> --index 0` の最後に出るタスクの所要時間を見て `commands_per_task`・`time_limit` を直す
5. グリッドを戻して本番を投入する

## 4. データのアーカイブ（DVC + Google Drive API）

`archive/data-<日付>/` のスナップショットを，DVC で Google Drive に Google Drive API 経由で保存する設定。
サービスアカウントで接続するのでブラウザでの認可が要らず，クラスタの Notebook からも同じように push / pull できる。
4.1・4.2 は Google 側の手作業，4.3 はスクリプトで行う。

### 4.1 Google Cloud 側（研究室で 1 回やれば，以降のプロジェクトは使い回せる）

- [ ] Google Cloud でプロジェクトを作り，「Google Drive API」を有効にする
- [ ] 「IAM と管理 > サービスアカウント」でサービスアカウントを作り，鍵（JSON）を作ってダウンロードする

### 4.2 Google Drive 側（プロジェクトごと）

- [ ] **共有ドライブ**にこのプロジェクト用のフォルダを作る（サービスアカウントは自分のストレージ容量を
  持たないため，マイドライブのフォルダには書き込めない）
- [ ] 共有ドライブのメンバーにサービスアカウントのメールアドレス（`...@<gcp-project>.iam.gserviceaccount.com`）を
  「コンテンツ管理者」で追加する
- [ ] フォルダの URL `https://drive.google.com/drive/folders/<FOLDER_ID>` から `<FOLDER_ID>` を控える

### 4.3 リポジトリ側（`scripts/setup_dvc.sh`）

対話形式で実行し，4.2 で控えたフォルダの URL（または ID）と，4.1 でダウンロードした鍵のパスを答える。

```bash
scripts/setup_dvc.sh
git commit -m "Set DVC remote" .dvc/config
```

```
Google Drive のフォルダの URL または ID: https://drive.google.com/drive/folders/1AbC...
認証方法: 1) サービスアカウント（推奨。共有ドライブが必要）  2) 自前の OAuth クライアント（個人アカウント）
番号 [1]:
サービスアカウントの鍵（JSON）のパス: ~/Downloads/my-gcp-project-123abc.json
...
[dvc] OK
```

引数で指定する場合は `scripts/setup_dvc.sh --folder-id <URL または ID> --key <鍵.json>`。
オプションとスクリプトがやることの詳細は [scripts/README.md](../scripts/README.md#setup_dvcsh)。要点:

- DVC が無ければ uv のツールとして入れる（`dvc[gdrive]` が引き込む古い pyOpenSSL では落ちるため，新しくして入れる）
- 鍵は**このリポジトリの `.secrets/gdrive-service-account.json`**（git 管理外，権限 600）にコピーする。
  鍵はプロジェクトごとに閉じていて，ホームディレクトリの共通の場所には置かない。ダウンロードした元の鍵は消してよい
- 最後に Google Drive のフォルダに接続できるか確認する（`[dvc] OK` が出れば成功）

チェックリスト:

- [ ] 初回のアーカイブで push まで確認する: `scripts/archive_data.sh` → `dvc push archive/data-<日付>.dvc` →
  Drive のフォルダにファイルができる
- [ ] 別の環境（2 台目の PC・クラスタの Notebook など）では，clone してから鍵をその環境に置き
  （JupyterHub ならアップロード），`scripts/setup_dvc.sh` を実行する（フォルダ ID は `.dvc/config` に入っている）

### 共有ドライブが使えない場合

個人の Google アカウントしかない場合は，サービスアカウントの代わりに自前の OAuth クライアントで API に接続する。
Google Cloud の「API とサービス > 認証情報」で OAuth クライアント ID（デスクトップアプリ）を作り，
`scripts/setup_dvc.sh` の認証方法で `2` を選ぶ（引数なら `--client-id <ID> --client-secret <SECRET>`）。
初回の接続でだけブラウザでの認可が要る（ブラウザの無いクラスタでは使いにくい）。

## 5. 記録の準備

- [ ] `refs/references.bib` に主要な先行研究を入れる
- [ ] `notes/TEMPLATE.md` をコピーして最初の研究ノートを書く（目的・問い）
