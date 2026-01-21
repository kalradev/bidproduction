"""
Migration script to transfer data from PostgreSQL to MongoDB
Run this script once to migrate all existing data

Usage:
    python migrate_to_mongodb.py
"""
import asyncio
import json
from datetime import datetime
from bson import ObjectId
from pymongo import MongoClient
from core.database import get_db_connection
from psycopg2.extras import RealDictCursor
from core.config import settings
from core.mongodb import init_mongodb
import logging

logger = logging.getLogger(__name__)

def migrate_users():
    """Migrate users table from PostgreSQL to MongoDB"""
    logger.info("🔄 Migrating users...")
    
    conn = get_db_connection()
    if not conn:
        logger.error("❌ Cannot connect to PostgreSQL")
        return {}
    
    db = init_mongodb()
    if db is None:
        logger.error("❌ Cannot connect to MongoDB")
        conn.close()
        return {}
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM users ORDER BY id")
        users = cursor.fetchall()
        
        # Create user_id mapping (PostgreSQL ID -> MongoDB ObjectId string)
        user_mapping = {}
        users_collection = db.users
        
        for user in users:
            # Convert to MongoDB document
            user_doc = {
                "full_name": user['full_name'],
                "email": user['email'],
                "password": user['password'],
                "role": user.get('role', 'bid_manager'),
                "created_at": user['created_at'],
                "updated_at": user.get('updated_at', user['created_at'])
            }
            
            # Check if user already exists (by email)
            existing = users_collection.find_one({"email": user['email']})
            if existing:
                logger.info(f"⚠️ User {user['email']} already exists, skipping...")
                user_mapping[user['id']] = str(existing['_id'])
                continue
            
            # Insert into MongoDB
            result = users_collection.insert_one(user_doc)
            user_mapping[user['id']] = str(result.inserted_id)
            logger.info(f"✅ Migrated user: {user['email']} (PostgreSQL ID: {user['id']} -> MongoDB ID: {user_mapping[user['id']]})")
        
        # Create unique index on email
        users_collection.create_index("email", unique=True)
        
        logger.info(f"✅ Migrated {len(users)} users")
        cursor.close()
        conn.close()
        return user_mapping
    except Exception as e:
        logger.error(f"❌ Error migrating users: {str(e)}")
        if conn:
            conn.close()
        return {}

def migrate_projects(user_mapping):
    """Migrate projects table from PostgreSQL to MongoDB"""
    logger.info("🔄 Migrating projects...")
    
    conn = get_db_connection()
    if not conn:
        return {}
    
    db = init_mongodb()
    if db is None:
        conn.close()
        return {}
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM projects ORDER BY id")
        projects = cursor.fetchall()
        
        project_mapping = {}
        projects_collection = db.projects
        
        for project in projects:
            # Convert user_id to MongoDB ObjectId
            pg_user_id = project.get('user_id')
            mongodb_user_id = None
            if pg_user_id and pg_user_id in user_mapping:
                mongodb_user_id = ObjectId(user_mapping[pg_user_id])
            elif pg_user_id:
                logger.warning(f"⚠️ Project {project['project_name']} has user_id {pg_user_id} not found in user_mapping")
            
            project_doc = {
                "project_name": project['project_name'],
                "tender_id": project['tender_id'],
                "client_name": project['client_name'],
                "user_id": mongodb_user_id,
                "created_at": project['created_at']
            }
            
            # Check if project already exists
            existing = projects_collection.find_one({
                "project_name": project['project_name'],
                "user_id": mongodb_user_id
            })
            if existing:
                logger.info(f"⚠️ Project {project['project_name']} already exists, skipping...")
                project_mapping[project['id']] = str(existing['_id'])
                continue
            
            result = projects_collection.insert_one(project_doc)
            project_mapping[project['id']] = str(result.inserted_id)
            logger.info(f"✅ Migrated project: {project['project_name']} (PostgreSQL ID: {project['id']} -> MongoDB ID: {project_mapping[project['id']]})")
        
        # Create indexes
        projects_collection.create_index([("project_name", 1), ("user_id", 1)], unique=True)
        projects_collection.create_index("user_id")
        
        logger.info(f"✅ Migrated {len(projects)} projects")
        cursor.close()
        conn.close()
        return project_mapping
    except Exception as e:
        logger.error(f"❌ Error migrating projects: {str(e)}")
        if conn:
            conn.close()
        return {}

