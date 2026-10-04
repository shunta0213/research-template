# 実験別 入出力リファレンス

各実験が `data/runs/<実験名>/<hash>/` に保存する `input.npz` / `output.npz` のキー一覧。

- 太字 = ハッシュ対象（`RunStore.param_types`。同じ値なら `<hash>` が一致する）
- それ以外は記録用（`input.npz` には保存されるがハッシュには影響しない）
- すべての実験の `input.npz` に共通して次が入る（`src/runs.py` が自動で保存）

| キー | 内容 |
|---|---|
| params_hash | ハッシュ値そのもの（ディレクトリ名と一致） |
| git_commit | 実行時のコミット（未コミットの変更があれば `-dirty` 付き） |
| started_at | 実行開始時刻 |

## mc-pi

モンテカルロ法による π の推定（`experiments/mc-pi/`）。

### input.npz

| キー | 内容 |
|---|---|
| **n_samples** | サンプル点の数 |
| **seed** | 乱数シード（`np.random.default_rng`） |

### output.npz

| キー | 内容 |
|---|---|
| n_inside | 円の内側に入った点の数 |
| pi_hat | π の推定値 `4 n_inside / n_samples` |
| std_error | 推定値の標準誤差 |
| elapsed_sec | 計算時間（秒） |

<!-- 新しい実験を追加したら，上と同じ形式で節を追加する -->
