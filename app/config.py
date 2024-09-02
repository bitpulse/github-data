from pydantic import BaseSettings

class Settings(BaseSettings):
    mongodb_url: str
    paypal_client_id: str
    paypal_client_secret: str
    paypal_mode: str = "sandbox"

    class Config:
        env_file = ".env"

settings = Settings()