"""
Eligibility Checklist Model - MongoDB Implementation
Handles eligibility checklist operations
"""
import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from core.mongodb import get_mongodb, convert_id_to_str, str_to_objectid

logger = logging.getLogger(__name__)

class EligibilityChecklistModel:
    @staticmethod
    def get_by_project_and_document(project_id, document_id: Optional[str], user_id) -> Dict[str, bool]:
        """Get all eligibility checklist items for a project/document"""
        db = get_mongodb()
        if db is None:
            return {}
        try:
            collection = db.eligibility_checklist
            
            # Convert IDs to ObjectId
            project_oid = str_to_objectid(project_id) if isinstance(project_id, (str, int)) else project_id
            doc_oid = str_to_objectid(document_id) if document_id and isinstance(document_id, (str, int)) else document_id
            user_oid = str_to_objectid(user_id) if isinstance(user_id, (str, int)) else user_id
            
            # Build query
            query = {
                "project_id": project_oid,
                "user_id": user_oid
            }
            
            if document_id:
                query["document_id"] = doc_oid
            else:
                query["document_id"] = None
            
            # Find all matching items
            results = list(collection.find(query))
            
            # Convert to dictionary format
            checklist = {}
            for item in results:
                checklist[item["criteria_text"]] = item.get("is_checked", False)
            
            return checklist
        except Exception as e:
            logger.error(f"Error getting eligibility checklist: {str(e)}")
            return {}

    @staticmethod
    def save_checklist(project_id, document_id: Optional[str], user_id, checklist: Dict[str, bool]) -> bool:
        """Save or update eligibility checklist items"""
        db = get_mongodb()
        if db is None:
            return False
        try:
            collection = db.eligibility_checklist
            
            # Convert IDs to ObjectId
            project_oid = str_to_objectid(project_id) if isinstance(project_id, (str, int)) else project_id
            doc_oid = str_to_objectid(document_id) if document_id and isinstance(document_id, (str, int)) else document_id
            user_oid = str_to_objectid(user_id) if isinstance(user_id, (str, int)) else user_id
            
            # Save each checklist item
            for criteria_text, is_checked in checklist.items():
                query = {
                    "project_id": project_oid,
                    "document_id": doc_oid if document_id else None,
                    "user_id": user_oid,
                    "criteria_text": criteria_text
                }
                
                update_doc = {
                    "$set": {
                        "is_checked": is_checked,
                        "updated_at": datetime.utcnow()
                    },
                    "$setOnInsert": {
                        "created_at": datetime.utcnow()
                    }
                }
                
                # Upsert (update if exists, insert if not)
                collection.update_one(query, update_doc, upsert=True)
            
            # Create indexes
            collection.create_index([
                ("project_id", 1),
                ("document_id", 1),
                ("user_id", 1),
                ("criteria_text", 1)
            ], unique=True)
            collection.create_index("user_id")
            
            logger.info(f"✅ Saved eligibility checklist for project {project_id}, document {document_id}")
            return True
        except Exception as e:
            logger.error(f"Error saving eligibility checklist: {str(e)}")
            return False

    @staticmethod
    def update_item(project_id, document_id: Optional[str], user_id, criteria_text: str, is_checked: bool) -> bool:
        """Update a single eligibility checklist item"""
        db = get_mongodb()
        if db is None:
            return False
        try:
            collection = db.eligibility_checklist
            
            # Convert IDs to ObjectId
            project_oid = str_to_objectid(project_id) if isinstance(project_id, (str, int)) else project_id
            doc_oid = str_to_objectid(document_id) if document_id and isinstance(document_id, (str, int)) else document_id
            user_oid = str_to_objectid(user_id) if isinstance(user_id, (str, int)) else user_id
            
            query = {
                "project_id": project_oid,
                "document_id": doc_oid if document_id else None,
                "user_id": user_oid,
                "criteria_text": criteria_text
            }
            
            update_doc = {
                "$set": {
                    "is_checked": is_checked,
                    "updated_at": datetime.utcnow()
                },
                "$setOnInsert": {
                    "created_at": datetime.utcnow()
                }
            }
            
            # Upsert (update if exists, insert if not)
            collection.update_one(query, update_doc, upsert=True)
            
            return True
        except Exception as e:
            logger.error(f"Error updating eligibility checklist item: {str(e)}")
            return False
