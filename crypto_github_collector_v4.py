#!/usr/bin/env python3
"""
Crypto GitHub Data Collector v4 - Smart Contributor Tracking
Efficiently monitors GitHub repositories and tracks contributors without freezing
"""

import sys
import os
import time
import signal
import json
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Tuple, Optional, Set
from urllib.parse import urlparse
import schedule
from pymongo import MongoClient, ASCENDING, DESCENDING, UpdateOne
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

# Contributor tracking settings
ENABLE_CONTRIBUTOR_TRACKING = os.getenv('ENABLE_CONTRIBUTOR_TRACKING', 'true').lower() == 'true'
MAX_CONTRIBUTORS_PER_REPO = int(os.getenv('MAX_CONTRIBUTORS_PER_REPO', '20'))
CONTRIBUTOR_PROFILE_DEPTH = os.getenv('CONTRIBUTOR_PROFILE_DEPTH', 'basic')  # basic|full
CONTRIBUTOR_CACHE_DAYS = int(os.getenv('CONTRIBUTOR_CACHE_DAYS', '7'))

# Collection names
CRYPTO_COLLECTION = 'crypto_project'
REPO_STATS_COLLECTION = 'github_repo_stats_timeseries'
DAILY_STATS_COLLECTION = 'github_daily_repo_stats'
CONTRIBUTORS_COLLECTION = 'github_contributors'
CONTRIBUTOR_ACTIVITY_COLLECTION = 'github_contributor_activity_timeseries'


