"""AI-enhanced image analyzer — vision model analysis of site photos.

Requires AI_ENABLED=true and AI_API_KEY.
Analyzes installation site photos for risks and conditions.
"""

from __future__ import annotations

from app.ai.core.ai_client import AIClient

SYSTEM_PROMPT = """你是一个广告安装工程的现场勘查专家。请分析提供的现场照片，识别以下内容：

1. 墙面情况（wall_condition）：是什么材质（砖墙/混凝土/石膏板/玻璃等），是否平整，有无破损
2. 高度风险（height_risk）：安装位置高度评估，是否有高空作业需求（无/低/中/高）
3. 脚手架需求（scaffolding_needed）：是否需要脚手架/升降机/吊车（不需要/建议使用/必须使用）
4. 障碍物（obstacles_found）：是否有影响安装的障碍物（无/有电线/有管道/有装饰物/其他）
5. 成本影响（cost_impact）：是否会增加安装成本（无影响/小幅增加/显著增加）

请返回严格 JSON 格式：
{
  "wall_condition": "描述墙面材质和状态",
  "height_risk": "无|低|中|高",
  "scaffolding_needed": "不需要|建议使用|必须使用",
  "obstacles_found": "无|有电线|有管道|有装饰物|其他",
  "cost_impact": "无影响|小幅增加|显著增加",
  "notes": "综合分析和建议"
}
"""


class ImageAnalyzer:
    """AI-powered site photo analyzer for installation risk assessment.

    Usage:
        client = AIClient()
        analyzer = ImageAnalyzer(client)
        findings = await analyzer.analyze_site_photo(image_bytes, task_context)
    """

    def __init__(self, ai_client: AIClient) -> None:
        self.ai_client = ai_client

    async def analyze_site_photo(
        self, image_bytes: bytes, task_context: dict | None = None
    ) -> dict | None:
        """Analyze a site photo using vision model.

        Args:
            image_bytes: Raw image file bytes
            task_context: Optional dict with installation task info (project_name, address, etc.)

        Returns:
            Structured findings dict, or None on failure
        """
        prompt = "请分析这张安装现场照片。"
        if task_context:
            prompt += (
                f"\n关联安装任务：{task_context.get('project_name', '未知项目')}，"
                f"地址：{task_context.get('address', '未知')}"
            )

        text = await self.ai_client.analyze_image(image_bytes, prompt)
        return _parse_json(text)


def _parse_json(text: str) -> dict | None:
    import json
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1])
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None
