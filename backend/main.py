"""
[INPUT]: 依赖 FastAPI, database.engine/Base, 三个 router
[OUTPUT]: 对外提供 ASGI app 实例（uvicorn 入口）
[POS]: 应用根节点，负责启动初始化、中间件注册、路由挂载
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import engine, Base
from routers import payment_intents, refunds, webhooks

# 启动时自动建表
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Stripe Mock Payment Server",
    description="Stripe API 兼容的本地 mock 服务，无需真实凭证即可测试支付流程",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(payment_intents.router)
app.include_router(refunds.router)
app.include_router(webhooks.router)


@app.get("/health")
def health():
    return {"status": "ok"}
