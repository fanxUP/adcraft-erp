"""2D 排版套料服务。

策略模式：NestingStrategy 抽象基类 + 具体实现。
NestingService 编排器，失败时返回估算标记。
"""

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any


class NestingStrategy(ABC):
    """排版策略接口。"""

    @abstractmethod
    def nest(self, rects: list[dict], sheet_w: Decimal, sheet_h: Decimal) -> dict:
        """执行排版。

        rects: [{"id": str, "w": Decimal, "h": Decimal, "qty": int}]
        返回 {"sheets": [...], "utilization_pct": D, "is_estimated": bool}
        """


class SimpleGridNesting(NestingStrategy):
    """简易网格排版：按高度排序，从左到右排列，换行处理。"""

    def nest(self, rects: list[dict], sheet_w: Decimal, sheet_h: Decimal) -> dict:
        sw = Decimal(str(sheet_w))
        sh = Decimal(str(sheet_h))

        # 展开所有件
        pieces = []
        for r in rects:
            w = Decimal(str(r.get("w", 0)))
            h = Decimal(str(r.get("h", 0)))
            qty = int(r.get("qty", 1))
            if w <= 0 or h <= 0:
                continue
            for _ in range(qty):
                pieces.append({"id": r.get("id", ""), "w": w, "h": h, "rotated": False})

        if not pieces:
            return {"sheets": [], "total_sheets": 0, "utilization_pct": Decimal("0"), "is_estimated": False}

        # 按高度降序
        pieces.sort(key=lambda p: (-p["h"], -p["w"]))

        sheets = []
        current_sheet = {"sheet_no": 1, "items": []}
        cursor_x = Decimal("0")
        cursor_y = Decimal("0")
        row_h = Decimal("0")

        for p in pieces:
            pw, ph = p["w"], p["h"]

            # 尝试旋转
            if pw > sw or ph > sh:
                if ph <= sw and pw <= sh:
                    pw, ph = ph, pw
                    p["rotated"] = True
                else:
                    continue  # 放不下

            # 当前行放不下 → 换行
            if cursor_x + pw > sw:
                cursor_x = Decimal("0")
                cursor_y += row_h
                row_h = Decimal("0")

            # 换行后超出高度 → 新板
            if cursor_y + ph > sh:
                if current_sheet["items"]:
                    sheets.append(current_sheet)
                current_sheet = {"sheet_no": len(sheets) + 1, "items": []}
                cursor_x = Decimal("0")
                cursor_y = Decimal("0")
                row_h = Decimal("0")

                # 再试一次（旋转可能改变尺寸）
                pw2, ph2 = p["w"], p["h"]
                if p["rotated"]:
                    pw2, ph2 = ph2, pw2
                if pw2 > sw or ph2 > sh:
                    continue

            p["x"] = cursor_x
            p["y"] = cursor_y
            p["w"] = pw
            p["h"] = ph
            current_sheet["items"].append(p)
            cursor_x += pw
            row_h = max(row_h, ph)

        if current_sheet["items"]:
            sheets.append(current_sheet)

        total_piece_area = sum(
            Decimal(str(it["w"])) * Decimal(str(it["h"]))
            for s in sheets for it in s["items"]
        )
        total_sheet_area = sw * sh * Decimal(len(sheets))
        utilization = (
            (total_piece_area / total_sheet_area * Decimal("100")).quantize(Decimal("0.01"))
            if total_sheet_area > 0 else Decimal("0")
        )

        return {
            "sheets": sheets,
            "total_sheets": len(sheets),
            "total_pieces": sum(len(s["items"]) for s in sheets),
            "total_pieces_input": len(pieces),
            "utilization_pct": utilization,
            "is_estimated": False,
        }


class NestingService:
    """排版编排服务。按需选择策略，失败则回退返回估算。"""

    def __init__(self, strategy: NestingStrategy | None = None):
        self._strategy = strategy or SimpleGridNesting()

    def calculate(self, rects: list[dict], sheet_w: Decimal, sheet_h: Decimal) -> dict:
        """执行排版计算，失败回退不抛异常。"""
        try:
            result = self._strategy.nest(rects, sheet_w, sheet_h)
            return result
        except Exception as e:
            return {
                "sheets": [],
                "total_sheets": 0,
                "total_pieces": 0,
                "utilization_pct": Decimal("0"),
                "is_estimated": True,
                "error": str(e),
            }
