"""
[INPUT]: 依赖 FastAPI TestClient, SQLAlchemy in-memory DB
[OUTPUT]: 10 个支付意图+退款场景的自动化测试
[POS]: tests 层，覆盖核心业务路径和边界条件
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

import json
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, get_db
from main import app

# StaticPool 保证所有连接复用同一内存库，测试间隔离靠 drop_all/create_all
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


# ── 工具函数 ───────────────────────────────────────────────────────────────────

def create_pi(client, amount=1000, currency="usd"):
    return client.post("/v1/payment_intents", json={"amount": amount, "currency": currency})


def confirm_pi(client, pi_id, card_number="4242424242424242"):
    return client.post(f"/v1/payment_intents/{pi_id}/confirm", json={
        "payment_method_data": {
            "type": "card",
            "card": {"number": card_number, "exp_month": 12, "exp_year": 2030, "cvc": "123"},
        }
    })


# ── 测试用例 ───────────────────────────────────────────────────────────────────

def test_create_payment_intent(client):
    """1. 创建 PaymentIntent 返回正确结构和初始状态"""
    resp = create_pi(client)
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "requires_confirmation"
    assert data["amount"] == 1000
    assert data["currency"] == "usd"
    assert data["id"].startswith("pi_mock_")
    assert "client_secret" in data


def test_confirm_success_card(client):
    """2. 成功卡确认后状态变为 succeeded"""
    pi_id = create_pi(client).json()["id"]
    resp = confirm_pi(client, pi_id, "4242424242424242")
    assert resp.status_code == 200
    assert resp.json()["status"] == "succeeded"


def test_confirm_declined_card(client):
    """3. 拒绝卡确认后状态变为 payment_failed 并附带错误"""
    pi_id = create_pi(client).json()["id"]
    resp = confirm_pi(client, pi_id, "4000000000000002")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "payment_failed"
    assert data["error_code"] == "card_declined"


def test_confirm_3ds_card(client):
    """4. 3DS 卡确认后状态变为 requires_action"""
    pi_id = create_pi(client).json()["id"]
    resp = confirm_pi(client, pi_id, "4000002500003155")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "requires_action"
    assert data["next_action"] is not None


def test_authenticate_3ds_success(client):
    """5. 完成 3DS 认证(success) → 状态变为 succeeded"""
    pi_id = create_pi(client).json()["id"]
    confirm_pi(client, pi_id, "4000002500003155")
    resp = client.post(f"/v1/payment_intents/{pi_id}/authenticate", json={"action": "success"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "succeeded"


def test_authenticate_3ds_fail(client):
    """5b. 完成 3DS 认证(fail) → 状态变为 payment_failed"""
    pi_id = create_pi(client).json()["id"]
    confirm_pi(client, pi_id, "4000002500003155")
    resp = client.post(f"/v1/payment_intents/{pi_id}/authenticate", json={"action": "fail"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "payment_failed"


def test_create_refund(client):
    """6. 退款成功返回 Refund 对象"""
    pi_id = create_pi(client).json()["id"]
    confirm_pi(client, pi_id)
    resp = client.post("/v1/refunds", json={"payment_intent": pi_id})
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "succeeded"
    assert data["amount"] == 1000
    assert data["id"].startswith("re_mock_")


def test_partial_refund(client):
    """7. 部分退款金额正确记录"""
    pi_id = create_pi(client).json()["id"]
    confirm_pi(client, pi_id)
    resp = client.post("/v1/refunds", json={"payment_intent": pi_id, "amount": 500})
    assert resp.status_code == 201
    assert resp.json()["amount"] == 500


def test_refund_non_succeeded_payment(client):
    """8. 对未成功支付发起退款返回 400"""
    pi_id = create_pi(client).json()["id"]
    # 状态仍为 requires_confirmation，未确认
    resp = client.post("/v1/refunds", json={"payment_intent": pi_id})
    assert resp.status_code == 400


def test_invalid_luhn_card(client):
    """9. Luhn 校验失败的卡号返回 payment_failed"""
    pi_id = create_pi(client).json()["id"]
    resp = confirm_pi(client, pi_id, "4242424242424241")  # 末位改错
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "payment_failed"
    assert data["error_code"] == "invalid_number"


def test_insufficient_funds_card(client):
    """10. 余额不足卡返回对应错误码"""
    pi_id = create_pi(client).json()["id"]
    resp = confirm_pi(client, pi_id, "4000000000009995")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "payment_failed"
    assert data["error_code"] == "insufficient_funds"


def test_get_payment_intent(client):
    """GET 单个 PaymentIntent 返回正确数据"""
    pi_id = create_pi(client).json()["id"]
    resp = client.get(f"/v1/payment_intents/{pi_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == pi_id


def test_list_payment_intents(client):
    """LIST 支持 limit 和 status 过滤"""
    create_pi(client)
    pi_id2 = create_pi(client).json()["id"]
    confirm_pi(client, pi_id2)

    all_resp = client.get("/v1/payment_intents")
    assert all_resp.json()["total_count"] == 2

    succeeded_resp = client.get("/v1/payment_intents?status=succeeded")
    assert succeeded_resp.json()["total_count"] == 1


def test_cancel_payment_intent(client):
    """取消未成功的 PaymentIntent"""
    pi_id = create_pi(client).json()["id"]
    resp = client.post(f"/v1/payment_intents/{pi_id}/cancel")
    assert resp.status_code == 200
    assert resp.json()["status"] == "canceled"


def test_cancel_succeeded_payment_intent(client):
    """取消已成功的 PaymentIntent 返回 400"""
    pi_id = create_pi(client).json()["id"]
    confirm_pi(client, pi_id)
    resp = client.post(f"/v1/payment_intents/{pi_id}/cancel")
    assert resp.status_code == 400
