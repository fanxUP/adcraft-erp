from pathlib import Path


def test_project_cost_group_name_is_created_by_migration():
    versions_dir = Path(__file__).parents[1] / "alembic" / "versions"
    migration_sources = [
        path.read_text(encoding="utf-8")
        for path in versions_dir.glob("*.py")
    ]

    assert any(
        'op.add_column("project_costs", sa.Column("group_name"' in source
        for source in migration_sources
    )


def test_vehicle_dispatch_companions_is_created_by_migration():
    versions_dir = Path(__file__).parents[1] / "alembic" / "versions"
    migration_sources = [
        path.read_text(encoding="utf-8")
        for path in versions_dir.glob("*.py")
    ]

    assert any(
        '"vehicle_dispatches"' in source
        and 'sa.Column("companions"' in source
        and "op.add_column(" in source
        for source in migration_sources
    )


def test_quote_audit_log_matches_append_only_table():
    from app.models.cdr_quote import QuoteAuditLog

    columns = QuoteAuditLog.__table__.columns

    assert "created_at" in columns
    assert "updated_at" not in columns


def test_ai_business_rule_tables_are_created_by_migration():
    versions_dir = Path(__file__).parents[1] / "alembic" / "versions"
    migration_sources = [
        path.read_text(encoding="utf-8")
        for path in versions_dir.glob("*.py")
    ]

    assert any(
        '"ai_business_rules"' in source
        and '"ai_business_rule_sync_logs"' in source
        and "op.create_table(" in source
        for source in migration_sources
    )