def migrate_project_documents(project_mapping):
    """Migrate project_documents table from PostgreSQL to MongoDB"""
    logger.info("🔄 Migrating project_documents...")
    
    conn = get_db_connection()
    if not conn:
        return {}
    
    db = init_mongodb()
    if db is None:
        conn.close()
        return {}
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM project_documents ORDER BY id")
        documents = cursor.fetchall()
        
        doc_mapping = {}
        docs_collection = db.project_documents
        
        for doc in documents:
            # Convert project_id to MongoDB ObjectId
            pg_project_id = doc['project_id']
            mongodb_project_id = None
            if pg_project_id and pg_project_id in project_mapping:
                mongodb_project_id = ObjectId(project_mapping[pg_project_id])
            else:
                logger.warning(f"⚠️ Document {doc['file_name']} has project_id {pg_project_id} not found in project_mapping, skipping...")
                continue
            
            # Parse analysis_data if it's a JSON string
            analysis_data = doc.get('analysis_data')
            if isinstance(analysis_data, str):
                try:
                    analysis_data = json.loads(analysis_data)
                except:
                    analysis_data = {}
            
            document_doc = {
                "project_id": mongodb_project_id,
                "file_hash": doc['file_hash'],
                "file_name": doc['file_name'],
                "update_type": doc.get('update_type'),
                "extracted_text": doc.get('extracted_text'),
                "analysis_data": analysis_data,  # MongoDB stores as object
                "created_at": doc['created_at']
            }
            
            result = docs_collection.insert_one(document_doc)
            doc_mapping[doc['id']] = str(result.inserted_id)
            logger.info(f"✅ Migrated document: {doc['file_name']} (PostgreSQL ID: {doc['id']} -> MongoDB ID: {doc_mapping[doc['id']]})")
        
        # Create indexes
        docs_collection.create_index("project_id")
        docs_collection.create_index("file_hash")
        
        logger.info(f"✅ Migrated {len(documents)} documents")
        cursor.close()
        conn.close()
        return doc_mapping
    except Exception as e:
        logger.error(f"❌ Error migrating project_documents: {str(e)}")
        if conn:
            conn.close()
        return {}

def migrate_analysis_records(project_mapping, doc_mapping):
    """Migrate analysis_records table from PostgreSQL to MongoDB"""
    logger.info("🔄 Migrating analysis_records...")
    
    conn = get_db_connection()
    if not conn:
        return
    
    db = init_mongodb()
    if db is None:
        conn.close()
        return
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM analysis_records ORDER BY id")
        records = cursor.fetchall()
        
        records_collection = db.analysis_records
        
        for record in records:
            # Convert IDs to MongoDB ObjectId
            pg_project_id = record['project_id']
            mongodb_project_id = None
            if pg_project_id and pg_project_id in project_mapping:
                mongodb_project_id = ObjectId(project_mapping[pg_project_id])
            else:
                logger.warning(f"⚠️ Analysis record has project_id {pg_project_id} not found, skipping...")
                continue
            
            pg_doc_id = record.get('document_id')
            mongodb_doc_id = None
            if pg_doc_id and pg_doc_id in doc_mapping:
                mongodb_doc_id = ObjectId(doc_mapping[pg_doc_id])
            
            pg_linked_id = record.get('linked_section_id')
            mongodb_linked_id = None
            if pg_linked_id:
                # Try to find it in migrated records (would need to track record mapping)
                # For now, skip linked_section_id migration
                pass
            
            record_doc = {
                "project_id": mongodb_project_id,
                "document_id": mongodb_doc_id,
                "section": record['section'],
                "content": record['content'],
                "source_type": record['source_type'],
                "source_file_name": record.get('source_file_name'),
                "source_file_id": record.get('source_file_id'),
                "linked_section_id": mongodb_linked_id,
                "created_at": record['created_at']
            }
            
            records_collection.insert_one(record_doc)
        
        # Create indexes
        records_collection.create_index([("project_id", 1), ("section", 1)])
        records_collection.create_index("document_id")
        
        logger.info(f"✅ Migrated {len(records)} analysis records")
        cursor.close()
        conn.close()
    except Exception as e:
        logger.error(f"❌ Error migrating analysis_records: {str(e)}")
        if conn:
            conn.close()

def migrate_file_cache():
    """Migrate file_cache table from PostgreSQL to MongoDB"""
    logger.info("🔄 Migrating file_cache...")
    
    conn = get_db_connection()
    if not conn:
        return
    
    db = init_mongodb()
    if db is None:
        conn.close()
        return
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM file_cache ORDER BY id")
        cache_entries = cursor.fetchall()
        
        cache_collection = db.file_cache
        
        for entry in cache_entries:
            # Parse JSON strings if they exist
            summaries = entry.get('departmental_summaries')
            if isinstance(summaries, str):
                try:
                    summaries = json.loads(summaries)
                except:
                    summaries = {}
            
            metadata = entry.get('metadata')
            if metadata and isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except:
                    metadata = None
            
            cache_doc = {
                "file_hash": entry['file_hash'],
                "processing_version": entry['processing_version'],
                "original_filename": entry['original_filename'],
                "extracted_text": entry['extracted_text'],
                "departmental_summaries": summaries,  # MongoDB stores as object
                "metadata": metadata,  # MongoDB stores as object
                "last_accessed_at": entry.get('last_accessed_at', entry['created_at'])
            }
            
            # Use upsert to avoid duplicates
            # created_at only set on insert, last_accessed_at always updated
            cache_collection.update_one(
                {
                    "file_hash": entry['file_hash'],
                    "processing_version": entry['processing_version']
                },
                {
                    "$set": cache_doc,
                    "$setOnInsert": {"created_at": entry['created_at']}
                },
                upsert=True
            )
        
        # Create unique index
        cache_collection.create_index([("file_hash", 1), ("processing_version", 1)], unique=True)
        
        logger.info(f"✅ Migrated {len(cache_entries)} file cache entries")
        cursor.close()
        conn.close()
    except Exception as e:
        logger.error(f"❌ Error migrating file_cache: {str(e)}")
        if conn:
            conn.close()

