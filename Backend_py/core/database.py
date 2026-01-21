import psycopg2
from psycopg2.extras import RealDictCursor
import os
import logging
import time
from core.config import settings

logger = logging.getLogger(__name__)

def get_db_connection():
    try:
        if settings.DATABASE_URL:
            conn = psycopg2.connect(settings.DATABASE_URL)
        else:
            conn = psycopg2.connect(
                dbname=settings.POSTGRES_DB,
                user=settings.POSTGRES_USER,
                password=settings.POSTGRES_PASSWORD,
                host=settings.POSTGRES_HOST,
                port=settings.POSTGRES_PORT
            )
        return conn
    except Exception as e:
        logger.error(f"❌ Database connection error: {str(e)}")
        return None

def init_db():
    conn = get_db_connection()
    if not conn:
        logger.warning("⚠️ Could not connect to PostgreSQL for initialization. Skipping init_db.")
        return
        
    try:
        cursor = conn.cursor()
        
        # Create file_cache if not exists (keep existing functionality for compatibility)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS file_cache (
                id SERIAL PRIMARY KEY,
                file_hash TEXT NOT NULL,
                processing_version INTEGER NOT NULL DEFAULT 1,
                original_filename TEXT NOT NULL,
                extracted_text TEXT NOT NULL,
                departmental_summaries TEXT NOT NULL,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(file_hash, processing_version)
            );
        """)
        
        # Create projects table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id SERIAL PRIMARY KEY,
                project_name TEXT UNIQUE NOT NULL,
                tender_id TEXT NOT NULL,
                client_name TEXT NOT NULL,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Add user_id column if it doesn't exist (for existing databases)
        cursor.execute("""
            DO $$ 
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name='projects' AND column_name='user_id'
                ) THEN
                    ALTER TABLE projects ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE CASCADE;
                END IF;
            END $$;
        """)
        
        # Create project_documents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS project_documents (
                id SERIAL PRIMARY KEY,
                project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
                file_hash TEXT NOT NULL,
                file_name TEXT NOT NULL,
                update_type TEXT CHECK (update_type IN ('BASE_RFP', 'CORRIGENDUM', 'REFERENCE_UPDATE')),
                extracted_text TEXT,
                analysis_data JSONB, -- Storing the full AI summary here as well
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Create analysis_records table (for granular clause storage)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analysis_records (
                id SERIAL PRIMARY KEY,
                project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
                document_id INTEGER REFERENCES project_documents(id) ON DELETE CASCADE,
                section TEXT NOT NULL,
                content TEXT NOT NULL,
                source_type TEXT NOT NULL,
                source_file_name TEXT,
                source_file_id TEXT,
                linked_section_id INTEGER REFERENCES analysis_records(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Create users table for authentication
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                full_name VARCHAR(255) NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                role VARCHAR(50) DEFAULT 'bid_manager',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Create index on email for faster lookups
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);")
        
        # Create eligibility_checklist table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS eligibility_checklist (
                id SERIAL PRIMARY KEY,
                project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
                document_id INTEGER REFERENCES project_documents(id) ON DELETE CASCADE,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                criteria_text TEXT NOT NULL,
                is_checked BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Create unique index that handles NULL document_id properly
        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_eligibility_unique 
            ON eligibility_checklist(project_id, COALESCE(document_id, -1), user_id, criteria_text);
        """)
        
        # Create indices
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_file_hash_version ON file_cache(file_hash, processing_version);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_project_name ON projects(project_name);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_project_user_id ON projects(user_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_analysis_project_section ON analysis_records(project_id, section);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_eligibility_project_doc ON eligibility_checklist(project_id, document_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_eligibility_user ON eligibility_checklist(user_id);")
        
        conn.commit()
        cursor.close()
        conn.close()
        logger.info("✅ PostgreSQL Database initialized with project-centric tables")
    except Exception as e:
        logger.error(f"❌ Error initializing PostgreSQL: {str(e)}")
        if conn:
            conn.rollback()
            conn.close()

# PostgreSQL initialization disabled - Application now uses MongoDB
# Uncomment below if you need PostgreSQL for migration scripts only
# init_db()
