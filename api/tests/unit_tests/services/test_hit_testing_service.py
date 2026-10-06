"""Unit tests for the database-independent hit-testing helpers."""

from dataclasses import replace
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from core.rag.embedding.retrieval import RetrievalSegments
from models.dataset import DocumentSegment
from services.hit_testing_service import HitTestingService


@pytest.fixture
def signed_segment(monkeypatch: pytest.MonkeyPatch) -> DocumentSegment:
    monkeypatch.setattr("models.dataset.dify_config", SimpleNamespace(SECRET_KEY="ippr-unit-key"))
    monkeypatch.setattr("models.dataset.time.time", lambda: 1_700_000_000)
    monkeypatch.setattr("models.dataset.os.urandom", lambda _: b"\x01" * 16)
    segment = DocumentSegment(
        tenant_id="00000000-0000-0000-0000-000000000001",
        dataset_id="00000000-0000-0000-0000-000000000002",
        document_id="00000000-0000-0000-0000-000000000003",
        position=1,
        content="![image](/files/00000000-0000-0000-0000-000000000004/file-preview)",
        word_count=1,
        tokens=2,
        created_by="00000000-0000-0000-0000-000000000005",
    )
    segment.created_at = datetime(2023, 11, 14)
    return segment


class TestSignedRetrievalRecords:
    def test_real_conversion_preserves_records_and_refreshes_presentation(self, signed_segment, monkeypatch):
        record = RetrievalSegments(segment=signed_segment, score=0.8, summary="summary")
        original = record.model_dump()
        session = Mock()
        document = SimpleNamespace(
            id=signed_segment.document_id,
            data_source_type="upload_file",
            name="synthetic.md",
            doc_type="text",
            doc_metadata={"source": "synthetic"},
        )
        session.scalars.return_value.all.return_value = [document]
        signer = Mock(wraps=signed_segment.get_sign_content)
        monkeypatch.setattr(signed_segment, "get_sign_content", signer)
        original_dump = RetrievalSegments.model_dump
        dump = Mock(side_effect=original_dump)
        monkeypatch.setattr(RetrievalSegments, "model_dump", lambda self: dump(self))

        first = HitTestingService._dump_retrieval_records(session, [record])[0]
        monkeypatch.setattr("models.dataset.time.time", lambda: 1_700_000_001)
        monkeypatch.setattr("models.dataset.os.urandom", lambda _: b"\x02" * 16)
        second = HitTestingService._dump_retrieval_records(session, [record])[0]

        assert signer.call_count == 2
        assert dump.call_count == 2
        assert original_dump(record) == original
        assert first["segment"]["content"] == signed_segment.content
        assert second["segment"]["content"] == signed_segment.content
        assert first["segment"]["sign_content"] != second["segment"]["sign_content"]
        assert "timestamp=1700000000" in first["segment"]["sign_content"]
        assert "timestamp=1700000001" in second["segment"]["sign_content"]
        assert first["segment"]["created_at"] == signed_segment.created_at
        assert first["segment"]["document"] == HitTestingService._dump_dataset_document(document)
        assert {key: first[key] for key in original if key != "segment"} == {
            key: original[key] for key in original if key != "segment"
        }
        assert session.scalars.call_count == 2
        session.get.assert_not_called()
        session.execute.assert_not_called()

    @pytest.mark.parametrize("document_id", ["", None, 123])
    @pytest.mark.parametrize("with_document", [False, True])
    def test_invalid_document_id_fallback_is_signed(self, signed_segment, monkeypatch, document_id, with_document):
        valid = RetrievalSegments(segment=signed_segment, score=0.9)
        fallback_segment = DocumentSegment(
            tenant_id=signed_segment.tenant_id,
            dataset_id=signed_segment.dataset_id,
            document_id="",
            position=2,
            content=signed_segment.content,
            word_count=1,
            tokens=2,
            created_by=signed_segment.created_by,
        )
        monkeypatch.setattr(fallback_segment, "document_id", document_id)
        fallback = RetrievalSegments(segment=fallback_segment, score=0.7)
        session = Mock()
        session.scalars.return_value.all.return_value = [
            SimpleNamespace(
                id=signed_segment.document_id,
                data_source_type="upload_file",
                name="test",
                doc_type=None,
                doc_metadata=None,
            )
        ]
        signer = Mock(wraps=fallback_segment.get_sign_content)
        monkeypatch.setattr(fallback_segment, "get_sign_content", signer)

        result = HitTestingService._dump_retrieval_records(session, [valid, fallback] if with_document else [fallback])

        assert result[-1]["segment"]["sign_content"] == signed_segment.get_sign_content()
        assert result[-1]["segment"]["content"] == fallback_segment.content
        assert "document" not in result[-1]["segment"]
        signer.assert_called_once_with()
        assert session.scalars.call_count == int(with_document)

    def test_missing_documents_skip_before_signing_and_keep_batch_order(self, signed_segment, monkeypatch, caplog):
        session = Mock()
        session.scalars.return_value.all.return_value = []
        signer = Mock(wraps=signed_segment.get_sign_content)
        monkeypatch.setattr(signed_segment, "get_sign_content", signer)
        record = RetrievalSegments(segment=signed_segment, score=0.8)

        assert HitTestingService._dump_retrieval_records(session, [record, record]) == []
        signer.assert_not_called()
        session.scalars.assert_called_once()
        assert caplog.text.count("Skipping hit-testing records with missing documents") == 1
        assert signed_segment.document_id in caplog.text

        session.scalars.return_value.all.return_value = [
            SimpleNamespace(
                id=signed_segment.document_id,
                data_source_type="upload_file",
                name="test",
                doc_type=None,
                doc_metadata=None,
            )
        ]
        other = RetrievalSegments(segment=signed_segment, score=0.6)
        missing_segment = replace(signed_segment, document_id="00000000-0000-0000-0000-000000000006")
        missing_signer = Mock(wraps=missing_segment.get_sign_content)
        monkeypatch.setattr(missing_segment, "get_sign_content", missing_signer)
        missing = RetrievalSegments(segment=missing_segment, score=0.1)
        nullable = SimpleNamespace(segment=None, model_dump=Mock(return_value={"segment": None, "score": 0.2}))
        result = HitTestingService._dump_retrieval_records(session, [record, nullable, missing, other, record])
        assert [item["score"] for item in result] == [0.8, 0.2, 0.6, 0.8]
        assert signer.call_count == 3
        missing_signer.assert_not_called()
        nullable.model_dump.assert_called_once_with()
        assert session.scalars.call_count == 2
        assert set(session.scalars.call_args.args[0].compile().params["id_1"]) == {
            signed_segment.document_id,
            missing_segment.document_id,
        }

    def test_empty_and_nullable_segment_fallback(self):
        session = Mock()
        assert HitTestingService._dump_retrieval_records(session, []) == []
        nullable = SimpleNamespace(segment=None, model_dump=Mock(return_value={"segment": None, "score": 0.2}))
        assert HitTestingService._dump_retrieval_records(session, [nullable]) == [{"segment": None, "score": 0.2}]
        nullable.model_dump.assert_called_once_with()
        session.scalars.assert_not_called()


