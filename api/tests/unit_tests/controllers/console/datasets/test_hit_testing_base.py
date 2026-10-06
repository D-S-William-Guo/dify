import base64
import hashlib
import hmac
from copy import deepcopy
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch
from urllib.parse import parse_qs, urlsplit
from uuid import UUID

import pytest
from flask import Flask
from pydantic import ValidationError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import operators, visitors
from sqlalchemy.sql.elements import BinaryExpression, Null
from werkzeug.exceptions import Forbidden, InternalServerError, NotFound, Unauthorized

import services
from controllers.console.app.error import (
    CompletionRequestError,
    ProviderModelCurrentlyNotSupportError,
    ProviderNotInitializeError,
    ProviderQuotaExceededError,
)
from controllers.console.datasets.error import DatasetNotInitializedError
from controllers.console.datasets.hit_testing_base import (
    DatasetsHitTestingBase,
)
from controllers.files import image_preview
from controllers.service_api import wraps as service_api_wraps
from core.app.file_access import DatabaseFileAccessController
from core.app.workflow.file_runtime import DifyWorkflowFileRuntime
from core.errors.error import (
    LLMBadRequestError,
    ModelCurrentlyNotSupportError,
    ProviderTokenNotInitError,
    QuotaExceededError,
)
from core.rag.embedding.retrieval import RetrievalSegments
from fields.hit_testing_fields import HitTestingResponse
from graphon.model_runtime.errors.invoke import InvokeError
from models.account import Account, Tenant, TenantAccountRole
from models.dataset import Dataset, DatasetPermission, DatasetPermissionEnum, DocumentSegment
from models.model import ApiToken
from services import api_token_service, file_service
from services.dataset_service import DatasetService
from services.file_service import FileService
from services.hit_testing_service import HitTestingService


@pytest.fixture
def account():
    acc = Account(name="User", email="user@example.com")
    acc.id = "account-1"
    tenant = Tenant(name="Tenant")
    tenant.id = "tenant-1"
    acc._current_tenant = tenant
    acc.role = TenantAccountRole.OWNER
    return acc


@pytest.fixture
def dataset():
    return Dataset(id="dataset-1", tenant_id="tenant-1", name="Dataset", created_by="account-1")


def hit_testing_record() -> dict[str, object]:
    return {
        "segment": {
            "id": "segment-1",
            "position": 1,
            "document_id": "document-1",
            "content": "Chunk text",
            "answer": None,
            "word_count": 2,
            "tokens": 3,
            "keywords": None,
            "index_node_id": None,
            "index_node_hash": None,
            "hit_count": 0,
            "enabled": True,
            "disabled_at": None,
            "disabled_by": None,
            "status": "completed",
            "created_by": "account-1",
            "created_at": 1_700_000_000,
            "indexing_at": None,
            "completed_at": None,
            "error": None,
            "stopped_at": None,
            "document": {
                "id": "document-1",
                "data_source_type": "upload_file",
                "name": "guide.md",
                "doc_type": None,
                "doc_metadata": None,
            },
        },
        "child_chunks": None,
        "files": None,
        "score": 0.8,
    }


class TestGetAndValidateDataset:
    def test_success(self, dataset, account):
        with (
            patch.object(
                DatasetService,
                "get_dataset",
                return_value=dataset,
            ),
            patch.object(
                DatasetService,
                "check_dataset_permission",
            ),
        ):
            result = DatasetsHitTestingBase.get_and_validate_dataset(Mock(), "dataset-1", account, "tenant-1")

        assert result == dataset

    def test_dataset_not_found(self, account):
        with patch.object(
            DatasetService,
            "get_dataset",
            return_value=None,
        ):
            with pytest.raises(NotFound, match="Dataset not found"):
                DatasetsHitTestingBase.get_and_validate_dataset(Mock(), "dataset-1", account, "tenant-1")

    def test_permission_denied(self, dataset, account):
        with (
            patch.object(
                DatasetService,
                "get_dataset",
                return_value=dataset,
            ),
            patch.object(
                DatasetService,
                "check_dataset_permission",
                side_effect=services.errors.account.NoPermissionError("no access"),
            ),
        ):
            with pytest.raises(Forbidden, match="no access"):
                DatasetsHitTestingBase.get_and_validate_dataset(Mock(), "dataset-1", account, "tenant-1")


