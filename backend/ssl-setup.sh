#!/bin/bash


echo "🔐 Golf CMS SSL Certificate Setup"
echo "=================================="

mkdir -p ssl

if [ -d "/etc/letsencrypt/live/golfcms.com" ]; then
    echo "✅ Found Let's Encrypt certificates, copying..."
    cp /etc/letsencrypt/live/golfcms.com/fullchain.pem ssl/
    cp /etc/letsencrypt/live/golfcms.com/privkey.pem ssl/
    echo "✅ SSL certificates copied successfully"
elif [ "$1" = "--generate-self-signed" ]; then
    echo "🔧 Generating self-signed certificates for development/testing..."
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout ssl/privkey.pem \
        -out ssl/fullchain.pem \
        -subj "/C=US/ST=State/L=City/O=Golf CMS/CN=golfcms.com" \
        -addext "subjectAltName=DNS:golfcms.com,DNS:www.golfcms.com,DNS:localhost"
    echo "✅ Self-signed certificates generated"
    echo "⚠️  WARNING: Self-signed certificates should only be used for development!"
else
    echo "❌ No SSL certificates found."
    echo ""
    echo "Options:"
    echo "1. Run with --generate-self-signed for development/testing"
    echo "2. Set up Let's Encrypt certificates:"
    echo "   sudo apt install certbot"
    echo "   sudo certbot certonly --standalone -d golfcms.com -d www.golfcms.com"
    echo "   Then run this script again"
    echo ""
    echo "3. Place your SSL certificates manually:"
    echo "   - Copy fullchain.pem to ssl/fullchain.pem"
    echo "   - Copy private key to ssl/privkey.pem"
    exit 1
fi

chmod 600 ssl/privkey.pem
chmod 644 ssl/fullchain.pem

echo "🎉 SSL setup complete!"
