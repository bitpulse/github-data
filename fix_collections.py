#!/usr/bin/env python3
"""
Script to fix/recreate MongoDB collections if needed
"""

from src.config.settings import settings
from src.storage.mongodb_client import mongodb_client
from loguru import logger

def fix_collections():
    """Drop and recreate collections with correct settings"""
    try:
        # Connect to MongoDB
        mongodb_client.client = mongodb_client.MongoClient(settings.mongodb_uri)
        mongodb_client.db = mongodb_client.client[settings.mongodb_database]
        
        # Get existing collections
        existing_collections = mongodb_client.db.list_collection_names()
        
        # Drop the release milestones collection if it exists with wrong config
        if settings.release_milestones_collection in existing_collections:
            mongodb_client.db.drop_collection(settings.release_milestones_collection)
            logger.info(f"Dropped collection: {settings.release_milestones_collection}")
        
        # Now reconnect to recreate collections properly
        mongodb_client.client.close()
        mongodb_client.client = None
        mongodb_client.connect()
        
        logger.info("Collections fixed successfully!")
        
    except Exception as e:
        logger.error(f"Error fixing collections: {e}")
    finally:
        if mongodb_client.client:
            mongodb_client.close()

if __name__ == "__main__":
    fix_collections()