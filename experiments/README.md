# experiments

1 実験 1 フォルダ。各フォルダは次の 3 ファイルで構成する（`mc-pi/` が例）。

| ファイル | 役割 |
|---|---|
| `<name>.py` | 計算本体（CLI）。1 回の実行で 1 パラメータ点を計算し `data/runs/<name>/<hash>/` に保存 |
| `<name>_taskio.py` | `RunStore` を 1 つ定義（ハッシュ対象のパラメータと型）。上下 2 つから import する |
| `<name>-add-tasks.py` | パラメータグリッドを実行・投入。先頭の定数で `BACKEND`（`local` / `pueue` / `cjob`）とリソースを指定する |

必要に応じて `<name>.ipynb`（1 点だけの動作確認用）を置いてよい。集計・作図は `analysis/<name>/` で行う。

実行はリポジトリ直下から:

```bash
uv run python experiments/<name>/<name>.py --help
uv run python experiments/<name>/<name>-add-tasks.py
```

追加手順・パラメータを変えるときの規則は `docs/development.md`，cjob のパラメータの決め方は `docs/setup.md`「3.2」を参照。
