from app.models.subscription import SubscriptionModel
from app.schemas.subscription import SubscriptionCreate, SubscriptionUpdate
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from datetime import datetime, timedelta

async def create_subscription(db: AsyncIOMotorDatabase, subscription: SubscriptionCreate) -> SubscriptionModel:
    start_date = datetime.now()
    next_billing_date = start_date.replace(month=start_date.month + 1)
    if next_billing_date.month == 1:
        next_billing_date = next_billing_date.replace(year=next_billing_date.year + 1)

    subscription_dict = subscription.dict()
    subscription_dict.update({
        "start_date": start_date,
        "next_billing_date": next_billing_date,
        "paypal_agreement_id": "",
        "status": "pending"
    })
    result = await db.subscriptions.insert_one(subscription_dict)
    return SubscriptionModel(_id=result.inserted_id, **subscription_dict)

async def get_subscription(db: AsyncIOMotorDatabase, subscription_id: str) -> SubscriptionModel | None:
    subscription = await db.subscriptions.find_one({"_id": ObjectId(subscription_id)})
    if subscription:
        return SubscriptionModel(**subscription)

async def update_subscription(db: AsyncIOMotorDatabase, subscription_id: str, subscription: SubscriptionUpdate) -> SubscriptionModel | None:
    subscription_dict = {k: v for k, v in subscription.dict().items() if v is not None}
    if subscription_dict:
        await db.subscriptions.update_one({"_id": ObjectId(subscription_id)}, {"$set": subscription_dict})
    return await get_subscription(db, subscription_id)

async def delete_subscription(db: AsyncIOMotorDatabase, subscription_id: str) -> bool:
    result = await db.subscriptions.delete_one({"_id": ObjectId(subscription_id)})
    return result.deleted_count > 0
