from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class SubscriptionCreate(BaseModel):
    user_id: str

class SubscriptionUpdate(BaseModel):
    next_billing_date: Optional[datetime] = None
    paypal_agreement_id: Optional[str] = None
    status: Optional[str] = None

class SubscriptionInDB(SubscriptionCreate):
    id: str
    start_date: datetime
    next_billing_date: datetime
    paypal_agreement_id: str
    status: str