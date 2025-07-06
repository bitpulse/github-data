# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python project for collecting GitHub data to analyze cryptocurrency projects. The main goals are:
- Collect all activities about a GitHub repository given a repo link
- Collect all activities from a GitHub user
- Use this data for crypto project analysis (activity levels, founders, etc.)

## Project Structure

The project is in early development stages with minimal structure:
```
github-data/
├── src/
│   └── __init__.py    # Empty Python package initializer
└── README.md          # Basic project description
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

Since the project has no established commands yet, when implementing features you should:
- Create a `requirements.txt` or `pyproject.toml` for dependencies
- Set up virtual environment management
- Define entry points for the main functionality