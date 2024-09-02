from pydantic import BaseModel
from datetime import datetime

class SubscriptionCreate(BaseModel):
    user_id: str
    server_id: str

class SubscriptionUpdate(BaseModel):
    next_billing_date: datetime | None = None
    paypal_agreement_id: str | None = None

class SubscriptionInDB(SubscriptionCreate):
    id: str
    start_date: datetime
    next_billing_date: datetime
    paypal_agreement_id: str