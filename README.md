# GitHub Data Collector for Crypto Projects

A comprehensive time series data collection system that monitors GitHub repositories of cryptocurrency projects. It integrates with your existing `crypto_project` MongoDB collection to automatically track development activity and provide chart-ready data for frontend visualization.

## 🎯 Purpose

This system bridges the gap between your crypto market data and GitHub development metrics, enabling:
- Correlation analysis between development activity and market performance
- Real-time monitoring of project health and developer engagement
- Historical trend analysis for predictive insights
- Chart-ready data for dashboards and analytics

## ✨ Features

- **Automatic Repository Discovery**: Extracts GitHub repos from your `crypto_project` collection
- **Crypto Project Integration**: Links all data to `coin_id` for market correlation
- **Time Series Storage**: MongoDB collections optimized for temporal queries
- **Change Tracking**: Calculates deltas between data points for trend analysis
- **Chart-Ready API**: Pre-formatted data for direct frontend consumption
- **Smart Rate Limiting**: Maximizes data collection within GitHub API limits
- **Daily Aggregations**: Pre-computed summaries for fast chart rendering

## Prerequisites

- Python 3.8+
- MongoDB 5.0+ (required for time series collections)
- GitHub Personal Access Token

## Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd github-data
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and add:
   - `GITHUB_TOKEN`: Your GitHub personal access token (get one at https://github.com/settings/tokens)
   - `MONGODB_URI`: MongoDB connection string (default: `mongodb://localhost:27017/`)
   - `MONGODB_DATABASE`: Database name (default: `github_crypto_analysis`)

4. **Start MongoDB**
   ```bash
   # If using Docker
   docker run -d -p 27017:27017 mongo:latest
   
   # Or ensure your local MongoDB is running
   mongod
   ```

5. **Verify setup**
   ```bash
   python test_setup.py
   ```
   
   This will check all dependencies, configuration, and connections.

## Usage

### Running the Collector

**Single File Solution (Recommended)**:

```bash
# Run continuous collection (monitors every hour)
python crypto_github_collector.py

# Run one-time collection (all repositories)
python crypto_github_collector.py --once

# Run one-time collection (primary repositories only)
python crypto_github_collector.py --primary

# List repositories that will be monitored
python crypto_github_collector.py --list
```

**Alternative Methods**:

```bash
# Extract and view repository mappings
python extract_crypto_repos.py

# Use modular version with more options
python main_crypto.py
```

The collector will:
- Extract GitHub repositories from your crypto_project collection
- Link repository data to coin_id for correlation analysis
- Gather comprehensive GitHub metrics
- Calculate changes from previous data points
- Store in MongoDB time series collections with crypto project mapping

### Viewing Collected Data

**View repository stats**:

```bash
python examples/view_data.py --repo bitcoin/bitcoin
python examples/view_data.py --summary
```

**Backend API Examples (Chart-Ready Data)**:

```bash
# Demo all API endpoints
python examples/backend_api_examples.py --demo

# Test specific coin
python examples/backend_api_examples.py --coin bitcoin --days 30
```

**Chart Data API Endpoints**:
```python
# In your backend, import the API
from src.analysis.chart_data_api import chart_api

# Get chart data for frontend
stars_data = chart_api.get_stars_chart_data('bitcoin', days=30)
dashboard_data = chart_api.get_multi_metric_dashboard('ethereum', days=7)
leaderboard = chart_api.get_top_projects_leaderboard(limit=10)
```

**Example API Response (Chart-Ready)**:
```json
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
```

### Adding Custom Projects

Edit `CRYPTO_PROJECTS` in `main.py`:
```python
CRYPTO_PROJECTS = [
    ('bitcoin', 'bitcoin'),
    ('ethereum', 'go-ethereum'),
    # Add your project:
    ('your-org', 'your-repo'),
]
```

## 📊 Data Collected

### Repository Metrics (Hourly)
- **Basic Stats**: Stars, forks, watchers, open issues (with change tracking)
- **Activity Metrics**: Commits (24h/7d), active contributors, top contributors
- **Development Health**: PR merge rates, issue resolution times, code velocity
- **Crypto Mapping**: Each data point linked to `coin_id` for correlation

### Time Series Collections

**`repo_stats_timeseries`** - Raw hourly data:
```javascript
{
  timestamp: ISODate("2024-01-15T10:00:00Z"),
  repo: {
    coin_id: "bitcoin",
    owner: "bitcoin",
    name: "bitcoin",
    is_primary_repo: true
  },
  stats: {
    stars: 76543,
    stars_change: +12,
    forks: 35678,
    forks_change: +3
  }
}
```

**`daily_repo_stats`** - Aggregated for charts:
```javascript
{
  date: "2024-01-15",
  coin_id: "bitcoin",
  metrics: {
    stars_end: 76543,
    commits_24h: 8,
    contributors_7d: 12
  }
}
```

## 🏗️ Architecture

### Data Flow
```
Your crypto_project Collection
            ↓
    Repository Extraction
            ↓
     GitHub API Collection
            ↓
    Time Series Storage
            ↓
     Chart Aggregation
            ↓
    Backend API Ready
```

### Key Components
- **Crypto Integration**: Reads from your existing `crypto_project` collection
- **GitHub Collection**: PyGithub with smart rate limiting
- **Time Series Storage**: MongoDB 5.0+ collections with automatic optimization
- **Chart API**: Pre-built functions returning frontend-ready JSON
- **Change Tracking**: Automatic delta calculations for trend analysis

## 🪙 How It Works

1. **Discovery**: Reads your `crypto_project` collection
2. **Extraction**: Finds GitHub URLs in `links.repos_url.github`
3. **Collection**: Gathers metrics every hour (configurable)
4. **Storage**: Saves to time series with `coin_id` reference
5. **Aggregation**: Creates daily summaries for charts
6. **API Ready**: Provides chart-formatted JSON for your backend

## 🚀 Quick Start Guide

```bash
# 1. Clone and setup
git clone <repo-url>
cd github-data
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Edit .env with your GitHub token and MongoDB URI

# 3. Start collecting
python crypto_github_collector.py

# That's it! Data collection starts immediately
```

## 📈 Using the Data

### For Backend Developers

```python
from src.analysis.chart_data_api import chart_api

# Get chart data for your API endpoints
stars_data = chart_api.get_stars_chart_data('bitcoin', days=30)
# Returns: {"chart_data": [{"x": "2024-01-01", "y": 76000}], ...}

dashboard = chart_api.get_multi_metric_dashboard('ethereum')
# Returns complete dashboard data with multiple metrics

leaderboard = chart_api.get_top_projects_leaderboard()
# Returns top projects by GitHub activity
```

### Direct MongoDB Queries

```javascript
// Get latest stats for a coin
db.repo_stats_timeseries.findOne(
  {"repo.coin_id": "bitcoin"},
  {sort: {timestamp: -1}}
)

// Get daily aggregations for charts
db.daily_repo_stats.find({
  "coin_id": "bitcoin",
  "timestamp": {$gte: new Date(Date.now() - 30*24*60*60*1000)}
})
```

## ⚙️ Configuration

All settings in `.env`:
- `GITHUB_TOKEN`: Your personal access token (required)
- `MONGODB_URI`: Connection string (default: localhost)
- `MONGODB_DATABASE`: Database name
- `COLLECTION_INTERVAL_HOURS`: How often to collect (default: 1)
- `RATE_LIMIT_BUFFER`: API safety margin (default: 0.8)
