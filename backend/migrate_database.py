from app.database import Base, engine
from app.services.provisioning_service import provisioning_service
from sqlalchemy.orm import Session
from app.database import SessionLocal

def migrate_database():
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")
    
    print("Setting up default email templates...")
    db = SessionLocal()
    try:
        provisioning_service.create_default_email_templates(db)
        print("Default email templates created successfully!")
    except Exception as e:
        print(f"Error creating email templates: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    migrate_database()
