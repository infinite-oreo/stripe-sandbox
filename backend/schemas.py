"""
[INPUT]: 依赖 pydantic BaseModel，依赖业务常量
[OUTPUT]: 对外提供所有 Request/Response Pydantic schema
[POS]: API 边界契约层，连接 HTTP 报文与 ORM 模型的桥梁
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, field_validator


# ── PaymentIntent ──────────────────────────────────────────────────────────────

class PaymentIntentCreate(BaseModel):
    amount: int
    currency: str = "usd"
    payment_method: str = "card"
    description: str | None = None

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("amount must be positive")
        return v


class CardData(BaseModel):
    number: str
    exp_month: int
    exp_year: int
    cvc: str


class PaymentMethodData(BaseModel):
    type: str = "card"
    card: CardData


class PaymentIntentConfirm(BaseModel):
    payment_method_data: PaymentMethodData


class PaymentIntentAuthenticate(BaseModel):
    action: str  # "success" | "fail"


class NextAction(BaseModel):
    type: str
    redirect_to_url: dict[str, str] | None = None


class StripeError(BaseModel):
    code: str
    message: str
    type: str


class ErrorResponse(BaseModel):
    error: StripeError


class PaymentIntentResponse(BaseModel):
    id: str
    amount: int
    currency: str
    status: str
    description: str | None
    client_secret: str
    card_last4: str | None
    error_code: str | None
    error_message: str | None
    next_action: NextAction | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PaymentIntentListResponse(BaseModel):
    data: list[PaymentIntentResponse]
    has_more: bool
    total_count: int


# ── Refund ─────────────────────────────────────────────────────────────────────

class RefundCreate(BaseModel):
    payment_intent: str
    amount: int | None = None


class RefundResponse(BaseModel):
    id: str
    payment_intent_id: str
    amount: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class RefundListResponse(BaseModel):
    data: list[RefundResponse]
    has_more: bool
    total_count: int


# ── Webhook ────────────────────────────────────────────────────────────────────

class WebhookEndpointCreate(BaseModel):
    url: str
    events: list[str]


class WebhookEndpointResponse(BaseModel):
    id: str
    url: str
    events: list[str]
    created_at: datetime

    class Config:
        from_attributes = True


class WebhookEvent(BaseModel):
    id: str
    type: str
    created: int
    data: dict[str, Any]
