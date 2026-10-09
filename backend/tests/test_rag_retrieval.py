"""RAG retrieval with in-memory fakes; no Chroma store or network access."""

from types import SimpleNamespace

import pytest
import chromadb

from app.exceptions import RAGUnavailableException
from app.services import rag_service as rag


def result(*, distance=0.2, metadata=None):
    return {
        "ids": [["document:0"]],
        "documents": [["Quy định học bổng"]],
        "metadatas": [[metadata or {"document_id": "document", "filename": "Sổ tay.pdf", "page_number": 3}]],
        "distances": [[distance]],
    }


def setup_collection(monkeypatch, *, count=1, response=None, query_error=None):
    calls = []

    def query(**kwargs):
        calls.append(kwargs)
        if query_error:
            raise query_error
        return result() if response is None else response

    collection = SimpleNamespace(count=lambda: count, query=query)
    monkeypatch.setattr(rag, "RAG_ENABLED", True)
    monkeypatch.setattr(rag, "_collection", lambda: collection)
    monkeypatch.setattr(rag, "_embed", lambda texts: [[0.1, 0.2]])
    return calls


def test_disabled_does_not_open_collection_or_embed(monkeypatch):
    monkeypatch.setattr(rag, "RAG_ENABLED", False)
    monkeypatch.setattr(rag, "_collection", lambda: pytest.fail("opened collection"))
    monkeypatch.setattr(rag, "_embed", lambda texts: pytest.fail("called embedding"))
    assert rag.retrieve("Xin chào") == []


def test_empty_collection_skips_embedding_and_query(monkeypatch):
    setup_collection(monkeypatch, count=0)
    monkeypatch.setattr(rag, "_embed", lambda texts: pytest.fail("called embedding"))
    assert rag.retrieve("Học bổng?") == []


def test_success_preserves_vietnamese_query_and_metadata(monkeypatch):
    calls = setup_collection(monkeypatch)
    seen = []
    monkeypatch.setattr(rag, "_embed", lambda texts: seen.extend(texts) or [[0.1, 0.2]])
    chunks = rag.retrieve("Điều kiện học bổng là gì?")
    assert seen == ["Điều kiện học bổng là gì?"]
    assert calls[0]["n_results"] == rag.RAG_TOP_K
    assert [(c.document_id, c.filename, c.page_number, c.text) for c in chunks] == [
        ("document", "Sổ tay.pdf", 3, "Quy định học bổng")
    ]
    prompt = rag.prompt_context(chunks)
    assert "Sổ tay.pdf, trang 3" in prompt
    assert "Quy định học bổng" in prompt


def test_below_threshold_is_normal_empty_result(monkeypatch):
    setup_collection(monkeypatch, response=result(distance=0.9))
    assert rag.retrieve("Chuyện khác") == []
    assert rag.prompt_context([]) is None


@pytest.mark.parametrize("problem", [TimeoutError("timeout"), RuntimeError("embedding unavailable")])
def test_embedding_failure_is_controlled(monkeypatch, problem):
    setup_collection(monkeypatch)

    def fail(_):
        raise RAGUnavailableException(category="embedding") from problem

    monkeypatch.setattr(rag, "_embed", fail)
    with pytest.raises(RAGUnavailableException) as caught:
        rag.retrieve("Câu hỏi")
    assert caught.value.category == "embedding"


def test_collection_open_failure_is_controlled(monkeypatch):
    monkeypatch.setattr(rag, "RAG_ENABLED", True)
    monkeypatch.setattr(rag, "_collection", lambda: (_ for _ in ()).throw(RAGUnavailableException(category="collection_open")))
    with pytest.raises(RAGUnavailableException) as caught:
        rag.retrieve("Câu hỏi")
    assert caught.value.category == "collection_open"


def test_count_failure_is_controlled(monkeypatch):
    monkeypatch.setattr(rag, "RAG_ENABLED", True)
    monkeypatch.setattr(rag, "_collection", lambda: SimpleNamespace(count=lambda: (_ for _ in ()).throw(RuntimeError("private details"))))
    with pytest.raises(RAGUnavailableException) as caught:
        rag.retrieve("Câu hỏi")
    assert caught.value.category == "collection_count"
    assert "private details" not in str(caught.value)


@pytest.mark.parametrize("problem", [RuntimeError("query failed"), ValueError("dimension mismatch")])
def test_query_failure_and_dimension_mismatch_are_controlled(monkeypatch, problem):
    setup_collection(monkeypatch, query_error=problem)
    with pytest.raises(RAGUnavailableException) as caught:
        rag.retrieve("Câu hỏi")
    assert caught.value.category == "collection_query"


@pytest.mark.parametrize(
    "response",
    [
        {},
        {"ids": [], "documents": [], "metadatas": [], "distances": []},
        {"ids": [[]], "documents": [[]], "metadatas": [[]]},
        {"ids": [["x"]], "documents": [[]], "metadatas": [[]], "distances": [[]]},
        result(metadata={"document_id": "document", "filename": "Sổ tay.pdf"}),
        result(metadata={"document_id": "document", "filename": "Sổ tay.pdf", "page_number": "three"}),
        result(distance=float("nan")),
        result(distance="not-a-number"),
    ],
)
def test_malformed_results_are_controlled(monkeypatch, response):
    setup_collection(monkeypatch, response=response)
    with pytest.raises(RAGUnavailableException) as caught:
        rag.retrieve("Câu hỏi")
    assert caught.value.category == "invalid_result"


def test_valid_empty_result_arrays_are_not_an_error(monkeypatch):
    setup_collection(monkeypatch, response={"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]})
    assert rag.retrieve("Câu hỏi") == []


def test_missing_key_is_controlled_without_network(monkeypatch):
    monkeypatch.setattr(rag, "RAG_ENABLED", True)
    monkeypatch.setattr(rag, "embedding_client", None)
    with pytest.raises(RAGUnavailableException) as caught:
        rag._collection()
    assert caught.value.category == "missing_key"


def test_collection_open_error_is_wrapped_without_raw_detail(monkeypatch):
    monkeypatch.setattr(rag, "RAG_ENABLED", True)
    monkeypatch.setattr(rag, "embedding_client", object())
    monkeypatch.setattr(chromadb, "PersistentClient", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("sensitive collection detail")))
    with pytest.raises(RAGUnavailableException) as caught:
        rag._collection()
    assert caught.value.category == "collection_open"
    assert "sensitive collection detail" not in str(caught.value)


@pytest.mark.parametrize("problem", [TimeoutError("embedding timed out"), RuntimeError("provider unavailable")])
def test_embed_provider_error_is_wrapped_without_network(monkeypatch, problem):
    fake_models = SimpleNamespace(embed_content=lambda **kwargs: (_ for _ in ()).throw(problem))
    monkeypatch.setattr(rag, "embedding_client", SimpleNamespace(models=fake_models))
    with pytest.raises(RAGUnavailableException) as caught:
        rag._embed(["Câu hỏi tiếng Việt"])
    assert caught.value.category == "embedding"
    assert str(problem) not in str(caught.value)
