from supabase import create_client, Client
import os
from dotenv import load_dotenv

load_dotenv()

def create_storage_bucket():
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')
    
    if not supabase_url or not supabase_key:
        print("Error: Supabase credentials not found")
        return
    
    supabase: Client = create_client(supabase_url, supabase_key)
    
    try:
        bucket_name = 'golf-cms-uploads'
        
        result = supabase.storage.create_bucket(
            bucket_name,
            options={
                'public': True,
                'file_size_limit': 10485760,
                'allowed_mime_types': ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
            }
        )
        
        if result:
            print(f"Storage bucket '{bucket_name}' created successfully!")
        else:
            print("Bucket may already exist or creation failed")
            
    except Exception as e:
        print(f"Error creating storage bucket: {e}")

if __name__ == "__main__":
    create_storage_bucket()
