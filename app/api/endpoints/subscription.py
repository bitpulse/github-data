from fastapi import APIRouter, HTTPException, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.schemas.subscription import SubscriptionCreate, SubscriptionUpdate, SubscriptionInDB
from app.crud.subscription import create_subscription, get_subscription, update_subscription, delete_subscription
from app.crud.server import get_server
from app.services.paypal import create_billing_plan, create_agreement
from datetime import datetime

router = APIRouter()

async def get_database() -> AsyncIOMotorDatabase:
    return router.app.mongodb

@router.post("/subscriptions/", response_model=SubscriptionInDB)
async def create_subscription_endpoint(
    subscription: SubscriptionCreate,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    # Create subscription in database
    db_subscription = await create_subscription(db, subscription)
    
    # Get server details
    server = await get_server(db, subscription.server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    # Calculate prorated amount
    days_in_month = (db_subscription.next_billing_date - db_subscription.start_date).days
    prorated_amount = (server.price / days_in_month) * (days_in_month - db_subscription.start_date.day + 1)

    # Create PayPal billing plan and agreement
    billing_plan = create_billing_plan(server)
    agreement = create_agreement(billing_plan, db_subscription, prorated_amount)

    # Update subscription with PayPal agreement ID
    updated_subscription = await update_subscription(
        db, 
        str(db_subscription.id), 
        SubscriptionUpdate(paypal_agreement_id=agreement.id)
    )

    return {**updated_subscription.dict(), "approval_url": agreement.links[0].href}

@router.get("/subscriptions/{subscription_id}", response_model=SubscriptionInDB)
async def read_subscription(subscription_id: str, db: AsyncIOMotorDatabase = Depends(get_database)):
    subscription = await get_subscription(db, subscription_id)
    if subscription is None:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return subscription

@router.put("/subscriptions/{subscription_id}", response_model=SubscriptionInDB)
async def update_subscription_endpoint(subscription_id: str, subscription: SubscriptionUpdate, db: AsyncIOMotorDatabase = Depends(get_database)):
    updated_subscription = await update_subscription(db, subscription_id, subscription)
    if updated_subscription is None:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return updated_subscription

@router.delete("/subscriptions/{subscription_id}", response_model=bool)
async def delete_subscription_endpoint(subscription_id: str, db: AsyncIOMotorDatabase = Depends(get_database)):
    deleted = await delete_subscription(db, subscription_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return True

@router.post("/subscriptions/{subscription_id}/execute", response_model=SubscriptionInDB)
async def execute_agreement(subscription_id: str, token: str, db: AsyncIOMotorDatabase = Depends(get_database)):
    subscription = await get_subscription(db, subscription_id)
    if subscription is None:
        raise HTTPException(status_code=404, detail="Subscription not found")

    # Execute the PayPal agreement
    agreement = paypalrestsdk.BillingAgreement.find(subscription.paypal_agreement_id)
    if agreement.execute({"token": token}):
        # Update the subscription status in the database
        updated_subscription = await update_subscription(
            db,
            subscription_id,
            SubscriptionUpdate(next_billing_date=datetime.now().replace(month=datetime.now().month + 1))
        )
        return updated_subscription
    else:
        raise HTTPException(status_code=400, detail="Failed to execute agreement")
