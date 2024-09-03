from fastapi import APIRouter
from app.api.endpoints import subscription

router = APIRouter()
router.include_router(subscription.router, prefix="/subscriptions", tags=["subscriptions"])