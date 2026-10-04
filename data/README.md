# data

git 管理外（この README のみ管理）。環境変数 `DATA_ROOT` で別の場所に移せる。

```
data/
  inputs/                     外部から持ってきたデータ・生成済みの問題インスタンス
  runs/<実験名>/<hash>/
    input.npz                 パラメータと記録用の値
    output.npz                計算結果（これがあれば完了）
  tasks/<group>-<日時>-<id>.json   cjob に投入したタスク（コマンドのまとまり）の一覧
```

キーの一覧は `docs/experiments-io.md`。外部データを置いたときは，入手元・日付・ライセンスを
`inputs/` 内の README か `notes/` に書いておく。

バックアップと復元は `docs/development.md`「データのアーカイブ」を参照。
