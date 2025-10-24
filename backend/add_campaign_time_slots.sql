-- Migration: Add time slot scheduling fields to sponsor_campaigns table

-- Add new columns for time slot scheduling
ALTER TABLE sponsor_campaigns ADD COLUMN IF NOT EXISTS start_time VARCHAR;
ALTER TABLE sponsor_campaigns ADD COLUMN IF NOT EXISTS end_time VARCHAR;
ALTER TABLE sponsor_campaigns ADD COLUMN IF NOT EXISTS days_of_week VARCHAR;
ALTER TABLE sponsor_campaigns ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE;

-- Add comments for documentation
COMMENT ON COLUMN sponsor_campaigns.start_time IS 'Start time in HH:MM format (e.g., 09:00)';
COMMENT ON COLUMN sponsor_campaigns.end_time IS 'End time in HH:MM format (e.g., 17:00)';
COMMENT ON COLUMN sponsor_campaigns.days_of_week IS 'JSON array of days (e.g., ["monday", "tuesday"])';
COMMENT ON COLUMN sponsor_campaigns.updated_at IS 'Timestamp of last update';
