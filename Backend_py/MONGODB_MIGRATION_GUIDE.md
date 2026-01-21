# MongoDB Migration Guide

## Overview
This application has been successfully migrated from PostgreSQL to MongoDB. All database operations now use MongoDB for data storage.

## What Changed

### 1. Configuration
- **File**: `Backend_py/core/config.py`
- Added `MONGODB_STRING` and `MONGODB_DB` configuration settings
- `.env` file should have: `MONGODB_STRING=mongodb+srv://...`

### 2. Database Connection
- **New File**: `Backend_py/core/mongodb.py`
- Replaces `core.database.get_db_connection()` for PostgreSQL
- Provides both sync (`get_mongodb()`) and async (`get_mongodb_async()`) connections
- Automatically handles ObjectId conversions

### 3. Models Converted
All models have been converted to use MongoDB:

#### `Backend_py/models/project.py`
- Uses MongoDB collections: `projects`, `project_documents`, `analysis_records`
- IDs are now MongoDB ObjectIds (stored as strings in API responses)

#### `Backend_py/models/file_cache.py`
- Uses MongoDB collection: `file_cache`
- JSON fields stored natively as objects (no JSON string parsing needed)

#### `Backend_py/models/eligibility_checklist.py`
- Uses MongoDB collection: `eligibility_checklist`
- Supports nested queries with ObjectId references

### 4. API Routes Converted
- `Backend_py/api/auth_routes.py` - User authentication
- `Backend_py/api/rfp_routes.py` - RFP analysis endpoints

### 5. Services Updated
- `Backend_py/services/project_service.py` - Project document processing

## Migration Steps

### Step 1: Install Dependencies
```bash
pip install pymongo motor
```

### Step 2: Verify MongoDB Connection String
Check `.env` file line 19:
```
MONGODB_STRING=mongodb+srv://bidproject_user:Bidproject123@bidproject.gnc49pm.mongodb.net/?appName=bidproject
```

### Step 3: Run Migration Script
```bash
cd Backend_py
python migrate_to_mongodb.py
```

This will:
- Migrate all users from PostgreSQL to MongoDB
- Migrate all projects
- Migrate all project documents
- Migrate analysis records
- Migrate file cache entries
- Migrate eligibility checklist items

### Step 4: Verify Migration
1. Check MongoDB collections are created
2. Verify data counts match PostgreSQL
3. Test application functionality

### Step 5: Test Application
1. Start the backend server
2. Test user registration/login
3. Test project creation
4. Test document upload and analysis
5. Verify all features work correctly

## MongoDB Collections

### Collections Created:
- `users` - User accounts and authentication
- `projects` - Project information
- `project_documents` - Uploaded documents and analysis
- `analysis_records` - Granular analysis tracking
- `file_cache` - Cached document processing results
- `eligibility_checklist` - Eligibility checklist items

## ID Handling

### Important Notes:
1. **PostgreSQL IDs** (integers) are replaced with **MongoDB ObjectIds** (strings)
2. All API responses convert ObjectIds to strings automatically
3. Foreign key relationships use ObjectId references
4. Migration script maintains ID mapping during transfer

### Example:
```python
# Old (PostgreSQL)
project_id = 123  # integer

# New (MongoDB)
project_id = "507f1f77bcf86cd799439011"  # string ObjectId
```

## Backward Compatibility

- Migration script reads from PostgreSQL and writes to MongoDB
- Original PostgreSQL database is NOT modified
- You can run migration multiple times (uses upsert logic)
- Both databases can coexist during transition period

## Troubleshooting

### Connection Issues
- Verify MongoDB connection string in `.env`
- Check MongoDB server is accessible
- Verify network/firewall settings for MongoDB Atlas

### Missing Data
- Run migration script again (idempotent)
- Check logs for errors during migration
- Verify PostgreSQL data exists

### ID Mismatches
- Migration script creates ID mappings
- Check `user_mapping`, `project_mapping`, `doc_mapping` in logs
- Verify foreign key relationships

## Performance Considerations

### Indexes Created:
- `users.email` - Unique index for fast lookups
- `projects.project_name + user_id` - Unique index
- `project_documents.project_id` - Index for queries
- `file_cache.file_hash + processing_version` - Unique index
- `eligibility_checklist.project_id + document_id + user_id + criteria_text` - Unique index

### MongoDB Advantages:
- Native JSON storage (no JSON parsing needed)
- Flexible schema (easy to add fields)
- Horizontal scalability
- Better performance for nested data structures

## Rollback Plan

If you need to rollback to PostgreSQL:

1. Keep PostgreSQL database intact (migration doesn't delete data)
2. Revert code changes (git checkout previous commit)
3. Restart application (it will use PostgreSQL again)

## Next Steps

After successful migration:
1. Monitor application performance
2. Verify all features work correctly
3. Consider removing PostgreSQL dependencies if not needed
4. Update documentation for team members

## Support

If you encounter issues:
1. Check migration logs for errors
2. Verify MongoDB connection string
3. Check MongoDB server status
4. Review error messages in application logs

