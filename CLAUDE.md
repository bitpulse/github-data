# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python project for collecting GitHub data to analyze cryptocurrency projects. The main goals are:

- Collect all activities about a GitHub repository given a repo link
- Collect all activities from a GitHub user
- Store data in MongoDB time series collections for trend analysis
- Track changes over time to predict project health and sustainability

## Project Structure

The project now has a complete implementation:

```
github-data/
├── main.py                    # Main collector with scheduler
├── requirements.txt           # Python dependencies
├── .env.example              # Configuration template
├── src/
│   ├── config/               # Settings and metrics configuration
│   ├── collectors/           # GitHub data collectors
│   ├── storage/              # MongoDB and time series operations
│   ├── models/               # Pydantic data schemas
│   ├── analysis/             # Analysis modules (ready for expansion)
│   ├── scheduler/            # Scheduling logic
│   └── utils/                # Utility functions
└── examples/
    └── view_data.py          # Example data viewer
```

## Development Setup

1. Install dependencies: `pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and configure:
   - Add your GitHub personal access token
   - Configure MongoDB connection URI
3. Ensure MongoDB 5.0+ is running (required for time series collections)

## Architecture

### Core Components

1. **Data Collection** (PyGithub-based):
   - Repository stats collector with change tracking
   - Contributor activity collector (to be implemented)
   - Rate limiting with 80% buffer of API limits

2. **Storage** (MongoDB Time Series):
   - Automatic bucketing and compression
   - Optimized for time-based queries
   - Built-in data retention policies

3. **Analysis** (Ready for expansion):
   - Trend detection and growth analysis
   - Anomaly detection
   - Project health scoring

### MongoDB Collections

- `repo_stats_timeseries` - Repository metrics (stars, forks, commits, etc.)
- `contributor_activity_timeseries` - Developer activity tracking
- `release_milestones_timeseries` - Release and milestone data

## Common Tasks

### Running the collector

- `python main.py` - Run continuous hourly collection
- `python main.py --once` - Run one-time collection

### Viewing data

- `python examples/view_data.py --repo owner/name` - View latest stats
- `python examples/view_data.py --summary` - View all projects summary
- `python examples/view_data.py --repo owner/name --trends --days 30` - View trends

### Adding new crypto projects

Edit the `CRYPTO_PROJECTS` list in `main.py`

## Key Implementation Details

1. **Rate Limiting**: Implemented in `BaseCollector` with automatic retry and backoff
2. **Change Tracking**: Every data point includes deltas from previous collection
3. **Error Handling**: Graceful handling of API errors, rate limits, and missing repos
4. **Time Series**: Hourly granularity with automatic aggregation support
5. **Monitored Projects**: 25+ major crypto projects including Bitcoin, Ethereum, DeFi protocols

## Memories
- `to memorize` added as a placeholder memory