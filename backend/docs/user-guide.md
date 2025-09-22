# Golf CMS User Guide

## Table of Contents

1. [Getting Started](#getting-started)
2. [Admin Portal](#admin-portal)
3. [Tenant Portal](#tenant-portal)
4. [Device Management](#device-management)
5. [Sponsor Campaigns](#sponsor-campaigns)
6. [Notices and Overrides](#notices-and-overrides)
7. [Analytics and Reporting](#analytics-and-reporting)
8. [Troubleshooting](#troubleshooting)

## Getting Started

### System Requirements

- Modern web browser (Chrome, Firefox, Safari, Edge)
- Internet connection for cloud-based management
- E-ink display devices with LTE/LoRa connectivity

### Account Types

**Admin Account**
- Full system access
- Manage all golf courses and devices
- Create and manage sponsor campaigns
- Access to analytics and billing

**Tenant Account**
- Course-specific access
- Create temporary notices
- View device status for their course
- Limited analytics access

### First Login

1. Navigate to the Golf CMS portal
2. Enter your email and password
3. Complete the onboarding wizard (new accounts)
4. Familiarize yourself with the dashboard

## Admin Portal

### Dashboard Overview

The admin dashboard provides a comprehensive view of:
- System-wide statistics
- Course management
- Device monitoring
- Revenue analytics
- System health

### Managing Courses

#### Adding a New Course

1. Click "Courses" tab
2. Click "Add Course" button
3. Fill in course details:
   - Course name
   - Location
   - Owner email
   - Contact information
4. Select subscription plan
5. Click "Create Course"

#### Course Settings

- **Basic Information**: Name, location, contact details
- **Subscription**: Plan type, billing status
- **Users**: Manage course staff access
- **Devices**: Assign and configure devices

### Device Management

#### Adding Devices

1. Navigate to "Devices" tab
2. Click "Add Device"
3. Enter device information:
   - Device name (e.g., "Tee Box 1")
   - Unique device ID
   - Course assignment
   - Location details
4. Save device configuration

#### Device Status Monitoring

- **Online/Offline Status**: Real-time connectivity
- **Last Sync**: When device last checked for updates
- **Battery Level**: Power status (if supported)
- **Signal Strength**: Network connectivity quality

### Sponsor Campaign Management

#### Creating Campaigns

1. Go to "Campaigns" tab
2. Click "Create Campaign"
3. Fill campaign details:
   - Sponsor name
   - Target devices
   - Campaign duration
   - Rotation settings
4. Upload creative assets (up to 5 per device)
5. Set rotation interval (hours/days/weeks/months)
6. Activate campaign

#### Campaign Settings

- **Duration**: Start and end dates
- **Rotation**: How often content changes
- **Priority**: Campaign importance level
- **Targeting**: Specific devices or device groups

### Revenue Analytics

#### Key Metrics

- **Monthly Recurring Revenue (MRR)**
- **Annual Recurring Revenue (ARR)**
- **Subscriber count by plan**
- **Churn rate and growth metrics**

#### Tenant Analytics

- Course-by-course performance
- Device utilization rates
- Engagement metrics
- Onboarding completion status

## Tenant Portal

### Dashboard Features

Tenant users see a simplified dashboard with:
- Their course devices
- Active notices
- Device status
- Basic analytics

### Creating Notices

#### Notice Types

- **Temporary Announcements**: Course conditions, events
- **Emergency Alerts**: Weather warnings, course closures
- **Promotional Messages**: Pro shop specials, tournaments

#### Creating a Notice

1. Click "Create Notice"
2. Enter notice details:
   - Title (brief description)
   - Content (detailed message)
   - Target devices
   - Start time
3. Review and publish

#### Notice Limitations

- Maximum duration: 1 hour
- Automatically expires
- Overrides sponsor content temporarily
- Limited to assigned course devices

### Device Monitoring

Tenant users can view:
- Device online/offline status
- Last sync times
- Current content display
- Notice history

## Device Management

### Device Setup

#### Initial Configuration

1. Power on the e-ink display device
2. Connect to cellular/LoRa network
3. Device automatically registers with system
4. Admin assigns device to course
5. Device begins content synchronization

#### Sync Process

Devices automatically:
- Check for updates every 5-15 minutes
- Download new content when available
- Report status and analytics
- Handle network interruptions gracefully

### Content Display Priority

1. **Active Notices** (highest priority)
   - Temporary overrides
   - Maximum 1 hour duration
   - Course-specific

2. **Sponsor Campaigns** (normal priority)
   - Rotating advertisements
   - Scheduled content
   - Long-term campaigns

3. **Default Content** (fallback)
   - Course branding
   - Basic information
   - System messages

## Sponsor Campaigns

### Campaign Planning

#### Content Guidelines

- **Image Format**: 1600×1200 pixels recommended
- **File Types**: JPEG, PNG
- **Color**: Optimized for e-ink displays
- **Text**: High contrast, readable fonts
- **Branding**: Include sponsor logos and contact info

#### Rotation Strategies

- **Time-based**: Change content at set intervals
- **Event-based**: Trigger on specific conditions
- **Seasonal**: Adjust for weather or events
- **Performance-based**: Optimize based on engagement

### Campaign Management

#### Monitoring Performance

- **Impression Counts**: How often content is displayed
- **Device Reach**: Number of devices showing campaign
- **Duration Tracking**: Total display time
- **Engagement Metrics**: Device interaction data

#### Optimization Tips

- Test different creative variations
- Adjust rotation timing based on play patterns
- Monitor device uptime and connectivity
- Coordinate with course events and seasons

## Notices and Overrides

### Best Practices

#### When to Use Notices

- **Course Conditions**: Wet conditions, cart path only
- **Temporary Rules**: Preferred lies, ground under repair
- **Events**: Tournaments, maintenance, closures
- **Safety**: Weather warnings, hazard alerts

#### Writing Effective Notices

- Keep messages concise and clear
- Use action-oriented language
- Include specific details (holes, times, conditions)
- Avoid jargon or complex terminology

### Notice Management

#### Scheduling

- **Immediate**: Publish notice right away
- **Scheduled**: Set future start time
- **Duration**: Maximum 1 hour per notice
- **Targeting**: Specific devices or hole ranges

#### Monitoring

- Track notice display status
- Monitor device acknowledgment
- Review notice history and effectiveness
- Coordinate with course operations

## Analytics and Reporting

### Admin Analytics

#### System Overview

- Total devices and online status
- Impression counts across all courses
- Revenue metrics and subscription status
- System performance and uptime

#### Course Performance

- Device utilization by course
- Content engagement metrics
- Notice frequency and effectiveness
- Tenant activity levels

### Tenant Analytics

#### Course Metrics

- Device status for their course
- Notice history and performance
- Basic engagement statistics
- Uptime and connectivity reports

#### Usage Insights

- Peak usage times
- Most effective notice types
- Device performance trends
- Seasonal patterns

### Reporting Features

#### Automated Reports

- Daily device status summaries
- Weekly performance reports
- Monthly analytics dashboards
- Custom report scheduling

#### Export Options

- CSV data exports
- PDF report generation
- API access for custom integrations
- Real-time dashboard widgets

## Troubleshooting

### Common Issues

#### Device Connectivity

**Problem**: Device shows as offline
**Solutions**:
- Check cellular/network signal strength
- Verify device power and battery status
- Restart device if necessary
- Contact support for hardware issues

**Problem**: Content not updating
**Solutions**:
- Verify campaign is active and scheduled
- Check device sync timestamps
- Ensure content meets format requirements
- Review network connectivity

#### Notice Problems

**Problem**: Notice not displaying
**Solutions**:
- Confirm notice is within 1-hour limit
- Check device targeting settings
- Verify notice start time and scheduling
- Ensure device is online and syncing

**Problem**: Notice expired too quickly
**Solutions**:
- Review notice duration settings
- Check for conflicting notices
- Verify system time synchronization
- Contact support for extension requests

### Getting Help

#### Support Channels

- **Email Support**: support@golfcms.com
- **Phone Support**: 1-800-GOLF-CMS
- **Live Chat**: Available in admin portal
- **Knowledge Base**: docs.golfcms.com

#### System Status

- **Status Page**: status.golfcms.com
- **Maintenance Windows**: Announced in advance
- **Emergency Alerts**: Sent via email and SMS
- **Performance Monitoring**: Real-time system health

### Best Practices

#### System Maintenance

- Regularly review device status
- Keep content fresh and relevant
- Monitor analytics for optimization opportunities
- Maintain good communication with course staff

#### Security

- Use strong passwords
- Enable two-factor authentication
- Regularly review user access
- Report suspicious activity immediately

#### Performance Optimization

- Optimize image sizes for faster sync
- Schedule content updates during low-traffic periods
- Monitor network usage and costs
- Plan campaigns around course events and seasons
