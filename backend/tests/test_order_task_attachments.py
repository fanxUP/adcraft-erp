from io import BytesIO
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import UploadFile

from app.services.order_task_attachment_service import OrderTaskAttachmentService


class _Result:
    def __init__(self, scalar=None, rows=()):
        self._scalar = scalar
        self._rows = list(rows)

    def scalar_one_or_none(self):
        return self._scalar

    def scalars(self):
        return self

    def all(self):
        return self._rows


class _Db:
    def __init__(self, *results):
        self._results = list(results)
        self.execute = AsyncMock(side_effect=self._execute)
        self.add = MagicMock(side_effect=self._assign_id)
        self.flush = AsyncMock()
        self.delete = AsyncMock()

    @staticmethod
    def _assign_id(model):
        if getattr(model, "id", None) is None:
            model.id = uuid4()

    async def _execute(self, *_args, **_kwargs):
        return self._results.pop(0)


def _order(order_id, *, status="designing"):
    return SimpleNamespace(
        id=order_id,
        doc_type="order",
        deleted_at=None,
        status=status,
    )


def _task(task_id, order_id, *, task_type="design", status="pending"):
    no_field = {
        "design": "design_no",
        "production": "production_no",
        "installation": "installation_no",
    }[task_type]
    return SimpleNamespace(
        id=task_id,
        document_id=order_id,
        status=status,
        completed_at=None,
        created_at=None,
        **{no_field: f"{task_type}-001"},
    )


def _attachment(attachment_id, order_id, *, stage="design"):
    return SimpleNamespace(
        id=attachment_id,
        related_type="order_stage",
        related_id=order_id,
        order_id=order_id,
        stage=stage,
        filename="设计说明.pdf",
        file_path="202609/private.pdf",
        file_size=128,
        file_type="application/pdf",
        category="pdf",
        uploaded_by=uuid4(),
        remark=None,
        created_at=None,
    )


@pytest.mark.asyncio
async def test_list_returns_three_stage_groups_and_never_exposes_storage_path():
    order_id = uuid4()
    attachment = _attachment(uuid4(), order_id)
    db = _Db(
        _Result(scalar=_order(order_id)),
        _Result(rows=[(attachment, "设计员", "designer")]),
        _Result(rows=[]),
        _Result(rows=[]),
    )

    payload = await OrderTaskAttachmentService(db).list_for_order(order_id)

    assert [group["task_type"] for group in payload["groups"]] == [
        "design",
        "production",
        "installation",
    ]
    design_group = payload["groups"][0]
    assert design_group["attachment_count"] == 1
    assert design_group["attachments"][0]["uploaded_by_name"] == "设计员"
    assert design_group["attachments"][0]["stage"] == "design"
    assert "file_path" not in design_group["attachments"][0]


@pytest.mark.asyncio
async def test_upload_rejects_task_that_does_not_belong_to_requested_order(tmp_path, monkeypatch):
    order_id = uuid4()
    monkeypatch.setattr("app.services.order_task_attachment_service.settings.LOCAL_UPLOAD_DIR", str(tmp_path))
    db = _Db(_Result(scalar=_order(order_id)), _Result(scalar=None))
    file = UploadFile(filename="设计说明.pdf", file=BytesIO(b"%PDF-1.7"))

    with pytest.raises(ValueError, match="不存在或不属于该订单"):
        await OrderTaskAttachmentService(db).upload(
            order_id,
            "design",
            uuid4(),
            file,
            uuid4(),
        )


@pytest.mark.asyncio
async def test_cancelled_task_context_does_not_block_order_attachment_upload(tmp_path, monkeypatch):
    order_id = uuid4()
    task_id = uuid4()
    monkeypatch.setattr("app.services.order_task_attachment_service.settings.LOCAL_UPLOAD_DIR", str(tmp_path))
    db = _Db(
        _Result(scalar=_order(order_id)),
        _Result(scalar=_task(task_id, order_id, status="cancelled")),
    )
    file = UploadFile(filename="设计说明.pdf", file=BytesIO(b"%PDF-1.7"))

    from unittest.mock import patch

    with patch("app.services.order_task_attachment_service.log_operation", new=AsyncMock()):
        payload = await OrderTaskAttachmentService(db).upload(
            order_id,
            "design",
            task_id,
            file,
            uuid4(),
        )
    assert payload["related_type"] == "order_stage"
    assert payload["order_id"] == str(order_id)
    assert payload["stage"] == "design"


@pytest.mark.asyncio
async def test_upload_returns_metadata_and_keeps_physical_path_private(tmp_path, monkeypatch):
    order_id = uuid4()
    task_id = uuid4()
    uploader_id = uuid4()
    monkeypatch.setattr("app.services.order_task_attachment_service.settings.LOCAL_UPLOAD_DIR", str(tmp_path))
    db = _Db(
        _Result(scalar=_order(order_id)),
        _Result(scalar=_task(task_id, order_id)),
    )
    file = UploadFile(
        filename="../../设计说明.pdf",
        file=BytesIO(b"%PDF-1.7\ncontent"),
        headers={"content-type": "application/pdf"},
    )

    from unittest.mock import patch

    with patch("app.services.order_task_attachment_service.log_operation", new=AsyncMock()):
        payload = await OrderTaskAttachmentService(db).upload(
            order_id,
            "design",
            task_id,
            file,
            uploader_id,
            "设计员",
        )

    assert payload["filename"] == "设计说明.pdf"
    assert payload["category"] == "pdf"
    assert payload["related_type"] == "order_stage"
    assert payload["order_id"] == str(order_id)
    assert payload["stage"] == "design"
    assert "file_path" not in payload
    assert list(tmp_path.rglob("*.pdf"))


