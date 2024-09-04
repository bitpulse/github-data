from fastapi import APIRouter, HTTPException, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.schemas.subscription import SubscriptionCreate, SubscriptionUpdate, SubscriptionInDB
from app.crud.subscription import create_subscription, get_subscription, update_subscription, delete_subscription
from app.services.paypal import create_billing_plan, create_agreement, execute_agreement
from datetime import datetime

router = APIRouter()

async def get_database() -> AsyncIOMotorDatabase:
    return router.app.mongodb

@router.post("/", response_model=dict)
async def create_subscription_endpoint(
    subscription: SubscriptionCreate,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    # Create subscription in database
    db_subscription = await create_subscription(db, subscription)
    
    # Create PayPal billing plan and agreement
    billing_plan = create_billing_plan()
    agreement = create_agreement(billing_plan, db_subscription)

    # Update subscription with PayPal agreement ID
    await update_subscription(
        db, 
        str(db_subscription.id), 
        SubscriptionUpdate(paypal_agreement_id=agreement.id)
    )

    return {
        "subscription_id": str(db_subscription.id),
        "approval_url": next(link.href for link in agreement.links if link.rel == "approval_url")
    }

@router.post("/{subscription_id}/execute")
async def execute_subscription_agreement(
    subscription_id: str,
    payer_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    subscription = await get_subscription(db, subscription_id)
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")

    agreement = execute_agreement(subscription.paypal_agreement_id, payer_id)

    await update_subscription(
        db,
        subscription_id,
        SubscriptionUpdate(
            next_billing_date=datetime.fromisoformat(agreement.agreement_details.next_billing_date),
            status="active"
        )
    )

    return {"message": "Subscription activated successfully"}

@router.get("/{subscription_id}", response_model=SubscriptionInDB)
async def read_subscription(subscription_id: str, db: AsyncIOMotorDatabase = Depends(get_database)):
    subscription = await get_subscription(db, subscription_id)
    if subscription is None:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return subscription

@router.put("/{subscription_id}", response_model=SubscriptionInDB)
async def update_subscription_endpoint(subscription_id: str, subscription: SubscriptionUpdate, db: AsyncIOMotorDatabase = Depends(get_database)):
    updated_subscription = await update_subscription(db, subscription_id, subscription)
    if updated_subscription is None:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return updated_subscription

@router.delete("/{subscription_id}", response_model=bool)
async def delete_subscription_endpoint(subscription_id: str, db: AsyncIOMotorDatabase = Depends(get_database)):
    deleted = await delete_subscription(db, subscription_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return True

@router.post("/{subscription_id}/execute", response_model=SubscriptionInDB)
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
            SubscriptionUpdate(
                next_billing_date=datetime.now().replace(month=datetime.now().month + 1),
                status="active"
            )
        )
        return updated_subscription
    else:
        raise HTTPException(status_code=400, detail="Failed to execute agreement")
