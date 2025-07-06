#!/usr/bin/env python3
"""
Test script to verify the setup is correct
"""

import sys
import os

print("Testing GitHub Data Collector Setup...")
print("=" * 50)

# Test Python version
print(f"Python version: {sys.version}")
if sys.version_info < (3, 8):
    print("❌ ERROR: Python 3.8+ is required")
    sys.exit(1)
else:
    print("✅ Python version OK")

# Test imports
try:
    import pymongo
    print(f"✅ PyMongo version: {pymongo.__version__}")
except ImportError:
    print("❌ ERROR: PyMongo not installed. Run: pip install -r requirements.txt")
    sys.exit(1)

try:
    import github
    print(f"✅ PyGithub installed")
except ImportError:
    print("❌ ERROR: PyGithub not installed. Run: pip install -r requirements.txt")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    print("✅ python-dotenv installed")
except ImportError:
    print("❌ ERROR: python-dotenv not installed. Run: pip install -r requirements.txt")
    sys.exit(1)

# Test local imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from src.config.settings import settings
    print("✅ Local imports working")
except ImportError as e:
    print(f"❌ ERROR: Cannot import local modules: {e}")
    sys.exit(1)

# Test environment configuration
print("\nChecking environment configuration...")
if not os.path.exists('.env'):
    print("❌ ERROR: .env file not found. Copy .env.example to .env and configure it")
    sys.exit(1)
else:
    print("✅ .env file exists")

try:
    from src.config.settings import validate_settings
    validate_settings()
    print("✅ Environment variables configured correctly")
except ValueError as e:
    print(f"❌ ERROR: {e}")
    print("   Please edit .env and add your GitHub token and MongoDB URI")
    sys.exit(1)

# Test MongoDB connection
print("\nTesting MongoDB connection...")
try:
    from src.storage.mongodb_client import mongodb_client
    mongodb_client.connect()
    print("✅ MongoDB connection successful")
    
    # Check MongoDB version
    server_info = mongodb_client.client.server_info()
    version = server_info.get('version', 'unknown')
    print(f"   MongoDB version: {version}")
    
    # Check for time series support
    major_version = int(version.split('.')[0]) if version != 'unknown' else 0
    if major_version < 5:
        print(f"⚠️  WARNING: MongoDB {version} detected. Version 5.0+ is required for time series collections")
    
    mongodb_client.close()
except Exception as e:
    print(f"❌ ERROR: Cannot connect to MongoDB: {e}")
    print("   Make sure MongoDB is running on localhost:27017 or update MONGODB_URI in .env")
    sys.exit(1)

# Test GitHub API
print("\nTesting GitHub API...")
try:
    from src.collectors.base_collector import BaseCollector
    
    class TestCollector(BaseCollector):
        def collect(self, *args, **kwargs):
            pass
        def get_collection_name(self):
            return "test"
    
    collector = TestCollector()
    rate_limit = collector.check_rate_limit()
    
    print(f"✅ GitHub API connection successful")
    print(f"   Rate limit: {rate_limit['core']['remaining']}/{rate_limit['core']['limit']} requests remaining")
    
except Exception as e:
    print(f"❌ ERROR: Cannot connect to GitHub API: {e}")
    print("   Check your GITHUB_TOKEN in .env")
    sys.exit(1)

print("\n" + "=" * 50)
print("✅ All tests passed! The system is ready to use.")
print("\nNext steps:")
print("1. Run 'python main.py --once' to collect data once")
print("2. Run 'python main.py' to start continuous collection")
print("3. Run 'python examples/view_data.py --summary' to view collected data")