"""
[INPUT]: 依赖 payment_processor, models, schemas, database.get_db
[OUTPUT]: 对外暴露 /v1/payment_intents 的所有路由
[POS]: routers 层，HTTP 边界到业务逻辑的入口
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

from datetime import datetime, UTC

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models import PaymentIntent
from schemas import (
    PaymentIntentCreate,
    PaymentIntentConfirm,
    PaymentIntentAuthenticate,
    PaymentIntentResponse,
    PaymentIntentListResponse,
    NextAction,
    ErrorResponse,
    StripeError,
)
from services.payment_processor import process_confirm, process_authenticate
from utils import generate_id

router = APIRouter(prefix="/v1/payment_intents", tags=["payment_intents"])


def _stripe_error(code: str, message: str, err_type: str = "card_error") -> HTTPException:
    return HTTPException(
        status_code=400,
        detail={"error": {"code": code, "message": message, "type": err_type}},
    )


def _to_response(pi: PaymentIntent) -> PaymentIntentResponse:
    next_action = None
    if pi.status == "requires_action":
        next_action = NextAction(
            type="use_stripe_sdk",
            redirect_to_url={"url": f"http://localhost:8000/v1/payment_intents/{pi.id}/3ds_challenge"},
        )
    return PaymentIntentResponse(
        id=pi.id,
        amount=pi.amount,
        currency=pi.currency,
        status=pi.status,
        description=pi.description,
        client_secret=pi.client_secret,
        card_last4=pi.card_last4,
        error_code=pi.error_code,
        error_message=pi.error_message,
        next_action=next_action,
        created_at=pi.created_at,
        updated_at=pi.updated_at,
    )


@router.post("", status_code=201, response_model=PaymentIntentResponse)
def create_payment_intent(body: PaymentIntentCreate, db: Session = Depends(get_db)):
    pi_id = generate_id("pi")
    pi = PaymentIntent(
        id=pi_id,
        amount=body.amount,
        currency=body.currency.lower(),
        status="requires_confirmation",
        description=body.description,
        client_secret=f"{pi_id}_secret_{generate_id('sk')}",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db.add(pi)
    db.commit()
    db.refresh(pi)
    return _to_response(pi)


@router.post("/{pi_id}/confirm", response_model=PaymentIntentResponse)
async def confirm_payment_intent(
    pi_id: str,
    body: PaymentIntentConfirm,
    db: Session = Depends(get_db),
):
    pi = db.query(PaymentIntent).filter(PaymentIntent.id == pi_id).first()
    if not pi:
        raise HTTPException(status_code=404, detail={"error": {"code": "resource_missing", "message": "No such payment intent.", "type": "invalid_request_error"}})

    if pi.status != "requires_confirmation":
        raise _stripe_error("invalid_request_error", f"PaymentIntent cannot be confirmed in status '{pi.status}'.", "invalid_request_error")

    pi = await process_confirm(pi, body, db)

    if pi.status == "payment_failed" and pi.error_code:
        # 仍返回对象（和 Stripe 行为一致），客户端检查 status 字段
        pass

    return _to_response(pi)


@router.get("", response_model=PaymentIntentListResponse)
def list_payment_intents(
    limit: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    q = db.query(PaymentIntent)
    if status:
        q = q.filter(PaymentIntent.status == status)
    total = q.count()
    items = q.order_by(PaymentIntent.created_at.desc()).limit(limit).all()
    return PaymentIntentListResponse(
        data=[_to_response(pi) for pi in items],
        has_more=total > limit,
        total_count=total,
    )


@router.get("/{pi_id}", response_model=PaymentIntentResponse)
def get_payment_intent(pi_id: str, db: Session = Depends(get_db)):
    pi = db.query(PaymentIntent).filter(PaymentIntent.id == pi_id).first()
    if not pi:
        raise HTTPException(status_code=404, detail={"error": {"code": "resource_missing", "message": "No such payment intent.", "type": "invalid_request_error"}})
    return _to_response(pi)


@router.post("/{pi_id}/cancel", response_model=PaymentIntentResponse)
def cancel_payment_intent(pi_id: str, db: Session = Depends(get_db)):
    pi = db.query(PaymentIntent).filter(PaymentIntent.id == pi_id).first()
    if not pi:
        raise HTTPException(status_code=404, detail={"error": {"code": "resource_missing", "message": "No such payment intent.", "type": "invalid_request_error"}})

    if pi.status == "succeeded":
        raise _stripe_error("invalid_request_error", "PaymentIntent in status 'succeeded' cannot be canceled.", "invalid_request_error")

    pi.status = "canceled"
    pi.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(pi)
    return _to_response(pi)


@router.post("/{pi_id}/authenticate", response_model=PaymentIntentResponse)
async def authenticate_payment_intent(
    pi_id: str,
    body: PaymentIntentAuthenticate,
    db: Session = Depends(get_db),
):
    pi = db.query(PaymentIntent).filter(PaymentIntent.id == pi_id).first()
    if not pi:
        raise HTTPException(status_code=404, detail={"error": {"code": "resource_missing", "message": "No such payment intent.", "type": "invalid_request_error"}})

    if pi.status != "requires_action":
        raise _stripe_error("invalid_request_error", f"PaymentIntent is not awaiting authentication (status: {pi.status}).", "invalid_request_error")

    pi = await process_authenticate(pi, body, db)
    return _to_response(pi)
