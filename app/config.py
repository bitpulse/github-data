from pydantic import BaseSettings

class Settings(BaseSettings):
    mongodb_url: str
    paypal_client_id: str
    paypal_client_secret: str
    paypal_mode: str = "sandbox"
    subscription_price: float
    subscription_name: str

    class Config:
        env_file = ".env"

settings = Settings()
