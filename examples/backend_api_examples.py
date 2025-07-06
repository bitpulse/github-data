#!/usr/bin/env python3
"""
Backend API Examples - How to query GitHub time series data for charts
These examples show how your backend can query the MongoDB collections
to get chart-ready data for the frontend
"""

import sys
import os
from datetime import datetime, timedelta
import json
from typing import Dict, List, Any

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.analysis.chart_data_api import chart_api
from src.storage.mongodb_client import mongodb_client


class BackendAPIExamples:
    """Examples of backend API functions for chart data"""
    
    def __init__(self):
        # Ensure database connection
        mongodb_client.connect()
    
    def api_get_available_coins(self) -> Dict[str, Any]:
        """
        API: GET /api/crypto/coins
        Returns list of available crypto projects with GitHub data
        """
        coins = chart_api.get_available_coins()
        
        return {
            'status': 'success',
            'count': len(coins),
            'data': coins
        }
    
    def api_get_stars_chart(self, coin_id: str, days: int = 30) -> Dict[str, Any]:
        """
        API: GET /api/charts/stars/{coin_id}?days=30
        Returns stars chart data for a specific coin
        """
        chart_data = chart_api.get_stars_chart_data(coin_id, days)
        
        if 'error' in chart_data:
            return {
                'status': 'error',
                'message': chart_data['error']
            }
        
        return {
            'status': 'success',
            'data': chart_data
        }
    
    def api_get_commits_chart(self, coin_id: str, days: int = 30) -> Dict[str, Any]:
        """
        API: GET /api/charts/commits/{coin_id}?days=30
        Returns commits chart data for a specific coin
        """
        chart_data = chart_api.get_commits_chart_data(coin_id, days)
        
        if 'error' in chart_data:
            return {
                'status': 'error',
                'message': chart_data['error']
            }
        
        return {
            'status': 'success',
            'data': chart_data
        }
    
    def api_get_dashboard_data(self, coin_id: str, days: int = 30) -> Dict[str, Any]:
        """
        API: GET /api/dashboard/{coin_id}?days=30
        Returns multi-metric dashboard data
        """
        dashboard_data = chart_api.get_multi_metric_dashboard(coin_id, days)
        
        if 'error' in dashboard_data:
            return {
                'status': 'error',
                'message': dashboard_data['error']
            }
        
        return {
            'status': 'success',
            'data': dashboard_data
        }
    
    def api_get_correlation_data(self, coin_id: str, days: int = 30) -> Dict[str, Any]:
        """
        API: GET /api/correlation/{coin_id}?days=30
        Returns GitHub metrics with market data for correlation analysis
        """
        correlation_data = chart_api.get_correlation_analysis(coin_id, days)
        
        if 'error' in correlation_data:
            return {
                'status': 'error',
                'message': correlation_data['error']
            }
        
        return {
            'status': 'success',
            'data': correlation_data
        }
    
    def api_get_leaderboard(self, limit: int = 10) -> Dict[str, Any]:
        """
        API: GET /api/leaderboard?limit=10
        Returns top crypto projects by GitHub activity
        """
        leaderboard = chart_api.get_top_projects_leaderboard(limit)
        
        if 'error' in leaderboard:
            return {
                'status': 'error',
                'message': leaderboard['error']
            }
        
        return {
            'status': 'success',
            'data': leaderboard
        }
    
    def api_get_repository_info(self, coin_id: str) -> Dict[str, Any]:
        """
        API: GET /api/repositories/{coin_id}
        Returns repository breakdown for a coin
        """
        repo_info = chart_api.get_repository_breakdown(coin_id)
        
        if 'error' in repo_info:
            return {
                'status': 'error',
                'message': repo_info['error']
            }
        
        return {
            'status': 'success',
            'data': repo_info
        }
    
    # Direct MongoDB query examples (for custom queries)
    
    def api_custom_query_latest_stats(self, coin_id: str) -> Dict[str, Any]:
        """
        Custom MongoDB query example: Get latest stats for a coin
        """
        collection = mongodb_client.get_collection('repo_stats_timeseries')
        
        latest_stats = collection.find_one(
            {'repo.coin_id': coin_id},
            sort=[('timestamp', -1)]
        )
        
        if not latest_stats:
            return {
                'status': 'error',
                'message': f'No data found for coin_id: {coin_id}'
            }
        
        # Convert ObjectId and datetime for JSON serialization
        latest_stats['_id'] = str(latest_stats['_id'])
        latest_stats['timestamp'] = latest_stats['timestamp'].isoformat()
        if latest_stats.get('repo', {}).get('created_at'):
            latest_stats['repo']['created_at'] = latest_stats['repo']['created_at'].isoformat()
        if latest_stats.get('repo', {}).get('updated_at'):
            latest_stats['repo']['updated_at'] = latest_stats['repo']['updated_at'].isoformat()
        
        return {
            'status': 'success',
            'data': latest_stats
        }
    
    def api_custom_query_time_range(self, coin_id: str, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        Custom MongoDB query example: Get data for specific time range
        Usage: api_custom_query_time_range('bitcoin', '2024-01-01', '2024-01-31')
        """
        from datetime import datetime
        
        try:
            start_dt = datetime.fromisoformat(start_date)
            end_dt = datetime.fromisoformat(end_date)
        except ValueError:
            return {
                'status': 'error',
                'message': 'Invalid date format. Use YYYY-MM-DD'
            }
        
        collection = mongodb_client.get_collection('repo_stats_timeseries')
        
        cursor = collection.find(
            {
                'repo.coin_id': coin_id,
                'timestamp': {'$gte': start_dt, '$lte': end_dt}
            },
            {
                'timestamp': 1,
                'repo.owner': 1,
                'repo.name': 1,
                'stats.stars': 1,
                'stats.forks': 1,
                'activity.commits_last_24h': 1
            }
        ).sort('timestamp', 1)
        
        results = []
        for doc in cursor:
            doc['_id'] = str(doc['_id'])
            doc['timestamp'] = doc['timestamp'].isoformat()
            results.append(doc)
        
        return {
            'status': 'success',
            'count': len(results),
            'data': results
        }


def demo_api_calls():
    """Demonstrate API calls with sample data"""
    api = BackendAPIExamples()
    
    print("GitHub Time Series API Demo")
    print("=" * 50)
    
    # 1. Get available coins
    print("\n1. Available Crypto Projects:")
    coins_response = api.api_get_available_coins()
    if coins_response['status'] == 'success':
        for coin in coins_response['data'][:5]:  # Show first 5
            print(f"   - {coin['name']} ({coin['symbol']}) - {coin['coin_id']}")
        print(f"   ... and {len(coins_response['data']) - 5} more")
    
    # 2. Get chart data for Bitcoin (if available)
    available_coins = [coin['coin_id'] for coin in coins_response.get('data', [])]
    if 'bitcoin' in available_coins:
        coin_id = 'bitcoin'
    elif available_coins:
        coin_id = available_coins[0]
    else:
        print("No crypto projects found with GitHub data")
        return
    
    print(f"\n2. Stars Chart Data for {coin_id}:")
    stars_response = api.api_get_stars_chart(coin_id, days=7)
    if stars_response['status'] == 'success':
        data = stars_response['data']
        print(f"   Current stars: {data['summary']['current']:,}")
        print(f"   Change (7d): {data['summary']['change']:+,}")
        print(f"   Chart points: {len(data['chart_data'])}")
    else:
        print(f"   Error: {stars_response.get('message', 'Unknown error')}")
    
    # 3. Get dashboard data
    print(f"\n3. Dashboard Data for {coin_id}:")
    dashboard_response = api.api_get_dashboard_data(coin_id, days=7)
    if dashboard_response['status'] == 'success':
        data = dashboard_response['data']
        print(f"   Project: {data['project_name']} ({data['symbol']})")
        print(f"   Metrics available: {list(data['metrics'].keys())}")
        for metric, summary in data['summary'].items():
            print(f"   {metric}: {summary['current']} ({summary['change']:+})")
    
    # 4. Get leaderboard
    print(f"\n4. GitHub Activity Leaderboard:")
    leaderboard_response = api.api_get_leaderboard(limit=5)
    if leaderboard_response['status'] == 'success':
        for project in leaderboard_response['data']['leaderboard']:
            print(f"   #{project['rank']} {project['project_name']} ({project['symbol']})")
            print(f"       Stars: {project['metrics']['total_stars']:,}")
    
    # 5. Example of chart-ready JSON output
    print(f"\n5. Example JSON Output (Stars Chart):")
    print(json.dumps(stars_response, indent=2))


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Backend API Examples')
    parser.add_argument('--demo', action='store_true', help='Run demo of all API calls')
    parser.add_argument('--coin', help='Test specific coin ID')
    parser.add_argument('--days', type=int, default=7, help='Number of days for charts')
    
    args = parser.parse_args()
    
    if args.demo:
        demo_api_calls()
    elif args.coin:
        api = BackendAPIExamples()
        
        print(f"Testing API calls for {args.coin}:")
        
        # Test stars chart
        response = api.api_get_stars_chart(args.coin, args.days)
        print("\nStars Chart API Response:")
        print(json.dumps(response, indent=2)[:500] + "..." if len(json.dumps(response)) > 500 else json.dumps(response, indent=2))
        
        # Test dashboard
        response = api.api_get_dashboard_data(args.coin, args.days)
        print("\nDashboard API Response:")
        print(json.dumps(response, indent=2)[:500] + "..." if len(json.dumps(response)) > 500 else json.dumps(response, indent=2))
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()