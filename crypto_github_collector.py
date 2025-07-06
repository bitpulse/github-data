#!/usr/bin/env python3
"""
Crypto GitHub Data Collector - All-in-One Continuous Collection
Monitors GitHub repositories linked to your crypto projects and stores time series data for charts
"""

import sys
import os
import time
import signal
import json
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from urllib.parse import urlparse
import schedule
from pymongo import MongoClient, ASCENDING, DESCENDING
from github import Github, GithubException, RateLimitExceededException
from loguru import logger
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
MONGODB_DATABASE = os.getenv('MONGODB_DATABASE', 'github_crypto_analysis')
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
COLLECTION_INTERVAL_HOURS = int(os.getenv('COLLECTION_INTERVAL_HOURS', '1'))
RATE_LIMIT_BUFFER = float(os.getenv('RATE_LIMIT_BUFFER', '0.8'))
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Collection names
CRYPTO_COLLECTION = 'crypto_project'
REPO_STATS_COLLECTION = 'repo_stats_timeseries'
DAILY_STATS_COLLECTION = 'daily_repo_stats'


class CryptoGitHubCollector:
    """All-in-one collector for crypto project GitHub data"""
    
    def __init__(self):
        self.running = True
        self.github = Github(GITHUB_TOKEN)
        self.mongo_client = MongoClient(MONGODB_URI)
        self.db = self.mongo_client[MONGODB_DATABASE]
        self.crypto_repositories = []
        self.rate_limit_requests = []
        self.rate_limit_window = timedelta(hours=1)
        self.max_requests = int(5000 * RATE_LIMIT_BUFFER)
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Initialize
        self._setup_logging()
        self._verify_setup()
        self._initialize_collections()
        self._load_crypto_repositories()
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
    
    def _setup_logging(self):
        """Configure logging"""
        logger.remove()
        logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
            level=LOG_LEVEL
        )
        
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        logger.add(
            f"{log_dir}/crypto_github_collector.log",
            rotation="10 MB",
            retention="7 days",
            level=LOG_LEVEL
        )
    
    def _verify_setup(self):
        """Verify configuration and connections"""
        if not GITHUB_TOKEN or GITHUB_TOKEN == 'your_github_personal_access_token_here':
            logger.error("Please set GITHUB_TOKEN in your .env file")
            sys.exit(1)
        
        # Test MongoDB connection
        try:
            self.mongo_client.admin.command('ping')
            logger.info(f"Connected to MongoDB at {MONGODB_URI}")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            sys.exit(1)
        
        # Test GitHub connection
        try:
            rate_limit = self.github.get_rate_limit()
            logger.info(f"GitHub API connected. Rate limit: {rate_limit.core.remaining}/{rate_limit.core.limit}")
        except Exception as e:
            logger.error(f"Failed to connect to GitHub API: {e}")
            sys.exit(1)
    
    def _initialize_collections(self):
        """Initialize MongoDB time series collections"""
        existing_collections = self.db.list_collection_names()
        
        # Create repo stats time series collection
        if REPO_STATS_COLLECTION not in existing_collections:
            try:
                self.db.create_collection(
                    REPO_STATS_COLLECTION,
                    timeseries={
                        'timeField': 'timestamp',
                        'metaField': 'repo',
                        'granularity': 'hours'
                    }
                )
                logger.info(f"Created time series collection: {REPO_STATS_COLLECTION}")
            except Exception as e:
                logger.warning(f"Collection might already exist: {e}")
        
        # Create indexes
        repo_collection = self.db[REPO_STATS_COLLECTION]
        repo_collection.create_index([('repo.coin_id', 1), ('timestamp', -1)])
        repo_collection.create_index([('repo.owner', 1), ('repo.name', 1), ('timestamp', -1)])
        logger.info("Database collections ready")
    
    def _load_crypto_repositories(self):
        """Load repositories from crypto_project collection"""
        crypto_collection = self.db[CRYPTO_COLLECTION]
        
        projects = crypto_collection.find({}, {
            'coin_id': 1,
            'basic_info.name': 1,
            'basic_info.symbol': 1,
            'links.repos_url.github': 1
        })
        
        repo_count = 0
        project_count = 0
        
        for project in projects:
            coin_id = project.get('coin_id')
            if not coin_id:
                continue
            
            repos_info = project.get('links', {}).get('repos_url', {}).get('github', [])
            if not repos_info:
                continue
            
            project_count += 1
            basic_info = project.get('basic_info', {})
            
            for i, repo_url in enumerate(repos_info):
                if not repo_url or not repo_url.startswith('https://github.com/'):
                    continue
                
                owner, repo_name = self._parse_github_url(repo_url)
                if owner and repo_name:
                    self.crypto_repositories.append({
                        'owner': owner,
                        'name': repo_name,
                        'coin_id': coin_id,
                        'project_name': basic_info.get('name', coin_id),
                        'symbol': basic_info.get('symbol', '').upper(),
                        'is_primary': i == 0,
                        'priority': 'primary' if i == 0 else 'secondary'
                    })
                    repo_count += 1
        
        if not self.crypto_repositories:
            logger.error("No GitHub repositories found in crypto_project collection")
            sys.exit(1)
        
        logger.info(f"Loaded {repo_count} repositories from {project_count} crypto projects")
        primary_count = sum(1 for r in self.crypto_repositories if r['is_primary'])
        logger.info(f"Primary repositories: {primary_count}, Secondary: {repo_count - primary_count}")
    
    def _parse_github_url(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        """Parse GitHub URL to extract owner and repository name"""
        try:
            url = url.rstrip('.git')
            parsed = urlparse(url)
            if parsed.netloc != 'github.com':
                return None, None
            
            path_parts = parsed.path.strip('/').split('/')
            if len(path_parts) >= 2:
                return path_parts[0], path_parts[1]
        except Exception:
            pass
        return None, None
    
    def _check_rate_limit(self):
        """Check and manage rate limiting"""
        now = datetime.utcnow()
        
        # Remove old requests outside the window
        self.rate_limit_requests = [req_time for req_time in self.rate_limit_requests 
                                   if now - req_time < self.rate_limit_window]
        
        if len(self.rate_limit_requests) >= self.max_requests:
            oldest_request = min(self.rate_limit_requests)
            wait_until = oldest_request + self.rate_limit_window
            wait_seconds = (wait_until - now).total_seconds()
            
            if wait_seconds > 0:
                logger.warning(f"Rate limit reached. Waiting {wait_seconds:.1f} seconds...")
                time.sleep(wait_seconds)
        
        self.rate_limit_requests.append(now)
    
    def collect_repository_stats(self, repo_info: Dict) -> Optional[Dict]:
        """Collect statistics for a single repository"""
        owner = repo_info['owner']
        name = repo_info['name']
        
        try:
            self._check_rate_limit()
            
            # Get repository object
            repo = self.github.get_repo(f"{owner}/{name}")
            
            # Get previous data for delta calculations
            previous = self.db[REPO_STATS_COLLECTION].find_one(
                {'repo.owner': owner, 'repo.name': name},
                sort=[('timestamp', -1)]
            )
            
            # Collect basic stats
            stats = {
                'stars': repo.stargazers_count,
                'forks': repo.forks_count,
                'watchers': repo.subscribers_count,
                'open_issues': repo.open_issues_count,
                'size_kb': repo.size,
                'network_count': repo.network_count
            }
            
            # Calculate deltas if previous data exists
            if previous and 'stats' in previous:
                for key in ['stars', 'forks', 'watchers', 'open_issues']:
                    if key in stats and key in previous['stats']:
                        stats[f'{key}_change'] = stats[key] - previous['stats'][key]
                        if previous['stats'][key] > 0:
                            stats[f'{key}_growth_rate'] = stats[f'{key}_change'] / previous['stats'][key]
            
            # Collect activity metrics
            now = datetime.utcnow()
            commits_24h = self._count_commits_since(repo, now - timedelta(hours=24))
            commits_7d = self._count_commits_since(repo, now - timedelta(days=7))
            contributors_7d = self._get_active_contributors(repo, 7)
            
            # Compile data
            data = {
                'timestamp': now,
                'repo': {
                    'owner': owner,
                    'name': name,
                    'coin_id': repo_info['coin_id'],
                    'project_name': repo_info['project_name'],
                    'symbol': repo_info['symbol'],
                    'is_primary_repo': repo_info['is_primary'],
                    'repo_priority': repo_info['priority'],
                    'language': repo.language,
                    'description': repo.description
                },
                'stats': stats,
                'activity': {
                    'commits_last_24h': commits_24h,
                    'commits_last_7d': commits_7d,
                    'unique_contributors_7d': len(contributors_7d),
                    'top_contributors_7d': contributors_7d[:5]  # Top 5
                }
            }
            
            logger.info(f"✅ Collected {owner}/{name} ({repo_info['coin_id']}): "
                       f"⭐ {stats['stars']} 🍴 {stats['forks']} 💻 {commits_7d} commits/7d")
            
            return data
            
        except RateLimitExceededException as e:
            reset_time = datetime.fromtimestamp(e.resettime)
            wait_seconds = (reset_time - datetime.utcnow()).total_seconds()
            logger.warning(f"GitHub rate limit hit. Waiting {wait_seconds:.1f} seconds...")
            time.sleep(wait_seconds + 1)
            return self.collect_repository_stats(repo_info)
            
        except Exception as e:
            logger.error(f"Error collecting {owner}/{name}: {e}")
            return None
    
    def _count_commits_since(self, repo, since: datetime) -> int:
        """Count commits since a given date"""
        try:
            self._check_rate_limit()
            commits = repo.get_commits(since=since)
            return commits.totalCount
        except Exception:
            return 0
    
    def _get_active_contributors(self, repo, days: int) -> List[Dict]:
        """Get active contributors in the last N days"""
        try:
            self._check_rate_limit()
            since = datetime.utcnow() - timedelta(days=days)
            commits = repo.get_commits(since=since)
            
            contributor_stats = {}
            for commit in commits[:50]:  # Limit to recent 50
                if commit.author:
                    username = commit.author.login
                    if username not in contributor_stats:
                        contributor_stats[username] = {'username': username, 'commits': 0}
                    contributor_stats[username]['commits'] += 1
            
            return sorted(contributor_stats.values(), key=lambda x: x['commits'], reverse=True)
            
        except Exception:
            return []
    
    def collect_all_repositories(self):
        """Collect data for all repositories"""
        logger.info(f"🚀 Starting collection for {len(self.crypto_repositories)} repositories")
        start_time = datetime.utcnow()
        
        # Sort repositories by priority
        primary_repos = [r for r in self.crypto_repositories if r['is_primary']]
        secondary_repos = [r for r in self.crypto_repositories if not r['is_primary']]
        
        success_count = 0
        error_count = 0
        
        # Collect primary repositories first
        logger.info(f"📊 Collecting {len(primary_repos)} primary repositories...")
        for repo_info in primary_repos:
            if not self.running:
                break
            
            data = self.collect_repository_stats(repo_info)
            if data:
                self.db[REPO_STATS_COLLECTION].insert_one(data)
                success_count += 1
            else:
                error_count += 1
            
            time.sleep(1)  # Be respectful
        
        # Check remaining rate limit before secondary repos
        rate_limit = self.github.get_rate_limit()
        remaining = rate_limit.core.remaining
        
        if remaining > len(secondary_repos) + 100:
            logger.info(f"📁 Collecting {len(secondary_repos)} secondary repositories...")
            for repo_info in secondary_repos:
                if not self.running:
                    break
                
                data = self.collect_repository_stats(repo_info)
                if data:
                    self.db[REPO_STATS_COLLECTION].insert_one(data)
                    success_count += 1
                else:
                    error_count += 1
                
                time.sleep(1)
        else:
            logger.warning(f"Skipping secondary repos - low rate limit ({remaining} remaining)")
        
        # Create daily aggregations
        self.create_daily_aggregations()
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.info(f"✅ Collection completed in {duration:.1f}s. "
                   f"Success: {success_count}, Errors: {error_count}")
        
        # Final rate limit check
        final_rate_limit = self.github.get_rate_limit()
        logger.info(f"Rate limit: {final_rate_limit.core.remaining}/{final_rate_limit.core.limit}")
    
    def create_daily_aggregations(self):
        """Create daily aggregations for chart queries"""
        logger.info("Creating daily aggregations...")
        
        # Get data from last 24 hours
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=1)
        
        pipeline = [
            {
                '$match': {
                    'timestamp': {'$gte': start_date, '$lte': end_date},
                    'repo.coin_id': {'$exists': True}
                }
            },
            {
                '$group': {
                    '_id': {
                        'date': {'$dateToString': {'format': '%Y-%m-%d', 'date': '$timestamp'}},
                        'coin_id': '$repo.coin_id',
                        'repo_key': {'$concat': ['$repo.owner', '/', '$repo.name']}
                    },
                    'repo_info': {'$first': '$repo'},
                    'stars_data': {'$push': '$stats.stars'},
                    'forks_data': {'$push': '$stats.forks'},
                    'commits_max': {'$max': '$activity.commits_last_24h'},
                    'contributors_avg': {'$avg': '$activity.unique_contributors_7d'}
                }
            },
            {
                '$project': {
                    '_id': {'$concat': ['$_id.coin_id', '_', '$_id.repo_key', '_', '$_id.date']},
                    'date': '$_id.date',
                    'coin_id': '$_id.coin_id',
                    'repo_key': '$_id.repo_key',
                    'repo_info': 1,
                    'metrics': {
                        'stars_start': {'$arrayElemAt': ['$stars_data', 0]},
                        'stars_end': {'$arrayElemAt': ['$stars_data', -1]},
                        'forks_start': {'$arrayElemAt': ['$forks_data', 0]},
                        'forks_end': {'$arrayElemAt': ['$forks_data', -1]},
                        'max_commits_24h': '$commits_max',
                        'avg_contributors_7d': '$contributors_avg'
                    },
                    'timestamp': {'$dateFromString': {'dateString': '$_id.date'}}
                }
            }
        ]
        
        results = list(self.db[REPO_STATS_COLLECTION].aggregate(pipeline))
        
        if results:
            # Upsert daily aggregations
            daily_collection = self.db[DAILY_STATS_COLLECTION]
            for doc in results:
                daily_collection.replace_one({'_id': doc['_id']}, doc, upsert=True)
            
            logger.info(f"Created {len(results)} daily aggregation records")
    
    def run_continuous(self):
        """Run continuous collection"""
        logger.info("🚀 Starting continuous GitHub data collection")
        logger.info(f"Collection interval: {COLLECTION_INTERVAL_HOURS} hour(s)")
        
        # Schedule collection
        schedule.every(COLLECTION_INTERVAL_HOURS).hours.do(self.collect_all_repositories)
        
        # Run once immediately
        self.collect_all_repositories()
        
        # Keep running
        while self.running:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
        
        logger.info("Shutting down...")
        self.mongo_client.close()
    
    def run_once(self, primary_only: bool = False):
        """Run collection once and exit"""
        if primary_only:
            logger.info("Running one-time collection (primary repositories only)")
            self.crypto_repositories = [r for r in self.crypto_repositories if r['is_primary']]
        else:
            logger.info("Running one-time collection (all repositories)")
        
        self.collect_all_repositories()
        self.mongo_client.close()
    
    def list_repositories(self):
        """List repositories that will be monitored"""
        print(f"\n{'='*80}")
        print(f"CRYPTO GITHUB REPOSITORIES ({len(self.crypto_repositories)} total)")
        print(f"{'='*80}\n")
        
        # Group by coin_id
        by_coin = {}
        for repo in self.crypto_repositories:
            coin_id = repo['coin_id']
            if coin_id not in by_coin:
                by_coin[coin_id] = {
                    'project_name': repo['project_name'],
                    'symbol': repo['symbol'],
                    'repos': []
                }
            by_coin[coin_id]['repos'].append(repo)
        
        # Display
        for coin_id, data in sorted(by_coin.items()):
            print(f"🪙 {data['project_name']} ({data['symbol']}) - {coin_id}")
            for repo in data['repos']:
                emoji = "🔥" if repo['is_primary'] else "📁"
                print(f"   {emoji} {repo['owner']}/{repo['name']} ({repo['priority']})")
            print()
        
        # Summary
        primary_count = sum(1 for r in self.crypto_repositories if r['is_primary'])
        print(f"{'='*80}")
        print(f"SUMMARY: {len(by_coin)} projects, {len(self.crypto_repositories)} repositories")
        print(f"Primary: {primary_count}, Secondary: {len(self.crypto_repositories) - primary_count}")
        print(f"{'='*80}\n")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Crypto GitHub Data Collector - Continuous monitoring for chart data'
    )
    parser.add_argument('--once', action='store_true', help='Run once and exit')
    parser.add_argument('--primary', action='store_true', help='Collect primary repositories only')
    parser.add_argument('--list', action='store_true', help='List repositories that will be monitored')
    
    args = parser.parse_args()
    
    # Create collector
    collector = CryptoGitHubCollector()
    
    if args.list:
        collector.list_repositories()
    elif args.once or args.primary:
        collector.run_once(primary_only=args.primary)
    else:
        # Default: continuous collection
        collector.run_continuous()


if __name__ == "__main__":
    main()