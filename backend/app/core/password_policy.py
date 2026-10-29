"""Password length rules shared by API schemas and service-level callers."""

MIN_PASSWORD_LENGTH = 6
MAX_PASSWORD_LENGTH = 128
MAX_PASSWORD_BYTES = 72


def validate_new_password(password: str) -> None:
    """Reject unsafe password values without ever echoing the value."""
    if not isinstance(password, str) or not password:
        raise ValueError("新密码不能为空")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"新密码至少 {MIN_PASSWORD_LENGTH} 位")
    if len(password) > MAX_PASSWORD_LENGTH:
        raise ValueError(f"新密码不能超过 {MAX_PASSWORD_LENGTH} 位")
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise ValueError("新密码不能超过 72 个 UTF-8 字节（汉字通常占 3 字节）")
