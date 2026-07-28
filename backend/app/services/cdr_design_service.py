"""CDR 设计文件服务 - 文件上传、SVG 解析、AI 报价辅助。"""

import os
import uuid
import logging

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.models.task import Attachment

logger = logging.getLogger(__name__)


class SvgShapeExtractor:
    """解析 SVG 文件，提取图形尺寸信息。"""

    @staticmethod
    def extract_shapes(svg_content: str) -> dict:
        shapes = []
        import re

        viewbox_match = re.search(r'viewBox=["' "']" r'([\d.\s]+)["' "']", svg_content)
        svg_width_match = re.search(r'width=["' "']" r'([\d.]+)(cm|mm|in|pt|px)?["' "']", svg_content)
        svg_height_match = re.search(r'height=["' "']" r'([\d.]+)(cm|mm|in|pt|px)?["' "']", svg_content)

        doc_w = float(svg_width_match.group(1)) if svg_width_match else 0
        doc_h = float(svg_height_match.group(1)) if svg_height_match else 0
        doc_w_unit = (svg_width_match.group(2) or "px") if svg_width_match else "px"
        doc_h_unit = (svg_height_match.group(2) or "px") if svg_height_match else "px"

        doc_width_mm = SvgShapeExtractor._to_mm(doc_w, doc_w_unit)
        doc_height_mm = SvgShapeExtractor._to_mm(doc_h, doc_h_unit)

        scale = 1.0
        if viewbox_match:
            vb = list(map(float, viewbox_match.group(1).split()))
            if len(vb) == 4 and doc_width_mm and vb[2] > 0:
                scale = doc_width_mm / vb[2]

        for m in re.finditer(r'<rect[^>]*?\s+width=["' "']" r'([\d.]+)["' "']" r'[^>]*?\s+height=["' "']" r'([\d.]+)["' "']", svg_content):
            w = float(m.group(1)) * scale
            h = float(m.group(2)) * scale
            shapes.append({"type": "rectangle", "width_mm": round(w, 2), "height_mm": round(h, 2),
                           "area_m2": round(w * h / 1000000, 4), "quantity": 1,
                           "label": "矩形 %.0fx%.0fmm" % (w, h)})

        for m in re.finditer(r'<circle[^>]*?\s+r=["' "']" r'([\d.]+)["' "']", svg_content):
            r_val = float(m.group(1)) * scale
            d = r_val * 2
            shapes.append({"type": "circle", "width_mm": round(d, 2), "height_mm": round(d, 2),
                           "area_m2": round(3.14159 * r_val * r_val / 1000000, 4), "quantity": 1,
                           "label": "圆形 直径%.0fmm" % d})

        for m in re.finditer(r'<ellipse[^>]*?\s+rx=["' "']" r'([\d.]+)["' "']" r'[^>]*?\s+ry=["' "']" r'([\d.]+)["' "']", svg_content):
            rx = float(m.group(1)) * scale
            ry = float(m.group(2)) * scale
            shapes.append({"type": "ellipse", "width_mm": round(rx * 2, 2), "height_mm": round(ry * 2, 2),
                           "area_m2": round(3.14159 * rx * ry / 1000000, 4), "quantity": 1,
                           "label": "椭圆 %.0fx%.0fmm" % (rx * 2, ry * 2)})

        return {
            "document_width_mm": round(doc_width_mm, 2) if doc_width_mm else None,
            "document_height_mm": round(doc_height_mm, 2) if doc_height_mm else None,
            "shapes": shapes,
            "shape_count": len(shapes),
            "total_area_m2": round(sum(s["area_m2"] for s in shapes), 4) if shapes else None,
        }

    @staticmethod
    def _to_mm(value: float, unit: str) -> float:
        units = {"mm": 1, "cm": 10, "m": 1000, "in": 25.4, "pt": 0.3528, "px": 0.2646}
        return value * units.get(unit, 0.2646)


