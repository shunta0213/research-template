# data

git 管理外（この README のみ管理）。環境変数 `DATA_ROOT` で別の場所に移せる。

```
data/
  inputs/                     外部から持ってきたデータ・生成済みの問題インスタンス
  runs/<実験名>/<hash>/
    input.npz                 パラメータと記録用の値
    output.npz                計算結果（これがあれば完了）
  tasks/<group>-<日時>-<id>.json   cjob に投入したコマンド一覧（sweep の _INDEX_ 番目を実行する）
```

キーの一覧は `docs/experiments-io.md`。外部データを置いたときは，入手元・日付・ライセンスを
`inputs/` 内の README か `notes/` に書いておく。

バックアップは `scripts/archive_data.sh`（`archive/data-<日付>/` に圧縮して DVC で Google Drive へ），
復元は `scripts/restore_data.sh data-<日付>`。
