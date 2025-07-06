from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import time
from abc import ABC, abstractmethod
from github import Github, GithubException, RateLimitExceededException
from github.GithubObject import NotSet
from loguru import logger

from src.config.settings import settings
from src.storage.mongodb_client import mongodb_client
from src.storage.timeseries_ops import TimeSeriesOperations


class RateLimiter:
    """Rate limiter for GitHub API calls"""
    
    def __init__(self, max_requests_per_hour: int, buffer: float = 0.8):
        self.max_requests = int(max_requests_per_hour * buffer)
        self.requests = []
        self.window = timedelta(hours=1)
    
    def wait_if_needed(self) -> None:
        """Wait if rate limit would be exceeded"""
        now = datetime.utcnow()
        
        # Remove old requests outside the window
        self.requests = [req_time for req_time in self.requests 
                        if now - req_time < self.window]
        
        if len(self.requests) >= self.max_requests:
            # Calculate wait time
            oldest_request = min(self.requests)
            wait_until = oldest_request + self.window
            wait_seconds = (wait_until - now).total_seconds()
            
            if wait_seconds > 0:
                logger.warning(f"Rate limit reached. Waiting {wait_seconds:.1f} seconds...")
                time.sleep(wait_seconds)
    
    def record_request(self) -> None:
        """Record a request"""
        self.requests.append(datetime.utcnow())


class BaseCollector(ABC):
    """Base class for GitHub data collectors"""
    
    def __init__(self):
        self.github = Github(settings.github_token)
        self.rate_limiter = RateLimiter(
            settings.rate_limit_requests_per_hour,
            settings.rate_limit_buffer
        )
        self.db_client = mongodb_client
        self.ts_ops = TimeSeriesOperations()
        self._ensure_connected()
    
    def _ensure_connected(self) -> None:
        """Ensure database connection is established"""
        if not self.db_client.client:
            self.db_client.connect()
    
    def _make_api_call(self, func, *args, **kwargs):
        """Make an API call with rate limiting and error handling"""
        self.rate_limiter.wait_if_needed()
        
        try:
            result = func(*args, **kwargs)
            self.rate_limiter.record_request()
            return result
            
        except RateLimitExceededException as e:
            # GitHub's rate limit was hit despite our tracking
            reset_time = datetime.fromtimestamp(e.resettime)
            wait_seconds = (reset_time - datetime.utcnow()).total_seconds()
            logger.warning(f"GitHub rate limit exceeded. Waiting {wait_seconds:.1f} seconds...")
            time.sleep(wait_seconds + 1)
            return self._make_api_call(func, *args, **kwargs)
            
        except GithubException as e:
            logger.error(f"GitHub API error: {e}")
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error during API call: {e}")
            raise
    
    def check_rate_limit(self) -> Dict[str, Any]:
        """Check current rate limit status"""
        rate_limit = self._make_api_call(self.github.get_rate_limit)
        
        core = rate_limit.core
        search = rate_limit.search
        
        return {
            'core': {
                'limit': core.limit,
                'remaining': core.remaining,
                'reset': datetime.fromtimestamp(core.reset.timestamp()),
                'used': core.limit - core.remaining
            },
            'search': {
                'limit': search.limit,
                'remaining': search.remaining,
                'reset': datetime.fromtimestamp(search.reset.timestamp()),
                'used': search.limit - search.remaining
            }
        }
    
    def get_repository(self, owner: str, name: str):
        """Get a repository object"""
        return self._make_api_call(
            self.github.get_repo,
            f"{owner}/{name}"
        )
    
    def get_user(self, username: str):
        """Get a user object"""
        return self._make_api_call(
            self.github.get_user,
            username
        )
    
    @abstractmethod
    def collect(self, *args, **kwargs) -> Dict[str, Any]:
        """Collect data - to be implemented by subclasses"""
        pass
    
    @abstractmethod
    def get_collection_name(self) -> str:
        """Get the MongoDB collection name for this collector"""
        pass
    
    def save_data(self, data: Dict[str, Any]) -> str:
        """Save collected data to MongoDB"""
        if 'timestamp' not in data:
            data['timestamp'] = datetime.utcnow()
        
        collection_name = self.get_collection_name()
        collection = self.db_client.get_collection(collection_name)
        
        result = collection.insert_one(data)
        logger.info(f"Saved data to {collection_name}: {result.inserted_id}")
        
        return str(result.inserted_id)
    
    def bulk_save_data(self, data_list: List[Dict[str, Any]]) -> int:
        """Bulk save collected data to MongoDB"""
        timestamp = datetime.utcnow()
        
        for data in data_list:
            if 'timestamp' not in data:
                data['timestamp'] = timestamp
        
        collection_name = self.get_collection_name()
        count = self.db_client.bulk_insert(collection_name, data_list)
        
        logger.info(f"Bulk saved {count} documents to {collection_name}")
        return count
    
    def get_previous_data(self, filter_query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get the most recent previous data point"""
        collection_name = self.get_collection_name()
        collection = self.db_client.get_collection(collection_name)
        
        return collection.find_one(
            filter_query,
            sort=[('timestamp', -1)]
        )