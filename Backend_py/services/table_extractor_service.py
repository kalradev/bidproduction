import logging
import tabula
import pandas as pd
import json
import re
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

async def extract_boq_table(buffer: bytes, plain_text: Optional[str] = None) -> Dict[str, Any]:
    logger.info("🎯 Starting DETERMINISTIC table extraction...")
    
    # Save buffer to temp file for tabula
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(buffer)
        tmp_path = tmp.name
        
    try:
        logger.info("🐍 Attempting tabula-py extraction...")
        # lattice=True for bordered, stream=True for borderless
        tables = tabula.read_pdf(
            tmp_path,
            pages='all',
            multiple_tables=True,
            lattice=True,
            stream=True,
            silent=True
        )
        
        if tables:
            processed_tables = []
            total_rows = 0
            for idx, df in enumerate(tables):
                if df.empty:
                    continue
                headers = [str(c) for c in df.columns]
                rows = []
                for _, row in df.iterrows():
                    row_list = [str(val).strip() for val in row]
                    if any(cell and cell != 'nan' and cell != 'None' for cell in row_list):
                        rows.append(row_list)
                
                if rows:
                    processed_tables.append({
                        'tableIndex': idx,
                        'headers': headers,
                        'rows': rows,
                        'rowCount': len(rows)
                    })
                    total_rows += len(rows)
            
            if processed_tables:
                # Identify BOQ table
                boq_table = identify_boq_table(processed_tables)
                if boq_table:
                    result = {
                        'success': True,
                        'method': 'tabula-deterministic',
                        'rowCount': boq_table['rowCount'],
                        'headers': boq_table['headers'],
                        'rows': boq_table['rows']
                    }
                    
                    # Check for transposed
                    transformed = transform_transposed_table(result['headers'], result['rows'])
                    if transformed:
                        return {
                            'success': True,
                            'rowCount': len(transformed['rows']),
                            'headers': transformed['headers'],
                            'rows': transformed['rows'],
                            'metadata': {'wasTransposed': True, 'method': 'tabula-transposed'}
                        }
                    return result
                    
        logger.info("⚠️ Tabula found no tables, falling back to text-based...")
    except Exception as e:
        logger.error(f"❌ Tabula extraction failed: {str(e)}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
            
    # Text-based fallback
    if plain_text:
        return extract_tables_from_text(plain_text)
        
    return {'success': False, 'rowCount': 0, 'rows': [], 'error': 'All methods failed'}

def identify_boq_table(processed_tables: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    boq_keywords = ['item', 'description', 'quantity', 'rate', 'amount', 'unit', 's.no', 'sr.no', 'boq', 'bom']
    best_match = None
    best_score = 0
    
    for table in processed_tables:
        headers_text = ' '.join(table['headers']).lower()
        score = sum(1 for keyword in boq_keywords if keyword in headers_text)
        if score > best_score and table['rowCount'] > 5:
            best_score = score
            best_match = table
            
    return best_match

def is_transposed_table(headers: List[str], rows: List[List[str]]) -> bool:
    if not headers or not rows:
        return False
    
    header_text = ' '.join(headers).lower()
    product_indicators = ['model', 'product', 'item', 'variant', 'type', 'version']
    has_product_headers = any(ind in header_text for ind in product_indicators)
    
    first_header = headers[0].lower()
    is_spec_header = 'specification' in first_header or 'feature' in first_header or not first_header
    
    spec_indicators = ['specification', 'feature', 'interface', 'performance', 'capacity', 'throughput']
    first_col_values = ' '.join([str(row[0]).lower() for row in rows[:15]])
    has_spec_first_col = any(ind in first_col_values for ind in spec_indicators)
    
    return (has_product_headers or has_spec_first_col) and 2 <= len(headers) <= 10

def transform_transposed_table(headers: List[str], rows: List[List[str]]) -> Optional[Dict[str, Any]]:
    if not is_transposed_table(headers, rows):
        return None
        
    product_headers = headers[1:]
    transformed_rows = []
    
    for col_idx in range(len(product_headers)):
        product_name = product_headers[col_idx] or f"Product {col_idx + 1}"
        specs = []
        for row in rows:
            if not row: continue
            spec_name = row[0].strip()
            spec_val = row[col_idx + 1].strip() if col_idx + 1 < len(row) else ""
            if spec_name and spec_val and spec_val not in ["-", "—", "N/A", "n/a", "nan"]:
                specs.append(f"{spec_name}: {spec_val}")
        
        if specs:
            transformed_rows.append([product_name, "; ".join(specs), "N/A", "N/A"])
            
    if not transformed_rows:
        return None
        
    return {
        "headers": ["Product Name", "Specifications", "Quantity", "Unit"],
        "rows": transformed_rows
    }

def extract_tables_from_text(text: str) -> Dict[str, Any]:
    lines = [L.strip() for L in text.split('\n') if L.strip()]
    rows = []
    
    # Very simple tabular detection for text
    for line in lines:
        cols = re.split(r'\s{2,}|\t|\|', line)
        cols = [c.strip() for c in cols if c.strip()]
        if len(cols) >= 2:
            rows.append(cols)
            
    if rows:
        return {
            'success': True,
            'rowCount': len(rows),
            'headers': [],
            'rows': rows,
            'metadata': {'method': 'text-based'}
        }
    return {'success': False, 'rowCount': 0, 'rows': []}
