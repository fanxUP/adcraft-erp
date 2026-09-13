"""Regression tests for employee date input normalization."""

from datetime import date

from app.schemas.employee import EmployeeCreate, EmployeeUpdate


def test_employee_create_accepts_blank_optional_dates():
    employee = EmployeeCreate(
        name="测试员工",
        birth_date="",
        hire_date="",
        resignation_date="",
    )

    assert employee.birth_date is None
    assert employee.hire_date is None
    assert employee.resignation_date is None


def test_employee_update_keeps_valid_dates_and_normalizes_blank_dates():
    employee = EmployeeUpdate(
        birth_date="1990-01-01",
        hire_date="",
        resignation_date=None,
    )

    assert employee.birth_date == date(1990, 1, 1)
    assert employee.hire_date is None
    assert employee.resignation_date is None
