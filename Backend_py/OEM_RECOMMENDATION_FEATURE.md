# 🎯 AI-Powered OEM & Model Recommendation System

## Overview

This system uses AI to dynamically recommend suitable OEM manufacturers and their specific models based on product specifications extracted from tender documents.

**Key Feature:** ZERO HARDCODING - All recommendations are generated in real-time by AI.

---

## 🌟 Features

### 1. **Dynamic AI Recommendations**
- Analyzes product specifications from tender documents
- Generates 2-3 OEM options with actual model names
- Matches specifications intelligently (size, material, features, capacity)
- No predefined mappings or hardcoded data

### 2. **Make in India (MII) Priority**
- Prioritizes Indian OEMs when specifications match
- Clearly labels Indian OEM vs Global OEM
- Helps meet government MII compliance requirements

### 3. **Best Fit Matching**
- Match Score (85-100%): How well the model matches specifications
- Price Range: Budget / Mid-Range / Premium
- Availability: Readily Available / On Order / Limited
- Reasoning: Why this model is recommended

### 4. **Multiple Options**
- Primary recommendation (Best match)
- Alternative options (2nd and 3rd choice)
- Provides flexibility for procurement decisions

---

## 🏗️ Architecture

### Backend Components

#### 1. **OEM Recommendation Service**
**File:** `Backend_py/services/oem_recommendation_service.py`

**Functions:**
- `recommend_oem_models()` - Generates AI recommendations for a single product
- `enrich_products_with_recommendations()` - Batch processes all products
- `get_recommendation_stats()` - Returns enrichment statistics

**AI Model:** GPT-4o-mini (cost-effective, fast)

**Parameters:**
- Product Name
- Category
- Specifications (from tender)
- Quantity
- Existing OEM (if mentioned in tender)

**Returns:**
```json
{
  "recommendations": [
    {
      "oem": "Manufacturer Name",
      "model": "Specific Model/Series",
      "miiStatus": "Indian OEM" or "Global OEM",
      "matchScore": 85-100,
      "priceRange": "Budget/Mid-Range/Premium",
      "availability": "Readily Available/On Order",
      "reasoning": "Why this matches specifications"
    }
  ]
}
```

#### 2. **Integration with Analysis Pipeline**
**File:** `Backend_py/services/ai_service.py`

**Process:**
1. Extract products from tender document
2. Run fallback BOQ extraction if needed
3. **NEW:** Enrich products with OEM recommendations
4. Store enriched data in database

**When Recommendations are Generated:**
- After product extraction completes
- Only for products with missing/N/A models
- Runs asynchronously in batches (5 concurrent)

---

### Frontend Components

#### **Product Mapping Page**
**File:** `Frontend/src/pages/ProductMappingPage.tsx`

**Display:**
- Shows 2-3 OEM options per product
- Primary recommendation highlighted as "BEST"
- Match score and price range displayed
- Model names with reasoning (truncated)
- MII status color-coded

**Visual Hierarchy:**
```
Product: Manager Table
Category: Furniture

OEM Options:
  1. Godrej [BEST]          Model: Executive Plus 1800
     Mid-Range • Match: 95%       Reasoning: Exact size match...
  
  2. Durian                 Model: Luxura Manager 1800
     Premium • Match: 90%         Reasoning: Premium quality...
  
  3. Featherlite            Model: Optima Executive
     Mid-Range • Match: 85%       Reasoning: Similar specs...

MII Status: Indian OEM
            +2 more options
```

---

## 🔄 Data Flow

