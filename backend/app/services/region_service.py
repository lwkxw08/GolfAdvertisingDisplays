from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from ..database import Region, User, Course

class RegionService:
    def __init__(self):
        pass
    
    def create_region(self, db: Session, region_data: Dict[str, Any]) -> Region:
        """Create a new region"""
        
        region = Region(
            name=region_data['name'],
            description=region_data.get('description', ''),
            country=region_data.get('country', ''),
            timezone=region_data.get('timezone', 'UTC'),
            is_active=region_data.get('is_active', True)
        )
        
        db.add(region)
        db.commit()
        db.refresh(region)
        
        return region
    
    def get_regions(self, db: Session, active_only: bool = True) -> List[Region]:
        """Get all regions"""
        
        query = db.query(Region)
        
        if active_only:
            query = query.filter(Region.is_active == True)
        
        return query.all()
    
    def get_region(self, db: Session, region_id: int) -> Optional[Region]:
        """Get a specific region"""
        
        return db.query(Region).filter(Region.id == region_id).first()
    
    def update_region(self, db: Session, region_id: int, region_data: Dict[str, Any]) -> Optional[Region]:
        """Update a region"""
        
        region = self.get_region(db, region_id)
        if not region:
            return None
        
        for key, value in region_data.items():
            if hasattr(region, key):
                setattr(region, key, value)
        
        db.commit()
        db.refresh(region)
        
        return region
    
    def delete_region(self, db: Session, region_id: int) -> bool:
        """Delete a region (soft delete by setting is_active=False)"""
        
        region = self.get_region(db, region_id)
        if not region:
            return False
        
        courses_count = db.query(Course).filter(Course.region_id == region_id).count()
        users_count = db.query(User).filter(User.region_id == region_id).count()
        
        if courses_count > 0 or users_count > 0:
            region.is_active = False
        else:
            db.delete(region)
        
        db.commit()
        return True
    
    def get_region_statistics(self, db: Session, region_id: int) -> Dict[str, Any]:
        """Get statistics for a region"""
        
        region = self.get_region(db, region_id)
        if not region:
            return {}
        
        courses_count = db.query(Course).filter(Course.region_id == region_id).count()
        users_count = db.query(User).filter(User.region_id == region_id).count()
        
        active_courses = db.query(Course).filter(
            Course.region_id == region_id,
            Course.is_active == True
        ).count()
        
        active_users = db.query(User).filter(
            User.region_id == region_id,
            User.is_active == True
        ).count()
        
        return {
            'region_id': region_id,
            'region_name': region.name,
            'total_courses': courses_count,
            'active_courses': active_courses,
            'total_users': users_count,
            'active_users': active_users,
            'timezone': region.timezone,
            'country': region.country
        }

region_service = RegionService()
