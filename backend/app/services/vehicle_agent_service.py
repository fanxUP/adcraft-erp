"""Vehicle Agent Service — rule-based intent recognition for WeChat/Feishu messages."""

import re
from uuid import UUID
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.vehicle import (
    VehicleAgentDraft, Vehicle, VehicleDriver, VehicleDispatch,
    VehicleFuelRecord, VehicleMaintenanceRecord, VehicleIncident,
    VehicleUseRequest,
)
from app.services.operation_log_service import (
    log_operation, OBJ_VEHICLE_AGENT_DRAFT, ACTION_CREATE, ACTION_UPDATE,
)


# ── Intent patterns ────────────────────────────────────────────────────────────

INTENT_PATTERNS = [
    # 1. vehicle_use_request — 用车申请
    {
        "intent": "vehicle_use_request",
        "confidence": 0.85,
        "risk_level": "medium",
        "suggested_action": "create_vehicle_use_request_draft",
        "requires_confirmation": True,
        "requires_finance_review": False,
        "patterns": [
            r"需要.*车",
            r"用车",
            r"安排.*车",
            r"派.*车.*去",
            r"要一辆",
            r"有没有车",
        ],
    },
    # 2. vehicle_dispatch — 派车安排
    {
        "intent": "vehicle_dispatch",
        "confidence": 0.90,
        "risk_level": "medium",
        "suggested_action": "create_vehicle_dispatch_draft",
        "requires_confirmation": True,
        "requires_finance_review": False,
        "patterns": [
            r"开.*去",
            r"[辽京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤川青藏琼宁].{1}[A-Z][A-Z0-9]{5,6}",
            r"派车",
            r"安排.*出发",
            r"司机.*开",
        ],
    },
    # 3. vehicle_start — 出车
    {
        "intent": "vehicle_start",
        "confidence": 0.90,
        "risk_level": "low",
        "suggested_action": "update_dispatch_status_started",
        "requires_confirmation": True,
        "requires_finance_review": False,
        "patterns": [
            r"出车",
            r"出发了",
            r"上路了",
            r"已经出发",
            r"开始走了",
        ],
    },
    # 4. vehicle_arrival — 到达现场
    {
        "intent": "vehicle_arrival",
        "confidence": 0.90,
        "risk_level": "low",
        "suggested_action": "update_dispatch_status_arrived",
        "requires_confirmation": True,
        "requires_finance_review": False,
        "patterns": [
            r"到了",
            r"到达",
            r"现场",
            r"已经到",
            r"抵达",
        ],
    },
    # 5. vehicle_return — 收车
    {
        "intent": "vehicle_return",
        "confidence": 0.90,
        "risk_level": "low",
        "suggested_action": "update_dispatch_status_returned",
        "requires_confirmation": True,
        "requires_finance_review": False,
        "patterns": [
            r"收车",
            r"回来了",
            r"返回了",
            r"已经回",
            r"到家了",
            r"回来了",
        ],
    },
    # 6. fuel_expense — 油费
    {
        "intent": "fuel_expense",
        "confidence": 0.88,
        "risk_level": "medium",
        "suggested_action": "create_vehicle_expense_draft",
        "requires_confirmation": True,
        "requires_finance_review": True,
        "patterns": [
            r"加油",
            r"油费",
            r"加了.*油",
            r"油钱",
            r"加满",
            r"柴油",
            r"汽油",
        ],
    },
    # 7. vehicle_issue — 车辆异常
    {
        "intent": "vehicle_issue",
        "confidence": 0.85,
        "risk_level": "high",
        "suggested_action": "create_vehicle_incident_draft",
        "requires_confirmation": True,
        "requires_finance_review": False,
        "patterns": [
            r"没气",
            r"坏了",
            r"故障",
            r"爆胎",
            r"抛锚",
            r"打不着",
            r"漏油",
            r"漏水",
            r"异响",
            r"刮蹭",
            r"追尾",
            r"撞了",
            r"事故",
            r"违章",
            r"罚单",
        ],
    },
    # 8. maintenance_request — 维修保养
    {
        "intent": "maintenance_request",
        "confidence": 0.85,
        "risk_level": "medium",
        "suggested_action": "create_maintenance_draft",
        "requires_confirmation": True,
        "requires_finance_review": True,
        "patterns": [
            r"保养",
            r"维修",
            r"该换了",
            r"该修了",
            r"该保养",
            r"换机油",
            r"换胎",
            r"换刹车",
            r"修车",
        ],
    },
    # 9. vehicle_query — 车辆查询
    {
        "intent": "vehicle_query",
        "confidence": 0.80,
        "risk_level": "low",
        "suggested_action": "query_vehicles",
        "requires_confirmation": False,
        "requires_finance_review": False,
        "patterns": [
            r"哪些车",
            r"谁在开",
            r"还有车吗",
            r"车辆.*状态",
            r"今天.*出车",
            r"哪辆车",
            r"车在哪",
        ],
    },
]