class TestHitTestingArgsCheck:
    def test_args_check_called(self):
        args = {"query": "test"}

        with patch.object(
            HitTestingService,
            "hit_testing_args_check",
        ) as check_mock:
            DatasetsHitTestingBase.hit_testing_args_check(args)

        check_mock.assert_called_once_with(args)


class TestParseArgs:
    def test_parse_args_success(self):
        payload = {"query": "hello"}

        result = DatasetsHitTestingBase.parse_args(payload)

        assert result["query"] == "hello"

    def test_parse_args_invalid(self):
        payload = {"query": "x" * 300}

        with pytest.raises(ValueError):
            DatasetsHitTestingBase.parse_args(payload)

    def test_parse_args_ignores_unknown_fields_for_compatibility(self):
        payload = {"query": "hello", "top_k": 3}

        result = DatasetsHitTestingBase.parse_args(payload)

        assert result == {"query": "hello"}


class TestPerformHitTesting:
    def test_success(self, dataset, account):
        response = {
            "query": {"content": "hello"},
            "records": [],
        }

        with patch.object(
            HitTestingService,
            "retrieve",
            return_value=response,
        ):
            result = DatasetsHitTestingBase.perform_hit_testing(
                Mock(), dataset, {"query": "hello"}, account, "tenant-1"
            )

        assert result["query"] == {"content": "hello"}
        assert result["records"] == []

    def test_success_prepares_nullable_list_fields(self, dataset, account):
        response = {
            "query": {"content": "hello"},
            "records": [hit_testing_record()],
        }

        with patch.object(
            HitTestingService,
            "retrieve",
            return_value=response,
        ):
            result = DatasetsHitTestingBase.perform_hit_testing(
                Mock(), dataset, {"query": "hello"}, account, "tenant-1"
            )

        assert result["query"] == {"content": "hello"}
        record = result["records"][0]
        assert record["segment"]["keywords"] == []
        assert record["segment"]["sign_content"] is None
        assert record["child_chunks"] == []
        assert record["files"] == []
        assert record["score"] == 0.8
        assert record["tsne_position"] is None
        assert record["summary"] is None

    def test_invalid_query_response_raises_value_error(self, dataset, account):
        with (
            patch.object(
                HitTestingService,
                "retrieve",
                return_value={"query": "hello", "records": []},
            ),
            pytest.raises(ValueError, match="Invalid hit testing query response"),
        ):
            DatasetsHitTestingBase.perform_hit_testing(Mock(), dataset, {"query": "hello"}, account, "tenant-1")

    def test_invalid_records_response_raises_value_error(self):
        with pytest.raises(ValueError, match="Invalid hit testing records response"):
            DatasetsHitTestingBase._prepare_hit_testing_records({"records": []})

    def test_invalid_record_response_raises_value_error(self):
        with pytest.raises(ValueError, match="Invalid hit testing record response"):
            DatasetsHitTestingBase._prepare_hit_testing_records(["record"])

    def test_index_not_initialized(self, dataset, account):
        with patch.object(
            HitTestingService,
            "retrieve",
            side_effect=services.errors.index.IndexNotInitializedError(),
        ):
            with pytest.raises(DatasetNotInitializedError):
                DatasetsHitTestingBase.perform_hit_testing(Mock(), dataset, {"query": "hello"}, account, "tenant-1")

    def test_provider_token_not_init(self, dataset, account):
        with patch.object(
            HitTestingService,
            "retrieve",
            side_effect=ProviderTokenNotInitError("token missing"),
        ):
            with pytest.raises(ProviderNotInitializeError):
                DatasetsHitTestingBase.perform_hit_testing(Mock(), dataset, {"query": "hello"}, account, "tenant-1")

    def test_quota_exceeded(self, dataset, account):
        with patch.object(
            HitTestingService,
            "retrieve",
            side_effect=QuotaExceededError(),
        ):
            with pytest.raises(ProviderQuotaExceededError):
                DatasetsHitTestingBase.perform_hit_testing(Mock(), dataset, {"query": "hello"}, account, "tenant-1")

    def test_model_not_supported(self, dataset, account):
        with patch.object(
            HitTestingService,
            "retrieve",
            side_effect=ModelCurrentlyNotSupportError(),
        ):
            with pytest.raises(ProviderModelCurrentlyNotSupportError):
                DatasetsHitTestingBase.perform_hit_testing(Mock(), dataset, {"query": "hello"}, account, "tenant-1")

    def test_llm_bad_request(self, dataset, account):
        with patch.object(
            HitTestingService,
            "retrieve",
            side_effect=LLMBadRequestError("bad request"),
        ):
            with pytest.raises(ProviderNotInitializeError):
                DatasetsHitTestingBase.perform_hit_testing(Mock(), dataset, {"query": "hello"}, account, "tenant-1")

    def test_invoke_error(self, dataset, account):
        with patch.object(
            HitTestingService,
            "retrieve",
            side_effect=InvokeError("invoke failed"),
        ):
            with pytest.raises(CompletionRequestError):
                DatasetsHitTestingBase.perform_hit_testing(Mock(), dataset, {"query": "hello"}, account, "tenant-1")

    def test_value_error(self, dataset, account):
        with patch.object(
            HitTestingService,
            "retrieve",
            side_effect=ValueError("bad args"),
        ):
            with pytest.raises(ValueError, match="bad args"):
                DatasetsHitTestingBase.perform_hit_testing(Mock(), dataset, {"query": "hello"}, account, "tenant-1")

    def test_unexpected_error(self, dataset, account):
        with patch.object(
            HitTestingService,
            "retrieve",
            side_effect=Exception("boom"),
        ):
            with pytest.raises(InternalServerError, match="boom"):
                DatasetsHitTestingBase.perform_hit_testing(Mock(), dataset, {"query": "hello"}, account, "tenant-1")


