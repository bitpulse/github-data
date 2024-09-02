from app.models.server import ServerModel
from app.schemas.server import ServerCreate, ServerUpdate
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

async def create_server(db: AsyncIOMotorDatabase, server: ServerCreate) -> ServerModel:
    server_dict = server.dict()
    result = await db.servers.insert_one(server_dict)
    return ServerModel(_id=result.inserted_id, **server_dict)

async def get_server(db: AsyncIOMotorDatabase, server_id: str) -> ServerModel | None:
    server = await db.servers.find_one({"_id": ObjectId(server_id)})
    if server:
        return ServerModel(**server)

async def update_server(db: AsyncIOMotorDatabase, server_id: str, server: ServerUpdate) -> ServerModel | None:
    server_dict = {k: v for k, v in server.dict().items() if v is not None}
    if server_dict:
        await db.servers.update_one({"_id": ObjectId(server_id)}, {"$set": server_dict})
    return await get_server(db, server_id)

async def delete_server(db: AsyncIOMotorDatabase, server_id: str) -> bool:
    result = await db.servers.delete_one({"_id": ObjectId(server_id)})
    return result.deleted_count > 0