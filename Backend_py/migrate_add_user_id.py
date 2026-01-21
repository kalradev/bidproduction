"""
Migration script to add user_id column to projects table.
This script handles existing databases that don't have the user_id column yet.
"""
from core.database import get_db_connection
import logging

logger = logging.getLogger(__name__)

def migrate():
    """Add user_id column to projects table if it doesn't exist"""
    conn = get_db_connection()
    if not conn:
        print("❌ Database connection failed")
        return False
    
    try:
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='projects' AND column_name='user_id';
        """)
        
        if cursor.fetchone():
            print("✅ user_id column already exists in projects table")
            cursor.close()
            conn.close()
            return True
        
        # Add the column
        print("🔄 Adding user_id column to projects table...")
        cursor.execute("""
            ALTER TABLE projects 
            ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE CASCADE;
        """)
        
        # Create index for better query performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_project_user_id ON projects(user_id);
        """)
        
        conn.commit()
        print("✅ Migration completed: user_id column added to projects table")
        print("⚠️  Note: Existing projects will have NULL user_id. They won't appear for new users.")
        print("   You may want to assign them to a specific user or leave them as-is.")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {str(e)}")
        logger.error(f"Migration error: {str(e)}", exc_info=True)
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("🚀 Starting migration: Add user_id to projects table")
    print("-" * 60)
    success = migrate()
    print("-" * 60)
    if success:
        print("✅ Migration completed successfully!")
    else:
        print("❌ Migration failed. Please check the error messages above.")

