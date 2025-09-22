# Golf CMS API Documentation

## Overview

The Golf CMS API provides comprehensive management capabilities for multi-tenant e-ink golf tee box display systems. This RESTful API supports course management, device control, sponsor campaigns, and real-time content delivery.

## Base URL

- Production: `https://app-mtdyxjgp.fly.dev`
- Development: `http://localhost:8000`

## Authentication

All API endpoints require JWT authentication. Include the token in the Authorization header:

```
Authorization: Bearer <your-jwt-token>
```

### Login

```http
POST /auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password"
}
```

## User Roles

- **Admin**: Full system access, can manage all courses and devices
- **Client Tenant**: Limited to their own course, can create notices only

## Core Endpoints

### Courses

#### List Courses (Admin only)
```http
GET /admin/courses
```

#### Create Course (Admin only)
```http
POST /admin/courses
Content-Type: application/json

{
  "name": "Pine Valley Golf Club",
  "location": "New Jersey, USA"
}
```

### Devices

#### List Devices
```http
GET /devices
```

#### Create Device (Admin only)
```http
POST /admin/devices
Content-Type: application/json

{
  "name": "Tee Box 1",
  "device_id": "TB001",
  "course_id": 1
}
```

#### Get Device Playlist
```http
GET /devices/{device_id}/playlist
```

### Sponsor Campaigns

#### Create Campaign (Admin only)
```http
POST /admin/campaigns
Content-Type: multipart/form-data

sponsor_name: "Local Pro Shop"
device_id: 1
start_date: "2024-01-01T00:00:00"
end_date: "2024-12-31T23:59:59"
rotation_interval: 7
rotation_unit: "days"
creative: <file>
```

### Notices (Client Tenant)

#### Create Notice
```http
POST /notices
Content-Type: application/json

{
  "title": "Preferred Lies in Play",
  "content": "Due to recent rain, preferred lies are in effect on all fairways.",
  "device_id": 1,
  "start_time": "2024-01-01T08:00:00"
}
```

## Analytics Endpoints

### System Analytics (Admin only)

#### Revenue Analytics
```http
GET /admin/analytics/revenue
```

Response:
```json
{
  "total_mrr": 2999.70,
  "total_arr": 35996.40,
  "total_subscribers": 15,
  "plan_breakdown": {
    "basic": {
      "subscribers": 10,
      "monthly_revenue": 299.90,
      "price_per_month": 29.99
    }
  }
}
```

#### Tenant Usage Analytics
```http
GET /admin/analytics/tenants
```

#### System Performance Metrics
```http
GET /admin/analytics/performance
```

### Course Analytics

#### Analytics Summary
```http
GET /admin/analytics/summary
```

#### Course-Specific Analytics
```http
GET /admin/analytics/course/{course_id}
```

## Backup & Recovery (Admin only)

#### Create Backup
```http
POST /admin/backup/create
```

#### Export Data
```http
GET /admin/backup/export?course_id=1
```

#### Schedule Automated Backup
```http
POST /admin/backup/schedule
```

## Monitoring & Health

#### Basic Health Check
```http
GET /monitoring/health
```

#### Detailed Health Check
```http
GET /monitoring/health/detailed
```

#### System Metrics
```http
GET /monitoring/metrics
```

## Onboarding

#### Get Onboarding Progress
```http
GET /onboarding/progress/{course_id}
```

#### Complete Onboarding
```http
POST /onboarding/complete/{course_id}
```

## Rate Limiting

The API implements rate limiting to ensure fair usage:

- Authentication endpoints: 5 requests per 5 minutes
- Registration endpoints: 3 requests per hour
- General API endpoints: 100 requests per minute

Rate limit headers are included in responses:
- `X-RateLimit-Limit`: Request limit per window
- `X-RateLimit-Remaining`: Remaining requests in current window
- `X-RateLimit-Reset`: Time when the rate limit resets

## Error Handling

The API returns standard HTTP status codes:

- `200 OK`: Successful request
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

Error responses include details:
```json
{
  "error": "Validation Error",
  "message": "Invalid email format",
  "details": {
    "field": "email",
    "code": "invalid_format"
  }
}
```

## Webhooks

### Device Status Updates

Devices can report their status via webhook:

```http
POST /webhooks/device-status
Content-Type: application/json

{
  "device_id": "TB001",
  "status": "online",
  "last_sync": "2024-01-01T12:00:00Z",
  "uptime_hours": 24.5,
  "impressions_count": 150
}
```

## SDKs and Libraries

Official SDKs are available for:
- JavaScript/TypeScript
- Python
- PHP

## Support

For API support, contact:
- Email: support@golfcms.com
- Documentation: https://docs.golfcms.com
- Status Page: https://status.golfcms.com
