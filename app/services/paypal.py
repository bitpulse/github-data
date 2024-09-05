import paypalrestsdk
from paypalrestsdk import BillingPlan, BillingAgreement
from app.config import settings
from app.models.subscription import SubscriptionModel
from datetime import datetime, timedelta
import logging

# Configure PayPal SDK
paypalrestsdk.configure({
    "mode": settings.paypal_mode,
    "client_id": settings.paypal_client_id,
    "client_secret": settings.paypal_client_secret
})

logger = logging.getLogger(__name__)

def create_billing_plan():
    billing_plan = BillingPlan({
        "name": settings.subscription_name,
        "description": f"Monthly subscription for {settings.subscription_name}",
        "type": "INFINITE",
        "payment_definitions": [{
            "name": "Monthly Payments",
            "type": "REGULAR",
            "frequency": "MONTH",
            "frequency_interval": "1",
            "amount": {
                "value": str(settings.subscription_price),
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
    
    if billing_plan.create():
        if billing_plan.activate():
            return billing_plan
        else:
            logger.error(f"Failed to activate billing plan: {billing_plan.error}")
            raise Exception(f"Failed to activate billing plan: {billing_plan.error}")
    else:
        logger.error(f"Failed to create billing plan: {billing_plan.error}")
        raise Exception(f"Failed to create billing plan: {billing_plan.error}")

def create_agreement(billing_plan: BillingPlan, subscription: SubscriptionModel):
    # Set start_date to 5 minutes from now and ensure it's in UTC
    start_date = (datetime.utcnow() + timedelta(minutes=5)).replace(microsecond=0)
    
    billing_agreement = BillingAgreement({
        "name": f"Agreement for {settings.subscription_name}",
        "description": f"Monthly subscription for {settings.subscription_name}",
        "start_date": start_date.isoformat() + "Z",  # Add 'Z' to indicate UTC
        "plan": {
            "id": billing_plan.id
        },
        "payer": {
            "payment_method": "paypal"
        }
    })

    if billing_agreement.create():
        return billing_agreement
    else:
        logger.error(f"Failed to create billing agreement: {billing_agreement.error}")
        raise Exception(f"Failed to create billing agreement: {billing_agreement.error}")

def execute_agreement(agreement_id: str, payer_id: str):
    agreement = BillingAgreement.find(agreement_id)
    if agreement.execute({"payer_id": payer_id}):
        return agreement
    else:
        logger.error(f"Failed to execute agreement: {agreement.error}")
        raise Exception(f"Failed to execute agreement: {agreement.error}")

def cancel_agreement(agreement_id: str):
    agreement = BillingAgreement.find(agreement_id)
    if agreement.cancel({"note": "Cancelling the agreement"}):
        return True
    else:
        logger.error(f"Failed to cancel agreement: {agreement.error}")
        raise Exception(f"Failed to cancel agreement: {agreement.error}")

def get_agreement_details(agreement_id: str):
    try:
        agreement = BillingAgreement.find(agreement_id)
        return agreement
    except Exception as e:
        logger.error(f"Failed to get agreement details: {str(e)}")
        raise Exception(f"Failed to get agreement details: {str(e)}")