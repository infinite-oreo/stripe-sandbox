"""
[INPUT]: 依赖 database.Base，依赖 sqlalchemy 列类型
[OUTPUT]: 对外提供 PaymentIntent, Refund, WebhookEndpoint, WebhookDelivery ORM 模型
[POS]: 数据层核心，定义四张表的结构和关系
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

from datetime import datetime, UTC
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import mapped_column, Mapped, relationship

from database import Base


class PaymentIntent(Base):
    __tablename__ = "payment_intents"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    client_secret: Mapped[str] = mapped_column(String, nullable=False)
    card_last4: Mapped[str | None] = mapped_column(String(4), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    refunds: Mapped[list["Refund"]] = relationship("Refund", back_populates="payment_intent_rel")


class Refund(Base):
    __tablename__ = "refunds"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    payment_intent_id: Mapped[str] = mapped_column(String, ForeignKey("payment_intents.id"))
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    payment_intent_rel: Mapped["PaymentIntent"] = relationship("PaymentIntent", back_populates="refunds")


class WebhookEndpoint(Base):
    __tablename__ = "webhook_endpoints"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    url: Mapped[str] = mapped_column(String, nullable=False)
    events: Mapped[str] = mapped_column(String, nullable=False)  # JSON 数组序列化存储
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    endpoint_id: Mapped[str] = mapped_column(String, nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    payload: Mapped[str] = mapped_column(String, nullable=False)  # JSON 序列化
    response_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    attempted_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
