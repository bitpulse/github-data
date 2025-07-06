# GitHub Data Collector for Crypto Projects

A Python-based time series data collector for analyzing cryptocurrency project activity on GitHub. This tool collects comprehensive metrics from GitHub repositories and stores them in MongoDB time series collections for trend analysis and predictions.

## Features

- **Time Series Data Collection**: Hourly snapshots of repository metrics
- **Change Tracking**: Automatic calculation of deltas between data points
- **MongoDB Time Series**: Optimized storage with automatic compression
- **Rate Limiting**: Respects GitHub API limits with built-in buffer
- **25+ Crypto Projects**: Pre-configured with major cryptocurrency projects
- **Trend Analysis**: Built-in tools for viewing growth trends and patterns

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

**Continuous collection mode** (runs every hour):
```bash
python main.py
```

**One-time collection**:
```bash
python main.py --once
```

The collector will:
- Gather data for all configured crypto projects
- Calculate changes from previous data points
- Store in MongoDB time series collections
- Show progress and rate limit status

### Viewing Collected Data

**View latest stats for a specific repository**:

```bash
python examples/view_data.py --repo bitcoin/bitcoin
```

Output example:
```
=== Latest Stats for bitcoin/bitcoin ===
Timestamp: 2024-01-15 10:00:00

Basic Statistics:
  Stars: 76,543 (+12)
  Forks: 35,678 (+3)
  Watchers: 3,456 (-2)
  Open Issues: 567 (+5)

Activity Metrics:
  Commits (24h): 5
  Commits (7d): 45
  Contributors (7d): 12
  PRs merged (7d): 8
```

**View growth trends**:
```bash
python examples/view_data.py --repo ethereum/go-ethereum --trends --days 30
```

**View summary of all monitored projects**:
```bash
python examples/view_data.py --summary
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

## Data Collected

### Repository Metrics
- **Basic Stats**: Stars, forks, watchers, open issues, repository size
- **Activity Metrics**: Commits (24h/7d/30d), active contributors, top contributors
- **PR/Issue Stats**: Open PRs, merged PRs, closed issues, resolution times
- **Release Info**: Latest release, days since release, total releases
- **Change Tracking**: Delta calculations for all numeric metrics

### Time Series Storage
Data is stored in MongoDB time series collections with:
- Hourly granularity
- Automatic compression and bucketing
- Optimized for time-based queries
- Built-in aggregation support

## Architecture

- **PyGithub**: GitHub API v3 integration with automatic pagination
- **MongoDB Time Series**: Efficient storage for temporal data
- **Rate Limiting**: Smart rate limiter with 80% buffer and automatic retry
- **Modular Design**: Separate collectors, storage, and analysis modules
- **Error Handling**: Graceful handling of API errors and missing repositories

## Monitored Projects

The system comes pre-configured with 25+ major cryptocurrency projects including:
- **Bitcoin Ecosystem**: bitcoin/bitcoin, bitcoin/bips
- **Ethereum Ecosystem**: ethereum/go-ethereum, ethereum/solidity
- **DeFi Protocols**: Uniswap, Aave, Compound, MakerDAO
- **Layer 2 Solutions**: Arbitrum, Optimism, zkSync
- **Other Blockchains**: Solana, Polkadot, Cosmos, Cardano
- **Developer Tools**: OpenZeppelin, Truffle, Foundry

## Advanced Usage

### Analyzing Trends

The time series data enables various analyses:
- Growth rate calculations
- Moving averages
- Anomaly detection
- Contributor retention analysis
- Development velocity tracking

### Extending the System

The modular architecture makes it easy to add:
- New data collectors (e.g., contributor details, code metrics)
- Additional analysis algorithms
- Export formats (CSV, JSON)
- Alerting systems
- Web dashboards

## Configuration Options

See `.env.example` for all configuration options:
- `COLLECTION_INTERVAL_HOURS`: How often to collect data (default: 1)
- `RATE_LIMIT_BUFFER`: Safety buffer for API limits (default: 0.8)
- `DATA_RETENTION_DAYS`: How long to keep data (default: 365)
- `BATCH_SIZE`: Batch size for bulk operations (default: 100)
