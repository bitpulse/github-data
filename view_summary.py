#!/usr/bin/env python3
"""
Simple script to view collected GitHub data summary
"""

from pymongo import MongoClient, DESCENDING
from datetime import datetime, timezone, timedelta
import os
from dotenv import load_dotenv
from collections import defaultdict

# Load environment
load_dotenv()

# MongoDB connection
client = MongoClient(os.getenv('MONGODB_URI', 'mongodb://localhost:27017/'))
db = client[os.getenv('MONGODB_DATABASE', 'github_crypto_analysis')]

def format_number(num):
    """Format large numbers with K/M suffix"""
    if num >= 1_000_000:
        return f"{num/1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num/1_000:.1f}K"
    return str(num)

def view_summary():
    """View summary of collected data"""
    
    print("\n🔍 GitHub Data Collection Summary")
    print("=" * 60)
    
    # Get collection counts
    repo_count = db.repo_stats_timeseries.count_documents({})
    daily_count = db.daily_repo_stats.count_documents({})
    contrib_count = db.github_contributors.count_documents({})
    
    print(f"\n📊 Collection Statistics:")
    print(f"  • Time series data points: {format_number(repo_count)}")
    print(f"  • Daily aggregations: {format_number(daily_count)}")
    print(f"  • Contributors tracked: {format_number(contrib_count)}")
    
    # Get latest data points
    latest = list(db.repo_stats_timeseries.find().sort('timestamp', DESCENDING).limit(10))
    
    if latest:
        print(f"\n⏰ Latest Data Collection:")
        print(f"  • Most recent: {latest[0]['timestamp'].strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
        # Group by coin_id
        coins = defaultdict(list)
        for entry in latest:
            coins[entry['repo']['coin_id']].append(entry)
        
        print(f"  • Projects collected: {len(coins)}")
        
        # Show top projects
        print("\n🏆 Top Projects by Stars:")
        sorted_latest = sorted(latest, key=lambda x: x['stats']['stars'], reverse=True)[:5]
        
        for i, entry in enumerate(sorted_latest, 1):
            repo = entry['repo']
            stats = entry['stats']
            activity = entry['activity']
            
            print(f"\n  {i}. {repo['project_name']} ({repo['symbol']})")
            print(f"     Repository: {repo['owner']}/{repo['name']}")
            print(f"     ⭐ Stars: {format_number(stats['stars'])}")
            print(f"     🍴 Forks: {format_number(stats['forks'])}")
            print(f"     👥 Contributors: {activity.get('total_contributors', 'N/A')}")
            print(f"     💻 Commits (7d): {activity.get('commits_last_7d', 0)}")
    
    # Check data freshness
    now = datetime.now(timezone.utc)
    one_hour_ago = now - timedelta(hours=1)
    recent_count = db.repo_stats_timeseries.count_documents({
        'timestamp': {'$gte': one_hour_ago}
    })
    
    print(f"\n📈 Data Freshness:")
    print(f"  • Data points in last hour: {recent_count}")
    
    if recent_count == 0:
        print("  ⚠️  No recent data collection detected!")
        print("  💡 Run 'python crypto_github_collector_v4.py' to start collecting")
    else:
        print("  ✅ Data collection is active")
    
    # Show collection schedule
    print(f"\n⏱️  Collection Schedule:")
    print(f"  • Interval: Every {os.getenv('COLLECTION_INTERVAL_HOURS', '1')} hour(s)")
    print(f"  • Contributor tracking: {os.getenv('ENABLE_CONTRIBUTOR_TRACKING', 'true')}")
    
    # Show rate limit usage
    if latest:
        print(f"\n🔑 GitHub API Status:")
        print(f"  • Rate limit buffer: {float(os.getenv('RATE_LIMIT_BUFFER', '0.8')) * 100:.0f}%")
        print(f"  • Max requests/hour: {int(5000 * float(os.getenv('RATE_LIMIT_BUFFER', '0.8')))}")
    
    print("\n" + "=" * 60 + "\n")

def view_recent_activity(hours=24):
    """View recent activity across all projects"""
    
    print(f"\n📊 Activity in Last {hours} Hours")
    print("=" * 60)
    
    start_time = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    pipeline = [
        {'$match': {'timestamp': {'$gte': start_time}}},
        {'$group': {
            '_id': '$repo.coin_id',
            'project_name': {'$first': '$repo.project_name'},
            'symbol': {'$first': '$repo.symbol'},
            'total_commits': {'$sum': '$activity.commits_last_24h'},
            'data_points': {'$sum': 1}
        }},
        {'$match': {'total_commits': {'$gt': 0}}},
        {'$sort': {'total_commits': -1}},
        {'$limit': 10}
    ]
    
    active_projects = list(db.repo_stats_timeseries.aggregate(pipeline))
    
    if active_projects:
        print("\n🔥 Most Active Projects:")
        for i, project in enumerate(active_projects, 1):
            print(f"  {i}. {project['project_name']} ({project['symbol']})")
            print(f"     Commits: {project['total_commits']}")
            print(f"     Data points: {project['data_points']}")
    else:
        print("  No activity found in the specified period")
    
    print()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='View GitHub data collection summary')
    parser.add_argument('--activity', type=int, help='Show activity for last N hours')
    
    args = parser.parse_args()
    
    view_summary()
    
    if args.activity:
        view_recent_activity(args.activity)
    
    client.close()