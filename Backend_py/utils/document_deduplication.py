import re
from typing import List, Dict, Any

def normalize_document_name(doc_name: str) -> str:
    if not doc_name or not isinstance(doc_name, str):
        return doc_name
        
    normalized = doc_name.strip()
    # Convert to title case
    normalized = normalized.lower().title()
    
    # Handle common abbreviations
    uppercase_words = ['ISO', 'GST', 'PAN', 'EMD', 'MII', 'BIS', 'RoHS', 'MSME', 'PF', 'ESI', 'IT', 'TDS', 'NSIC', 'UAM']
    for word in uppercase_words:
        pattern = re.compile(rf'\b{word}\b', re.IGNORECASE)
        normalized = pattern.sub(word, normalized)
        
    return normalized

def deduplicate_documents(documents: List[str]) -> List[str]:
    if not isinstance(documents, list):
        return documents
        
    seen = set()
    result = []
    
    for doc in documents:
        if not doc or not isinstance(doc, str):
            continue
            
        normalized = normalize_document_name(doc)
        lower_key = normalized.lower()
        
        if lower_key not in seen:
            seen.add(lower_key)
            result.append(normalized)
            
    return result

def deduplicate_legal_documents(summaries: Dict[str, Any]) -> Dict[str, Any]:
    if not summaries or not isinstance(summaries, dict):
        return summaries
        
    if "legal" in summaries and isinstance(summaries["legal"].get("requiredDocuments"), list):
        summaries["legal"]["requiredDocuments"] = deduplicate_documents(summaries["legal"]["requiredDocuments"])
        
    return summaries
