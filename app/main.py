from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient
from app.api.routes import router
from app.config import settings

app = FastAPI()

@app.on_event("startup")
async def startup_db_client():
    app.mongodb_client = AsyncIOMotorClient(settings.mongodb_url)
    app.mongodb = app.mongodb_client.subscription_db

@app.on_event("shutdown")
async def shutdown_db_client():
    app.mongodb_client.close()

app.include_router(router)
