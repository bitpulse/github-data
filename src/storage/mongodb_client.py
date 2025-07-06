from typing import Optional, Dict, Any
from datetime import datetime
import pymongo
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from loguru import logger

from src.config.settings import settings


class MongoDBClient:
    """MongoDB client with time series collection support"""
    
    def __init__(self):
        self.client: Optional[MongoClient] = None
        self.db: Optional[Database] = None
        self._collections: Dict[str, Collection] = {}
        
    def connect(self) -> None:
        """Establish connection to MongoDB"""
        try:
            self.client = MongoClient(settings.mongodb_uri)
            self.db = self.client[settings.mongodb_database]
            
            # Test connection
            self.client.admin.command('ping')
            logger.info(f"Connected to MongoDB at {settings.mongodb_uri}")
            
            # Initialize time series collections
            self._initialize_timeseries_collections()
            
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    
    def _initialize_timeseries_collections(self) -> None:
        """Create time series collections if they don't exist"""
        existing_collections = self.db.list_collection_names()
        
        # Repository stats time series
        if settings.repo_stats_collection not in existing_collections:
            self._create_timeseries_collection(
                settings.repo_stats_collection,
                time_field='timestamp',
                meta_field='repo',
                granularity=settings.timeseries_granularity
            )
            logger.info(f"Created time series collection: {settings.repo_stats_collection}")
        
        # Contributor activity time series
        if settings.contributor_activity_collection not in existing_collections:
            self._create_timeseries_collection(
                settings.contributor_activity_collection,
                time_field='timestamp',
                meta_field='contributor',
                granularity=settings.timeseries_granularity
            )
            logger.info(f"Created time series collection: {settings.contributor_activity_collection}")
        
        # Release milestones time series
        if settings.release_milestones_collection not in existing_collections:
            self._create_timeseries_collection(
                settings.release_milestones_collection,
                time_field='timestamp',
                meta_field='repo',
                granularity='days'  # Less frequent updates
            )
            logger.info(f"Created time series collection: {settings.release_milestones_collection}")
        
        # Create indexes
        self._create_indexes()
    
    def _create_timeseries_collection(
        self,
        collection_name: str,
        time_field: str,
        meta_field: str,
        granularity: str
    ) -> None:
        """Create a time series collection"""
        try:
            self.db.create_collection(
                collection_name,
                timeseries={
                    'timeField': time_field,
                    'metaField': meta_field,
                    'granularity': granularity
                }
            )
        except pymongo.errors.CollectionInvalid:
            logger.warning(f"Collection {collection_name} already exists")
    
    def _create_indexes(self) -> None:
        """Create indexes for better query performance"""
        # Repository stats indexes
        repo_collection = self.get_collection(settings.repo_stats_collection)
        repo_collection.create_index([('repo.owner', 1), ('repo.name', 1), ('timestamp', -1)])
        repo_collection.create_index([('repo.id', 1), ('timestamp', -1)])
        
        # Contributor activity indexes
        contrib_collection = self.get_collection(settings.contributor_activity_collection)
        contrib_collection.create_index([('contributor.username', 1), ('timestamp', -1)])
        contrib_collection.create_index([('contributor.id', 1), ('timestamp', -1)])
        
        logger.info("Created database indexes")
    
    def get_collection(self, collection_name: str) -> Collection:
        """Get a collection by name"""
        if collection_name not in self._collections:
            self._collections[collection_name] = self.db[collection_name]
        return self._collections[collection_name]
    
    def insert_repo_stats(self, stats_data: Dict[str, Any]) -> str:
        """Insert repository statistics"""
        collection = self.get_collection(settings.repo_stats_collection)
        
        # Ensure timestamp is present
        if 'timestamp' not in stats_data:
            stats_data['timestamp'] = datetime.utcnow()
        
        result = collection.insert_one(stats_data)
        return str(result.inserted_id)
    
    def insert_contributor_activity(self, activity_data: Dict[str, Any]) -> str:
        """Insert contributor activity data"""
        collection = self.get_collection(settings.contributor_activity_collection)
        
        # Ensure timestamp is present
        if 'timestamp' not in activity_data:
            activity_data['timestamp'] = datetime.utcnow()
        
        result = collection.insert_one(activity_data)
        return str(result.inserted_id)
    
    def bulk_insert(self, collection_name: str, documents: list) -> int:
        """Bulk insert documents"""
        collection = self.get_collection(collection_name)
        
        # Ensure all documents have timestamps
        for doc in documents:
            if 'timestamp' not in doc:
                doc['timestamp'] = datetime.utcnow()
        
        result = collection.insert_many(documents)
        return len(result.inserted_ids)
    
    def get_latest_stats(self, repo_owner: str, repo_name: str) -> Optional[Dict[str, Any]]:
        """Get the latest stats for a repository"""
        collection = self.get_collection(settings.repo_stats_collection)
        
        return collection.find_one(
            {
                'repo.owner': repo_owner,
                'repo.name': repo_name
            },
            sort=[('timestamp', -1)]
        )
    
    def close(self) -> None:
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("Closed MongoDB connection")


# Global instance
mongodb_client = MongoDBClient()