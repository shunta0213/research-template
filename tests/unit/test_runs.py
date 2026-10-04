import numpy as np
import pytest

from src.runs import INPUT_FILE, OUTPUT_FILE, RunStore, load_run, params_hash


@pytest.fixture
def store(tmp_path):
    return RunStore(experiment="dummy", param_types={"n": int, "x": float}, root=tmp_path)


def test_build_params_normalizes_types_and_order(store):
    params = store.build_params(x=1, n=2.0)
    assert list(params) == ["n", "x"]
    assert type(params["n"]) is int and type(params["x"]) is float


def test_build_params_rejects_missing_and_unknown(store):
    with pytest.raises(ValueError, match="missing"):
        store.build_params(n=1)
    with pytest.raises(ValueError, match="unknown"):
        store.build_params(n=1, x=1.0, y=0)


def test_same_params_give_same_run_dir(store):
    assert store.run_dir(store.build_params(n=1, x=0.5)) == store.run_dir(store.build_params(x=0.5, n=1))
    assert store.run_dir(store.build_params(n=1, x=0.5)) != store.run_dir(store.build_params(n=2, x=0.5))


def test_params_hash_supports_arrays():
    params = {"W": np.eye(3)}
    assert params_hash(params) == params_hash({"W": np.eye(3)})
    assert params_hash(params) != params_hash({"W": 2 * np.eye(3)})


def test_run_is_done_only_after_output(store):
    params = store.build_params(n=3, x=0.1)
    run_dir = store.save_input(params, note="recorded only")
    assert (run_dir / INPUT_FILE).exists()
    assert not store.is_done(params)
    assert load_run(run_dir) is None

    store.save_output(params, value=np.arange(3))
    assert (run_dir / OUTPUT_FILE).exists()
    assert store.is_done(params)


def test_load_run_merges_input_and_output(store):
    params = store.build_params(n=3, x=0.1)
    run_dir = store.save_input(params, note="recorded only")
    store.save_output(params, value=np.arange(3), score=1.5)

    row = load_run(run_dir)
    assert row["run_dir"] == run_dir.name
    assert row["params_hash"] == run_dir.name
    assert row["n"] == 3 and row["x"] == 0.1 and row["note"] == "recorded only"
    assert row["score"] == 1.5 and isinstance(row["score"], float)
    np.testing.assert_array_equal(row["value"], np.arange(3))
    assert "git_commit" in row and "started_at" in row
