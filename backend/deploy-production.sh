#!/bin/bash

set -e

echo "🚀 Starting Golf CMS production deployment..."

if [ -z "$DATABASE_URL" ]; then
    echo "❌ DATABASE_URL environment variable is required"
    exit 1
fi

if [ -z "$SUPABASE_URL" ]; then
    echo "❌ SUPABASE_URL environment variable is required"
    exit 1
fi

if [ -z "$SUPABASE_KEY" ]; then
    echo "❌ SUPABASE_KEY environment variable is required"
    exit 1
fi

mkdir -p logs
mkdir -p ssl

if [ ! -f ssl/fullchain.pem ]; then
    echo "🔐 Generating self-signed SSL certificates..."
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout ssl/privkey.pem \
        -out ssl/fullchain.pem \
        -subj "/C=US/ST=State/L=City/O=Organization/CN=golfcms.com"
    echo "⚠️  Note: Using self-signed certificates. Replace with real SSL certificates for production."
fi

echo "🏗️  Building Docker containers..."
docker-compose -f docker-compose.prod.yml build

echo "🚀 Starting services..."
docker-compose -f docker-compose.prod.yml up -d

echo "⏳ Waiting for services to start..."
sleep 30

echo "🏥 Performing health check..."
if curl -f http://localhost/healthz; then
    echo "✅ Golf CMS is running successfully!"
    echo "🌐 API available at: http://localhost"
    echo "📊 Health check: http://localhost/healthz"
    echo "📚 API docs: http://localhost/docs"
else
    echo "❌ Health check failed. Check logs:"
    docker-compose -f docker-compose.prod.yml logs
    exit 1
fi

echo "🎉 Production deployment complete!"
