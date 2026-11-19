import pytest


def pytest_collection_modifyitems(items):
    """Marca cada teste pelo nível (unit/integration/system) conforme a pasta."""
    for item in items:
        caminho = str(item.fspath).replace("\\", "/")
        for nivel in ("unit", "integration", "system"):
            if f"/tests/{nivel}/" in caminho:
                item.add_marker(getattr(pytest.mark, nivel))
