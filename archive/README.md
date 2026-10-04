# archive

使わなくなったものとデータのスナップショットの保管場所。通常の pytest（`testpaths = ["tests"]`）と ruff の対象外。

- `code-YYYYMMDD/`: 引退させたコード・テスト・ノートブック（git 管理）。**リポジトリ直下からの相対パスを保ったまま**移す
  （例: `src/foo/bar.py` → `archive/code-20261004/src/foo/bar.py`）。移した理由を `docs/decisions.md` に書く
- `data-YYYYMMDD/`: `data/` の圧縮スナップショット（`*.tar.zst` と `SHA256SUMS`）。中身は git 管理外で DVC が追跡し，
  Google Drive に保存する。git には `data-YYYYMMDD.dvc`（ポインタ）だけを入れる

スナップショットの作り方・戻し方は `docs/development.md`「データのアーカイブ」と
`scripts/README.md`（`archive_data.sh`・`restore_data.sh`）を参照。
