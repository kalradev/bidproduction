import logging
import hashlib
from typing import List, Dict, Any, Optional
from data.mii_database import classify_mii_status, get_all_indian_oems, get_all_global_oems

logger = logging.getLogger(__name__)

def simple_hash(str_val: str) -> int:
    """Generate deterministic hash for consistent selection."""
    hash_object = hashlib.md5(str_val.encode())
    return int(hash_object.hexdigest(), 16)

def select_deterministic(options: List[str], product_name: str) -> Optional[str]:
    if not options:
        return None
    index = simple_hash(product_name) % len(options)
    return options[index]

def clean_oem_name(oem_name: str) -> str:
    if not oem_name or not isinstance(oem_name, str):
        return oem_name
    
    cleaned = oem_name.replace(" or equivalent", "").replace("equivalent to", "").strip()
    
    # Handle separators
    if " / " in cleaned or "/" in cleaned:
        sep = " / " if " / " in cleaned else "/"
        parts = [p.replace(" or equivalent", "").strip() for p in cleaned.split(sep)]
        parts = [p for p in parts if p]
        cleaned = " / ".join(parts)
        
    return cleaned

def get_smart_default(product_name: str, category: str) -> Optional[Dict[str, Any]]:
    p_lower = product_name.lower()
    c_lower = category.lower()
    
    # Simplified version of the JS logic
    if 'hardware' in c_lower or 'server' in c_lower or 'computer' in c_lower:
        if 'rack' in p_lower or 'cabinet' in p_lower:
            racks = ['APC', 'Tripp Lite', 'Panduit', 'Rittal']
            return {"oem": select_deterministic(racks, product_name), "miiStatus": "Global OEM", "confidence": 65}
        if 'monitor' in p_lower or 'display' in p_lower:
            monitors = ['Dell', 'HP', 'LG', 'Samsung']
            return {"oem": select_deterministic(monitors, product_name), "miiStatus": "Global OEM", "confidence": 66}
            
    if 'networking' in c_lower or 'network' in c_lower:
        if 'switch' in p_lower:
            switches = ['Cisco Catalyst', 'HPE Aruba', 'Juniper']
            return {"oem": select_deterministic(switches, product_name), "miiStatus": "Global OEM", "confidence": 68}
            
    # Add more defaults as needed to match JS
    return None

async def enrich_products(products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    enriched = []
    for product in products:
        p_copy = product.copy()
        name = p_copy.get("productName", "")
        category = p_copy.get("category", "")
        oem = p_copy.get("oem", "Unspecified")
        
        # Clean OEM
        oem = clean_oem_name(oem)
        
        if not oem or oem == "Unspecified" or oem == "N/A":
            # Try smart default
            smart = get_smart_default(name, category)
            if smart:
                p_copy["oem"] = smart["oem"]
                p_copy["miiStatus"] = smart["miiStatus"]
                p_copy["confidence"] = smart["confidence"]
                p_copy["source"] = "smart_default"
            else:
                # Provide multiple options for variety as in JS
                options = ["Cisco", "IBM", "Oracle", "Dell", "HPE", "Microsoft"]
                h = simple_hash(name)
                sel_options = [options[h % len(options)], options[(h+1) % len(options)]]
                p_copy["oem"] = " / ".join(sel_options)
                p_copy["miiStatus"] = "Global OEM" # Should check both
                p_copy["source"] = "multiple_options"
        else:
            p_copy["miiStatus"] = classify_mii_status(oem, category)
            p_copy["confidence"] = 90
            p_copy["source"] = "document"
            
        enriched.append(p_copy)
    return enriched

def get_enrichment_stats(products: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(products)
    indian_oems = 0
    global_oems = 0
    unspecified = 0
    enriched = 0
    unique_oems = set()
    unique_indian = set()
    unique_global = set()
    
    for p in products:
        oem = p.get("oem", "Unspecified")
        status = p.get("miiStatus", "")
        
        if oem != "Unspecified" and oem != "N/A":
            enriched += 1
            unique_oems.add(oem)
            if "Indian" in status:
                indian_oems += 1
                unique_indian.add(oem)
            else:
                global_oems += 1
                unique_global.add(oem)
        else:
            unspecified += 1
            
    mii_compliance = f"{int((indian_oems / total * 100))}%" if total > 0 else "0%"
    
    return {
        "total": total,
        "enriched": enriched,
        "indianOEMs": indian_oems,
        "globalOEMs": global_oems,
        "unspecified": unspecified,
        "uniqueOEMCount": len(unique_oems),
        "uniqueIndianCount": len(unique_indian),
        "uniqueGlobalCount": len(unique_global),
        "miiCompliance": mii_compliance
    }
