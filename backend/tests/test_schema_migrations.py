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


def test_cdr_quote_lines_receive_regular_quote_fields_by_migration():
    versions_dir = Path(__file__).parents[1] / "alembic" / "versions"
    migration_sources = [
        path.read_text(encoding="utf-8")
        for path in versions_dir.glob("*.py")
    ]

    assert any(
        '"quote_lines"' in source
        and '"material_process"' in source
        and '"process_fee"' in source
        and '"group_name"' in source
        and "op.add_column(" in source
        for source in migration_sources
    )


def test_existing_quote_length_and_width_are_moved_to_width_and_height():
    versions_dir = Path(__file__).parents[1] / "alembic" / "versions"
    migration_sources = [
        path.read_text(encoding="utf-8")
        for path in versions_dir.glob("*.py")
    ]

    assert any(
        "UPDATE business_document_items AS item" in source
        and "height = item.width" in source
        and "width = item.length" in source
        and "length = NULL" in source
        and "document.doc_type = 'quote'" in source
        for source in migration_sources
    )


def test_order_item_lifecycle_migration_is_additive_and_reversible():
    versions_dir = Path(__file__).parents[1] / "alembic" / "versions"
    source = next(
        path.read_text(encoding="utf-8")
        for path in versions_dir.glob("*.py")
        if path.name.startswith("j1k2l3m4n5o6_")
    )

    assert 'op.add_column(' in source
    assert '"business_document_items"' in source
    assert '"lifecycle_status"' in source
    assert 'server_default="active"' in source
    assert '"voided_at"' in source
    assert '"void_reason"' in source
    assert '"superseded_by_item_id"' in source
    assert 'op.create_foreign_key(' in source
    assert 'op.create_index(' in source
    assert 'op.drop_constraint(' in source
    assert 'op.drop_column("business_document_items", "lifecycle_status")' in source


def test_outsource_order_item_migration_adds_safe_fk_index_and_decimal_quantity():
    versions_dir = Path(__file__).parents[1] / "alembic" / "versions"
    source = next(
        path.read_text(encoding="utf-8")
        for path in versions_dir.glob("*.py")
        if "outsource_order_item" in path.name
    )

    assert 'revision = "k2l3m4n5o6p7"' in source
    assert 'down_revision = "j1k2l3m4n5o6"' in source
    assert 'op.create_foreign_key(' in source
    assert '"fk_outsource_tasks_order_item_id"' in source
    assert 'ondelete="SET NULL"' in source
    assert 'op.create_index(' in source
    assert '"ix_outsource_order_item"' in source
    assert 'sa.Numeric(14, 3)' in source
    assert 'postgresql_using="quantity::numeric"' in source
    assert 'quantity != trunc(quantity)' in source
