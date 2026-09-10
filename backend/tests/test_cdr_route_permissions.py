"""Ensure price-producing CDR helper routes are not login-only."""

from pathlib import Path


def test_cdr_routes_do_not_leave_login_only_dependencies():
    source = (Path(__file__).parents[1] / "app" / "api" / "cdr_quotes.py").read_text()

    # A login-only CDR endpoint can return calculated prices or pricing rules to
    # an execution user. Every CDR route must therefore use a CDR permission.
    assert "current_user: User = Depends(get_current_user)" not in source
