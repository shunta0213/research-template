# analysis

実験結果の集計・可視化。

- `<name>/`: 実験 `experiments/<name>/` の結果を見るノートブック。図は `<name>/figs/` に保存する
- `compare/`: 複数の実験をまたぐ比較。図は `compare/figs/<ノートブック名>/` に保存する

集計は `src.run_cache.load_runs_cached` でキャッシュ（`cache/`）する。キャッシュは自動では更新されないので，
新しいランを取り込むときは `refresh="new"`，loader を変えたときは `refresh=True` を指定する。

論文に載せる図を作ったら，どのノートブックのどのセルで作ったかを `notes/` に書いておく。
