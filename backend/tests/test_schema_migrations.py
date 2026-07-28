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
