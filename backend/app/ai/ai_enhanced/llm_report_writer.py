"""AI-enhanced report writer — uses LLM to generate free-form narrative reports.

Requires AI_ENABLED=true and AI_API_KEY.
"""

from __future__ import annotations

import json

from app.ai.core.ai_client import AIClient, AIClientError, AIAPIError

SYSTEM_PROMPT = """你是一个广告制作安装行业的经营分析师。根据提供的经营数据，生成一份专业的经营分析报告。

要求：
1. 用简洁专业的语言总结经营情况
2. 分析关键指标的变化趋势
3. 指出存在的问题和风险
4. 提出具体的改进建议（3-5条）

请返回 JSON 格式：
{
  "narrative": "报告正文（Markdown格式）",
  "suggestions": ["建议1", "建议2", "建议3"]
}
"""


class LLMReportWriter:
    """AI-enhanced narrative report writer.

    Usage:
        client = AIClient()
        writer = LLMReportWriter(client)
        narrative, suggestions = await writer.write_narrative(stats, "monthly")
    """

    def __init__(self, ai_client: AIClient) -> None:
        self.ai_client = ai_client

    async def write_narrative(self, stats: dict, period: str) -> tuple[str, list[str]]:
        """Generate AI narrative and suggestions from structured stats.

        Args:
            stats: Dictionary of report statistics
            period: "weekly" or "monthly"

        Returns:
            (narrative_text, list_of_suggestions)
        """
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
            )
            data = _parse_json(response)
            return data.get("narrative", ""), data.get("suggestions", [])
        except (AIClientError, AIAPIError):
            return "", []


def _parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1])
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


def _format_json(obj: object, indent: int = 2) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=indent, default=str)
