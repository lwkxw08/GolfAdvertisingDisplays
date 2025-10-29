from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from .database import get_db, User, UserRole

SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            print("DEBUG: JWT token missing 'sub' field")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        print(f"DEBUG: JWT token verified successfully for email: {email}")
        return email
    except JWTError as e:
        print(f"DEBUG: JWT verification failed: {type(e).__name__} - {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_user(email: str = Depends(verify_token), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        print(f"DEBUG: User not found in database: {email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    print(f"DEBUG: User found: {email}, role: {user.role}")
    return user

def require_admin(current_user: User = Depends(get_current_user)):
    admin_roles = [UserRole.SUPER_ADMIN, UserRole.REGIONAL_ADMIN]
    if hasattr(current_user.role, 'value'):
        role_value = current_user.role.value
    else:
        role_value = str(current_user.role)
    
    if role_value in ['admin', 'ADMIN', 'SUPER_ADMIN', 'REGIONAL_ADMIN'] or current_user.role in admin_roles:
        return current_user
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Admin access required"
    )

def require_super_admin(current_user: User = Depends(get_current_user)):
    if hasattr(current_user.role, 'value'):
        role_value = current_user.role.value
    else:
        role_value = str(current_user.role)
    
    if role_value in ['admin', 'ADMIN', 'SUPER_ADMIN'] or current_user.role == UserRole.SUPER_ADMIN:
        return current_user
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Super admin access required"
    )

def require_course_manager(current_user: User = Depends(get_current_user)):
    manager_roles = [UserRole.SUPER_ADMIN, UserRole.REGIONAL_ADMIN, UserRole.COURSE_MANAGER]
    if hasattr(current_user.role, 'value'):
        role_value = current_user.role.value
    else:
        role_value = str(current_user.role)
    
    if role_value in ['admin', 'ADMIN', 'SUPER_ADMIN', 'REGIONAL_ADMIN', 'COURSE_MANAGER'] or current_user.role in manager_roles:
        return current_user
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Course manager access required"
    )

def require_tenant_access(current_user: User = Depends(get_current_user)):
    return current_user

def check_course_access(course_id: int, current_user: User, db: Session = None):
    if hasattr(current_user.role, 'value'):
        role_value = current_user.role.value
    else:
        role_value = str(current_user.role)
    
    # Super admins have access to all courses
    if role_value in ['admin', 'ADMIN', 'SUPER_ADMIN'] or current_user.role == UserRole.SUPER_ADMIN:
        return True
    
    if (role_value == 'REGIONAL_ADMIN' or current_user.role == UserRole.REGIONAL_ADMIN) and current_user.region_id:
        if db:
            from .database import Course
            course = db.query(Course).filter(Course.id == course_id).first()
            if course and course.region_id == current_user.region_id:
                return True
    
    if (role_value in ['COURSE_MANAGER', 'CLIENT_TENANT', 'CLIENT'] or 
        current_user.role in [UserRole.COURSE_MANAGER, UserRole.CLIENT_TENANT]) and current_user.course_id == course_id:
        return True
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Access denied to this course. User course_id: {current_user.course_id}, requested course_id: {course_id}, role: {role_value}"
    )
