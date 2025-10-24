-- Migration: Add time slot scheduling fields to sponsor_campaigns table and orientation to devices table

-- Add new columns for time slot scheduling to sponsor_campaigns
ALTER TABLE sponsor_campaigns ADD COLUMN IF NOT EXISTS start_time VARCHAR;
ALTER TABLE sponsor_campaigns ADD COLUMN IF NOT EXISTS end_time VARCHAR;
ALTER TABLE sponsor_campaigns ADD COLUMN IF NOT EXISTS days_of_week VARCHAR;
ALTER TABLE sponsor_campaigns ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE;

DO $$ BEGIN
    CREATE TYPE deviceorientation AS ENUM ('PORTRAIT', 'LANDSCAPE');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

ALTER TABLE devices ADD COLUMN IF NOT EXISTS orientation deviceorientation DEFAULT 'PORTRAIT'::deviceorientation;

-- Add comments for documentation
COMMENT ON COLUMN sponsor_campaigns.start_time IS 'Start time in HH:MM format (e.g., 09:00)';
COMMENT ON COLUMN sponsor_campaigns.end_time IS 'End time in HH:MM format (e.g., 17:00)';
COMMENT ON COLUMN sponsor_campaigns.days_of_week IS 'JSON array of days (e.g., ["monday", "tuesday"])';
COMMENT ON COLUMN sponsor_campaigns.updated_at IS 'Timestamp of last update';
COMMENT ON COLUMN devices.orientation IS 'Device screen orientation: PORTRAIT or LANDSCAPE';

-- Add recurrence_pattern field to notice_templates table
ALTER TABLE notice_templates ADD COLUMN IF NOT EXISTS recurrence_pattern JSON;

COMMENT ON COLUMN notice_templates.recurrence_pattern IS 'Recurring pattern: {"type": "daily"|"weekly", "days": [...], "time": "HH:MM"}';
