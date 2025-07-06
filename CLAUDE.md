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

**Note**: This project currently has no dependency management files (requirements.txt, pyproject.toml, etc.) or defined development commands. When implementing features, you'll need to:

1. Set up appropriate Python dependency management
2. Install necessary libraries for GitHub API interaction (likely `requests` or `PyGithub`)
3. Create proper module structure in the `src/` directory

## Architecture Considerations

When implementing the GitHub data collection features:

1. **API Authentication**: You'll need to handle GitHub API authentication (personal access tokens or GitHub Apps)
2. **Rate Limiting**: GitHub API has rate limits - implement proper handling
3. **Data Storage**: Consider how collected data will be stored (JSON files, database, etc.)
4. **Modular Design**: Separate concerns between:
   - GitHub API client
   - Data collection logic
   - Data processing/analysis
   - Storage/export functionality

## Testing

No testing framework is currently set up. When adding tests, consider using `pytest` as it's the standard for Python projects.

## Common Tasks

### Running the collector:
- `python main.py` - Run continuous hourly collection
- `python main.py --once` - Run one-time collection

### Viewing data:
- `python examples/view_data.py --repo owner/name` - View latest stats
- `python examples/view_data.py --summary` - View all projects summary

### Adding new crypto projects:
Edit the `CRYPTO_PROJECTS` list in `main.py`

## MongoDB Time Series Collections

The project uses MongoDB time series collections for efficient storage:
- `repo_stats_timeseries` - Repository statistics with hourly granularity
- `contributor_activity_timeseries` - Contributor activity tracking
- `release_milestones_timeseries` - Release and milestone tracking

## Key Implementation Details

1. **Rate Limiting**: Implemented in `BaseCollector` with buffer (80% of limit)
2. **Change Tracking**: Automatic delta calculation between data points
3. **Bulk Operations**: Use `bulk_save_data()` for efficiency
4. **Error Handling**: Graceful handling of API errors and rate limits

## Memories
- `to memorize` added as a placeholder memory