```
┌─────────────────────────────────────────────────┐
│ 1. User Uploads Tender Document                │
└────────────────┬────────────────────────────────┘
                 ▼
┌─────────────────────────────────────────────────┐
│ 2. AI Extracts Products                         │
│    - Product Name                               │
│    - Category                                   │
│    - Specifications                             │
│    - Quantity                                   │
│    - OEM (if mentioned)                         │
└────────────────┬────────────────────────────────┘
                 ▼
┌─────────────────────────────────────────────────┐
│ 3. Fallback BOQ Extraction (if needed)          │
└────────────────┬────────────────────────────────┘
                 ▼
┌─────────────────────────────────────────────────┐
│ 4. AI OEM Recommendation Service                │
│    For each product:                            │
│    - Analyze specifications                     │
│    - Search AI knowledge base                   │
│    - Generate 2-3 recommendations               │
│    - Calculate match scores                     │
│    - Determine MII status                       │
└────────────────┬────────────────────────────────┘
                 ▼
┌─────────────────────────────────────────────────┐
│ 5. Store Enriched Data in Database              │
│    - Original product data                      │
│    - oemRecommendations array                   │
│    - Best recommendation as primary             │
└────────────────┬────────────────────────────────┘
                 ▼
┌─────────────────────────────────────────────────┐
│ 6. Frontend Displays Multiple Options           │
│    - Product Mapping page shows all options    │
│    - Visual hierarchy with match scores         │
│    - Color-coded MII status                     │
└─────────────────────────────────────────────────┘
```

---

## 📊 Example Scenarios

### Scenario 1: Furniture with Specifications

**Input from Tender:**
```
Product: Manager Table
Specifications: Size 1800x900mm, Laminated wood, 2 drawers
Quantity: 10 units
```

**AI Generates:**
```json
[
  {
    "oem": "Godrej",
    "model": "Executive Plus 1800 Premium Oak",
    "miiStatus": "Indian OEM",
    "matchScore": 95,
    "priceRange": "Mid-Range",
    "reasoning": "Exact size match, laminated wood finish, 2-drawer configuration"
  },
  {
    "oem": "Durian",
    "model": "Luxura Manager 1800 Walnut",
    "miiStatus": "Indian OEM",
    "matchScore": 90,
    "priceRange": "Premium",
    "reasoning": "Matches size and material, premium finish options"
  },
  {
    "oem": "Featherlite",
    "model": "Optima Executive XL Wood",
    "miiStatus": "Indian OEM",
    "matchScore": 85,
    "priceRange": "Mid-Range",
    "reasoning": "Similar specifications, ergonomic design"
  }
]
```

---

### Scenario 2: IT Equipment with Technical Specs

**Input from Tender:**
```
Product: Workstation
Specifications: Intel i7 12th Gen, 32GB RAM, 1TB SSD, Windows 11 Pro
Quantity: 50 units
OEM: HP / Dell / Equivalent
```

**AI Generates:**
```json
[
  {
    "oem": "HP",
    "model": "Z2 G9 Tower Workstation",
    "miiStatus": "Global OEM",
    "matchScore": 98,
    "priceRange": "Premium",
    "reasoning": "Pre-approved brand. Exact spec match: i7-12700, 32GB DDR4, 1TB NVMe"
  },
  {
    "oem": "Dell",
    "model": "Precision 3660 Tower",
    "miiStatus": "Global OEM",
    "matchScore": 96,
    "priceRange": "Premium",
    "reasoning": "Pre-approved brand. Matches all specs, enterprise support"
  },
  {
    "oem": "Lenovo",
    "model": "ThinkStation P360 Tower",
    "miiStatus": "Global OEM",
    "matchScore": 92,
    "priceRange": "Mid-Range",
    "reasoning": "Equivalent option. Similar specs, cost-effective"
  }
]
```

---

### Scenario 3: Electrical with Generic Specs

**Input from Tender:**
```
Product: LED Panel Light
Specifications: 600x600mm, 40W, 6500K Cool White
Quantity: 100 units
```

**AI Generates:**
```json
[
  {
    "oem": "Havells",
    "model": "Adore LED Panel Square 40W 6500K",
    "miiStatus": "Indian OEM",
    "matchScore": 100,
    "priceRange": "Mid-Range",
    "reasoning": "Exact match: 600x600mm size, 40W power, 6500K color temperature"
  },
  {
    "oem": "Philips",
    "model": "SmartBright LED Panel RC095V",
    "miiStatus": "Global OEM",
    "matchScore": 98,
    "priceRange": "Premium",
    "reasoning": "Perfect spec match, high CRI, long warranty"
  },
  {
    "oem": "Syska",
    "model": "SSK-EMB-40W-6500K Panel",
    "miiStatus": "Indian OEM",
    "matchScore": 95,
    "priceRange": "Budget",
    "reasoning": "Matches all specifications, budget-friendly option"
  }
]
```

