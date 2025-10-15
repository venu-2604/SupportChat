from pymongo import MongoClient
from ..core.config import settings


def get_mongo_client() -> MongoClient:
    return MongoClient(settings.MONGO_URI)


def get_mongo_db():
    """Get MongoDB database instance"""
    client = get_mongo_client()
    return client[settings.MONGO_DB]


def get_case_memory_collection():
    client = get_mongo_client()
    db = client[settings.MONGO_DB]
    return db["case_memory"]


