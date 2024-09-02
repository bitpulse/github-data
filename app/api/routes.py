from fastapi import APIRouter
from app.api.endpoints import subscription, server

router = APIRouter()
router.include_router(subscription.router, prefix="/subscriptions", tags=["subscriptions"])
router.include_router(server.router, prefix="/servers", tags=["servers"])