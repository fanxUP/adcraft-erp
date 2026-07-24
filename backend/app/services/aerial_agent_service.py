"""Agent 消息识别与草稿管理服务"""
import json
import re
import uuid
from datetime import datetime, date
from typing import Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.aerial import (
    AerialAgentDraft, AerialDailyLedger, AerialDriverExpense,
    AerialVehicleCost, AerialDriver, AerialVehicle, AerialLedgerAuditLog,
)
from app.services.aerial_service import AerialService


# ── 意图识别规则 ──────────────────────────────────────────────────────────────

INTENT_PATTERNS = {
    "aerial_work_ledger": {
        "keywords": ["出车", "干活", "装", "拆", "挂", "喷绘", "灯箱", "招牌", "门头", "高空车", "作业", "施工"],
        "amount_patterns": [r"收(\d+)", r"收费(\d+)", r"高空车收(\d+)", r"应收(\d+)"],
        "location_patterns": [r"去(.+?)(?:装|拆|干|施工|挂|喷)", r"在(.+?)(?:装|拆|干|施工|挂|喷)"],
    },
    "aerial_driver_expense": {
        "keywords": ["垫付", "垫了", "油费", "加油", "停车费", "过路费", "高速费", "餐费", "饭钱"],
        "amount_patterns": [r"油费.*?(\d+)", r"停车.*?(\d+)", r"过路费.*?(\d+)", r"高速.*?(\d+)", r"餐费.*?(\d+)", r"饭钱.*?(\d+)", r"垫了.*?(\d+)"],
    },
    "aerial_payment_claim": {
        "keywords": ["客户说", "已经转了", "已经付了", "钱转了", "款已付", "客户已付", "说付了"],
    },
    "aerial_vehicle_issue": {
        "keywords": ["没气", "爆胎", "漏油", "故障", "坏了", "维修", "保养", "异常", "问题", "抛锚", "打不着"],
    },
    "aerial_query_report": {
        "keywords": ["赚了多少", "收入", "利润", "统计", "本月", "这个月", "上个月", "多少钱", "几台车"],
    },
    "aerial_reimbursement_claim": {
        "keywords": ["报销", "报销确认", "该报了", "可以报了吗"],
    },
}

EXPENSE_TYPE_MAP = {
    "油费": "fuel", "加油": "fuel",
    "停车费": "parking", "停车": "parking",
    "过路费": "toll", "高速费": "toll", "高速": "toll",
    "餐费": "meal", "饭钱": "meal", "餐": "meal",
}