SYNTHETIC_TENANT_ID = "00000000-0000-0000-0000-000000000001"
SYNTHETIC_DATASET_ID = "00000000-0000-0000-0000-000000000002"
SYNTHETIC_DOCUMENT_ID = "00000000-0000-0000-0000-000000000003"
SYNTHETIC_FILE_ID = "00000000-0000-0000-0000-000000000004"
SYNTHETIC_ACCOUNT_ID = "00000000-0000-0000-0000-000000000005"
OTHER_SYNTHETIC_ID = "00000000-0000-0000-0000-000000000006"
PREVIEW_FAILURES = ["id", "domain", "sign", "nonce", "timestamp", "expired"]


def synthetic_preview_segment(content: str) -> DocumentSegment:
    segment = DocumentSegment(
        tenant_id=SYNTHETIC_TENANT_ID,
        dataset_id=SYNTHETIC_DATASET_ID,
        document_id=SYNTHETIC_DOCUMENT_ID,
        position=1,
        content=content,
        word_count=1,
        tokens=2,
        created_by=SYNTHETIC_ACCOUNT_ID,
    )
    segment.created_at = datetime(2023, 11, 14, tzinfo=UTC)
    return segment


@pytest.fixture
def preview_runtime(monkeypatch: pytest.MonkeyPatch) -> DifyWorkflowFileRuntime:
    config = SimpleNamespace(SECRET_KEY="ippr-unit-key", FILES_ACCESS_TIMEOUT=60)
    monkeypatch.setattr("models.dataset.dify_config", config)
    monkeypatch.setattr("core.app.workflow.file_runtime.dify_config", config)
    # Both modules share stdlib time; generate before advancing the verification clock.
    monkeypatch.setattr("models.dataset.time.time", lambda: 1_700_000_000)
    monkeypatch.setattr("core.app.workflow.file_runtime.time.time", lambda: 1_700_000_000)
    monkeypatch.setattr("models.dataset.os.urandom", lambda _: b"\x01" * 16)
    return DifyWorkflowFileRuntime(file_access_controller=DatabaseFileAccessController())


