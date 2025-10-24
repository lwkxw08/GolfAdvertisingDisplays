
CREATE TABLE IF NOT EXISTS device_health_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id INTEGER NOT NULL,
    battery_level REAL,
    battery_voltage REAL,
    is_charging BOOLEAN DEFAULT FALSE,
    connectivity_type VARCHAR(20),
    signal_strength REAL,
    wifi_ssid VARCHAR(100),
    temperature REAL,
    cpu_usage REAL,
    memory_usage REAL,
    storage_usage REAL,
    display_errors INTEGER DEFAULT 0,
    last_error TEXT,
    uptime_seconds INTEGER,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_device_health_device_timestamp ON device_health_metrics(device_id, timestamp);

CREATE TABLE IF NOT EXISTS device_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id INTEGER NOT NULL,
    alert_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    is_resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMP,
    resolved_by INTEGER,
    metadata TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE,
    FOREIGN KEY (resolved_by) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_device_alerts_device ON device_alerts(device_id);
CREATE INDEX IF NOT EXISTS idx_device_alerts_type ON device_alerts(alert_type);
CREATE INDEX IF NOT EXISTS idx_device_alerts_resolved ON device_alerts(is_resolved);

CREATE TABLE IF NOT EXISTS alert_notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id INTEGER NOT NULL,
    notification_type VARCHAR(20) NOT NULL,
    recipient VARCHAR(200) NOT NULL,
    status VARCHAR(20) NOT NULL,
    sent_at TIMESTAMP,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (alert_id) REFERENCES device_alerts(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_alert_notifications_status ON alert_notifications(status);

CREATE TABLE IF NOT EXISTS device_remote_commands (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id INTEGER NOT NULL,
    command_type VARCHAR(50) NOT NULL,
    command_data TEXT,
    status VARCHAR(20) NOT NULL,
    issued_by INTEGER NOT NULL,
    issued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    executed_at TIMESTAMP,
    result TEXT,
    error_message TEXT,
    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE,
    FOREIGN KEY (issued_by) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_device_commands_device ON device_remote_commands(device_id);
CREATE INDEX IF NOT EXISTS idx_device_commands_status ON device_remote_commands(status);
