# Golf CMS - Multi-Tenant Digital Tee Box Management System

A comprehensive SaaS platform for managing digital e-ink displays on golf course tee boxes, featuring sponsor campaigns, temporary notices, and multi-tenant architecture.

## Features

### Core CMS Features
- **Multi-tenant Architecture**: Secure tenant isolation with role-based access control
- **Device Management**: Register and monitor tee box displays across multiple golf courses
- **Sponsor Campaigns**: Upload and schedule up to 5 creative assets per device with flexible rotation
- **Temporary Notices**: Course staff can create time-limited overrides (max 1 hour)
- **Real-time Sync**: Devices sync playlists every 5-15 minutes via API

### SaaS Features
- **User Registration & Onboarding**: Streamlined signup flow for new golf courses
- **Stripe Billing Integration**: Subscription management with multiple plan tiers
- **Supabase Storage**: Cloud file storage for sponsor creative assets
- **Email Notifications**: Automated emails for user invites, billing, and system alerts
- **Analytics & Reporting**: Usage metrics, device uptime, and revenue analytics
- **Admin Super-User Portal**: Manage all tenants, billing, and system settings

## Technology Stack

### Backend
- **FastAPI**: Modern Python web framework
- **SQLAlchemy**: Database ORM with PostgreSQL
- **Supabase**: PostgreSQL database and file storage
- **Stripe**: Payment processing and subscription management
- **JWT Authentication**: Secure token-based authentication

### Frontend
- **React**: Modern UI framework with TypeScript
- **Tailwind CSS**: Utility-first CSS framework
- **Shadcn/UI**: Component library for consistent design
- **Recharts**: Data visualization for analytics

## User Roles

### Admin (Super-User)
- Full system access across all tenants
- Manage courses, devices, and sponsor campaigns
- View system-wide analytics and billing
- Configure email templates and system settings

### Client Tenant (Course Staff)
- Access limited to their own course
- Create temporary notices (max 1 hour duration)
- View device status and active campaigns
- Cannot modify sponsor content

## API Endpoints

### Authentication
- `POST /auth/login` - User login
- `POST /auth/register` - User registration
- `POST /auth/register-course` - New course registration

### Course Management
- `GET /admin/courses` - List all courses (admin only)
- `POST /admin/courses` - Create new course
- `GET /courses/{course_id}` - Get course details

### Device Management
- `GET /admin/devices` - List all devices (admin only)
- `GET /courses/{course_id}/devices` - List course devices
- `POST /admin/devices` - Create new device

### Campaign Management
- `GET /admin/campaigns` - List all campaigns
- `POST /admin/campaigns` - Create new campaign with file upload

### Analytics
- `GET /admin/analytics/summary` - System-wide analytics
- `GET /admin/analytics/courses` - Per-course analytics

### Billing
- `GET /admin/subscriptions` - List all subscriptions
- `POST /stripe/webhook` - Stripe webhook handler

## Database Schema

### Core Tables
- `users` - User accounts with role-based access
- `courses` - Golf course information and settings
- `devices` - Tee box display devices
- `sponsor_campaigns` - Sponsor creative campaigns
- `notices` - Temporary course notices

### SaaS Tables
- `subscriptions` - Stripe subscription management
- `device_analytics` - Usage and performance metrics
- `email_templates` - System email templates
- `email_logs` - Email delivery tracking

## Deployment

### Backend
- Deployed on Fly.io: https://app-mtdyxjgp.fly.dev/
- Environment variables configured for production
- Automatic database migrations on deployment

### Frontend
- Deployed on Devin Apps: https://web-app-fpcoy3i7.devinapps.com/
- React build optimized for production
- Environment variables for API endpoints

## Development Setup

### Prerequisites
- Python 3.12+
- Node.js 18+
- PostgreSQL (or Supabase account)
- Stripe account for billing

### Backend Setup
```bash
cd backend
poetry install
cp .env.example .env
# Configure environment variables
poetry run python migrate_database.py
poetry run fastapi dev app/main.py
```

### Frontend Setup
```bash
cd frontend
npm install
cp .env.example .env
# Configure API URL
npm run dev
```

## Environment Variables

### Backend (.env)
```
DATABASE_URL=postgresql://...
SUPABASE_URL=https://...
SUPABASE_KEY=...
STRIPE_SECRET_KEY=sk_...
STRIPE_WEBHOOK_SECRET=whsec_...
SMTP_USERNAME=...
SMTP_PASSWORD=...
```

### Frontend (.env)
```
VITE_API_URL=https://app-mtdyxjgp.fly.dev
```

## Demo Accounts

- **Admin**: admin@golfcms.com / admin123
- **Tenant**: staff@pinevalley.com / staff123

## License

MIT License - see LICENSE file for details
