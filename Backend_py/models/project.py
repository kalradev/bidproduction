"""
Project Model - MongoDB Implementation
Handles all project-related database operations
"""
import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from bson import ObjectId
from core.mongodb import get_mongodb, convert_id_to_str, str_to_objectid

logger = logging.getLogger(__name__)

class ProjectModel:
    @staticmethod
    def get_by_name(project_name: str, user_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Get project by name and optionally user_id"""
        db = get_mongodb()
        if db is None:
            return None
        try:
            collection = db.projects
            query = {"project_name": project_name}
            
            if user_id:
                user_oid = str_to_objectid(user_id) if isinstance(user_id, (str, int)) else user_id
                query["user_id"] = user_oid
            
            project = collection.find_one(query)
            if project:
                return convert_id_to_str(project)
            return None
        except Exception as e:
            logger.error(f"Error getting project: {str(e)}")
            return None

    @staticmethod
    def get_all(user_id: int) -> List[Dict[str, Any]]:
        """Get all projects for a user"""
        db = get_mongodb()
        if db is None:
            return []
        try:
            collection = db.projects
            user_oid = str_to_objectid(user_id) if isinstance(user_id, (str, int)) else user_id
            
            projects = list(collection.find({"user_id": user_oid}).sort("project_name", 1))
            return [convert_id_to_str(p) for p in projects]
        except Exception as e:
            logger.error(f"Error getting all projects: {str(e)}")
            return []

    @staticmethod
    def create(project_name: str, tender_id: str, client_name: str, user_id: int) -> Optional[int]:
        """Create a new project"""
        db = get_mongodb()
        if db is None:
            return None
        try:
            collection = db.projects
            
            # Convert user_id to ObjectId
            user_oid = str_to_objectid(user_id) if isinstance(user_id, (str, int)) else user_id
            
            # Check if project already exists for this user
            existing = collection.find_one({
                "project_name": project_name,
                "user_id": user_oid
            })
            if existing:
                logger.warning(f"Project {project_name} already exists for user {user_id}")
                return str(existing["_id"])
            
            project_doc = {
                "project_name": project_name,
                "tender_id": tender_id,
                "client_name": client_name,
                "user_id": user_oid,
                "created_at": datetime.utcnow()
            }
            
            result = collection.insert_one(project_doc)
            
            # Create indexes if they don't exist
            collection.create_index([("project_name", 1), ("user_id", 1)], unique=True)
            collection.create_index("user_id")
            
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error creating project: {str(e)}")
            return None

    @staticmethod
    def add_document(project_id: int, file_hash: str, file_name: str, update_type: str, extracted_text: str, analysis_data: Dict[str, Any]) -> Optional[int]:
        """Add a document to a project"""
        db = get_mongodb()
        if db is None:
            return None
        try:
            collection = db.project_documents
            
            # Convert project_id to ObjectId
            project_oid = str_to_objectid(project_id) if isinstance(project_id, (str, int)) else project_id
            
            document_doc = {
                "project_id": project_oid,
                "file_hash": file_hash,
                "file_name": file_name,
                "update_type": update_type,
                "extracted_text": extracted_text,
                "analysis_data": analysis_data,  # MongoDB stores JSON natively
                "created_at": datetime.utcnow()
            }
            
            result = collection.insert_one(document_doc)
            
            # Create indexes
            collection.create_index("project_id")
            collection.create_index("file_hash")
            
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error adding document: {str(e)}")
            return None

    @staticmethod
    def add_analysis_record(project_id: int, document_id: int, section: str, content: str, source_type: str, source_file_name: str, source_file_id: str, linked_section_id: Optional[int] = None):
        """Add an analysis record"""
        db = get_mongodb()
        if db is None:
            return
        try:
            collection = db.analysis_records
            
            # Convert IDs to ObjectId
            project_oid = str_to_objectid(project_id) if isinstance(project_id, (str, int)) else project_id
            doc_oid = str_to_objectid(document_id) if isinstance(document_id, (str, int)) else document_id
            linked_oid = str_to_objectid(linked_section_id) if linked_section_id and isinstance(linked_section_id, (str, int)) else linked_section_id
            
            record_doc = {
                "project_id": project_oid,
                "document_id": doc_oid,
                "section": section,
                "content": content,
                "source_type": source_type,
                "source_file_name": source_file_name,
                "source_file_id": source_file_id,
                "linked_section_id": linked_oid,
                "created_at": datetime.utcnow()
            }
            
            collection.insert_one(record_doc)
            
            # Create indexes
            collection.create_index([("project_id", 1), ("section", 1)])
            collection.create_index("document_id")
        except Exception as e:
            logger.error(f"Error adding analysis record: {str(e)}")

    @staticmethod
    def get_merged_analysis(project_id: int) -> List[Dict[str, Any]]:
        """Get all analysis records for a project"""
        db = get_mongodb()
        if db is None:
            return []
        try:
            collection = db.analysis_records
            
            # Convert project_id to ObjectId
            project_oid = str_to_objectid(project_id) if isinstance(project_id, (str, int)) else project_id
            
            records = list(collection.find({"project_id": project_oid}).sort("created_at", 1))
            return [convert_id_to_str(r) for r in records]
        except Exception as e:
            logger.error(f"Error getting merged analysis: {str(e)}")
            return []
    
    @staticmethod
    def get_documents_by_project(project_id: int) -> List[Dict[str, Any]]:
        """Get all documents for a project"""
        db = get_mongodb()
        if db is None:
            return []
        try:
            collection = db.project_documents
            
            # Convert project_id to ObjectId
            project_oid = str_to_objectid(project_id) if isinstance(project_id, (str, int)) else project_id
            
            documents = list(collection.find({"project_id": project_oid}).sort("created_at", 1))
            return [convert_id_to_str(d) for d in documents]
        except Exception as e:
            logger.error(f"Error getting documents: {str(e)}")
            return []
    
    @staticmethod
    def get_final_analysis(project_id: int) -> Dict[str, Any]:
        """Get final merged analysis with documents"""
        db = get_mongodb()
        if db is None:
            return {}
        try:
            project_oid = str_to_objectid(project_id) if isinstance(project_id, (str, int)) else project_id
            
            # Get project
            project = db.projects.find_one({"_id": project_oid})
            if not project:
                return {}
            
            # Get all documents
            documents = list(db.project_documents.find({"project_id": project_oid}).sort("created_at", 1))
            
            # Get all analysis records
            analysis_records = list(db.analysis_records.find({"project_id": project_oid}).sort("created_at", 1))
            
            return {
                "project": convert_id_to_str(project),
                "documents": [convert_id_to_str(d) for d in documents],
                "analysis_records": [convert_id_to_str(r) for r in analysis_records]
            }
        except Exception as e:
            logger.error(f"Error getting final analysis: {str(e)}")
            return {}
