from typing import List, Dict, Any
from datetime import timedelta

# Repository metrics to collect
REPO_METRICS = {
    'basic_stats': [
        'stargazers_count',
        'forks_count',
        'watchers_count',
        'open_issues_count',
        'size',
        'subscribers_count'
    ],
    'activity_metrics': [
        'commits_count',
        'contributors_count',
        'pull_requests_count',
        'issues_count',
        'releases_count'
    ],
    'calculated_metrics': [
        'star_growth_rate',
        'fork_growth_rate',
        'commit_velocity',
        'contributor_retention',
        'issue_resolution_rate'
    ]
}

# User/Contributor metrics to collect
CONTRIBUTOR_METRICS = {
    'profile_stats': [
        'followers',
        'following',
        'public_repos',
        'public_gists',
        'created_at'
    ],
    'activity_metrics': [
        'contributions',
        'commits',
        'pull_requests',
        'issues',
        'reviews'
    ]
}

# Time windows for analysis
TIME_WINDOWS = {
    'hourly': timedelta(hours=1),
    'daily': timedelta(days=1),
    'weekly': timedelta(days=7),
    'monthly': timedelta(days=30),
    'quarterly': timedelta(days=90)
}

# Metrics that should trigger alerts
ALERT_THRESHOLDS = {
    'star_growth_daily': {
        'min': 0.1,  # 10% growth
        'max': 10.0  # 1000% growth (might indicate manipulation)
    },
    'contributor_churn_weekly': {
        'max': 0.5  # 50% contributor loss
    },
    'commit_velocity_drop': {
        'max': 0.7  # 70% drop in commits
    },
    'issue_backlog_growth': {
        'max': 1.5  # 150% growth in open issues
    }
}

# Aggregation pipelines
AGGREGATION_CONFIGS = {
    'moving_averages': [7, 30, 90],  # days
    'growth_calculations': ['linear', 'exponential'],
    'trend_detection': {
        'min_data_points': 7,
        'confidence_threshold': 0.8
    }
}

# Crypto-specific metrics
CRYPTO_PROJECT_METRICS = {
    'development_activity': [
        'commit_frequency',
        'release_cadence',
        'contributor_diversity',
        'code_review_ratio'
    ],
    'community_health': [
        'issue_response_time',
        'pr_merge_time',
        'community_contributors_ratio',
        'discussion_activity'
    ],
    'sustainability_indicators': [
        'bus_factor',  # Number of key contributors
        'contributor_retention_rate',
        'funding_diversity',
        'fork_activity'
    ]
}

def get_metrics_for_collection(collection_type: str) -> List[str]:
    """Get metrics list for a specific collection type"""
    if collection_type == 'repository':
        return REPO_METRICS['basic_stats'] + REPO_METRICS['activity_metrics']
    elif collection_type == 'contributor':
        return CONTRIBUTOR_METRICS['profile_stats'] + CONTRIBUTOR_METRICS['activity_metrics']
    else:
        return []

def get_alert_config(metric_name: str) -> Dict[str, Any]:
    """Get alert configuration for a specific metric"""
    return ALERT_THRESHOLDS.get(metric_name, {})