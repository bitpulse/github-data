#!/usr/bin/env python3
"""
GitHub Data Collector for Crypto Project Analysis
Main entry point for scheduled data collection
"""

import sys
import time
import signal
from datetime import datetime
from typing import List, Tuple
import schedule
from loguru import logger

from src.config.settings import settings, validate_settings
from src.storage.mongodb_client import mongodb_client
from src.collectors.repository import RepositoryStatsCollector


# List of crypto projects to monitor
# Format: (owner, repository_name)
CRYPTO_PROJECTS: List[Tuple[str, str]] = [
    # Bitcoin ecosystem
    ('bitcoin', 'bitcoin'),
    ('bitcoin', 'bips'),
    ('bitcoinj', 'bitcoinj'),
    
    # Ethereum ecosystem
    ('ethereum', 'go-ethereum'),
    ('ethereum', 'solidity'),
    ('ethereum', 'web3.js'),
    ('ethereum', 'ethereum-org-website'),
    
    # DeFi projects
    ('Uniswap', 'interface'),
    ('Uniswap', 'v3-core'),
    ('aave', 'aave-v3-core'),
    ('compound-finance', 'compound-protocol'),
    ('makerdao', 'dss'),
    
    # Layer 2 solutions
    ('OffchainLabs', 'arbitrum'),
    ('ethereum-optimism', 'optimism'),
    ('matter-labs', 'zksync'),
    
    # Other major projects
    ('solana-labs', 'solana'),
    ('paritytech', 'polkadot'),
    ('cosmos', 'cosmos-sdk'),
    ('algorand', 'go-algorand'),
    ('cardano-foundation', 'cardano-node'),
    
    # Developer tools
    ('OpenZeppelin', 'openzeppelin-contracts'),
    ('trufflesuite', 'truffle'),
    ('foundry-rs', 'foundry'),
    
    # Add more projects as needed
]


class GithubDataCollector:
    """Main collector orchestrator"""
    
    def __init__(self):
        self.repo_collector = RepositoryStatsCollector()
        self.running = True
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
    
    def collect_all_repos(self):
        """Collect data for all configured repositories"""
        logger.info(f"Starting data collection for {len(CRYPTO_PROJECTS)} projects")
        start_time = datetime.utcnow()
        
        success_count = 0
        error_count = 0
        
        for owner, repo_name in CRYPTO_PROJECTS:
            try:
                logger.info(f"Collecting data for {owner}/{repo_name}")
                
                # Collect repository stats
                repo_data = self.repo_collector.collect(owner, repo_name)
                
                # Save to MongoDB
                self.repo_collector.save_data(repo_data)
                
                success_count += 1
                
                # Small delay between requests to be respectful
                time.sleep(0.5)
                
            except Exception as e:
                error_count += 1
                logger.error(f"Failed to collect data for {owner}/{repo_name}: {e}")
                continue
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.info(
            f"Collection completed in {duration:.1f}s. "
            f"Success: {success_count}, Errors: {error_count}"
        )
        
        # Check rate limit status
        rate_limit = self.repo_collector.check_rate_limit()
        logger.info(
            f"Rate limit status - Core: {rate_limit['core']['remaining']}/{rate_limit['core']['limit']}, "
            f"Search: {rate_limit['search']['remaining']}/{rate_limit['search']['limit']}"
        )
    
    def run_scheduler(self):
        """Run the scheduler for periodic collection"""
        logger.info("Starting GitHub data collector scheduler")
        
        # Schedule collection based on configuration
        schedule.every(settings.collection_interval_hours).hours.do(self.collect_all_repos)
        
        # Run once immediately
        self.collect_all_repos()
        
        # Keep running until interrupted
        while self.running:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
        
        logger.info("Scheduler stopped")
    
    def run_once(self):
        """Run collection once and exit"""
        logger.info("Running one-time collection")
        self.collect_all_repos()


def setup_logging():
    """Configure logging"""
    logger.remove()  # Remove default handler
    
    # Console logging
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
        level=settings.log_level
    )
    
    # File logging
    if settings.log_file:
        logger.add(
            settings.log_file,
            rotation="10 MB",
            retention="7 days",
            level=settings.log_level
        )


def main():
    """Main entry point"""
    # Set up logging
    setup_logging()
    
    # Validate settings
    try:
        validate_settings()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        logger.error("Please copy .env.example to .env and configure your settings")
        sys.exit(1)
    
    # Initialize database connection
    try:
        mongodb_client.connect()
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        sys.exit(1)
    
    # Create collector instance
    collector = GithubDataCollector()
    
    # Check command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == '--once':
        # Run once and exit
        collector.run_once()
    else:
        # Run scheduler
        collector.run_scheduler()
    
    # Clean up
    mongodb_client.close()
    logger.info("GitHub data collector shutdown complete")


if __name__ == "__main__":
    main()