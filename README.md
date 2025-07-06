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

## 🚀 Quick Start (Docker)

```bash
# 1. Clone and configure
git clone <repo-url>
cd github-data
cp .env.example .env
# Edit .env with your credentials

# 2. Deploy with Docker
./deploy.sh
```

That's it! The collector will run continuously in Docker.

## 📋 Prerequisites

- Docker & Docker Compose
- MongoDB 5.0+ (local or cloud)
- GitHub Personal Access Token

## ⚙️ Configuration

Edit `.env` file:

```env
# Required
GITHUB_TOKEN=your_github_token
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net
MONGODB_DATABASE=github_crypto_analysis

# Optional
COLLECTION_INTERVAL_HOURS=1
LOG_LEVEL=INFO
ENABLE_CONTRIBUTOR_TRACKING=true
MAX_CONTRIBUTORS_PER_REPO=50
```

## 🐳 Docker Commands

```bash
# Deploy/Update
./deploy.sh

# View logs
docker-compose logs -f

# Stop collector
docker-compose down

# View collected data
docker-compose exec github-collector python view_summary.py

# Check status!
docker-compose ps
```

## 📊 Data Collected

### Repository Metrics (Hourly)

- **Basic Stats**: Stars, forks, watchers, open issues (with change tracking)
- **Activity Metrics**: Commits (24h/7d), active contributors, top contributors
- **Crypto Mapping**: Each data point linked to `coin_id` for correlation
- **Contributor Tracking**: Smart two-phase approach to avoid rate limits

### Time Series Collections

**`github_repo_stats_timeseries`** - Raw hourly data:

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
  },
  activity: {
    commits_last_24h: 5,
    commits_last_7d: 45,
    unique_contributors_7d: 12,
    total_contributors: 845
  }
}
```

**`github_daily_repo_stats`** - Aggregated for charts:

```javascript
{
  date: "2024-01-15",
  coin_id: "bitcoin",
  metrics: {
    stars_end: 76543,
    commits_24h: 8,
    contributors_7d: 12,
    total_contributors: 845
  }
}
```

## 🏗️ Architecture

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

## 📈 Using the Data

### For Backend Developers

📚 **See the comprehensive [Backend API Guide](BACKEND_API_GUIDE.md)** for:

- Complete API endpoint examples
- MongoDB query patterns
- Frontend integration examples
- Performance optimization tips

### Direct MongoDB Queries

```javascript
// Get latest stats for a coin
db.github_repo_stats_timeseries.findOne(
  { "repo.coin_id": "bitcoin" },
  { sort: { timestamp: -1 } }
);

// Get daily aggregations for charts
db.github_daily_repo_stats.find({
  coin_id: "bitcoin",
  timestamp: { $gte: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000) },
});
```

## 📖 Documentation

- [EC2 Docker Setup](EC2_DOCKER_SETUP.md) - Deploy on AWS EC2
- [Backend API Guide](BACKEND_API_GUIDE.md) - Complete API implementation
- [API Quick Reference](API_QUICK_REFERENCE.md) - Endpoint examples
- [Dashboard Example](examples/dashboard_mockup.html) - Visualization mockup

## 🔧 Manual Usage (without Docker)

If you prefer running without Docker:

```bash
# Install dependencies
pip install -r requirements.txt

# Run once
python crypto_github_collector_v4.py --once

# Run continuously
python crypto_github_collector_v4.py

# List monitored repositories
python crypto_github_collector_v4.py --list

# Update contributor profiles
python crypto_github_collector_v4.py --update-contributors
```

## 🔍 Monitoring

```bash
# View summary
python view_summary.py

# Check recent activity
python view_summary.py --activity 24

# View Docker logs
docker-compose logs -f
```

## 📊 How It Works

1. **Discovery**: Reads your `crypto_project` collection
2. **Extraction**: Finds GitHub URLs in `links.repos_url.github`
3. **Collection**: Gathers metrics every hour (configurable)
4. **Storage**: Saves to time series with `coin_id` reference
5. **Aggregation**: Creates daily summaries for charts
6. **API Ready**: Provides chart-formatted JSON for your backend

## 🚨 Troubleshooting

- **Rate Limits**: The collector uses smart rate limiting (80% buffer)
- **Memory Usage**: Docker container is limited to reasonable resources
- **Connection Issues**: Check MongoDB URI and GitHub token
- **Missing Data**: Verify repositories exist and are public

For detailed troubleshooting, see [EC2 Docker Setup](EC2_DOCKER_SETUP.md#troubleshooting).
