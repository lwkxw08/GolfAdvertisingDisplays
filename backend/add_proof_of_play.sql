
CREATE TABLE IF NOT EXISTS campaign_display_logs (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(36) UNIQUE NOT NULL,
    device_id INTEGER NOT NULL REFERENCES devices(id),
    campaign_id INTEGER REFERENCES sponsor_campaigns(id),
    content_type VARCHAR(20) NOT NULL,
    displayed_at TIMESTAMP WITH TIME ZONE NOT NULL,
    ended_at TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,
    image_hash VARCHAR(64) NOT NULL,
    hash_algo VARCHAR(10) DEFAULT 'sha256',
    creative_url TEXT,
    render_result BOOLEAN NOT NULL,
    connectivity_type VARCHAR(20),
    power_mode VARCHAR(20),
    firmware_version VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_display_logs_event_id ON campaign_display_logs(event_id);
CREATE INDEX IF NOT EXISTS idx_display_logs_device ON campaign_display_logs(device_id);
CREATE INDEX IF NOT EXISTS idx_display_logs_campaign ON campaign_display_logs(campaign_id);
CREATE INDEX IF NOT EXISTS idx_display_logs_displayed_at ON campaign_display_logs(displayed_at);
CREATE INDEX IF NOT EXISTS idx_display_logs_campaign_date ON campaign_display_logs(campaign_id, displayed_at);

COMMENT ON TABLE campaign_display_logs IS 'Proof-of-Play logging: immutable record of every campaign display for sponsor reporting and compliance';
