"""
[INPUT]: 依赖 secrets, string 标准库
[OUTPUT]: 对外提供 generate_id(prefix) -> str
[POS]: 全局工具，ID 生成的唯一来源，避免各模块重复实现
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

import secrets
import string

_ALPHABET = string.ascii_lowercase + string.digits


def generate_id(prefix: str, length: int = 12) -> str:
    suffix = "".join(secrets.choice(_ALPHABET) for _ in range(length))
    return f"{prefix}_mock_{suffix}"
