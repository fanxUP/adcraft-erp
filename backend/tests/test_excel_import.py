"""Tests for Excel import utility: parsing, validation, and data formatting."""

from io import BytesIO

import openpyxl
import pytest

from app.utils.excel_import import parse_excel, format_value, parse_number, ExcelImportResult


# --- Helper to create test Excel files ---

def _make_excel(headers: list[str], rows: list[list]) -> bytes:
    """Create an Excel file in memory and return raw bytes."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(headers)
    for row in rows:
        ws.append(row)
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()


class TestParseExcel:
    COLUMN_MAP = {"客户名称": "name", "电话": "phone", "地址": "address"}

    def test_parse_basic(self):
        """Parse a valid Excel file with all columns present."""
        data = _make_excel(
            headers=["客户名称", "电话", "地址"],
            rows=[["张三", "13800138000", "北京市"], ["李四", "13900139000", "上海市"]],
        )
        rows, errors = parse_excel(data, required_columns=["客户名称"], column_map=self.COLUMN_MAP)
        assert errors == []
        assert len(rows) == 2
        assert rows[0]["name"] == "张三"
        assert rows[0]["phone"] == "13800138000"
        assert rows[0]["address"] == "北京市"
        assert rows[1]["name"] == "李四"

    def test_parse_with_extra_columns(self):
        """Extra columns beyond the column map are ignored (not included in output)."""
        data = _make_excel(
            headers=["客户名称", "电话", "地址", "备注", "邮编"],
            rows=[["张三", "13800138000", "北京市", "VIP客户", "100000"]],
        )
        rows, errors = parse_excel(data, required_columns=["客户名称"], column_map=self.COLUMN_MAP)
        assert errors == []
        assert len(rows) == 1
        assert "备注" not in rows[0]
        assert "邮编" not in rows[0]

    def test_missing_required_column(self):
        """Returns error when a required column is missing from the header."""
        data = _make_excel(
            headers=["电话", "地址"],
            rows=[["13800138000", "北京市"]],
        )
        rows, errors = parse_excel(data, required_columns=["客户名称"], column_map=self.COLUMN_MAP)
        assert rows == []
        assert any("客户名称" in e for e in errors)

    def test_multiple_missing_columns(self):
        """Returns errors for all missing required columns, not just the first."""
        data = _make_excel(
            headers=["电话"],
            rows=[],
        )
        rows, errors = parse_excel(
            data,
            required_columns=["客户名称", "电话", "地址"],
            column_map=self.COLUMN_MAP,
        )
        assert rows == []
        assert len(errors) == 2  # 客户名称 and 地址 are missing
        assert all("缺少必填列" in e for e in errors)

    def test_empty_rows_are_skipped(self):
        """Rows where all mapped values are None are excluded."""
        data = _make_excel(
            headers=["客户名称", "电话", "地址"],
            rows=[["张三", "13800138000", "北京市"], [None, None, None], ["李四", None, "上海市"]],
        )
        rows, errors = parse_excel(data, required_columns=["客户名称"], column_map=self.COLUMN_MAP)
        assert errors == []
        assert len(rows) == 2
        assert rows[0]["name"] == "张三"
        assert rows[1]["name"] == "李四"

    def test_header_row_number_included(self):
        """Each parsed row includes an _excel_row key with the 1-based row number."""
        data = _make_excel(
            headers=["客户名称", "电话"],
            rows=[["张三", "13800"], ["李四", "13900"]],
        )
        rows, errors = parse_excel(data, required_columns=["客户名称"], column_map=self.COLUMN_MAP)
        assert errors == []
        assert rows[0]["_excel_row"] == 2  # row 1 is header
        assert rows[1]["_excel_row"] == 3

    def test_no_data_rows(self):
        """A sheet with only headers and no data rows returns empty list."""
        data = _make_excel(headers=["名称"], rows=[])
        rows, errors = parse_excel(data, required_columns=[], column_map={})
        assert rows == []
        assert errors == []


class TestParseExcelEmptyFile:
    def test_empty_workbook(self):
        """An Excel file with no rows returns empty."""
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append([])  # Just an empty header
        buf = BytesIO()
        wb.save(buf)
        buf.seek(0)

        rows, errors = parse_excel(buf.read(), required_columns=[], column_map={})
        assert rows == []
        assert errors == ["Excel 文件为空"]

    def test_corrupted_bytes(self):
        """Random bytes should not crash, should raise a relevant error."""
        with pytest.raises(Exception):
            parse_excel(b"this is not an excel file\x00\x01\x02", required_columns=[], column_map={})


class TestFormatValue:
    def test_none_returns_none(self):
        assert format_value(None) is None

    def test_integer_float(self):
        """A float like 100.0 returns '100' (no decimal)."""
        assert format_value(100.0) == "100"

    def test_decimal_float(self):
        """A float like 99.5 returns '99.5'."""
        assert format_value(99.5) == "99.5"

    def test_string_stripped(self):
        assert format_value("  hello  ") == "hello"

    def test_empty_string(self):
        assert format_value("  ") is None

    def test_zero(self):
        assert format_value(0) == "0"
        assert format_value(0.0) == "0"


class TestParseNumber:
    def test_none_returns_none(self):
        assert parse_number(None) is None

    def test_int_becomes_float(self):
        assert parse_number(100) == 100.0

    def test_float_preserved(self):
        assert parse_number(99.5) == 99.5

    def test_numeric_string(self):
        assert parse_number("123.45") == 123.45

    def test_string_with_commas(self):
        assert parse_number("1,234.56") == 1234.56

    def test_empty_string(self):
        assert parse_number("") is None

    def test_invalid_string(self):
        assert parse_number("abc") is None


class TestExcelImportResult:
    def test_to_dict(self):
        result = ExcelImportResult()
        result.total_rows = 10
        result.succeeded = 7
        result.failed = 3
        result.errors = [{"row": 3, "message": "名称不能为空"}]
        d = result.to_dict()
        assert d["total_rows"] == 10
        assert d["succeeded"] == 7
        assert d["failed"] == 3
        assert len(d["errors"]) == 1
        assert d["errors"][0]["message"] == "名称不能为空"

    def test_default_values(self):
        """A fresh ExcelImportResult has zero counts and no errors."""
        result = ExcelImportResult()
        d = result.to_dict()
        assert d["total_rows"] == 0
        assert d["succeeded"] == 0
        assert d["failed"] == 0
        assert d["errors"] == []
