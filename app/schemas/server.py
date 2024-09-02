from pydantic import BaseModel

class ServerCreate(BaseModel):
    name: str
    price: float

class ServerUpdate(BaseModel):
    name: str | None = None
    price: float | None = None

class ServerInDB(ServerCreate):
    id: str