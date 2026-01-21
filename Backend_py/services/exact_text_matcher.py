import re
from typing import List, Dict, Any, Optional, Set

def normalize_text(text: str) -> str:
    if not text or not isinstance(text, str):
        return ""
    
    # Normalize to lowercase and remove most punctuation
    text = text.lower()
    text = re.sub(r'\s+', ' ', text)
    # Keep some symbols commonly found in bids
    text = re.sub(r'[^\w\s₹$%.,\d]', '', text)
    return text.strip()

def extract_atomic_units(text: str) -> List[str]:
    if not text or not isinstance(text, str):
        return []
        
    units = []
    seen = set()
    
    # Split by sentence endings
    sentences = re.split(r'[.!?]\s+', text)
    # Split by line breaks
    lines = text.split('\n')
    # Split by common list markers
    list_items = re.split(r'(?:^|\n)\s*(?:[•\-\*]\s+|\d+[\.\)]\s+)', text)
    
    all_units = sentences + lines + list_items
    
    for unit in all_units:
        trimmed = unit.strip()
        if 10 <= len(trimmed) <= 500 and trimmed not in seen:
            seen.add(trimmed)
            units.append(trimmed)
            
    return units

def calculate_word_overlap(text1: str, text2: str) -> float:
    w1 = set(normalize_text(text1).split())
    w2 = set(normalize_text(text2).split())
    
    if not w1 or not w2:
        return 0.0
        
    intersection = w1.intersection(w2)
    union = w1.union(w2)
    
    return len(intersection) / len(union)

def extract_numeric_patterns(text: str) -> List[str]:
    patterns = []
    
    # Currency
    currency = re.findall(r'₹?\s*[\d,]+\.?d*\s*(?:lakhs?|crore?|cr|lacs?|\/-)?', text, re.IGNORECASE)
    patterns.extend(currency)
    
    # Percentages
    percentages = re.findall(r'\d+\.?\d*%', text)
    patterns.extend(percentages)
    
    # Numbers
    numbers = re.findall(r'\b\d+\b', text)
    patterns.extend(numbers)
    
    return [normalize_text(p) for p in patterns if p]

def find_exact_match(query: str, page_texts: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not query or not page_texts:
        return None
        
    n_query = normalize_text(query)
    q_numeric = extract_numeric_patterns(query)
    
    best_match = None
    best_score = 0.0
    
    for page_data in page_texts:
        page_num = page_data.get("pageNumber")
        sentences = page_data.get("sentences", [])
        if not sentences:
            sentences = extract_atomic_units(page_data.get("text", ""))
            
        for sentence in sentences:
            n_sentence = normalize_text(sentence)
            
            # Substring match
            if n_query in n_sentence or n_sentence in n_query:
                score = min(len(n_query), len(n_sentence)) / max(len(n_query), len(n_sentence))
                if score > best_score:
                    best_score = score
                    best_match = {
                        "matchedText": sentence,
                        "page": page_num,
                        "confidence": 1.0 if score >= 0.95 else 0.9,
                        "matchType": "full_substring"
                    }
            
            # Word overlap
            overlap = calculate_word_overlap(query, sentence)
            if overlap >= 0.7 and overlap > best_score:
                s_numeric = extract_numeric_patterns(sentence)
                num_overlap = 0.0
                if q_numeric:
                    num_overlap = len([p for p in q_numeric if p in s_numeric]) / len(q_numeric)
                
                combined = (overlap * 0.7) + (num_overlap * 0.3)
                if combined > best_score:
                    best_score = combined
                    best_match = {
                        "matchedText": sentence,
                        "page": page_num,
                        "confidence": 0.95 if combined >= 0.9 else combined,
                        "matchType": "phrase_overlap"
                    }
                    
    if best_match and best_match["confidence"] >= 0.85:
        return best_match
    return None

def find_all_exact_matches(query: str, page_texts: List[Dict[str, Any]], max_results: int = 3) -> List[Dict[str, Any]]:
    if not query or not page_texts:
        return []
        
    n_query = normalize_text(query)
    q_numeric = extract_numeric_patterns(query)
    matches = []
    seen = set()
    
    for page_data in page_texts:
        page_num = page_data.get("pageNumber")
        sentences = page_data.get("sentences", [])
        if not sentences:
            sentences = extract_atomic_units(page_data.get("text", ""))
            
        for sentence in sentences:
            n_sentence = normalize_text(sentence)
            overlap = calculate_word_overlap(query, sentence)
            
            is_full = n_query in n_sentence or n_sentence in n_query
            is_phrase = overlap >= 0.7
            
            if is_full or is_phrase:
                confidence = 0.0
                if is_full:
                    score = min(len(n_query), len(n_sentence)) / max(len(n_query), len(n_sentence))
                    confidence = 1.0 if score >= 0.95 else 0.9
                else:
                    s_numeric = extract_numeric_patterns(sentence)
                    num_overlap = 0.0
                    if q_numeric:
                        num_overlap = len([p for p in q_numeric if p in s_numeric]) / len(q_numeric)
                    confidence = (overlap * 0.7) + (num_overlap * 0.3)
                    
                if confidence >= 0.85:
                    key = f"{page_num}_{n_sentence[:50]}"
                    if key not in seen:
                        seen.add(key)
                        matches.append({
                            "matchedText": sentence,
                            "page": page_num,
                            "confidence": confidence,
                            "matchType": "full_substring" if is_full else "phrase_overlap"
                        })
                        
    matches.sort(key=lambda x: (-x["confidence"], x["page"]))
    return matches[:max_results]
