from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from ..database import User, UserRole, AuditLog, SSOProvider
import json
import requests
from datetime import datetime

class AuthService:
    def __init__(self):
        pass
    
    def check_permission(self, user: User, action: str, resource_type: str, resource_id: Optional[str] = None) -> bool:
        """Check if user has permission for specific action"""
        if user.role == UserRole.SUPER_ADMIN:
            return True
        
        if user.role == UserRole.REGIONAL_ADMIN:
            if action in ['read', 'update'] and resource_type in ['course', 'device', 'campaign']:
                return True
            if action == 'create' and resource_type in ['course', 'device']:
                return True
        
        if user.role == UserRole.COURSE_MANAGER:
            if resource_type == 'course' and str(user.course_id) == resource_id:
                return True
            if resource_type in ['device', 'campaign', 'notice'] and action in ['read', 'create', 'update']:
                return True
        
        if user.role == UserRole.CLIENT_TENANT:
            if resource_type == 'notice' and action in ['read', 'create']:
                return True
            if resource_type in ['device', 'campaign'] and action == 'read':
                return True
        
        if user.permissions:
            try:
                permissions = json.loads(user.permissions)
                permission_key = f"{resource_type}:{action}"
                return permissions.get(permission_key, False)
            except:
                pass
        
        return False
    
    def log_action(self, db: Session, user: User, action: str, resource_type: str, 
                   resource_id: Optional[str] = None, details: Optional[Dict] = None,
                   ip_address: Optional[str] = None, user_agent: Optional[str] = None):
        """Log user action for audit trail"""
        audit_log = AuditLog(
            user_id=user.id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.add(audit_log)
        db.commit()
    
    def authenticate_sso(self, db: Session, provider_name: str, sso_token: str) -> Optional[User]:
        """Authenticate user via SSO provider"""
        provider = db.query(SSOProvider).filter(
            SSOProvider.name == provider_name,
            SSOProvider.is_active == True
        ).first()
        
        if not provider:
            return None
        
        try:
            if provider.provider_type == 'saml':
                return self._authenticate_saml(db, provider, sso_token)
            elif provider.provider_type == 'oauth':
                return self._authenticate_oauth(db, provider, sso_token)
            elif provider.provider_type == 'oidc':
                return self._authenticate_oidc(db, provider, sso_token)
        except Exception as e:
            print(f"SSO authentication error: {e}")
            return None
        
        return None
    
    def _authenticate_saml(self, db: Session, provider: SSOProvider, saml_response: str) -> Optional[User]:
        """Handle SAML authentication"""
        return None
    
    def _authenticate_oauth(self, db: Session, provider: SSOProvider, oauth_token: str) -> Optional[User]:
        """Handle OAuth authentication"""
        config = provider.configuration
        
        response = requests.get(
            config['userinfo_endpoint'],
            headers={'Authorization': f'Bearer {oauth_token}'}
        )
        
        if response.status_code != 200:
            return None
        
        user_info = response.json()
        email = user_info.get('email')
        
        if not email:
            return None
        
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(
                email=email,
                hashed_password='',  # No password for SSO users
                role=UserRole.CLIENT_TENANT,
                sso_provider=provider.name,
                sso_user_id=user_info.get('sub')
            )
            db.add(user)
            db.commit()
        
        user.last_login = datetime.utcnow()
        db.commit()
        
        return user
    
    def _authenticate_oidc(self, db: Session, provider: SSOProvider, id_token: str) -> Optional[User]:
        """Handle OpenID Connect authentication"""
        return None

auth_service = AuthService()
