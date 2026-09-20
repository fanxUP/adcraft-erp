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


def test_order_item_delete_consistency_migration_adds_reversible_scope_fields():
    versions_dir = Path(__file__).parents[1] / "alembic" / "versions"
    source = next(
        path.read_text(encoding="utf-8")
        for path in versions_dir.glob("*.py")
        if path.name.startswith("oid01_")
    )

    assert 'revision: str = "oid01_item_delete_consistency"' in source
    assert 'down_revision: Union[str, None] = "branding01_system_branding"' in source
    assert '"link_status"' in source
    assert '"removed_at"' in source
    assert '"removed_by"' in source
    assert '"removed_reason"' in source
    assert '"scope_status"' in source
    assert '"scope_closed_at"' in source
    assert '"scope_closed_reason"' in source
    assert 'op.create_foreign_key(' in source
    assert 'op.create_index(' in source
    assert 'op.create_check_constraint(' in source
    assert 'op.drop_column("task_order_item_links", "link_status")' in source
    assert 'for table_name in reversed(_TASK_TABLES):' in source
    assert 'op.drop_column(table_name, "scope_status")' in source


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


def test_unified_payable_ledger_migration_is_additive_and_protected():
    versions_dir = Path(__file__).parents[1] / "alembic" / "versions"
    source = next(
        path.read_text(encoding="utf-8")
        for path in versions_dir.glob("*.py")
        if path.name.startswith("cpa01_")
    )

    assert 'revision: str = "cpa01_payable_ledger"' in source
    assert 'down_revision: Union[str, None] = "cbr01_payment_allocations"' in source
    assert '"payable_payments"' in source
    assert '"payable_amount"' in source
    assert '"ck_payable_payments_source_type"' in source
    assert '"ck_payable_payments_amount_positive"' in source
    assert "不能回滚应付付款流水" in source


def test_expense_payment_method_migration_adds_nullable_column():
    versions_dir = Path(__file__).parents[1] / "alembic" / "versions"
    source = next(
        path.read_text(encoding="utf-8")
        for path in versions_dir.glob("epm01_*.py")
    )

    assert 'revision: str = "epm01_expense_payment_method"' in source
    assert 'down_revision: Union[str, None] = "sup01_supplier_master"' in source
    assert 'op.add_column(' in source
    assert '"expenses"' in source
    assert 'sa.Column("payment_method", sa.String(length=32), nullable=True' in source
    assert 'op.drop_column("expenses", "payment_method")' in source


def test_order_business_date_migration_backfills_orders_and_is_reversible():
    versions_dir = Path(__file__).parents[1] / "alembic" / "versions"
    source = next(
        path.read_text(encoding="utf-8")
        for path in versions_dir.glob("obd01_*.py")
    )

    assert 'revision: str = "obd01_order_business_date"' in source
    assert 'down_revision: Union[str, None] = "epm01_expense_payment_method"' in source
    assert 'op.add_column(' in source
    assert '"business_documents"' in source
    assert 'sa.Column("order_date", sa.Date(), nullable=True' in source
    assert "doc_type = 'order'" in source
    assert "created_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Shanghai'" in source
    assert 'op.create_index(' in source
    assert 'op.create_check_constraint(' in source
    assert 'op.drop_column("business_documents", "order_date")' in source


def test_supplier_master_migration_is_additive_and_backfills_only_exact_unique_names():
    migration_files = list(
        (Path(__file__).resolve().parents[1] / "alembic" / "versions").glob("sup01_*.py")
    )
    assert len(migration_files) == 1
    source = migration_files[0].read_text()
    assert 'sup01_supplier_master' in source
    assert 'cpa01_payable_ledger' in source
    assert '"project_costs"' in source
    assert '"expenses"' in source
    assert 'supplier_id' in source
    assert "btrim(pc.payee_company_name) = btrim(ov.name)" in source
    assert "count(*)" in source
    assert "def downgrade()" in source