class CdrDesignService:
    """CDR 设计文件管理——上传、SVG 解析、AI 辅助。"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.upload_dir = os.path.join(settings.LOCAL_UPLOAD_DIR, "cdr")
        os.makedirs(self.upload_dir, exist_ok=True)

    async def upload_design_file(self, quote_id: str, file: UploadFile, uploaded_by: uuid.UUID) -> dict:
        ext = os.path.splitext(file.filename or "file")[1].lower()
        allowed = {".cdr", ".svg", ".pdf", ".ai", ".eps", ".dxf", ".png", ".jpg", ".jpeg"}
        if ext not in allowed:
            raise ValueError("不支持的文件格式: " + ext)

        from app.models.business_document import BusinessDocument
        from app.models.business_document import BusinessDocument
        doc = await self.db.get(BusinessDocument, uuid.UUID(quote_id))
        if not doc or doc.doc_type != "quote":
            raise ValueError("报价不存在")

        safe_name = uuid.uuid4().hex + ext
        file_path = os.path.join(self.upload_dir, safe_name)
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        att = Attachment(
            related_type="cdr_quote",
            related_id=uuid.UUID(quote_id),
            filename=file.filename or safe_name,
            file_path=file_path,
            file_size=len(content),
            file_type=ext.lstrip("."),
            category="design_file",
            uploaded_by=uploaded_by,
            remark="设计文件上传",
        )
        self.db.add(att)
        await self.db.flush()
        await self.db.refresh(att)
        return {"id": str(att.id), "filename": att.filename, "file_size": att.file_size, "file_type": att.file_type}

    async def list_attachments(self, quote_id: str) -> list[dict]:
        result = await self.db.execute(
            select(Attachment).where(
                Attachment.related_type == "cdr_quote",
                Attachment.related_id == uuid.UUID(quote_id),
            ).order_by(Attachment.created_at.desc())
        )
        return [{"id": str(a.id), "filename": a.filename, "file_size": a.file_size,
                 "file_type": a.file_type,
                 "created_at": a.created_at.isoformat() if a.created_at else None}
                for a in result.scalars().all()]

    async def delete_attachment(self, att_id: str) -> None:
        att = await self.db.get(Attachment, uuid.UUID(att_id))
        if not att:
            raise ValueError("附件不存在")
        if os.path.exists(att.file_path):
            os.remove(att.file_path)
        await self.db.delete(att)

    async def parse_svg(self, att_id: str) -> dict:
        att = await self.db.get(Attachment, uuid.UUID(att_id))
        if not att:
            raise ValueError("附件不存在")
        if att.file_type != "svg":
            raise ValueError("仅支持 SVG 文件解析")
        with open(att.file_path, "r", encoding="utf-8", errors="replace") as f:
            svg_content = f.read()
        result = SvgShapeExtractor.extract_shapes(svg_content)
        result["filename"] = att.filename
        result["attachment_id"] = att_id
        return result

    async def ai_assist_from_description(self, quote_id: str, description: str, current_user_id: uuid.UUID) -> dict:
        from app.ai.gateway_providers.gateway_ai_client import GatewayAIClient
        from app.ai.core.resolver import FeatureResolver

        if not FeatureResolver.is_gateway_available():
            raise ValueError("AI 服务未配置")

        attachments = await self.list_attachments(quote_id)
        files_info = "\n".join("- " + a["filename"] + " (" + a["file_type"] + ")" for a in attachments) if attachments else "暂无上传文件"
        from app.models.business_document import BusinessDocument
        doc = await self.db.get(BusinessDocument, uuid.UUID(quote_id))
        project = doc.project_name if doc else "未命名"

        prompt = (
            "你是广告制作行业的报价专家。\n"
            "项目名称: " + project + "\n"
            "已上传设计文件:\n" + files_info + "\n\n"
            "用户需求:\n" + description + "\n\n"
            "请生成 JSON 格式报价明细行列表，每行包含:\n"
            "- description: 项目描述\n"
            "- width_mm: 宽度(mm)\n"
            "- height_mm: 高度(mm)\n"
            "- quantity: 数量\n"
            "- unit: 单位\n"
            "- material_suggestion: 建议材料\n"
            "仅输出 JSON，不要多余文字。"
        )

        client = GatewayAIClient(self.db)
        text = await client.chat_completion(prompt)

        import json, re as regex
        try:
            jm = regex.search(r"```(?:json)?\n?(.*?)\n?```", text, regex.DOTALL)
            parsed = json.loads(jm.group(1)) if jm else json.loads(text)
        except Exception:
            parsed = {"raw": text[:500]}

        return {"project_name": project, "files": [a["filename"] for a in attachments], "ai_suggestions": parsed}
