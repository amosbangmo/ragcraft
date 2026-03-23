from infrastructure.persistence.caching.process_project_chain_cache import ProcessProjectChainCache


def test_drop_removes_key() -> None:
    c = ProcessProjectChainCache()
    c.set("p1", object())
    c.drop("p1")
    assert c.get("p1") is None
