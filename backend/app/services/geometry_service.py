"""CDR 智能报价——几何分析服务。

纯业务逻辑，无状态，无数据库依赖。
所有方法不抛出异常：失败时返回 is_estimated=True + fallback 值。
所有计算使用 Decimal，禁止 float。
"""

from decimal import Decimal, ROUND_HALF_UP, ROUND_CEILING
from typing import Any


class GeometryService:
    """几何计算服务 — 纯业务逻辑，无状态。"""

    ROUND_4 = Decimal("0.0001")
    ROUND_2 = Decimal("0.01")

    # ── 净面积（含孔洞扣除） ──────────────────────────────────────

    def calculate_net_area(
        self,
        width_mm: Decimal,
        height_mm: Decimal,
        holes: list[dict] | None = None,
    ) -> dict:
        """计算净面积：包围盒面积 - 孔洞面积。

        holes 格式: [{"area_mm2": Decimal | int | float, "type": "cutout|inner"}]
        """
        try:
            w = Decimal(str(width_mm))
            h = Decimal(str(height_mm))
            bbox_area = (w * h).quantize(self.ROUND_4)
            hole_area = Decimal("0")
            for hole in (holes or []):
                hole_area += Decimal(str(hole.get("area_mm2", 0)))
            hole_area = hole_area.quantize(self.ROUND_4)
            net_area = max(bbox_area - hole_area, Decimal("0")).quantize(self.ROUND_4)
            return {
                "bbox_area_mm2": bbox_area,
                "hole_area_mm2": hole_area,
                "net_area_mm2": net_area,
                "hole_ratio": (hole_area / bbox_area).quantize(self.ROUND_4) if bbox_area > 0 else Decimal("0"),
                "is_estimated": False,
            }
        except Exception as e:
            return {
                "bbox_area_mm2": None,
                "hole_area_mm2": None,
                "net_area_mm2": None,
                "hole_ratio": Decimal("0"),
                "is_estimated": True,
                "error": str(e),
            }

    # ── 曲线分类 ──────────────────────────────────────────────────

    def classify_curve(self, curve_data: dict) -> dict:
        """区分开放/闭合曲线。

        curve_data 期望字段:
          - type: str ("curve" | "open_curve" | "closed_curve")
          - closed: bool (CDR 返回的闭合标记)
          - length_mm: Decimal | int | float
          - area_mm2: Decimal | int | float (闭合曲线面积)
        """
        try:
            is_closed = curve_data.get("closed", False) or curve_data.get("type") in ("closed_curve",)
            length = Decimal(str(curve_data.get("length_mm", 0)))
            area = Decimal(str(curve_data.get("area_mm2", 0))) if is_closed else Decimal("0")
            return {
                "is_closed": bool(is_closed),
                "length_mm": length.quantize(self.ROUND_4),
                "area_mm2": area.quantize(self.ROUND_4),
                "is_estimated": False,
            }
        except Exception as e:
            return {
                "is_closed": False,
                "length_mm": Decimal("0"),
                "area_mm2": Decimal("0"),
                "is_estimated": True,
                "error": str(e),
            }

    # ── 重叠检测 ──────────────────────────────────────────────────

    def detect_overlap(self, objects: list[dict]) -> dict:
        """检测对象重叠。

        检查每个对象包围盒与其它对象的交集。
        objects 格式: [{"left": D, "top": D, "width": D, "height": D, ...}]
        """
        try:
            count = 0
            total_overlap_area = Decimal("0")
            overlaps = []
            rects = []
            for obj in objects:
                try:
                    l = Decimal(str(obj.get("left", 0)))
                    t = Decimal(str(obj.get("top", 0)))
                    r = l + Decimal(str(obj.get("width", 0)))
                    b = t + Decimal(str(obj.get("height", 0)))
                    rects.append({"left": l, "top": t, "right": r, "bottom": b})
                except Exception:
                    rects.append(None)

            n = len(rects)
            for i in range(n):
                if rects[i] is None:
                    continue
                for j in range(i + 1, n):
                    if rects[j] is None:
                        continue
                    ri, rj = rects[i], rects[j]
                    # 检查是否有交集
                    if ri["right"] > rj["left"] and rj["right"] > ri["left"] \
                       and ri["bottom"] > rj["top"] and rj["bottom"] > ri["top"]:
                        ox = min(ri["right"], rj["right"]) - max(ri["left"], rj["left"])
                        oy = min(ri["bottom"], rj["bottom"]) - max(ri["top"], rj["top"])
                        if ox > 0 and oy > 0:
                            oa = (ox * oy).quantize(self.ROUND_4)
                            total_overlap_area += oa
                            count += 1
                            overlaps.append({"i": i, "j": j, "overlap_area_mm2": oa})

            return {
                "overlap_count": count,
                "overlap_area_mm2": total_overlap_area.quantize(self.ROUND_4),
                "overlaps": overlaps,
                "is_estimated": False,
            }
        except Exception as e:
            return {
                "overlap_count": 0,
                "overlap_area_mm2": Decimal("0"),
                "overlaps": [],
                "is_estimated": True,
                "error": str(e),
            }

    # ── 板材整张取整 ──────────────────────────────────────────────

    def estimate_sheets(
        self,
        width_mm: Decimal,
        height_mm: Decimal,
        sheet_w: Decimal,
        sheet_h: Decimal,
        quantity: Decimal = Decimal("1"),
        allow_rotation: bool = True,
    ) -> dict:
        """板材整张取整计算。

        返回需用张数、每张可放数量、利用率。
        支持旋转（宽高互换以获得更优排列）。
        """
        try:
            w = Decimal(str(width_mm))
            h = Decimal(str(height_mm))
            sw = Decimal(str(sheet_w))
            sh = Decimal(str(sheet_h))
            qty = Decimal(str(quantity))

            if w <= 0 or h <= 0 or sw <= 0 or sh <= 0:
                return {
                    "sheets_needed": 0,
                    "per_sheet": 0,
                    "utilization_pct": Decimal("0"),
                    "is_estimated": True,
                    "error": "尺寸必须大于 0",
                }

            # 计算不旋转
            cols1 = int(sw / w)
            rows1 = int(sh / h)
            per_sheet1 = cols1 * rows1

            # 计算旋转（宽高互换）
            per_sheet2 = 0
            if allow_rotation:
                cols2 = int(sw / h)
                rows2 = int(sh / w)
                per_sheet2 = cols2 * rows2

            # 选最优
            if per_sheet2 > per_sheet1:
                per_sheet = per_sheet2
                used_w = h  # 旋转后摆放尺寸
                used_h = w
                cols = int(sw / h)
                rows = int(sh / w)
                rotated = True
            else:
                per_sheet = per_sheet1
                used_w = w
                used_h = h
                cols = cols1
                rows = rows1
                rotated = False

            if per_sheet <= 0:
                return {
                    "sheets_needed": 0,
                    "per_sheet": 0,
                    "utilization_pct": Decimal("0"),
                    "is_estimated": True,
                    "error": "单件尺寸超过板材尺寸，无法排版",
                }

            # 需要张数（向上取整）
            sheets = int((qty + Decimal(per_sheet) - Decimal("1")) / Decimal(per_sheet))
            # 利用率 = (单件面积 × 每张数量) / 板材面积
            piece_area = w * h
            sheet_area = sw * sh
            utilization = (piece_area * Decimal(per_sheet) / sheet_area * Decimal("100")).quantize(self.ROUND_2)

            return {
                "sheets_needed": sheets,
                "per_sheet": per_sheet,
                "cols": cols,
                "rows": rows,
                "rotated": rotated,
                "utilization_pct": utilization,
                "piece_area_mm2": piece_area.quantize(self.ROUND_4),
                "sheet_area_mm2": sheet_area.quantize(self.ROUND_4),
                "is_estimated": False,
            }
        except Exception as e:
            return {
                "sheets_needed": 0,
                "per_sheet": 0,
                "utilization_pct": Decimal("0"),
                "is_estimated": True,
                "error": str(e),
            }

    # ── 简易排版 ──────────────────────────────────────────────────

    def simple_nesting(
        self,
        rects: list[dict],
        sheet_w: Decimal,
        sheet_h: Decimal,
    ) -> dict:
        """简易排版：按高度从大到小排序，从左到右排列。

        rects: [{"id": str, "w": Decimal, "h": Decimal, "qty": int}]
        返回 sheets: [{"sheet_no": int, "items": [...]}]
        """
        try:
            sw = Decimal(str(sheet_w))
            sh = Decimal(str(sheet_h))

            # 展开所有件，按高度降序
            pieces = []
            for r in rects:
                w = Decimal(str(r.get("w", 0)))
                h = Decimal(str(r.get("h", 0)))
                qty = int(r.get("qty", 1))
                for _ in range(qty):
                    pieces.append({"id": r.get("id", ""), "w": w, "h": h})

            if not pieces:
                return {"sheets": [], "is_estimated": False}

            # 按高度降序，高度相同按宽度降序
            pieces.sort(key=lambda p: (-p["h"], -p["w"]))

            sheets = []
            current_sheet = {"sheet_no": 1, "items": []}
            # 简单行式排版：每行放满后换行
            cursor_x = Decimal("0")
            cursor_y = Decimal("0")
            row_h = Decimal("0")

            for p in pieces:
                pw, ph = p["w"], p["h"]
                if pw > sw or ph > sh:
                    # 单件超过板材，尝试旋转
                    if ph <= sw and pw <= sh:
                        pw, ph = ph, pw
                    else:
                        continue  # 实在放不下，跳过

                # 当前行放不下，换行
                if cursor_x + pw > sw:
                    cursor_x = Decimal("0")
                    cursor_y += row_h
                    row_h = Decimal("0")

                # 换行后超出板材高度，新开一张
                if cursor_y + ph > sh:
                    if current_sheet["items"]:
                        sheets.append(current_sheet)
                    current_sheet = {"sheet_no": len(sheets) + 1, "items": []}
                    cursor_x = Decimal("0")
                    cursor_y = Decimal("0")
                    row_h = Decimal("0")

                p["x"] = cursor_x
                p["y"] = cursor_y
                current_sheet["items"].append(p)

                cursor_x += pw
                row_h = max(row_h, ph)

            if current_sheet["items"]:
                sheets.append(current_sheet)

            # 计算利用率
            total_piece_area = sum(
                Decimal(str(it["w"])) * Decimal(str(it["h"]))
                for s in sheets for it in s["items"]
            )
            total_sheet_area = sw * sh * Decimal(len(sheets))
            utilization = (total_piece_area / total_sheet_area * Decimal("100")).quantize(self.ROUND_2) if total_sheet_area > 0 else Decimal("0")

            return {
                "sheets": sheets,
                "total_sheets": len(sheets),
                "total_pieces": len(pieces),
                "utilization_pct": utilization,
                "is_estimated": False,
            }
        except Exception as e:
            return {
                "sheets": [],
                "total_sheets": 0,
                "total_pieces": 0,
                "utilization_pct": Decimal("0"),
                "is_estimated": True,
                "error": str(e),
            }

    # ── CDR 载荷分析 ──────────────────────────────────────────────

    def analyze_cdr_payload(self, payload: dict) -> dict:
        """从 CDR capture_payload 提取完整几何分析。

        capture_payload 期望结构（CDR 插件返回）：
        {
            "objects": [
                {"type": "curve|rectangle|text|bitmap|ellipse|...",
                 "width_mm": D, "height_mm": D, "length_mm": D,
                 "area_mm2": D, "closed": bool,
                 "left": D, "top": D, ...}
            ],
            "page": {"width_mm": D, "height_mm": D},
            "selection_count": int,
        }
        """
        try:
            objects = payload.get("objects", [])
            page = payload.get("page", {})

            # 统计各类型
            type_counts: dict[str, int] = {}
            total_bbox_area = Decimal("0")
            total_curve_length = Decimal("0")
            closed_curves = []
            open_curves = []
            holes_detected = []

            for obj in objects:
                obj_type = obj.get("type", "unknown")
                type_counts[obj_type] = type_counts.get(obj_type, 0) + 1

                w = Decimal(str(obj.get("width_mm", 0)))
                h = Decimal(str(obj.get("height_mm", 0)))
                total_bbox_area += w * h

                length = Decimal(str(obj.get("length_mm", 0)))
                total_curve_length += length

                is_closed = bool(obj.get("closed", False))
                if obj_type in ("curve",):
                    if is_closed:
                        closed_curves.append(obj)
                    else:
                        open_curves.append(obj)

                # 检测可能的孔洞（小的闭合曲线在大闭合曲线内部）
                if is_closed and obj.get("area_mm2", 0) > 0:
                    holes_detected.append({
                        "area_mm2": Decimal(str(obj.get("area_mm2", 0))),
                        "type": "inner",
                    })

            # 重叠检测
            overlap = self.detect_overlap(objects)

            return {
                "object_count": len(objects),
                "type_counts": type_counts,
                "total_bbox_area_mm2": total_bbox_area.quantize(self.ROUND_4),
                "total_curve_length_mm": total_curve_length.quantize(self.ROUND_4),
                "closed_curve_count": len(closed_curves),
                "open_curve_count": len(open_curves),
                "holes_detected": holes_detected,
                "total_hole_area_mm2": sum(h["area_mm2"] for h in holes_detected).quantize(self.ROUND_4),
                "overlap": overlap,
                "page": {
                    "width_mm": Decimal(str(page.get("width_mm", 0))).quantize(self.ROUND_4),
                    "height_mm": Decimal(str(page.get("height_mm", 0))).quantize(self.ROUND_4),
                } if page else None,
                "is_estimated": False,
            }
        except Exception as e:
            return {
                "object_count": 0,
                "type_counts": {},
                "is_estimated": True,
                "error": str(e),
            }


# ── 便捷单例 ──────────────────────────────────────────────────

geometry_service = GeometryService()
