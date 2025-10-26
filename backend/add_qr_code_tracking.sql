
CREATE TABLE IF NOT EXISTS qr_codes (
    id SERIAL PRIMARY KEY,
    campaign_id INTEGER REFERENCES sponsor_campaigns(id) ON DELETE CASCADE,
    course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    qr_code_key VARCHAR(100) UNIQUE NOT NULL,
    destination_url TEXT NOT NULL,
    title VARCHAR(200),
    description TEXT,
    qr_code_image_url TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_qr_codes_campaign ON qr_codes(campaign_id);
CREATE INDEX idx_qr_codes_course ON qr_codes(course_id);
CREATE INDEX idx_qr_codes_key ON qr_codes(qr_code_key);
CREATE INDEX idx_qr_codes_active ON qr_codes(is_active);

CREATE TABLE IF NOT EXISTS qr_code_scans (
    id SERIAL PRIMARY KEY,
    qr_code_id INTEGER NOT NULL REFERENCES qr_codes(id) ON DELETE CASCADE,
    scan_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ip_address VARCHAR(45),
    user_agent TEXT,
    device_type VARCHAR(50),
    browser VARCHAR(100),
    operating_system VARCHAR(100),
    country VARCHAR(100),
    city VARCHAR(100),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    referrer TEXT,
    is_unique_visitor BOOLEAN DEFAULT TRUE,
    session_id VARCHAR(100)
);

CREATE INDEX idx_qr_scans_qr_code ON qr_code_scans(qr_code_id);
CREATE INDEX idx_qr_scans_timestamp ON qr_code_scans(scan_timestamp);
CREATE INDEX idx_qr_scans_session ON qr_code_scans(session_id);
CREATE INDEX idx_qr_scans_unique ON qr_code_scans(is_unique_visitor);

CREATE TABLE IF NOT EXISTS qr_code_analytics (
    id SERIAL PRIMARY KEY,
    qr_code_id INTEGER NOT NULL REFERENCES qr_codes(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    total_scans INTEGER DEFAULT 0,
    unique_scans INTEGER DEFAULT 0,
    mobile_scans INTEGER DEFAULT 0,
    desktop_scans INTEGER DEFAULT 0,
    tablet_scans INTEGER DEFAULT 0,
    top_country VARCHAR(100),
    top_city VARCHAR(100),
    avg_scans_per_hour DECIMAL(10, 2) DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(qr_code_id, date)
);

CREATE INDEX idx_qr_analytics_qr_code ON qr_code_analytics(qr_code_id);
CREATE INDEX idx_qr_analytics_date ON qr_code_analytics(date);

CREATE OR REPLACE FUNCTION update_qr_code_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_qr_codes_updated_at
    BEFORE UPDATE ON qr_codes
    FOR EACH ROW
    EXECUTE FUNCTION update_qr_code_updated_at();

CREATE TRIGGER update_qr_code_analytics_updated_at
    BEFORE UPDATE ON qr_code_analytics
    FOR EACH ROW
    EXECUTE FUNCTION update_qr_code_updated_at();
