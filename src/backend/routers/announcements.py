"""
Announcements endpoints for the High School Management System API
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from bson import ObjectId

from ..database import announcements_collection, teachers_collection

router = APIRouter(
    prefix="/announcements",
    tags=["announcements"]
)


def serialize_announcement(announcement):
    """Convert MongoDB document to JSON-serializable format"""
    if announcement:
        announcement["_id"] = str(announcement["_id"])
        # Convert datetime objects to ISO format strings
        for field in ["start_date", "expiration_date", "created_at"]:
            if field in announcement and isinstance(announcement[field], datetime):
                announcement[field] = announcement[field].isoformat()
    return announcement


@router.get("/")
def get_active_announcements() -> List[Dict[str, Any]]:
    """Get all active announcements that are currently visible"""
    now = datetime.now(timezone.utc)
    
    # Find announcements that are active and within their date range
    query = {
        "active": True,
        "$and": [
            {"expiration_date": {"$gt": now}},
            {
                "$or": [
                    {"start_date": {"$lte": now}},
                    {"start_date": {"$exists": False}}
                ]
            }
        ]
    }
    
    announcements = list(announcements_collection.find(query).sort("created_at", -1))
    return [serialize_announcement(ann) for ann in announcements]


@router.get("/all")
def get_all_announcements(username: str) -> List[Dict[str, Any]]:
    """Get all announcements for management (requires authentication)"""
    # Verify user is authenticated
    teacher = teachers_collection.find_one({"_id": username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    announcements = list(announcements_collection.find().sort("created_at", -1))
    return [serialize_announcement(ann) for ann in announcements]


@router.post("/")
def create_announcement(
    title: str,
    message: str,
    expiration_date: str,
    username: str,
    start_date: Optional[str] = None
) -> Dict[str, Any]:
    """Create a new announcement"""
    # Verify user is authenticated
    teacher = teachers_collection.find_one({"_id": username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        # Parse dates
        exp_date = datetime.fromisoformat(expiration_date.replace('Z', '+00:00'))
        start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00')) if start_date else datetime.now(timezone.utc)
        
        # Validate expiration date is in the future
        if exp_date <= datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail="Expiration date must be in the future")
        
        announcement = {
            "title": title,
            "message": message,
            "start_date": start_dt,
            "expiration_date": exp_date,
            "created_by": username,
            "created_at": datetime.now(timezone.utc),
            "active": True
        }
        
        result = announcements_collection.insert_one(announcement)
        announcement["_id"] = str(result.inserted_id)
        
        return serialize_announcement(announcement)
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid date format")
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to create announcement")


@router.put("/{announcement_id}")
def update_announcement(
    announcement_id: str,
    title: str,
    message: str,
    expiration_date: str,
    username: str,
    start_date: Optional[str] = None,
    active: bool = True
) -> Dict[str, Any]:
    """Update an existing announcement"""
    # Verify user is authenticated
    teacher = teachers_collection.find_one({"_id": username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        # Validate ObjectId
        obj_id = ObjectId(announcement_id)
        
        # Parse dates
        exp_date = datetime.fromisoformat(expiration_date.replace('Z', '+00:00'))
        start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00')) if start_date else None
        
        # Validate expiration date is in the future
        if exp_date <= datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail="Expiration date must be in the future")
        
        update_data = {
            "title": title,
            "message": message,
            "expiration_date": exp_date,
            "active": active
        }
        
        if start_dt:
            update_data["start_date"] = start_dt
        
        result = announcements_collection.update_one(
            {"_id": obj_id},
            {"$set": update_data}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Announcement not found")
        
        updated_announcement = announcements_collection.find_one({"_id": obj_id})
        return serialize_announcement(updated_announcement)
    
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid announcement ID or date format")
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to update announcement")


@router.delete("/{announcement_id}")
def delete_announcement(announcement_id: str, username: str) -> Dict[str, str]:
    """Delete an announcement"""
    # Verify user is authenticated
    teacher = teachers_collection.find_one({"_id": username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        obj_id = ObjectId(announcement_id)
        result = announcements_collection.delete_one({"_id": obj_id})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Announcement not found")
        
        return {"message": "Announcement deleted successfully"}
    
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid announcement ID")
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to delete announcement")