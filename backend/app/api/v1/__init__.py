"""API v1 router — aggregates all v1 sub-routers."""

from fastapi import APIRouter
from app.api.v1 import users, agents, demands, orders, auth, admin, wallet, review, semantic, ai_review

router = APIRouter()

router.include_router(auth.router, tags=["认证"])
router.include_router(admin.router, tags=["管理后台"])
router.include_router(users.router, prefix="/users", tags=["用户"])
router.include_router(agents.router, prefix="/agents", tags=["Agent"])
router.include_router(demands.router, prefix="/demands", tags=["需求"])
router.include_router(orders.router, prefix="/orders", tags=["订单"])
router.include_router(wallet.router, prefix="/wallet", tags=["钱包"])
router.include_router(review.router, tags=["评价系统"])
router.include_router(semantic.router, tags=["语义匹配"])
router.include_router(ai_review.router, tags=["AI辅助验收"])
