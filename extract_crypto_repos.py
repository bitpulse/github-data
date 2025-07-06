#!/usr/bin/env python3
"""
Extract GitHub repositories from existing crypto_project collection
and create mappings for monitoring
"""

import sys
import re
from typing import List, Dict, Tuple
from urllib.parse import urlparse
from pymongo import MongoClient
from loguru import logger

from src.config.settings import settings


class CryptoRepoExtractor:
    """Extract GitHub repositories from crypto_project collection"""
    
    def __init__(self, crypto_collection_name: str = "crypto_project"):
        self.crypto_collection_name = crypto_collection_name
        self.client = MongoClient(settings.mongodb_uri)
        self.db = self.client[settings.mongodb_database]
        self.crypto_projects = []
        self.repo_mappings = {}
    
    def extract_repositories(self) -> Dict[str, List[Dict]]:
        """Extract all GitHub repositories from crypto projects"""
        logger.info(f"Extracting repositories from {self.crypto_collection_name} collection")
        
        crypto_collection = self.db[self.crypto_collection_name]
        projects = crypto_collection.find({}, {
            'coin_id': 1,
            'basic_info.name': 1,
            'basic_info.symbol': 1,
            'links.repos_url.github': 1,
            'developer_data': 1
        })
        
        repo_mappings = {}
        
        for project in projects:
            coin_id = project.get('coin_id')
            if not coin_id:
                continue
            
            # Get basic project info
            basic_info = project.get('basic_info', {})
            project_name = basic_info.get('name', coin_id)
            symbol = basic_info.get('symbol', '').upper()
            
            # Extract GitHub repositories
            repos_info = project.get('links', {}).get('repos_url', {}).get('github', [])
            repositories = []
            
            for i, repo_url in enumerate(repos_info):
                if not repo_url or not repo_url.startswith('https://github.com/'):
                    continue
                
                # Parse repository URL
                owner, repo_name = self._parse_github_url(repo_url)
                if owner and repo_name:
                    repo_data = {
                        'owner': owner,
                        'name': repo_name,
                        'url': repo_url,
                        'coin_id': coin_id,
                        'project_name': project_name,
                        'symbol': symbol,
                        'is_primary': i == 0,  # First repo is considered primary
                        'priority': 'primary' if i == 0 else 'secondary'
                    }
                    repositories.append(repo_data)
            
            if repositories:
                repo_mappings[coin_id] = {
                    'project_info': {
                        'coin_id': coin_id,
                        'name': project_name,
                        'symbol': symbol,
                        'developer_data': project.get('developer_data', {})
                    },
                    'repositories': repositories
                }
                
                logger.info(f"Found {len(repositories)} repositories for {project_name} ({coin_id})")
        
        self.repo_mappings = repo_mappings
        logger.info(f"Total extracted: {len(repo_mappings)} projects with repositories")
        
        return repo_mappings
    
    def _parse_github_url(self, url: str) -> Tuple[str, str]:
        """Parse GitHub URL to extract owner and repository name"""
        try:
            # Remove trailing .git if present
            url = url.rstrip('.git')
            
            # Parse URL
            parsed = urlparse(url)
            if parsed.netloc != 'github.com':
                return None, None
            
            # Extract path parts
            path_parts = parsed.path.strip('/').split('/')
            if len(path_parts) >= 2:
                owner = path_parts[0]
                repo_name = path_parts[1]
                return owner, repo_name
            
        except Exception as e:
            logger.warning(f"Error parsing GitHub URL {url}: {e}")
        
        return None, None
    
    def generate_crypto_projects_list(self) -> List[Tuple[str, str, str]]:
        """Generate CRYPTO_PROJECTS list for main.py with coin_id mapping"""
        crypto_projects = []
        
        for coin_id, project_data in self.repo_mappings.items():
            for repo in project_data['repositories']:
                crypto_projects.append((
                    repo['owner'],
                    repo['name'],
                    coin_id  # Add coin_id as third element
                ))
        
        return crypto_projects
    
    def save_mappings_to_file(self, filename: str = "crypto_repo_mappings.json"):
        """Save repository mappings to JSON file"""
        import json
        
        with open(filename, 'w') as f:
            json.dump(self.repo_mappings, f, indent=2)
        
        logger.info(f"Saved repository mappings to {filename}")
    
    def print_summary(self):
        """Print a summary of extracted repositories"""
        print("\n" + "="*80)
        print("CRYPTO PROJECT GITHUB REPOSITORIES SUMMARY")
        print("="*80)
        
        total_repos = 0
        primary_repos = 0
        
        for coin_id, project_data in self.repo_mappings.items():
            project_info = project_data['project_info']
            repositories = project_data['repositories']
            
            print(f"\n🪙 {project_info['name']} ({project_info['symbol']}) - {coin_id}")
            print(f"   Developer Stats: {repositories[0]['owner']}/{repositories[0]['name']}")
            
            dev_data = project_info.get('developer_data', {})
            if dev_data:
                print(f"   ⭐ Stars: {dev_data.get('stars', 0):,}")
                print(f"   🍴 Forks: {dev_data.get('forks', 0):,}")
                print(f"   📝 Commits (4w): {dev_data.get('commit_count_4_weeks', 0)}")
            
            print(f"   📚 Repositories ({len(repositories)}):")
            for repo in repositories:
                priority_emoji = "🔥" if repo['is_primary'] else "📁"
                print(f"     {priority_emoji} {repo['owner']}/{repo['name']} ({repo['priority']})")
            
            total_repos += len(repositories)
            primary_repos += sum(1 for r in repositories if r['is_primary'])
        
        print(f"\n" + "="*80)
        print(f"TOTAL: {len(self.repo_mappings)} projects, {total_repos} repositories ({primary_repos} primary)")
        print("="*80)
    
    def get_chart_ready_summary(self) -> Dict:
        """Get summary data in chart-ready format"""
        summary = {
            'total_projects': len(self.repo_mappings),
            'total_repositories': 0,
            'primary_repositories': 0,
            'projects': []
        }
        
        for coin_id, project_data in self.repo_mappings.items():
            project_info = project_data['project_info']
            repositories = project_data['repositories']
            dev_data = project_info.get('developer_data', {})
            
            project_summary = {
                'coin_id': coin_id,
                'name': project_info['name'],
                'symbol': project_info['symbol'],
                'repositories_count': len(repositories),
                'primary_repo': repositories[0] if repositories else None,
                'github_stats': {
                    'stars': dev_data.get('stars', 0),
                    'forks': dev_data.get('forks', 0),
                    'commits_4w': dev_data.get('commit_count_4_weeks', 0),
                    'contributors': dev_data.get('pull_request_contributors', 0)
                }
            }
            
            summary['projects'].append(project_summary)
            summary['total_repositories'] += len(repositories)
            summary['primary_repositories'] += sum(1 for r in repositories if r['is_primary'])
        
        return summary
    
    def close(self):
        """Close database connection"""
        self.client.close()


def main():
    """Main function"""
    extractor = CryptoRepoExtractor()
    
    try:
        # Extract repositories
        repo_mappings = extractor.extract_repositories()
        
        if not repo_mappings:
            logger.error("No repositories found in crypto_project collection")
            return
        
        # Print summary
        extractor.print_summary()
        
        # Save mappings
        extractor.save_mappings_to_file()
        
        # Generate projects list for main.py
        crypto_projects = extractor.generate_crypto_projects_list()
        
        print(f"\n📋 CRYPTO_PROJECTS list for main.py:")
        print("CRYPTO_PROJECTS = [")
        for owner, repo_name, coin_id in crypto_projects:
            print(f"    ('{owner}', '{repo_name}', '{coin_id}'),")
        print("]")
        
        # Chart-ready summary
        chart_summary = extractor.get_chart_ready_summary()
        print(f"\n📊 Chart-ready summary:")
        print(f"Total projects to monitor: {chart_summary['total_projects']}")
        print(f"Total repositories: {chart_summary['total_repositories']}")
        print(f"Primary repositories: {chart_summary['primary_repositories']}")
        
    except Exception as e:
        logger.error(f"Error extracting repositories: {e}")
    finally:
        extractor.close()


if __name__ == "__main__":
    main()