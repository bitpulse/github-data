# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python project for collecting GitHub data from cryptocurrency projects for time series analysis and charting. The system integrates with an existing `crypto_project` MongoDB collection to monitor GitHub repositories and track development activity over time.

### Key Features

- Automatically extracts GitHub repositories from `crypto_project` collection
- Links all GitHub data to `coin_id` for correlation with market data
- Stores time series data optimized for frontend charts
- Tracks changes (deltas) between data points
- Creates daily aggregations for fast chart queries
- Continuous monitoring with configurable intervals

## Project Structure

```
github-data/
├── crypto_github_collector.py  # Single-file solution for continuous collection
├── main_crypto.py             # Modular version with crypto integration
├── extract_crypto_repos.py    # Extract repos from crypto_project collection
├── requirements.txt           # Python dependencies
├── .env.example              # Configuration template
├── src/
│   ├── config/               # Settings and metrics configuration
│   ├── collectors/           # GitHub data collectors (with coin_id support)
│   ├── storage/              # MongoDB and time series operations
│   ├── models/               # Pydantic data schemas
│   ├── analysis/             # Chart data aggregation and API
│   └── utils/                # Crypto mapping utilities
└── examples/
    ├── view_data.py          # View collected data
    └── backend_api_examples.py # Chart-ready API examples
```

## Development Setup

1. Install dependencies: `pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and configure:
   - Add your GitHub personal access token
   - Configure MongoDB connection URI
3. Ensure MongoDB 5.0+ is running (required for time series collections)

## Architecture

### Integration with Crypto Projects

The system reads from your existing `crypto_project` collection to automatically discover GitHub repositories. Each repository is linked to its `coin_id` for correlation analysis.

### Core Components

1. **Data Collection**:
   - Extracts repos from `crypto_project` collection
   - Collects GitHub metrics with PyGithub
   - Links all data to `coin_id`
   - Rate limiting with 80% buffer

2. **Time Series Storage**:
   - `repo_stats_timeseries` - Hourly GitHub metrics with coin_id
   - `daily_repo_stats` - Aggregated daily data for charts
   - MongoDB time series collections with automatic optimization

3. **Chart Data API**:
   - Ready-to-use functions for backend integration
   - Returns JSON formatted for frontend charts
   - Multiple chart types: stars, commits, dashboard, leaderboard

### Data Flow

```
crypto_project collection → Repository Extraction → GitHub API Collection → 
Time Series Storage → Chart Aggregation → Backend API → Frontend Charts
```

## Common Tasks

### Quick Start

```bash
# Single command to start continuous monitoring
python crypto_github_collector.py
```

### Data Collection Options

- `python crypto_github_collector.py` - Continuous monitoring (every hour)
- `python crypto_github_collector.py --once` - Run once for all repos
- `python crypto_github_collector.py --primary` - Primary repos only
- `python crypto_github_collector.py --list` - See what will be monitored

### Viewing Chart Data

```bash
# Test chart API endpoints
python examples/backend_api_examples.py --demo

# View raw data
python examples/view_data.py --repo bitcoin/bitcoin
```

### Backend Integration

```python
from src.analysis.chart_data_api import chart_api

# Get chart-ready data
stars_chart = chart_api.get_stars_chart_data('bitcoin', days=30)
dashboard = chart_api.get_multi_metric_dashboard('ethereum', days=7)
```

## Key Implementation Details

1. **Crypto Integration**: Automatically discovers repos from `crypto_project` collection
2. **Chart-Ready Data**: All data formatted for direct use in frontend charts
3. **Time Series Storage**: MongoDB collections optimized for time-based queries
4. **Change Tracking**: Every data point includes deltas for trend analysis
5. **Rate Limiting**: Smart rate limiter prevents API exhaustion
6. **Scalability**: Handles hundreds of repositories across multiple projects

## Important Notes

- The system expects a `crypto_project` collection with GitHub URLs in `links.repos_url.github`
- All GitHub data is linked to `coin_id` for correlation with market data
- Time series data accumulates over time for better trend analysis
- Daily aggregations are created automatically for faster chart queries