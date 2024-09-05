from fastapi import FastAPI
from app.api.routes import router
from app.config import settings

app = FastAPI()

app.include_router(router)

@app.on_event("startup")
async def startup_db_client():
    # We don't need to do anything here now, as we're creating the client in the dependency
    pass

@app.on_event("shutdown")
async def shutdown_db_client():
    # We don't need to do anything here now, as we're creating the client in the dependency
    pass