# Custom Domain Setup for Golf CMS

## Overview
This guide explains how to set up a custom domain (e.g., golfcms.com) for the Golf CMS production deployment.

## Prerequisites
- Domain name registered and DNS access
- SSL certificates (Let's Encrypt recommended)
- Production server with Docker and nginx

## DNS Configuration

### A Records
Point your domain to your server IP:
```
A    golfcms.com        -> YOUR_SERVER_IP
A    www.golfcms.com    -> YOUR_SERVER_IP
A    api.golfcms.com    -> YOUR_SERVER_IP
```

### CNAME Records (Alternative)
If using a load balancer or CDN:
```
CNAME  www.golfcms.com    -> golfcms.com
CNAME  api.golfcms.com    -> golfcms.com
```

## SSL Certificate Setup

### Option 1: Let's Encrypt (Recommended)
```bash
# Install certbot
sudo apt update && sudo apt install certbot

# Generate certificates
sudo certbot certonly --standalone \
  -d golfcms.com \
  -d www.golfcms.com \
  -d api.golfcms.com

# Copy certificates to project
sudo cp /etc/letsencrypt/live/golfcms.com/fullchain.pem ssl/
sudo cp /etc/letsencrypt/live/golfcms.com/privkey.pem ssl/
sudo chown $USER:$USER ssl/*.pem
```

### Option 2: Self-Signed (Development Only)
```bash
./ssl-setup.sh --generate-self-signed
```

## Environment Configuration

Update `.env.production`:
```bash
# Custom domain configuration
FRONTEND_URL=https://golfcms.com
CORS_ORIGINS=https://golfcms.com,https://www.golfcms.com,https://api.golfcms.com

# Update nginx server_name in nginx.conf
server_name golfcms.com www.golfcms.com api.golfcms.com;
```

## Deployment Steps

1. **Update DNS records** to point to your server
2. **Generate SSL certificates** using Let's Encrypt
3. **Update environment variables** with custom domain
4. **Deploy with Docker Compose**:
   ```bash
   ./deploy-production.sh
   ```
5. **Verify deployment**:
   ```bash
   curl -f https://golfcms.com/healthz
   ```

## Frontend Deployment

Update frontend environment and redeploy:
```bash
# Update frontend/.env
REACT_APP_API_URL=https://api.golfcms.com

# Redeploy frontend to custom domain
# (Instructions depend on hosting provider)
```

## Monitoring

- Health checks: `https://golfcms.com/healthz`
- Metrics: `https://golfcms.com/monitoring/metrics`
- API docs: `https://golfcms.com/docs`

## Troubleshooting

### Common Issues
1. **DNS propagation**: Wait 24-48 hours for global DNS propagation
2. **SSL certificate errors**: Verify certificate paths and permissions
3. **CORS errors**: Ensure all domains are listed in CORS_ORIGINS
4. **Rate limiting**: Check nginx rate limiting configuration

### Logs
```bash
# View application logs
docker-compose -f docker-compose.prod.yml logs golf-cms-api

# View nginx logs
docker-compose -f docker-compose.prod.yml logs nginx
```
