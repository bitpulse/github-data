"""
Chart data aggregator for crypto GitHub time series data
Creates chart-ready aggregations from raw time series data
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.collection import Collection
from loguru import logger

from src.config.settings import settings
from src.storage.mongodb_client import mongodb_client


class ChartDataAggregator:
    """Aggregates time series data into chart-ready formats"""
    
    def __init__(self):
        self.db_client = mongodb_client
        self._ensure_connected()
    
    def _ensure_connected(self):
        """Ensure database connection"""
        if not self.db_client.client:
            self.db_client.connect()
    
    def create_daily_aggregations(self, days_back: int = 30) -> int:
        """Create daily aggregations for faster chart queries"""
        collection = self.db_client.get_collection(settings.repo_stats_collection)
        daily_collection = self.db_client.get_collection('daily_repo_stats')
        
        # Calculate date range
        end_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        start_date = end_date - timedelta(days=days_back)
        
        logger.info(f"Creating daily aggregations from {start_date} to {end_date}")
        
        # Aggregation pipeline for daily summaries
        pipeline = [
            {
                '$match': {
                    'timestamp': {'$gte': start_date, '$lt': end_date + timedelta(days=1)},
                    'repo.coin_id': {'$exists': True}
                }
            },
            {
                '$group': {
                    '_id': {
                        'date': {'$dateToString': {'format': '%Y-%m-%d', 'date': '$timestamp'}},
                        'coin_id': '$repo.coin_id',
                        'owner': '$repo.owner',
                        'name': '$repo.name'
                    },
                    'repo_info': {'$first': '$repo'},
                    'daily_stats': {
                        '$push': {
                            'timestamp': '$timestamp',
                            'stars': '$stats.stars',
                            'forks': '$stats.forks',
                            'watchers': '$stats.watchers',
                            'open_issues': '$stats.open_issues',
                            'commits_24h': '$activity.commits_last_24h',
                            'contributors_7d': '$activity.unique_contributors_7d'
                        }
                    },
                    'data_points': {'$sum': 1}
                }
            },
            {
                '$addFields': {
                    'date': '$_id.date',
                    'coin_id': '$_id.coin_id',
                    'repo_key': {'$concat': ['$_id.owner', '/', '$_id.name']},
                    # Calculate daily metrics
                    'stars_start': {'$arrayElemAt': ['$daily_stats.stars', 0]},
                    'stars_end': {'$arrayElemAt': ['$daily_stats.stars', -1]},
                    'forks_start': {'$arrayElemAt': ['$daily_stats.forks', 0]},
                    'forks_end': {'$arrayElemAt': ['$daily_stats.forks', -1]},
                    'max_commits_24h': {'$max': '$daily_stats.commits_24h'},
                    'avg_contributors_7d': {'$avg': '$daily_stats.contributors_7d'}
                }
            },
            {
                '$addFields': {
                    'stars_change': {'$subtract': ['$stars_end', '$stars_start']},
                    'forks_change': {'$subtract': ['$forks_end', '$forks_start']}
                }
            },
            {
                '$project': {
                    '_id': {
                        '$concat': ['$coin_id', '_', '$repo_key', '_', '$date']
                    },
                    'date': 1,
                    'coin_id': 1,
                    'repo_key': 1,
                    'repo_info': 1,
                    'metrics': {
                        'stars_start': '$stars_start',
                        'stars_end': '$stars_end',
                        'stars_change': '$stars_change',
                        'forks_start': '$forks_start',
                        'forks_end': '$forks_end',
                        'forks_change': '$forks_change',
                        'max_commits_24h': '$max_commits_24h',
                        'avg_contributors_7d': '$avg_contributors_7d'
                    },
                    'data_points': 1,
                    'timestamp': {'$dateFromString': {'dateString': '$date'}}
                }
            }
        ]
        
        # Execute aggregation and upsert results
        results = list(collection.aggregate(pipeline))
        
        if results:
            # Use bulk operations for efficiency
            from pymongo import UpdateOne
            bulk_ops = []
            
            for doc in results:
                bulk_ops.append(
                    UpdateOne(
                        {'_id': doc['_id']},
                        {'$set': doc},
                        upsert=True
                    )
                )
            
            if bulk_ops:
                daily_collection.bulk_write(bulk_ops)
                logger.info(f"Created/updated {len(bulk_ops)} daily aggregation records")
        
        return len(results)
    
    def get_chart_data_stars(self, coin_id: str, days: int = 30) -> Dict[str, Any]:
        """Get stars chart data for a coin"""
        collection = self.db_client.get_collection('daily_repo_stats')
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        pipeline = [
            {
                '$match': {
                    'coin_id': coin_id,
                    'timestamp': {'$gte': start_date, '$lte': end_date}
                }
            },
            {
                '$group': {
                    '_id': '$date',
                    'total_stars': {'$sum': '$metrics.stars_end'},
                    'total_stars_change': {'$sum': '$metrics.stars_change'},
                    'repositories': {
                        '$push': {
                            'repo': '$repo_key',
                            'stars': '$metrics.stars_end',
                            'change': '$metrics.stars_change',
                            'is_primary': '$repo_info.is_primary_repo'
                        }
                    }
                }
            },
            {
                '$sort': {'_id': 1}
            },
            {
                '$project': {
                    'date': '$_id',
                    'total_stars': 1,
                    'total_stars_change': 1,
                    'repositories': 1,
                    '_id': 0
                }
            }
        ]
        
        results = list(collection.aggregate(pipeline))
        
        return {
            'coin_id': coin_id,
            'metric': 'stars',
            'timeframe': f'{days}d',
            'data': results
        }
    
    def get_chart_data_commits(self, coin_id: str, days: int = 30) -> Dict[str, Any]:
        """Get commits chart data for a coin"""
        collection = self.db_client.get_collection(settings.repo_stats_collection)
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        pipeline = [
            {
                '$match': {
                    'repo.coin_id': coin_id,
                    'timestamp': {'$gte': start_date, '$lte': end_date}
                }
            },
            {
                '$group': {
                    '_id': {
                        'date': {'$dateToString': {'format': '%Y-%m-%d', 'date': '$timestamp'}},
                        'repo': {'$concat': ['$repo.owner', '/', '$repo.name']}
                    },
                    'max_commits_24h': {'$max': '$activity.commits_last_24h'},
                    'repo_info': {'$first': '$repo'}
                }
            },
            {
                '$group': {
                    '_id': '$_id.date',
                    'total_commits': {'$sum': '$max_commits_24h'},
                    'repositories': {
                        '$push': {
                            'repo': '$_id.repo',
                            'commits': '$max_commits_24h',
                            'is_primary': '$repo_info.is_primary_repo'
                        }
                    }
                }
            },
            {
                '$sort': {'_id': 1}
            },
            {
                '$project': {
                    'date': '$_id',
                    'total_commits': 1,
                    'repositories': 1,
                    '_id': 0
                }
            }
        ]
        
        results = list(collection.aggregate(pipeline))
        
        return {
            'coin_id': coin_id,
            'metric': 'commits_24h',
            'timeframe': f'{days}d',
            'data': results
        }
    
    def get_multi_metric_chart_data(self, coin_id: str, days: int = 30) -> Dict[str, Any]:
        """Get multiple metrics for comprehensive charts"""
        daily_collection = self.db_client.get_collection('daily_repo_stats')
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        pipeline = [
            {
                '$match': {
                    'coin_id': coin_id,
                    'timestamp': {'$gte': start_date, '$lte': end_date}
                }
            },
            {
                '$group': {
                    '_id': '$date',
                    'stars': {'$sum': '$metrics.stars_end'},
                    'stars_change': {'$sum': '$metrics.stars_change'},
                    'forks': {'$sum': '$metrics.forks_end'},
                    'forks_change': {'$sum': '$metrics.forks_change'},
                    'commits': {'$sum': '$metrics.max_commits_24h'},
                    'avg_contributors': {'$avg': '$metrics.avg_contributors_7d'},
                    'repositories_count': {'$sum': 1}
                }
            },
            {
                '$sort': {'_id': 1}
            },
            {
                '$project': {
                    'date': '$_id',
                    'metrics': {
                        'stars': '$stars',
                        'stars_change': '$stars_change',
                        'forks': '$forks',
                        'forks_change': '$forks_change',
                        'commits_24h': '$commits',
                        'avg_contributors_7d': '$avg_contributors',
                        'repositories_count': '$repositories_count'
                    },
                    '_id': 0
                }
            }
        ]
        
        results = list(daily_collection.aggregate(pipeline))
        
        return {
            'coin_id': coin_id,
            'timeframe': f'{days}d',
            'data': results
        }
    
    def get_correlation_data(self, coin_id: str, days: int = 30) -> Dict[str, Any]:
        """Get GitHub metrics for correlation with market data"""
        # This would join with your crypto_project market data
        daily_collection = self.db_client.get_collection('daily_repo_stats')
        crypto_collection = self.db_client.get_collection('crypto_project')
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get GitHub metrics
        github_pipeline = [
            {
                '$match': {
                    'coin_id': coin_id,
                    'timestamp': {'$gte': start_date, '$lte': end_date}
                }
            },
            {
                '$group': {
                    '_id': '$date',
                    'github_metrics': {
                        'stars': {'$sum': '$metrics.stars_end'},
                        'forks': {'$sum': '$metrics.forks_end'},
                        'commits_24h': {'$sum': '$metrics.max_commits_24h'},
                        'contributors_7d': {'$avg': '$metrics.avg_contributors_7d'}
                    }
                }
            },
            {
                '$sort': {'_id': 1}
            }
        ]
        
        github_results = list(daily_collection.aggregate(github_pipeline))
        
        # Get latest market data for this coin
        market_data = crypto_collection.find_one(
            {'coin_id': coin_id},
            {'market_metrics': 1, 'basic_info.name': 1, 'basic_info.symbol': 1}
        )
        
        return {
            'coin_id': coin_id,
            'project_name': market_data.get('basic_info', {}).get('name', coin_id) if market_data else coin_id,
            'symbol': market_data.get('basic_info', {}).get('symbol', '').upper() if market_data else '',
            'timeframe': f'{days}d',
            'github_data': github_results,
            'latest_market_data': market_data.get('market_metrics', {}) if market_data else {}
        }
    
    def get_top_projects_summary(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get summary of top crypto projects by GitHub activity"""
        collection = self.db_client.get_collection(settings.repo_stats_collection)
        
        # Get latest data for each project
        pipeline = [
            {
                '$match': {
                    'repo.coin_id': {'$exists': True},
                    'timestamp': {'$gte': datetime.utcnow() - timedelta(hours=24)}
                }
            },
            {
                '$group': {
                    '_id': '$repo.coin_id',
                    'latest_data': {'$last': '$$ROOT'},
                    'total_stars': {'$sum': '$stats.stars'},
                    'total_forks': {'$sum': '$stats.forks'},
                    'total_commits_7d': {'$sum': '$activity.commits_last_7d'},
                    'repositories_count': {'$sum': 1}
                }
            },
            {
                '$sort': {'total_stars': -1}
            },
            {
                '$limit': limit
            },
            {
                '$project': {
                    'coin_id': '$_id',
                    'project_name': '$latest_data.repo.project_name',
                    'symbol': '$latest_data.repo.symbol',
                    'metrics': {
                        'total_stars': '$total_stars',
                        'total_forks': '$total_forks',
                        'total_commits_7d': '$total_commits_7d',
                        'repositories_count': '$repositories_count'
                    },
                    '_id': 0
                }
            }
        ]
        
        return list(collection.aggregate(pipeline))


# Global instance
chart_aggregator = ChartDataAggregator()