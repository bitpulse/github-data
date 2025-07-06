# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Docker-based GitHub data collector for cryptocurrency projects. It monitors GitHub repositories of crypto projects, collecting time series data for analysis and charting. The system integrates with an existing `crypto_project` MongoDB collection to automatically discover repositories and track development activity.

### Key Features

- **Automatic Repository Discovery**: Extracts GitHub repos from `crypto_project` collection
- **Time Series Storage**: MongoDB collections optimized for temporal queries  
- **Smart Contributor Tracking**: Two-phase approach to avoid rate limit issues
- **Change Tracking**: Calculates deltas between data points for trend analysis
- **Chart-Ready Data**: Pre-formatted for direct frontend consumption
- **Docker Deployment**: Simple deployment with `./deploy.sh`
- **Continuous Monitoring**: Runs hourly by default (configurable)

## Current Architecture

### Simplified Docker Setup

```
github-data/
├── crypto_github_collector_v4.py  # Main collector (V4 with smart contributor tracking)
├── Dockerfile                     # Python 3.11 slim container
├── docker-compose.yml             # Service configuration
├── deploy.sh                      # One-command deployment
├── .env.example                   # Configuration template
├── requirements.txt               # Python dependencies
├── view_summary.py               # View collected data
└── Documentation/
    ├── README.md                 # Main documentation (Docker-focused)
    ├── EC2_DOCKER_SETUP.md      # EC2 deployment guide
    ├── BACKEND_API_GUIDE.md     # API implementation examples
    ├── API_QUICK_REFERENCE.md   # Quick API reference
    └── CHART_INTEGRATION.md     # Chart data integration guide
```

## Deployment

### Quick Start (Docker)

```bash
# 1. Configure
cp .env.example .env
# Edit .env with credentials

# 2. Deploy
./deploy.sh
```

### Environment Variables

```env
# Required
GITHUB_TOKEN=your_github_token
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net
MONGODB_DATABASE=github_crypto_analysis

# Optional  
COLLECTION_INTERVAL_HOURS=1
ENABLE_CONTRIBUTOR_TRACKING=true
MAX_CONTRIBUTORS_PER_REPO=50
```

## Data Collection

### V4 Collector Features

1. **Smart Rate Limiting**: Uses 80% of GitHub API quota efficiently
2. **Two-Phase Contributor Tracking**:
   - Phase 1: Basic contributor data during main collection
   - Phase 2: Detailed profiles via `--update-contributors`
3. **Timezone-Aware**: All datetime comparisons handle timezones correctly
4. **Efficient Commit Counting**: Uses `totalCount` (single API call) instead of pagination

### Recent Bug Fixes

- **Commit Counting**: Fixed inefficient API usage in `_count_commits_since()` 
  - Now uses `totalCount` for accurate counts (not capped at 100)
  - Reduces API calls from 4+ to just 1
- **Timezone Handling**: Added `_ensure_timezone_aware()` helper
  - Fixes "can't subtract offset-naive and offset-aware datetimes" errors

## Data Structure

### Time Series Collections

**`repo_stats_timeseries`** (hourly):
```javascript
{
  timestamp: ISODate("2025-01-15T10:00:00Z"),
  repo: {
    coin_id: "bitcoin",
    owner: "bitcoin", 
    name: "bitcoin",
    is_primary_repo: true
  },
  stats: {
    stars: 84438,
    stars_change: +5,
    forks: 37486,
    forks_change: +2
  },
  activity: {
    commits_last_24h: 8,
    commits_last_7d: 67,
    total_contributors: 845
  }
}
```

**`daily_repo_stats`** (aggregated):
```javascript
{
  coin_id: "bitcoin",
  date: "2025-01-15",
  metrics: {
    stars_end: 84438,
    commits_24h: 8,
    total_contributors: 845
  }
}
```

## Backend Integration

### Fetching Chart Data

```python
# MongoDB aggregation for historical data
pipeline = [
    {
        '$match': {
            'repo.coin_id': coin_id,
            'timestamp': {'$gte': start_date}
        }
    },
    {
        '$group': {
            '_id': {'$dateToString': {'format': '%Y-%m-%d', 'date': '$timestamp'}},
            'total_stars': {'$sum': '$stats.stars'},
            'total_forks': {'$sum': '$stats.forks'}
        }
    },
    {'$sort': {'_id': 1}}
]

# Format for Chart.js
return {
    'labels': [r['_id'] for r in results],
    'datasets': [
        {
            'label': 'Stars',
            'data': [r['total_stars'] for r in results],
            'borderColor': 'rgb(255, 206, 86)'
        }
    ]
}
```

## Monitoring

### Docker Commands

```bash
# View logs
docker-compose logs -f

# Check data collection
docker-compose exec github-collector python view_summary.py

# Manual data check
docker-compose exec github-collector python fetch_chart_data.py bitcoin --days 7
```

### Health Checks

The system logs:
- Collection progress every 10 repositories
- Rate limit status when < 100 remaining
- Success/error counts after each run
- Failed repositories list

## Important Notes

- **MongoDB 5.0+** required for time series collections
- **Monitors 189 repositories** from 87 crypto projects by default
- **Primary repos collected first**, secondary if rate limit allows
- **Data accumulates over time** - charts populate as collection continues
- **No virtual environment needed** - Docker handles dependencies

## Recent Updates (July 2025)

1. **Cleaned repository** - Removed unnecessary files for Docker deployment
2. **Fixed commit counting bug** - More efficient and accurate
3. **Updated README** - Docker-focused with clear deployment steps
4. **Added chart integration docs** - Shows how to fetch historical data
5. **Simplified .env.example** - Only essential configuration