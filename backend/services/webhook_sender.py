"""
[INPUT]: 依赖 httpx AsyncClient，依赖 WebhookEndpoint/WebhookDelivery models
[OUTPUT]: 对外提供 send_webhook_event(db, payment_intent, event_type)
[POS]: 异步事件投递层，payment_processor 调用后触发
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

import json
import time
import asyncio
import logging
from datetime import datetime, UTC

import httpx
from sqlalchemy.orm import Session

from models import WebhookEndpoint, WebhookDelivery
from schemas import PaymentIntentResponse, WebhookEvent
from utils import generate_id

logger = logging.getLogger(__name__)


def _build_event(event_type: str, pi_data: dict) -> dict:
    return {
        "id": generate_id("evt"),
        "type": event_type,
        "created": int(time.time()),
        "data": {"object": pi_data},
    }


async def _deliver(client: httpx.AsyncClient, url: str, payload: dict) -> tuple[bool, int | None]:
    headers = {
        "Content-Type": "application/json",
        "Stripe-Signature": f"mock_signature_{generate_id('sig')}",
    }
    try:
        resp = await client.post(url, json=payload, headers=headers, timeout=10.0)
        return resp.status_code < 400, resp.status_code
    except Exception as exc:
        logger.warning("Webhook delivery failed: %s", exc)
        return False, None


async def send_webhook_event(db: Session, pi_dict: dict, event_type: str) -> None:
    endpoints = db.query(WebhookEndpoint).all()
    if not endpoints:
        return

    event_payload = _build_event(event_type, pi_dict)
    payload_str = json.dumps(event_payload)

    async with httpx.AsyncClient() as client:
        for endpoint in endpoints:
            subscribed = json.loads(endpoint.events)
            if event_type not in subscribed:
                continue

            success, status = await _deliver(client, endpoint.url, event_payload)

            # 首次失败重试一次
            if not success:
                await asyncio.sleep(2)
                success, status = await _deliver(client, endpoint.url, event_payload)

            delivery = WebhookDelivery(
                id=generate_id("wdel"),
                endpoint_id=endpoint.id,
                event_type=event_type,
                payload=payload_str,
                response_status=status,
                success=success,
                attempted_at=datetime.now(UTC),
            )
            db.add(delivery)

    db.commit()
