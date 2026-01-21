"""
Fallback BOQ/Product extractor for when AI fails to extract products
This directly parses the document text for product tables
"""
import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def extract_products_from_text(document_text: str) -> List[Dict[str, Any]]:
    """
    Extract products from document text when AI fails
    Looks for BOQ/BOM tables and parses them
    """
    logger.info("🔧 Fallback: Attempting direct BOQ extraction from document text...")
    
    products = []
    
    # Strategy 1: Look for table-like structures with | or tab delimiters
    lines = document_text.split('\n')
    
    # Find sections that might contain BOQ
    boq_section_starts = []
    for i, line in enumerate(lines):
        line_lower = line.lower()
        if any(keyword in line_lower for keyword in ['bill of quantities', 'boq', 'bom', 'bill of materials', 'schedule of items', 'item description', 'annexure', 'annexe', 'schedule', 'technical specifications', 'product list', 'items to be supplied']):
            boq_section_starts.append(i)
            logger.info(f"   Found potential BOQ section at line {i}: {line[:80]}")
    
    if not boq_section_starts:
        logger.warning("   No BOQ section header found")
        # Try scanning entire document for table-like structures
        logger.info("   Attempting to find tables in entire document...")
        boq_section_starts = [0]
    
    # Extract table rows from all BOQ sections
    all_table_rows = []
    for boq_section_start in boq_section_starts[:3]:  # Check up to 3 sections
        # Extract table rows from BOQ section (next 300 lines after header)
        table_section = lines[boq_section_start:min(boq_section_start + 300, len(lines))]
        
        # Look for rows with delimiters (| or multiple spaces/tabs)
        for line in table_section:
            # Check if line looks like a table row
            if '|' in line or '\t' in line or re.search(r'\s{3,}', line):
                # Skip empty or header-like rows
                if line.strip() and not all(c in '-=|+\t ' for c in line.strip()):
                    all_table_rows.append(line)
    
    if not all_table_rows:
        logger.warning("   No table rows found in any BOQ section")
        # Try a more aggressive approach - look for numbered lists
        logger.info("   Trying to find numbered item lists...")
        for line in lines:
            # Look for lines starting with numbers (potential product items)
            if re.match(r'^\s*\d+[\.)]\s+\w', line):
                all_table_rows.append(line)
    
    if not all_table_rows:
        logger.warning("   No table rows or numbered lists found")
        return []
    
    logger.info(f"   Found {len(all_table_rows)} potential table rows")
    
    # Parse rows
    sr_no_pattern = re.compile(r'^\s*(\d+)[.|)]?\s*')  # Matches: "1.", "1)", "1 "
    
    for row in all_table_rows[:100]:  # Limit to first 100 rows
        # Try to extract product info
        row_clean = row.strip()
        
        # Split by | or tab
        if '|' in row_clean:
            cells = [c.strip() for c in row_clean.split('|') if c.strip()]
        elif '\t' in row_clean:
            cells = [c.strip() for c in row_clean.split('\t') if c.strip()]
        else:
            # Split by multiple spaces
            cells = [c.strip() for c in re.split(r'\s{2,}', row_clean) if c.strip()]
        
        if len(cells) < 2:
            continue
        
        # Check if first cell is a serial number
        sr_match = sr_no_pattern.match(cells[0])
        if sr_match:
            sr_no = sr_match.group(1)
            # Product name is usually the second cell or remainder of first cell
            product_name = cells[1] if len(cells) > 1 else cells[0][len(sr_match.group(0)):].strip()
        else:
            # No serial number, assume first cell is product name
            product_name = cells[0]
            sr_no = str(len(products) + 1)
        
        # Skip if product name looks like a header
        if any(keyword in product_name.lower() for keyword in ['sr.no', 'sl.no', 'item', 'description', 'product', 'quantity', 'total']):
            continue
        
        # Skip if product name is too short or looks invalid
        if len(product_name) < 3 or product_name.isdigit():
            continue
        
        # Extract quantity (look for numbers)
        quantity = "N/A"
        unit = "N/A"
        for cell in cells[1:]:
            # Check if cell is a number (quantity)
            if re.match(r'^\d+(\.\d+)?$', cell):
                quantity = cell
            # Check for units
            elif cell.lower() in ['nos', 'no', 'pcs', 'units', 'set', 'sets', 'meter', 'meters', 'kg', 'liter']:
                unit = cell
        
        # Create product object
        product = {
            "srNo": sr_no,
            "productName": product_name[:100],  # Limit length
            "category": "Other",  # Will be classified later
            "specifications": " | ".join(cells[2:5]) if len(cells) > 2 else "",
            "quantity": quantity,
            "unit": unit,
            "oem": "Unspecified",
            "model": "N/A",
            "miiStatus": "Pending Classification",
            "source": "fallback-extraction"
        }
        
        products.append(product)
    
    logger.info(f"   ✅ Fallback extracted {len(products)} products")
    if products:
        logger.info(f"   Sample: {products[0]['productName']}")
    
    return products


def enhance_analysis_with_fallback_products(analysis_data: Dict[str, Any], document_text: str) -> Dict[str, Any]:
    """
    Check if productMapping is empty and try fallback extraction if needed
    """
    if not analysis_data.get("productMapping"):
        logger.warning("No productMapping in analysis data")
        return analysis_data
    
    product_mapping = analysis_data["productMapping"]
    current_products = product_mapping.get("miiProductStatus", [])
    
    if len(current_products) == 0:
        logger.info("🔄 AI extracted 0 products - trying fallback BOQ extraction...")
        fallback_products = extract_products_from_text(document_text)
        
        if fallback_products:
            logger.info(f"✅ Fallback extraction successful: {len(fallback_products)} products found")
            product_mapping["miiProductStatus"] = fallback_products
            product_mapping["totalItems"] = len(fallback_products)
            product_mapping["extractionMethod"] = "fallback"
            analysis_data["productMapping"] = product_mapping
        else:
            logger.warning("⚠️ Fallback extraction also found 0 products")
    
    return analysis_data

