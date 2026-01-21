import os
import json
import logging
import re
from typing import List, Dict, Any, Optional
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer
from core.config import settings

logger = logging.getLogger(__name__)

def extract_atomic_units(text: str) -> List[str]:
    if not text:
        return []
    
    units = []
    seen = set()
    
    # Split by sentence endings
    sentences = re.split(r'[.!?]\s+', text)
    # Split by line breaks
    lines = text.split('\n')
    
    all_units = sentences + lines
    for unit in all_units:
        trimmed = unit.strip()
        if 10 <= len(trimmed) <= 500 and trimmed not in seen:
            seen.add(trimmed)
            units.append(trimmed)
    
    return units

async def extract_page_by_page(buffer: bytes, file_hash: str = None) -> List[Dict[str, Any]]:
    # Save buffer to temp file
    temp_dir = os.path.join(settings.DATA_DIR, 'temp')
    os.makedirs(temp_dir, exist_ok=True)
    
    temp_file_path = os.path.join(temp_dir, f"{file_hash or 'temp'}.pdf")
    with open(temp_file_path, 'wb') as f:
        f.write(buffer)
        
    try:
        page_data = []
        page_num = 0
        
        for page_layout in extract_pages(temp_file_path):
            page_num += 1
            page_text = ""
            
            for element in page_layout:
                if isinstance(element, LTTextContainer):
                    page_text += element.get_text()
            
            if page_text and page_text.strip():
                sentences = extract_atomic_units(page_text)
                page_data.append({
                    'pageNumber': page_num,
                    'text': page_text,
                    'sentences': sentences,
                    'wordCount': len(page_text.split())
                })
        
        return page_data
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

def store_page_by_page_data(file_hash: str, page_data: List[Dict[str, Any]]):
    storage_dir = os.path.join(settings.DATA_DIR, 'pageTexts')
    os.makedirs(storage_dir, exist_ok=True)
    
    file_path = os.path.join(storage_dir, f"{file_hash}.json")
    
    data = {
        "fileHash": file_hash,
        "totalPages": len(page_data),
        "pages": page_data
    }
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    
    logger.info(f"✅ Stored page-by-page data: {file_path} ({len(page_data)} pages)")

def load_page_by_page_data(file_hash: str) -> Optional[List[Dict[str, Any]]]:
    storage_dir = os.path.join(settings.DATA_DIR, 'pageTexts')
    file_path = os.path.join(storage_dir, f"{file_hash}.json")
    
    if not os.path.exists(file_path):
        return None
        
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        return data.get("pages", [])
