from types import SimpleNamespace

from app.ai_assistant.prompt_builder import PromptBuilder
from app.ai_assistant.schemas import AiPageContext


def test_page_context_accepts_structured_page_capabilities():
    context = AiPageContext(
        page="order_detail",
        page_title="订单详情",
        page_purpose="查看订单信息、交付任务、验收与收款进度",
        business_type="order",
        business_id="33333333-3333-3333-3333-333333333333",
        workflow_stage="order_delivery",
        available_actions=["查看订单进度", "查看关联任务", "查看收款情况"],
        business_status="designing",
    )

    assert context.page_title == "订单详情"
    assert context.available_actions == ["查看订单进度", "查看关联任务", "查看收款情况"]
    assert context.business_status == "designing"


def test_prompt_uses_structured_current_page_instead_of_legacy_route_names():
    prompt = PromptBuilder().build_system_prompt(
        SimpleNamespace(username="admin", real_name="管理员", roles=[]),
        {
            "page": "order_detail",
            "page_title": "订单详情",
            "page_purpose": "查看订单信息、交付任务、验收与收款进度",
            "workflow_stage": "order_delivery",
            "available_actions": ["查看订单进度", "查看关联任务"],
            "business_type": "order",
            "business_id": "33333333-3333-3333-3333-333333333333",
            "business_status": "designing",
        },
        [],
    )

    assert "当前页面：订单详情（order_detail）" in prompt
    assert "页面用途：查看订单信息、交付任务、验收与收款进度" in prompt
    assert "当前状态：designing" in prompt
    assert "页面可执行操作：查看订单进度、查看关联任务" in prompt
    assert "CDROrderDetail" not in prompt


def test_prompt_uses_the_canonical_backend_workflows():
    prompt = PromptBuilder().build_system_prompt(
        SimpleNamespace(username="admin", real_name="管理员", roles=[]),
        None,
        [],
    )

    assert "pending_confirm → confirmed / cancelled" in prompt
    assert "pending_acceptance → completed / in_installation / cancelled" in prompt
    assert "pending_review → confirmed / revision" in prompt
    assert "change_order_status" in prompt
    assert "blockers 为空" in prompt
