import paypalrestsdk
from paypalrestsdk import BillingPlan, BillingAgreement
from app.config import settings
from app.models.server import ServerModel
from app.models.subscription import SubscriptionModel
from datetime import datetime, timedelta

paypalrestsdk.configure({
    "mode": settings.paypal_mode,
    "client_id": settings.paypal_client_id,
    "client_secret": settings.paypal_client_secret
})

def create_billing_plan(server: ServerModel):
    billing_plan = BillingPlan({
        "name": f"Plan for {server.name}",
        "description": f"Monthly subscription for {server.name}",
        "type": "INFINITE",
        "payment_definitions": [{
            "name": "Monthly Payments",
            "type": "REGULAR",
            "frequency": "MONTH",
            "frequency_interval": "1",
            "amount": {
                "value": str(server.price),
                "currency": "USD"
            },
            "cycles": "0",
        }],
        "merchant_preferences": {
            "setup_fee": {
                "value": "0",
                "currency": "USD"
            },
            "return_url": "http://example.com/success",
            "cancel_url": "http://example.com/cancel",
            "auto_bill_amount": "YES",
            "initial_fail_amount_action": "CONTINUE",
            "max_fail_attempts": "3"
        }
    })
    
    if billing_plan.create() and billing_plan.activate():
        return billing_plan
    else:
        raise Exception("Failed to create billing plan")

def create_agreement(billing_plan: BillingPlan, subscription: SubscriptionModel, prorated_amount: float):
    start_date = datetime.now() + timedelta(minutes=5)
    billing_agreement = BillingAgreement({
        "name": f"Agreement for {billing_plan.name}",
        "description": f"Monthly subscription for {billing_plan.description}",
        "start_date": start_date.isoformat(),
        "plan": {
            "id": billing_plan.id
        },
        "payer": {
            "payment_method": "paypal"
        },
        "override_merchant_preferences": {
            "setup_fee": {
                "value": str(prorated_amount),
                "currency": "USD"
            }
        }
    })

    if billing_agreement.create():
        return billing_agreement
    else:
        raise Exception("Failed to create billing agreement")
