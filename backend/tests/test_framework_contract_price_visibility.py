"""Framework-contract reads must require the contract module permission."""

from pathlib import Path


def test_framework_contract_routes_do_not_leave_login_only_dependencies():
    source = (Path(__file__).parents[1] / "app" / "api" / "framework_contracts.py").read_text()

    # Framework projects expose project_amount and order references, so a
    # bearer token alone must never be sufficient to call this router.
    assert "current_user: User = Depends(get_current_user)" not in source
