#!/usr/bin/env python3
"""
Run database migration to add missing columns
"""
import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv('.env.production')

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL environment variable not set")
    sys.exit(1)

print(f"Connecting to database...")
engine = create_engine(DATABASE_URL)

with open('migrations/add_missing_columns.sql', 'r') as f:
    migration_sql = f.read()

statements = [s.strip() for s in migration_sql.split(';') if s.strip() and not s.strip().startswith('--')]

print(f"Running {len(statements)} migration statements...")

try:
    with engine.connect() as conn:
        for i, statement in enumerate(statements, 1):
            if statement.strip():
                print(f"\nStatement {i}:")
                print(statement[:100] + "..." if len(statement) > 100 else statement)
                result = conn.execute(text(statement))
                conn.commit()
                print(f"✓ Statement {i} executed successfully")
    
    print("\n✅ Migration completed successfully!")
    
except Exception as e:
    print(f"\n❌ Migration failed: {e}")
    sys.exit(1)
