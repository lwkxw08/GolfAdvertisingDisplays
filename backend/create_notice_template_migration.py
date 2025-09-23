from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

migration_sql = """
CREATE TABLE IF NOT EXISTS notice_templates (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    title VARCHAR NOT NULL,
    content TEXT NOT NULL,
    course_id INTEGER NOT NULL REFERENCES courses(id),
    created_by INTEGER NOT NULL REFERENCES users(id),
    style_id INTEGER REFERENCES notice_styles(id),
    default_duration_minutes INTEGER DEFAULT 60,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_notice_templates_course_id ON notice_templates(course_id);
CREATE INDEX IF NOT EXISTS idx_notice_templates_active ON notice_templates(is_active);
"""

with engine.connect() as conn:
    conn.execute(text(migration_sql))
    conn.commit()
    print("Notice template migration completed successfully!")
