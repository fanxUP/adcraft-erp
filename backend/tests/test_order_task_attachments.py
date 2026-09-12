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


def _order(order_id):
    return SimpleNamespace(id=order_id, doc_type="order", deleted_at=None)


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


def _attachment(attachment_id, task_id):
    return SimpleNamespace(
        id=attachment_id,
        related_type="design_task",
        related_id=task_id,
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
    task_id = uuid4()
    attachment = _attachment(uuid4(), task_id)
    db = _Db(
        _Result(scalar=_order(order_id)),
        _Result(rows=[_task(task_id, order_id)]),
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
    design_task = payload["groups"][0]["tasks"][0]
    assert design_task["upload_allowed"] is True
    assert design_task["attachments"][0]["uploaded_by_name"] == "设计员"
    assert "file_path" not in design_task["attachments"][0]


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
async def test_cancelled_task_is_read_only_for_order_attachment_upload(tmp_path, monkeypatch):
    order_id = uuid4()
    task_id = uuid4()
    monkeypatch.setattr("app.services.order_task_attachment_service.settings.LOCAL_UPLOAD_DIR", str(tmp_path))
    db = _Db(
        _Result(scalar=_order(order_id)),
        _Result(scalar=_task(task_id, order_id, status="cancelled")),
    )
    file = UploadFile(filename="设计说明.pdf", file=BytesIO(b"%PDF-1.7"))

    with pytest.raises(ValueError, match="已取消的任务不能上传资料"):
        await OrderTaskAttachmentService(db).upload(
            order_id,
            "design",
            task_id,
            file,
            uuid4(),
        )


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
    assert "file_path" not in payload
    assert list(tmp_path.rglob("*.pdf"))


@pytest.mark.asyncio
async def test_file_access_rejects_attachment_from_another_order():
    order_id = uuid4()
    db = _Db(_Result(scalar=_order(order_id)), _Result(scalar=None))

    with pytest.raises(ValueError, match="附件不存在或不属于该订单"):
        await OrderTaskAttachmentService(db).get_file(order_id, uuid4())
