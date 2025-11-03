-- Add device_uptime_windows table for idempotent uptime tracking
-- This table stores 5-minute windows of uptime data from devices
-- The unique constraint on (device_id, window_start) ensures idempotency

CREATE TABLE IF NOT EXISTS device_uptime_windows (
    id SERIAL PRIMARY KEY,
    device_id INTEGER NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    window_start TIMESTAMPTZ NOT NULL,
    window_end TIMESTAMPTZ NOT NULL,
    uptime_minutes INTEGER DEFAULT 0,
    downtime_minutes INTEGER DEFAULT 0,
    total_syncs INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT unique_device_window UNIQUE (device_id, window_start)
);

CREATE INDEX IF NOT EXISTS idx_uptime_windows_device ON device_uptime_windows(device_id);
CREATE INDEX IF NOT EXISTS idx_uptime_windows_start ON device_uptime_windows(window_start);
CREATE INDEX IF NOT EXISTS idx_uptime_windows_device_start ON device_uptime_windows(device_id, window_start);

COMMENT ON TABLE device_uptime_windows IS 'Idempotent 5-minute windows of device uptime data';
COMMENT ON COLUMN device_uptime_windows.window_start IS 'Start of 5-minute window (minute-aligned UTC)';
COMMENT ON COLUMN device_uptime_windows.uptime_minutes IS 'Minutes device was online/reachable in this window';
COMMENT ON COLUMN device_uptime_windows.downtime_minutes IS 'Minutes device was offline/unreachable in this window';
