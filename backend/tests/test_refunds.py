"""
[INPUT]: 依赖 TestClient, 内存数据库
[OUTPUT]: Refund 路由独立测试（超额退款、查询等）
[POS]: tests 层，补充 test_payment_intents 中退款的边界覆盖
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, get_db
from main import app

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(reset_db):
    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _make_succeeded_pi(client):
    pi_id = client.post("/v1/payment_intents", json={"amount": 2000}).json()["id"]
    client.post(f"/v1/payment_intents/{pi_id}/confirm", json={
        "payment_method_data": {
            "type": "card",
            "card": {"number": "4242424242424242", "exp_month": 12, "exp_year": 2030, "cvc": "123"},
        }
    })
    return pi_id


def test_refund_exceeds_amount(client):
    """退款超出原始金额返回 400"""
    pi_id = _make_succeeded_pi(client)
    resp = client.post("/v1/refunds", json={"payment_intent": pi_id, "amount": 9999})
    assert resp.status_code == 400


def test_refund_not_found_pi(client):
    """对不存在的 PI 退款返回 404"""
    resp = client.post("/v1/refunds", json={"payment_intent": "pi_mock_nonexistent"})
    assert resp.status_code == 404


def test_get_refund(client):
    """查询单个 Refund 返回正确数据"""
    pi_id = _make_succeeded_pi(client)
    refund_id = client.post("/v1/refunds", json={"payment_intent": pi_id}).json()["id"]
    resp = client.get(f"/v1/refunds/{refund_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == refund_id


def test_get_refund_not_found(client):
    """查询不存在的 Refund 返回 404"""
    resp = client.get("/v1/refunds/re_mock_nonexistent")
    assert resp.status_code == 404


def test_webhook_endpoint_crud(client):
    """Webhook 端点注册→列举→删除完整流程"""
    # 注册
    create_resp = client.post("/v1/webhook_endpoints", json={
        "url": "http://localhost:9000/webhook",
        "events": ["payment_intent.succeeded"],
    })
    assert create_resp.status_code == 201
    ep_id = create_resp.json()["id"]

    # 列举
    list_resp = client.get("/v1/webhook_endpoints")
    assert len(list_resp.json()) == 1

    # 删除
    del_resp = client.delete(f"/v1/webhook_endpoints/{ep_id}")
    assert del_resp.status_code == 204

    # 确认删除
    assert len(client.get("/v1/webhook_endpoints").json()) == 0
