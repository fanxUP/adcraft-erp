# Outsourcing Tasks by Order Item Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable each external task to optionally belong to one order item, expose that relationship throughout the API and UI, and keep order cost aggregation correct without changing order sales totals or the order status machine.

**Architecture:** Reuse the existing nullable `outsource_tasks.order_item_id` column. Add a foreign key with `ON DELETE SET NULL`, centralize cross-order validation in `OutsourceService`, expose item-aware list and dropdown APIs, and render an order-scoped external-task panel that groups tasks by item. Keep `NULL` item links as explicit order-level external tasks for backward compatibility.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy async, PostgreSQL, Alembic, pytest/pytest-asyncio, Vue 3, TypeScript, Element Plus, Vite, Vitest.

**Spec:** `docs/superpowers/specs/2026-09-02-outsourcing-order-items-design.md`

## Global Constraints

- `order_item_id` remains nullable; `NULL` means an order-level external task.
- One external task belongs to at most one order item in this release; a task covering multiple items is split into multiple tasks.
- A non-null `order_item_id` is valid only when `related_doc_type == "order"` and the item belongs to `related_doc_id`.
- Quote external tasks must keep `order_item_id` empty.
- The foreign key uses `ON DELETE SET NULL`; deleting/replacing an item never deletes the external task or its payment history.
- Order cost includes only external tasks with `deleted_at IS NULL` and status `completed` or `settled`.
- External task `total_amount` is vendor cost and must never be overwritten by order sales `total_amount`.
- This release does not change order status transitions, order-item sales fields, or internal design/production/installation task workflows.
- Do not add a package, service, database table, or many-to-many association that is not listed in this plan.
- Preserve the repository’s current Python `>=3.12`, Vue 3, TypeScript, Element Plus, pytest, Vitest, ESLint, and Vite toolchain.
- Tasks 1–8 end with their focused test command and a commit containing only that task’s files; Task 9 records verification evidence without changing source files.
- Before any production migration, run the existing backup flow and verify the migration against the current database.

---

## File Map

The implementation is divided by responsibility so each change has a focused test boundary:

### Data and backend

- `backend/app/models/outsource.py` — declare the SQLAlchemy foreign key and the read-side order-item relationship.
- `backend/alembic/versions/j4k5l6m7n8o9_add_outsource_order_item_fk.py` — add the validated foreign key and index with a reversible migration.
- `backend/app/schemas/outsource.py` — add item link fields and the order-item dropdown response shape.
- `backend/app/repositories/outsource_repo.py` — filter by item and preserve explicit `order_item_id = NULL` updates.
- `backend/app/services/outsource_service.py` — normalize and validate document/item links, serialize item names, provide item dropdown data, and refresh affected order costs.
- `backend/app/api/outsource.py` — expose the item filter, item dropdown endpoint, and explicit-null update semantics.
- `backend/app/services/order_cost_service.py` — exclude soft-deleted external tasks from cost aggregation.
- `backend/app/services/business_document_service.py` — stop copying order sales totals into external-task costs while retaining project-name description sync.

### Backend tests

- `backend/tests/test_schema_migrations.py` — assert the new migration declares the FK, `SET NULL`, and index.
- `backend/tests/test_outsource_service.py` — cover item ownership, serialization, filtering, explicit clearing, paid-task protection, and cost refresh calls.
- `backend/tests/test_outsource_route_permissions.py` — assert the new dropdown route uses `PERM_OUTSOURCE_READ`.
- `backend/tests/test_order_cost_aggregation.py` — assert the external-cost query contains the active-task predicate.
- `backend/tests/test_order_service.py` — assert an order sales-total update does not overwrite external-task cost values.

### Frontend

- `frontend/src/types/api.ts` — add item ID/name to external-task responses and define item options.
- `frontend/src/api/outsource.ts` — add item filtering and the order-item dropdown request.
- `frontend/src/utils/outsourceTaskGrouping.ts` — provide pure grouping and cost-summary functions.
- `frontend/src/utils/outsourceTaskGrouping.test.ts` — test order-level grouping, item grouping, cancelled-task counts, and completed-cost totals.
- `frontend/src/views/outsource/OutsourceTaskList.vue` — add item selection, route-query prefill, item display, and paid-task edit protection.
- `frontend/src/components/outsource/OutsourceTaskCard.vue` — add optional item selection when an internal task sends an external task.
- `frontend/src/components/outsource/OrderOutsourcePanel.vue` — display order external tasks and item-level summaries, with item-prefilled navigation to creation.
- `frontend/src/views/orders/OrderDetail.vue` — add the “外协任务” tab and mount the order panel.

### Product/API documentation

- `docs/02_功能模块PRD.md` — document item-level external-task ownership and cost semantics.
- `docs/04_API接口设计.md` — document the item-aware external-task fields, filter, and dropdown endpoint.

---
### Task 1: Add the order-item foreign key and migration

**Files:**
- Modify: `backend/app/models/outsource.py:OutsourceTask.order_item_id and relationships`
- Create: `backend/alembic/versions/j4k5l6m7n8o9_add_outsource_order_item_fk.py`
- Test: `backend/tests/test_schema_migrations.py`

**Interfaces:**
- Consumes: Existing `business_document_items.id`, current Alembic head `i3j4k5l6m7n8`, and the nullable `outsource_tasks.order_item_id` column.
- Produces: Database constraint `fk_outsource_tasks_order_item_id`, index `ix_outsource_order_item`, and `OutsourceTask.order_item` loaded with `lazy="selectin"`.

- [ ] **Step 1: Write the failing migration-source test**

Append this test to `backend/tests/test_schema_migrations.py`:

```python
def test_outsource_order_item_fk_uses_set_null_and_has_an_index():
    versions_dir = Path(__file__).parents[1] / "alembic" / "versions"
    migration_sources = [
        path.read_text(encoding="utf-8")
        for path in versions_dir.glob("*.py")
    ]

    assert any(
        'op.create_foreign_key("fk_outsource_tasks_order_item_id"' in source
        and '"business_document_items"' in source
        and 'ondelete="SET NULL"' in source
        and 'op.create_index("ix_outsource_order_item"' in source
        for source in migration_sources
    )
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run from `/opt/adcraft`:

```bash
cd backend
.venv/bin/pytest tests/test_schema_migrations.py::test_outsource_order_item_fk_uses_set_null_and_has_an_index -q
```

Expected: FAIL because no migration currently declares the new foreign key and index.

- [ ] **Step 3: Add the SQLAlchemy relationship**

Change `OutsourceTask.order_item_id` and add `order_item` in `backend/app/models/outsource.py`:

```python
from sqlalchemy import Index


class OutsourceTask(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "outsource_tasks"

    __table_args__ = (
        Index("ix_outsource_order_item", "order_item_id"),
    )

    order_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("business_document_items.id", ondelete="SET NULL"),
        nullable=True,
    )

    order_item: Mapped["BusinessDocumentItem | None"] = relationship(
        lazy="selectin",
        foreign_keys=[order_item_id],
    )
```

Keep the existing `vendor` relationship unchanged. Do not add a reverse relationship to `BusinessDocumentItem`.

- [ ] **Step 4: Create the reversible migration with a preflight check**

Create `backend/alembic/versions/j4k5l6m7n8o9_add_outsource_order_item_fk.py` with this structure:

```python
"""Add the optional external-task to order-item relationship."""

