"""Regression tests for quote-to-production deviation matching."""

from types import SimpleNamespace


def test_compare_line_passes_quote_line_before_production_task():
    from app.ai.rule_based.deviation_analyzer import DeviationAnalyzer

    quote_line = SimpleNamespace(
        line_no=1,
        description="PVC",
        amount=100,
        estimated_cost=30,
        width_mm=1000,
        height_mm=500,
        length_m=None,
        quantity=2,
        unit_price=50,
        product_id=None,
    )
    production_task = SimpleNamespace(
        material_id=None,
        production_no="PVC-001",
        project_name="PVC panel",
        quantity=2,
        width=1.0,
        height=0.5,
        status="completed",
    )

    result = DeviationAnalyzer(None)._compare_line(quote_line, [production_task])

    assert result["no_production_data"] is False
    assert result["actual"]["quantity"] == 2.0
    assert result["deviation"]["quantity"]["diff"] == 0.0