class CryptoGitHubCollector:
    """Smart collector with efficient contributor tracking"""
    
    def __init__(self):
        self.running = True
        self.github = Github(GITHUB_TOKEN)
        self.mongo_client = MongoClient(MONGODB_URI)
        self.db = self.mongo_client[MONGODB_DATABASE]
        self.crypto_repositories = []
        self.rate_limit_requests = []
        self.rate_limit_window = timedelta(hours=1)
        self.max_requests = int(5000 * RATE_LIMIT_BUFFER)
        self.failed_repos = set()  # Track failed repositories
        self.contributor_cache_duration = timedelta(days=CONTRIBUTOR_CACHE_DAYS)
        
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
        
        logger.info(f"Contributor tracking: {'ENABLED' if ENABLE_CONTRIBUTOR_TRACKING else 'DISABLED'}")
        if ENABLE_CONTRIBUTOR_TRACKING:
            logger.info(f"Max contributors per repo: {MAX_CONTRIBUTORS_PER_REPO}")
            logger.info(f"Contributor profile depth: {CONTRIBUTOR_PROFILE_DEPTH}")
            logger.info(f"Contributor cache days: {CONTRIBUTOR_CACHE_DAYS}")
    
    def _initialize_collections(self):
        """Initialize MongoDB collections including contributor tracking"""
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
        
        # Create contributor activity time series collection if enabled
        if ENABLE_CONTRIBUTOR_TRACKING and CONTRIBUTOR_ACTIVITY_COLLECTION not in existing_collections:
            try:
                self.db.create_collection(
                    CONTRIBUTOR_ACTIVITY_COLLECTION,
                    timeseries={
                        'timeField': 'timestamp',
                        'metaField': 'contributor',
                        'granularity': 'hours'
                    }
                )
                logger.info(f"Created time series collection: {CONTRIBUTOR_ACTIVITY_COLLECTION}")
            except Exception as e:
                logger.warning(f"Collection might already exist: {e}")
        
        # Create indexes
        repo_collection = self.db[REPO_STATS_COLLECTION]
        repo_collection.create_index([('repo.coin_id', 1), ('timestamp', -1)])
        repo_collection.create_index([('repo.owner', 1), ('repo.name', 1), ('timestamp', -1)])
        
        # Contributor indexes
        if ENABLE_CONTRIBUTOR_TRACKING:
            contrib_collection = self.db[CONTRIBUTORS_COLLECTION]
            contrib_collection.create_index([('username', 1)], unique=True)
            contrib_collection.create_index([('projects', 1)])
            contrib_collection.create_index([('profile_updated', 1)])
            contrib_collection.create_index([('needs_update', 1)])
            
            activity_collection = self.db[CONTRIBUTOR_ACTIVITY_COLLECTION]
            activity_collection.create_index([('contributor.username', 1), ('timestamp', -1)])
            activity_collection.create_index([('contributor.coin_ids', 1), ('timestamp', -1)])
        
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
    
    def _ensure_timezone_aware(self, dt: datetime) -> datetime:
        """Ensure datetime object is timezone-aware"""
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
    
    def _parse_github_url(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        """Parse GitHub URL to extract owner and repository name"""
        try:
            # Handle various GitHub URL formats
            url = url.rstrip('/')
            url = url.rstrip('.git')
            
            # Remove any trailing slashes or extra paths
            if '/tree/' in url or '/blob/' in url:
                url = url.split('/tree/')[0].split('/blob/')[0]
            
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
        """Check and manage rate limiting with better feedback"""
        rate_limit = self.github.get_rate_limit()
        remaining = rate_limit.core.remaining
        reset_time = datetime.fromtimestamp(rate_limit.core.reset.timestamp(), tz=timezone.utc)
        
        # Log rate limit status periodically
        if remaining % 100 == 0 or remaining < 100:
            logger.info(f"Rate limit: {remaining}/{rate_limit.core.limit} remaining")
        
        # If we're getting low, wait
        if remaining < 50:
            wait_seconds = (reset_time - datetime.now(timezone.utc)).total_seconds()
            if wait_seconds > 0:
                logger.warning(f"Low rate limit ({remaining} remaining). Waiting {wait_seconds:.1f} seconds...")
                time.sleep(wait_seconds + 1)
    
    def collect_repository_stats(self, repo_info: Dict) -> Optional[Dict]:
        """Collect statistics for a single repository with smart contributor tracking"""
        owner = repo_info['owner']
        name = repo_info['name']
        repo_key = f"{owner}/{name}"
        
        # Skip if previously failed
        if repo_key in self.failed_repos:
            logger.debug(f"Skipping known failed repo: {repo_key}")
            return None
        
        try:
            self._check_rate_limit()
            
            # Get repository object
            try:
                repo = self.github.get_repo(repo_key)
            except GithubException as e:
                if e.status == 404:
                    logger.warning(f"Repository not found (404): {repo_key}")
                    self.failed_repos.add(repo_key)
                    return None
                elif e.status == 403:
                    logger.warning(f"Access forbidden (403): {repo_key}")
                    self.failed_repos.add(repo_key)
                    return None
                raise
            
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
            now = datetime.now(timezone.utc)
            commits_24h = self._count_commits_since(repo, now - timedelta(hours=24))
            commits_7d = self._count_commits_since(repo, now - timedelta(days=7))
            
            # Get contributor data based on settings
            if ENABLE_CONTRIBUTOR_TRACKING:
                contributor_count = self._get_contributor_count(repo)
                recent_contributors = self._get_active_contributors(repo, 7)
                # Store basic contributor info
                self._store_basic_contributor_info(repo, repo_info['coin_id'], recent_contributors)
            else:
                contributor_count = 0
                recent_contributors = []
            
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
                    'unique_contributors_7d': len(recent_contributors),
                    'total_contributors': contributor_count,
                    'top_contributors_7d': recent_contributors[:10]  # Top 10 recent
                }
            }
            
            logger.info(f"✅ Collected {owner}/{name} ({repo_info['coin_id']}): "
                       f"⭐ {stats['stars']} 🍴 {stats['forks']} "
                       f"💻 {commits_7d} commits/7d 👥 {contributor_count} contributors")
            
            return data
            
        except RateLimitExceededException as e:
            reset_time = datetime.fromtimestamp(e.resettime, tz=timezone.utc)
            wait_seconds = (reset_time - datetime.now(timezone.utc)).total_seconds()
            logger.warning(f"GitHub rate limit hit. Waiting {wait_seconds:.1f} seconds...")
            time.sleep(wait_seconds + 1)
            return self.collect_repository_stats(repo_info)
            
        except Exception as e:
            logger.error(f"Error collecting {owner}/{name}: {e}")
            return None
    
    def _count_commits_since(self, repo, since: datetime) -> int:
        """Count commits since a given date
        
        Uses totalCount for efficiency (single API call).
        Returns actual count, not capped at 100.
        """
        try:
            self._check_rate_limit()
            # Ensure since datetime is timezone-aware
            since = self._ensure_timezone_aware(since)
            commits = repo.get_commits(since=since)
            
            # For recent commits (24h/7d), we can safely use totalCount
            # as it's a single API call for count-only operations
            try:
                # This is efficient - PyGithub only makes one API call for totalCount
                return commits.totalCount
            except Exception:
                # Fallback: count first page only (more efficient than iterating)
                # get_page(0) fetches first page with default 30 items
                first_page = commits.get_page(0)
                return len(list(first_page))
        except Exception:
            return 0
    
    def _get_contributor_count(self, repo) -> int:
        """Get total contributor count without fetching all data"""
        try:
            self._check_rate_limit()
            # Just get the count, not all contributors
            contributors = repo.get_contributors()
            return contributors.totalCount
        except Exception:
            return 0
    
    def _get_active_contributors(self, repo, days: int) -> List[Dict]:
        """Get active contributors in the last N days"""
        try:
            self._check_rate_limit()
            since = datetime.now(timezone.utc) - timedelta(days=days)
            # Ensure since datetime is timezone-aware
            since = self._ensure_timezone_aware(since)
            commits = repo.get_commits(since=since)
            
            contributor_stats = {}
            commit_count = 0
            
            for commit in commits:
                if commit_count >= 50:  # Limit to recent 50 commits
                    break
                commit_count += 1
                
                if commit.author:
                    username = commit.author.login
                    if username not in contributor_stats:
                        contributor_stats[username] = {
                            'username': username,
                            'commits': 0
                        }
                    contributor_stats[username]['commits'] += 1
            
            return sorted(contributor_stats.values(), key=lambda x: x['commits'], reverse=True)
            
        except Exception as e:
            logger.debug(f"Error getting active contributors: {e}")
            return []
    
    def _store_basic_contributor_info(self, repo, coin_id: str, recent_contributors: List[Dict]):
        """Store basic contributor information efficiently"""
        try:
            self._check_rate_limit()
            
            # Get top contributors with more info
            contributors = repo.get_contributors()
            bulk_updates = []
            
            # Process only top contributors
            contributor_count = 0
            for contributor in contributors:
                if contributor_count >= MAX_CONTRIBUTORS_PER_REPO:
                    break
                contributor_count += 1
                
                username = contributor.login
                
                # Check if contributor needs update
                existing = self.db[CONTRIBUTORS_COLLECTION].find_one({'username': username})
                needs_update = True
                
                if existing and 'profile_updated' in existing:
                    last_updated = existing['profile_updated']
                    if isinstance(last_updated, datetime):
                        # Ensure timezone awareness for comparison
                        last_updated = self._ensure_timezone_aware(last_updated)
                        if datetime.now(timezone.utc) - last_updated < self.contributor_cache_duration:
                            needs_update = False
                
                # Basic data always updated
                update_data = {
                    'username': username,
                    'avatar_url': contributor.avatar_url,
                    'profile_url': contributor.html_url,
                    'contributions': contributor.contributions,
                    'last_seen': datetime.now(timezone.utc),
                    'needs_update': needs_update
                }
                
                # If basic profile depth or needs update, get minimal extra info
                if CONTRIBUTOR_PROFILE_DEPTH == 'basic' and needs_update:
                    update_data['profile_updated'] = datetime.now(timezone.utc)
                
                bulk_updates.append(
                    UpdateOne(
                        {'username': username},
                        {
                            '$set': update_data,
                            '$addToSet': {
                                'projects': coin_id,
                                'repositories': f"{repo.owner.login}/{repo.name}"
                            }
                        },
                        upsert=True
                    )
                )
            
            # Bulk update
            if bulk_updates:
                self.db[CONTRIBUTORS_COLLECTION].bulk_write(bulk_updates)
                logger.debug(f"Updated {len(bulk_updates)} contributor records for {repo.owner.login}/{repo.name}")
                
        except Exception as e:
            logger.warning(f"Error storing contributor info: {e}")
    
    def update_contributor_profiles(self, limit: int = 100):
        """Update detailed contributor profiles in a separate process"""
        logger.info(f"Starting contributor profile updates (limit: {limit})")
        
        # Find contributors that need profile updates
        contributors = self.db[CONTRIBUTORS_COLLECTION].find(
            {'needs_update': True},
            sort=[('profile_updated', 1)],
            limit=limit
        )
        
        updated_count = 0
        error_count = 0
        
        for contributor in contributors:
            username = contributor['username']
            
            try:
                self._check_rate_limit()
                
                # Get detailed profile
                user = self.github.get_user(username)
                
                profile_data = {
                    'name': user.name,
                    'company': user.company,
                    'location': user.location,
                    'bio': user.bio,
                    'blog': user.blog,
                    'email': user.email,
                    'hireable': user.hireable,
                    'public_repos': user.public_repos,
                    'public_gists': user.public_gists,
                    'followers': user.followers,
                    'following': user.following,
                    'created_at': self._ensure_timezone_aware(user.created_at),
                    'updated_at': self._ensure_timezone_aware(user.updated_at),
                    'profile_updated': datetime.now(timezone.utc),
                    'needs_update': False
                }
                
                # Update profile
                self.db[CONTRIBUTORS_COLLECTION].update_one(
                    {'username': username},
                    {'$set': profile_data}
                )
                
                updated_count += 1
                logger.info(f"Updated profile for {username} ({updated_count}/{limit})")
                
                # Small delay to be respectful
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error updating profile for {username}: {e}")
                error_count += 1
                
                # Mark as updated anyway to avoid repeated failures
                self.db[CONTRIBUTORS_COLLECTION].update_one(
                    {'username': username},
                    {
                        '$set': {
                            'profile_updated': datetime.now(timezone.utc),
                            'needs_update': False,
                            'profile_error': str(e)
                        }
                    }
                )
        
        logger.info(f"Contributor profile update completed. Updated: {updated_count}, Errors: {error_count}")
    
    def collect_all_repositories(self):
        """Collect data for all repositories"""
        logger.info(f"🚀 Starting collection for {len(self.crypto_repositories)} repositories")
        start_time = datetime.now(timezone.utc)
        
        # Sort repositories by priority
        primary_repos = [r for r in self.crypto_repositories if r['is_primary']]
        secondary_repos = [r for r in self.crypto_repositories if not r['is_primary']]
        
        success_count = 0
        error_count = 0
        
        # Collect primary repositories first
        logger.info(f"📊 Collecting {len(primary_repos)} primary repositories...")
        for i, repo_info in enumerate(primary_repos):
            if not self.running:
                break
            
            # Progress indicator
            if i % 10 == 0:
                logger.info(f"Progress: {i}/{len(primary_repos)} primary repos...")
            
            data = self.collect_repository_stats(repo_info)
            if data:
                self.db[REPO_STATS_COLLECTION].insert_one(data)
                success_count += 1
            else:
                error_count += 1
            
            # Small delay to be respectful
            time.sleep(0.5)
        
        # Check remaining rate limit before secondary repos
        rate_limit = self.github.get_rate_limit()
        remaining = rate_limit.core.remaining
        
        if remaining > 100:
            logger.info(f"📁 Collecting {len(secondary_repos)} secondary repositories...")
            for i, repo_info in enumerate(secondary_repos):
                if not self.running:
                    break
                
                # Progress indicator
                if i % 10 == 0:
                    logger.info(f"Progress: {i}/{len(secondary_repos)} secondary repos...")
                
                # Check rate limit more frequently for secondary repos
                if i % 5 == 0:
                    rate_limit = self.github.get_rate_limit()
                    if rate_limit.core.remaining < 50:
                        logger.warning("Low rate limit, stopping secondary repo collection")
                        break
                
                data = self.collect_repository_stats(repo_info)
                if data:
                    self.db[REPO_STATS_COLLECTION].insert_one(data)
                    success_count += 1
                else:
                    error_count += 1
                
                time.sleep(0.5)
        else:
            logger.warning(f"Skipping secondary repos - low rate limit ({remaining} remaining)")
        
        # Create daily aggregations
        self.create_daily_aggregations()
        
        # Generate contributor summary
        if ENABLE_CONTRIBUTOR_TRACKING:
            self.generate_contributor_summary()
        
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        logger.info(f"✅ Collection completed in {duration:.1f}s. "
                   f"Success: {success_count}, Errors: {error_count}")
        
        if self.failed_repos:
            logger.info(f"Failed repositories ({len(self.failed_repos)}): {list(self.failed_repos)[:5]}...")
        
        # Final rate limit check
        final_rate_limit = self.github.get_rate_limit()
        logger.info(f"Rate limit: {final_rate_limit.core.remaining}/{final_rate_limit.core.limit}")
    
    def create_daily_aggregations(self):
        """Create daily aggregations for chart queries"""
        logger.info("Creating daily aggregations...")
        
        # Get data from last 24 hours
        end_date = datetime.now(timezone.utc)
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
                    'contributors_avg': {'$avg': '$activity.unique_contributors_7d'},
                    'total_contributors': {'$max': '$activity.total_contributors'}
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
                        'avg_contributors_7d': '$contributors_avg',
                        'total_contributors': '$total_contributors'
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
    
    def generate_contributor_summary(self):
        """Generate summary statistics for contributors"""
        try:
            # Get top contributors across all projects
            pipeline = [
                {
                    '$project': {
                        'username': 1,
                        'name': 1,
                        'followers': 1,
                        'public_repos': 1,
                        'projects_count': {'$size': {'$ifNull': ['$projects', []]}},
                        'repos_count': {'$size': {'$ifNull': ['$repositories', []]}},
                        'last_seen': 1
                    }
                },
                {'$sort': {'projects_count': -1, 'followers': -1}},
                {'$limit': 10}
            ]
            
            top_contributors = list(self.db[CONTRIBUTORS_COLLECTION].aggregate(pipeline))
            
            if top_contributors:
                logger.info(f"Top contributor: {top_contributors[0]['username']} "
                           f"({top_contributors[0]['projects_count']} projects)")
                
                # Count total unique contributors
                total_contributors = self.db[CONTRIBUTORS_COLLECTION].count_documents({})
                logger.info(f"Total unique contributors tracked: {total_contributors}")
            
        except Exception as e:
            logger.warning(f"Error generating contributor summary: {e}")
    
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
        description='Crypto GitHub Data Collector v4 - Smart contributor tracking'
    )
    parser.add_argument('--once', action='store_true', help='Run once and exit')
    parser.add_argument('--primary', action='store_true', help='Collect primary repositories only')
    parser.add_argument('--list', action='store_true', help='List repositories that will be monitored')
    parser.add_argument('--update-contributors', action='store_true', 
                        help='Update detailed contributor profiles (separate process)')
    parser.add_argument('--contributor-limit', type=int, default=100,
                        help='Number of contributor profiles to update (default: 100)')
    
    args = parser.parse_args()
    
    # Create collector
    collector = CryptoGitHubCollector()
    
    if args.list:
        collector.list_repositories()
    elif args.update_contributors:
        # Run contributor profile updates only
        collector.update_contributor_profiles(limit=args.contributor_limit)
    elif args.once or args.primary:
        collector.run_once(primary_only=args.primary)
    else:
        # Default: continuous collection
        collector.run_continuous()


if __name__ == "__main__":
    main()