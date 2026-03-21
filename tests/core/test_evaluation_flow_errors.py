from src.core.evaluation_flow_errors import map_evaluation_flow_exception
from src.core.exceptions import DocStoreError, LLMServiceError, VectorStoreError


def test_map_plain_exception_uses_default_with_flow_context():
    msg = map_evaluation_flow_exception(RuntimeError("x"), dataset_evaluation=False)
    assert "manual evaluation" in msg.lower()

    msg_ds = map_evaluation_flow_exception(RuntimeError("x"), dataset_evaluation=True)
    assert "dataset evaluation" in msg_ds.lower()


def test_map_ragcraft_errors_use_user_message():
    exc = VectorStoreError("internal", user_message="vector down")
    assert map_evaluation_flow_exception(exc, dataset_evaluation=False) == "vector down"

    exc2 = DocStoreError("internal", user_message="sqlite down")
    assert map_evaluation_flow_exception(exc2, dataset_evaluation=True) == "sqlite down"


def test_map_llm_service_error():
    exc = LLMServiceError("internal", user_message="model timeout")
    assert map_evaluation_flow_exception(exc, dataset_evaluation=False) == "model timeout"
