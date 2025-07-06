#!/usr/bin/env python3
"""
Example script to view collected GitHub data
"""

import sys
from datetime import datetime, timedelta
from tabulate import tabulate
from loguru import logger

# Add parent directory to path
sys.path.append('..')

from src.config.settings import settings
from src.storage.mongodb_client import mongodb_client
from src.storage.timeseries_ops import TimeSeriesOperations


def view_latest_repo_stats(owner: str, repo_name: str):
    """View the latest statistics for a repository"""
    mongodb_client.connect()
    
    # Get latest stats
    latest = mongodb_client.get_latest_stats(owner, repo_name)
    
    if not latest:
        print(f"No data found for {owner}/{repo_name}")
        return
    
    print(f"\n=== Latest Stats for {owner}/{repo_name} ===")
    print(f"Timestamp: {latest['timestamp']}")
    
    # Basic stats
    stats = latest['stats']
    print(f"\nBasic Statistics:")
    print(f"  Stars: {stats['stars']:,} ({stats.get('stars_change', 0):+d})")
    print(f"  Forks: {stats['forks']:,} ({stats.get('forks_change', 0):+d})")
    print(f"  Watchers: {stats['watchers']:,} ({stats.get('watchers_change', 0):+d})")
    print(f"  Open Issues: {stats['open_issues']:,} ({stats.get('open_issues_change', 0):+d})")
    
    # Activity metrics
    activity = latest['activity']
    print(f"\nActivity Metrics:")
    print(f"  Commits (24h): {activity['commits_last_24h']}")
    print(f"  Commits (7d): {activity['commits_last_7d']}")
    print(f"  Contributors (7d): {activity['unique_contributors_7d']}")
    print(f"  PRs merged (7d): {activity['prs_merged_7d']}")
    
    # Top contributors
    if activity.get('top_contributors_7d'):
        print(f"\nTop Contributors (7 days):")
        contributors_data = [
            [c['username'], c['commits'], c['additions'], c['deletions']]
            for c in activity['top_contributors_7d'][:5]
        ]
        print(tabulate(
            contributors_data,
            headers=['Username', 'Commits', 'Additions', 'Deletions'],
            tablefmt='grid'
        ))


def view_growth_trends(owner: str, repo_name: str, days: int = 7):
    """View growth trends for a repository"""
    mongodb_client.connect()
    ts_ops = TimeSeriesOperations()
    
    # Get star growth trends
    trends = ts_ops.get_growth_trends(
        settings.repo_stats_collection,
        owner,
        repo_name,
        'stars',
        days
    )
    
    if not trends:
        print(f"No trend data available for {owner}/{repo_name}")
        return
    
    print(f"\n=== Growth Trends for {owner}/{repo_name} (last {days} days) ===")
    print(f"Total Growth Rate: {trends['total_growth_rate']:.2%}")
    print(f"Average Daily Growth: {trends['average_daily_growth']:.2%}")
    print(f"Trend Direction: {trends['trend_direction']}")
    print(f"Volatility: {trends['volatility']:.2%}")


def view_all_projects_summary():
    """View a summary of all monitored projects"""
    mongodb_client.connect()
    collection = mongodb_client.get_collection(settings.repo_stats_collection)
    
    # Get latest data for each unique repository
    pipeline = [
        {'$sort': {'timestamp': -1}},
        {
            '$group': {
                '_id': {'owner': '$repo.owner', 'name': '$repo.name'},
                'latest': {'$first': '$$ROOT'}
            }
        },
        {'$replaceRoot': {'newRoot': '$latest'}},
        {'$sort': {'stats.stars': -1}}
    ]
    
    results = list(collection.aggregate(pipeline))
    
    if not results:
        print("No data collected yet")
        return
    
    print("\n=== All Monitored Projects Summary ===")
    
    table_data = []
    for doc in results[:20]:  # Top 20 by stars
        repo = doc['repo']
        stats = doc['stats']
        activity = doc['activity']
        
        table_data.append([
            f"{repo['owner']}/{repo['name']}",
            f"{stats['stars']:,}",
            f"{stats.get('stars_change', 0):+d}",
            f"{activity['commits_last_7d']}",
            f"{activity['unique_contributors_7d']}",
            repo.get('language', 'N/A')
        ])
    
    print(tabulate(
        table_data,
        headers=['Repository', 'Stars', 'Change', 'Commits(7d)', 'Contributors(7d)', 'Language'],
        tablefmt='grid'
    ))


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='View collected GitHub data')
    parser.add_argument('--repo', help='Repository in format owner/name')
    parser.add_argument('--trends', action='store_true', help='Show growth trends')
    parser.add_argument('--summary', action='store_true', help='Show all projects summary')
    parser.add_argument('--days', type=int, default=7, help='Days for trend analysis')
    
    args = parser.parse_args()
    
    if args.summary:
        view_all_projects_summary()
    elif args.repo:
        owner, name = args.repo.split('/')
        if args.trends:
            view_growth_trends(owner, name, args.days)
        else:
            view_latest_repo_stats(owner, name)
    else:
        parser.print_help()
    
    mongodb_client.close()


if __name__ == "__main__":
    # Need to install tabulate for nice table formatting
    try:
        import tabulate
    except ImportError:
        print("Please install tabulate: pip install tabulate")
        sys.exit(1)
    
    main()