---

## 🎯 Benefits

### For Bid Preparation
1. **Faster:** No manual research needed for each product
2. **Compliant:** All options match tender specifications
3. **Competitive:** Multiple options for cost optimization
4. **MII-Friendly:** Prioritizes Indian manufacturers

### For Procurement
1. **Validated Options:** All models meet specifications
2. **Fallback Choices:** Alternatives ready if primary unavailable
3. **Price Comparison:** Can compare across suggested options
4. **Quality Assurance:** AI considers brand reputation and availability

---

## 🔧 Configuration

### Environment Variables

Required in `.env`:
```bash
OPENAI_API_KEY=sk-your-key-here
```

### Cost Optimization

**Current Configuration:**
- Model: `gpt-4o-mini` (cost-effective)
- Temperature: `0.3` (consistent, factual)
- Concurrent requests: `5` (rate limit friendly)

**Estimated Cost:**
- ~$0.001 per product recommendation
- 100 products = ~$0.10
- 1000 products = ~$1.00

### Performance

**Processing Speed:**
- Single product: ~1-2 seconds
- 100 products: ~40-60 seconds (batched)
- Runs asynchronously, doesn't block analysis

---

## 📈 Statistics & Monitoring

### Logged Metrics

After enrichment, the system logs:
```
✅ OEM Enrichment Complete:
   - Products enriched: 95/100
   - Total recommendations: 285
   - Enrichment rate: 95%
```

### Data Structure in Database

Stored in `project_documents.analysis_data`:
```json
{
  "productMapping": {
    "miiProductStatus": [
      {
        "productName": "Manager Table",
        "category": "Furniture",
        "specifications": "1800x900mm, Laminated wood",
        "oem": "Godrej",
        "model": "Executive Plus 1800",
        "miiStatus": "Indian OEM",
        "oemRecommendations": [
          {
            "oem": "Godrej",
            "model": "Executive Plus 1800",
            "miiStatus": "Indian OEM",
            "matchScore": 95,
            "priceRange": "Mid-Range",
            "availability": "Readily Available",
            "reasoning": "Exact size match..."
          },
          // ... 2 more recommendations
        ],
        "recommendationSource": "ai_generated"
      }
    ]
  }
}
```

---

## 🚀 Usage

### For Developers

The system works automatically:
1. Upload tender document
2. Analysis runs (product extraction + OEM enrichment)
3. View results in Product Mapping page

No manual intervention needed!

### For Users

**Product Mapping Page:**
- Each product shows 2-3 OEM options
- Primary recommendation marked as "BEST"
- Match scores help decision-making
- Color-coded MII status (Green = Indian, Red = Global)
- Reasoning explains why each option is recommended

---

## 🔍 Troubleshooting

### No Recommendations Generated

**Possible Causes:**
1. OpenAI API key missing/invalid
2. Rate limit reached
3. Network issues

**Check Logs:**
```python
logger.info("🎯 Enriching X products with AI OEM recommendations...")
logger.info("✅ OEM Enrichment Complete: ...")
```

### Recommendations Not Displayed

**Check:**
1. Frontend receives `oemRecommendations` array
2. Browser console for errors
3. Data structure matches expected format

---

## 📝 Future Enhancements

### Potential Improvements
1. **Cache recommendations** for similar products
2. **Real-time pricing data** integration
3. **Availability checking** with supplier APIs
4. **User feedback loop** to improve recommendations
5. **Custom scoring weights** per category
6. **Multi-language support** for specifications

---

## ✅ Implementation Checklist

- [x] Create OEM recommendation service
- [x] Integrate with analysis pipeline
- [x] Update frontend display
- [x] Test with various product types
- [x] Documentation complete

---

## 📞 Support

For issues or questions:
1. Check logs in Backend console
2. Verify OpenAI API key is valid
3. Ensure internet connectivity
4. Review this documentation

---

**Status:** ✅ FULLY IMPLEMENTED & READY FOR USE

**Date:** January 19, 2026

**Version:** 1.0.0







