"""
MongoDB Database Connection Module
Handles all MongoDB operations for the application
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from typing import Optional
import logging
from core.config import settings
from bson import ObjectId

logger = logging.getLogger(__name__)

# MongoDB client instances
mongodb_client: Optional[AsyncIOMotorClient] = None
mongodb_sync_client: Optional[MongoClient] = None
db = None
db_sync = None

def init_mongodb():
    """Initialize MongoDB connection (sync)"""
    global mongodb_sync_client, db_sync
    
    if not settings.MONGODB_STRING:
        logger.warning("⚠️ MONGODB_STRING not found in settings. MongoDB disabled.")
        return None
    
    try:
        # Extract database name from connection string if not specified
        connection_string = settings.MONGODB_STRING
        
        # Create sync client for migrations and sync operations
        mongodb_sync_client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)
        
        # Test connection
        mongodb_sync_client.admin.command('ping')
        
        # Get database (extract from connection string or use default)
        if '/' in connection_string.split('?')[0]:
            # Extract DB name from connection string: mongodb://.../dbname
            db_name = connection_string.split('/')[-1].split('?')[0]
            if db_name:
                db_sync = mongodb_sync_client[db_name]
            else:
                db_sync = mongodb_sync_client[settings.MONGODB_DB]
        else:
            db_sync = mongodb_sync_client[settings.MONGODB_DB]
        
        logger.info(f"✅ MongoDB connection established (sync) - Database: {db_sync.name}")
        return db_sync
    except ConnectionFailure as e:
        logger.error(f"❌ MongoDB connection failed: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"❌ MongoDB initialization error: {str(e)}")
        return None

async def init_mongodb_async():
    """Initialize MongoDB async connection"""
    global mongodb_client, db
    
    if not settings.MONGODB_STRING:
        logger.warning("⚠️ MONGODB_STRING not found in settings. MongoDB disabled.")
        return None
    
    try:
        connection_string = settings.MONGODB_STRING
        
        # Create async client
        mongodb_client = AsyncIOMotorClient(connection_string, serverSelectionTimeoutMS=5000)
        
        # Test connection
        await mongodb_client.admin.command('ping')
        
        # Get database
        if '/' in connection_string.split('?')[0]:
            db_name = connection_string.split('/')[-1].split('?')[0]
            if db_name:
                db = mongodb_client[db_name]
            else:
                db = mongodb_client[settings.MONGODB_DB]
        else:
            db = mongodb_client[settings.MONGODB_DB]
        
        logger.info(f"✅ MongoDB async connection established - Database: {db.name}")
        return db
    except Exception as e:
        logger.error(f"❌ MongoDB async initialization error: {str(e)}")
        return None

def get_mongodb():
    """Get MongoDB database instance (sync)"""
    if db_sync is None:
        init_mongodb()
    return db_sync

async def get_mongodb_async():
    """Get MongoDB database instance (async)"""
    if db is None:
        await init_mongodb_async()
    return db

def convert_id_to_str(doc):
    """Convert ObjectId to string for JSON serialization"""
    if doc is None:
        return None
    if isinstance(doc, ObjectId):
        return str(doc)
    if isinstance(doc, dict):
        result = {}
        for key, value in doc.items():
            if key == '_id':
                result['id'] = str(value) if isinstance(value, ObjectId) else value
            elif isinstance(value, ObjectId):
                result[key] = str(value)
            elif isinstance(value, dict):
                result[key] = convert_id_to_str(value)
            elif isinstance(value, list):
                result[key] = [convert_id_to_str(item) for item in value]
            else:
                result[key] = value
        return result
    elif isinstance(doc, list):
        return [convert_id_to_str(item) for item in doc]
    return doc

def str_to_objectid(id_str):
    """Convert string ID to ObjectId"""
    if isinstance(id_str, ObjectId):
        return id_str
    if isinstance(id_str, str) and ObjectId.is_valid(id_str):
        return ObjectId(id_str)
    return None

# Initialize sync connection on import
init_mongodb()

