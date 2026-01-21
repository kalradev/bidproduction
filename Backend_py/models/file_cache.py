"""
File Cache Model - MongoDB Implementation
Handles file caching operations
"""
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from core.mongodb import get_mongodb, convert_id_to_str

logger = logging.getLogger(__name__)

class FileCache:
    @staticmethod
    def find_by_hash(file_hash: str, version: int) -> Optional[Dict[str, Any]]:
        """Find cached file by hash and version"""
        db = get_mongodb()
        if db is None:
            return None
        try:
            collection = db.file_cache
            
            # Find the cached file
            cached_file = collection.find_one({
                "file_hash": file_hash,
                "processing_version": version
            })
            
            if cached_file:
                # Update last accessed time
                collection.update_one(
                    {"_id": cached_file["_id"]},
                    {"$set": {"last_accessed_at": datetime.utcnow()}}
                )
                
                result = convert_id_to_str(cached_file)
                
                # Parse JSON strings if they exist (backward compatibility)
                if isinstance(result.get("departmental_summaries"), str):
                    result["departmental_summaries"] = json.loads(result["departmental_summaries"])
                if result.get("metadata") and isinstance(result["metadata"], str):
                    result["metadata"] = json.loads(result["metadata"])
                
                return result
            return None
        except Exception as e:
            logger.error(f"Error finding in cache: {str(e)}")
            return None

    @staticmethod
    def create(data: Dict[str, Any]):
        """Create or update a cached file"""
        db = get_mongodb()
        if db is None:
            return
        
        try:
            collection = db.file_cache
            
            file_hash = data["fileHash"]
            version = data["processingVersion"]
            filename = data["originalFilename"]
            text = data["extractedText"]
            summaries = data["departmentalSummaries"]
            metadata = data.get("metadata")

            cache_doc = {
                "file_hash": file_hash,
                "processing_version": version,
                "original_filename": filename,
                "extracted_text": text,
                "departmental_summaries": summaries,  # MongoDB stores as object
                "metadata": metadata,  # MongoDB stores as object
                "created_at": datetime.utcnow(),
                "last_accessed_at": datetime.utcnow()
            }
            
            # Use upsert (update if exists, insert if not)
            collection.update_one(
                {
                    "file_hash": file_hash,
                    "processing_version": version
                },
                {
                    "$set": cache_doc,
                    "$setOnInsert": {"created_at": datetime.utcnow()}
                },
                upsert=True
            )
            
            # Create unique index
            collection.create_index([("file_hash", 1), ("processing_version", 1)], unique=True)
            
            logger.info(f"✅ Cached file: {filename} (hash: {file_hash[:8]}..., v{version})")
        except Exception as e:
            logger.error(f"Error creating cache: {str(e)}")
