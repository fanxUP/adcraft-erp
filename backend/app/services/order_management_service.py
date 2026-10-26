"""Order-first entry points and durable reconciliation, within one unit of work.

This module never commits. HTTP get_db owns the transaction; original receipts,
allocations and execution facts are retained as an append-only business ledger.
"""
from datetime import datetime, time, timedelta
from decimal import Decimal
import hmac
from uuid import UUID, uuid4

from sqlalchemy import exists, func, select, text
from sqlalchemy.orm import selectinload

from app.models.business_document import BusinessDocument, BusinessDocumentVersion, OrderChangeAction
from app.models.customer import Customer
from app.models.payment import Payment, PaymentAllocation
from app.repositories.payment_repo import PaymentRepository
from app.services.quote_calculation import calculate_quote_totals, normalize_quote_item_data

ZERO = Decimal("0.00")


def money(value):
    return Decimal(str(value or 0)).quantize(Decimal("0.01"))


def document_totals(subtotals, *, discount_amount=0, tax_rate=0, settlement_adjustment=0):
    result = calculate_quote_totals(list(subtotals), discount_amount=discount_amount or 0, tax_rate=tax_rate or 0)
    result["total_amount"] = money(result["total_amount"] + money(settlement_adjustment))
    if result["total_amount"] < 0:
        raise ValueError("结算金额不能为负数")
    return result


def settlement_values(total, paid, cost):
    total, paid, cost = money(total), money(paid), money(cost)
    return {"total_amount": float(total), "paid_amount": float(paid),
            "unpaid_amount": float(max(total - paid, ZERO)),
            "overpaid_amount": float(max(paid - total, ZERO)),
            "cost_amount": float(cost), "gross_profit": float(total - cost)}


