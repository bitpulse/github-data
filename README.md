This repo is for collecting github data

given github repo link

- get all the activities about the repo

given github user

- get all the activities from the github user

---

we will use this data for crypto projects analysis(how active they are, who are founders and etc)

## Setup

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and configure:
   - Add your GitHub personal access token
   - Configure MongoDB connection (default: localhost:27017)
4. Ensure MongoDB is running

## Usage

### Run continuous collection (every hour):
```bash
python main.py
```

### Run one-time collection:
```bash
python main.py --once
```

### View collected data:
```bash
# View latest stats for a repository
python examples/view_data.py --repo bitcoin/bitcoin

# View growth trends
python examples/view_data.py --repo ethereum/go-ethereum --trends --days 30

# View summary of all projects
python examples/view_data.py --summary
```

## Architecture

- **MongoDB Time Series Collections**: Stores historical data with automatic optimization
- **Rate Limiting**: Respects GitHub API limits (5000 requests/hour for authenticated users)
- **Change Tracking**: Calculates deltas between data points for trend analysis
- **Scheduled Collection**: Runs hourly by default to track changes over time
