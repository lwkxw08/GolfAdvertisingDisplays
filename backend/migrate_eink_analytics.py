from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()

def migrate_device_analytics():
    """Add E-ink specific fields to DeviceAnalytics table"""
    database_url = os.getenv("DATABASE_URL", "sqlite:///./golf_cms.db")
    engine = create_engine(database_url)
    
    with engine.connect() as conn:
        try:
            print("Adding connectivity_type column...")
            conn.execute(text("ALTER TABLE device_analytics ADD COLUMN connectivity_type VARCHAR(20) DEFAULT 'wifi'"))
            conn.commit()
            print("✓ connectivity_type column added")
        except Exception as e:
            print(f"connectivity_type column (may already exist): {e}")
        
        try:
            print("Adding power_level column...")
            conn.execute(text("ALTER TABLE device_analytics ADD COLUMN power_level FLOAT DEFAULT 85.0"))
            conn.commit()
            print("✓ power_level column added")
        except Exception as e:
            print(f"power_level column (may already exist): {e}")
        
        try:
            print("Adding signal_strength column...")
            conn.execute(text("ALTER TABLE device_analytics ADD COLUMN signal_strength FLOAT DEFAULT -50.0"))
            conn.commit()
            print("✓ signal_strength column added")
        except Exception as e:
            print(f"signal_strength column (may already exist): {e}")
        
        try:
            print("Adding error_count column...")
            conn.execute(text("ALTER TABLE device_analytics ADD COLUMN error_count INTEGER DEFAULT 0"))
            conn.commit()
            print("✓ error_count column added")
        except Exception as e:
            print(f"error_count column (may already exist): {e}")
        
        try:
            print("Adding last_refresh_duration column...")
            conn.execute(text("ALTER TABLE device_analytics ADD COLUMN last_refresh_duration FLOAT DEFAULT 19.0"))
            conn.commit()
            print("✓ last_refresh_duration column added")
        except Exception as e:
            print(f"last_refresh_duration column (may already exist): {e}")
        
        print("Migration completed successfully")

if __name__ == "__main__":
    migrate_device_analytics()
