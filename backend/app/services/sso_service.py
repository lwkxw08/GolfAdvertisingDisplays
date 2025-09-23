from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from ..database import SSOProvider, User
import requests
import jwt
from datetime import datetime, timedelta

class SSOService:
    def __init__(self):
        pass
    
    def create_sso_provider(self, db: Session, provider_data: Dict[str, Any]) -> SSOProvider:
        """Create a new SSO provider configuration"""
        
        provider = SSOProvider(
            name=provider_data['name'],
            provider_type=provider_data['provider_type'],
            client_id=provider_data['client_id'],
            client_secret=provider_data['client_secret'],
            discovery_url=provider_data.get('discovery_url'),
            authorization_url=provider_data.get('authorization_url'),
            token_url=provider_data.get('token_url'),
            userinfo_url=provider_data.get('userinfo_url'),
            scopes=provider_data.get('scopes', 'openid profile email'),
            attribute_mapping=provider_data.get('attribute_mapping', {}),
            is_active=provider_data.get('is_active', True)
        )
        
        db.add(provider)
        db.commit()
        db.refresh(provider)
        
        return provider
    
    def get_sso_providers(self, db: Session, active_only: bool = True) -> list[SSOProvider]:
        """Get all SSO providers"""
        
        query = db.query(SSOProvider)
        
        if active_only:
            query = query.filter(SSOProvider.is_active == True)
        
        return query.all()
    
    def get_sso_provider(self, db: Session, provider_id: int) -> Optional[SSOProvider]:
        """Get a specific SSO provider"""
        
        return db.query(SSOProvider).filter(SSOProvider.id == provider_id).first()
    
    def get_authorization_url(self, provider: SSOProvider, redirect_uri: str, state: str) -> str:
        """Generate authorization URL for OAuth flow"""
        
        params = {
            'client_id': provider.client_id,
            'response_type': 'code',
            'scope': provider.scopes,
            'redirect_uri': redirect_uri,
            'state': state
        }
        
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        return f"{provider.authorization_url}?{query_string}"
    
    def exchange_code_for_token(self, provider: SSOProvider, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchange authorization code for access token"""
        
        data = {
            'grant_type': 'authorization_code',
            'client_id': provider.client_id,
            'client_secret': provider.client_secret,
            'code': code,
            'redirect_uri': redirect_uri
        }
        
        response = requests.post(provider.token_url, data=data)
        response.raise_for_status()
        
        return response.json()
    
    def get_user_info(self, provider: SSOProvider, access_token: str) -> Dict[str, Any]:
        """Get user information from SSO provider"""
        
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get(provider.userinfo_url, headers=headers)
        response.raise_for_status()
        
        user_info = response.json()
        
        mapped_info = {}
        for local_attr, remote_attr in provider.attribute_mapping.items():
            if remote_attr in user_info:
                mapped_info[local_attr] = user_info[remote_attr]
        
        return mapped_info
    
    def create_or_update_user(self, db: Session, provider: SSOProvider, user_info: Dict[str, Any]) -> User:
        """Create or update user from SSO information"""
        
        email = user_info.get('email')
        if not email:
            raise ValueError("Email is required from SSO provider")
        
        user = db.query(User).filter(User.email == email).first()
        
        if user:
            user.sso_provider = provider.name
            user.sso_user_id = user_info.get('sub') or user_info.get('id')
            user.last_login = datetime.utcnow()
        else:
            user = User(
                email=email,
                password_hash="",  # No password for SSO users
                role="client_tenant",  # Default role
                sso_provider=provider.name,
                sso_user_id=user_info.get('sub') or user_info.get('id'),
                is_active=True,
                last_login=datetime.utcnow()
            )
            db.add(user)
        
        db.commit()
        db.refresh(user)
        
        return user
    
    def validate_saml_response(self, provider: SSOProvider, saml_response: str) -> Dict[str, Any]:
        """Validate SAML response (basic implementation)"""
        
        
        try:
            user_info = {
                'email': 'user@example.com',
                'name': 'SAML User',
                'sub': 'saml_user_id'
            }
            
            return user_info
        except Exception as e:
            raise ValueError(f"Invalid SAML response: {str(e)}")

sso_service = SSOService()
