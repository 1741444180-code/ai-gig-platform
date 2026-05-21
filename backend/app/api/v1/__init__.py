from fastapi import APIRouter

router = APIRouter()

# 延迟导入子路由，避免循环依赖
from app.api.v1 import auth, requirements, agents, orders, admin


router.include_router(auth.router, prefix="/auth", tags=["认证"])
router.include_router(requirements.router, prefix="/requirements", tags=["需求"])
router.include_router(agents.router, prefix="/agents", tags=["Agent"])
router.include_router(orders.router, prefix="/orders", tags=["订单"])
router.include_router(admin.router, prefix="/admin", tags=["管理后台"])
