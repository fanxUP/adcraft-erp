"""CDR 智能报价——核心定价规则引擎。

设计原则：
- 纯业务逻辑，无状态，无副作用
- 相同输入 + 相同规则版本 = 相同输出
- 每一步计算记录到 pricing_trace
- 所有金额使用 Decimal，禁止 float
- 引擎不依赖数据库会话，所有数据通过参数传入
"""

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import Any
from uuid import UUID


# ── 数据类 ──────────────────────────────────────────────────────


@dataclass
class PriceTraceStep:
    """价格计算过程中的一个步骤记录。"""
    rule_code: str
    description: str
    input_value: dict | None = None
    output_value: dict | None = None


@dataclass
class ProductInfo:
    """产品信息（从 DB 加载）。"""
    id: UUID
    pricing_method: str  # area | length | quantity | fixed | tiered
    default_price: Decimal
    min_charge: Decimal
    default_loss_rate: Decimal
    requires_geometry: bool
    needs_installation: bool
    allows_outsource: bool
    needs_approval: bool
    unit: str


@dataclass
class MaterialInfo:
    """材料信息（从 DB 加载）。"""
    id: UUID
    name: str
    purchase_price: Decimal
    sale_price: Decimal
    loss_rate: Decimal
    unit: str
    thickness_mm: Decimal | None = None
    sheet_width_mm: Decimal | None = None
    sheet_height_mm: Decimal | None = None


@dataclass
class ProcessInfo:
    """工艺信息（从 DB 加载）。"""
    id: UUID
    name: str
    billing_basis: str  # area | length | quantity | hours | fixed
    default_price: Decimal
    startup_fee: Decimal
    min_charge: Decimal
    standard_hours: Decimal | None = None


@dataclass
class CalculateRequest:
    """报价计算请求。"""
    product: ProductInfo
    material: MaterialInfo | None = None
    processes: list[ProcessInfo] = field(default_factory=list)
    last_deal_price: Decimal | None = None
    customer_level: str | None = None

    # 几何参数
    width_mm: Decimal | None = None
    height_mm: Decimal | None = None
    length_m: Decimal | None = None
    quantity: Decimal = Decimal("1")
    pieces: Decimal | None = None

    # Phase 7: 高级几何
    hole_area_mm2: Decimal | None = None
    is_open_curve: bool = False
    curve_length_mm: Decimal | None = None
    use_sheet_rounding: bool = False
    sheet_width_mm: Decimal | None = None
    sheet_height_mm: Decimal | None = None
    sheet_sale_price: Decimal | None = None

    # 客户输入
    customer_discount_rate: Decimal = Decimal("1")
    manual_unit_price: Decimal | None = None
    manual_adjustment: Decimal = Decimal("0")

    # 系统参数
    tax_rate: Decimal = Decimal("0")


@dataclass
class CalculateResult:
    """报价计算响应。"""
    billable_quantity: Decimal = Decimal("0")
    unit_price: Decimal = Decimal("0")
    subtotal_amount: Decimal = Decimal("0")
    material_cost: Decimal = Decimal("0")
    process_cost: Decimal = Decimal("0")
    startup_fee: Decimal = Decimal("0")
    total_cost: Decimal = Decimal("0")
    discount_amount: Decimal = Decimal("0")
    tax_amount: Decimal = Decimal("0")
    total_amount: Decimal = Decimal("0")
    minimum_charge_applied: bool = False
    requires_approval: bool = False
    # Phase 7 几何估算标记
    geometry_estimates: dict | None = None
    sheet_usage: dict | None = None
    warnings: list[str] = field(default_factory=list)
    pricing_trace: list[PriceTraceStep] = field(default_factory=list)


# ── 单位换算常量 ────────────────────────────────────────────────

SQMM_PER_SQM = Decimal("1000000")  # 1 平方米 = 1,000,000 平方毫米
MM_PER_M = Decimal("1000")


# ── 定价引擎核心 ────────────────────────────────────────────────