def generated_preview_parameters(kind: str, prefix: str = "") -> dict[str, str]:
    url = f"{prefix}/files/{SYNTHETIC_FILE_ID}/{kind}-preview"
    signed = synthetic_preview_segment(url).get_sign_content()
    parsed = urlsplit(signed)
    assert parsed.path == f"/files/{SYNTHETIC_FILE_ID}/{kind}-preview"
    assert parsed.netloc == urlsplit(prefix).netloc
    assert signed.count("?") == 1
    parameters = parse_qs(parsed.query)
    assert set(parameters) == {"timestamp", "nonce", "sign"}
    assert all(len(values) == 1 for values in parameters.values())
    return {key: values[0] for key, values in parameters.items()}


def invalid_preview_parameters(kind: str, parameters: dict[str, str], variant: str) -> tuple[str, dict[str, str]]:
    modified = dict(parameters)
    file_id = SYNTHETIC_FILE_ID
    if variant == "id":
        file_id = OTHER_SYNTHETIC_ID
    elif variant == "domain":
        modified = generated_preview_parameters("file" if kind == "image" else "image")
    elif variant == "sign":
        modified["sign"] = ("A" if modified["sign"][0] != "A" else "B") + modified["sign"][1:]
    elif variant == "nonce":
        modified["nonce"] = "02" * 16
    elif variant == "timestamp":
        modified["timestamp"] = "1700000001"
    return file_id, modified


class TestUploadPreviewSecurity:
    @pytest.mark.parametrize(
        ("handler", "model"),
        [
            (image_preview.ImagePreviewApi, image_preview.FileSignatureQuery),
            (image_preview.FilePreviewApi, image_preview.FilePreviewQuery),
        ],
    )
    @pytest.mark.parametrize("missing", ["timestamp", "nonce", "sign"])
    def test_each_missing_preview_field_stops_before_file_service(self, monkeypatch, handler, model, missing):
        parameters = {"timestamp": "1700000000", "nonce": "01" * 16, "sign": "synthetic"}
        del parameters[missing]
        service = Mock()
        monkeypatch.setattr(image_preview, "FileService", service)
        monkeypatch.setattr(image_preview, "db", SimpleNamespace(engine=object()))
        with Flask(__name__).test_request_context(query_string=parameters), pytest.raises(ValidationError) as error:
            handler().get(UUID(SYNTHETIC_FILE_ID))
        assert error.value.title == model.__name__
        assert [(item["type"], item["loc"]) for item in error.value.errors()] == [("missing", (missing,))]
        service.assert_not_called()

    @pytest.mark.parametrize("kind", ["image", "file"])
    @pytest.mark.parametrize("prefix", ["", "https://docs.example.test"])
    def test_generated_preview_parameters_pass_real_verifier(self, preview_runtime, monkeypatch, kind, prefix):
        parameters = generated_preview_parameters(kind, prefix)
        payload = f"{kind}-preview|{SYNTHETIC_FILE_ID}|{parameters['timestamp']}|{parameters['nonce']}"
        expected = base64.urlsafe_b64encode(hmac.new(b"ippr-unit-key", payload.encode(), hashlib.sha256).digest())
        assert parameters["sign"] == expected.decode()
        assert preview_runtime.verify_preview_signature(preview_kind=kind, file_id=SYNTHETIC_FILE_ID, **parameters)
        monkeypatch.setattr("core.app.workflow.file_runtime.time.time", lambda: 1_700_000_060)
        assert preview_runtime.verify_preview_signature(preview_kind=kind, file_id=SYNTHETIC_FILE_ID, **parameters)

    @pytest.mark.parametrize("kind", ["image", "file"])
    @pytest.mark.parametrize("variant", PREVIEW_FAILURES)
    def test_generated_preview_parameters_reject_wrong_id_domain_tampering_and_expiry(
        self, preview_runtime, monkeypatch, kind, variant
    ):
        parameters = generated_preview_parameters(kind)
        verify_kind = kind
        if variant == "domain":
            verify_kind = "file" if kind == "image" else "image"
        file_id, parameters = invalid_preview_parameters(kind, parameters, variant if variant != "domain" else "fresh")
        if variant == "expired":
            monkeypatch.setattr("core.app.workflow.file_runtime.time.time", lambda: 1_700_000_061)
        assert not preview_runtime.verify_preview_signature(preview_kind=verify_kind, file_id=file_id, **parameters)

    @pytest.mark.parametrize("kind", ["image", "file"])
    @pytest.mark.parametrize("variant", PREVIEW_FAILURES + ["fresh"])
    def test_invalid_preview_verification_stops_before_sql_and_storage(
        self, preview_runtime, monkeypatch, kind, variant
    ):
        parameters = generated_preview_parameters(kind)
        file_id, parameters = invalid_preview_parameters(kind, parameters, variant)
        if variant == "expired":
            monkeypatch.setattr("core.app.workflow.file_runtime.time.time", lambda: 1_700_000_061)

        def verify(*, upload_file_id: str, timestamp: str, nonce: str, sign: str) -> bool:
            return preview_runtime.verify_preview_signature(
                preview_kind=kind, file_id=upload_file_id, timestamp=timestamp, nonce=nonce, sign=sign
            )

        verifier = Mock(side_effect=verify)
        monkeypatch.setattr(file_service.file_helpers, f"verify_{kind}_signature", verifier)
        storage = Mock()
        monkeypatch.setattr(file_service, "storage", storage)
        maker = MagicMock(spec=sessionmaker)
        session = maker.return_value.__enter__.return_value
        session.scalar.return_value = None
        service = FileService(session_factory=maker)
        method = service.get_image_preview if kind == "image" else service.get_file_generator_by_file_id

        with pytest.raises(NotFound) as error:
            method(file_id=file_id, **parameters)

        assert error.value.code == 404
        verifier.assert_called_once_with(upload_file_id=file_id, **parameters)
        if variant == "fresh":
            maker.assert_called_once_with(expire_on_commit=False)
            session.scalar.assert_called_once()
        else:
            maker.assert_not_called()
            session.scalar.assert_not_called()
        session.execute.assert_not_called()
        storage.load.assert_not_called()


