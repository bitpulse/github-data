from pydantic import BaseModel, Field
from bson import ObjectId
from datetime import datetime
from .server import PyObjectId

class SubscriptionModel(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: str
    server_id: PyObjectId
    start_date: datetime
    next_billing_date: datetime
    paypal_agreement_id: str

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}