#!/usr/bin/env python3

import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./golf_cms.db")

def run_migration():
    """Create enterprise tables and update existing ones"""
    engine = create_engine(DATABASE_URL)
    
    migration_sql = """
    -- Create regions table
    CREATE TABLE IF NOT EXISTS regions (
        id SERIAL PRIMARY KEY,
        name VARCHAR NOT NULL,
        description TEXT,
        is_active BOOLEAN DEFAULT true,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Create audit_logs table
    CREATE TABLE IF NOT EXISTS audit_logs (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id),
        action VARCHAR NOT NULL,
        resource_type VARCHAR NOT NULL,
        resource_id VARCHAR,
        details JSONB,
        ip_address VARCHAR,
        user_agent VARCHAR,
        timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Create custom_dashboards table
    CREATE TABLE IF NOT EXISTS custom_dashboards (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id) NOT NULL,
        name VARCHAR NOT NULL,
        layout JSONB NOT NULL,
        filters JSONB,
        is_shared BOOLEAN DEFAULT false,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Create device_diagnostics table
    CREATE TABLE IF NOT EXISTS device_diagnostics (
        id SERIAL PRIMARY KEY,
        device_id INTEGER REFERENCES devices(id) NOT NULL,
        battery_level FLOAT,
        signal_strength FLOAT,
        temperature FLOAT,
        memory_usage FLOAT,
        storage_usage FLOAT,
        firmware_version VARCHAR,
        last_error TEXT,
        diagnostic_data JSONB,
        timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Create notice_styles table
    CREATE TABLE IF NOT EXISTS notice_styles (
        id SERIAL PRIMARY KEY,
        name VARCHAR NOT NULL,
        font_family VARCHAR NOT NULL DEFAULT 'arial',
        font_size INTEGER NOT NULL DEFAULT 24,
        font_weight VARCHAR NOT NULL DEFAULT 'normal',
        text_color VARCHAR NOT NULL DEFAULT '#000000',
        background_color VARCHAR NOT NULL DEFAULT '#FFFFFF',
        border_style VARCHAR,
        padding INTEGER NOT NULL DEFAULT 10,
        text_align VARCHAR NOT NULL DEFAULT 'center',
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Create advanced_schedules table
    CREATE TABLE IF NOT EXISTS advanced_schedules (
        id SERIAL PRIMARY KEY,
        name VARCHAR NOT NULL,
        schedule_type VARCHAR NOT NULL,
        conditions JSONB,
        start_date TIMESTAMP WITH TIME ZONE NOT NULL,
        end_date TIMESTAMP WITH TIME ZONE NOT NULL,
        recurrence_pattern JSONB,
        priority INTEGER DEFAULT 1,
        is_active BOOLEAN DEFAULT true,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Create sso_providers table
    CREATE TABLE IF NOT EXISTS sso_providers (
        id SERIAL PRIMARY KEY,
        name VARCHAR NOT NULL,
        provider_type VARCHAR NOT NULL,
        configuration JSONB NOT NULL,
        is_active BOOLEAN DEFAULT true,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Add new columns to existing tables
    ALTER TABLE users ADD COLUMN IF NOT EXISTS region_id INTEGER REFERENCES regions(id);
    ALTER TABLE users ADD COLUMN IF NOT EXISTS permissions TEXT;
    ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login TIMESTAMP WITH TIME ZONE;
    ALTER TABLE users ADD COLUMN IF NOT EXISTS sso_provider VARCHAR;
    ALTER TABLE users ADD COLUMN IF NOT EXISTS sso_user_id VARCHAR;
    
    ALTER TABLE courses ADD COLUMN IF NOT EXISTS region_id INTEGER REFERENCES regions(id);
    
    ALTER TABLE devices ADD COLUMN IF NOT EXISTS firmware_version VARCHAR;
    ALTER TABLE devices ADD COLUMN IF NOT EXISTS hardware_version VARCHAR;
    ALTER TABLE devices ADD COLUMN IF NOT EXISTS remote_update_enabled BOOLEAN DEFAULT true;
    ALTER TABLE devices ADD COLUMN IF NOT EXISTS diagnostic_enabled BOOLEAN DEFAULT true;
    
    ALTER TABLE notices ADD COLUMN IF NOT EXISTS duration_minutes INTEGER;
    ALTER TABLE notices ADD COLUMN IF NOT EXISTS style_id INTEGER REFERENCES notice_styles(id);
    ALTER TABLE notices ADD COLUMN IF NOT EXISTS schedule_id INTEGER REFERENCES advanced_schedules(id);
    
    ALTER TABLE sponsor_campaigns ADD COLUMN IF NOT EXISTS schedule_id INTEGER REFERENCES advanced_schedules(id);
    ALTER TABLE sponsor_campaigns ADD COLUMN IF NOT EXISTS ab_test_group VARCHAR;
    ALTER TABLE sponsor_campaigns ADD COLUMN IF NOT EXISTS performance_metrics TEXT;
    
    -- Update existing notices to have duration_minutes based on end_time - start_time
    UPDATE notices 
    SET duration_minutes = EXTRACT(EPOCH FROM (end_time - start_time)) / 60 
    WHERE duration_minutes IS NULL;
    
    -- Create indexes for performance
    CREATE INDEX IF NOT EXISTS idx_audit_logs_user_timestamp ON audit_logs(user_id, timestamp);
    CREATE INDEX IF NOT EXISTS idx_audit_logs_resource ON audit_logs(resource_type, resource_id);
    CREATE INDEX IF NOT EXISTS idx_device_diagnostics_device_timestamp ON device_diagnostics(device_id, timestamp);
    CREATE INDEX IF NOT EXISTS idx_custom_dashboards_user ON custom_dashboards(user_id);
    
    -- Insert default notice styles
    INSERT INTO notice_styles (name, font_family, font_size, font_weight, text_color, background_color)
    VALUES 
        ('Default', 'arial', 24, 'normal', '#000000', '#FFFFFF'),
        ('Large Bold', 'arial', 32, 'bold', '#000000', '#FFFFFF'),
        ('Warning', 'impact', 28, 'bold', '#FF0000', '#FFFF00'),
        ('Elegant', 'times', 26, 'normal', '#333333', '#F5F5F5')
    ON CONFLICT DO NOTHING;
    
    -- Create default region
    INSERT INTO regions (name, description)
    VALUES ('Default Region', 'Default region for all courses')
    ON CONFLICT DO NOTHING;
    """
    
    try:
        with engine.connect() as conn:
            statements = migration_sql.split(';')
            for statement in statements:
                statement = statement.strip()
                if statement:
                    try:
                        conn.execute(text(statement))
                        conn.commit()
                    except Exception as e:
                        print(f"Warning: {e}")
                        continue
        
        print("✅ Enterprise migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
