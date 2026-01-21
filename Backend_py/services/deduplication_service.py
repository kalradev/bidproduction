import logging
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

def get_edit_distance(s1: str, s2: str) -> int:
    if len(s1) < len(s2):
        return get_edit_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
        
    return previous_row[-1]

def calculate_similarity(s1: str, s2: str) -> float:
    if not s1 or not s2:
        return 0.0
    s1, s2 = s1.lower().strip(), s2.lower().strip()
    if s1 == s2:
        return 1.0
    longer = max(len(s1), len(s2))
    distance = get_edit_distance(s1, s2)
    return (longer - distance) / longer

def are_duplicates(p1: Dict[str, Any], p2: Dict[str, Any], threshold: float = 0.85) -> bool:
    n1, n2 = p1.get("productName", "").lower().strip(), p2.get("productName", "").lower().strip()
    if n1 == n2 and n1:
        return True
        
    name_sim = calculate_similarity(n1, n2)
    if name_sim >= threshold:
        oem1, oem2 = p1.get("oem", "Unspecified"), p2.get("oem", "Unspecified")
        if oem1 != "Unspecified" and oem2 != "Unspecified":
            oem_sim = calculate_similarity(oem1, oem2)
            if oem_sim < 0.5 and name_sim < 0.95:
                return False
        return True
    return False

def merge_specifications(s1: str, s2: str) -> str:
    if not s1: return s2 or ""
    if not s2: return s1 or ""
    
    parts1 = [p.strip() for p in re.split(r'[;,\n]', s1) if p.strip()]
    parts2 = [p.strip() for p in re.split(r'[;,\n]', s2) if p.strip()]
    
    all_parts = parts1 + parts2
    unique = []
    seen = set()
    for p in all_parts:
        if p.lower() not in seen:
            seen.add(p.lower())
            unique.append(p)
    return "; ".join(unique)

import re

def deduplicate_pipeline(products: List[Dict[str, Any]], options: Dict[str, Any] = None) -> Dict[str, Any]:
    options = options or {}
    threshold = options.get("threshold", 0.85)
    
    initial_count = len(products)
    if initial_count == 0:
        return {"products": [], "metadata": {"initialCount": 0, "finalCount": 0, "duplicatesRemoved": 0}}
        
    unique_products = []
    removed_count = 0
    
    for p in products:
        is_dup = False
        for up in unique_products:
            if are_duplicates(p, up, threshold):
                is_dup = True
                removed_count += 1
                # Merge logic
                if p.get("oem") != "Unspecified" and up.get("oem") == "Unspecified":
                    up["oem"] = p["oem"]
                if p.get("specifications") or up.get("specifications"):
                    up["specifications"] = merge_specifications(up.get("specifications", ""), p.get("specifications", ""))
                if p.get("confidence", 0) > up.get("confidence", 0):
                    up["confidence"] = p["confidence"]
                break
        if not is_dup:
            unique_products.append(p.copy())
            
    return {
        "products": unique_products,
        "metadata": {
            "initialCount": initial_count,
            "finalCount": len(unique_products),
            "duplicatesRemoved": removed_count
        }
    }
