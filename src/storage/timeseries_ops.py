from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import pymongo
from pymongo import ASCENDING, DESCENDING
from loguru import logger

from src.storage.mongodb_client import mongodb_client
from src.config.settings import settings


class TimeSeriesOperations:
    """Operations for time series data manipulation and analysis"""
    
    def __init__(self):
        self.db_client = mongodb_client
    
    def calculate_delta(
        self,
        collection_name: str,
        repo_owner: str,
        repo_name: str,
        metric_fields: List[str]
    ) -> Dict[str, Any]:
        """Calculate delta between current and previous data points"""
        collection = self.db_client.get_collection(collection_name)
        
        # Get last two data points
        cursor = collection.find(
            {
                'repo.owner': repo_owner,
                'repo.name': repo_name
            },
            sort=[('timestamp', DESCENDING)],
            limit=2
        )
        
        data_points = list(cursor)
        if len(data_points) < 2:
            return {}
        
        current = data_points[0]
        previous = data_points[1]
        
        deltas = {}
        for field in metric_fields:
            current_value = self._get_nested_value(current, field)
            previous_value = self._get_nested_value(previous, field)
            
            if current_value is not None and previous_value is not None:
                deltas[f"{field}_change"] = current_value - previous_value
                if previous_value > 0:
                    deltas[f"{field}_growth_rate"] = (current_value - previous_value) / previous_value
        
        return deltas
    
    def get_time_range_data(
        self,
        collection_name: str,
        start_time: datetime,
        end_time: datetime,
        filter_query: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Get data within a time range"""
        collection = self.db_client.get_collection(collection_name)
        
        query = {'timestamp': {'$gte': start_time, '$lte': end_time}}
        if filter_query:
            query.update(filter_query)
        
        return list(collection.find(query).sort('timestamp', ASCENDING))
    
    def calculate_moving_average(
        self,
        collection_name: str,
        repo_owner: str,
        repo_name: str,
        metric_field: str,
        window_days: int
    ) -> List[Dict[str, Any]]:
        """Calculate moving average for a metric"""
        collection = self.db_client.get_collection(collection_name)
        
        pipeline = [
            {
                '$match': {
                    'repo.owner': repo_owner,
                    'repo.name': repo_name,
                    'timestamp': {
                        '$gte': datetime.utcnow() - timedelta(days=window_days * 2)
                    }
                }
            },
            {
                '$sort': {'timestamp': 1}
            },
            {
                '$setWindowFields': {
                    'partitionBy': '$repo.id',
                    'sortBy': {'timestamp': 1},
                    'output': {
                        f'{metric_field}_moving_avg': {
                            '$avg': f'$stats.{metric_field}',
                            'window': {
                                'range': [-window_days * 24 * 60 * 60, 0],
                                'unit': 'second'
                            }
                        }
                    }
                }
            },
            {
                '$match': {
                    'timestamp': {
                        '$gte': datetime.utcnow() - timedelta(days=window_days)
                    }
                }
            }
        ]
        
        return list(collection.aggregate(pipeline))
    
    def detect_anomalies(
        self,
        collection_name: str,
        repo_owner: str,
        repo_name: str,
        metric_field: str,
        threshold_multiplier: float = 2.0
    ) -> List[Dict[str, Any]]:
        """Detect anomalies in time series data using statistical methods"""
        collection = self.db_client.get_collection(collection_name)
        
        # Calculate mean and standard deviation
        stats_pipeline = [
            {
                '$match': {
                    'repo.owner': repo_owner,
                    'repo.name': repo_name,
                    'timestamp': {
                        '$gte': datetime.utcnow() - timedelta(days=30)
                    }
                }
            },
            {
                '$group': {
                    '_id': None,
                    'mean': {'$avg': f'$stats.{metric_field}'},
                    'stdDev': {'$stdDevPop': f'$stats.{metric_field}'}
                }
            }
        ]
        
        stats_result = list(collection.aggregate(stats_pipeline))
        if not stats_result:
            return []
        
        mean = stats_result[0]['mean']
        std_dev = stats_result[0]['stdDev']
        
        # Find anomalies
        anomaly_pipeline = [
            {
                '$match': {
                    'repo.owner': repo_owner,
                    'repo.name': repo_name,
                    'timestamp': {
                        '$gte': datetime.utcnow() - timedelta(days=7)
                    }
                }
            },
            {
                '$addFields': {
                    'z_score': {
                        '$divide': [
                            {'$subtract': [f'$stats.{metric_field}', mean]},
                            std_dev
                        ]
                    }
                }
            },
            {
                '$match': {
                    '$or': [
                        {'z_score': {'$gt': threshold_multiplier}},
                        {'z_score': {'$lt': -threshold_multiplier}}
                    ]
                }
            }
        ]
        
        return list(collection.aggregate(anomaly_pipeline))
    
    def get_growth_trends(
        self,
        collection_name: str,
        repo_owner: str,
        repo_name: str,
        metric_field: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """Calculate growth trends for a metric"""
        collection = self.db_client.get_collection(collection_name)
        
        pipeline = [
            {
                '$match': {
                    'repo.owner': repo_owner,
                    'repo.name': repo_name,
                    'timestamp': {
                        '$gte': datetime.utcnow() - timedelta(days=days)
                    }
                }
            },
            {
                '$sort': {'timestamp': 1}
            },
            {
                '$group': {
                    '_id': {
                        '$dateToString': {
                            'format': '%Y-%m-%d',
                            'date': '$timestamp'
                        }
                    },
                    'daily_max': {'$max': f'$stats.{metric_field}'},
                    'daily_min': {'$min': f'$stats.{metric_field}'},
                    'daily_avg': {'$avg': f'$stats.{metric_field}'},
                    'data_points': {'$sum': 1}
                }
            },
            {
                '$sort': {'_id': 1}
            }
        ]
        
        daily_data = list(collection.aggregate(pipeline))
        
        if len(daily_data) < 2:
            return {}
        
        # Calculate overall growth
        first_value = daily_data[0]['daily_avg']
        last_value = daily_data[-1]['daily_avg']
        
        growth_rate = (last_value - first_value) / first_value if first_value > 0 else 0
        
        # Calculate daily growth rates
        daily_growth_rates = []
        for i in range(1, len(daily_data)):
            prev_val = daily_data[i-1]['daily_avg']
            curr_val = daily_data[i]['daily_avg']
            if prev_val > 0:
                daily_growth_rates.append((curr_val - prev_val) / prev_val)
        
        return {
            'total_growth_rate': growth_rate,
            'average_daily_growth': sum(daily_growth_rates) / len(daily_growth_rates) if daily_growth_rates else 0,
            'trend_direction': 'increasing' if growth_rate > 0 else 'decreasing',
            'volatility': max(daily_growth_rates) - min(daily_growth_rates) if daily_growth_rates else 0,
            'data_points': len(daily_data)
        }
    
    def _get_nested_value(self, data: Dict[str, Any], field_path: str) -> Any:
        """Get value from nested dictionary using dot notation"""
        parts = field_path.split('.')
        value = data
        
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return None
        
        return value