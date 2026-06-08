"""
[INPUT]: 依赖 card_validator, webhook_sender, models, utils
[OUTPUT]: 对外提供 process_confirm, process_authenticate
[POS]: 支付核心编排层，协调验卡→状态变更→webhook 三步流程
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

import asyncio
import logging
from datetime import datetime, UTC

from sqlalchemy.orm import Session

from models import PaymentIntent
from schemas import PaymentIntentConfirm, PaymentIntentAuthenticate
from services.card_validator import validate_card
from services.webhook_sender import send_webhook_event
from utils import generate_id

logger = logging.getLogger(__name__)


def _pi_to_dict(pi: PaymentIntent) -> dict:
    return {
        "id": pi.id,
        "amount": pi.amount,
        "currency": pi.currency,
        "status": pi.status,
        "description": pi.description,
        "client_secret": pi.client_secret,
        "card_last4": pi.card_last4,
        "error_code": pi.error_code,
        "error_message": pi.error_message,
        "created_at": pi.created_at.isoformat(),
        "updated_at": pi.updated_at.isoformat(),
    }


async def process_confirm(
    pi: PaymentIntent,
    body: PaymentIntentConfirm,
    db: Session,
) -> PaymentIntent:
    card = body.payment_method_data.card
    result = validate_card(card)
    now = datetime.now(UTC)

    pi.card_last4 = card.number.replace(" ", "")[-4:]
    pi.updated_at = now

    if not result.valid and result.result == "validation_error":
        pi.status = "payment_failed"
        pi.error_code = result.error_code
        pi.error_message = result.error_message
        db.commit()
        db.refresh(pi)
        return pi

    if result.result == "requires_3ds":
        pi.status = "requires_action"
        db.commit()
        db.refresh(pi)
        return pi

    if result.result == "declined":
        pi.status = "payment_failed"
        pi.error_code = result.error_code
        pi.error_message = result.error_message
        db.commit()
        db.refresh(pi)
        # 异步触发失败 webhook，不阻塞响应
        asyncio.create_task(send_webhook_event(db, _pi_to_dict(pi), "payment_intent.payment_failed"))
        return pi

    # 成功路径（含可选延迟）
    if result.delay > 0:
        await asyncio.sleep(result.delay)

    pi.status = "succeeded"
    pi.error_code = None
    pi.error_message = None
    db.commit()
    db.refresh(pi)
    asyncio.create_task(send_webhook_event(db, _pi_to_dict(pi), "payment_intent.succeeded"))
    return pi


async def process_authenticate(
    pi: PaymentIntent,
    body: PaymentIntentAuthenticate,
    db: Session,
) -> PaymentIntent:
    now = datetime.now(UTC)
    pi.updated_at = now

    if body.action == "success":
        pi.status = "succeeded"
        db.commit()
        db.refresh(pi)
        asyncio.create_task(send_webhook_event(db, _pi_to_dict(pi), "payment_intent.succeeded"))
    else:
        pi.status = "payment_failed"
        pi.error_code = "authentication_required"
        pi.error_message = "3D Secure authentication failed."
        db.commit()
        db.refresh(pi)
        asyncio.create_task(send_webhook_event(db, _pi_to_dict(pi), "payment_intent.payment_failed"))

    return pi
