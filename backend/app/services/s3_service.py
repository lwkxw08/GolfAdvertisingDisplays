import os
from typing import Optional
import uuid
from pathlib import Path
from supabase import create_client, Client

class SupabaseStorageService:
    def __init__(self):
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY')
        
        if not supabase_url or not supabase_key:
            print("Warning: Supabase credentials not configured")
            self.supabase = None
        else:
            self.supabase: Client = create_client(supabase_url, supabase_key)
        
        self.bucket_name = 'golf-cms-uploads'
    
    def upload_file(self, file_content: bytes, filename: str, content_type: str = 'image/jpeg') -> Optional[str]:
        """Upload file to Supabase Storage and return the public URL"""
        if not self.supabase:
            print("Supabase client not initialized")
            return None
            
        try:
            file_extension = Path(filename).suffix
            unique_filename = f"campaigns/{uuid.uuid4()}{file_extension}"
            
            result = self.supabase.storage.from_(self.bucket_name).upload(
                path=unique_filename,
                file=file_content,
                file_options={"content-type": content_type}
            )
            
            public_url = self.supabase.storage.from_(self.bucket_name).get_public_url(unique_filename)
            return public_url
                
        except Exception as e:
            print(f"Error uploading file to Supabase Storage: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def delete_file(self, file_url: str) -> bool:
        """Delete file from Supabase Storage using the public URL"""
        if not self.supabase:
            return False
            
        try:
            path = file_url.split(f"{self.bucket_name}/")[-1]
            result = self.supabase.storage.from_(self.bucket_name).remove([path])
            return result.data is not None
        except Exception as e:
            print(f"Error deleting file from Supabase Storage: {e}")
            return False
    
    def generate_signed_url(self, path: str, expiration: int = 3600) -> Optional[str]:
        """Generate a signed URL for private file access"""
        if not self.supabase:
            return None
            
        try:
            result = self.supabase.storage.from_(self.bucket_name).create_signed_url(
                path=path,
                expires_in=expiration
            )
            return result.get('signedURL')
        except Exception as e:
            print(f"Error generating signed URL: {e}")
            return None

storage_service = SupabaseStorageService()
