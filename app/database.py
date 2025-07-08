from motor.motor_asyncio import AsyncIOMotorClient
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os

class Settings(BaseSettings):

    load_dotenv()

    DB_USER: str = os.getenv("DB_USER")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD")
    DB_CLUSTER: str = os.getenv("DB_CLUSTER")
    DB_NAME: str = os.getenv("DB_NAME")

    @property
    def MONGODB_URL(self):
        return f"mongodb+srv://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_CLUSTER}.mongodb.net/?retryWrites=true&w=majority&appName=cul-cluster"

settings = Settings()

client = AsyncIOMotorClient(settings.MONGODB_URL)
database = client[settings.DB_NAME]

def get_database():
    return database

async def get_next_sequence_value(sequence_name: str):
    sequence_document = await database["counters"].find_one_and_update(
        {"_id": sequence_name},
        {"$inc": {"sequence_value": 1}},
        upsert=True,
        return_document=True
    )
    return sequence_document.get("sequence_value", 1)