from alembic import op
import sqlalchemy as sa


revision = "j4k5l6m7n8o9"
down_revision = "i3j4k5l6m7n8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    invalid_count = bind.execute(
        sa.text(
            """
            SELECT COUNT(*)
            FROM outsource_tasks AS task
            LEFT JOIN business_document_items AS item
              ON item.id = task.order_item_id
            WHERE task.order_item_id IS NOT NULL
              AND item.id IS NULL
            """
        )
    ).scalar_one()
    if invalid_count:
        raise RuntimeError(
            f"outsource_tasks.order_item_id contains {invalid_count} invalid values"
        )

    op.create_foreign_key(
        "fk_outsource_tasks_order_item_id",
        "outsource_tasks",
        "business_document_items",
        ["order_item_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_outsource_order_item",
        "outsource_tasks",
        ["order_item_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_outsource_order_item", table_name="outsource_tasks")
    op.drop_constraint(
        "fk_outsource_tasks_order_item_id",
        "outsource_tasks",
        type_="foreignkey",
    )
```

The migration must not alter nullability, delete rows, or attempt to infer historical item links.

- [ ] **Step 5: Run the migration-source test and model import check**

Run:

```bash
cd /opt/adcraft/backend
.venv/bin/pytest tests/test_schema_migrations.py::test_outsource_order_item_fk_uses_set_null_and_has_an_index -q
.venv/bin/python -c "from app.models.outsource import OutsourceTask; assert OutsourceTask.__table__.c.order_item_id.nullable"
```

Expected: both commands exit 0; the column remains nullable.

- [ ] **Step 6: Commit the database relationship**

```bash
cd /opt/adcraft
git add backend/app/models/outsource.py backend/alembic/versions/j4k5l6m7n8o9_add_outsource_order_item_fk.py backend/tests/test_schema_migrations.py
git diff --cached --check
git commit -m "feat: link outsource tasks to order items"
```

---
### Task 2: Extend schemas, repository filtering, and service validation

**Files:**
- Modify: `backend/app/schemas/outsource.py:OutsourceTaskCreate, OutsourceTaskUpdate, OutsourceTaskResponse`
- Modify: `backend/app/repositories/outsource_repo.py:OutsourceTaskRepository.list_tasks and update`
- Modify: `backend/app/services/outsource_service.py:list_tasks, create_task, update_task, _task_to_dict`
- Test: `backend/tests/test_outsource_service.py`

**Interfaces:**
- Consumes: `OutsourceTask.order_item` from Task 1 and the existing `related_doc_id/order_id` compatibility mapping.
- Produces: `order_item_id` accepted by create/update, item-aware list filtering, `order_item_name` in serialized responses, and `OutsourceService._validate_order_item_link(related_doc_id: UUID | None, related_doc_type: str | None, order_item_id: UUID | None) -> None`.

- [ ] **Step 1: Extend the test fixture and write failing behavior tests**

In `make_mock_outsource_task`, add these fields so serialization tests represent both linked and order-level tasks:

```python
t.related_doc_id = kwargs.get("related_doc_id", SAMPLE_ORDER_ID)
t.related_doc_type = kwargs.get("related_doc_type", "order")
t.order_item_id = kwargs.get("order_item_id")
t.order_item = kwargs.get("order_item")
```

Add a stable item UUID in the test module:

```python
from uuid import UUID

SAMPLE_ORDER_ITEM_ID = UUID("55555555-5555-5555-5555-555555555555")
```

Add these tests:

```python
@pytest.mark.asyncio
async def test_create_task_accepts_item_owned_by_selected_order(service):
    svc, _, task_repo, _ = service
    order = MagicMock(id=SAMPLE_ORDER_ID, doc_type="order", deleted_at=None)
    item = MagicMock(
        id=SAMPLE_ORDER_ITEM_ID,
        document_id=SAMPLE_ORDER_ID,
        item_name="户外写真",
    )
    svc.db.get = AsyncMock(side_effect=[order, item])
    task_repo.create.return_value = make_mock_outsource_task(
        order_item_id=SAMPLE_ORDER_ITEM_ID,
        order_item=item,
    )

    with patch(
        "app.services.outsource_service.generate_outsource_task_no",
        AsyncMock(return_value="OT20260902-0001"),
    ):
        result = await svc.create_task(
            {
                "vendor_id": SAMPLE_USER_ID,
                "related_doc_id": SAMPLE_ORDER_ID,
                "related_doc_type": "order",
                "order_item_id": SAMPLE_ORDER_ITEM_ID,
                "task_type": "production",
                "quantity": 1,
                "unit_price": 100,
            }
        )

    assert result["order_item_id"] == str(SAMPLE_ORDER_ITEM_ID)
    assert result["order_item_name"] == "户外写真"
    assert task_repo.create.await_args.args[0]["order_item_id"] == SAMPLE_ORDER_ITEM_ID


@pytest.mark.asyncio
async def test_create_task_rejects_item_from_another_order(service):
    svc, _, task_repo, _ = service
    order = MagicMock(id=SAMPLE_ORDER_ID, doc_type="order", deleted_at=None)
    foreign_item = MagicMock(
        id=SAMPLE_ORDER_ITEM_ID,
        document_id=UUID("66666666-6666-6666-6666-666666666666"),
        item_name="其他订单明细",
    )
    svc.db.get = AsyncMock(side_effect=[order, foreign_item])

    with patch(
        "app.services.outsource_service.generate_outsource_task_no",
        AsyncMock(return_value="OT20260902-0002"),
    ):
        with pytest.raises(ValueError, match="不属于所选订单"):
            await svc.create_task(
                {
                    "vendor_id": SAMPLE_USER_ID,
                    "related_doc_id": SAMPLE_ORDER_ID,
                    "related_doc_type": "order",
                    "order_item_id": SAMPLE_ORDER_ITEM_ID,
                    "task_type": "production",
                    "quantity": 1,
                    "unit_price": 100,
                }
            )

    task_repo.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_task_can_explicitly_clear_unpaid_item_link(service):
    svc, _, task_repo, _ = service
    task = make_mock_outsource_task(
        order_item_id=SAMPLE_ORDER_ITEM_ID,
        paid_amount=0,
        unpaid_amount=100,
    )
    task_repo.get_by_id.return_value = task

    result = await svc.update_task(
        SAMPLE_ORDER_ID,
        {"order_item_id": None},
    )

    assert result["order_item_id"] is None
    assert task_repo.update.await_args.args[1]["order_item_id"] is None
```

Add a schema assertion that the following create payload validates and that `OutsourceTaskUpdate.model_fields_set` records an explicitly supplied `None`:

```python
OutsourceTaskCreate(
    vendor_id=str(SAMPLE_USER_ID),
    task_type="production",
    order_item_id=str(SAMPLE_ORDER_ITEM_ID),
)
```

- [ ] **Step 2: Run the new tests and verify they fail**

```bash
cd /opt/adcraft/backend
.venv/bin/pytest tests/test_outsource_service.py -q
```

Expected: FAIL because the schemas, validation, serialization, and repository call do not yet support `order_item_id`.

- [ ] **Step 3: Add schema fields and the dropdown response model**

In `backend/app/schemas/outsource.py`, add the following fields:

```python
class OutsourceTaskCreate(BaseModel):
    vendor_id: str = Field(...)
    related_doc_id: str | None = None
    related_doc_type: str | None = None
    related_project_name: str | None = None
    order_id: str | None = None
    order_item_id: str | None = None
    source_task_type: str | None = None
    source_task_id: str | None = None
    task_type: str = Field(...)
    description: str | None = None
    quantity: int = Field(1, gt=0)
    unit_price: Decimal = Field(Decimal("0"), ge=0)
    expected_at: str | None = None
    remark: str | None = None


class OutsourceTaskUpdate(BaseModel):
    vendor_id: str | None = None
    related_doc_id: str | None = None
    related_doc_type: str | None = None
    order_item_id: str | None = None
    source_task_type: str | None = None
    source_task_id: str | None = None
    task_type: str | None = None
    description: str | None = None
    quantity: int | None = Field(None, gt=0)
    unit_price: Decimal | None = Field(None, ge=0)
    status: str | None = None
    expected_at: str | None = None
    completed_at: str | None = None
    remark: str | None = None


class OutsourceOrderItemOption(BaseModel):
    id: str
    label: str
    item_name: str
    quantity: Decimal
    unit: str | None = None
    group_name: str | None = None
    sort_order: int = 0
```

Add `order_item_id: str | None = None` and `order_item_name: str | None = None` to `OutsourceTaskResponse`.

- [ ] **Step 4: Add the repository filter and explicit-null update rule**

Change the repository signature to keep `order_item_id` beside `related_doc_id`:

```python
async def list_tasks(
    self,
    skip: int = 0,
    limit: int = 20,
    status: str | None = None,
    vendor_id: UUID | None = None,
    related_doc_id: UUID | None = None,
    order_item_id: UUID | None = None,
    source_task_type: str | None = None,
    source_task_id: UUID | None = None,
    task_type: str | None = None,
) -> tuple[list[OutsourceTask], int]:
```

Add the predicate immediately after the document predicate:

```python
if order_item_id:
    q = q.where(OutsourceTask.order_item_id == order_item_id)
```

Keep the existing `OutsourceTask.deleted_at.is_(None)` predicate. In `update`, allow explicit null only for the nullable item link:

```python
for key, value in data.items():
    if value is not None or key == "order_item_id":
        setattr(task, key, value)
await self.db.flush()
return task
```

- [ ] **Step 5: Implement normalization, validation, and serialization**

Add the shared validation method to `OutsourceService`:

```python
async def _validate_order_item_link(
    self,
    related_doc_id: UUID | None,
    related_doc_type: str | None,
    order_item_id: UUID | None,
) -> None:
    if order_item_id is None:
        return
    if related_doc_type != "order":
        raise ValueError("订单明细只能关联订单")
    if related_doc_id is None:
        raise ValueError("关联订单不能为空")

    from app.models.business_document import BusinessDocument, BusinessDocumentItem

    document = await self.db.get(BusinessDocument, related_doc_id)
    if (
        document is None
        or document.deleted_at is not None
        or document.doc_type != "order"
    ):
        raise ValueError("订单不存在")

    item = await self.db.get(BusinessDocumentItem, order_item_id)
    if item is None:
        raise ValueError("订单明细不存在")
    if item.document_id != related_doc_id:
        raise ValueError("订单明细不属于所选订单")
```

In `create_task`, perform the existing `order_id -> related_doc_id` mapping first, set `related_doc_type` to `order` when the compatibility-only `order_id` is used with an item, convert a non-empty `order_item_id` to `UUID`, and call `_validate_order_item_link` before `task_repo.create`.

In `update_task`, calculate prospective values before changing the ORM object:

```python
old_item_id = task.order_item_id
new_item_id = data.get("order_item_id", old_item_id)
if new_item_id is not None:
    new_item_id = UUID(str(new_item_id))
    data["order_item_id"] = new_item_id

new_doc_id = data.get("related_doc_id", task.related_doc_id)
if new_doc_id:
    new_doc_id = UUID(str(new_doc_id))
    data["related_doc_id"] = new_doc_id
new_doc_type = data.get("related_doc_type", task.related_doc_type)

await self._validate_order_item_link(new_doc_id, new_doc_type, new_item_id)
if old_item_id != new_item_id and Decimal(str(task.paid_amount or 0)) > 0:
    raise ValueError("已有付款的外协任务不能修改订单明细归属")
```

Use keyword arguments when calling the repository so future additions do not shift positional test assertions:

```python
tasks, total = await self.task_repo.list_tasks(
    skip=skip,
    limit=page_size,
    status=status,
    vendor_id=vendor_id,
    related_doc_id=related_doc_id,
    order_item_id=order_item_id,
    source_task_type=source_task_type,
    source_task_id=source_task_id,
    task_type=task_type,
)
```

Serialize the linked item without triggering asynchronous lazy loading:

```python
"order_item_id": str(t.order_item_id) if t.order_item_id else None,
"order_item_name": getattr(t.order_item, "item_name", None) if t.order_item else None,
```

Update the existing source/task-type filter tests to inspect `call_args.kwargs` and add an item-filter assertion.

- [ ] **Step 6: Run the service test suite**

```bash
cd /opt/adcraft/backend
.venv/bin/pytest tests/test_outsource_service.py -q
```

Expected: all existing external-task tests and the new item-link tests pass.

- [ ] **Step 7: Commit the service contract**

```bash
cd /opt/adcraft
git add backend/app/schemas/outsource.py backend/app/repositories/outsource_repo.py backend/app/services/outsource_service.py backend/tests/test_outsource_service.py
git diff --cached --check
git commit -m "feat: validate outsource order item links"
```

---
### Task 3: Expose item-aware external-task APIs

**Files:**
- Modify: `backend/app/api/outsource.py:list_tasks, update_task, new order-item route`
- Modify: `backend/app/services/outsource_service.py:list_order_items_for_dropdown`
- Test: `backend/tests/test_outsource_route_permissions.py`
- Test: `backend/tests/test_outsource_service.py`

**Interfaces:**
- Consumes: Task 2’s item-aware service signature and `OutsourceOrderItemOption` model.
- Produces: `GET /outsource/tasks?order_item_id=ORDER_ITEM_UUID`, `GET /outsource/orders/{order_id}/items-for-dropdown`, and explicit-null update behavior at the HTTP boundary.

- [ ] **Step 1: Add the route permission expectation and failing dropdown-service test**

Add this expected route to `test_outsource_routes_use_business_permissions`:

```python
("GET", "/outsource/orders/{order_id}/items-for-dropdown"): PERM_OUTSOURCE_READ,
```

Add a service test that provides an order and two items through the existing mocked async session and asserts ordered, labeled options:

```python
@pytest.mark.asyncio
async def test_list_order_items_for_dropdown_returns_order_items(service):
    svc, _, _, _ = service
    order = MagicMock(id=SAMPLE_ORDER_ID, doc_type="order", deleted_at=None)
    first = MagicMock(
        id=SAMPLE_ORDER_ITEM_ID,
        item_name="户外写真",
        quantity=2,
        unit="平方米",
        group_name="门头广告",
        sort_order=1,
    )
    second = MagicMock(
        id=UUID("77777777-7777-7777-7777-777777777777"),
        item_name="亚克力字",
        quantity=1,
        unit="套",
        group_name=None,
        sort_order=2,
    )
    result = MagicMock()
    result.scalars.return_value.all.return_value = [first, second]
    svc.db.get = AsyncMock(return_value=order)
    svc.db.execute = AsyncMock(return_value=result)

    items = await svc.list_order_items_for_dropdown(SAMPLE_ORDER_ID)

    assert items[0]["id"] == str(SAMPLE_ORDER_ITEM_ID)
    assert items[0]["label"] == "1. 户外写真｜数量 2｜平方米"
    assert items[1]["label"] == "2. 亚克力字｜数量 1｜套"
```

- [ ] **Step 2: Run the focused route and service tests and verify the new assertions fail**

```bash
cd /opt/adcraft/backend
.venv/bin/pytest tests/test_outsource_route_permissions.py tests/test_outsource_service.py -q
```

Expected: FAIL because the route and dropdown service method do not yet exist, and the list route has no item query parameter.

---
- [ ] **Step 3: Add order_item_id to the list route and preserve explicit null on update**

Extend the route query parameters:

~~~python
order_id: str | None = None
order_item_id: str | None = None
task_type: str | None = None
~~~

Convert the item ID alongside the existing UUID conversions:

~~~python
iid = UUID(order_item_id) if order_item_id else None
~~~

Call the service with keywords:

~~~python
tasks, total = await service.list_tasks(
    page=page,
    page_size=page_size,
    status=status,
    vendor_id=vid,
    related_doc_id=oid,
    order_item_id=iid,
    source_task_type=source_task_type,
    source_task_id=stid,
    task_type=task_type,
)
~~~

Change only the external-task update route from exclude_none=True to exclude_unset=True:

~~~python
task = await service.update_task(
    tid,
    data.model_dump(exclude_unset=True),
)
~~~

Keep vendor update’s current exclude_none=True behavior unchanged.

- [ ] **Step 4: Implement the dropdown service method**

Add this method to OutsourceService:

~~~python
async def list_order_items_for_dropdown(self, order_id: UUID) -> list[dict]:
    from app.models.business_document import BusinessDocument, BusinessDocumentItem

    document = await self.db.get(BusinessDocument, order_id)
    if (
        document is None
        or document.deleted_at is not None
        or document.doc_type != "order"
    ):
        raise ValueError("订单不存在")

    result = await self.db.execute(
        select(BusinessDocumentItem)
        .where(BusinessDocumentItem.document_id == order_id)
        .order_by(
            BusinessDocumentItem.sort_order.asc(),
            BusinessDocumentItem.created_at.asc(),
        )
    )
    items = result.scalars().all()
    options = []
    for index, item in enumerate(items, start=1):
        label_parts = [f"{index}. {item.item_name}"]
        if item.quantity is not None:
            label_parts.append(f"数量 {item.quantity}")
        if item.unit:
            label_parts.append(item.unit)
        options.append(
            {
                "id": str(item.id),
                "label": "｜".join(label_parts),
                "item_name": item.item_name,
                "quantity": item.quantity,
                "unit": item.unit,
                "group_name": item.group_name,
                "sort_order": item.sort_order,
            }
        )
    return options
~~~

Do not query or expose quote items from this endpoint.

- [ ] **Step 5: Add the protected endpoint**

Place this route in backend/app/api/outsource.py with the other order dropdown routes:

~~~python
@router.get("/orders/{order_id}/items-for-dropdown")
async def list_order_items_for_dropdown(
    order_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_OUTSOURCE_READ)),
):
    service = OutsourceService(db)
    try:
        items = await service.list_order_items_for_dropdown(UUID(order_id))
        return success(items)
    except ValueError as exc:
        return error(40401, str(exc))
~~~

- [ ] **Step 6: Run API-focused tests**

~~~bash
cd /opt/adcraft/backend
.venv/bin/pytest tests/test_outsource_route_permissions.py tests/test_outsource_service.py -q
~~~

Expected: all route permission, dropdown, list-filter, and explicit-null update tests pass.

- [ ] **Step 7: Commit the API surface**

~~~bash
cd /opt/adcraft
git add backend/app/api/outsource.py backend/app/services/outsource_service.py backend/tests/test_outsource_route_permissions.py backend/tests/test_outsource_service.py
git diff --cached --check
git commit -m "feat: expose outsource order item APIs"
~~~

---
### Task 4: Correct cost aggregation and synchronize affected orders

**Files:**

- Modify: backend/app/services/order_cost_service.py:OrderCostAggregationService.calculate
- Modify: backend/app/services/outsource_service.py:create_task, update_task, create_payment, cancel_task, revert_task, delete_task, restore_task
- Modify: backend/app/services/business_document_service.py:update
- Test: backend/tests/test_order_cost_aggregation.py
- Test: backend/tests/test_outsource_service.py
- Test: backend/tests/test_order_service.py

**Interfaces:**

- Consumes: Task 2’s normalized document/item values and Task 3’s service methods.
- Produces: active-task-only order cost aggregation and _sync_related_order_cost(related_doc_id, related_doc_type) calls after cost-affecting external-task operations.

- [ ] **Step 1: Write failing cost and synchronization tests**

Add a cost-query predicate assertion to backend/tests/test_order_cost_aggregation.py:

~~~python
@pytest.mark.asyncio
async def test_cost_breakdown_excludes_soft_deleted_outsource_tasks():
    db = MagicMock()
    results = []
    for value in (Decimal("100"), Decimal("0"), Decimal("0")):
        result = MagicMock()
        result.scalar.return_value = value
        results.append(result)
    db.execute = AsyncMock(side_effect=results)

    await OrderCostAggregationService(db).calculate(uuid4())

    outsource_statement = db.execute.await_args_list[0].args[0]
    assert "outsource_tasks.deleted_at IS NULL" in str(outsource_statement)
~~~

In backend/tests/test_outsource_service.py, patch the service helper in the fixture so existing unit tests do not call the real order service, then add:

~~~python
@pytest.mark.asyncio
async def test_completing_outsource_task_refreshes_related_order_cost(service):
    svc, _, task_repo, _ = service
    task = make_mock_outsource_task(
        status="in_progress",
        related_doc_id=SAMPLE_ORDER_ID,
        related_doc_type="order",
    )
    task_repo.get_by_id.return_value = task
    svc._sync_related_order_cost = AsyncMock()

    await svc.update_task(SAMPLE_ORDER_ID, {"status": "completed"})

    svc._sync_related_order_cost.assert_awaited_once_with(
        SAMPLE_ORDER_ID,
        "order",
    )
~~~

Add a payment test that moves a completed task from unpaid to settled and asserts the same helper call. Add delete and cancel tests that assert the related order is refreshed after the status or soft-delete write.

In backend/tests/test_order_service.py, add a regression test using a linked external task:

~~~python
@pytest.mark.asyncio
async def test_order_total_update_does_not_overwrite_outsource_cost():
    db = MagicMock()
    doc = make_order(project_name="灯箱制作", total_amount=Decimal("1000"))
    task = MagicMock(
        related_doc_id=doc.id,
        related_doc_type="order",
        description="旧描述",
        unit_price=Decimal("150"),
        total_amount=Decimal("150"),
    )
    outsource_result = MagicMock()
    outsource_result.scalars.return_value.all.return_value = [task]
    contract_result = MagicMock()
    contract_result.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(side_effect=[outsource_result, contract_result])
    db.flush = AsyncMock()

    service = BusinessDocumentService(db, doc_type="order")
    service.repo.get_by_id = AsyncMock(return_value=doc)
    service.repo.update = AsyncMock(side_effect=lambda document, data: document)
    service._sync_contact_to_customer = AsyncMock()
    service._to_detail = MagicMock(return_value={})

    await service.update(
        doc.id,
        {"project_name": "灯箱制作", "total_amount": Decimal("1200")},
    )

    assert task.description == "灯箱制作"
    assert task.unit_price == Decimal("150")
    assert task.total_amount == Decimal("150")
~~~

- [ ] **Step 2: Run the new tests and verify the cost predicate fails**

~~~bash
cd /opt/adcraft/backend
.venv/bin/pytest tests/test_order_cost_aggregation.py tests/test_outsource_service.py tests/test_order_service.py -q
~~~

Expected: the deleted-task SQL assertion and lifecycle-call assertions fail before implementation; the existing tests remain runnable.

- [ ] **Step 3: Exclude soft-deleted external tasks from aggregation**

Change the external-cost statement to include the active predicate:

~~~python
outsource = await self._sum(
    select(func.coalesce(func.sum(OutsourceTask.total_amount), 0)).where(
        OutsourceTask.related_doc_id == document_id,
        OutsourceTask.deleted_at.is_(None),
        OutsourceTask.status.in_(("completed", "settled")),
    )
)
~~~

Keep inventory and manual-cost queries unchanged.

- [ ] **Step 4: Implement the order-cost refresh helper**

Add this helper to OutsourceService:

~~~python
async def _sync_related_order_cost(
    self,
    related_doc_id: UUID | None,
    related_doc_type: str | None,
) -> None:
    if related_doc_id is None or related_doc_type != "order":
        return

    from app.models.business_document import BusinessDocument
    document = await self.db.get(BusinessDocument, related_doc_id)
    if (
        document is None
        or document.deleted_at is not None
        or document.doc_type != "order"
    ):
        return

    from app.services.business_document_service import BusinessDocumentService
    await BusinessDocumentService(self.db, doc_type="order").auto_calculate_cost(
        related_doc_id
    )
~~~

Call it after the successful database flush in create_task, create_payment, cancel_task, revert_task, delete_task, and restore_task.

In update_task, save the old pair before applying data, then refresh each distinct affected order after task_repo.update:

~~~python
old_related_doc_id = task.related_doc_id
old_related_doc_type = task.related_doc_type

affected_documents = {
    (old_related_doc_id, old_related_doc_type),
    (task.related_doc_id, task.related_doc_type),
}
for related_doc_id, related_doc_type in affected_documents:
    await self._sync_related_order_cost(related_doc_id, related_doc_type)
~~~

Use the same distinct-pair pattern in any update path that can change related_doc_id.

- [ ] **Step 5: Remove sales-total-to-cost overwriting**

In BusinessDocumentService.update, keep the existing external-task query only under if data.get("project_name") and retain:

~~~python
if data.get("project_name"):
    for task in tasks:
        task.description = data["project_name"]
~~~

Delete the assignment of data["total_amount"] to task.unit_price and task.total_amount. A payload containing only total_amount must not query or mutate external-task costs.

- [ ] **Step 6: Run the cost and lifecycle tests**

~~~bash
cd /opt/adcraft/backend
.venv/bin/pytest tests/test_order_cost_aggregation.py tests/test_outsource_service.py tests/test_order_service.py -q
~~~

Expected: all focused tests pass, including the soft-delete predicate, lifecycle refresh calls, and cost-isolation regression.

- [ ] **Step 7: Commit cost behavior**

~~~bash
cd /opt/adcraft
git add backend/app/services/order_cost_service.py backend/app/services/outsource_service.py backend/app/services/business_document_service.py backend/tests/test_order_cost_aggregation.py backend/tests/test_outsource_service.py backend/tests/test_order_service.py
git diff --cached --check
git commit -m "fix: keep outsource costs in order aggregation"
~~~

---
### Task 5: Add frontend item types, API calls, and tested grouping utilities

**Files:**

- Modify: frontend/src/types/api.ts:OutsourceTaskResponse
- Modify: frontend/src/api/outsource.ts:getOutsourceTasks and new getOutsourceOrderItems
- Create: frontend/src/utils/outsourceTaskGrouping.ts
- Create: frontend/src/utils/outsourceTaskGrouping.test.ts

**Interfaces:**

- Consumes: Task 3’s JSON fields and GET /outsource/orders/{order_id}/items-for-dropdown response.
- Produces: OutsourceOrderItemOption, ORDER_LEVEL_OUTSOURCE_KEY, groupTasksByOrderItem, and summarizeOutsourceTasks for Vue components.

- [ ] **Step 1: Write failing utility tests**

Create frontend/src/utils/outsourceTaskGrouping.test.ts:

~~~ts
import { describe, expect, it } from 'vitest'
import type { OutsourceTaskResponse } from '@/types/api'
import {
  ORDER_LEVEL_OUTSOURCE_KEY,
  groupTasksByOrderItem,
  summarizeOutsourceTasks,
} from './outsourceTaskGrouping'

const makeTask = (
  overrides: Partial<OutsourceTaskResponse> = {},
): OutsourceTaskResponse => ({
  id: 'task-1',
  task_no: 'OT-1',
  vendor_id: 'vendor-1',
  task_type: 'production',
  quantity: 1,
  unit_price: 100,
  total_amount: 100,
  paid_amount: 0,
  unpaid_amount: 100,
  status: 'pending',
  order_item_id: null,
  order_item_name: null,
  ...overrides,
})

describe('groupTasksByOrderItem', () => {
  it('uses a stable key for order-level tasks', () => {
    const groups = groupTasksByOrderItem([
      makeTask({ id: 'order-task', order_item_id: null }),
      makeTask({ id: 'item-task', order_item_id: 'item-1' }),
    ])

    expect(groups[ORDER_LEVEL_OUTSOURCE_KEY].map(task => task.id)).toEqual(['order-task'])
    expect(groups['item-1'].map(task => task.id)).toEqual(['item-task'])
  })
})

describe('summarizeOutsourceTasks', () => {
  it('separates active task totals from completed cost totals', () => {
    const summary = summarizeOutsourceTasks([
      makeTask({ total_amount: 100, paid_amount: 20, unpaid_amount: 80, status: 'pending' }),
      makeTask({ id: 'completed', total_amount: 200, paid_amount: 200, unpaid_amount: 0, status: 'completed' }),
      makeTask({ id: 'cancelled', total_amount: 300, paid_amount: 0, unpaid_amount: 300, status: 'cancelled' }),
      makeTask({ id: 'deleted', total_amount: 400, deleted_at: '2026-09-02T00:00:00Z' }),
    ])

    expect(summary.taskCount).toBe(3)
    expect(summary.activeTaskCount).toBe(2)
    expect(summary.totalAmount).toBe(600)
    expect(summary.paidAmount).toBe(220)
    expect(summary.unpaidAmount).toBe(380)
    expect(summary.costAmount).toBe(200)
  })
})
~~~

- [ ] **Step 2: Run the utility test and verify it fails**

~~~bash
cd /opt/adcraft/frontend
npx vitest run src/utils/outsourceTaskGrouping.test.ts
~~~

Expected: FAIL because the utility module and new response fields do not yet exist.

- [ ] **Step 3: Add the frontend API types and functions**

Add these fields to OutsourceTaskResponse:

~~~ts
order_item_id?: string | null
order_item_name?: string | null
~~~

Add the dropdown type:

~~~ts
export interface OutsourceOrderItemOption {
  id: string
  label: string
  item_name: string
  quantity: number
  unit: string | null
  group_name: string | null
  sort_order: number
}
~~~

Extend the task-list parameter type with order_item_id?: string and add this API function in frontend/src/api/outsource.ts:

~~~ts
export function getOutsourceOrderItems(orderId: string) {
  return get<OutsourceOrderItemOption[]>(
    '/outsource/orders/' + orderId + '/items-for-dropdown',
  )
}
~~~

Import OutsourceOrderItemOption from @/types/api and leave existing create/update payload compatibility intact.

- [ ] **Step 4: Implement the pure grouping utility**

Create frontend/src/utils/outsourceTaskGrouping.ts:

~~~ts
import type { OutsourceTaskResponse } from '@/types/api'

export const ORDER_LEVEL_OUTSOURCE_KEY = '__order__'

export interface OutsourceTaskSummary {
  taskCount: number
  activeTaskCount: number
  totalAmount: number
  paidAmount: number
  unpaidAmount: number
  costAmount: number
}

export function groupTasksByOrderItem(
  tasks: OutsourceTaskResponse[],
): Record<string, OutsourceTaskResponse[]> {
  return tasks
    .filter(task => !task.deleted_at)
    .reduce<Record<string, OutsourceTaskResponse[]>>((groups, task) => {
      const key = task.order_item_id || ORDER_LEVEL_OUTSOURCE_KEY
      groups[key] ??= []
      groups[key].push(task)
      return groups
    }, {})
}

export function summarizeOutsourceTasks(
  tasks: OutsourceTaskResponse[],
): OutsourceTaskSummary {
  const visible = tasks.filter(task => !task.deleted_at)
  const sum = (field: 'total_amount' | 'paid_amount' | 'unpaid_amount') =>
    visible.reduce((total, task) => total + Number(task[field] || 0), 0)
  const costAmount = visible
    .filter(task => task.status === 'completed' || task.status === 'settled')
    .reduce((total, task) => total + Number(task.total_amount || 0), 0)

  return {
    taskCount: visible.length,
    activeTaskCount: visible.filter(task => task.status !== 'cancelled').length,
    totalAmount: sum('total_amount'),
    paidAmount: sum('paid_amount'),
    unpaidAmount: sum('unpaid_amount'),
    costAmount,
  }
}
~~~

- [ ] **Step 5: Run the utility tests and typecheck**

~~~bash
cd /opt/adcraft/frontend
npx vitest run src/utils/outsourceTaskGrouping.test.ts
npm run typecheck
~~~

Expected: both commands pass.

- [ ] **Step 6: Commit the frontend contract utilities**

~~~bash
cd /opt/adcraft
git add frontend/src/types/api.ts frontend/src/api/outsource.ts frontend/src/utils/outsourceTaskGrouping.ts frontend/src/utils/outsourceTaskGrouping.test.ts
git diff --cached --check
git commit -m "feat: add frontend outsource item contracts"
~~~

---
### Task 6: Add item selection to external-task creation flows

**Files:**

- Modify: frontend/src/views/outsource/OutsourceTaskList.vue
- Modify: frontend/src/components/outsource/OutsourceTaskCard.vue

**Interfaces:**

- Consumes: getOutsourceOrderItems, OutsourceOrderItemOption, and order_item_id API payload support from Task 5.
- Produces: item selection in the global external-task form and optional item selection when an internal task sends an external task.

- [ ] **Step 1: Add item state and reset behavior to OutsourceTaskList.vue**

Add the import and reactive state:

~~~ts
import { useRoute } from 'vue-router'
import { getOutsourceOrderItems } from '@/api/outsource'
import type { OutsourceOrderItemOption } from '@/types/api'

const route = useRoute()
const orderItems = ref<OutsourceOrderItemOption[]>([])
const editingPaid = ref(false)

const form = reactive({
  vendor_id: '',
  related_doc_id: '',
  related_doc_type: '',
  order_item_id: '',
  task_type: 'production',
  description: '',
  quantity: 1,
  unit_price: 0,
  remark: '',
})
~~~

Add the loader and document-change behavior:

~~~ts
async function loadOrderItems(orderId: string) {
  orderItems.value = []
  if (!orderId) return
  try {
    orderItems.value = await getOutsourceOrderItems(orderId)
  } catch {
    orderItems.value = []
  }
}

async function onRelatedDocChange(value: string) {
  form.order_item_id = ''
  if (!value) {
    form.related_doc_type = ''
    return
  }
  const isQuote = quotes.value.some(quote => quote.id === value)
  form.related_doc_type = isQuote ? 'quote' : 'order'
  if (!isQuote) await loadOrderItems(value)
}
~~~

When handleCreate resets the form, reset order_item_id, orderItems, and editingPaid as well. When handleEdit loads an order task, await loadOrderItems(row.related_doc_id) before opening the dialog and set editingPaid.value = row.paid_amount > 0.

- [ ] **Step 2: Add the item selector and list column**

Insert this form item after the related-document selector:

~~~vue
<el-form-item label="订单明细" prop="order_item_id">
  <el-select
    v-model="form.order_item_id"
    clearable
    filterable
    :disabled="form.related_doc_type !== 'order' || editingPaid"
    placeholder="可选，留空表示整单外协"
    style="width: 100%"
  >
    <el-option
      v-for="item in orderItems"
      :key="item.id"
      :label="item.label"
      :value="item.id"
    />
  </el-select>
</el-form-item>
~~~

Add a table column after the project/task column:

~~~vue
<el-table-column label="订单明细" min-width="160" show-overflow-tooltip>
  <template #default="{ row }">
    {{ row.order_item_name || '整单外协' }}
  </template>
</el-table-column>
~~~

- [ ] **Step 3: Serialize create, update, and route-query payloads correctly**

Use undefined for an empty create selection and null for an explicit edit clear:

~~~ts
const payload = editingId.value
  ? { ...form, order_item_id: form.order_item_id || null }
  : { ...form, order_item_id: form.order_item_id || undefined }

if (editingId.value) {
  await updateOutsourceTask(editingId.value, payload)
} else {
  await createOutsourceTask(payload)
}
~~~

After the existing vendor/order/quote loading in onMounted, read the order-prefill query once:

~~~ts
const queryOrderId = typeof route.query.order_id === 'string' ? route.query.order_id : ''
const queryItemId = typeof route.query.order_item_id === 'string' ? route.query.order_item_id : ''
if (queryOrderId) {
  handleCreate()
  form.related_doc_id = queryOrderId
  form.related_doc_type = 'order'
  await loadOrderItems(queryOrderId)
  if (orderItems.value.some(item => item.id === queryItemId)) {
    form.order_item_id = queryItemId
  }
  dialogVisible.value = true
}
~~~

Ensure handleCreate does not erase the query values after they are assigned.

- [ ] **Step 4: Add item selection to OutsourceTaskCard.vue**

Add the same orderItems ref and load it from props.orderId on mount. Add this form field before quantity:

~~~vue
<el-form-item label="关联明细">
  <el-select
    v-model="form.order_item_id"
    clearable
    filterable
    placeholder="可选，留空表示整单外协"
    style="width: 100%"
  >
    <el-option
      v-for="item in orderItems"
      :key="item.id"
      :label="item.label"
      :value="item.id"
    />
  </el-select>
</el-form-item>
~~~

Reset form.order_item_id in openDialog and add it to the existing create request:

~~~ts
order_item_id: form.order_item_id || undefined,
~~~

Do not remove source_task_type or source_task_id from the request.

- [ ] **Step 5: Run frontend checks for the changed flows**

~~~bash
cd /opt/adcraft/frontend
npm run typecheck
npm run lint
npx vitest run src/utils/outsourceTaskGrouping.test.ts
~~~

Expected: all commands pass without Vue template or payload type errors.

- [ ] **Step 6: Commit the creation-flow UI**

~~~bash
cd /opt/adcraft
git add frontend/src/views/outsource/OutsourceTaskList.vue frontend/src/components/outsource/OutsourceTaskCard.vue
git diff --cached --check
git commit -m "feat: select order items for outsource tasks"
~~~

---
### Task 7: Add the order-detail external-task panel

**Files:**

- Create: frontend/src/components/outsource/OrderOutsourcePanel.vue
- Modify: frontend/src/views/orders/OrderDetail.vue

**Interfaces:**

- Consumes: getOutsourceTasks, groupTasksByOrderItem, summarizeOutsourceTasks, OrderItemResponse, and the existing order-detail router.
- Produces: an order-scoped “外协任务” tab with per-item summaries, task rows, order-level task display, and item-prefilled navigation to creation.

- [ ] **Step 1: Create the order panel with explicit props and loading state**

Create frontend/src/components/outsource/OrderOutsourcePanel.vue with this script setup contract:

~~~vue
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getOutsourceTasks } from '@/api/outsource'
import type { OrderItemResponse, OutsourceTaskResponse } from '@/types/api'
import {
  ORDER_LEVEL_OUTSOURCE_KEY,
  groupTasksByOrderItem,
  summarizeOutsourceTasks,
} from '@/utils/outsourceTaskGrouping'

const props = defineProps<{
  orderId: string
  items: OrderItemResponse[]
}>()

const router = useRouter()
const loading = ref(false)
const tasks = ref<OutsourceTaskResponse[]>([])

const groups = computed(() => groupTasksByOrderItem(tasks.value))
const itemSummaries = computed(() => props.items.map(item => ({
  item,
  summary: summarizeOutsourceTasks(groups.value[item.id] || []),
})))
const orderSummary = computed(() =>
  summarizeOutsourceTasks(groups.value[ORDER_LEVEL_OUTSOURCE_KEY] || []),
)

async function refresh() {
  loading.value = true
  try {
    const result = await getOutsourceTasks({
      page: 1,
      page_size: 100,
      order_id: props.orderId,
    })
    tasks.value = result.items
  } catch {
    ElMessage.error('外协任务加载失败')
  } finally {
    loading.value = false
  }
}

function startOutsource(orderItemId?: string) {
  router.push({
    path: '/outsource/tasks',
    query: {
      order_id: props.orderId,
      ...(orderItemId ? { order_item_id: orderItemId } : {}),
    },
  })
}

function statusLabel(status: string) {
  const labels: Record<string, string> = {
    pending: '待处理',
    in_progress: '进行中',
    completed: '已完成',
    settled: '已结算',
    cancelled: '已取消',
  }
  return labels[status] || status
}

function statusType(status: string) {
  const types: Record<string, string> = {
    pending: 'info',
    in_progress: 'warning',
    completed: 'success',
    settled: '',
    cancelled: 'danger',
  }
  return (types[status] || 'info') as 'primary' | 'success' | 'warning' | 'info' | 'danger' | undefined
}

onMounted(() => {
  void refresh()
})
</script>
~~~

Keep the task list request at page_size: 100, matching the current API maximum, and show the existing pagination-free order panel as a complete order snapshot. If the order later exceeds 100 external tasks, the global task list remains the complete paginated view.

- [ ] **Step 2: Add the item summary table and task table**

Use one summary row per order item, not a nested task table in every item row:

~~~vue
<template>
  <div class="order-outsource-panel">
    <el-card shadow="never" class="info-card">
      <template #header>
        <div class="card-header">
          <span>订单明细外协摘要</span>
          <el-button type="danger" size="small" @click="startOutsource()">
            新建整单外协
          </el-button>
        </div>
      </template>
      <el-table :data="itemSummaries" v-loading="loading" stripe size="small">
        <el-table-column label="订单明细" min-width="220">
          <template #default="{ row }">{{ row.item.item_name }}</template>
        </el-table-column>
        <el-table-column label="任务数" width="90">
          <template #default="{ row }">{{ row.summary.taskCount }}</template>
        </el-table-column>
        <el-table-column label="已发生成本" width="120" align="right">
          <template #default="{ row }">¥{{ row.summary.costAmount.toFixed(2) }}</template>
        </el-table-column>
        <el-table-column label="未付" width="120" align="right">
          <template #default="{ row }">¥{{ row.summary.unpaidAmount.toFixed(2) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click="startOutsource(row.item.id)">
              发起外协
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <div v-if="orderSummary.taskCount" class="order-level-summary">
        整单外协：{{ orderSummary.taskCount }} 个任务，已发生成本 ¥{{ orderSummary.costAmount.toFixed(2) }}
      </div>
    </el-card>

    <el-card shadow="never" class="info-card task-card">
      <template #header><span>外协任务明细</span></template>
      <el-table :data="tasks" v-loading="loading" stripe size="small" empty-text="暂无外协任务">
        <el-table-column prop="task_no" label="外协编号" width="160" />
        <el-table-column label="订单明细" min-width="180">
          <template #default="{ row }">{{ row.order_item_name || '整单外协' }}</template>
        </el-table-column>
        <el-table-column prop="vendor_name" label="外协商" width="140" />
        <el-table-column prop="description" label="描述" min-width="180" show-overflow-tooltip />
        <el-table-column label="金额" width="110" align="right">
          <template #default="{ row }">¥{{ Number(row.total_amount || 0).toFixed(2) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>
~~~

Use the project’s existing CSS variables for info-card, and keep cancelled tasks visible with their status for auditability; only soft-deleted tasks are excluded by the API and utility.

- [ ] **Step 3: Add the tab to OrderDetail.vue**

Import the component:

~~~ts
import OrderOutsourcePanel from '@/components/outsource/OrderOutsourcePanel.vue'
~~~

Add a tab after the existing internal “任务” tab:

~~~vue
<el-tab-pane label="外协任务" name="outsource">
  <OrderOutsourcePanel
    v-if="order"
    :order-id="order.id"
    :items="order.items || []"
  />
</el-tab-pane>
~~~

Do not add external tasks to the internal design/production/installation counts or change OrderProjectOverview status shortcuts.

- [ ] **Step 4: Run frontend checks**

~~~bash
cd /opt/adcraft/frontend
npm run typecheck
npm run lint
npx vitest run src/utils/outsourceTaskGrouping.test.ts
npm run build
~~~

Expected: the new component, order-detail tab, and route navigation compile and build successfully.

- [ ] **Step 5: Commit the order-detail panel**

~~~bash
cd /opt/adcraft
git add frontend/src/components/outsource/OrderOutsourcePanel.vue frontend/src/views/orders/OrderDetail.vue
git diff --cached --check
git commit -m "feat: show outsource tasks by order item"
~~~

---
### Task 8: Update product and API documentation

**Files:**

- Modify: docs/02_功能模块PRD.md:外协管理章节
- Modify: docs/04_API接口设计.md:外协接口章节

**Interfaces:**

- Consumes: The final backend field names, endpoint path, cost predicate, and UI labels from Tasks 1–7.
- Produces: Documentation that describes order_item_id, order_item_name, the item dropdown endpoint, order-level compatibility, and cost semantics.

- [ ] **Step 1: Add the product behavior text**

Under the external-task feature section of docs/02_功能模块PRD.md, add this exact behavior block:

~~~markdown
### 订单明细级外协

外协任务可以关联一个订单明细。未选择订单明细时表示整单外协，历史任务和运输类整单任务继续兼容。

- 订单明细关联只适用于订单，不适用于报价单；
- 一个外协任务一期只关联一个订单明细；跨多个明细的任务拆分创建；
- 订单明细被编辑替换后，原外协任务保留，明细关联置空；
- 已完成或已结算且未删除的外协任务计入订单成本；
- 外协任务成本不修改订单销售金额和订单明细销售字段；
- 本功能不自动改变订单主状态或订单明细状态。
~~~

- [ ] **Step 2: Add the API contract text**

Under the external-task API section of docs/04_API接口设计.md, add:

~~~markdown
#### 外协任务订单明细字段

POST /outsource/tasks 和 PUT /outsource/tasks/{task_id} 支持可选字段 order_item_id。

GET /outsource/tasks 支持 order_item_id 查询参数。响应包含 order_item_id 和 order_item_name；两者为空时表示整单外协。

#### 获取订单明细下拉数据

GET /outsource/orders/{order_id}/items-for-dropdown

该接口只返回有效订单的明细，返回字段为 id、label、item_name、quantity、unit、group_name、sort_order。报价单不能使用订单明细字段。
~~~

- [ ] **Step 3: Check documentation formatting and commit**

~~~bash
cd /opt/adcraft
git diff --check
git add docs/02_功能模块PRD.md docs/04_API接口设计.md
git diff --cached --check
git commit -m "docs: describe outsource order item behavior"
~~~

Expected: the commit contains only the two documentation files and has no whitespace errors.

---
### Task 9: Run complete verification and prepare the rollout

**Files:**

- Verify: backend/app/models/outsource.py
- Verify: backend/alembic/versions/j4k5l6m7n8o9_add_outsource_order_item_fk.py
- Verify: backend/app/schemas/outsource.py
- Verify: backend/app/repositories/outsource_repo.py
- Verify: backend/app/services/outsource_service.py
- Verify: backend/app/api/outsource.py
- Verify: backend/app/services/order_cost_service.py
- Verify: backend/app/services/business_document_service.py
- Verify: frontend/src/types/api.ts
- Verify: frontend/src/api/outsource.ts
- Verify: frontend/src/utils/outsourceTaskGrouping.ts
- Verify: frontend/src/views/outsource/OutsourceTaskList.vue
- Verify: frontend/src/components/outsource/OutsourceTaskCard.vue
- Verify: frontend/src/components/outsource/OrderOutsourcePanel.vue
- Verify: frontend/src/views/orders/OrderDetail.vue

**Interfaces:**

- Consumes: All implementation commits from Tasks 1–8.
- Produces: Fresh test evidence, migration evidence, a clean feature diff, and a deployment-ready revision.

- [ ] **Step 1: Run the complete backend test suite**

~~~bash
cd /opt/adcraft/backend
.venv/bin/pytest -q
~~~

Expected: exit code 0 with all backend tests passing.

- [ ] **Step 2: Run the complete frontend quality suite**

~~~bash
cd /opt/adcraft/frontend
npm run lint
npm run typecheck
npm run test
npm run build
npm run check:ai-contract
~~~

Expected: all commands exit 0 and Vite produces the normal production build.

- [ ] **Step 3: Run repository-level checks**

~~~bash
cd /opt/adcraft
git diff --check
git log -n 10 --oneline
git status --short --branch
./scripts/pre-deploy-check.sh
~~~

Expected: the feature commits are identifiable, no tracked file has whitespace errors, and existing user-owned .bak, .tmp, and frontend/dist.bak-* files remain untracked and are not staged or deleted.

- [ ] **Step 4: Back up the production database before migration**

~~~bash
cd /opt/adcraft
./scripts/backup.sh
latest_backup=$(find backups -maxdepth 1 -type f -name 'backup_*.tar.gz' -printf '%T@ %p\n' | sort -n | tail -1 | cut -d' ' -f2-)
test -n "$latest_backup"
test -s "$latest_backup"
echo "$latest_backup"
~~~

Expected: the script prints a newly created non-empty archive path. Keep the archive for rollback evidence.

- [ ] **Step 5: Execute the migration with the preflight data check**

Run the preflight query against the live database before upgrade:

~~~bash
sudo -u postgres psql -d adcraft_erp -v ON_ERROR_STOP=1 -c "SELECT COUNT(*) AS invalid_order_item_links FROM outsource_tasks AS task LEFT JOIN business_document_items AS item ON item.id = task.order_item_id WHERE task.order_item_id IS NOT NULL AND item.id IS NULL;"
~~~

Expected: invalid_order_item_links is 0.

Then run:

~~~bash
cd /opt/adcraft/backend
.venv/bin/alembic upgrade head
.venv/bin/alembic current
~~~

Expected: the new revision is the current head and no application row is changed by the migration.

- [ ] **Step 6: Verify the live constraint and index**

~~~bash
sudo -u postgres psql -d adcraft_erp -v ON_ERROR_STOP=1 -c "SELECT conname, confdeltype FROM pg_constraint WHERE conname = 'fk_outsource_tasks_order_item_id';"
sudo -u postgres psql -d adcraft_erp -v ON_ERROR_STOP=1 -c "SELECT indexname FROM pg_indexes WHERE indexname = 'ix_outsource_order_item';"
~~~

Expected: the constraint exists with delete action SET NULL (confdeltype = 'n') and the index query returns one row.

- [ ] **Step 7: Verify the application paths without an OS reboot**

After code publication and migration, verify the active service and restart only the application process that owns the changed backend code:

~~~bash
systemctl is-active adcraft-backend
systemctl restart adcraft-backend
systemctl is-active adcraft-backend
curl -fsS http://127.0.0.1/health
~~~

If the deployment uses the project’s Docker Compose path instead of the systemd unit, use the existing scripts/deploy.sh --local flow and verify adcraft_backend and adcraft_nginx are running. Do not reboot the host. Validate these user paths after restart:

1. Select an order in 外协任务 and verify its order-item selector loads only that order’s items.
2. Create one item-linked task and one order-level task.
3. Open the order’s 外协任务 tab and verify both rows display under the correct labels.
4. Complete the item-linked task and verify the order cost increases by its external cost.
5. Soft-delete it and verify the order cost decreases and the task leaves the active panel.
6. Edit the order sales total and verify the external task’s unit price and total amount remain unchanged.

- [ ] **Step 8: Record final revision and working-tree evidence**

~~~bash
cd /opt/adcraft
git log -n 12 --oneline
git diff --check
git status --short --branch
~~~

Expected: the final feature revision is identifiable in Git, all required verification commands have fresh exit-code evidence, and no unrelated backup artifact is included in a commit.