def assert_sql_predicate(statement, column, value: str | None) -> str | None:
    predicates = [
        node
        for node in visitors.iterate(statement.whereclause)
        if isinstance(node, BinaryExpression) and node.left.compare(column.__clause_element__())
    ]
    assert len(predicates) == 1
    predicate = predicates[0]
    if value is None:
        assert predicate.operator is operators.is_
        assert isinstance(predicate.right, Null)
    else:
        assert predicate.operator is operators.eq
        assert predicate.right.value == value
        assert value in statement.compile().params.values()
        return predicate.right.value
    return None


@pytest.fixture
def dataset_security(preview_runtime, monkeypatch) -> SimpleNamespace:
    tenant = Tenant(name="Synthetic tenant")
    tenant.id = SYNTHETIC_TENANT_ID
    actor = Account(name="Synthetic owner", email="owner@example.test")
    actor.id = SYNTHETIC_ACCOUNT_ID
    actor._current_tenant = tenant
    actor.role = TenantAccountRole.OWNER
    dataset = Dataset(
        id=SYNTHETIC_DATASET_ID,
        tenant_id=tenant.id,
        name="Synthetic dataset",
        created_by=actor.id,
        maintainer=OTHER_SYNTHETIC_ID,
        permission=DatasetPermissionEnum.ONLY_ME,
        enable_api=True,
    )
    session = MagicMock()
    session.return_value = session  # The real decorator calls db.session() for the tenant setter.
    state = SimpleNamespace(token_tenant=tenant.id, rows=[dataset], owner_join=True, owner_account=True)

    def scalar(statement):
        entity = statement.column_descriptions[0]["entity"]
        if entity is Dataset:
            selected_id = assert_sql_predicate(statement, Dataset.id, dataset.id)
            selected_tenant = assert_sql_predicate(statement, Dataset.tenant_id, state.token_tenant)
            return next((row for row in state.rows if row.id == selected_id and row.tenant_id == selected_tenant), None)
        assert entity is DatasetPermission
        assert_sql_predicate(statement, DatasetPermission.dataset_id, dataset.id)
        assert_sql_predicate(statement, DatasetPermission.account_id, actor.id)
        return None

    def get(model, row_id):
        if model is Account:
            assert row_id == actor.id
            return actor if state.owner_account else None
        assert model is Dataset
        assert row_id == dataset.id
        return next((row for row in state.rows if row.id == row_id), None)

    session.scalar.side_effect = scalar
    session.get.side_effect = get
    session.execute.return_value.one_or_none.side_effect = lambda: (
        (tenant, SimpleNamespace(account_id=actor.id)) if state.owner_join else None
    )
    session.scalars.return_value.all.return_value = [
        SimpleNamespace(
            id=SYNTHETIC_DOCUMENT_ID,
            data_source_type="upload_file",
            name="synthetic.md",
            doc_type=None,
            doc_metadata=None,
        )
    ]
    monkeypatch.setattr(service_api_wraps, "db", SimpleNamespace(session=session))
    cache = Mock(side_effect=lambda token, scope: SimpleNamespace(tenant_id=state.token_tenant, type="dataset"))
    monkeypatch.setattr(service_api_wraps.ApiTokenCache, "get", cache)
    usage = Mock()
    monkeypatch.setattr(service_api_wraps, "record_token_usage", usage)
    signal = Mock()
    monkeypatch.setattr(service_api_wraps.user_logged_in, "send", signal)

    def set_tenant(current_tenant: Tenant, *, session) -> None:
        actor._current_tenant = current_tenant
        actor.role = TenantAccountRole.OWNER

    monkeypatch.setattr(actor, "set_current_tenant_with_session", set_tenant)
    app = Flask(__name__)
    app.login_manager = Mock()
    segment = synthetic_preview_segment(f"![image](/files/{SYNTHETIC_FILE_ID}/file-preview)")
    record = RetrievalSegments(segment=segment, score=0.8)
    original = record.model_dump()
    original_dump = HitTestingService._dump_retrieval_records
    original_sign = DocumentSegment.get_sign_content
    dump = Mock(wraps=original_dump)
    monkeypatch.setattr(HitTestingService, "_dump_retrieval_records", dump)
    signer = Mock(side_effect=original_sign)
    monkeypatch.setattr(DocumentSegment, "get_sign_content", lambda self: signer(self))

    def retrieve(**kwargs):
        assert kwargs["dataset"] is dataset
        assert kwargs["account"] is actor
        assert kwargs["session"] is session
        state.dumped = HitTestingService._dump_retrieval_records(session, [record])
        state.dumped_snapshot = deepcopy(state.dumped)
        return {"query": {"content": "synthetic query"}, "records": state.dumped}

    retrieval = Mock(side_effect=retrieve)
    monkeypatch.setattr(HitTestingService, "retrieve", retrieval)

    def shared(tenant_id: str, dataset_id: str) -> HitTestingResponse:
        validated = DatasetsHitTestingBase.get_and_validate_dataset(session, dataset_id, actor, tenant_id)
        response = DatasetsHitTestingBase.perform_hit_testing(
            session, validated, {"query": "synthetic query"}, actor, tenant_id
        )
        return HitTestingResponse.model_validate(response)

    continuation = Mock(side_effect=shared)

    @service_api_wraps.validate_dataset_token
    def protected(tenant_id: str, dataset_id: str) -> HitTestingResponse:
        return continuation(tenant_id, dataset_id)

    return SimpleNamespace(
        app=app,
        session=session,
        actor=actor,
        dataset=dataset,
        state=state,
        cache=cache,
        usage=usage,
        retrieval=retrieval,
        dump=dump,
        signer=signer,
        continuation=continuation,
        protected=protected,
        shared=shared,
        segment=segment,
        record=record,
        original=original,
        runtime=preview_runtime,
    )


