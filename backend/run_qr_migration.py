#!/usr/bin/env python3
"""
Run QR Code Tracking Migration

This script runs the SQL migration to add QR code tracking tables to the database.
"""

import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

def run_migration():
    """Run the QR code tracking migration"""
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        print("Error: DATABASE_URL not found in environment variables")
        return False
    
    migration_file = 'add_qr_code_tracking.sql'
    
    try:
        with open(migration_file, 'r') as f:
            migration_sql = f.read()
    except FileNotFoundError:
        print(f"Error: Migration file '{migration_file}' not found")
        return False
    
    try:
        print(f"Connecting to database...")
        conn = psycopg.connect(database_url)
        cursor = conn.cursor()
        
        print(f"Running migration from {migration_file}...")
        cursor.execute(migration_sql)
        
        conn.commit()
        print("✓ Migration completed successfully!")
        
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('qr_codes', 'qr_code_scans', 'qr_code_analytics')
            ORDER BY table_name;
        """)
        
        tables = cursor.fetchall()
        print(f"\n✓ Verified tables created:")
        for table in tables:
            print(f"  - {table[0]}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except psycopg.Error as e:
        print(f"Database error: {e}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == '__main__':
    success = run_migration()
    exit(0 if success else 1)