class AerialAgentService:
    def __init__(self, db: AsyncSession, current_user, ip_address: str = ""):
        self.db = db
        self.current_user = current_user
        self.ip_address = ip_address
        self.aerial_svc = AerialService(db, current_user, ip_address)

    # ── 意图识别 ────────────────────────────────────────────────────────────

    def _recognize_intent(self, text: str) -> dict:
        """基于规则的意图识别"""
        scores = {}
        for intent, rules in INTENT_PATTERNS.items():
            score = 0
            for kw in rules["keywords"]:
                if kw in text:
                    score += 1
            if score > 0:
                scores[intent] = score

        if not scores:
            return {"intent": "normal_chat", "confidence": 0.9, "risk_level": "low"}

        # 优先级：车辆异常 > 付款声称 > 查询 > 垫付出车等
        priority_order = [
            "aerial_vehicle_issue",
            "aerial_payment_claim",
            "aerial_query_report",
            "aerial_reimbursement_claim",
            "aerial_driver_expense",
            "aerial_work_ledger",
        ]
        best_intent = max(scores, key=lambda i: (scores[i], -priority_order.index(i) if i in priority_order else 0))
        max_score = scores[best_intent]
        confidence = min(0.5 + max_score * 0.15, 0.95)

        risk_map = {
            "aerial_work_ledger": "medium",
            "aerial_driver_expense": "medium",
            "aerial_payment_claim": "high",
            "aerial_vehicle_issue": "medium",
            "aerial_query_report": "low",
            "aerial_reimbursement_claim": "medium",
            "normal_chat": "low",
        }
        return {
            "intent": best_intent,
            "confidence": round(confidence, 2),
            "risk_level": risk_map.get(best_intent, "low"),
        }

    def _extract_fields(self, text: str, intent: str) -> dict:
        """从消息中提取结构化字段"""
        extracted = {}

        # 提取金额
        amounts = re.findall(r"(\d+(?:\.\d{1,2})?)\s*(?:元|块)?", text)
        amounts = [float(a) for a in amounts if 0 < float(a) < 1000000]

        # 提取日期（今天/昨天/前天/具体日期）
        today = date.today()
        if "今天" in text or "今日" in text:
            extracted["work_date"] = today.isoformat()
        elif "昨天" in text or "昨日" in text:
            extracted["work_date"] = date.fromordinal(today.toordinal() - 1).isoformat()
        elif "前天" in text:
            extracted["work_date"] = date.fromordinal(today.toordinal() - 2).isoformat()
        else:
            date_match = re.search(r"(\d{1,2})[月./](\d{1,2})[日号]?", text)
            if date_match:
                m, d = int(date_match.group(1)), int(date_match.group(2))
                try:
                    extracted["work_date"] = date(today.year, m, d).isoformat()
                except ValueError:
                    extracted["work_date"] = today.isoformat()
            else:
                extracted["work_date"] = today.isoformat()

        # 提取发送人
        extracted["driver_name_hint"] = None

        if intent == "aerial_work_ledger":
            # 地点
            for pat in INTENT_PATTERNS["aerial_work_ledger"]["location_patterns"]:
                m = re.search(pat, text)
                if m:
                    extracted["work_location"] = m.group(1).strip()
                    break
            if "work_location" not in extracted:
                # 尝试匹配"去XX"
                m = re.search(r"去(.+?)[，,。]", text)
                if m:
                    extracted["work_location"] = m.group(1).strip()

            # 作业内容
            content_match = re.search(r"装(.+?)[，,。]|拆(.+?)[，,。]|挂(.+?)[，,。]", text)
            if content_match:
                extracted["work_content"] = (content_match.group(1) or content_match.group(2) or content_match.group(3) or "").strip()

            # 应收金额
            for pat in INTENT_PATTERNS["aerial_work_ledger"]["amount_patterns"]:
                m = re.search(pat, text)
                if m:
                    extracted["receivable_amount"] = float(m.group(1))
                    break
            if "receivable_amount" not in extracted and amounts:
                extracted["receivable_amount"] = amounts[0]

            # 垫付费用（如果同时提到了）
            expenses = self._extract_expenses(text)
            if expenses:
                extracted["driver_expenses"] = expenses

        elif intent == "aerial_driver_expense":
            extracted["driver_expenses"] = self._extract_expenses(text)

        elif intent == "aerial_vehicle_issue":
            # 提取问题描述
            issue_keywords = ["没气", "爆胎", "漏油", "故障", "坏了", "维修", "异常", "问题"]
            for kw in issue_keywords:
                if kw in text:
                    extracted["issue_description"] = text
                    break
            # 提取车辆信息
            plate_match = re.search(r"([京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼][A-Z]\w{5,6})", text)
            if plate_match:
                extracted["plate_number"] = plate_match.group(1)

        elif intent == "aerial_payment_claim":
            extracted["claim_text"] = text

        elif intent == "aerial_query_report":
            extracted["query_text"] = text
            # 提取时间范围
            if "本月" in text or "这个月" in text:
                extracted["query_month"] = today.strftime("%Y-%m")
            elif "上个月" in text:
                last_month = today.month - 1 or 12
                last_year = today.year if today.month > 1 else today.year - 1
                extracted["query_month"] = f"{last_year}-{last_month:02d}"

        return extracted

    def _extract_expenses(self, text: str) -> list:
        """提取垫付费用"""
        expenses = []
        for type_name, type_code in EXPENSE_TYPE_MAP.items():
            if type_name in text:
                m = re.search(rf"{type_name}.*?(\d+(?:\.\d{{1,2}})?)", text)
                if m:
                    expenses.append({"expense_type": type_code, "expense_type_label": type_name, "amount": float(m.group(1))})
        return expenses

    def _determine_action(self, intent: str) -> str:
        """根据意图确定建议动作"""
        action_map = {
            "aerial_work_ledger": "create_aerial_ledger_draft",
            "aerial_driver_expense": "create_aerial_expense_draft",
            "aerial_payment_claim": "create_payment_reminder",
            "aerial_vehicle_issue": "create_vehicle_issue_draft",
            "aerial_query_report": "query_report",
            "aerial_reimbursement_claim": "create_reimbursement_reminder",
            "normal_chat": "no_action",
        }
        return action_map.get(intent, "no_action")

    # ── 消息接入 ────────────────────────────────────────────────────────────

    async def ingest_message(self, data: dict) -> dict:
        """接收并处理 Agent 消息"""
        text = data.get("content", "").strip()
        if not text:
            return {"draft_id": None, "intent": "normal_chat", "message": "空消息"}

        # 1. 识别意图
        recognition = self._recognize_intent(text)
        intent = recognition["intent"]

        # 2. 如果是查询类，直接返回结果
        if intent == "aerial_query_report":
            extracted = self._extract_fields(text, intent)
            query_result = await self._handle_query(extracted)
            # 仍然保存草稿记录
            draft = await self._save_draft(data, recognition, extracted)
            return {
                "draft_id": str(draft.id),
                "intent": intent,
                "confidence": recognition["confidence"],
                "risk_level": recognition["risk_level"],
                "suggested_action": "query_report",
                "query_result": query_result,
            }

        # 3. 提取字段
        extracted = self._extract_fields(text, intent)

        # 4. 匹配驾驶员
        sender_name = data.get("sender_name", "")
        if sender_name:
            driver = await self._match_driver(sender_name)
            if driver:
                extracted["driver_id"] = str(driver.id)
                extracted["driver_name"] = driver.driver_name

        # 5. 保存草稿
        draft = await self._save_draft(data, recognition, extracted)

        return {
            "draft_id": str(draft.id),
            "intent": intent,
            "confidence": recognition["confidence"],
            "risk_level": recognition["risk_level"],
            "extracted": extracted,
            "suggested_action": self._determine_action(intent),
            "requires_confirmation": True,
        }

    async def _save_draft(self, msg_data: dict, recognition: dict, extracted: dict) -> AerialAgentDraft:
        """保存草稿到数据库"""
        draft = AerialAgentDraft(
            platform=msg_data.get("platform", "unknown"),
            conversation_id=msg_data.get("conversation_id"),
            message_id=msg_data.get("message_id"),
            sender_id=msg_data.get("sender_id"),
            sender_name=msg_data.get("sender_name"),
            raw_message=msg_data.get("content", ""),
            intent=recognition["intent"],
            confidence=recognition["confidence"],
            risk_level=recognition["risk_level"],
            extracted_json=json.dumps(extracted, ensure_ascii=False),
            suggested_action=self._determine_action(recognition["intent"]),
            status="pending",
        )
        self.db.add(draft)
        await self.db.flush()
        await self.db.refresh(draft)
        return draft

    async def _match_driver(self, name: str) -> Optional[AerialDriver]:
        """匹配驾驶员"""
        if not name:
            return None
        result = await self.db.execute(
            select(AerialDriver).where(
                AerialDriver.driver_name.ilike(f"%{name}%"),
                AerialDriver.status == "active",
            )
        )
        return result.scalar_one_or_none()

    async def _handle_query(self, extracted: dict) -> dict:
        """处理查询类消息"""
        month = extracted.get("query_month")
        if not month:
            return {"message": "未识别查询月份"}

        stats = await self.aerial_svc.get_report_monthly(month)
        trip_count = stats.get("trip_count", 0)
        receivable = stats.get("receivable", 0)
        received = stats.get("received", 0)
        gross_profit = stats.get("gross_profit", 0)
        return {
            "month": month,
            "total_trips": trip_count,
            "total_receivable": receivable,
            "total_received": received,
            "total_profit": gross_profit,
            "message": f"{month}月：共{trip_count}车次，"
                       f"应收{receivable}元，"
                       f"实收{received}元，"
                       f"毛利{gross_profit}元",
        }

    # ── 草稿 CRUD ──────────────────────────────────────────────────────────

    async def list_drafts(self, status: Optional[str] = None, skip: int = 0, limit: int = 20):
        """列出草稿"""
        q = select(AerialAgentDraft)
        if status:
            q = q.where(AerialAgentDraft.status == status)
        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar() or 0
        q = q.order_by(AerialAgentDraft.created_at.desc()).offset(skip).limit(limit)
        rows = (await self.db.execute(q)).scalars().all()
        return rows, total

    async def get_draft(self, draft_id: uuid.UUID) -> Optional[AerialAgentDraft]:
        result = await self.db.execute(select(AerialAgentDraft).where(AerialAgentDraft.id == draft_id))
        return result.scalar_one_or_none()

    async def confirm_draft(self, draft_id: uuid.UUID, adjustments: Optional[dict] = None) -> dict:
        """确认草稿，写入正式台账/费用"""
        draft = await self.get_draft(draft_id)
        if not draft:
            return {"success": False, "error": "草稿不存在"}
        if draft.status != "pending":
            return {"success": False, "error": f"草稿状态为{draft.status}，无法确认"}

        extracted = json.loads(draft.extracted_json) if draft.extracted_json else {}

        # 合并人工调整
        if adjustments:
            extracted.update(adjustments)

        intent = draft.intent
        result_ids = {}

        try:
            if intent == "aerial_work_ledger":
                ledger = await self._create_ledger_from_draft(extracted)
                if ledger:
                    ledger_uuid = uuid.UUID(ledger["id"]) if isinstance(ledger.get("id"), str) else ledger.get("id")
                    draft.created_ledger_id = ledger_uuid
                    result_ids["ledger_id"] = str(ledger_uuid)

                    # 如果有垫付费用，同时创建
                    for exp in extracted.get("driver_expenses", []):
                        if ledger_uuid and extracted.get("driver_id"):
                            expense_data = {
                                "ledger_id": str(ledger_uuid),
                                "driver_id": extracted.get("driver_id"),
                                "expense_type": exp.get("expense_type", "other"),
                                "expense_date": extracted.get("work_date", date.today().isoformat()),
                                "amount": exp.get("amount", 0),
                                "paid_by_driver": True,
                            }
                            await self.aerial_svc.create_expense(expense_data)
                            result_ids.setdefault("expenses_created", 0)
                            result_ids["expenses_created"] = result_ids.get("expenses_created", 0) + 1

            elif intent == "aerial_driver_expense":
                # 匹配当天台账
                driver_id = extracted.get("driver_id")
                work_date = extracted.get("work_date")
                ledger_id = None
                if driver_id and work_date:
                    ledger = await self._find_ledger_for_expense(driver_id, work_date)
                    if ledger:
                        ledger_id = str(ledger.id)

                for exp in extracted.get("driver_expenses", []):
                    if not ledger_id or not driver_id:
                        result_ids["warning"] = "未找到匹配的台账，请手动关联垫付费用"
                        continue
                    expense_data = {
                        "ledger_id": ledger_id,
                        "driver_id": driver_id,
                        "expense_type": exp.get("expense_type", "other"),
                        "expense_date": extracted.get("work_date", date.today().isoformat()),
                        "amount": exp.get("amount", 0),
                        "paid_by_driver": True,
                    }
                    await self.aerial_svc.create_expense(expense_data)
                    result_ids.setdefault("expenses_created", 0)
                    result_ids["expenses_created"] = result_ids.get("expenses_created", 0) + 1

            elif intent == "aerial_vehicle_issue":
                # 车辆异常只记录草稿，不自动创建费用（金额未知）
                # 人工确认后可在草稿详情中手动创建维修费用
                result_ids["note"] = "车辆异常草稿已确认，请手动创建维修费用记录"

            # 更新草稿状态
            draft.status = "confirmed"
            draft.confirmed_by = self.current_user.id if self.current_user else None
            draft.confirmed_at = datetime.utcnow()

            # 审计日志
            audit = AerialLedgerAuditLog(
                ledger_id=draft.created_ledger_id,
                operator_id=self.current_user.id if self.current_user else None,
                action="agent_confirm",
                source="erp",
                target_type="agent_draft",
                target_id=draft.id,
                before_json=json.dumps({"status": "pending"}, ensure_ascii=False),
                after_json=json.dumps({"status": "confirmed", "result_ids": result_ids}, ensure_ascii=False, default=str),
                remark=f"Agent草稿确认: {draft.raw_message[:100]}",
            )
            self.db.add(audit)
            await self.db.flush()

            return {"success": True, "ids": result_ids}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def reject_draft(self, draft_id: uuid.UUID, reason: Optional[str] = None) -> dict:
        """拒绝草稿"""
        draft = await self.get_draft(draft_id)
        if not draft:
            return {"success": False, "error": "草稿不存在"}
        if draft.status != "pending":
            return {"success": False, "error": f"草稿状态为{draft.status}，无法拒绝"}

        draft.status = "rejected"
        draft.reject_reason = reason
        draft.confirmed_by = self.current_user.id if self.current_user else None
        draft.confirmed_at = datetime.utcnow()

        # 审计日志
        audit = AerialLedgerAuditLog(
            ledger_id=None,
            operator_id=self.current_user.id if self.current_user else None,
            action="agent_reject",
            source="erp",
            target_type="agent_draft",
            target_id=draft.id,
            before_json=json.dumps({"status": "pending"}, ensure_ascii=False),
            after_json=json.dumps({"status": "rejected", "reason": reason}, ensure_ascii=False),
            remark=f"Agent草稿拒绝: {reason or '无原因'}",
        )
        self.db.add(audit)
        await self.db.flush()

        return {"success": True}

    async def _create_ledger_from_draft(self, extracted: dict) -> Optional[AerialDailyLedger]:
        """从草稿创建正式台账"""
        driver_id = extracted.get("driver_id")
        vehicle_id = extracted.get("vehicle_id")

        # 如果没有匹配到驾驶员和车辆，尝试用第一个活跃的
        if not driver_id:
            r = await self.db.execute(select(AerialDriver).where(AerialDriver.status == "active").limit(1))
            driver = r.scalar_one_or_none()
            if driver:
                driver_id = str(driver.id)

        if not vehicle_id:
            r = await self.db.execute(select(AerialVehicle).where(AerialVehicle.status.in_(["active", "available"])).limit(1))
            vehicle = r.scalar_one_or_none()
            if vehicle:
                vehicle_id = str(vehicle.id)

        if not driver_id or not vehicle_id:
            return None

        ledger_data = {
            "aerial_vehicle_id": vehicle_id,
            "driver_id": driver_id,
            "work_date": extracted.get("work_date", date.today().isoformat()),
            "work_location": extracted.get("work_location", ""),
            "customer_name": extracted.get("customer_name", ""),
            "work_content": extracted.get("work_content", ""),
            "receivable_amount": extracted.get("receivable_amount", 0),
            "final_amount": extracted.get("receivable_amount", 0),
            "payment_status": "pending",
            "status": "draft",
        }
        return await self.aerial_svc.create_ledger(ledger_data)

    async def _find_ledger_for_expense(self, driver_id: str, work_date: str) -> Optional[AerialDailyLedger]:
        """查找驾驶员当天的台账，用于关联垫付"""
        try:
            dt = date.fromisoformat(work_date)
        except (ValueError, TypeError):
            return None
        result = await self.db.execute(
            select(AerialDailyLedger).where(
                AerialDailyLedger.driver_id == uuid.UUID(driver_id),
                func.date(AerialDailyLedger.work_date) == dt,
            ).limit(1)
        )
        return result.scalar_one_or_none()
