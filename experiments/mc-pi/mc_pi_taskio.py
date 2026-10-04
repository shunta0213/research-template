"""mc-pi のパラメータ ⇄ run ディレクトリ（data/runs/mc-pi/<hash>/）の対応。

mc-pi.py（計算本体）と mc-pi-add-tasks.py（タスク投入）の両方から import し，
同じパラメータからは常に同じディレクトリが得られることを保証する。
"""

from src.runs import RunStore

# 結果に影響するパラメータのみをハッシュ対象にする（順序を変えると既存データのハッシュが変わる）
STORE = RunStore(
    experiment="mc-pi",
    param_types={
        "n_samples": int,
        "seed": int,
    },
)
