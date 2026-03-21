"""
Pytest-only hooks. (``unittest discover`` per folder is unaffected.)

Smoke tests replace entire ``sys.modules`` entries; they must run last so other
test modules are not imported while stubs are installed.
"""


def pytest_collection_modifyitems(config, items):
    smoke = [i for i in items if "test_smoke_upload_ingest_ask" in i.nodeid]
    if not smoke:
        return
    rest = [i for i in items if i not in smoke]
    items[:] = rest + smoke