@pytest.mark.asyncio
async def test_upload_does_not_require_a_task_to_exist(tmp_path, monkeypatch):
    order_id = uuid4()
    uploader_id = uuid4()
    monkeypatch.setattr("app.services.order_task_attachment_service.settings.LOCAL_UPLOAD_DIR", str(tmp_path))
    db = _Db(_Result(scalar=_order(order_id)))
    file = UploadFile(
        filename="设计说明.pdf",
        file=BytesIO(b"%PDF-1.7\ncontent"),
        headers={"content-type": "application/pdf"},
    )

    from unittest.mock import patch

    with patch("app.services.order_task_attachment_service.log_operation", new=AsyncMock()):
        payload = await OrderTaskAttachmentService(db).upload(
            order_id,
            "design",
            None,
            file,
            uploader_id,
        )

    assert db.execute.await_count == 1
    assert payload["related_id"] == str(order_id)
    assert payload["order_id"] == str(order_id)
    assert payload["stage"] == "design"


@pytest.mark.asyncio
async def test_order_source_can_download_without_task_context(tmp_path, monkeypatch):
    order_id = uuid4()
    attachment = _attachment(uuid4(), order_id)
    stored_file = tmp_path / attachment.file_path
    stored_file.parent.mkdir(parents=True)
    stored_file.write_bytes(b"%PDF-1.7\ncontent")
    monkeypatch.setattr("app.services.order_task_attachment_service.settings.LOCAL_UPLOAD_DIR", str(tmp_path))
    db = _Db(
        _Result(scalar=_order(order_id)),
        _Result(scalar=attachment),
    )

    result_attachment, stored_path = await OrderTaskAttachmentService(db).get_file(
        order_id,
        attachment.id,
        stage="design",
    )

    assert result_attachment is attachment
    assert stored_path == str(stored_file.resolve())
    assert db.execute.await_count == 2


@pytest.mark.asyncio
async def test_order_source_can_delete_without_task_context(monkeypatch):
    order_id = uuid4()
    attachment = _attachment(uuid4(), order_id)
    db = _Db(
        _Result(scalar=_order(order_id)),
        _Result(scalar=attachment),
    )

    from unittest.mock import patch

    with patch("app.services.order_task_attachment_service.log_operation", new=AsyncMock()):
        metadata, relative_path = await OrderTaskAttachmentService(db).delete(
            order_id,
            attachment.id,
            uuid4(),
            "管理员",
            stage="design",
        )

    assert metadata["order_id"] == str(order_id)
    assert metadata["stage"] == "design"
    assert relative_path == attachment.file_path
    db.delete.assert_awaited_once_with(attachment)


@pytest.mark.asyncio
async def test_task_entry_cannot_use_another_stage(monkeypatch):
    import app.services.order_task_attachment_service as attachment_service

    viewer = SimpleNamespace(permissions={"design_task:read"})
    monkeypatch.setattr(
        attachment_service,
        "user_has_permission",
        lambda user, permission: permission in user.permissions,
    )
    with pytest.raises(PermissionError, match="没有制作任务资料查看权限"):
        await OrderTaskAttachmentService(_Db()).list_for_order(
            uuid4(),
            stage="production",
            task_id=uuid4(),
            viewer=viewer,
        )


@pytest.mark.asyncio
async def test_file_access_rejects_attachment_from_another_order():
    order_id = uuid4()
    db = _Db(_Result(scalar=_order(order_id)), _Result(scalar=None))

    with pytest.raises(ValueError, match="附件不存在或不属于该订单"):
        await OrderTaskAttachmentService(db).get_file(order_id, uuid4())


@pytest.mark.asyncio
async def test_completed_project_reader_can_read_stage_materials_without_task_context(monkeypatch):
    import app.services.order_task_attachment_service as attachment_service

    order_id = uuid4()
    viewer = SimpleNamespace(
        id=uuid4(),
        permissions={"design_task:read", "task_completion:read"},
    )
    monkeypatch.setattr(
        attachment_service,
        "user_has_permission",
        lambda user, permission: permission in user.permissions,
    )
    db = _Db(
        _Result(scalar=_order(order_id, status="completed")),
        _Result(scalar=uuid4()),
        _Result(rows=[]),
    )

    payload = await OrderTaskAttachmentService(db).list_for_order(
        order_id,
        stage="design",
        viewer=viewer,
    )

    assert payload["order_id"] == str(order_id)
    assert [group["stage"] for group in payload["groups"]] == ["design"]
    assert db.execute.await_count == 3


@pytest.mark.asyncio
async def test_completed_project_reader_without_own_completion_event_is_rejected(monkeypatch):
    import app.services.order_task_attachment_service as attachment_service

    order_id = uuid4()
    viewer = SimpleNamespace(
        id=uuid4(),
        permissions={"design_task:read", "task_completion:read"},
    )
    monkeypatch.setattr(
        attachment_service,
        "user_has_permission",
        lambda user, permission: permission in user.permissions,
    )
    db = _Db(
        _Result(scalar=_order(order_id, status="completed")),
        _Result(scalar=None),
    )

    with pytest.raises(PermissionError, match="缺少任务上下文"):
        await OrderTaskAttachmentService(db).list_for_order(
            order_id,
            stage="design",
            viewer=viewer,
        )
