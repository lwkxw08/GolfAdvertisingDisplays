
CREATE TABLE IF NOT EXISTS campaign_analytics (
    id SERIAL PRIMARY KEY,
    campaign_id INTEGER NOT NULL REFERENCES sponsor_campaigns(id) ON DELETE CASCADE,
    device_id INTEGER NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    impressions INTEGER DEFAULT 0,
    rotation_count INTEGER DEFAULT 0,
    display_duration_seconds INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_campaign_analytics_campaign ON campaign_analytics(campaign_id);
CREATE INDEX idx_campaign_analytics_device ON campaign_analytics(device_id);
CREATE INDEX idx_campaign_analytics_date ON campaign_analytics(date);
CREATE UNIQUE INDEX idx_campaign_analytics_unique ON campaign_analytics(campaign_id, device_id, date);

CREATE TABLE IF NOT EXISTS device_uptime_logs (
    id SERIAL PRIMARY KEY,
    device_id INTEGER NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    uptime_minutes INTEGER DEFAULT 0,
    downtime_minutes INTEGER DEFAULT 0,
    total_syncs INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_device_uptime_device ON device_uptime_logs(device_id);
CREATE INDEX idx_device_uptime_date ON device_uptime_logs(date);
CREATE UNIQUE INDEX idx_device_uptime_unique ON device_uptime_logs(device_id, date);

CREATE TABLE IF NOT EXISTS revenue_configurations (
    id SERIAL PRIMARY KEY,
    course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    device_cost_per_month DECIMAL(10, 2) DEFAULT 0.00,
    sponsorship_revenue_per_month DECIMAL(10, 2) DEFAULT 0.00,
    course_revenue_split_percentage DECIMAL(5, 2) DEFAULT 50.00,
    platform_revenue_split_percentage DECIMAL(5, 2) DEFAULT 50.00,
    notes TEXT,
    effective_from DATE NOT NULL,
    effective_to DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_revenue_config_course ON revenue_configurations(course_id);
CREATE INDEX idx_revenue_config_dates ON revenue_configurations(effective_from, effective_to);

CREATE TABLE IF NOT EXISTS revenue_analytics (
    id SERIAL PRIMARY KEY,
    course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    region_id INTEGER REFERENCES regions(id) ON DELETE SET NULL,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    total_device_costs DECIMAL(10, 2) DEFAULT 0.00,
    total_sponsorship_revenue DECIMAL(10, 2) DEFAULT 0.00,
    course_revenue_share DECIMAL(10, 2) DEFAULT 0.00,
    platform_revenue_share DECIMAL(10, 2) DEFAULT 0.00,
    net_revenue DECIMAL(10, 2) DEFAULT 0.00,
    active_devices_count INTEGER DEFAULT 0,
    active_campaigns_count INTEGER DEFAULT 0,
    total_impressions INTEGER DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_revenue_analytics_course ON revenue_analytics(course_id);
CREATE INDEX idx_revenue_analytics_region ON revenue_analytics(region_id);
CREATE INDEX idx_revenue_analytics_period ON revenue_analytics(period_start, period_end);

CREATE TABLE IF NOT EXISTS saved_reports (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    report_name VARCHAR(200) NOT NULL,
    report_type VARCHAR(50) NOT NULL, -- campaign_performance, device_uptime, revenue_analytics
    filters JSON,
    date_range_start DATE,
    date_range_end DATE,
    course_ids INTEGER[],
    region_ids INTEGER[],
    schedule_frequency VARCHAR(20), -- daily, weekly, monthly, null for one-time
    last_generated_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_saved_reports_user ON saved_reports(user_id);
CREATE INDEX idx_saved_reports_type ON saved_reports(report_type);

CREATE TABLE IF NOT EXISTS report_exports (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    saved_report_id INTEGER REFERENCES saved_reports(id) ON DELETE SET NULL,
    report_type VARCHAR(50) NOT NULL,
    export_format VARCHAR(10) NOT NULL, -- csv, pdf
    file_path VARCHAR(500),
    file_size_bytes INTEGER,
    filters JSON,
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_report_exports_user ON report_exports(user_id);
CREATE INDEX idx_report_exports_generated ON report_exports(generated_at);

CREATE OR REPLACE FUNCTION update_analytics_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_campaign_analytics_updated_at
    BEFORE UPDATE ON campaign_analytics
    FOR EACH ROW
    EXECUTE FUNCTION update_analytics_updated_at();

CREATE TRIGGER update_device_uptime_logs_updated_at
    BEFORE UPDATE ON device_uptime_logs
    FOR EACH ROW
    EXECUTE FUNCTION update_analytics_updated_at();

CREATE TRIGGER update_revenue_configurations_updated_at
    BEFORE UPDATE ON revenue_configurations
    FOR EACH ROW
    EXECUTE FUNCTION update_analytics_updated_at();

CREATE TRIGGER update_revenue_analytics_updated_at
    BEFORE UPDATE ON revenue_analytics
    FOR EACH ROW
    EXECUTE FUNCTION update_analytics_updated_at();

CREATE TRIGGER update_saved_reports_updated_at
    BEFORE UPDATE ON saved_reports
    FOR EACH ROW
    EXECUTE FUNCTION update_analytics_updated_at();
