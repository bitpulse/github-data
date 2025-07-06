"""
Crypto project to GitHub repository mapping utilities
"""

import json
from typing import Dict, List, Tuple, Optional
from pymongo import MongoClient
from loguru import logger

from src.config.settings import settings


class CryptoRepositoryMapper:
    """Maps crypto projects to their GitHub repositories"""
    
    def __init__(self, crypto_collection_name: str = "crypto_project"):
        self.crypto_collection_name = crypto_collection_name
        self._repo_to_coin_map = {}
        self._coin_to_repos_map = {}
        self._loaded = False
    
    def load_mappings(self) -> None:
        """Load repository mappings from crypto_project collection"""
        if self._loaded:
            return
        
        try:
            client = MongoClient(settings.mongodb_uri)
            db = client[settings.mongodb_database]
            crypto_collection = db[self.crypto_collection_name]
            
            projects = crypto_collection.find({}, {
                'coin_id': 1,
                'basic_info.name': 1,
                'basic_info.symbol': 1,
                'links.repos_url.github': 1
            })
            
            for project in projects:
                coin_id = project.get('coin_id')
                if not coin_id:
                    continue
                
                basic_info = project.get('basic_info', {})
                project_name = basic_info.get('name', coin_id)
                symbol = basic_info.get('symbol', '').upper()
                
                repos_info = project.get('links', {}).get('repos_url', {}).get('github', [])
                repositories = []
                
                for i, repo_url in enumerate(repos_info):
                    if not repo_url or not repo_url.startswith('https://github.com/'):
                        continue
                    
                    owner, repo_name = self._parse_github_url(repo_url)
                    if owner and repo_name:
                        repo_key = f"{owner}/{repo_name}"
                        
                        # Map repository to coin
                        self._repo_to_coin_map[repo_key] = {
                            'coin_id': coin_id,
                            'project_name': project_name,
                            'symbol': symbol,
                            'is_primary': i == 0,
                            'priority': 'primary' if i == 0 else 'secondary'
                        }
                        
                        repositories.append({
                            'owner': owner,
                            'name': repo_name,
                            'is_primary': i == 0,
                            'priority': 'primary' if i == 0 else 'secondary'
                        })
                
                if repositories:
                    self._coin_to_repos_map[coin_id] = {
                        'project_name': project_name,
                        'symbol': symbol,
                        'repositories': repositories
                    }
            
            client.close()
            self._loaded = True
            logger.info(f"Loaded mappings for {len(self._coin_to_repos_map)} crypto projects")
            
        except Exception as e:
            logger.error(f"Error loading repository mappings: {e}")
            raise
    
    def get_coin_id(self, owner: str, repo_name: str) -> Optional[str]:
        """Get coin_id for a repository"""
        self.load_mappings()
        repo_key = f"{owner}/{repo_name}"
        mapping = self._repo_to_coin_map.get(repo_key)
        return mapping['coin_id'] if mapping else None
    
    def get_repo_info(self, owner: str, repo_name: str) -> Optional[Dict]:
        """Get complete repository information"""
        self.load_mappings()
        repo_key = f"{owner}/{repo_name}"
        return self._repo_to_coin_map.get(repo_key)
    
    def get_repositories_for_coin(self, coin_id: str) -> List[Dict]:
        """Get all repositories for a coin"""
        self.load_mappings()
        coin_data = self._coin_to_repos_map.get(coin_id)
        return coin_data['repositories'] if coin_data else []
    
    def get_all_repositories(self) -> List[Tuple[str, str, str]]:
        """Get all repositories as (owner, name, coin_id) tuples"""
        self.load_mappings()
        repos = []
        for repo_key, info in self._repo_to_coin_map.items():
            owner, name = repo_key.split('/', 1)
            repos.append((owner, name, info['coin_id']))
        return repos
    
    def get_primary_repositories(self) -> List[Tuple[str, str, str]]:
        """Get only primary repositories for each project"""
        self.load_mappings()
        repos = []
        for repo_key, info in self._repo_to_coin_map.items():
            if info['is_primary']:
                owner, name = repo_key.split('/', 1)
                repos.append((owner, name, info['coin_id']))
        return repos
    
    def is_primary_repo(self, owner: str, repo_name: str) -> bool:
        """Check if repository is the primary repo for its project"""
        info = self.get_repo_info(owner, repo_name)
        return info['is_primary'] if info else False
    
    def get_project_summary(self) -> Dict:
        """Get summary of all mapped projects"""
        self.load_mappings()
        return {
            'total_projects': len(self._coin_to_repos_map),
            'total_repositories': len(self._repo_to_coin_map),
            'primary_repositories': sum(1 for info in self._repo_to_coin_map.values() if info['is_primary']),
            'projects': list(self._coin_to_repos_map.keys())
        }
    
    def _parse_github_url(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        """Parse GitHub URL to extract owner and repository name"""
        try:
            from urllib.parse import urlparse
            
            url = url.rstrip('.git')
            parsed = urlparse(url)
            
            if parsed.netloc != 'github.com':
                return None, None
            
            path_parts = parsed.path.strip('/').split('/')
            if len(path_parts) >= 2:
                return path_parts[0], path_parts[1]
                
        except Exception as e:
            logger.warning(f"Error parsing GitHub URL {url}: {e}")
        
        return None, None


# Global instance
crypto_mapper = CryptoRepositoryMapper()