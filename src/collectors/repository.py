from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from github.Repository import Repository
from github.GithubException import UnknownObjectException
from loguru import logger

from src.collectors.base_collector import BaseCollector
from src.config.settings import settings
from src.config.metrics_config import REPO_METRICS, TIME_WINDOWS


class RepositoryStatsCollector(BaseCollector):
    """Collector for repository statistics and metrics"""
    
    def get_collection_name(self) -> str:
        return settings.repo_stats_collection
    
    def collect(self, owner: str, repo_name: str) -> Dict[str, Any]:
        """Collect comprehensive repository statistics"""
        try:
            repo = self.get_repository(owner, repo_name)
            
            # Get previous data for delta calculations
            previous_data = self.get_previous_data({
                'repo.owner': owner,
                'repo.name': repo_name
            })
            
            # Collect basic stats
            basic_stats = self._collect_basic_stats(repo)
            
            # Collect activity metrics
            activity_metrics = self._collect_activity_metrics(repo)
            
            # Calculate deltas if previous data exists
            stats_with_deltas = self._calculate_deltas(basic_stats, previous_data)
            
            # Compile final data structure
            data = {
                'timestamp': datetime.utcnow(),
                'repo': {
                    'owner': owner,
                    'name': repo_name,
                    'id': repo.id,
                    'language': repo.language,
                    'created_at': repo.created_at,
                    'updated_at': repo.updated_at,
                    'description': repo.description,
                    'topics': list(repo.get_topics())
                },
                'stats': stats_with_deltas,
                'activity': activity_metrics
            }
            
            logger.info(f"Collected stats for {owner}/{repo_name}")
            return data
            
        except UnknownObjectException:
            logger.error(f"Repository {owner}/{repo_name} not found")
            raise
        except Exception as e:
            logger.error(f"Error collecting repository stats: {e}")
            raise
    
    def _collect_basic_stats(self, repo: Repository) -> Dict[str, Any]:
        """Collect basic repository statistics"""
        return {
            'stars': repo.stargazers_count,
            'forks': repo.forks_count,
            'watchers': repo.subscribers_count,
            'open_issues': repo.open_issues_count,
            'size_kb': repo.size,
            'network_count': repo.network_count,
            'has_wiki': repo.has_wiki,
            'has_pages': repo.has_pages,
            'has_discussions': repo.has_discussions,
            'archived': repo.archived,
            'disabled': repo.disabled
        }
    
    def _collect_activity_metrics(self, repo: Repository) -> Dict[str, Any]:
        """Collect activity-based metrics"""
        now = datetime.utcnow()
        
        # Get commit activity
        commits_24h = self._count_commits_since(repo, now - timedelta(hours=24))
        commits_7d = self._count_commits_since(repo, now - timedelta(days=7))
        commits_30d = self._count_commits_since(repo, now - timedelta(days=30))
        
        # Get contributor activity
        contributors_7d = self._get_active_contributors(repo, 7)
        contributors_30d = self._get_active_contributors(repo, 30)
        
        # Get PR and issue activity
        pr_stats = self._get_pr_stats(repo)
        issue_stats = self._get_issue_stats(repo)
        
        # Get release information
        latest_release = self._get_latest_release_info(repo)
        
        return {
            'commits_last_24h': commits_24h,
            'commits_last_7d': commits_7d,
            'commits_last_30d': commits_30d,
            'unique_contributors_7d': len(contributors_7d),
            'unique_contributors_30d': len(contributors_30d),
            'top_contributors_7d': contributors_7d[:10],  # Top 10
            **pr_stats,
            **issue_stats,
            **latest_release
        }
    
    def _count_commits_since(self, repo: Repository, since: datetime) -> int:
        """Count commits since a given date"""
        try:
            commits = self._make_api_call(
                repo.get_commits,
                since=since
            )
            # GitHub API returns paginated results, get total count
            return commits.totalCount
        except Exception as e:
            logger.warning(f"Error counting commits: {e}")
            return 0
    
    def _get_active_contributors(self, repo: Repository, days: int) -> List[Dict[str, Any]]:
        """Get active contributors in the last N days"""
        try:
            since = datetime.utcnow() - timedelta(days=days)
            commits = self._make_api_call(
                repo.get_commits,
                since=since
            )
            
            contributor_stats = {}
            for commit in commits[:100]:  # Limit to recent 100 commits
                if commit.author:
                    username = commit.author.login
                    if username not in contributor_stats:
                        contributor_stats[username] = {
                            'username': username,
                            'commits': 0,
                            'additions': 0,
                            'deletions': 0
                        }
                    
                    contributor_stats[username]['commits'] += 1
                    if commit.stats:
                        contributor_stats[username]['additions'] += commit.stats.additions
                        contributor_stats[username]['deletions'] += commit.stats.deletions
            
            # Sort by commit count
            sorted_contributors = sorted(
                contributor_stats.values(),
                key=lambda x: x['commits'],
                reverse=True
            )
            
            return sorted_contributors
            
        except Exception as e:
            logger.warning(f"Error getting active contributors: {e}")
            return []
    
    def _get_pr_stats(self, repo: Repository) -> Dict[str, Any]:
        """Get pull request statistics"""
        try:
            open_prs = self._make_api_call(
                repo.get_pulls,
                state='open'
            ).totalCount
            
            # Get recently closed PRs
            week_ago = datetime.utcnow() - timedelta(days=7)
            closed_prs = self._make_api_call(
                repo.get_pulls,
                state='closed',
                sort='updated',
                direction='desc'
            )
            
            closed_this_week = sum(1 for pr in closed_prs[:50] 
                                 if pr.closed_at and pr.closed_at > week_ago)
            merged_this_week = sum(1 for pr in closed_prs[:50] 
                                 if pr.merged_at and pr.merged_at > week_ago)
            
            return {
                'open_pull_requests': open_prs,
                'prs_closed_7d': closed_this_week,
                'prs_merged_7d': merged_this_week
            }
            
        except Exception as e:
            logger.warning(f"Error getting PR stats: {e}")
            return {
                'open_pull_requests': 0,
                'prs_closed_7d': 0,
                'prs_merged_7d': 0
            }
    
    def _get_issue_stats(self, repo: Repository) -> Dict[str, Any]:
        """Get issue statistics"""
        try:
            # Get issue counts by state
            open_issues = self._make_api_call(
                repo.get_issues,
                state='open'
            ).totalCount
            
            # Get recently closed issues
            week_ago = datetime.utcnow() - timedelta(days=7)
            closed_issues = self._make_api_call(
                repo.get_issues,
                state='closed',
                sort='updated',
                direction='desc'
            )
            
            closed_this_week = sum(1 for issue in closed_issues[:50] 
                                 if issue.closed_at and issue.closed_at > week_ago 
                                 and not issue.pull_request)
            
            # Calculate average resolution time for recent issues
            resolution_times = []
            for issue in closed_issues[:20]:
                if issue.closed_at and issue.created_at and not issue.pull_request:
                    resolution_time = (issue.closed_at - issue.created_at).total_seconds() / 3600  # hours
                    resolution_times.append(resolution_time)
            
            avg_resolution_hours = sum(resolution_times) / len(resolution_times) if resolution_times else 0
            
            return {
                'open_issues_count': open_issues,
                'issues_closed_7d': closed_this_week,
                'avg_issue_resolution_hours': round(avg_resolution_hours, 2)
            }
            
        except Exception as e:
            logger.warning(f"Error getting issue stats: {e}")
            return {
                'open_issues_count': 0,
                'issues_closed_7d': 0,
                'avg_issue_resolution_hours': 0
            }
    
    def _get_latest_release_info(self, repo: Repository) -> Dict[str, Any]:
        """Get information about the latest release"""
        try:
            releases = self._make_api_call(repo.get_releases)
            
            if releases.totalCount == 0:
                return {
                    'has_releases': False,
                    'latest_release_tag': None,
                    'latest_release_date': None,
                    'days_since_last_release': None
                }
            
            latest_release = releases[0]
            days_since = (datetime.utcnow() - latest_release.created_at).days
            
            return {
                'has_releases': True,
                'latest_release_tag': latest_release.tag_name,
                'latest_release_date': latest_release.created_at,
                'days_since_last_release': days_since,
                'total_releases': releases.totalCount
            }
            
        except Exception as e:
            logger.warning(f"Error getting release info: {e}")
            return {
                'has_releases': False,
                'latest_release_tag': None,
                'latest_release_date': None,
                'days_since_last_release': None
            }
    
    def _calculate_deltas(self, current_stats: Dict[str, Any], 
                         previous_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate changes from previous data point"""
        if not previous_data or 'stats' not in previous_data:
            return current_stats
        
        previous_stats = previous_data['stats']
        stats_with_deltas = current_stats.copy()
        
        # Calculate deltas for numeric fields
        delta_fields = ['stars', 'forks', 'watchers', 'open_issues', 'size_kb']
        
        for field in delta_fields:
            if field in current_stats and field in previous_stats:
                current_val = current_stats[field]
                previous_val = previous_stats[field]
                
                stats_with_deltas[f'{field}_change'] = current_val - previous_val
                
                if previous_val > 0:
                    stats_with_deltas[f'{field}_growth_rate'] = (
                        (current_val - previous_val) / previous_val
                    )
        
        return stats_with_deltas
    
    def collect_multiple(self, repos: List[tuple]) -> List[Dict[str, Any]]:
        """Collect stats for multiple repositories"""
        results = []
        
        for owner, repo_name in repos:
            try:
                data = self.collect(owner, repo_name)
                results.append(data)
            except Exception as e:
                logger.error(f"Failed to collect data for {owner}/{repo_name}: {e}")
                continue
        
        return results