def _extract_plate_number(content: str) -> str | None:
    """Extract Chinese license plate number."""
    m = re.search(r"[辽京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤川青藏琼宁][A-Z][A-Z0-9]{5,6}", content)
    return m.group() if m else None


def _extract_amount(content: str) -> float | None:
    """Extract money amount (e.g. '280', '280元', '280.5')."""
    m = re.search(r"(\d+(?:\.\d+)?)\s*元", content)
    if m:
        return float(m.group(1))
    # Pattern: number after 加油/油费
    m = re.search(r"(?:加油|油费)\s*(\d+(?:\.\d+)?)", content)
    if m:
        return float(m.group(1))
    # Generic number near money keywords
    m = re.search(r"(\d+(?:\.\d+)?)", content)
    return float(m.group(1)) if m else None


def _extract_mileage(content: str) -> float | None:
    """Extract mileage number (e.g. '里程表 35680')."""
    m = re.search(r"里程表?\s*(\d+(?:\.\d+)?)", content)
    if m:
        return float(m.group(1))
    m = re.search(r"(\d{4,6})\s*(?:公里|km)", content, re.IGNORECASE)
    if m:
        return float(m.group(1))
    return None


def _extract_time_hint(content: str) -> str | None:
    """Extract time hints like '明天', '今天', '早上8点'."""
    m = re.search(r"(今天|明天|后天|大后天)", content)
    if m:
        return m.group(1)
    m = re.search(r"(\d{1,2})[点时:](\d{0,2})", content)
    if m:
        return m.group(0)
    return None


def _extract_destination(content: str) -> str | None:
    """Extract destination from message."""
    m = re.search(r"去(.{2,20}?)(?:[，,。\s]|$)", content)
    if m:
        dest = m.group(1).strip()
        if len(dest) >= 2:
            return dest
    m = re.search(r"到(.{2,20}?)(?:[，,。\s]|$)", content)
    if m:
        dest = m.group(1).strip()
        if len(dest) >= 2:
            return dest
    return None


def _extract_driver_name(content: str, known_drivers: list[str]) -> str | None:
    """Extract driver name if mentioned."""
    for name in known_drivers:
        if name in content:
            return name
    m = re.search(r"(\w{2,4})(?:师傅|开车|驾驶)", content)
    if m:
        return m.group(1)
    return None