class TestHitTestingServiceArguments:
    def test_escape_query_for_search_should_escape_double_quotes(self) -> None:
        query = 'test "query" with quotes'

        result = HitTestingService.escape_query_for_search(query)

        assert result == 'test \\"query\\" with quotes'

    def test_hit_testing_args_check_should_pass_with_valid_query(self) -> None:
        HitTestingService.hit_testing_args_check({"query": "valid query"})

    def test_hit_testing_args_check_should_pass_with_valid_attachments(self) -> None:
        HitTestingService.hit_testing_args_check({"attachment_ids": ["id1", "id2"]})

    def test_hit_testing_args_check_should_raise_error_when_no_query_or_attachments(self) -> None:
        with pytest.raises(ValueError, match="Query or attachment_ids is required"):
            HitTestingService.hit_testing_args_check({})

    def test_hit_testing_args_check_should_raise_error_when_query_too_long(self) -> None:
        with pytest.raises(ValueError, match="Query cannot exceed 250 characters"):
            HitTestingService.hit_testing_args_check({"query": "a" * 251})

    def test_hit_testing_args_check_should_raise_error_when_attachments_not_list(self) -> None:
        with pytest.raises(ValueError, match="Attachment_ids must be a list"):
            HitTestingService.hit_testing_args_check({"attachment_ids": "not a list"})
