from fastapi import APIRouter, HTTPException, Body
import os
import logging

from core.config import settings
from services.exact_text_matcher import find_exact_match, find_all_exact_matches
from services.page_by_page_extractor import load_page_by_page_data, extract_page_by_page, store_page_by_page_data

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/exact-match")
async def get_exact_match(
    query: str = Body(..., embed=True),
    file_hash: str = Body(..., embed=True, alias="fileHash")
):
    try:
        logger.info(f"🔍 Exact match search: \"{query[:50]}...\" in {file_hash[:16]}...")
        
        # Load page-by-page data
        page_texts = load_page_by_page_data(file_hash)
        
        if not page_texts:
            logger.info("📄 Page-by-page data not found, extracting now...")
            # We need the original file buffer. 
            # In a real app we'd fetch it from storage using file_hash.
            # For now, let's look in UPLOAD_DIR
            possible_files = [f for f in os.listdir(settings.UPLOAD_DIR) if f.startswith(file_hash)]
            if not possible_files:
                raise HTTPException(status_code=404, detail="Document not found")
            
            file_path = os.path.join(settings.UPLOAD_DIR, possible_files[0])
            with open(file_path, 'rb') as f:
                buffer = f.read()
                
            page_texts = await extract_page_by_page(buffer, file_hash)
            store_page_by_page_data(file_hash, page_texts)
            
        match = find_exact_match(query, page_texts)
        
        if match and match["confidence"] >= 0.85:
            logger.info(f"✅ Exact match found: Page {match['page']}, Confidence: {match['confidence']}")
            return {
                "success": True,
                "reference": match
            }
        else:
            logger.info(f"⚠️ No exact match found (confidence: {match['confidence'] if match else 0})")
            return {
                "success": False,
                "error": "No exact match found",
                "reference": None,
                "confidence": match["confidence"] if match else 0
            }
            
    except Exception as e:
        logger.error(f"Error in exact match: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/exact-matches")
async def get_exact_matches(
    query: str = Body(..., embed=True),
    file_hash: str = Body(..., embed=True, alias="fileHash"),
    max_results: int = Body(3, embed=True, alias="maxResults")
):
    try:
        logger.info(f"🔍 Finding all exact matches: \"{query[:50]}...\" in {file_hash[:16]}...")
        
        page_texts = load_page_by_page_data(file_hash)
        
        if not page_texts:
            possible_files = [f for f in os.listdir(settings.UPLOAD_DIR) if f.startswith(file_hash)]
            if not possible_files:
                raise HTTPException(status_code=404, detail="Document not found")
            
            file_path = os.path.join(settings.UPLOAD_DIR, possible_files[0])
            with open(file_path, 'rb') as f:
                buffer = f.read()
                
            page_texts = await extract_page_by_page(buffer, file_hash)
            store_page_by_page_data(file_hash, page_texts)
            
        matches = find_all_exact_matches(query, page_texts, max_results)
        
        if matches:
            logger.info(f"✅ Found {len(matches)} exact matches")
            return {
                "success": True,
                "references": matches
            }
        else:
            logger.info("⚠️ No exact matches found")
            return {
                "success": False,
                "error": "No exact matches found",
                "references": []
            }
            
    except Exception as e:
        logger.error(f"Error finding exact matches: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
