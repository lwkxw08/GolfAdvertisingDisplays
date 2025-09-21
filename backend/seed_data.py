from sqlalchemy.orm import Session
from app.database import SessionLocal, User, Course, Device, UserRole, Base, engine
from app.auth import get_password_hash

def create_seed_data():
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    admin_user = User(
        email="admin@golfcms.com",
        hashed_password=get_password_hash("admin123"),
        role=UserRole.ADMIN,
        is_active=True
    )
    db.add(admin_user)
    
    course = Course(
        name="Pine Valley Golf Club",
        location="New Jersey, USA"
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    
    tenant_user = User(
        email="staff@pinevalley.com",
        hashed_password=get_password_hash("staff123"),
        role=UserRole.CLIENT_TENANT,
        course_id=course.id,
        is_active=True
    )
    db.add(tenant_user)
    
    devices = [
        Device(name="Tee Box 1", device_id="PV-TB-001", course_id=course.id),
        Device(name="Tee Box 3", device_id="PV-TB-003", course_id=course.id),
        Device(name="Tee Box 7", device_id="PV-TB-007", course_id=course.id),
    ]
    
    for device in devices:
        db.add(device)
    
    db.commit()
    db.close()
    print("Seed data created successfully!")

if __name__ == "__main__":
    create_seed_data()
