'''
This file contains the code to connect to the MongoDB database and get the next sequence value for the _id field of the documents.
'''
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    MONGODB_URL: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "cul_db"

settings = Settings()

client = AsyncIOMotorClient(settings.MONGODB_URL)
database = client[settings.DATABASE_NAME]

def get_database():
    return database

async def get_next_sequence_value(sequence_name: str):
    sequence_document = await database["counters"].find_one_and_update(
        {"_id": sequence_name},
        {"$inc": {"sequence_value": 1}},
        upsert=True,
        return_document=True
    )
    return sequence_document["sequence_value"]