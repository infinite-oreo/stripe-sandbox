"""
[INPUT]: 依赖 models.WebhookEndpoint, schemas, database.get_db
[OUTPUT]: 对外暴露 /v1/webhook_endpoints 路由
[POS]: routers 层，webhook 端点注册管理
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

import json
from datetime import datetime, UTC

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import WebhookEndpoint
from schemas import WebhookEndpointCreate, WebhookEndpointResponse
from utils import generate_id

router = APIRouter(prefix="/v1/webhook_endpoints", tags=["webhooks"])


def _to_response(ep: WebhookEndpoint) -> WebhookEndpointResponse:
    return WebhookEndpointResponse(
        id=ep.id,
        url=ep.url,
        events=json.loads(ep.events),
        created_at=ep.created_at,
    )


@router.post("", status_code=201, response_model=WebhookEndpointResponse)
def create_webhook_endpoint(body: WebhookEndpointCreate, db: Session = Depends(get_db)):
    ep = WebhookEndpoint(
        id=generate_id("we"),
        url=body.url,
        events=json.dumps(body.events),
        created_at=datetime.now(UTC),
    )
    db.add(ep)
    db.commit()
    db.refresh(ep)
    return _to_response(ep)


@router.get("", response_model=list[WebhookEndpointResponse])
def list_webhook_endpoints(db: Session = Depends(get_db)):
    return [_to_response(ep) for ep in db.query(WebhookEndpoint).all()]


@router.delete("/{endpoint_id}", status_code=204)
def delete_webhook_endpoint(endpoint_id: str, db: Session = Depends(get_db)):
    ep = db.query(WebhookEndpoint).filter(WebhookEndpoint.id == endpoint_id).first()
    if not ep:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "resource_missing", "message": "No such webhook endpoint.", "type": "invalid_request_error"}},
        )
    db.delete(ep)
    db.commit()
