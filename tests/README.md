# Test suites

- `unit/`: `src/` のモジュール構造をミラーした単体テスト。新モジュールを追加したら同じ階層に `test_xxx.py` を作る
- `e2e/`: `experiments/` のスクリプトを実際に実行し，保存されたデータを検査する（`DATA_ROOT` を一時ディレクトリに向ける）

```bash
uv run pytest            # すべて
uv run pytest -m unit    # unit のみ
uv run pytest -m e2e     # e2e のみ
```