class OrderManagementService:
    def __init__(self, db, viewer=None):
        from app.services.business_document_service import BusinessDocumentService
        self.db, self.viewer = db, viewer
        self.documents = BusinessDocumentService(db, doc_type="order", viewer=viewer)

    async def _audit(self, order_id, action, data):
        from app.services.operation_log_service import log_operation
        await log_operation(self.db, getattr(self.viewer, "id", None),
                            getattr(self.viewer, "real_name", None) or getattr(self.viewer, "username", None),
                            "order", order_id, action, after_data=self.documents._json_safe(data))

    async def _lock_request(self, request_id):
        # All processes serialize a retried request before reading its result.
        await self.db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
                              {"key": f"order-request:{request_id}"})

    async def _order(self, order_id, *, deleted=False, lock=False):
        query = select(BusinessDocument).execution_options(populate_existing=True).where(BusinessDocument.id == order_id, BusinessDocument.doc_type == "order")
        if not deleted:
            query = query.where(BusinessDocument.deleted_at.is_(None))
        if lock:
            query = query.with_for_update()
        doc = (await self.db.execute(query)).scalar_one_or_none()
        if not doc:
            raise ValueError("订单不存在")
        if lock:
            await self.documents._lock_order_dependencies(order_id)
        return doc

    async def create(self, data):
        from app.services.number_generator import generate_order_no
        from app.services.order_customer_service import ensure_document_customer
        capture = None
        if data.get("capture_id"):
            from app.models.cdr_quote import CdrCaptureSession
            from app.core.permissions import user_has_permission
            capture = await self.db.get(CdrCaptureSession, data["capture_id"])
            if not capture or (capture.employee_id != getattr(self.viewer, "id", None) and not user_has_permission(self.viewer, "system:super_admin")):
                raise ValueError("图稿采集不存在或无权使用")
        request_id = data.get("capture_id") or data["request_id"]
        await self._lock_request(request_id)
        existing = (await self.db.execute(select(BusinessDocument.id).where(BusinessDocument.creation_request_id == request_id))).scalar_one_or_none()
        if existing:
            doc = await self._order(existing, deleted=True)
            if self.viewer and doc.sales_user_id != self.viewer.id:
                raise ValueError("该创建凭据已使用，请重新创建")
            if doc.deleted_at:
                raise ValueError("此前创建的订单已在回收站，请先恢复，不能重复创建")
            return await self.documents.get_by_id(existing)
        header = dict(data["header"])
        if not str(header.get("project_name") or "").strip():
            raise ValueError("请填写项目名称")
        customer_id = header.get("customer_id")
        if customer_id:
            customer_id = UUID(str(customer_id))
            customer = await self.db.get(Customer, customer_id)
            if not customer or customer.deleted_at:
                raise ValueError("客户不存在或已删除")
            header["customer_id"] = customer_id
            header["customer_name"] = None
        elif not str(header.get("customer_name") or "").strip():
            raise ValueError("请选择客户或填写客户名称")
        items = []
        for index, item in enumerate(data["items"]):
            raw = {key: value for key, value in item.items() if key != "id"}
            if not str(raw.get("item_name") or "").strip():
                raise ValueError("明细名称不能为空")
            items.append({**normalize_quote_item_data(raw), "sort_order": index})
        totals = document_totals([item["subtotal_amount"] for item in items],
                                 discount_amount=header.get("discount_amount"), tax_rate=header.get("tax_rate"))
        deadline = header.get("delivery_deadline")
        if isinstance(deadline, str):
            header["delivery_deadline"] = datetime.fromisoformat(deadline) if deadline else None
        doc = await self.documents.repo.create({**header, **totals, "items": items,
            "groups": data.get("groups", []), "doc_type": "order", "doc_no": await generate_order_no(self.db),
            "status": "pending_confirm", "order_date": data["order_date"], "creation_request_id": request_id,
            "sales_user_id": getattr(self.viewer, "id", None), "paid_amount": ZERO,
            "unpaid_amount": totals["total_amount"], "cost_amount": ZERO, "gross_profit": totals["total_amount"]})
        await ensure_document_customer(self.db, doc, getattr(self.viewer, "id", None))
        await self.db.flush()
        result = await self.documents.get_by_id(doc.id)
        await self.documents.repo.create_version(doc.id, 1, {"change_type": "order_created", "after": result,
            "change_batch_id": str(request_id)}, getattr(self.viewer, "id", None))
        await self._audit(doc.id, "create", result)
        if capture:
            from app.models.cdr_quote import DrawingSnapshot
            self.db.add(DrawingSnapshot(snapshot_code="DS-" + capture.session_code, capture_session_id=capture.id,
                quote_id=doc.id, drawing_fingerprint=capture.drawing_fingerprint,
                object_summary_json=capture.capture_payload_json, created_by=getattr(self.viewer, "id", None)))
            await self.db.flush()
        return result

    async def persist_actions(self, doc, batch_id, refresh, *, before=None, after=None):
        entries = [("review", row) for row in refresh.get("pending_review", [])]
        entries += [("adjustment", row) for row in refresh.get("adjustments", [])]
        source_changed = before is not None and (after is None or money(before.get("total_amount")) != money(after.get("total_amount")) or before.get("items") != after.get("items"))
        refreshed_keys = {(entry.get("module"), entry.get("record_id")) for entry in refresh.get("auto_refreshed", [])}
        if source_changed:
            for row in refresh.get("preserved_facts", []):
                if row.get("module") in {"contracts", "framework_contracts", "customer_statements", "stock_records"} and (row.get("module"), row.get("record_id")) not in refreshed_keys:
                    entry = {**row, "detail": "原确认记录保留，请登记补充协议、后续对账或退补料处理凭据"}
                    entries.append(("adjustment", entry))
                    refresh.setdefault("adjustments", []).append(entry)
        if money(doc.paid_amount) > money(doc.total_amount):
            entries.append(("funds", {"module": "payments", "record_id": str(doc.id), "record_no": doc.doc_no,
                                      "detail": f"超收 ¥{money(doc.paid_amount) - money(doc.total_amount)}，请登记实际退款或转为预收"}))
        # apply is already serialized and idempotent by batch. Do not perform
        # N extra lookups; deduplicate this batch and keep the DB unique guard.
        keys = set()
        for kind, row in entries:
            key = (row.get("module") or "order", str(row.get("record_id") or doc.id), kind)
            if key in keys:
                continue
            keys.add(key)
            self.db.add(OrderChangeAction(document_id=doc.id, batch_id=str(batch_id), module=key[0], record_key=key[1],
                record_no=row.get("record_no"), action_type=kind, detail=row.get("detail") or row.get("note") or "订单变更待处理",
                assigned_to=doc.sales_user_id, context=self.documents._json_safe({"before": before, "after": after, "association": row})))
        refresh["status"] = "PENDING_ADJUSTMENT" if entries else "VERIFIED"
        refresh["counts"] = {key: len(refresh.get(key, [])) for key in ("auto_refreshed", "preserved_facts", "pending_review", "adjustments", "blocked")}
        await self.db.flush()

    async def sync_execution(self, doc, batch_id, operations, before, refresh):
        """Refresh open demand; keep terminal scopes as historical work facts."""
        from app.models.task import DesignTask, ProductionTask, InstallationTask
        from app.models.task_order_item_link import TaskOrderItemLink
        from app.services.number_generator import generate_design_no, generate_production_no, generate_installation_no
        from app.services.business_document_service import TASK_REVIEW_ITEM_FIELDS
        if doc.status in {"pending_confirm", "cancelled"}:
            return
        originals = {item["id"]: item for item in (before or {}).get("items", [])}
        active = {str(item.id): item for item in await self.documents.repo.get_items(doc.id)}
        execution_ops = [op for op in operations if op["operation"] == "add" or
                         set(op.get("changed_fields", ())) & TASK_REVIEW_ITEM_FIELDS]
        task_specs = [("design", DesignTask, "design_no", generate_design_no),
                      ("production", ProductionTask, "production_no", generate_production_no),
                      ("installation", InstallationTask, "installation_no", generate_installation_no)]
        all_links = []
        for kind, model, _, _ in task_specs:
            tasks = (await self.db.execute(select(model).where(model.document_id == doc.id).with_for_update())).scalars().all()
            task_by_id = {task.id: task for task in tasks}
            if task_by_id:
                links = (await self.db.execute(select(TaskOrderItemLink).where(TaskOrderItemLink.task_type == kind,
                    TaskOrderItemLink.task_id.in_(task_by_id), TaskOrderItemLink.link_status == "active").with_for_update())).scalars().all()
                all_links += [(kind, task_by_id[link.task_id], link) for link in links]
            for task in tasks:
                if task.status not in {"confirmed", "completed", "cancelled"}:
                    task.project_name, task.customer_id = doc.project_name, doc.customer_id
                    if kind == "installation":
                        task.address, task.contact_name, task.contact_phone = doc.installation_address, doc.contact_person, doc.contact_phone
        followup = []
        for op in execution_ops:
            item_id = str(op.get("item_id") or "")
            item = active.get(item_id)
            if not item or op["operation"] == "delete":
                continue
            old = originals.get(item_id, {})
            links = [(kind, task, link) for kind, task, link in all_links if str(link.order_item_id) == item_id]
            for _, task, link in links:
                if link.scope_snapshot is None:
                    link.scope_snapshot = old or self.documents._item_snapshot(item)
                if link.planned_quantity is None:
                    link.planned_quantity = Decimal(str(old.get("quantity") or item.quantity))
                status = link.item_status or task.status
                if status in {"confirmed", "completed"} and link.completed_quantity is None:
                    link.completed_quantity = link.planned_quantity
                elif status == "pending" and link.completed_quantity is None:
                    link.completed_quantity = Decimal("0")
            terminals = bool(links) and all((link.item_status or task.status) in {"confirmed", "completed", "cancelled"} for _, task, link in links)
            if op["operation"] == "add" or terminals or (doc.status == "completed" and not links):
                fields = set(op.get("changed_fields", ())) - {"quantity"}
                quantity_only = op["operation"] != "add" and not (fields & TASK_REVIEW_ITEM_FIELDS)
                delta = Decimal(str(item.quantity)) - Decimal(str(old.get("quantity") or 0))
                required = max(delta, Decimal("0")) if quantity_only else Decimal(str(item.quantity))
                if required > 0:
                    for _, _, link in links:
                        link.link_status, link.removed_at = "removed", datetime.now()
                        link.removed_reason = f"订单变更 {batch_id}：原执行范围保留为历史，新范围另行安排"
                    followup.append((item, required))
                elif delta < 0:
                    refresh.setdefault("adjustments", []).append({"module": "execution", "record_id": item_id,
                        "detail": f"{item.item_name}：已完成原范围 {old.get('quantity')}，当前需求 {item.quantity}，请确认超做部分交付/退回/损耗"})
            else:
                for _, task, link in links:
                    if (link.item_status or task.status) not in {"confirmed", "completed", "cancelled"}:
                        # Unknown historical partial completion stays unknown;
                        # progress percentage is never converted to actual units.
                        if "quantity" in op.get("changed_fields", ()):
                            delta = Decimal(str(item.quantity)) - Decimal(str(old.get("quantity") or 0))
                            link.planned_quantity = max(Decimal(str(link.planned_quantity)) + delta, Decimal("0"))
                            if link.completed_quantity is not None and link.completed_quantity > link.planned_quantity:
                                refresh.setdefault("adjustments", []).append({"module": "execution", "record_id": str(link.id),
                                    "detail": f"{item.item_name}：当前任务已做 {link.completed_quantity}，变更后本任务需求 {link.planned_quantity}，请核对超做处理"})
        if followup:
            # New work has its own card, preserving previous completion facts.
            stage = {"in_production": "production", "in_installation": "installation"}.get(doc.status, "design")
            kind, model, number_field, generate_no = next(spec for spec in task_specs if spec[0] == stage)
            kwargs = {number_field: await generate_no(self.db), "document_id": doc.id, "order_item_id": None,
                      "customer_id": doc.customer_id, "project_name": doc.project_name, "status": "pending"}
            if kind == "production":
                kwargs["quantity"] = sum((quantity for _, quantity in followup), Decimal("0"))
            if kind == "installation":
                kwargs.update(address=doc.installation_address, contact_name=doc.contact_person, contact_phone=doc.contact_phone)
            task = model(**kwargs)
            self.db.add(task)
            await self.db.flush()
            for index, (item, quantity) in enumerate(followup):
                self.db.add(TaskOrderItemLink(task_type=kind, task_id=task.id, order_item_id=item.id,
                    position=index, item_status="pending", item_progress_pct=0, planned_quantity=quantity,
                    completed_quantity=0, scope_snapshot={**self.documents._item_snapshot(item), "task_origin": "order_followup"}))
            if doc.status == "completed":
                doc.status = "designing"
                await self.documents.repo.create_status_log(doc.id, "completed", doc.status,
                    "订单有新增执行范围，原完成记录保留", getattr(self.viewer, "id", None))
            refresh.setdefault("auto_refreshed", []).append({"module": f"{kind}_tasks", "record_id": str(task.id),
                "record_no": getattr(task, number_field), "detail": "新增/补做范围已生成独立待执行任务，原完成记录保留"})
        await self.db.flush()

    async def sync_drafts(self, doc, before, refresh):
        """Refresh only demonstrably order-derived draft snapshots."""
        from app.models.acceptance import AcceptanceForm, AcceptanceItem
        from app.models.contract import Contract, ContractDocument
        from app.models.framework_contract import FrameworkContractProject, FrameworkContractProjectDocument
        from app.services.payment_service import StatementService
        customers = {doc.customer_id}
        if (before or {}).get("customer_id"):
            customers.add(UUID(str(before["customer_id"])))
        statements = []
        for customer_id in sorted(customers, key=str):
            statements.extend(await StatementService(self.db).refresh_drafts_for_customer(customer_id))
        refresh.setdefault("auto_refreshed", []).extend({"module": "customer_statements", "record_id": str(row.id), "record_no": row.statement_no, "detail": "已刷新草稿对账汇总"} for row in statements)
        items = await self.documents.repo.get_items(doc.id)
        active = {item.id: item for item in items}
        old_ids = {UUID(item["id"]) for item in (before or {}).get("items", [])}
        forms = (await self.db.execute(select(AcceptanceForm).where(AcceptanceForm.document_id == doc.id,
            AcceptanceForm.deleted_at.is_(None), AcceptanceForm.status.in_(["draft", "rejected"])).with_for_update())).scalars().all()
        refreshed = set()
        for form in forms:
            mapping = {line.document_item_id: line for line in form.items if line.document_item_id}
            full_scope = set(mapping) == old_ids and len(mapping) == len(form.items)
            for item_id, line in mapping.items():
                item = active.get(item_id)
                if not item or line.item_status in {"accepted", "conditional"}:
                    continue
                projected = self.documents._item_snapshot(item)
                for target, source in {"item_name": "item_name", "material_process": "material_process", "specification": "specification",
                    "quantity": "quantity", "unit": "unit", "area": "area", "unit_price": "unit_price", "subtotal": "subtotal_amount",
                    "image_url": "image_url", "group_name": "group_name"}.items():
                    setattr(line, target, projected.get(source))
            if full_scope:
                for item in items:
                    if item.id not in mapping:
                        projected = self.documents._item_snapshot(item)
                        self.db.add(AcceptanceItem(acceptance_id=form.id, document_item_id=item.id, item_name=item.item_name,
                            material_process=item.material_process, specification=projected.get("specification"), quantity=item.quantity,
                            unit=item.unit, area=item.area, unit_price=item.unit_price, subtotal=item.subtotal_amount, image_url=item.image_url, group_name=item.group_name))
                refreshed.add(("acceptance_forms", str(form.id)))
        contracts = (await self.db.execute(select(Contract).join(ContractDocument, ContractDocument.contract_id == Contract.id)
            .where(ContractDocument.document_id == doc.id, Contract.deleted_at.is_(None), Contract.status == "draft").with_for_update(of=Contract))).scalars().all()
        for contract in contracts:
            linked = [record for record in contract.documents if record.doc_type == "order"]
            current_total = sum((money(record.total_amount) for record in linked), ZERO)
            old_total = current_total - money(doc.total_amount) + money((before or {}).get("total_amount"))
            if money(contract.total_amount) == old_total:
                contract.total_amount = current_total
                contract.unpaid_amount = max(current_total - money(contract.paid_amount), ZERO)
                refreshed.add(("contracts", str(contract.id)))
        projects = (await self.db.execute(select(FrameworkContractProject)
            .join(FrameworkContractProjectDocument, FrameworkContractProjectDocument.project_id == FrameworkContractProject.id)
            .where(FrameworkContractProjectDocument.document_id == doc.id, FrameworkContractProject.deleted_at.is_(None)).with_for_update(of=FrameworkContractProject))).scalars().all()
        for project in projects:
            if project.contract.status == "draft" and len(project.documents) == 1 and money(project.project_amount) == money((before or {}).get("total_amount")):
                project.project_amount = doc.total_amount
                refreshed.add(("framework_contracts", str(project.id)))
        for module, key in sorted(refreshed):
            refresh.setdefault("auto_refreshed", []).append({"module": module, "record_id": key, "detail": "已按明确订单来源刷新草稿内容"})
        refresh["pending_review"] = [row for row in refresh.get("pending_review", []) if (row.get("module"), row.get("record_id")) not in refreshed]
        await self.db.flush()

    async def _action_capabilities(self, row):
        """Apply module rights and the existing order/employee delivery scope."""
        from app.core.access_policy import AuthorizationPolicy
        from app.models.task import DesignTask, ProductionTask, InstallationTask
        from app.services.order_task_assignment_service import task_visibility_clause
        policy = AuthorizationPolicy(self.viewer)
        modules = {
            "payments": ("payment:read", "payment:create"),
            "project_costs": ("expense:read", "expense:update"),
            "contracts": ("contract:read", "contract:update"),
            "framework_contracts": ("contract:read", "contract:update"),
            "customer_statements": ("statement:read", "statement:confirm"),
            "outsource_tasks": ("outsource_task:read", "outsource_task:update"),
            "acceptance_forms": ("acceptance:read", "acceptance:update"),
            "acceptance_items": ("acceptance:read", "acceptance:update"),
            "stock_records": ("inventory:read", "inventory:update"),
        }
        task_sources = {"design": DesignTask, "production": ProductionTask, "installation": InstallationTask}
        task_type = next((kind for kind in task_sources if row.module in {f"{kind}_tasks", f"{kind}_task_links"}), None)
        if task_type:
            modules[row.module] = (f"{task_type}_task:read", f"{task_type}_task:update")
        read, write = modules.get(row.module, ("order:read", "order:update"))
        readable = policy.allows(read)
        if readable and task_type:
            model = task_sources[task_type]
            readable = bool(await self.db.scalar(select(exists().where(
                model.document_id == row.document_id, task_visibility_clause(model, self.viewer)))))
        writable = readable and policy.allows(write) and row.status == "pending"
        return readable, writable, "" if writable else "当前账号无处理权限或事项已处理"

    async def list_actions(self, order_id):
        await self._order(order_id, deleted=True)
        rows = (await self.db.execute(select(OrderChangeAction).where(OrderChangeAction.document_id == order_id)
                                     .order_by(OrderChangeAction.created_at.desc(), OrderChangeAction.id))).scalars().all()
        result = []
        for row in rows:
            readable, writable, reason = await self._action_capabilities(row)
            if not readable:
                continue
            result.append({"id": str(row.id), "batch_id": row.batch_id, "module": row.module, "record_no": row.record_no,
                 "action_type": row.action_type, "detail": row.detail, "status": row.status,
                 "assigned_to": str(row.assigned_to) if row.assigned_to else None, "resolution": row.resolution,
                 "created_at": row.created_at.isoformat(), "can_resolve": writable, "resolve_reason": reason,
                 "resolved_at": row.resolved_at.isoformat() if row.resolved_at else None})
        return result

    async def resolve_action(self, order_id, action_id, resolution):
        doc = await self._order(order_id, deleted=True, lock=True)
        row = (await self.db.execute(select(OrderChangeAction).where(OrderChangeAction.id == action_id,
            OrderChangeAction.document_id == order_id).with_for_update())).scalar_one_or_none()
        if not row:
            raise ValueError("处理事项不存在")
        readable, writable, _ = await self._action_capabilities(row)
        if not readable or not writable:
            raise ValueError("请由具备该关联业务操作权限的人员登记处理结果，已处理事项不能重复改写")
        if row.action_type == "funds" and money(doc.paid_amount) > money(doc.total_amount):
            raise ValueError("超收款尚未退款或转预收，请先完成资金处理")
        if not resolution.strip():
            raise ValueError("请填写处理结果及相关凭据编号")
        row.status, row.resolution = "resolved", resolution.strip()
        row.resolved_by, row.resolved_at = getattr(self.viewer, "id", None), datetime.now()
        await self._audit(doc.id, "resolve_change", {"action_id": str(action_id), "resolution": row.resolution})
        await self.db.flush()
        return {"id": str(row.id), "status": row.status}

    async def deletion_preview(self, order_id, data):
        if not data["reason"].strip():
            raise ValueError("请填写删除原因")
        doc = await self._order(order_id)
        self.documents._assert_expected_updated_at(doc, data["expected_updated_at"])
        relations = await self.documents._collect_order_item_relations(doc)
        for entry in relations.get("association_catalog", []):
            if entry["module"] in {"design_tasks", "production_tasks", "installation_tasks", "design_task_links", "production_task_links", "installation_task_links"}:
                entry["note"] = "未完成任务停止执行；已完成范围保留，恢复时只还原本次取消的任务"
            elif entry["module"] in {"payments", "project_costs", "stock_records"}:
                entry["note"] = "保留实际发生记录及原凭据，按最终结算核对待收或待退差额"
        paid = await self.documents._get_nonvoided_payment_total(doc.id)
        context = {"association_catalog": relations.get("association_catalog", []),
                   "before": settlement_values(doc.total_amount, paid, doc.cost_amount),
                   "after": settlement_values(data["settlement_amount"], paid, doc.cost_amount)}
        preview_id, expiry = str(uuid4()), (datetime.now() + timedelta(minutes=10)).isoformat()
        signature = self.documents._make_preview_hash(doc_id=doc.id, operation="cancel_order", item_id=None,
            data={"settlement_amount": str(money(data["settlement_amount"]))}, reason=data["reason"],
            expected_updated_at=data["expected_updated_at"], preview_id=preview_id, preview_expires_at=expiry,
            context=context, operated_by=getattr(self.viewer, "id", None))
        return {**context, "order_id": str(doc.id), "order_no": doc.doc_no, "preview_id": preview_id,
                "plan_hash": signature, "preview_expires_at": expiry}

    async def cancel_outsourcing(self, doc, refresh, *, previous_catalog=None, cancellation_snapshot=None):
        from app.models.outsource import OutsourceTask
        previous = {row["record_id"]: row.get("status") for row in previous_catalog or [] if row.get("module") == "outsource_tasks"}
        tasks = (await self.db.execute(select(OutsourceTask).where(OutsourceTask.related_doc_id == doc.id,
            OutsourceTask.related_doc_type == "order").with_for_update())).scalars().all()
        for task in tasks:
            prior = previous.get(str(task.id), task.status)
            if task.deleted_at:
                # A line-level refresh may already have cancelled this row in
                # the same batch. Pre-existing recycled rows are absent from
                # the signed catalogue and must never be revived.
                if str(task.id) in previous and prior in {"pending", "draft"} and task.status == "cancelled" and not money(task.paid_amount) and cancellation_snapshot is not None:
                    cancellation_snapshot.setdefault("outsource_tasks", []).append({"id": str(task.id), "status": prior, "deleted_at": task.deleted_at.isoformat()})
                continue
            if task.status in {"pending", "draft"} and not money(task.paid_amount):
                prior = task.status
                task.status, task.deleted_at = "cancelled", datetime.now()
                if cancellation_snapshot is not None:
                    cancellation_snapshot.setdefault("outsource_tasks", []).append({"id": str(task.id), "status": prior, "deleted_at": task.deleted_at.isoformat()})
            elif task.status != "cancelled":
                refresh["adjustments"].append({"module": "outsource_tasks", "record_id": str(task.id),
                    "record_no": task.task_no, "detail": "订单已取消，请确认外协取消范围及最终结算，原付款和成本保留"})

    async def delete(self, order_id, data):
        doc = await self._order(order_id, deleted=True, lock=True)
        if doc.deleted_at:
            applied = await self.documents._find_applied_mutation(order_id, data.get("preview_id"))
            if applied:
                return {"id": str(order_id), "deleted": True, "idempotent_replay": True}
            raise ValueError("订单已在回收站")
        current = await self.deletion_preview(order_id, data)
        expiry = data.get("preview_expires_at")
        if not expiry or datetime.fromisoformat(expiry) <= datetime.now():
            raise ValueError("删除预览已过期，请重新确认")
        expected = self.documents._make_preview_hash(doc_id=doc.id, operation="cancel_order", item_id=None,
            data={"settlement_amount": str(money(data["settlement_amount"]))}, reason=data["reason"],
            expected_updated_at=data["expected_updated_at"], preview_id=data.get("preview_id"), preview_expires_at=expiry,
            context={key: current[key] for key in ("association_catalog", "before", "after")},
            operated_by=getattr(self.viewer, "id", None))
        if not data.get("preview_id") or not hmac.compare_digest(expected, data.get("plan_hash") or ""):
            raise ValueError("关联数据已变化，请重新预览删除影响")
        before = await self.documents.get_by_id(doc.id)
        from app.services.payment_service import StatementService
        await StatementService(self.db).capture_confirmed_for_customer(doc.customer_id)
        batch_id = data["preview_id"]
        refresh = {"pending_review": [], "adjustments": []}
        # Cancelling work does not remove completed work, financial records or
        # signed acceptance forms. The change keeps an actionable directory.
        cancel_snapshot = await self.documents._cancel_open_tasks(doc.id)
        await self.cancel_outsourcing(doc, refresh, previous_catalog=current["association_catalog"], cancellation_snapshot=cancel_snapshot)
        for entry in current["association_catalog"]:
            if entry["module"] not in {"design_tasks", "production_tasks", "installation_tasks", "outsource_tasks"}:
                refresh["pending_review"].append({**entry, "detail": "订单已取消，请核对本项实际发生记录及取消差额"})
        previous_status = doc.status
        doc.settlement_adjustment = money(doc.settlement_adjustment) + money(data["settlement_amount"]) - money(doc.total_amount)
        doc.total_amount = money(data["settlement_amount"])
        doc.paid_amount = money(await self.documents._get_nonvoided_payment_total(doc.id))
        doc.unpaid_amount = max(doc.total_amount - doc.paid_amount, ZERO)
        doc.gross_profit = doc.total_amount - money(doc.cost_amount)
        doc.status, doc.deleted_at, doc.updated_at = "cancelled", datetime.now(), datetime.now()
        await self.db.flush()
        await StatementService(self.db).refresh_drafts_for_customer(doc.customer_id)
        await self.persist_actions(doc, batch_id, refresh, before=before)
        snapshot = {"change_type": "order_cancelled", "change_batch_id": batch_id, "reason": data["reason"],
                    "before": before, "after": settlement_values(doc.total_amount, doc.paid_amount, doc.cost_amount),
                    "association_catalog": current["association_catalog"], "cancel_snapshot": cancel_snapshot, "refresh_result": refresh}
        await self.documents.repo.create_version(doc.id, await self.documents.repo.get_next_version_no(doc.id), snapshot, getattr(self.viewer, "id", None))
        await self.documents.repo.create_status_log(doc.id, previous_status, "cancelled", data["reason"], getattr(self.viewer, "id", None))
        await self._audit(doc.id, "delete", snapshot)
        await self.db.flush()
        return {"id": str(doc.id), "deleted": True, "change_batch_id": batch_id, "after": snapshot["after"]}

    async def funds(self, order_id):
        from app.services.payment_service import PaymentService
        doc = await self._order(order_id, deleted=True)
        repo = PaymentRepository(self.db)
        rows, _ = await repo.list_payments(order_id=order_id, limit=200)
        # Include contract-only credit candidates for this same customer.
        credits = (await self.db.execute(select(Payment).options(selectinload(Payment.document).selectinload(BusinessDocument.customer), selectinload(Payment.allocations).selectinload(PaymentAllocation.contract), selectinload(Payment.allocations).selectinload(PaymentAllocation.document))
            .where(Payment.customer_id == doc.customer_id, Payment.is_voided.is_(False), Payment.amount > 0)
            .order_by(Payment.created_at.desc()).limit(200))).scalars().all()
        present = {row.id for row in rows}
        rows += [row for row in credits if row.id not in present and any(a.document_id is None for a in row.allocations)]
        payments = [PaymentService(self.db)._to_dict(row) for row in rows]
        result = {"order_id": str(doc.id), **settlement_values(doc.total_amount, await repo.get_document_paid_sum(doc.id), doc.cost_amount), "payments": payments}
        if not self.documents.can_view_finance_cost:
            result.pop("cost_amount", None); result.pop("gross_profit", None)
        return result

    async def mutate_funds(self, order_id, data):
        from app.services.number_generator import generate_payment_no
        from app.services.payment_service import PaymentService
        from app.models.contract import Contract
        await self._lock_request(data["request_id"])
        doc = await self._order(order_id, deleted=True, lock=True)
        key = f"funds:{data['request_id']}"
        previous = (await self.db.execute(select(BusinessDocumentVersion.id).where(
            BusinessDocumentVersion.document_id == doc.id,
            BusinessDocumentVersion.snapshot["change_batch_id"].astext == key))).scalar_one_or_none()
        if previous:
            return await self.funds(order_id)
        from app.services.payment_service import StatementService
        await StatementService(self.db).capture_confirmed_for_customer(doc.customer_id)
        if data["operation"] == "receipt":
            if doc.deleted_at or doc.status == "pending_confirm":
                raise ValueError("请先确认有效订单，再登记收款")
            amount = money(data["amount"])
            paid = money(await PaymentRepository(self.db).get_document_paid_sum(doc.id))
            if amount > max(money(doc.total_amount) - paid, ZERO):
                raise ValueError("收款金额超过订单未收金额")
            contract_ids = await PaymentRepository(self.db).get_contract_ids_for_document(doc.id)
            if len(contract_ids) > 1:
                raise ValueError("订单关联多个合同，请从应收管理明确选择收款合同")
            payment = Payment(payment_no=await generate_payment_no(self.db), document_id=doc.id,
                customer_id=doc.customer_id, amount=amount, record_type="receipt", request_id=data["request_id"],
                paid_at=datetime.combine(data["paid_at"], time.min), remark=data["reason"], created_by=getattr(self.viewer, "id", None))
            self.db.add(payment)
            await self.db.flush()
            if contract_ids:
                contract = await self.db.get(Contract, contract_ids[0], with_for_update=True)
                if not contract or contract.customer_id != doc.customer_id:
                    raise ValueError("合同客户归属不一致")
                self.db.add(PaymentAllocation(payment_id=payment.id, contract_id=contract.id, document_id=doc.id,
                    allocated_amount=amount, allocation_type="order", created_by=getattr(self.viewer, "id", None)))
                await self.db.flush()
                contract.paid_amount = await PaymentRepository(self.db).get_contract_paid_sum(contract.id)
                contract.unpaid_amount = max(await PaymentService(self.db)._get_contract_total(contract) - contract.paid_amount, ZERO)
            doc.paid_amount, doc.unpaid_amount, doc.updated_at = paid + amount, max(money(doc.total_amount) - paid - amount, ZERO), datetime.now()
            snapshot = {"change_type": "order_funds", "change_batch_id": key, "operation": "receipt", "payment_id": str(payment.id), "amount": str(amount), "paid_at": data["paid_at"].isoformat()}
            await self.documents.repo.create_version(doc.id, await self.documents.repo.get_next_version_no(doc.id), snapshot, getattr(self.viewer, "id", None))
            await StatementService(self.db).refresh_drafts_for_customer(doc.customer_id)
            await self._audit(doc.id, "funds", snapshot)
            await self.db.flush()
            return await self.funds(order_id)
        payment = await PaymentRepository(self.db).get_by_id(data["payment_id"], for_update=True)
        if not payment or payment.is_voided or payment.amount <= 0 or payment.customer_id != doc.customer_id:
            raise ValueError("请选择同一客户的有效原始收款凭据")
        amount, operation = money(data["amount"]), data["operation"]
        allocations = list(payment.allocations)
        matching = [a for a in allocations if a.document_id == doc.id]
        available = sum((money(a.allocated_amount) for a in matching), ZERO)
        if not allocations and payment.document_id == doc.id:
            available = money(payment.amount)
        # Refunds use their own negative payment rows. Count previous refunds
        # against this original receipt, even if other orders share the header.
        refunded = money((await self.db.execute(select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.reference_payment_id == payment.id, Payment.document_id == doc.id, Payment.is_voided.is_(False)))).scalar())
        available += refunded
        paid = money(await PaymentRepository(self.db).get_document_paid_sum(doc.id))
        if operation in {"refund", "release_credit"}:
            if amount > available or amount > max(paid - money(doc.total_amount), ZERO):
                raise ValueError("金额超过该凭据可处理金额或订单超收金额")
        elif doc.deleted_at or doc.status == "pending_confirm":
            raise ValueError("只能向有效且已确认的订单分配预收款")
        if operation == "refund":
            refund = Payment(payment_no=await generate_payment_no(self.db), document_id=doc.id,
                customer_id=doc.customer_id, amount=-amount, record_type="refund", reference_payment_id=payment.id,
                request_id=data["request_id"], paid_at=datetime.combine(data["paid_at"], time.min),
                remark=data["reason"], payment_method=payment.payment_method, created_by=getattr(self.viewer, "id", None))
            self.db.add(refund)
            await self.db.flush()
            remaining = amount
            for contract_id in sorted({a.contract_id for a in matching}, key=str):
                capacity = sum((money(a.allocated_amount) for a in matching if a.contract_id == contract_id), ZERO)
                # Earlier refund allocations reduce the available contract slice.
                old_refunds = money((await self.db.execute(select(func.coalesce(func.sum(PaymentAllocation.allocated_amount), 0))
                    .join(Payment, Payment.id == PaymentAllocation.payment_id).where(Payment.reference_payment_id == payment.id,
                    Payment.document_id == doc.id, Payment.is_voided.is_(False), PaymentAllocation.contract_id == contract_id))).scalar())
                used = min(remaining, max(capacity + old_refunds, ZERO))
                if used:
                    self.db.add(PaymentAllocation(payment_id=refund.id, contract_id=contract_id, document_id=doc.id,
                        allocated_amount=-used, allocation_type="order", created_by=getattr(self.viewer, "id", None)))
                    remaining -= used
            if allocations and remaining:
                raise ValueError("收款分配已变化，请重新核对退款来源")
        else:
            if not allocations:
                contract_ids = await PaymentRepository(self.db).get_contract_ids_for_document(doc.id)
                if len(contract_ids) != 1:
                    raise ValueError("历史收款需要先明确唯一合同归属，才可转入合同预收")
                allocation = PaymentAllocation(payment_id=payment.id, contract_id=contract_ids[0], document_id=doc.id,
                    allocated_amount=payment.amount, allocation_type="order", created_by=getattr(self.viewer, "id", None))
                self.db.add(allocation)
                allocations = matching = [allocation]
            if operation == "release_credit":
                source = matching
            else:
                order_contracts = await PaymentRepository(self.db).get_contract_ids_for_document(doc.id)
                source = [a for a in allocations if a.document_id is None and a.contract_id in order_contracts]
                if amount > max(money(doc.total_amount) - paid, ZERO):
                    raise ValueError("分配金额超过订单待收余额")
            by_contract = {cid: sum((money(a.allocated_amount) for a in source if a.contract_id == cid), ZERO)
                           for cid in {a.contract_id for a in source}}
            if operation == "release_credit" and refunded:
                # Refunds reduce the receipt's usable order balance.
                remaining_refund = -refunded
                for cid in sorted(by_contract, key=str):
                    deduction = min(max(by_contract[cid], ZERO), remaining_refund)
                    by_contract[cid] -= deduction
                    remaining_refund -= deduction
            if amount > sum((max(value, ZERO) for value in by_contract.values()), ZERO):
                raise ValueError("可用预收或订单分配金额不足")
            remaining = amount
            for cid in sorted(by_contract, key=str):
                used = min(remaining, max(by_contract[cid], ZERO))
                if not used:
                    continue
                for document_id, signed in ((doc.id, -used), (None, used)) if operation == "release_credit" else ((None, -used), (doc.id, used)):
                    self.db.add(PaymentAllocation(payment_id=payment.id, contract_id=cid, document_id=document_id,
                        allocated_amount=signed, allocation_type="order" if document_id else "contract", created_by=getattr(self.viewer, "id", None)))
                remaining -= used
        await self.db.flush()
        doc.paid_amount = money(await PaymentRepository(self.db).get_document_paid_sum(doc.id))
        doc.unpaid_amount = max(money(doc.total_amount) - doc.paid_amount, ZERO)
        doc.updated_at = datetime.now()
        for cid in sorted({a.contract_id for a in allocations}, key=str):
            contract = await self.db.get(Contract, cid, with_for_update=True)
            if contract:
                contract.paid_amount = await PaymentRepository(self.db).get_contract_paid_sum(cid)
                total = await PaymentService(self.db)._get_contract_total(contract)
                contract.unpaid_amount = max(total - contract.paid_amount, ZERO)
        if doc.paid_amount <= money(doc.total_amount):
            actions = (await self.db.execute(select(OrderChangeAction).where(OrderChangeAction.document_id == doc.id,
                OrderChangeAction.action_type == "funds", OrderChangeAction.status == "pending"))).scalars().all()
            for row in actions:
                row.status, row.resolution, row.resolved_at, row.resolved_by = "resolved", "已通过资金流水处理", datetime.now(), getattr(self.viewer, "id", None)
        snapshot = {"change_type": "order_funds", "change_batch_id": key, "operation": operation,
                    "payment_id": str(payment.id), "amount": str(amount), "reason": data["reason"], "paid_at": data["paid_at"].isoformat()}
        await self.documents.repo.create_version(doc.id, await self.documents.repo.get_next_version_no(doc.id), snapshot, getattr(self.viewer, "id", None))
        await StatementService(self.db).refresh_drafts_for_customer(doc.customer_id)
        await self._audit(doc.id, "funds", snapshot)
        await self.db.flush()
        return await self.funds(order_id)
