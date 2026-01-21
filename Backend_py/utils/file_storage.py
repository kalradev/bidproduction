import os
import logging
from core.config import settings

logger = logging.getLogger(__name__)

def store_file(buffer: bytes, file_hash: str, original_name: str) -> str:
    try:
        ext = os.path.splitext(original_name)[1].lower() or '.pdf'
        filename = f"{file_hash}{ext}"
        file_path = os.path.join(settings.UPLOAD_DIR, filename)
        
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        
        with open(file_path, 'wb') as f:
            f.write(buffer)
            
        logger.info(f"✅ File stored: {filename} ({len(buffer)/1024:.2f} KB)")
        return file_path
    except Exception as e:
        logger.error(f"Error storing file: {str(e)}")
        raise e

def get_stored_file_path(file_hash: str, original_name: str = None) -> Optional[str]:
    if not file_hash:
        return None
        
    ext = os.path.splitext(original_name)[1].lower() if original_name else ""
    filename = f"{file_hash}{ext or '.pdf'}"
    file_path = os.path.join(settings.UPLOAD_DIR, filename)
    
    if os.path.exists(file_path):
        return file_path
        
    # Try common extensions
    common_exts = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.png', '.jpg', '.jpeg']
    for ext in common_exts:
        alt_path = os.path.join(settings.UPLOAD_DIR, f"{file_hash}{ext}")
        if os.path.exists(alt_path):
            return alt_path
            
    # List all files with this hash prefix
    if os.path.exists(settings.UPLOAD_DIR):
        files = os.listdir(settings.UPLOAD_DIR)
        matches = [f for f in files if f.startswith(file_hash)]
        if matches:
            return os.path.join(settings.UPLOAD_DIR, matches[0])
            
    return None

def delete_stored_file(file_hash: str, original_name: str):
    try:
        ext = os.path.splitext(original_name)[1] or '.pdf'
        filename = f"{file_hash}{ext}"
        file_path = os.path.join(settings.UPLOAD_DIR, filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"✅ File deleted: {filename}")
    except Exception as e:
        logger.error(f"Error deleting file: {str(e)}")
