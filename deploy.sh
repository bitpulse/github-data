#!/bin/bash
# Simple deployment script for EC2

echo "🚀 Deploying GitHub Data Collector..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo "Please create .env from .env.example and add your credentials"
    exit 1
fi

# Pull latest code (optional)
if [ "$1" == "--pull" ]; then
    echo "📥 Pulling latest code..."
    git pull
fi

# Stop existing container
echo "🛑 Stopping existing container..."
docker-compose down

# Build new image
echo "🔨 Building Docker image..."
docker-compose build

# Start container
echo "▶️  Starting container..."
docker-compose up -d

# Show status
echo ""
echo "✅ Deployment complete!"
echo ""
docker-compose ps
echo ""
echo "📊 View logs with: docker-compose logs -f"
echo "🛑 Stop with: docker-compose down"