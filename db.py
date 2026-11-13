from motor.motor_asyncio import AsyncIOMotorClient
import os

_client=None
_db=None

async def init_db():
    global _client, _db
    uri=os.getenv("MONGODB_URI")
    _client=AsyncIOMotorClient(uri)
    _db=_client["research-agent"]

    await _db.reports.create_index("query")
    print("Database connection established.")


async def close_db():
    if _client:
        _client.close()
        print("Database connection closed.")



def get_db():
    if _db is None:
        raise Exception("Database not initialized. Call init_db() first.")
    return _db