import json
import logging
import os
import uuid
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.common import success, success_paginated
from app.schemas.conversation import (
    ConversationCreate,
    ConversationUpdate,
    ConversationResponse,
    ConversationDetailResponse,
    AddMembersRequest,
    UpdateMemberRoleRequest,
    MessageCreate,
    MessageResponse,
    MessageListResponse,
    UserPresenceResponse,
    UpdatePresenceRequest,
    BatchPresenceRequest,
)
from app.services.chat_service import (
    ChatService,
    register_chat_ws,
    unregister_chat_ws,
    broadcast_to_user,
    broadcast_to_conversation,
)
from app.repositories.conversation_repo import MessageRepo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("/private/{user_id}")
async def get_or_create_private_conversation(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取或创建与指定用户的私聊会话（懒加载）"""
    service = ChatService(db)
    result = await service.get_or_create_private_conversation(current_user.id, user_id)
    return success(result.model_dump(mode="json"))


@router.post("")
async def create_conversation(
    data: ConversationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建会话（私聊/群聊）"""
    service = ChatService(db)
    try:
        result = await service.create_conversation(data, current_user.id)
        return success(result.model_dump(mode="json"))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("")
async def get_conversations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取会话列表"""
    service = ChatService(db)
    result = await service.get_conversations(current_user.id, page, page_size)
    return success([r.model_dump(mode="json") for r in result])


# ============ 业务对象搜索（固定路径，必须在 /{conversation_id} 之前注册） ============

@router.get("/search-objects")
async def search_business_objects(
    type: str = Query(..., description="类型: order/quote/task/customer"),
    keyword: str = Query("", description="搜索关键词"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """搜索业务对象（用于名片分享）"""
    from app.models.business_document import BusinessDocument
    from app.models.task import DesignTask, ProductionTask, InstallationTask
    from app.models.customer import Customer

    results = []
    limit = 20

    if type == "order":
        from sqlalchemy.orm import joinedload
        query = select(BusinessDocument).options(joinedload(BusinessDocument.customer)).where(
            BusinessDocument.doc_type == "order",
            BusinessDocument.deleted_at.is_(None),
        )
        if keyword:
            query = query.join(Customer, BusinessDocument.customer_id == Customer.id).where(
                or_(
                    BusinessDocument.doc_no.ilike(f"%{keyword}%"),
                    Customer.name.ilike(f"%{keyword}%"),
                )
            )
        query = query.order_by(BusinessDocument.created_at.desc()).limit(limit)
        rows = (await db.execute(query)).unique().scalars().all()
        results = [
            {
                "id": str(o.id),
                "title": f"订单 #{o.doc_no}",
                "subtitle": f"客户: {o.customer.name if o.customer else '-'}",
                "status": o.status,
                "amount": float(o.total_amount) if o.total_amount else None,
            }
            for o in rows
        ]

    elif type == "quote":
        query = select(BusinessDocument).where(
            BusinessDocument.doc_type == "quote",
            BusinessDocument.deleted_at.is_(None),
        )
        if keyword:
            query = query.where(
                or_(
                    BusinessDocument.doc_no.ilike(f"%{keyword}%"),
                    BusinessDocument.customer_name.ilike(f"%{keyword}%"),
                )
            )
        query = query.order_by(BusinessDocument.created_at.desc()).limit(limit)
        rows = (await db.execute(query)).scalars().all()
        results = [
            {
                "id": str(q.id),
                "title": f"报价单 #{q.doc_no}",
                "subtitle": f"客户: {q.customer_name or '-'}",
                "status": q.status,
                "amount": float(q.total_amount) if q.total_amount else None,
            }
            for q in rows
        ]

    elif type == "task":
        task_configs = [
            (DesignTask, "design_no", "设计"),
            (ProductionTask, "production_no", "生产"),
            (InstallationTask, "installation_no", "安装"),
        ]
        for TaskModel, no_field, label in task_configs:
            no_col = getattr(TaskModel, no_field)
            query = select(TaskModel)
            if keyword:
                conditions = [no_col.ilike(f"%{keyword}%")]
                if hasattr(TaskModel, "project_name"):
                    conditions.append(TaskModel.project_name.ilike(f"%{keyword}%"))
                if hasattr(TaskModel, "description"):
                    conditions.append(TaskModel.description.ilike(f"%{keyword}%"))
                query = query.where(or_(*conditions))
            query = query.order_by(TaskModel.created_at.desc()).limit(limit)
            rows = (await db.execute(query)).scalars().all()
            for t in rows:
                title = f"[{label}] #{getattr(t, no_field)}"
                subtitle = getattr(t, "project_name", None) or (getattr(t, "description", "") or "")[:50] or "-"
                results.append({
                    "id": str(t.id),
                    "title": title,
                    "subtitle": subtitle,
                    "status": t.status,
                })

    elif type == "customer":
        from app.models.customer import CustomerContact
        from sqlalchemy.orm import joinedload
        query = select(Customer).options(joinedload(Customer.contacts)).where(Customer.deleted_at.is_(None))
        if keyword:
            query = query.outerjoin(CustomerContact, Customer.id == CustomerContact.customer_id).where(
                or_(
                    Customer.name.ilike(f"%{keyword}%"),
                    Customer.phone.ilike(f"%{keyword}%"),
                    CustomerContact.name.ilike(f"%{keyword}%"),
                )
            )
        query = query.order_by(Customer.created_at.desc()).limit(limit)
        rows = (await db.execute(query)).unique().scalars().all()
        results = [
            {
                "id": str(c.id),
                "title": f"客户: {c.name}",
                "subtitle": f"联系人: {next((ct.name for ct in c.contacts if ct.is_primary), c.contacts[0].name if c.contacts else '-')}",
                "status": None,
            }
            for c in rows
        ]

    else:
        raise HTTPException(status_code=400, detail=f"不支持的类型: {type}")

    return success(results)


@router.get("/messages/search")
async def search_messages(
    keyword: str,
    conversation_id: Optional[uuid.UUID] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """搜索消息"""
    service = ChatService(db)
    messages, total = await service.search_messages(
        current_user.id, keyword, conversation_id, page, page_size
    )
    return success({
        "items": [m.model_dump(mode="json") for m in messages],
        "total": total,
        "has_more": len(messages) == page_size,
    })


@router.get("/recent-shared")
async def get_recent_shared_cards(
    type: Optional[str] = Query(None, description="卡片类型过滤: order/quote/task/customer"),
    limit: int = Query(10, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取用户最近分享的业务卡片"""
    message_repo = MessageRepo(db)
    cards = await message_repo.get_recent_shared_cards(current_user.id, card_type=type, limit=limit)
    return success(cards)


@router.get("/my-recent-objects")
async def get_my_recent_objects(
    type: str = Query(..., description="类型: order/quote/task/customer"),
    limit: int = Query(10, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取用户最近创建/关联的业务对象"""
    from app.models.business_document import BusinessDocument
    from app.models.task import DesignTask, ProductionTask, InstallationTask
    from app.models.customer import Customer, CustomerContact
    from sqlalchemy.orm import joinedload

    results = []

    if type == "order":
        query = (
            select(BusinessDocument)
            .options(joinedload(BusinessDocument.customer))
            .where(
                BusinessDocument.doc_type == "order",
                BusinessDocument.deleted_at.is_(None),
                BusinessDocument.sales_user_id == current_user.id,
            )
            .order_by(BusinessDocument.created_at.desc())
            .limit(limit)
        )
        rows = (await db.execute(query)).unique().scalars().all()
        results = [
            {"id": str(o.id), "title": f"订单 #{o.doc_no}", "subtitle": f"客户: {o.customer.name if o.customer else '-'}", "status": o.status}
            for o in rows
        ]

    elif type == "quote":
        query = (
            select(BusinessDocument)
            .where(
                BusinessDocument.doc_type == "quote",
                BusinessDocument.deleted_at.is_(None),
                BusinessDocument.created_by == current_user.id,
            )
            .order_by(BusinessDocument.created_at.desc())
            .limit(limit)
        )
        rows = (await db.execute(query)).scalars().all()
        results = [
            {"id": str(q.id), "title": f"报价单 #{q.doc_no}", "subtitle": f"客户: {q.customer_name or '-'}", "status": q.status}
            for q in rows
        ]

    elif type == "task":
        task_configs = [
            (DesignTask, "design_no", "设计"),
            (ProductionTask, "production_no", "生产"),
            (InstallationTask, "installation_no", "安装"),
        ]
        for TaskModel, no_field, label in task_configs:
            no_col = getattr(TaskModel, no_field)
            query = (
                select(TaskModel)
                .where(TaskModel.assigned_to == current_user.id)
                .order_by(TaskModel.created_at.desc())
                .limit(limit)
            )
            rows = (await db.execute(query)).scalars().all()
            for t in rows:
                subtitle = getattr(t, "project_name", None) or (getattr(t, "description", "") or "")[:50] or "-"
                results.append({
                    "id": str(t.id),
                    "title": f"[{label}] #{getattr(t, no_field)}",
                    "subtitle": subtitle,
                    "status": t.status,
                })

    elif type == "customer":
        query = (
            select(Customer)
            .options(joinedload(Customer.contacts))
            .where(
                Customer.deleted_at.is_(None),
                Customer.created_by == current_user.id,
            )
            .order_by(Customer.created_at.desc())
            .limit(limit)
        )
        rows = (await db.execute(query)).unique().scalars().all()
        results = [
            {
                "id": str(c.id),
                "title": f"客户: {c.name}",
                "subtitle": f"联系人: {next((ct.name for ct in c.contacts if ct.is_primary), c.contacts[0].name if c.contacts else '-')}",
                "status": None,
            }
            for c in rows
        ]

    else:
        raise HTTPException(status_code=400, detail=f"不支持的类型: {type}")

    return success(results)


# ============ 会话详情（通配路由，必须在固定路径之后注册） ============

@router.get("/{conversation_id}")
async def get_conversation_detail(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取会话详情"""
    service = ChatService(db)
    result = await service.get_conversation_detail(conversation_id, current_user.id)
    if not result:
        raise HTTPException(status_code=404, detail="会话不存在")
    return success(result.model_dump(mode="json"))


@router.put("/{conversation_id}")
async def update_conversation(
    conversation_id: uuid.UUID,
    data: ConversationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新群信息"""
    service = ChatService(db)
    try:
        result = await service.update_conversation(
            conversation_id, current_user.id, data.name, data.avatar
        )
        if not result:
            raise HTTPException(status_code=404, detail="会话不存在")
        return success(result.model_dump(mode="json"))
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除会话/退出群"""
    service = ChatService(db)
    result = await service.delete_conversation(conversation_id, current_user.id)
    if not result:
        raise HTTPException(status_code=404, detail="会话不存在")
    return success()


# ============ 成员管理 ============

@router.post("/{conversation_id}/members")
async def add_members(
    conversation_id: uuid.UUID,
    data: AddMembersRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """添加成员"""
    service = ChatService(db)
    try:
        await service.add_members(conversation_id, current_user.id, data.user_ids)
        return success()
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.delete("/{conversation_id}/members/{user_id}")
async def remove_member(
    conversation_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """移除成员"""
    service = ChatService(db)
    try:
        await service.remove_member(conversation_id, current_user.id, user_id)
        return success()
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.put("/{conversation_id}/members/{user_id}")
async def update_member_role(
    conversation_id: uuid.UUID,
    user_id: uuid.UUID,
    data: UpdateMemberRoleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新成员角色"""
    service = ChatService(db)
    try:
        await service.update_member_role(
            conversation_id, current_user.id, user_id, data.role
        )
        return success()
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.post("/{conversation_id}/transfer")
async def transfer_owner(
    conversation_id: uuid.UUID,
    new_owner_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """转让群主"""
    service = ChatService(db)
    try:
        await service.transfer_owner(
            conversation_id, current_user.id, new_owner_id
        )
        return success()
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))


# ============ 消息管理 ============

@router.get("/{conversation_id}/messages")
async def get_messages(
    conversation_id: uuid.UUID,
    before_id: Optional[uuid.UUID] = None,
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取消息列表"""
    service = ChatService(db)
    try:
        result = await service.get_messages(
            conversation_id, current_user.id, before_id, limit
        )
        return success(result.model_dump(mode="json"))
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.post("/{conversation_id}/messages")
async def send_message(
    conversation_id: uuid.UUID,
    data: MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """发送消息"""
    service = ChatService(db)
    try:
        message = await service.send_message(
            conversation_id, current_user.id, data
        )

        # 通过 WebSocket 推送新消息给其他成员
        await broadcast_new_message(conversation_id, message, current_user.id)

        return success(message.model_dump(mode="json"))
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.delete("/messages/{message_id}")
async def delete_message(
    message_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除消息"""
    service = ChatService(db)
    try:
        result = await service.delete_message(message_id, current_user.id)
        if not result:
            raise HTTPException(status_code=404, detail="消息不存在")
        return success()
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.post("/messages/{message_id}/recall")
async def recall_message(
    message_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """撤回消息"""
    service = ChatService(db)
    try:
        result = await service.recall_message(message_id, current_user.id)
        if not result:
            raise HTTPException(status_code=404, detail="消息不存在")
        return success()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{conversation_id}/recommendations")
async def get_recommendations(
    conversation_id: uuid.UUID,
    limit: int = Query(10, ge=1, le=20),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """根据聊天上下文智能推荐相关业务对象"""
    from app.models.business_document import BusinessDocument
    from app.models.customer import Customer
    from sqlalchemy.orm import joinedload
    from collections import Counter

    # 获取最近消息
    msg_repo = MessageRepo(db)
    messages = await msg_repo.get_messages(conversation_id, limit=30)

    if not messages:
        return success([])

    # 提取关键词
    stop_words = {
        "的", "了", "是", "在", "有", "和", "不", "我", "你", "他", "她",
        "这", "那", "要", "会", "可以", "已经", "一个", "什么", "吗", "呢",
        "吧", "啊", "哦", "嗯", "好", "对", "没", "就", "也", "都", "还",
        "把", "被", "从", "到", "给", "让", "用", "为", "很", "太", "更",
        "比", "跟", "向", "往", "着", "过", "来", "去", "上", "下", "里",
        "能", "想", "做", "说", "看", "知道", "觉得", "现在", "时候",
        "大家", "我们", "你们", "他们", "自己", "这个", "那个", "怎么",
        "哪", "多少", "几", "那", "请", "谢", "先", "再", "又", "才",
        "只", "但", "而", "因为", "所以", "如果", "虽然", "或者", "还是",
        "以及", "然后", "关于", "对于", "之后", "之前", "以后", "以前",
    }

    keyword_counter: Counter[str] = Counter()
    card_titles: list[str] = []

    for msg in messages:
        if msg.content:
            # 简单分词：按空格和常见标点拆分
            import re
            words = re.split(r'[\s,，.。!！?？;；:：、\-\(\)（）\[\]【】"\']+', msg.content)
            for w in words:
                w = w.strip()
                if len(w) >= 2 and w not in stop_words:
                    keyword_counter[w] += 1

        # 从卡片消息提取关联信息
        if msg.type == "card" and msg.extra_data:
            extra = msg.extra_data
            if isinstance(extra, str):
                import json
                try:
                    extra = json.loads(extra)
                except Exception:
                    extra = {}
            title = extra.get("title", "")
            if title:
                card_titles.append(title)

    # 用卡片标题中的关键词增强权重
    for title in card_titles:
        import re
        words = re.split(r'[\s,，.。!！?？;；:：、\-]+', title)
        for w in words:
            w = w.strip()
            if len(w) >= 2 and w not in stop_words:
                keyword_counter[w] += 3  # 卡片标题权重更高

    if not keyword_counter:
        return success([])

    # 取 top 5 关键词
    top_keywords = [kw for kw, _ in keyword_counter.most_common(5)]

    # 用关键词搜索各业务对象
    results: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    # 搜索订单
    try:
        for kw in top_keywords:
            query = (
                select(BusinessDocument)
                .options(joinedload(BusinessDocument.customer))
                .where(
                    BusinessDocument.doc_type == "order",
                    BusinessDocument.deleted_at.is_(None),
                    or_(
                        BusinessDocument.doc_no.ilike(f"%{kw}%"),
                        BusinessDocument.project_name.ilike(f"%{kw}%"),
                    ),
                )
                .order_by(BusinessDocument.updated_at.desc())
                .limit(3)
            )
            rows = (await db.execute(query)).unique().scalars().all()
            for o in rows:
                oid = str(o.id)
                if oid not in seen_ids:
                    seen_ids.add(oid)
                    results.append({
                        "id": oid,
                        "type": "order",
                        "title": f"订单 #{o.doc_no}",
                        "subtitle": f"客户: {o.customer.name if o.customer else '-'}",
                        "status": o.status,
                        "amount": float(o.total_amount) if o.total_amount else None,
                    })
    except Exception:
        pass

    # 搜索报价单
    try:
        for kw in top_keywords:
            query = (
                select(BusinessDocument)
                .where(
                    BusinessDocument.doc_type == "quote",
                    BusinessDocument.deleted_at.is_(None),
                    or_(
                        BusinessDocument.doc_no.ilike(f"%{kw}%"),
                        BusinessDocument.customer_name.ilike(f"%{kw}%"),
                        BusinessDocument.project_name.ilike(f"%{kw}%"),
                    ),
                )
                .order_by(BusinessDocument.updated_at.desc())
                .limit(3)
            )
            rows = (await db.execute(query)).scalars().all()
            for q in rows:
                qid = str(q.id)
                if qid not in seen_ids:
                    seen_ids.add(qid)
                    results.append({
                        "id": qid,
                        "type": "quote",
                        "title": f"报价单 #{q.doc_no}",
                        "subtitle": f"客户: {q.customer_name or '-'}",
                        "status": q.status,
                        "amount": float(q.total_amount) if q.total_amount else None,
                    })
    except Exception:
        pass

    # 搜索客户
    try:
        for kw in top_keywords:
            query = (
                select(Customer)
                .where(
                    Customer.deleted_at.is_(None),
                    or_(
                        Customer.name.ilike(f"%{kw}%"),
                        Customer.company.ilike(f"%{kw}%"),
                    ),
                )
                .order_by(Customer.updated_at.desc())
                .limit(3)
            )
            rows = (await db.execute(query)).scalars().all()
            for c in rows:
                cid = str(c.id)
                if cid not in seen_ids:
                    seen_ids.add(cid)
                    results.append({
                        "id": cid,
                        "type": "customer",
                        "title": f"客户: {c.name}",
                        "subtitle": f"公司: {c.company or '-'}",
                        "status": None,
                    })
    except Exception:
        pass

    return success(results[:limit])


# ============ 文件上传 ============

@router.post("/upload")
async def upload_chat_file(
    conversation_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """上传聊天文件（图片/文件）"""
    service = ChatService(db)

    # 检查是否是成员
    is_member = await service.member_repo.is_member(conversation_id, current_user.id)
    if not is_member:
        raise HTTPException(status_code=403, detail="不是会话成员")

    # 文件大小限制
    max_size = 50 * 1024 * 1024  # 50MB
    file_content = await file.read()
    if len(file_content) > max_size:
        raise HTTPException(status_code=400, detail="文件大小不能超过50MB")

    # 确定文件类型
    content_type = file.content_type or ""
    if content_type.startswith("image/"):
        file_type = "image"
    else:
        file_type = "file"

    # 生成保存路径
    ext = os.path.splitext(file.filename or "")[1]
    date_dir = datetime.utcnow().strftime("%Y%m%d")
    upload_dir = os.path.join(os.environ.get("LOCAL_UPLOAD_DIR", "uploads"), "chat", date_dir)
    os.makedirs(upload_dir, exist_ok=True)

    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(upload_dir, filename)

    # 保存文件
    with open(filepath, "wb") as f:
        f.write(file_content)

    # 返回文件信息
    relative_path = f"/uploads/chat/{date_dir}/{filename}"
    return success({
        "url": relative_path,
        "name": file.filename or filename,
        "size": len(file_content),
        "type": file_type,
        "content_type": content_type,
    })


# ============ 业务卡片分享 ============

@router.post("/share-card")
async def share_business_card(
    conversation_id: str = Query(..., description="会话ID"),
    card_type: str = Query(..., description="卡片类型: order/quote/task/customer"),
    card_id: str = Query(..., description="业务对象ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """分享业务卡片到会话"""
    # 手动验证 ID 格式
    try:
        conv_uuid = uuid.UUID(conversation_id)
        card_uuid = uuid.UUID(card_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的ID格式")

    service = ChatService(db)

    # 检查是否是成员
    is_member = await service.member_repo.is_member(conv_uuid, current_user.id)
    if not is_member:
        raise HTTPException(status_code=403, detail="不是会话成员")

    # 获取业务对象信息
    card_data = await _get_card_data(db, card_type, card_uuid)
    if not card_data:
        raise HTTPException(status_code=404, detail="业务对象不存在")

    # 创建卡片消息
    message_data = MessageCreate(
        type="card",
        content=card_data["title"],
        extra_data={
            "card_type": card_type,
            "card_id": str(card_uuid),
            **card_data,
        },
    )

    message = await service.send_message(conv_uuid, current_user.id, message_data)

    # 广播消息
    await broadcast_new_message(conv_uuid, message, current_user.id)

    return success(message.model_dump(mode="json"))


async def _get_card_data(db: AsyncSession, card_type: str, card_id: uuid.UUID) -> Optional[dict]:
    """获取业务卡片数据"""
    from app.models.business_document import BusinessDocument
    from app.models.task import DesignTask, ProductionTask, InstallationTask
    from app.models.customer import Customer, CustomerContact

    if card_type == "order":
        obj = await db.get(BusinessDocument, card_id)
        if obj:
            # 加载关联客户
            await db.refresh(obj, ["customer"])
            customer_name = obj.customer.name if obj.customer else "-"
            return {
                "title": f"订单 #{obj.doc_no}",
                "subtitle": f"客户: {customer_name}",
                "status": obj.status,
                "amount": float(obj.total_amount) if obj.total_amount else None,
                "customer_id": str(obj.customer_id) if obj.customer_id else None,
            }
    elif card_type == "quote":
        obj = await db.get(BusinessDocument, card_id)
        if obj:
            return {
                "title": f"报价单 #{obj.doc_no}",
                "subtitle": f"客户: {obj.customer_name or '-'}",
                "status": obj.status,
                "amount": float(obj.total_amount) if obj.total_amount else None,
            }
    elif card_type == "task":
        # 尝试不同任务类型
        task_configs = [
            (DesignTask, "design_no", "设计", "design"),
            (ProductionTask, "production_no", "生产", "production"),
            (InstallationTask, "installation_no", "安装", "installation"),
        ]
        for TaskModel, no_field, label, task_type in task_configs:
            obj = await db.get(TaskModel, card_id)
            if obj:
                no_val = getattr(obj, no_field)
                subtitle = getattr(obj, "project_name", None) or (getattr(obj, "description", "") or "")[:50] or "-"
                return {
                    "title": f"[{label}] #{no_val}",
                    "subtitle": subtitle,
                    "status": obj.status,
                    "task_type": task_type,
                }
    elif card_type == "customer":
        obj = await db.get(Customer, card_id)
        if obj:
            await db.refresh(obj, ["contacts"])
            primary_contact = next((ct.name for ct in obj.contacts if ct.is_primary), obj.contacts[0].name if obj.contacts else "-")
            return {
                "title": f"客户: {obj.name}",
                "subtitle": f"联系人: {primary_contact}",
                "status": None,
            }

    return None


# ============ 已读回执 ============

@router.post("/{conversation_id}/messages/{message_id}/read")
async def mark_message_read(
    conversation_id: uuid.UUID,
    message_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """标记消息已读"""
    service = ChatService(db)
    result = await service.mark_read(conversation_id, message_id, current_user.id)
    if not result:
        raise HTTPException(status_code=404, detail="操作失败")
    return success()


@router.post("/{conversation_id}/read-all")
async def mark_conversation_read(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """标记会话所有消息已读"""
    service = ChatService(db)
    count = await service.mark_conversation_read(conversation_id, current_user.id)
    return success({"count": count})


# ============ 在线状态 ============

@router.get("/presence/{user_id}")
async def get_user_presence(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取用户在线状态"""
    service = ChatService(db)
    result = await service.get_presence(user_id)
    return success(result.model_dump(mode="json") if result else None)


@router.put("/presence")
async def update_my_presence(
    data: UpdatePresenceRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新我的在线状态"""
    service = ChatService(db)
    presence = await service.update_presence(current_user.id, data.status)

    # 广播状态更新给相关用户
    await broadcast_presence_update(current_user.id, data.status)

    return success(presence.model_dump(mode="json"))


@router.post("/presence/batch")
async def get_batch_presence(
    data: BatchPresenceRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """批量获取在线状态"""
    service = ChatService(db)
    result = await service.get_batch_presence(data.user_ids)
    return success([r.model_dump(mode="json") for r in result])


# ---------- 批量分享 ----------


@router.post("/{conversation_id}/messages/batch-share")
async def batch_share_cards(
    conversation_id: uuid.UUID,
    payload: dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """批量分享多个业务卡片到会话，合并为一条卡片消息"""
    items: list[dict[str, Any]] = payload.get("items", [])
    if not items or len(items) > 20:
        raise HTTPException(400, "items 不能为空且最多 20 条")

    service = ChatService(db)
    membership = await service.member_repo.get_member(conversation_id, current_user.id)
    if not membership:
        raise HTTPException(403, "不在会话中")

    # 构建卡片数据
    cards: list[dict[str, Any]] = []
    for item in items:
        card_type = item.get("card_type")
        card_id = item.get("card_id")
        if not card_type or not card_id:
            continue
        try:
            card_uuid = uuid.UUID(card_id) if isinstance(card_id, str) else card_id
        except ValueError:
            continue
        card_data = await _get_card_data(db, card_type, card_uuid)
        if card_data:
            card_data["card_type"] = card_type
            card_data["card_id"] = str(card_uuid)
            cards.append(card_data)

    if not cards:
        raise HTTPException(400, "无有效卡片")

    # 生成摘要文本
    titles = [c.get("title", "") for c in cards]
    summary = f"分享了 {len(cards)} 个项目：" + "、".join(titles[:3])
    if len(cards) > 3:
        summary += f" 等 {len(cards)} 个"

    extra_data = {
        "card_type": "batch",
        "cards": cards,
        "count": len(cards),
    }
    data = MessageCreate(
        type="card",
        content=summary,
        extra_data=extra_data,
    )
    message = await service.send_message(conversation_id, current_user.id, data)
    await broadcast_new_message(conversation_id, message, current_user.id)
    return success(message.model_dump(mode="json"))


# ============ WebSocket ============

async def websocket_chat(websocket: WebSocket):
    """WebSocket endpoint for chat"""
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id = uuid.UUID(payload.get("sub"))
    except (JWTError, ValueError):
        await websocket.close(code=4001, reason="Invalid token")
        return

    await websocket.accept()
    register_chat_ws(user_id, websocket)

    # 更新在线状态
    from app.core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        service = ChatService(db)
        await service.update_presence(user_id, "online")
        await db.commit()

    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
            else:
                # 处理其他消息类型
                try:
                    message = json.loads(data)
                    await handle_ws_message(user_id, message)
                except json.JSONDecodeError:
                    pass
    except WebSocketDisconnect:
        pass
    finally:
        unregister_chat_ws(user_id, websocket)

        # 更新离线状态
        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            service = ChatService(db)
            await service.update_presence(user_id, "offline")
            await db.commit()


async def handle_ws_message(user_id: uuid.UUID, message: dict) -> None:
    """处理 WebSocket 消息"""
    msg_type = message.get("type")

    if msg_type == "typing":
        # 广播输入状态
        conversation_id = message.get("conversation_id")
        await broadcast_typing(conversation_id, user_id)

    elif msg_type == "mark_read":
        # 标记已读
        conversation_id = message.get("conversation_id")
        message_id = message.get("message_id")
        if conversation_id and message_id:
            from app.core.database import AsyncSessionLocal
            async with AsyncSessionLocal() as db:
                service = ChatService(db)
                await service.mark_read(
                    uuid.UUID(conversation_id),
                    uuid.UUID(message_id),
                    user_id,
                )
                await db.commit()

                # 广播已读状态给会话成员
                await broadcast_to_conversation(
                    uuid.UUID(conversation_id),
                    {
                        "type": "message_read",
                        "data": {
                            "conversation_id": conversation_id,
                            "message_id": message_id,
                            "user_id": str(user_id),
                        }
                    },
                    exclude_user_id=user_id,
                )


async def broadcast_new_message(
    conversation_id: uuid.UUID,
    message: MessageResponse,
    sender_id: uuid.UUID,
) -> None:
    """广播新消息给会话成员"""
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        service = ChatService(db)
        conversation = await service.conversation_repo.get_by_id(conversation_id)
        if not conversation:
            return

        members = await service.member_repo.get_members(conversation_id)
        for member in members:
            if member.user_id != sender_id:
                await broadcast_to_user(member.user_id, {
                    "type": "new_message",
                    "data": {
                        "message": message.model_dump(mode="json"),
                        "conversation_id": str(conversation_id),
                    }
                })


async def broadcast_typing(
    conversation_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    """广播输入状态"""
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        service = ChatService(db)
        members = await service.member_repo.get_members(conversation_id)

        user = await db.get(User, user_id)
        user_name = user.real_name or user.username if user else "用户"

        for member in members:
            if member.user_id != user_id:
                await broadcast_to_user(member.user_id, {
                    "type": "user_typing",
                    "data": {
                        "conversation_id": str(conversation_id),
                        "user_id": str(user_id),
                        "user_name": user_name,
                    }
                })


async def broadcast_presence_update(
    user_id: uuid.UUID,
    status: str,
) -> None:
    """广播在线状态更新给共享会话的用户"""
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        service = ChatService(db)
        # 获取用户参与的所有会话ID
        conversation_ids = await service.member_repo.get_conversation_ids_by_user(user_id)

        # 获取所有相关会话的成员
        notified_user_ids: set[uuid.UUID] = set()
        for conv_id in conversation_ids:
            members = await service.member_repo.get_members(conv_id)
            for member in members:
                if member.user_id != user_id:
                    notified_user_ids.add(member.user_id)

        # 广播给相关在线用户
        for uid in notified_user_ids:
            if uid in _chat_ws_connections:
                await broadcast_to_user(uid, {
                    "type": "presence_update",
                    "data": {
                        "user_id": str(user_id),
                        "status": status,
                    }
                })