def migrate_eligibility_checklist(user_mapping, project_mapping, doc_mapping):
    """Migrate eligibility_checklist table from PostgreSQL to MongoDB"""
    logger.info("🔄 Migrating eligibility_checklist...")
    
    conn = get_db_connection()
    if not conn:
        return
    
    db = init_mongodb()
    if db is None:
        conn.close()
        return
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM eligibility_checklist ORDER BY id")
        checklist_items = cursor.fetchall()
        
        checklist_collection = db.eligibility_checklist
        
        for item in checklist_items:
            # Convert IDs to MongoDB ObjectId
            pg_project_id = item['project_id']
            mongodb_project_id = None
            if pg_project_id and pg_project_id in project_mapping:
                mongodb_project_id = ObjectId(project_mapping[pg_project_id])
            else:
                logger.warning(f"⚠️ Eligibility item has project_id {pg_project_id} not found, skipping...")
                continue
            
            pg_user_id = item.get('user_id')
            mongodb_user_id = None
            if pg_user_id and pg_user_id in user_mapping:
                mongodb_user_id = ObjectId(user_mapping[pg_user_id])
            
            pg_doc_id = item.get('document_id')
            mongodb_doc_id = None
            if pg_doc_id and pg_doc_id in doc_mapping:
                mongodb_doc_id = ObjectId(doc_mapping[pg_doc_id])
            
            checklist_doc = {
                "project_id": mongodb_project_id,
                "document_id": mongodb_doc_id,  # Can be None
                "user_id": mongodb_user_id,
                "criteria_text": item['criteria_text'],
                "is_checked": item.get('is_checked', False),
                "updated_at": item.get('updated_at', item['created_at'])
            }
            
            # Use upsert to avoid duplicates
            # created_at only set on insert, updated_at always updated
            checklist_collection.update_one(
                {
                    "project_id": mongodb_project_id,
                    "document_id": mongodb_doc_id,
                    "user_id": mongodb_user_id,
                    "criteria_text": item['criteria_text']
                },
                {
                    "$set": checklist_doc,
                    "$setOnInsert": {"created_at": item['created_at']}
                },
                upsert=True
            )
        
        # Create unique index
        checklist_collection.create_index([
            ("project_id", 1),
            ("document_id", 1),
            ("user_id", 1),
            ("criteria_text", 1)
        ], unique=True)
        checklist_collection.create_index("user_id")
        
        logger.info(f"✅ Migrated {len(checklist_items)} eligibility checklist items")
        cursor.close()
        conn.close()
    except Exception as e:
        logger.error(f"❌ Error migrating eligibility_checklist: {str(e)}")
        if conn:
            conn.close()

def main():
    """Main migration function"""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    logger.info("🚀 Starting PostgreSQL to MongoDB migration...")
    logger.info(f"   PostgreSQL DB: {settings.POSTGRES_DB}")
    logger.info(f"   MongoDB: {settings.MONGODB_STRING}")
    logger.info("")
    
    # Step 1: Migrate users (creates the mapping for foreign keys)
    user_mapping = migrate_users()
    if not user_mapping:
        logger.error("❌ User migration failed. Aborting.")
        return
    
    # Step 2: Migrate projects
    project_mapping = migrate_projects(user_mapping)
    if not project_mapping:
        logger.warning("⚠️ No projects to migrate or migration failed")
    
    # Step 3: Migrate project documents
    doc_mapping = migrate_project_documents(project_mapping)
    if not doc_mapping:
        logger.warning("⚠️ No documents to migrate or migration failed")
    
    # Step 4: Migrate analysis records
    migrate_analysis_records(project_mapping, doc_mapping)
    
    # Step 5: Migrate file cache
    migrate_file_cache()
    
    # Step 6: Migrate eligibility checklist
    migrate_eligibility_checklist(user_mapping, project_mapping, doc_mapping)
    
    logger.info("")
    logger.info("✅ Migration complete!")
    logger.info(f"   - Users migrated: {len(user_mapping)}")
    logger.info(f"   - Projects migrated: {len(project_mapping)}")
    logger.info(f"   - Documents migrated: {len(doc_mapping)}")
    logger.info("")
    logger.info("⚠️ IMPORTANT: Verify the migrated data in MongoDB before switching to MongoDB-only mode!")

if __name__ == "__main__":
    main()

