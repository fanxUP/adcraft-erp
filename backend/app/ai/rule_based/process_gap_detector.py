"""Rule-based process gap detector — finds missing required processes for quote lines.

Each rule:
- product_keywords: if product/description contains any of these, the rule activates
- material_keywords: (optional) if material name contains any of these
- missing_process: the process that's likely needed
- reason: human-readable explanation
- severity: info | warning | critical

Zero AI dependency — pure rule-based, always available.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cdr_quote import QuoteLine, QuoteLineProcess, QuoteVersion
from app.models.product import Process

# ── Process Gap Rules ──────────────────────────────────────────

ProcessGap = dict[str, Any]  # {"type", "severity", "line_id", "line_desc", "missing_process", "reason", "process_id"}

PROCESS_GAP_RULES: list[dict] = [
    # ── UV喷绘 / 写真 → 覆膜 ──
    {
        "product_keywords": ["UV", "uv", "Uv", "喷绘", "写真", "画面", "户外喷绘", "车贴"],
        "material_keywords": ["PVC", "pp", "PP", "车贴", "灯布", "刀刮布"],
        "missing_process_name": "覆膜",
        "reason": "{product} 建议覆膜以保护画面，延长使用寿命（尤其户外场景）",
        "severity": "warning",
    },
    # ── 亚克力 → 抛光 ──
    {
        "product_keywords": ["亚克力", "有机玻璃", "亚克力字", "亚克力面板", "亚克力盒"],
        "missing_process_name": "抛光",
        "reason": "{product} 建议抛光处理，提升边缘光滑度和透明质感",
        "severity": "info",
    },
    # ── 金属字 → 喷涂 ──
    {
        "product_keywords": ["金属字", "不锈钢字", "铁皮字", "铜字", "钛金字", "金属", "不锈钢"],
        "missing_process_name": "喷涂",
        "reason": "{product} 建议喷涂/烤漆处理，防锈并提升外观效果",
        "severity": "warning",
    },
    # ── 灯箱 → LED ──
    {
        "product_keywords": ["灯箱", "发光", "超薄灯箱", "拉布灯箱", "卡布灯箱", "软膜灯箱"],
        "missing_process_name": "LED灯条",
        "reason": "{product} 通常需搭配 LED 灯条/模组",
        "severity": "warning",
    },
    # ── 发光字 → LED ──
    {
        "product_keywords": ["发光字", "霓虹灯", "LED字", "树脂字", "通体发光字"],
        "missing_process_name": "LED模组",
        "reason": "{product} 需搭配 LED 模组/电源",
        "severity": "warning",
    },
    # ── 水晶字 → 抛光 ──
    {
        "product_keywords": ["水晶字", "水晶", "水晶标"],
        "missing_process_name": "抛光",
        "reason": "{product} 建议抛光处理以提升透明度和光泽",
        "severity": "info",
    },
    # ── 大型喷绘 → 拼接 ──
    {
        "product_keywords": ["大型", "超大", "大幅面", "楼体", "围挡", "户外广告"],
        "missing_process_name": "拼接缝制",
        "reason": "大幅面喷绘建议拼接缝制处理，确保安装平整",
        "severity": "warning",
    },
    # ── 户外标识 → 防水 ──
    {
        "product_keywords": ["户外", "室外", "楼顶", "外墙", "门头", "招牌"],
        "missing_process_name": "防水处理",
        "reason": "户外标识建议做防水处理，防止日晒雨淋导致褪色/脱落",
        "severity": "warning",
    },
    # ── 门头 → 安装支架 ──
    {
        "product_keywords": ["门头", "招牌", "店招", "楼顶字"],
        "missing_process_name": "支架制作",
        "reason": "{product} 通常需要定制支架/龙骨进行固定安装",
        "severity": "warning",
    },
    # ── 玻璃贴 → 覆膜 ──
    {
        "product_keywords": ["玻璃贴", "玻璃膜", "玻璃贴膜", "玻璃贴纸"],
        "missing_process_name": "覆膜",
        "reason": "玻璃贴建议覆膜增加耐久性和抗刮性",
        "severity": "info",
    },
    # ── 展架 / X展架 / 易拉宝 → 画面安装 ──
    {
        "product_keywords": ["展架", "X展架", "易拉宝", "门型展架", "展示架"],
        "missing_process_name": "画面裱装",
        "reason": "{product} 建议提供画面裱装/安装服务",
        "severity": "info",
    },
    # ── 雪弗板 / KT板 → 覆膜 ──
    {
        "material_keywords": ["雪弗板", "KT板", "安迪板", "PVC板", "PVC发泡板"],
        "missing_process_name": "覆膜",
        "reason": "{material} 表面建议覆膜保护画面",
        "severity": "info",
    },
    # ── 换灯布 → 安装 ──
    {
        "product_keywords": ["换灯布", "换画面", "灯布更换"],
        "missing_process_name": "安装",
        "reason": "{product} 通常含更换安装服务",
        "severity": "info",
    },
    # ── 高空作业 ──
    {
        "product_keywords": ["高空", "楼顶", "外墙", "三层以上", "高架"],
        "missing_process_name": "高空作业费",
        "reason": "{product} 涉及高空安装，需额外计高空作业费用",
        "severity": "critical",
    },
]


class ProcessGapDetector:
    """Detects missing required processes in CDR quote lines.

    Usage:
        detector = ProcessGapDetector(db)
        gaps = await detector.detect_gaps_for_quote(quote_id)
        # or for a single line:
        gaps = await detector.detect_gaps_for_line(line, line_processes)
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def detect_gaps_for_quote(
        self, quote_id: UUID, version_id: UUID | None = None
    ) -> list[ProcessGap]:
        """Detect process gaps for all lines in a quote version."""
        # Get lines — use latest version if no version_id given
        if not version_id:
            r = await self.db.execute(
                select(QuoteVersion)
                .where(QuoteVersion.quote_id == quote_id)
                .order_by(QuoteVersion.version_no.desc()).limit(1)
            )
            version = r.scalar_one_or_none()
            if not version:
                return []
            version_id = version.id

        # Load lines with their processes
        r_lines = await self.db.execute(
            select(QuoteLine).where(QuoteLine.version_id == version_id)
        )
        lines = r_lines.scalars().all()

        # Load process_id for each missing_process_name
        process_map = await self._build_process_name_map()

        all_gaps: list[ProcessGap] = []
        for line in lines:
            line_gaps = await self.detect_gaps_for_line(
                line, line.processes, process_map
            )
            all_gaps.extend(line_gaps)

        return all_gaps

    async def detect_gaps_for_line(
        self,
        line: QuoteLine,
        line_processes: list[QuoteLineProcess],
        process_name_map: dict[str, UUID] | None = None,
    ) -> list[ProcessGap]:
        """Check a single quote line for missing processes."""
        if process_name_map is None:
            process_name_map = await self._build_process_name_map()

        # Collect existing process names for this line
        existing_processes = set()
        for lp in line_processes:
            # lp.process_id — we need the name
            for pname, pid in process_name_map.items():
                if pid == lp.process_id:
                    existing_processes.add(pname)

        # Also check description text for implicit process references
        description = (line.description or "").lower()

        gaps: list[ProcessGap] = []
        checked_rules: set[int] = set()

        for idx, rule in enumerate(PROCESS_GAP_RULES):
            if idx in checked_rules:
                continue
            checked_rules.add(idx)

            missing = rule["missing_process_name"]

            # Skip if this process is already selected
            if self._process_already_selected(missing, existing_processes, description):
                continue

            # Check if rule matches this line
            product_match = self._keyword_match(rule.get("product_keywords", []), description)
            material_match = True
            if "material_keywords" in rule:
                # We don't have material name directly from line, check description
                material_match = self._keyword_match(rule["material_keywords"], description)

            if not product_match or not material_match:
                continue

            # Also check product name from the line's product_id if available
            if line.product_id and not product_match:
                # Try to check against product name
                pass  # Product match already from description

            # Gap detected — build result
            template_vars = {
                "product": line.description[:50],
                "material": line.description[:50],
            }
            process_id = process_name_map.get(missing)

            gaps.append({
                "type": "process_gap",
                "severity": rule["severity"],
                "line_id": str(line.id),
                "line_no": line.line_no,
                "line_desc": line.description,
                "missing_process_name": missing,
                "missing_process_id": str(process_id) if process_id else None,
                "reason": rule["reason"].format(**template_vars),
            })

        return gaps

    async def _build_process_name_map(self) -> dict[str, UUID]:
        """Build a dict mapping process name -> process_id."""
        r = await self.db.execute(select(Process))
        processes = r.scalars().all()
        return {p.name: p.id for p in processes}

    @staticmethod
    def _keyword_match(keywords: list[str], text: str) -> bool:
        """Check if any keyword appears in the text."""
        text_lower = text.lower()
        for kw in keywords:
            if kw.lower() in text_lower:
                return True
        return False

    @staticmethod
    def _process_already_selected(
        missing_name: str,
        existing_processes: set[str],
        description: str,
    ) -> bool:
        """Check if the process is already selected or mentioned."""
        if missing_name in existing_processes:
            return True
        # Check description for implicit mention
        desc_lower = description.lower()
        if missing_name.lower() in desc_lower:
            return True
        # Common synonyms
        synonyms = {
            "覆膜": ["过膜", "裱膜", "覆膜", "保护膜"],
            "抛光": ["打磨", "抛光"],
            "喷涂": ["喷漆", "烤漆", "喷塑", "静电喷涂"],
            "LED灯条": ["led", "灯带", "灯条", "led灯"],
            "LED模组": ["led模组", "led电源", "变压器"],
            "支架制作": ["支架", "龙骨", "钢结构"],
            "拼接缝制": ["拼接", "缝制"],
            "防水处理": ["防水"],
            "高空作业费": ["高空"],
        }
        for synonym in synonyms.get(missing_name, []):
            if synonym.lower() in desc_lower:
                return True
        return False


# ── Convenience function ───────────────────────────────────────

async def detect_process_gaps(
    db: AsyncSession, quote_id: UUID, version_id: UUID | None = None
) -> list[ProcessGap]:
    """Quick one-shot process gap detection."""
    detector = ProcessGapDetector(db)
    return await detector.detect_gaps_for_quote(quote_id, version_id)
