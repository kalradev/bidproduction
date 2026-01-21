import json
import logging
import asyncio
import re
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from core.config import settings

logger = logging.getLogger(__name__)

async_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

def validate_product_row(mapped_product: Dict[str, Any], raw_row: List[str]) -> bool:
    if not mapped_product.get("isValid"):
        return False
    
    product_name = mapped_product.get("productName", "").strip()
    if not product_name or len(product_name) < 3:
        return False
        
    invalid_names = [
        'n/a', 'not applicable', 'tbd', 'to be decided', 
        'miscellaneous', 'others', 'various', 
        'total', 'grand total', 'sub total', 'subtotal',
        'page', 'continued', 'cont.', 'header', 'footer',
        'item', 'description', 'quantity', 'rate', 'amount'
    ]
    
    p_lower = product_name.lower()
    for inv in invalid_names:
        if p_lower == inv or inv in p_lower:
            return False
            
    if raw_row:
        first_col = str(raw_row[0]).strip().lower()
        if first_col in ['s.no', 'sr.no', 'item', 'sl.no', 'no.']:
            return False
            
    return True

async def map_row_to_product(row: List[str], headers: List[str] = None, document_context: str = '') -> Optional[Dict[str, Any]]:
    try:
        headers = headers or []
        row_data = {}
        for i, h in enumerate(headers):
            if i < len(row):
                row_data[h] = row[i]
                
        row_text = json.dumps(row_data) if headers else " | ".join(row)
        
        system_prompt = "You are a BOQ (Bill of Quantities) and Product Specifications data mapper. Your task is to extract product information from table rows and map them to structured product objects."
        
        user_prompt = f"""Extract product information from this table row.

**CONTEXT:** {document_context or 'RFP/Tender Document'}

**TABLE HEADERS:** {', '.join(headers) if headers else 'No headers provided'}

**ROW DATA:**
{row_text}

**TASK:**
Map this row to a structured product object. Extract:
1. Product name (the item description, model name, or product identifier)
2. Quantity (if present)
3. Unit (e.g., nos, units, pcs, meters)
4. OEM/Brand (if mentioned in row, otherwise return "Unspecified")
5. Model (extract specific model number/name if present in the row data. If no model found, return "N/A")
6. Category (infer from product type: Hardware, Software, Civil, Electrical, Furniture, HVAC, Security, Networking, etc.)
7. Specifications (any technical details, performance metrics, features)

**SPECIAL HANDLING FOR SPECIFICATION TABLES:**
- If product name is "Model 1", "Model 2", "Model 3", etc., use that as the product name
- Extract all specifications from the row and include them in the specifications field

**CRITICAL RULES:**
- Product name MUST be specific and real
- If OEM/Brand not in row, return "Unspecified"
- Category must be one of: Hardware, Software, Civil, Electrical, Furniture, HVAC, Security, Networking, Mechanical, Plumbing, Other
- If this row is NOT a product (e.g., header, total, page number, footer), mark isValid as false

**OUTPUT FORMAT (JSON only):**
{{
  "productName": "string",
  "quantity": "number or string",
  "unit": "string",
  "oem": "string",
  "model": "string",
  "category": "string",
  "specifications": "string",
  "isValid": true/false
}}"""

        response = await async_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.0,
            response_format={"type": "json_object"}
        )
        
        mapped = json.loads(response.choices[0].message.content)
        
        if not validate_product_row(mapped, row):
            return None
            
        model = mapped.get("model", "N/A")
        if model == "N/A" or not model.strip():
            model = mapped.get("productName", "Standard Model")
            
        return {
            "productName": mapped.get("productName"),
            "quantity": mapped.get("quantity", "N/A"),
            "unit": mapped.get("unit", "N/A"),
            "oem": mapped.get("oem", "Unspecified"),
            "model": model,
            "category": mapped.get("category", "Other"),
            "specifications": mapped.get("specifications", ""),
            "miiStatus": "Pending Classification",
            "confidence": 85,
            "source": "table-extraction",
            "rawRow": row
        }
    except Exception as e:
        logger.error(f"Error mapping row: {str(e)}")
        return None

async def map_rows_to_products(rows: List[List[str]], headers: List[str] = None, document_context: str = '') -> List[Dict[str, Any]]:
    logger.info(f"🔄 Mapping {len(rows)} rows to products...")
    
    products = []
    batch_size = 10
    
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i+batch_size]
        tasks = [map_row_to_product(row, headers, document_context) for row in batch]
        results = await asyncio.gather(*tasks)
        products.extend([r for r in results if r])
        
        if i + batch_size < len(rows):
            await asyncio.sleep(1)
            
    logger.info(f"✅ Successfully mapped {len(products)} valid products from {len(rows)} rows")
    return products
