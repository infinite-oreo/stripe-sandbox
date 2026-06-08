"""
[INPUT]: 依赖 models.Refund/PaymentIntent, schemas, database.get_db
[OUTPUT]: 对外暴露 /v1/refunds 路由（创建、列表、单条查询）
[POS]: routers 层，退款业务入口，依赖 payment_intents 数据
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

from datetime import datetime, UTC

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models import Refund, PaymentIntent
from schemas import RefundCreate, RefundResponse, RefundListResponse
from utils import generate_id

router = APIRouter(prefix="/v1/refunds", tags=["refunds"])


@router.get("", response_model=RefundListResponse)
def list_refunds(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    total = db.query(Refund).count()
    items = db.query(Refund).order_by(Refund.created_at.desc()).limit(limit).all()
    return RefundListResponse(data=items, has_more=total > limit, total_count=total)


@router.post("", status_code=201, response_model=RefundResponse)
def create_refund(body: RefundCreate, db: Session = Depends(get_db)):
    pi = db.query(PaymentIntent).filter(PaymentIntent.id == body.payment_intent).first()
    if not pi:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "resource_missing", "message": "No such payment intent.", "type": "invalid_request_error"}},
        )

    if pi.status != "succeeded":
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "charge_already_refunded", "message": "Payment must be in 'succeeded' status to refund.", "type": "invalid_request_error"}},
        )

    refund_amount = body.amount if body.amount is not None else pi.amount
    if refund_amount > pi.amount:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "invalid_request_error", "message": "Refund amount exceeds payment amount.", "type": "invalid_request_error"}},
        )

    refund = Refund(
        id=generate_id("re"),
        payment_intent_id=pi.id,
        amount=refund_amount,
        status="succeeded",
        created_at=datetime.now(UTC),
    )
    db.add(refund)
    pi.status = "refunded"
    pi.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(refund)
    return refund


@router.get("/{refund_id}", response_model=RefundResponse)
def get_refund(refund_id: str, db: Session = Depends(get_db)):
    refund = db.query(Refund).filter(Refund.id == refund_id).first()
    if not refund:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "resource_missing", "message": "No such refund.", "type": "invalid_request_error"}},
        )
    return refund