class PriceEngine:
    """报价规则引擎——不依赖数据库，纯计算。"""

    ROUND_PRECISION = Decimal("0.01")  # 最终金额保留 2 位小数
    CALC_PRECISION = Decimal("0.0001")  # 中间计算保留 4 位小数

    def calculate(self, req: CalculateRequest) -> CalculateResult:
        """执行完整报价计算，返回结果含执行明细。"""
        result = CalculateResult()
        trace = result.pricing_trace

        # ── 1. 计算计费面积/数量 ──
        net_area_m2, billable_qty = self._compute_billable_quantity(req)

        # Phase 7: 几何估算标记
        geo_estimates = {}
        if req.hole_area_mm2 and req.hole_area_mm2 > 0:
            hole_m2 = (req.hole_area_mm2 * req.quantity) / SQMM_PER_SQM
            geo_estimates["hole_area_m2"] = str(hole_m2)
            geo_estimates["net_area_m2"] = str(net_area_m2)
        if req.is_open_curve:
            geo_estimates["is_open_curve"] = True
            geo_estimates["curve_length_mm"] = str(req.curve_length_mm or req.length_m or 0)
        if geo_estimates:
            result.geometry_estimates = geo_estimates

        trace_input = {
            "width_mm": str(req.width_mm) if req.width_mm else None,
            "height_mm": str(req.height_mm) if req.height_mm else None,
            "length_m": str(req.length_m) if req.length_m else None,
            "quantity": str(req.quantity),
            "loss_rate": str(req.product.default_loss_rate),
        }
        if req.hole_area_mm2:
            trace_input["hole_area_mm2"] = str(req.hole_area_mm2)
        if req.is_open_curve:
            trace_input["is_open_curve"] = "true"
            trace_input["curve_length_mm"] = str(req.curve_length_mm or req.length_m or 0)

        trace.append(PriceTraceStep(
            rule_code="BILLABLE-QTY",
            description="计算计费数量",
            input_value=trace_input,
            output_value={
                "net_area_m2": str(net_area_m2),
                "billable_quantity": str(billable_qty),
            },
        ))
        result.billable_quantity = billable_qty

        # ── 2. 计算材料成本 ──
        material_cost = self._calc_material_cost(req, billable_qty)
        if req.use_sheet_rounding and req.sheet_width_mm and req.sheet_height_mm:
            from app.services.geometry_service import geometry_service
            sr = geometry_service.estimate_sheets(
                width_mm=req.width_mm or Decimal("0"),
                height_mm=req.height_mm or Decimal("0"),
                sheet_w=req.sheet_width_mm,
                sheet_h=req.sheet_height_mm,
                quantity=req.quantity,
            )
            result.sheet_usage = {
                "sheets_needed": sr.get("sheets_needed", 0),
                "per_sheet": sr.get("per_sheet", 0),
                "utilization_pct": str(sr.get("utilization_pct", "0")),
                "is_estimated": sr.get("is_estimated", True),
            }
            trace.append(PriceTraceStep(
                rule_code="SHEET-ROUND",
                description="板材整张取整",
                input_value={"sheet_w_mm": str(req.sheet_width_mm), "sheet_h_mm": str(req.sheet_height_mm)},
                output_value={"sheets_needed": str(sr.get("sheets_needed", 0)), "utilization": str(sr.get("utilization_pct", "0"))},
            ))
        result.material_cost = material_cost
        if material_cost > 0:
            trace.append(PriceTraceStep(
                rule_code="MAT-COST",
                description="材料成本",
                input_value={"billable_qty": str(billable_qty)},
                output_value={"material_cost": str(material_cost)},
            ))

        # ── 3. 确定单价 ──
        unit_price = self._resolve_unit_price(req)
        result.unit_price = unit_price
        trace.append(PriceTraceStep(
            rule_code="UNIT-PRICE",
            description="定价",
            input_value={"pricing_method": req.product.pricing_method},
            output_value={"unit_price": str(unit_price)},
        ))

        # ── 4. 计算小计 ──
        subtotal = (billable_qty * unit_price).quantize(self.ROUND_PRECISION)
        result.subtotal_amount = subtotal

        # ── 5. 最低消费判断 ──
        min_charge = self._get_min_charge(req)
        if min_charge > 0 and subtotal < min_charge:
            result.minimum_charge_applied = True
            subtotal = min_charge
            trace.append(PriceTraceStep(
                rule_code="MIN-CHARGE",
                description="最低消费",
                input_value={"min_charge": str(min_charge), "subtotal_before": str(result.subtotal_amount)},
                output_value={"subtotal_after": str(subtotal)},
            ))
        result.subtotal_amount = subtotal

        # ── 6. 工艺费用 ──
        process_cost, startup_fee_total = self._calc_process_cost(req, billable_qty)
        result.process_cost = process_cost
        result.startup_fee = startup_fee_total
        if process_cost > 0 or startup_fee_total > 0:
            trace.append(PriceTraceStep(
                rule_code="PROCESS-COST",
                description="工艺费用",
                output_value={
                    "process_cost": str(process_cost),
                    "startup_fee": str(startup_fee_total),
                },
            ))

        # ── 7. 总成本 ──
        total_cost = material_cost + process_cost + startup_fee_total
        result.total_cost = total_cost.quantize(self.ROUND_PRECISION)

        # ── 8. 折扣 ──
        discount_rate = self._resolve_discount_rate(req)
        if discount_rate < Decimal("1"):
            discount_amount = (subtotal * (Decimal("1") - discount_rate)).quantize(self.ROUND_PRECISION)
            result.discount_amount = discount_amount
            trace.append(PriceTraceStep(
                rule_code="DISCOUNT",
                description="客户折扣",
                input_value={"discount_rate": str(discount_rate)},
                output_value={"discount_amount": str(discount_amount)},
            ))

        # ── 9. 税前金额 ──
        pre_tax = subtotal - result.discount_amount

        # ── 10. 税费 ──
        if req.tax_rate > 0:
            tax = (pre_tax * req.tax_rate / Decimal("100")).quantize(self.ROUND_PRECISION)
            result.tax_amount = tax
            trace.append(PriceTraceStep(
                rule_code="TAX",
                description=f"增值税（税率 {req.tax_rate}%）",
                input_value={"tax_rate": str(req.tax_rate), "pre_tax": str(pre_tax)},
                output_value={"tax_amount": str(tax)},
            ))

        # ── 11. 最终总价 ──
        result.total_amount = (pre_tax + result.tax_amount).quantize(self.ROUND_PRECISION)

        # ── 12. 手工调整 ──
        if req.manual_adjustment != 0:
            result.total_amount = (result.total_amount + req.manual_adjustment).quantize(self.ROUND_PRECISION)
            trace.append(PriceTraceStep(
                rule_code="MANUAL-ADJ",
                description="手工调整",
                input_value={"adjustment": str(req.manual_adjustment)},
                output_value={"total_after": str(result.total_amount)},
            ))

        # ── 13. 审批触发检查 ──
        result.requires_approval = self._check_requires_approval(req, result)
        if result.requires_approval:
            result.warnings.append("该报价需要审批")

        # ── 报价说明 ──
        if req.product.needs_installation:
            result.warnings.append("该产品需要安装——请在订单阶段安排安装任务")
        if req.material and req.material.loss_rate > 0:
            result.warnings.append(f"材料损耗率：{req.material.loss_rate * 100}%")

        return result

    # ── 内部方法 ──────────────────────────────────────────────

    def _compute_billable_quantity(self, req: CalculateRequest) -> tuple[Decimal, Decimal]:
        """计算净面积和计费数量（含孔洞扣除、开放曲线处理）。"""
        method = req.product.pricing_method

        if method == "area":
            if req.width_mm and req.height_mm:
                base_area_m2 = (req.width_mm * req.height_mm * req.quantity) / SQMM_PER_SQM
                # Phase 7: 孔洞面积扣除
                if req.hole_area_mm2 and req.hole_area_mm2 > 0:
                    hole_m2 = (req.hole_area_mm2 * req.quantity) / SQMM_PER_SQM
                    area_m2 = max(base_area_m2 - hole_m2, Decimal("0"))
                else:
                    area_m2 = base_area_m2
            else:
                area_m2 = Decimal("0")

            # 加损耗
            loss_rate = req.product.default_loss_rate or (req.material.loss_rate if req.material else Decimal("0"))
            billable = area_m2 * (Decimal("1") + loss_rate)
            return area_m2.quantize(self.CALC_PRECISION), billable.quantize(self.CALC_PRECISION)

        elif method == "length":
            # Phase 7: 开放曲线优先使用 curve_length_mm
            if req.is_open_curve and req.curve_length_mm and req.curve_length_mm > 0:
                total_m = (req.curve_length_mm * req.quantity) / MM_PER_M
            else:
                total_m = (req.length_m or Decimal("0")) * req.quantity
            loss_rate = req.product.default_loss_rate or (req.material.loss_rate if req.material else Decimal("0"))
            billable = total_m * (Decimal("1") + loss_rate)
            return total_m.quantize(self.CALC_PRECISION), billable.quantize(self.CALC_PRECISION)

        elif method in ("quantity", "tiered", "fixed"):
            qty = req.quantity
            if req.pieces and req.pieces > 1:
                qty = qty * req.pieces
            loss_rate = req.product.default_loss_rate or (req.material.loss_rate if req.material else Decimal("0"))
            billable = qty * (Decimal("1") + loss_rate)
            return qty.quantize(self.CALC_PRECISION), billable.quantize(self.CALC_PRECISION)

        return Decimal("0"), Decimal("0")

    def _calc_material_cost(self, req: CalculateRequest, billable_qty: Decimal) -> Decimal:
        """计算材料成本（含整张取整支持）。"""
        if not req.material:
            return Decimal("0")

        # Phase 7: 整张取整材料成本
        if req.use_sheet_rounding and req.sheet_width_mm and req.sheet_height_mm:
            sheet_cost = self._calc_sheet_material_cost(req)
            if sheet_cost is not None:
                return sheet_cost

        method = req.product.pricing_method
        if method == "area":
            cost = req.material.sale_price * billable_qty
        elif method == "length":
            cost = req.material.sale_price * billable_qty
        else:
            cost = req.material.sale_price * billable_qty

        return cost.quantize(self.ROUND_PRECISION)

    def _calc_sheet_material_cost(self, req: CalculateRequest) -> Decimal | None:
        """整张取整材料成本计算。"""
        if not req.width_mm or not req.height_mm:
            return None
        from app.services.geometry_service import geometry_service
        result = geometry_service.estimate_sheets(
            width_mm=req.width_mm,
            height_mm=req.height_mm,
            sheet_w=req.sheet_width_mm,
            sheet_h=req.sheet_height_mm,
            quantity=req.quantity,
        )
        if result.get("is_estimated") or result["sheets_needed"] <= 0:
            return None
        sale_price = req.sheet_sale_price or (req.material.sale_price if req.material else Decimal("0"))
        cost = Decimal(str(result["sheets_needed"])) * sale_price
        return cost.quantize(self.ROUND_PRECISION)

    def _resolve_unit_price(self, req: CalculateRequest) -> Decimal:
        """确定单价（优先级：手工价 > 客户最近成交价 > 材料售价 > 产品默认价）。"""
        # 1. 手工输入单价
        if req.manual_unit_price is not None:
            return req.manual_unit_price

        # 2. 客户最近一次成交/报价单价
        if req.last_deal_price is not None and req.last_deal_price > 0:
            return req.last_deal_price

        # 3. 材料售价（材料计价时）
        if req.material and req.material.sale_price > 0:
            return req.material.sale_price

        # 4. 产品默认价
        if req.product.default_price > 0:
            return req.product.default_price

        return Decimal("0")

    def _get_min_charge(self, req: CalculateRequest) -> Decimal:
        """获取最低消费。"""
        if req.product.min_charge > 0:
            return req.product.min_charge

        return Decimal("0")

    def _resolve_discount_rate(self, req: CalculateRequest) -> Decimal:
        """确定折扣率。"""
        # 客户输入折扣率
        if req.customer_discount_rate < Decimal("1"):
            return req.customer_discount_rate

        return Decimal("1")

    def _calc_process_cost(
        self, req: CalculateRequest, billable_qty: Decimal
    ) -> tuple[Decimal, Decimal]:
        """计算工艺费用总额和开机费。"""
        if not req.processes:
            return Decimal("0"), Decimal("0")

        total_process = Decimal("0")
        total_startup = Decimal("0")

        for proc in req.processes:
            cost = Decimal("0")

            if proc.billing_basis == "area":
                cost = proc.default_price * billable_qty
            elif proc.billing_basis == "quantity":
                cost = proc.default_price * req.quantity
            elif proc.billing_basis == "fixed":
                cost = proc.default_price
            elif proc.billing_basis == "hours" and proc.standard_hours:
                cost = proc.default_price * proc.standard_hours

            total_process += cost
            total_startup += proc.startup_fee

        return total_process.quantize(self.ROUND_PRECISION), total_startup.quantize(self.ROUND_PRECISION)

    def _check_requires_approval(self, req: CalculateRequest, result: CalculateResult) -> bool:
        """判断是否需要审批。"""
        if req.product.needs_approval:
            return True

        # 手工调整超过 10% 需要审批
        if req.manual_adjustment != 0 and result.subtotal_amount > 0:
            adj_ratio = abs(req.manual_adjustment) / result.subtotal_amount
            if adj_ratio > Decimal("0.1"):
                return True

        # 毛利率过低（低于 15% 需要审批）
        if result.total_cost > 0 and result.subtotal_amount > 0:
            margin = (result.subtotal_amount - result.total_cost) / result.subtotal_amount
            if margin < Decimal("0.15"):
                return True

        return False


# ── 便捷单例 ────────────────────────────────────────────────────

engine = PriceEngine()


def calculate(req: CalculateRequest) -> CalculateResult:
    """便捷调用入口。"""
    return engine.calculate(req)
