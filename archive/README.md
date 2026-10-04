# archive

使わなくなったものとデータのスナップショットの保管場所。通常の pytest（`testpaths = ["tests"]`）と ruff の対象外。

- `code-YYYYMMDD/`: 引退させたコード・テスト・ノートブック（git 管理）。**リポジトリ直下からの相対パスを保ったまま**移す
  （例: `src/foo/bar.py` → `archive/code-20261004/src/foo/bar.py`）。移した理由を `docs/decisions.md` に書く
- `data-YYYYMMDD/`: `scripts/archive_data.sh` が作る `data/` の圧縮スナップショット。
  中身は git 管理外で DVC が追跡し，Google Drive に保存する。git には `data-YYYYMMDD.dvc`（ポインタ）だけを入れる。
  `SHA256SUMS` で整合性を確認できる

```bash
scripts/archive_data.sh                          # スナップショット作成 + dvc add
git commit -m "Archive data snapshot data-YYYYMMDD" archive/data-YYYYMMDD.dvc
dvc push archive/data-YYYYMMDD.dvc               # Google Drive へ

scripts/restore_data.sh data-YYYYMMDD [runs ...] # 無ければ dvc pull して data/ に展開
```

DVC と Google Drive（API 経由）の初期設定は `docs/setup.md`「4. データのアーカイブ」を参照。
