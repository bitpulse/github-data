#!/usr/bin/env python3
"""
GitHub Data Collector for Crypto Projects - Integration Version
Main entry point that uses existing crypto_project collection
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
from src.utils.crypto_mapping import crypto_mapper


class CryptoGithubCollector:
    """Main collector that integrates with crypto_project collection"""
    
    def __init__(self):
        self.repo_collector = RepositoryStatsCollector()
        self.running = True
        self.crypto_repositories = []
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Load crypto project mappings
        self._load_crypto_repositories()
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
    
    def _load_crypto_repositories(self):
        """Load repositories from crypto_project collection"""
        try:
            # Get all repositories mapped to crypto projects
            self.crypto_repositories = crypto_mapper.get_all_repositories()
            
            if not self.crypto_repositories:
                logger.error("No repositories found in crypto_project collection")
                logger.info("Make sure your crypto_project collection has GitHub URLs in links.repos_url.github")
                sys.exit(1)
            
            # Get summary
            summary = crypto_mapper.get_project_summary()
            logger.info(f"Loaded {summary['total_repositories']} repositories from {summary['total_projects']} crypto projects")
            logger.info(f"Primary repositories: {summary['primary_repositories']}")
            
            # Log some examples
            primary_repos = crypto_mapper.get_primary_repositories()
            logger.info("Primary repositories to monitor:")
            for owner, name, coin_id in primary_repos[:5]:  # Show first 5
                logger.info(f"  - {owner}/{name} ({coin_id})")
            
            if len(primary_repos) > 5:
                logger.info(f"  ... and {len(primary_repos) - 5} more")
                
        except Exception as e:
            logger.error(f"Error loading crypto repositories: {e}")
            sys.exit(1)
    
    def collect_all_repos(self):
        """Collect data for all crypto project repositories"""
        logger.info(f"Starting data collection for {len(self.crypto_repositories)} crypto repositories")
        start_time = datetime.utcnow()
        
        success_count = 0
        error_count = 0
        
        # Prioritize primary repositories
        primary_repos = [(o, n, c) for o, n, c in self.crypto_repositories 
                        if crypto_mapper.is_primary_repo(o, n)]
        secondary_repos = [(o, n, c) for o, n, c in self.crypto_repositories 
                          if not crypto_mapper.is_primary_repo(o, n)]
        
        # Collect primary repositories first
        logger.info(f"Collecting {len(primary_repos)} primary repositories...")
        for owner, repo_name, coin_id in primary_repos:
            if not self.running:
                break
                
            try:
                logger.info(f"📊 Collecting {owner}/{repo_name} (crypto: {coin_id})")
                
                # Collect repository stats
                repo_data = self.repo_collector.collect(owner, repo_name)
                
                # Save to MongoDB
                self.repo_collector.save_data(repo_data)
                
                success_count += 1
                
                # Small delay between requests
                time.sleep(1)
                
            except Exception as e:
                error_count += 1
                logger.error(f"Failed to collect data for {owner}/{repo_name}: {e}")
                continue
        
        # Collect secondary repositories if we have rate limit remaining
        rate_limit = self.repo_collector.check_rate_limit()
        remaining_requests = rate_limit['core']['remaining']
        
        if remaining_requests > len(secondary_repos) + 100:  # Keep buffer
            logger.info(f"Collecting {len(secondary_repos)} secondary repositories...")
            for owner, repo_name, coin_id in secondary_repos:
                if not self.running:
                    break
                    
                try:
                    logger.info(f"📁 Collecting {owner}/{repo_name} (crypto: {coin_id})")
                    
                    # Collect repository stats
                    repo_data = self.repo_collector.collect(owner, repo_name)
                    
                    # Save to MongoDB
                    self.repo_collector.save_data(repo_data)
                    
                    success_count += 1
                    
                    # Small delay between requests
                    time.sleep(1)
                    
                except Exception as e:
                    error_count += 1
                    logger.error(f"Failed to collect data for {owner}/{repo_name}: {e}")
                    continue
        else:
            logger.warning(f"Skipping secondary repos - insufficient rate limit ({remaining_requests} remaining)")
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.info(
            f"Collection completed in {duration:.1f}s. "
            f"Success: {success_count}, Errors: {error_count}"
        )
        
        # Check final rate limit status
        final_rate_limit = self.repo_collector.check_rate_limit()
        logger.info(
            f"Rate limit status - Core: {final_rate_limit['core']['remaining']}/{final_rate_limit['core']['limit']}, "
            f"Search: {final_rate_limit['search']['remaining']}/{final_rate_limit['search']['limit']}"
        )
    
    def collect_primary_repos_only(self):
        """Collect data for primary repositories only (faster)"""
        primary_repos = crypto_mapper.get_primary_repositories()
        
        logger.info(f"Starting primary repository collection for {len(primary_repos)} crypto projects")
        start_time = datetime.utcnow()
        
        success_count = 0
        error_count = 0
        
        for owner, repo_name, coin_id in primary_repos:
            if not self.running:
                break
                
            try:
                logger.info(f"🔥 Collecting primary repo: {owner}/{repo_name} (crypto: {coin_id})")
                
                # Collect repository stats
                repo_data = self.repo_collector.collect(owner, repo_name)
                
                # Save to MongoDB
                self.repo_collector.save_data(repo_data)
                
                success_count += 1
                
                # Small delay between requests
                time.sleep(1)
                
            except Exception as e:
                error_count += 1
                logger.error(f"Failed to collect data for {owner}/{repo_name}: {e}")
                continue
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.info(
            f"Primary collection completed in {duration:.1f}s. "
            f"Success: {success_count}, Errors: {error_count}"
        )
    
    def run_scheduler(self):
        """Run the scheduler for periodic collection"""
        logger.info("Starting crypto GitHub data collector scheduler")
        
        # Schedule collection based on configuration
        schedule.every(settings.collection_interval_hours).hours.do(self.collect_all_repos)
        
        # Run once immediately
        self.collect_all_repos()
        
        # Keep running until interrupted
        while self.running:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
        
        logger.info("Scheduler stopped")
    
    def run_once(self, primary_only: bool = False):
        """Run collection once and exit"""
        if primary_only:
            logger.info("Running one-time primary repository collection")
            self.collect_primary_repos_only()
        else:
            logger.info("Running one-time full collection")
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
    collector = CryptoGithubCollector()
    
    # Check command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == '--once':
            # Run once and exit
            collector.run_once()
        elif sys.argv[1] == '--primary':
            # Run primary repositories only
            collector.run_once(primary_only=True)
        elif sys.argv[1] == '--list':
            # List repositories that would be monitored
            summary = crypto_mapper.get_project_summary()
            print(f"\nCrypto GitHub Repositories ({summary['total_repositories']} total):")
            print("="*60)
            
            for coin_id in summary['projects']:
                repos = crypto_mapper.get_repositories_for_coin(coin_id)
                coin_data = crypto_mapper._coin_to_repos_map[coin_id]
                print(f"\n🪙 {coin_data['project_name']} ({coin_data['symbol']}) - {coin_id}")
                for repo in repos:
                    priority_emoji = "🔥" if repo['is_primary'] else "📁"
                    print(f"   {priority_emoji} {repo['owner']}/{repo['name']} ({repo['priority']})")
            
            print(f"\n📊 Summary:")
            print(f"   Total projects: {summary['total_projects']}")
            print(f"   Total repositories: {summary['total_repositories']}")
            print(f"   Primary repositories: {summary['primary_repositories']}")
        else:
            print("Usage:")
            print("  python main_crypto.py              # Run continuous collection")
            print("  python main_crypto.py --once       # Run once (all repos)")
            print("  python main_crypto.py --primary    # Run once (primary repos only)")
            print("  python main_crypto.py --list       # List repositories to monitor")
            sys.exit(1)
    else:
        # Run scheduler
        collector.run_scheduler()
    
    # Clean up
    mongodb_client.close()
    logger.info("Crypto GitHub data collector shutdown complete")


if __name__ == "__main__":
    main()