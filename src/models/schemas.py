from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator


class RepoMetadata(BaseModel):
    """Repository metadata"""
    owner: str
    name: str
    id: int
    language: Optional[str]
    created_at: datetime
    updated_at: datetime
    description: Optional[str]
    topics: List[str] = Field(default_factory=list)


class RepoStats(BaseModel):
    """Repository statistics with change tracking"""
    # Basic stats
    stars: int
    stars_change: Optional[int] = None
    stars_growth_rate: Optional[float] = None
    
    forks: int
    forks_change: Optional[int] = None
    forks_growth_rate: Optional[float] = None
    
    watchers: int
    watchers_change: Optional[int] = None
    watchers_growth_rate: Optional[float] = None
    
    open_issues: int
    open_issues_change: Optional[int] = None
    open_issues_growth_rate: Optional[float] = None
    
    size_kb: int
    size_kb_change: Optional[int] = None
    
    # Additional stats
    network_count: int
    has_wiki: bool
    has_pages: bool
    has_discussions: bool
    archived: bool
    disabled: bool


class ContributorInfo(BaseModel):
    """Contributor information"""
    username: str
    commits: int
    additions: int
    deletions: int


class RepoActivity(BaseModel):
    """Repository activity metrics"""
    # Commit activity
    commits_last_24h: int
    commits_last_7d: int
    commits_last_30d: int
    
    # Contributor activity
    unique_contributors_7d: int
    unique_contributors_30d: int
    top_contributors_7d: List[ContributorInfo] = Field(default_factory=list)
    
    # PR activity
    open_pull_requests: int
    prs_closed_7d: int
    prs_merged_7d: int
    
    # Issue activity
    open_issues_count: int
    issues_closed_7d: int
    avg_issue_resolution_hours: float
    
    # Release info
    has_releases: bool
    latest_release_tag: Optional[str]
    latest_release_date: Optional[datetime]
    days_since_last_release: Optional[int]
    total_releases: Optional[int]


class RepoStatsDocument(BaseModel):
    """Complete repository stats document for time series"""
    timestamp: datetime
    repo: RepoMetadata
    stats: RepoStats
    activity: RepoActivity
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ContributorMetadata(BaseModel):
    """Contributor metadata"""
    username: str
    id: int
    repos: List[str] = Field(default_factory=list)
    type: str = 'User'


class ContributorStats(BaseModel):
    """Contributor statistics"""
    total_commits: int
    commits_change: Optional[int] = None
    
    followers: int
    followers_change: Optional[int] = None
    
    following: int
    public_repos: int
    contribution_streak: int  # days
    
    # Calculated metrics
    influence_score: Optional[float] = None


class ContributorActivity(BaseModel):
    """Contributor activity metrics"""
    commits_today: int
    prs_opened: int
    prs_merged: int
    issues_opened: int
    issues_closed: int
    reviews: int
    repos_contributed: List[str] = Field(default_factory=list)


class ContributorActivityDocument(BaseModel):
    """Complete contributor activity document for time series"""
    timestamp: datetime
    contributor: ContributorMetadata
    stats: ContributorStats
    activity: ContributorActivity
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ReleaseInfo(BaseModel):
    """Release information"""
    version: str
    tag_name: str
    release_date: datetime
    is_prerelease: bool
    download_count: int
    body: Optional[str]


class MilestoneInfo(BaseModel):
    """Milestone information"""
    title: str
    state: str  # 'open' or 'closed'
    due_date: Optional[datetime]
    completion_percentage: float
    open_issues: int
    closed_issues: int


class ReleaseMilestoneDocument(BaseModel):
    """Release and milestone tracking document"""
    timestamp: datetime
    repo: Dict[str, str]  # owner and name
    releases: Dict[str, Any]
    milestones: Dict[str, Any]
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# Aggregation result models
class TrendAnalysis(BaseModel):
    """Trend analysis results"""
    metric: str
    period_days: int
    trend_direction: str  # 'increasing', 'decreasing', 'stable'
    growth_rate: float
    volatility: float
    confidence: float
    data_points: int


class AnomalyDetection(BaseModel):
    """Anomaly detection results"""
    metric: str
    timestamp: datetime
    value: float
    expected_value: float
    z_score: float
    severity: str  # 'low', 'medium', 'high'


class ProjectHealth(BaseModel):
    """Overall project health score"""
    repo_owner: str
    repo_name: str
    timestamp: datetime
    
    # Component scores (0-100)
    development_activity_score: float
    community_engagement_score: float
    maintenance_score: float
    sustainability_score: float
    
    # Overall health (0-100)
    overall_health_score: float
    health_trend: str  # 'improving', 'declining', 'stable'
    
    # Risk indicators
    risk_factors: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    
    @validator('overall_health_score')
    def validate_score(cls, v):
        if not 0 <= v <= 100:
            raise ValueError('Score must be between 0 and 100')
        return v