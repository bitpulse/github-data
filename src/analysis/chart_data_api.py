"""
Chart Data API - Ready for backend integration
Provides clean API functions that return chart-ready data
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from loguru import logger

from src.analysis.chart_aggregator import chart_aggregator
from src.utils.crypto_mapping import crypto_mapper


class ChartDataAPI:
    """API layer for chart-ready data"""
    
    def __init__(self):
        self.aggregator = chart_aggregator
        self.mapper = crypto_mapper
    
    def get_available_coins(self) -> List[Dict[str, str]]:
        """Get list of available coins with GitHub data"""
        summary = self.mapper.get_project_summary()
        
        available_coins = []
        for coin_id in summary['projects']:
            coin_data = self.mapper._coin_to_repos_map.get(coin_id, {})
            available_coins.append({
                'coin_id': coin_id,
                'name': coin_data.get('project_name', coin_id),
                'symbol': coin_data.get('symbol', '').upper(),
                'repositories_count': len(coin_data.get('repositories', []))
            })
        
        return sorted(available_coins, key=lambda x: x['name'])
    
    def get_stars_chart_data(self, coin_id: str, days: int = 30) -> Dict[str, Any]:
        """
        Get stars data formatted for charts
        
        Returns:
        {
            "coin_id": "bitcoin",
            "metric": "stars",
            "timeframe": "30d",
            "chart_data": [
                {"x": "2024-01-01", "y": 76000},
                {"x": "2024-01-02", "y": 76012}
            ],
            "summary": {
                "current": 76543,
                "change": 543,
                "change_percent": 0.71
            }
        }
        """
        try:
            # Ensure daily aggregations are up to date
            self.aggregator.create_daily_aggregations(days + 5)
            
            # Get raw data
            raw_data = self.aggregator.get_chart_data_stars(coin_id, days)
            
            # Format for charts
            chart_points = []
            for item in raw_data['data']:
                chart_points.append({
                    'x': item['date'],
                    'y': item['total_stars']
                })
            
            # Calculate summary
            summary = {'current': 0, 'change': 0, 'change_percent': 0}
            if chart_points:
                summary['current'] = chart_points[-1]['y']
                if len(chart_points) > 1:
                    first_value = chart_points[0]['y']
                    summary['change'] = summary['current'] - first_value
                    if first_value > 0:
                        summary['change_percent'] = (summary['change'] / first_value) * 100
            
            return {
                'coin_id': coin_id,
                'metric': 'stars',
                'timeframe': f'{days}d',
                'chart_data': chart_points,
                'summary': summary
            }
            
        except Exception as e:
            logger.error(f"Error getting stars chart data for {coin_id}: {e}")
            return {'error': str(e)}
    
    def get_commits_chart_data(self, coin_id: str, days: int = 30) -> Dict[str, Any]:
        """Get commits data formatted for charts"""
        try:
            raw_data = self.aggregator.get_chart_data_commits(coin_id, days)
            
            chart_points = []
            for item in raw_data['data']:
                chart_points.append({
                    'x': item['date'],
                    'y': item['total_commits']
                })
            
            # Calculate summary
            summary = {
                'total': sum(point['y'] for point in chart_points),
                'average_daily': 0,
                'peak_day': 0
            }
            if chart_points:
                summary['average_daily'] = summary['total'] / len(chart_points)
                summary['peak_day'] = max(point['y'] for point in chart_points)
            
            return {
                'coin_id': coin_id,
                'metric': 'commits_24h',
                'timeframe': f'{days}d',
                'chart_data': chart_points,
                'summary': summary
            }
            
        except Exception as e:
            logger.error(f"Error getting commits chart data for {coin_id}: {e}")
            return {'error': str(e)}
    
    def get_multi_metric_dashboard(self, coin_id: str, days: int = 30) -> Dict[str, Any]:
        """
        Get multi-metric dashboard data
        
        Returns:
        {
            "coin_id": "bitcoin",
            "project_name": "Bitcoin",
            "symbol": "BTC",
            "timeframe": "30d",
            "metrics": {
                "stars": [{"x": "2024-01-01", "y": 76000}],
                "forks": [{"x": "2024-01-01", "y": 35000}],
                "commits": [{"x": "2024-01-01", "y": 5}]
            },
            "summary": {
                "stars": {"current": 76543, "change": 543},
                "forks": {"current": 35678, "change": 123}
            }
        }
        """
        try:
            # Ensure daily aggregations are up to date
            self.aggregator.create_daily_aggregations(days + 5)
            
            raw_data = self.aggregator.get_multi_metric_chart_data(coin_id, days)
            
            # Get project info
            coin_data = self.mapper._coin_to_repos_map.get(coin_id, {})
            project_name = coin_data.get('project_name', coin_id)
            symbol = coin_data.get('symbol', '').upper()
            
            # Format metrics for charts
            metrics = {
                'stars': [],
                'forks': [],
                'commits': [],
                'contributors': []
            }
            
            for item in raw_data['data']:
                date = item['date']
                metrics_data = item['metrics']
                
                metrics['stars'].append({'x': date, 'y': metrics_data['stars']})
                metrics['forks'].append({'x': date, 'y': metrics_data['forks']})
                metrics['commits'].append({'x': date, 'y': metrics_data['commits_24h']})
                metrics['contributors'].append({'x': date, 'y': round(metrics_data['avg_contributors_7d'], 1)})
            
            # Calculate summaries
            summary = {}
            for metric_name, metric_data in metrics.items():
                if metric_data:
                    current = metric_data[-1]['y']
                    first = metric_data[0]['y']
                    change = current - first
                    change_percent = (change / first * 100) if first > 0 else 0
                    
                    summary[metric_name] = {
                        'current': current,
                        'change': change,
                        'change_percent': round(change_percent, 2)
                    }
            
            return {
                'coin_id': coin_id,
                'project_name': project_name,
                'symbol': symbol,
                'timeframe': f'{days}d',
                'metrics': metrics,
                'summary': summary
            }
            
        except Exception as e:
            logger.error(f"Error getting dashboard data for {coin_id}: {e}")
            return {'error': str(e)}
    
    def get_correlation_analysis(self, coin_id: str, days: int = 30) -> Dict[str, Any]:
        """Get GitHub metrics alongside market data for correlation analysis"""
        try:
            correlation_data = self.aggregator.get_correlation_data(coin_id, days)
            
            # Format GitHub data for charts
            github_chart_data = {}
            for item in correlation_data['github_data']:
                date = item['_id']
                metrics = item['github_metrics']
                
                for metric_name, value in metrics.items():
                    if metric_name not in github_chart_data:
                        github_chart_data[metric_name] = []
                    github_chart_data[metric_name].append({'x': date, 'y': value})
            
            return {
                'coin_id': coin_id,
                'project_name': correlation_data['project_name'],
                'symbol': correlation_data['symbol'],
                'timeframe': f'{days}d',
                'github_metrics': github_chart_data,
                'latest_market_data': correlation_data['latest_market_data']
            }
            
        except Exception as e:
            logger.error(f"Error getting correlation data for {coin_id}: {e}")
            return {'error': str(e)}
    
    def get_top_projects_leaderboard(self, limit: int = 10) -> Dict[str, Any]:
        """
        Get top projects leaderboard
        
        Returns:
        {
            "timestamp": "2024-01-15T10:00:00Z",
            "leaderboard": [
                {
                    "rank": 1,
                    "coin_id": "bitcoin",
                    "project_name": "Bitcoin",
                    "symbol": "BTC",
                    "metrics": {
                        "total_stars": 76543,
                        "total_forks": 35678,
                        "total_commits_7d": 45,
                        "repositories_count": 2
                    }
                }
            ]
        }
        """
        try:
            top_projects = self.aggregator.get_top_projects_summary(limit)
            
            leaderboard = []
            for i, project in enumerate(top_projects):
                leaderboard.append({
                    'rank': i + 1,
                    'coin_id': project['coin_id'],
                    'project_name': project['project_name'],
                    'symbol': project['symbol'],
                    'metrics': project['metrics']
                })
            
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'leaderboard': leaderboard
            }
            
        except Exception as e:
            logger.error(f"Error getting leaderboard: {e}")
            return {'error': str(e)}
    
    def get_repository_breakdown(self, coin_id: str) -> Dict[str, Any]:
        """Get detailed breakdown of repositories for a coin"""
        try:
            repositories = self.mapper.get_repositories_for_coin(coin_id)
            coin_data = self.mapper._coin_to_repos_map.get(coin_id, {})
            
            repo_details = []
            for repo in repositories:
                repo_details.append({
                    'owner': repo['owner'],
                    'name': repo['name'],
                    'full_name': f"{repo['owner']}/{repo['name']}",
                    'is_primary': repo['is_primary'],
                    'priority': repo['priority']
                })
            
            return {
                'coin_id': coin_id,
                'project_name': coin_data.get('project_name', coin_id),
                'symbol': coin_data.get('symbol', '').upper(),
                'repositories': repo_details,
                'total_repositories': len(repo_details),
                'primary_repositories': sum(1 for repo in repo_details if repo['is_primary'])
            }
            
        except Exception as e:
            logger.error(f"Error getting repository breakdown for {coin_id}: {e}")
            return {'error': str(e)}


# Global instance for easy import
chart_api = ChartDataAPI()