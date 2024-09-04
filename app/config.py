from pydantic import BaseSettings, Field

class Settings(BaseSettings):
    mongodb_url: str = Field(..., env="MONGODB_URL")
    paypal_client_id: str = Field(..., env="PAYPAL_CLIENT_ID")
    paypal_client_secret: str = Field(..., env="PAYPAL_CLIENT_SECRET")
    paypal_mode: str = Field("sandbox", env="PAYPAL_MODE")
    subscription_price: float = Field(19.99, env="SUBSCRIPTION_PRICE")
    subscription_name: str = Field("My Website Subscription", env="SUBSCRIPTION_NAME")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()