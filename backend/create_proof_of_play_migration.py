#!/usr/bin/env python3
"""
Migration script to add proof-of-play logging table
"""
import os
import sys
from sqlalchemy import create_engine, text

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import Base, CampaignDisplayLog

def run_migration():
    """Run the proof-of-play migration"""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        sys.exit(1)
    
    print(f"Connecting to database...")
    engine = create_engine(database_url)
    
    try:
        print("Creating campaign_display_logs table...")
        CampaignDisplayLog.__table__.create(engine, checkfirst=True)
        print("✓ Table created successfully")
        
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_name = 'campaign_display_logs'"
            ))
            count = result.scalar()
            
            if count > 0:
                print("✓ Migration verified: campaign_display_logs table exists")
            else:
                print("✗ Migration failed: table not found")
                sys.exit(1)
        
        print("\n✓ Proof-of-Play migration completed successfully!")
        
    except Exception as e:
        print(f"✗ Migration failed: {e}")
        sys.exit(1)
    finally:
        engine.dispose()

if __name__ == "__main__":
    run_migration()
