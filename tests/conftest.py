from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).resolve().parent


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """tests/unit/ と tests/e2e/ 以下のテストに，ディレクトリ名と同じマーカーを自動で付ける。

    `uv run pytest -m unit` のように種類を絞って実行できる。
    """
    for item in items:
        suite = Path(item.fspath).resolve().relative_to(TESTS_DIR).parts[0]
        if suite in ("unit", "e2e"):
            item.add_marker(getattr(pytest.mark, suite))
