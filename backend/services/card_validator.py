"""
[INPUT]: 依赖 CardData schema
[OUTPUT]: 对外提供 validate_card(card) -> CardValidationResult
[POS]: services 层核心，封装所有卡号场景判断和 Luhn 校验
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

from dataclasses import dataclass
from datetime import datetime, UTC

from schemas import CardData

# 测试卡号场景表 — 与 Stripe 测试卡对齐
_CARD_SCENARIOS: dict[str, dict] = {
    "4242424242424242": {"result": "success"},
    "4000000000000002": {"result": "declined", "code": "card_declined", "message": "Your card was declined."},
    "4000000000009995": {"result": "declined", "code": "insufficient_funds", "message": "Your card has insufficient funds."},
    "4000000000000069": {"result": "declined", "code": "expired_card", "message": "Your card has expired."},
    "4000000000000127": {"result": "declined", "code": "incorrect_cvc", "message": "Your card's security code is incorrect."},
    "4000002500003155": {"result": "requires_3ds"},
    "4000000000000077": {"result": "success", "delay": 3},
}


@dataclass
class CardValidationResult:
    valid: bool
    result: str            # success | declined | requires_3ds | validation_error
    error_code: str | None = None
    error_message: str | None = None
    delay: int = 0         # 模拟延迟秒数


def _luhn_check(number: str) -> bool:
    digits = [int(d) for d in reversed(number) if d.isdigit()]
    total = sum(
        d if i % 2 == 0 else (d * 2 - 9 if d * 2 > 9 else d * 2)
        for i, d in enumerate(digits)
    )
    return total % 10 == 0


def validate_card(card: CardData) -> CardValidationResult:
    number = card.number.replace(" ", "")

    # 基础格式校验
    if not number.isdigit() or len(number) < 13:
        return CardValidationResult(False, "validation_error", "invalid_number", "Your card number is invalid.")

    if not _luhn_check(number):
        return CardValidationResult(False, "validation_error", "invalid_number", "Your card number is invalid.")

    if not (1 <= card.exp_month <= 12):
        return CardValidationResult(False, "validation_error", "invalid_expiry_month", "Your card's expiration month is invalid.")

    current_year = datetime.now(UTC).year
    if card.exp_year < current_year:
        return CardValidationResult(False, "validation_error", "expired_card", "Your card has expired.")

    if not card.cvc.isdigit() or len(card.cvc) != 3:
        return CardValidationResult(False, "validation_error", "incorrect_cvc", "Your card's security code is invalid.")

    # 场景路由
    scenario = _CARD_SCENARIOS.get(number)
    if scenario is None:
        return CardValidationResult(False, "declined", "card_declined", "Your card was declined.")

    match scenario["result"]:
        case "success":
            return CardValidationResult(True, "success", delay=scenario.get("delay", 0))
        case "requires_3ds":
            return CardValidationResult(True, "requires_3ds")
        case "declined":
            return CardValidationResult(False, "declined", scenario["code"], scenario["message"])
        case _:
            return CardValidationResult(False, "declined", "card_declined", "Your card was declined.")
