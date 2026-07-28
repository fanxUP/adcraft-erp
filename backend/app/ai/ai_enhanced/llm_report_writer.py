"""AI-enhanced report writer — uses LLM to generate free-form narrative reports.

Enhanced with:
- GatewayAIClient integration / task_code="report_writing" routing
- Domain-specific advertising industry prompts
- Confidence scoring based on data completeness
- Richer structured output
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.ai.core.ai_client import AIClient
from app.ai.gateway_providers.gateway_ai_client import GatewayAIClient

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一个广告制作安装行业的资深经营分析师。请根据提供的经营数据，生成一份专业的经营分析报告。

## 行业背景
广告制作安装行业特点：
- 订单金额从几百元到数十万元不等，需要关注大单占比
- 收款周期通常 30-90 天，回款率是核心健康指标
- 设计→生产→安装是标准流程，各环节待处理量反映产能瓶颈
- 逾期订单直接影响现金流，需重点关注

## 分析要求

### 1. 总体经营概况
- 用简洁专业的语言总结本期业务量（订单数 and 订单金额）
- 与行业经验基准比较（正常月订单 20-50 单为健康状态）

### 2. 财务健康分析
- 收款率评估：>80% 健康，60-80% 需关注，<60% 需预警
- 逾期订单占比：逾期/总订单 <10% 正常，10-20% 需注意，>20% 需重点整治

### 3. 产能与交付分析
- 设计/生产/安装各环节待处理量反映资源瓶颈
- 如果某环节积压超过 5 个，建议增加外包或调配人力

### 4. 风险提示
- 基于异常检测结果，指出最需要关注的 1-2 项风险

### 5. 改进建议（3-5 条）
- 具体可执行，而非空泛建议
- 结合数据给出有针对性的建议

请返回严格 JSON 格式：
{
  "narrative": "报告正文（专业Markdown格式，含小标题和关键数据加粗）",
  "suggestions": ["建议1（含原因和预期效果）", "建议2", "建议3"],
  "summary": "一句话核心结论（不超过30字）",
  "health_score": 85,
  "key_metrics": {
    "order_trend": "up|stable|down",
    "collection_health": "healthy|attention|warning",
    "capacity_bottleneck": "design|production|installation|none"
  }
}

字段说明：
- health_score: 0-100 的企业健康评分
- order_trend: 订单趋势（相比预期基准）
- collection_health: 回款健康度
- capacity_bottleneck: 产能瓶颈环节（根据待处理量判断）
"""


class LLMReportWriter:
    """AI-enhanced narrative report writer.

    Usage:
        client = GatewayAIClient(db)
        writer = LLMReportWriter(client)
        narrative, suggestions = await writer.write_narrative(stats, "monthly")
        # Returns (text, list_of_suggestions, confidence, meta)
    """

    def __init__(self, ai_client: GatewayAIClient | AIClient) -> None:
        self.ai_client = ai_client

    async def write_narrative(
        self, stats: dict, period: str
    ) -> tuple[str, list[str], str, dict[str, Any]]:
        """Generate AI narrative and suggestions from structured stats.

        Args:
            stats: Dictionary of report statistics
            period: "weekly" or "monthly"

        Returns:
            (narrative_text, list_of_suggestions, confidence_level, meta_dict)
        """
        confidence = self._calc_confidence(stats)

        prompt = (
            f"报告周期：{period}\n"
            f"经营数据：\n"
            f"```json\n{_format_json(stats)}\n```\n"
            f"请分析以上数据，生成经营报告。"
        )

        try:
            response = await self.ai_client.chat_completion(
                prompt=prompt,
                system_prompt=SYSTEM_PROMPT,
                task_code="report_writing",
                temperature=0.3,
                max_tokens=2048,
            )
            data = _parse_json(response) or {}

            narrative = data.get("narrative", "")
            suggestions = data.get("suggestions", [])
            summary = data.get("summary", "")
            health_score = data.get("health_score")
            key_metrics = data.get("key_metrics", {})

            meta = {
                "summary": summary,
                "health_score": health_score,
                "key_metrics": key_metrics,
            }

            return narrative, suggestions, confidence, meta

        except Exception:
            logger.exception("AI report generation failed")
            return "", [], "none", {}

    def _calc_confidence(self, stats: dict) -> str:
        """Calculate confidence level based on data completeness.

        | Condition | Confidence |
        |-----------|-----------|
        | Has all 5+ key fields with non-zero values | high |
        | Has 3-4 key fields | medium |
        | Has <3 key fields | low |

        Key fields for confidence: order_count, order_amount, payment_amount,
        overdue_count, pending_design/production/installation.
        """
        key_fields = [
            "order_count", "order_amount", "payment_amount",
            "overdue_count", "pending_design", "pending_production",
            "pending_installation",
        ]
        filled = sum(
            1 for k in key_fields
            if stats.get(k) is not None and stats.get(k) != 0
        )
        if filled >= 5:
            return "high"
        if filled >= 3:
            return "medium"
        return "low"


def _parse_json(text: str) -> dict[str, Any] | None:
    """Robust JSON extraction from LLM response."""
    if not text:
        return None
    text = text.strip()
    # Remove markdown code fences
    if text.startswith("```"):
        lines = text.split("\n")
        # Handle ```json or just ```
        first = lines[0].strip().lower()
        if first in ("```json", "```"):
            text = "\n".join(lines[1:-1])
        else:
            text = "\n".join(lines[1:])
        text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.warning(f"JSON parse failed: {e}")
        # Attempt to find a JSON object in the text
        try:
            start = text.index("{")
            end = text.rindex("}")
            return json.loads(text[start : end + 1])
        except (ValueError, json.JSONDecodeError):
            return None


def _format_json(obj: object, indent: int = 2) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=indent, default=str)