class VehicleAgentService:
    def __init__(self, db: AsyncSession, current_user=None, ip_address: str | None = None):
        self.db = db
        self.current_user = current_user
        self.ip_address = ip_address

    async def analyze_message(
        self,
        content: str,
        platform: str = "manual",
        conversation_id: str | None = None,
        message_id: str | None = None,
        sender_name: str | None = None,
        sender_id: str | None = None,
    ) -> dict:
        """Analyze a message and create a draft."""
        # Match intent
        matched = self._match_intent(content)
        if not matched:
            # Default to vehicle_query with low confidence
            matched = {
                "intent": "vehicle_query",
                "confidence": 0.30,
                "risk_level": "low",
                "suggested_action": "query_vehicles",
                "requires_confirmation": False,
                "requires_finance_review": False,
            }

        # Extract structured data
        extracted = await self._extract_data(content, matched["intent"])

        # Create draft
        draft = VehicleAgentDraft(
            intent=matched["intent"],
            confidence=Decimal(str(matched["confidence"])),
            risk_level=matched["risk_level"],
            status="pending",
            platform=platform,
            conversation_id=conversation_id,
            message_id=message_id,
            sender_name=sender_name,
            sender_id=sender_id,
            original_content=content,
            extracted_data=extracted,
            suggested_action=matched["suggested_action"],
            requires_confirmation=matched["requires_confirmation"],
            requires_finance_review=matched["requires_finance_review"],
        )
        self.db.add(draft)
        await self.db.flush()
        await self.db.refresh(draft)

        # Audit log
        await log_operation(
            db=self.db,
            user_id=self.current_user.id if self.current_user else None,
            user_name=self.current_user.real_name if self.current_user else None,
            object_type=OBJ_VEHICLE_AGENT_DRAFT,
            object_id=draft.id,
            action=ACTION_CREATE,
            ip_address=self.ip_address,
            after_data=self._draft_to_dict(draft),
        )

        return self._draft_to_dict(draft)

    def _match_intent(self, content: str) -> dict | None:
        """Match message content against intent patterns."""
        best_match = None
        best_score = 0.0

        for intent_def in INTENT_PATTERNS:
            matched_count = 0
            total_patterns = len(intent_def["patterns"])

            for pattern in intent_def["patterns"]:
                if re.search(pattern, content):
                    matched_count += 1

            if matched_count == 0:
                continue

            # Score = base confidence * match ratio
            match_ratio = matched_count / total_patterns
            score = intent_def["confidence"] * (0.5 + 0.5 * match_ratio)

            if score > best_score:
                best_score = score
                best_match = {
                    "intent": intent_def["intent"],
                    "confidence": round(min(score, 1.0), 2),
                    "risk_level": intent_def["risk_level"],
                    "suggested_action": intent_def["suggested_action"],
                    "requires_confirmation": intent_def["requires_confirmation"],
                    "requires_finance_review": intent_def["requires_finance_review"],
                }

        return best_match

    async def _extract_data(self, content: str, intent: str) -> dict:
        """Extract structured data based on intent."""
        extracted: dict = {}

        # Common extractions
        plate = _extract_plate_number(content)
        if plate:
            extracted["vehicle_plate"] = plate

        amount = _extract_amount(content)
        if amount is not None:
            extracted["amount"] = amount

        mileage = _extract_mileage(content)
        if mileage is not None:
            extracted["mileage"] = mileage

        time_hint = _extract_time_hint(content)
        if time_hint:
            extracted["time_hint"] = time_hint

        destination = _extract_destination(content)
        if destination:
            extracted["destination"] = destination

        # Intent-specific extractions
        if intent == "fuel_expense":
            extracted["expense_type"] = "油费"
            if amount:
                extracted["amount"] = amount

        elif intent == "vehicle_dispatch":
            # Try to match known drivers
            drivers = await self._get_known_driver_names()
            driver_name = _extract_driver_name(content, drivers)
            if driver_name:
                extracted["driver_name"] = driver_name

        elif intent == "vehicle_issue":
            # Extract issue type
            issue_keywords = {
                "爆胎": "tire", "没气": "tire", "漏油": "engine",
                "漏水": "engine", "异响": "mechanical", "刮蹭": "scratch",
                "追尾": "accident", "撞了": "accident", "事故": "accident",
                "违章": "violation", "罚单": "violation",
            }
            for kw, issue_type in issue_keywords.items():
                if kw in content:
                    extracted["issue_type"] = issue_type
                    break

        elif intent == "maintenance_request":
            maint_keywords = {
                "保养": "maintenance", "换机油": "maintenance",
                "换胎": "tire", "换刹车": "repair", "维修": "repair",
            }
            for kw, maint_type in maint_keywords.items():
                if kw in content:
                    extracted["maintenance_type"] = maint_type
                    break

        return extracted

    async def _get_known_driver_names(self) -> list[str]:
        """Get list of known driver names for matching."""
        result = await self.db.execute(
            select(VehicleDriver.driver_name).where(VehicleDriver.status == "active")
        )
        return list(result.scalars().all())

    def _draft_to_dict(self, d: VehicleAgentDraft) -> dict:
        """Convert draft to dict."""
        return {
            "id": str(d.id),
            "intent": d.intent,
            "confidence": float(d.confidence),
            "risk_level": d.risk_level,
            "status": d.status,
            "platform": d.platform,
            "conversation_id": d.conversation_id,
            "message_id": d.message_id,
            "sender_name": d.sender_name,
            "sender_id": d.sender_id,
            "original_content": d.original_content,
            "extracted_data": d.extracted_data,
            "suggested_action": d.suggested_action,
            "requires_confirmation": d.requires_confirmation,
            "requires_finance_review": d.requires_finance_review,
            "confirmed_by": str(d.confirmed_by) if d.confirmed_by else None,
            "confirmed_by_name": d.confirmed_by_user.real_name if d.confirmed_by_user else None,
            "confirmed_at": d.confirmed_at.isoformat() if d.confirmed_at else None,
            "reject_reason": d.reject_reason,
            "created_draft_id": d.created_draft_id,
            "created_draft_type": d.created_draft_type,
            "created_at": d.created_at.isoformat() if d.created_at else None,
            "updated_at": d.updated_at.isoformat() if d.updated_at else None,
        }

    # ── Draft CRUD ─────────────────────────────────────────────────────────────

    async def list_drafts(
        self,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        intent: str | None = None,
        platform: str | None = None,
    ) -> tuple[list[dict], int]:
        """List agent drafts with filters."""
        skip = (page - 1) * page_size
        q = select(VehicleAgentDraft)

        if status:
            q = q.where(VehicleAgentDraft.status == status)
        if intent:
            q = q.where(VehicleAgentDraft.intent == intent)
        if platform:
            q = q.where(VehicleAgentDraft.platform == platform)

        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar()

        q = q.order_by(VehicleAgentDraft.created_at.desc()).offset(skip).limit(page_size)
        result = await self.db.execute(q)
        drafts = list(result.scalars().all())

        return [self._draft_to_dict(d) for d in drafts], total

    async def get_draft(self, draft_id: UUID) -> dict | None:
        """Get a single draft."""
        result = await self.db.execute(
            select(VehicleAgentDraft).where(VehicleAgentDraft.id == draft_id)
        )
        d = result.scalar_one_or_none()
        return self._draft_to_dict(d) if d else None

    async def confirm_draft(self, draft_id: UUID, confirmed_by: UUID) -> dict:
        """Confirm a draft and create the corresponding record."""
        result = await self.db.execute(
            select(VehicleAgentDraft).where(VehicleAgentDraft.id == draft_id)
        )
        draft = result.scalar_one_or_none()
        if not draft:
            raise ValueError("草稿不存在")
        if draft.status != "pending":
            raise ValueError(f"草稿状态为 {draft.status}，无法确认")

        before = self._draft_to_dict(draft)

        # Create the actual record based on intent
        created_id = None
        created_type = None

        if draft.intent == "fuel_expense":
            created_id = await self._create_fuel_record(draft)
            created_type = "fuel"
        elif draft.intent == "maintenance_request":
            created_id = await self._create_maintenance_record(draft)
            created_type = "maintenance"
        elif draft.intent == "vehicle_use_request":
            created_id = await self._create_use_request(draft)
            created_type = "request"
        elif draft.intent == "vehicle_dispatch":
            created_id = await self._create_dispatch(draft)
            created_type = "dispatch"
        elif draft.intent == "vehicle_issue":
            created_id = await self._create_incident(draft)
            created_type = "incident"
        elif draft.intent in ("vehicle_start", "vehicle_arrival", "vehicle_return"):
            # These update existing dispatches, not create new records
            created_type = "dispatch_status_update"
        # vehicle_query doesn't need confirmation

        # Update draft
        draft.status = "confirmed"
        draft.confirmed_by = confirmed_by
        draft.confirmed_at = datetime.utcnow()
        if created_id:
            draft.created_draft_id = str(created_id)
            draft.created_draft_type = created_type
        await self.db.flush()
        await self.db.refresh(draft)

        await log_operation(
            db=self.db,
            user_id=self.current_user.id if self.current_user else None,
            user_name=self.current_user.real_name if self.current_user else None,
            object_type=OBJ_VEHICLE_AGENT_DRAFT,
            object_id=draft.id,
            action=ACTION_UPDATE,
            ip_address=self.ip_address,
            before_data=before,
            after_data=self._draft_to_dict(draft),
        )

        return self._draft_to_dict(draft)

    async def reject_draft(self, draft_id: UUID, reject_reason: str | None = None) -> dict:
        """Reject a draft."""
        result = await self.db.execute(
            select(VehicleAgentDraft).where(VehicleAgentDraft.id == draft_id)
        )
        draft = result.scalar_one_or_none()
        if not draft:
            raise ValueError("草稿不存在")
        if draft.status != "pending":
            raise ValueError(f"草稿状态为 {draft.status}，无法驳回")

        before = self._draft_to_dict(draft)

        draft.status = "rejected"
        draft.reject_reason = reject_reason
        await self.db.flush()
        await self.db.refresh(draft)

        await log_operation(
            db=self.db,
            user_id=self.current_user.id if self.current_user else None,
            user_name=self.current_user.real_name if self.current_user else None,
            object_type=OBJ_VEHICLE_AGENT_DRAFT,
            object_id=draft.id,
            action=ACTION_UPDATE,
            ip_address=self.ip_address,
            before_data=before,
            after_data=self._draft_to_dict(draft),
        )

        return self._draft_to_dict(draft)

    # ── Record creation helpers ─────────────────────────────────────────────────

    async def _resolve_vehicle_id(self, plate: str | None) -> UUID | None:
        """Resolve vehicle by plate number."""
        if not plate:
            return None
        result = await self.db.execute(
            select(Vehicle.id).where(Vehicle.plate_number == plate)
        )
        return result.scalar_one_or_none()

    async def _resolve_driver_id(self, name: str | None) -> UUID | None:
        """Resolve driver by name."""
        if not name:
            return None
        result = await self.db.execute(
            select(VehicleDriver.id).where(VehicleDriver.driver_name == name)
        )
        return result.scalar_one_or_none()

    async def _create_fuel_record(self, draft: VehicleAgentDraft) -> UUID:
        """Create a fuel record from draft."""
        data = draft.extracted_data or {}
        vehicle_id = await self._resolve_vehicle_id(data.get("vehicle_plate"))
        if not vehicle_id:
            raise ValueError("无法识别车辆，请手动创建油费记录")

        record = VehicleFuelRecord(
            vehicle_id=vehicle_id,
            amount=Decimal(str(data.get("amount", 0))),
            fuel_time=datetime.utcnow(),
            status="pending_review",
            remark=f"[Agent草稿] 来自: {draft.sender_name or '未知'}, 原文: {draft.original_content[:100]}",
        )
        self.db.add(record)
        await self.db.flush()
        await self.db.refresh(record)
        return record.id

    async def _create_maintenance_record(self, draft: VehicleAgentDraft) -> UUID:
        """Create a maintenance record from draft."""
        data = draft.extracted_data or {}
        vehicle_id = await self._resolve_vehicle_id(data.get("vehicle_plate"))
        if not vehicle_id:
            raise ValueError("无法识别车辆，请手动创建维修保养记录")

        record = VehicleMaintenanceRecord(
            vehicle_id=vehicle_id,
            maintenance_type=data.get("maintenance_type", "maintenance"),
            maintenance_date=datetime.utcnow(),
            status="pending_review",
            remark=f"[Agent草稿] 来自: {draft.sender_name or '未知'}, 原文: {draft.original_content[:100]}",
        )
        self.db.add(record)
        await self.db.flush()
        await self.db.refresh(record)
        return record.id

    async def _create_use_request(self, draft: VehicleAgentDraft) -> UUID:
        """Create a vehicle use request from draft."""
        data = draft.extracted_data or {}

        # Generate request no
        count_result = await self.db.execute(select(func.count()).select_from(VehicleUseRequest))
        count = count_result.scalar() or 0
        request_no = f"VUR-{datetime.now().strftime('%Y%m%d')}-{count + 1:04d}"

        req = VehicleUseRequest(
            request_no=request_no,
            requester_id=self.current_user.id if self.current_user else None,
            reason="installation",
            destination=data.get("destination"),
            start_time=None,
            status="pending",
            remark=f"[Agent草稿] 来自: {draft.sender_name or '未知'}, 原文: {draft.original_content[:100]}",
        )
        self.db.add(req)
        await self.db.flush()
        await self.db.refresh(req)
        return req.id

    async def _create_dispatch(self, draft: VehicleAgentDraft) -> UUID:
        """Create a dispatch from draft."""
        data = draft.extracted_data or {}
        vehicle_id = await self._resolve_vehicle_id(data.get("vehicle_plate"))
        if not vehicle_id:
            raise ValueError("无法识别车辆，请手动创建派车单")

        driver_id = await self._resolve_driver_id(data.get("driver_name"))

        # Generate dispatch no
        count_result = await self.db.execute(select(func.count()).select_from(VehicleDispatch))
        count = count_result.scalar() or 0
        dispatch_no = f"VD-{datetime.now().strftime('%Y%m%d')}-{count + 1:04d}"

        dispatch = VehicleDispatch(
            dispatch_no=dispatch_no,
            vehicle_id=vehicle_id,
            driver_id=driver_id,
            destination=data.get("destination"),
            status="assigned",
            created_by=self.current_user.id if self.current_user else None,
            remark=f"[Agent草稿] 来自: {draft.sender_name or '未知'}, 原文: {draft.original_content[:100]}",
        )
        self.db.add(dispatch)
        await self.db.flush()
        await self.db.refresh(dispatch)
        return dispatch.id

    async def _create_incident(self, draft: VehicleAgentDraft) -> UUID:
        """Create a vehicle incident from draft."""
        data = draft.extracted_data or {}
        vehicle_id = await self._resolve_vehicle_id(data.get("vehicle_plate"))
        if not vehicle_id:
            raise ValueError("无法识别车辆，请手动创建异常记录")

        issue_type_map = {
            "tire": "vehicle_damage",
            "engine": "vehicle_damage",
            "mechanical": "vehicle_damage",
            "scratch": "scratch",
            "accident": "accident",
            "violation": "traffic_violation",
        }
        issue_type = data.get("issue_type", "other")
        incident_type = issue_type_map.get(issue_type, "other")

        incident = VehicleIncident(
            vehicle_id=vehicle_id,
            incident_type=incident_type,
            incident_time=datetime.utcnow(),
            description=draft.original_content,
            status="pending",
            remark=f"[Agent草稿] 来自: {draft.sender_name or '未知'}",
        )
        self.db.add(incident)
        await self.db.flush()
        await self.db.refresh(incident)
        return incident.id
