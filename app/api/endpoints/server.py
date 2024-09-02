from fastapi import APIRouter, HTTPException, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.schemas.server import ServerCreate, ServerUpdate, ServerInDB
from app.crud.server import create_server, get_server, update_server, delete_server

router = APIRouter()

async def get_database() -> AsyncIOMotorDatabase:
    return router.app.mongodb

@router.post("/servers/", response_model=ServerInDB)
async def create_server_endpoint(server: ServerCreate, db: AsyncIOMotorDatabase = Depends(get_database)):
    return await create_server(db, server)

@router.get("/servers/{server_id}", response_model=ServerInDB)
async def read_server(server_id: str, db: AsyncIOMotorDatabase = Depends(get_database)):
    server = await get_server(db, server_id)
    if server is None:
        raise HTTPException(status_code=404, detail="Server not found")
    return server

@router.put("/servers/{server_id}", response_model=ServerInDB)
async def update_server_endpoint(server_id: str, server: ServerUpdate, db: AsyncIOMotorDatabase = Depends(get_database)):
    updated_server = await update_server(db, server_id, server)
    if updated_server is None:
        raise HTTPException(status_code=404, detail="Server not found")
    return updated_server

@router.delete("/servers/{server_id}", response_model=bool)
async def delete_server_endpoint(server_id: str, db: AsyncIOMotorDatabase = Depends(get_database)):
    deleted = await delete_server(db, server_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Server not found")
    return True