class TestDatasetAuthorizationSecurity:
    @staticmethod
    def assert_denied(fixture, before_continuation: bool = True) -> None:
        if before_continuation:
            fixture.continuation.assert_not_called()
        fixture.retrieval.assert_not_called()
        fixture.dump.assert_not_called()
        fixture.signer.assert_not_called()
        fixture.session.scalars.assert_not_called()

    @staticmethod
    def assert_signed_conversion(fixture, response: HitTestingResponse) -> None:
        fixture.retrieval.assert_called_once()
        fixture.dump.assert_called_once_with(fixture.session, [fixture.record])
        fixture.signer.assert_called_once_with(fixture.segment)
        assert fixture.record.model_dump() == fixture.original
        assert fixture.state.dumped == fixture.state.dumped_snapshot
        record = response.records[0]
        assert record.segment.content == fixture.segment.content
        assert record.segment.sign_content is not None
        parameters = parse_qs(urlsplit(record.segment.sign_content.split("(")[1].rstrip(")")).query)
        assert set(parameters) == {"timestamp", "nonce", "sign"}
        assert all(len(values) == 1 for values in parameters.values())
        assert fixture.runtime.verify_preview_signature(
            preview_kind="file", file_id=SYNTHETIC_FILE_ID, **{key: values[0] for key, values in parameters.items()}
        )
        assert record.segment.keywords == []
        assert record.child_chunks == record.files == []
        assert record.score == 0.8
        assert record.tsne_position is record.summary is None
        assert record.segment.created_at == 1_699_920_000
        assert record.segment.document.name == "synthetic.md"

    @pytest.mark.parametrize("variant", ["matching", "mismatched", "none", "absent"])
    def test_dataset_token_binds_dataset_and_token_tenant(self, dataset_security, variant):
        fixture = dataset_security
        if variant == "mismatched":
            fixture.state.token_tenant = OTHER_SYNTHETIC_ID
        elif variant == "none":
            fixture.state.token_tenant = None
        elif variant == "absent":
            fixture.state.rows = []
        with fixture.app.test_request_context(headers={"Authorization": "Bearer ippr-synthetic-token"}):
            if variant == "matching":
                response = fixture.protected(dataset_id=fixture.dataset.id)
                self.assert_signed_conversion(fixture, response)
                fixture.continuation.assert_called_once_with(SYNTHETIC_TENANT_ID, fixture.dataset.id)
            else:
                with pytest.raises(NotFound) as error:
                    fixture.protected(dataset_id=fixture.dataset.id)
                assert error.value.code == 404
                fixture.session.execute.assert_not_called()
                fixture.session.get.assert_not_called()
                self.assert_denied(fixture)
        fixture.cache.assert_called_once_with("ippr-synthetic-token", "dataset")
        fixture.session.scalar.assert_called_once()

    def test_api_disabled_dataset_stops_before_retrieval_and_signing(self, dataset_security):
        fixture = dataset_security
        fixture.dataset.enable_api = False
        with fixture.app.test_request_context(headers={"Authorization": "Bearer ippr-synthetic-token"}):
            with pytest.raises(Forbidden) as error:
                fixture.protected(dataset_id=fixture.dataset.id)
        assert error.value.code == 403
        fixture.session.execute.assert_not_called()
        fixture.session.get.assert_not_called()
        self.assert_denied(fixture)

    @pytest.mark.parametrize("header", [None, "malformed", "Basic synthetic", "Bearer invalid-synthetic-token"])
    def test_missing_or_invalid_dataset_token_stops_before_retrieval_and_signing(
        self, dataset_security, monkeypatch, header
    ):
        fixture = dataset_security
        fixture.cache.side_effect = None
        fixture.cache.return_value = None
        token_session = MagicMock()
        token_session.scalar.return_value = None
        maker = Mock(return_value=token_session)
        token_session.__enter__.return_value = token_session
        monkeypatch.setattr(api_token_service, "Session", maker)
        monkeypatch.setattr(api_token_service, "db", SimpleNamespace(engine=object()))
        cache_set = Mock()
        monkeypatch.setattr(api_token_service.ApiTokenCache, "set", cache_set)
        forward = Mock(side_effect=api_token_service.query_token_from_db)
        monkeypatch.setattr(service_api_wraps, "fetch_token_with_single_flight", forward)
        headers = {} if header is None else {"Authorization": header}
        with fixture.app.test_request_context(headers=headers), pytest.raises(Unauthorized) as error:
            fixture.protected(dataset_id=fixture.dataset.id)
        assert error.value.code == 401
        if header == "Bearer invalid-synthetic-token":
            fixture.cache.assert_called_once_with("invalid-synthetic-token", "dataset")
            forward.assert_called_once_with("invalid-synthetic-token", "dataset")
            statement = token_session.scalar.call_args.args[0]
            assert_sql_predicate(statement, ApiToken.token, "invalid-synthetic-token")
            assert_sql_predicate(statement, ApiToken.type, "dataset")
            cache_set.assert_called_once_with("invalid-synthetic-token", "dataset", None)
        else:
            fixture.cache.assert_not_called()
            forward.assert_not_called()
            token_session.scalar.assert_not_called()
        fixture.usage.assert_not_called()
        fixture.session.scalar.assert_not_called()
        fixture.session.execute.assert_not_called()
        fixture.session.get.assert_not_called()
        self.assert_denied(fixture)

    @pytest.mark.parametrize("missing", ["owner_join", "owner_account"])
    def test_missing_tenant_owner_or_account_retains_unauthorized(self, dataset_security, missing):
        fixture = dataset_security
        setattr(fixture.state, missing, False)
        with fixture.app.test_request_context(headers={"Authorization": "Bearer ippr-synthetic-token"}):
            with pytest.raises(Unauthorized) as error:
                fixture.protected(dataset_id=fixture.dataset.id)
        assert error.value.code == 401
        fixture.session.execute.assert_called_once()
        assert fixture.session.get.call_count == int(missing == "owner_account")
        self.assert_denied(fixture)

    @pytest.mark.parametrize("variant", ["cross_tenant", "cross_tenant_owner", "private", "partial"])
    def test_real_dataset_permissions_deny_before_retrieval_and_signing(self, dataset_security, variant):
        fixture = dataset_security
        fixture.actor.role = TenantAccountRole.OWNER if variant == "cross_tenant_owner" else TenantAccountRole.NORMAL
        if variant.startswith("cross_tenant"):
            other_tenant = Tenant(name="Other synthetic tenant")
            other_tenant.id = OTHER_SYNTHETIC_ID
            fixture.actor._current_tenant = other_tenant
        if variant == "partial":
            fixture.dataset.permission = DatasetPermissionEnum.PARTIAL_TEAM
        with pytest.raises(Forbidden) as error:
            fixture.shared(fixture.actor.current_tenant_id, fixture.dataset.id)
        assert error.value.code == 403
        fixture.session.get.assert_called_once_with(Dataset, fixture.dataset.id)
        assert fixture.session.scalar.call_count == int(variant == "partial")
        self.assert_denied(fixture, before_continuation=False)

    def test_missing_dataset_stops_before_retrieval_and_signing(self, dataset_security):
        fixture = dataset_security
        fixture.state.rows = []
        with pytest.raises(NotFound) as error:
            fixture.shared(SYNTHETIC_TENANT_ID, fixture.dataset.id)
        assert error.value.code == 404
        fixture.session.get.assert_called_once_with(Dataset, fixture.dataset.id)
        fixture.session.scalar.assert_not_called()
        self.assert_denied(fixture, before_continuation=False)

    @pytest.mark.parametrize("permission", [DatasetPermissionEnum.ONLY_ME, DatasetPermissionEnum.PARTIAL_TEAM])
    def test_authorized_owner_reaches_real_signed_conversion(self, dataset_security, permission):
        fixture = dataset_security
        fixture.dataset.permission = permission
        response = fixture.shared(SYNTHETIC_TENANT_ID, fixture.dataset.id)
        self.assert_signed_conversion(fixture, response)
        fixture.session.scalar.assert_not_called()
