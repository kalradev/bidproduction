import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from models.project import ProjectModel
from services.ai_service import generate_departmental_summaries

logger = logging.getLogger(__name__)

class ProjectService:
    @staticmethod
    async def process_project_document(
        project_name: str,
        tender_id: str,
        client_name: str,
        update_type: str,
        file_hash: str,
        file_name: str,
        extracted_text: str,
        user_id  # Can be int (for migration) or str (MongoDB ObjectId)
    ) -> Dict[str, Any]:
        # 1. Check if project exists (scoped to user)
        project = ProjectModel.get_by_name(project_name, user_id)
        
        previous_analysis = None
        if not project:
            if update_type != 'BASE_RFP':
                raise ValueError(f"Project '{project_name}' does not exist. First upload must be BASE_RFP.")
            
            project_id = ProjectModel.create(project_name, tender_id, client_name, user_id)
            if not project_id:
                raise ValueError("Failed to create new project.")
            logger.info(f"✨ Created NEW PROJECT: {project_name} (ID: {project_id}) for user {user_id}")
        else:
            project_id = project['id']
            # Verify the project belongs to this user
            if project.get('user_id') != user_id:
                raise ValueError(f"Project '{project_name}' does not belong to you.")
            if update_type == 'BASE_RFP':
                 raise ValueError(f"Project '{project_name}' already has a BASE_RFP. Use CORRIGENDUM or REFERENCE_UPDATE.")
            
            # Fetch latest document's analysis to merge with
            from core.mongodb import get_mongodb, str_to_objectid
            db = get_mongodb()
            if db is not None:
                try:
                    project_oid = str_to_objectid(project_id) if isinstance(project_id, str) else project_id
                    doc = db.project_documents.find_one(
                        {"project_id": project_oid},
                        sort=[("created_at", -1)]  # Latest first
                    )
                    if doc and doc.get('analysis_data'):
                        previous_analysis = doc['analysis_data']
                        logger.info(f"🔄 Found previous analysis for project {project_id} to merge with.")
                except Exception as e:
                    logger.error(f"Error fetching previous analysis: {str(e)}")

            logger.info(f"📁 Adding to EXISTING PROJECT: {project_name} (ID: {project_id}, Type: {update_type})")

        # 2. Extract structured data using AI
        ai_result = await generate_departmental_summaries(extracted_text, file_name)
        new_summaries = ai_result['summaries']
        
        # Debug: Log product mapping extraction
        if new_summaries.get("productMapping"):
            pm = new_summaries["productMapping"]
            product_count = len(pm.get("miiProductStatus", []))
            logger.info(f"📦 Product Mapping extracted: {product_count} products found")
            if product_count > 0:
                logger.info(f"   Sample product: {pm['miiProductStatus'][0]}")
            else:
                logger.warning("⚠️ No products extracted from document! Check if document contains BOQ/BOM.")
        else:
            logger.warning("⚠️ No productMapping section in AI response!")
        
        # 3. Merge with previous analysis if it exists
        if previous_analysis:
            from services.ai_service import naive_merge_summaries
            logger.info(f"⚖️ Merging NEW {update_type} with existing project baseline...")
            # We want new corrigendum to override previous RFP/Update
            merged_summaries = naive_merge_summaries([previous_analysis, new_summaries])
        else:
            merged_summaries = new_summaries

        # Perform OEM Enrichment on the merged result
        await ProjectService._enrich_and_sync_summaries(merged_summaries, [file_name])
        
        # Validate EMD vs Bid Value
        merged_summaries = ProjectService._validate_emd_vs_bid_value(merged_summaries)
        
        # Debug: Log final product mapping after enrichment
        if merged_summaries.get("productMapping"):
            pm = merged_summaries["productMapping"]
            product_count = len(pm.get("miiProductStatus", []))
            logger.info(f"✅ Final Product Mapping after enrichment: {product_count} products")
            logger.info(f"   Total Items: {pm.get('totalItems', 0)}")
            logger.info(f"   Products Mapped: {pm.get('productsMapped', 0)}")
        else:
            logger.error("❌ productMapping missing after enrichment!")

        # 4. Store document
        doc_id = ProjectModel.add_document(
            project_id, file_hash, file_name, update_type, extracted_text, merged_summaries
        )
        
        # 5. Store granular records for audit trace
        ProjectService._store_granular_records(project_id, doc_id, update_type, file_name, file_hash, new_summaries)
        
        # 6. Return both merged analysis and auditable trace
        final_data = ProjectService.get_final_analysis(project_id)
        final_data['departmentalSummaries'] = merged_summaries
        final_data['project_id'] = project_id  # Include project_id for document lookup
        
        # Debug: Final check of product mapping
        if merged_summaries.get("productMapping"):
            pm = merged_summaries["productMapping"]
            product_count = len(pm.get("miiProductStatus", []))
            logger.info(f"✅ Final return: {product_count} products in productMapping.miiProductStatus")
        else:
            logger.error("❌ CRITICAL: productMapping missing in final merged_summaries!")
        
        return final_data

    @staticmethod
    def _store_granular_records(project_id, doc_id, source_type: str, file_name: str, file_hash: str, summaries: Dict[str, Any]):
        """Breaks down the AI summary into auditable records."""
        sections_to_extract = [
            ('projectOverview', 'Project Overview'),
            ('bidManagement.successFactors', 'Success Factors'),
            ('bidManagement.keyPoints', 'Key Points'),
            ('bidManagement.complianceRequirements', 'Compliance Requirements'),
            ('bidManagement.riskAreas', 'Risk Areas'),
            ('bidManagement.riskFactors', 'Risk Factors'),
            ('technical.criticalRequirements', 'Technical Requirements'),
            ('commercial.keyTerms', 'Commercial Terms'),
            ('finance.financialRequirements', 'Financial Requirements'),
            ('legal.complianceRequirements', 'Legal Requirements')
        ]

        for path, section_name in sections_to_extract:
            data = ProjectService._get_nested_val(summaries, path)
            if not data: continue

            if isinstance(data, dict):
                # Handle categorized data e.g. {"Financial": ["item1"]}
                for category, items in data.items():
                    if isinstance(items, list):
                        for item in items:
                            ProjectModel.add_analysis_record(
                                project_id, doc_id, f"{section_name} - {category}", 
                                str(item), source_type, file_name, file_hash
                            )
                    elif items and items != 'N/A':
                         ProjectModel.add_analysis_record(
                             project_id, doc_id, f"{section_name} - {category}", 
                             str(items), source_type, file_name, file_hash
                         )
            elif isinstance(data, list):
                for item in data:
                    ProjectModel.add_analysis_record(
                        project_id, doc_id, section_name, 
                        str(item), source_type, file_name, file_hash
                    )
            elif data and data != 'N/A':
                 ProjectModel.add_analysis_record(
                     project_id, doc_id, section_name, 
                     str(data), source_type, file_name, file_hash
                 )

    @staticmethod
    def _get_nested_val(data: Dict[str, Any], path: str) -> Any:
        keys = path.split('.')
        for key in keys:
            if isinstance(data, dict):
                data = data.get(key)
            else:
                return None
        return data

    @staticmethod
    def _validate_emd_vs_bid_value(departmental_summaries: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that EMD and Bid Value are not the same (EMD should be much smaller)"""
        project_overview = departmental_summaries.get("projectOverview", {})
        emd = project_overview.get("emd", "")
        bid_value = project_overview.get("bidValue", "")
        
        # If both exist and appear to be the same value, flag it
        if emd and bid_value and emd != "N/A" and bid_value != "N/A":
            # Extract numeric values (remove currency symbols, commas, etc.)
            import re
            emd_clean = emd.replace(',', '').replace('₹', '').replace('Rs.', '').replace('Rs', '').strip()
            bid_clean = bid_value.replace(',', '').replace('₹', '').replace('Rs.', '').replace('Rs', '').strip()
            
            emd_num = re.findall(r'[\d.]+', emd_clean)
            bid_num = re.findall(r'[\d.]+', bid_clean)
            
            if emd_num and bid_num:
                try:
                    emd_val = float(emd_num[0])
                    bid_val = float(bid_num[0])
                    
                    # If they're exactly the same or very close, this is likely wrong
                    if abs(emd_val - bid_val) < 0.01 or (emd_val == bid_val):
                        logger.warning(f"⚠️ VALIDATION ERROR: EMD ({emd}) and Bid Value ({bid_value}) appear to be the same!")
                        logger.warning("   EMD should typically be 1-2% of Bid Value")
                        logger.warning("   This suggests incorrect extraction - please verify in source document")
                        # Mark bidValue as potentially incorrect if EMD seems reasonable
                        if emd_val < 10000000:  # If EMD is less than 1 crore, it's probably correct
                            logger.warning(f"   EMD ({emd}) seems reasonable - Bid Value might be incorrectly extracted")
                            project_overview["bidValue"] = "N/A"  # Mark as unknown to force re-extraction
                except (ValueError, IndexError):
                    pass
        
        return departmental_summaries

    @staticmethod
    def _ensure_stats_consistency(departmental_summaries: Dict[str, Any]):
        """Recalculates enrichment statistics for cached or processed data."""
        from services.oem_enrichment_service import get_enrichment_stats
        
        if (departmental_summaries.get("productMapping") and 
            departmental_summaries["productMapping"].get("miiProductStatus")):
            products = departmental_summaries["productMapping"]["miiProductStatus"]
            stats = get_enrichment_stats(products)
            
            departmental_summaries["productMapping"]["totalOEMs"] = {
                "count": stats["uniqueOEMCount"],
                "indian": stats["uniqueIndianCount"],
                "global": stats["uniqueGlobalCount"]
            }
            departmental_summaries["productMapping"]["productsMapped"] = stats["enriched"]
            departmental_summaries["productMapping"]["totalItems"] = stats["total"]
            
            mapped = stats["indianOEMs"]
            unmapped = stats["total"] - mapped
            departmental_summaries["productMapping"]["makeInIndiaMapping"] = {
                "status": stats["miiCompliance"],
                "mapped": mapped,
                "unmapped": unmapped
            }

    @staticmethod
    async def _enrich_and_sync_summaries(summaries: Dict[str, Any], filenames: List[str]):
        """Performs OEM enrichment and syncs technical specifications."""
        from services.oem_enrichment_service import enrich_products, get_enrichment_stats
        
        if (summaries.get("productMapping") and 
            summaries["productMapping"].get("miiProductStatus")):
            products = summaries["productMapping"]["miiProductStatus"]
            valid_products = [p for p in products if p.get("productName") and p.get("productName").strip() not in ["", "N/A", "n/a"]]
            
            enriched_products = await enrich_products(valid_products)
            stats = get_enrichment_stats(enriched_products)
            
            summaries["productMapping"]["miiProductStatus"] = enriched_products
            summaries["productMapping"]["totalOEMs"] = {
                "count": stats["uniqueOEMCount"],
                "indian": stats["uniqueIndianCount"],
                "global": stats["uniqueGlobalCount"]
            }
            summaries["productMapping"]["productsMapped"] = stats["enriched"]
            summaries["productMapping"]["totalItems"] = stats["total"]
            
            mapped = stats["indianOEMs"]
            unmapped = stats["total"] - mapped
            summaries["productMapping"]["makeInIndiaMapping"] = {
                "status": stats["miiCompliance"],
                "mapped": mapped,
                "unmapped": unmapped
            }
            
            if summaries.get("technical"):
                summaries["technical"]["totalItems"] = stats["total"]
                summaries["technical"]["keySpecifications"] = [
                    {"productName": p.get("productName", "N/A"), "specification": p.get("specifications", "").strip() or "No specifications mentioned"}
                    for p in enriched_products
                ]

    @staticmethod
    def get_final_analysis(project_id) -> Dict[str, Any]:
        """Produces the merged 'FINAL VISIBLE ANALYSIS'."""
        records = ProjectModel.get_merged_analysis(project_id)
        
        # Rule 1: CORRIGENDUM overrides everything
        # Rule 2: REFERENCE_UPDATE overrides BASE_RFP
        # Rule 3: BASE_RFP is fallback
        
        # We group by section + content (or just section for direct overrides)
        # Actually, if it's a list, we might want to show all.
        # But for "updated" items, we should prioritize.
        
        # For simplicity in this implementation, we will provide a list of all records 
        # but the latest for each section/category pair will be marked or highlighted.
        
        # Let's try to reconstruct a summary object similar to original but with source info.
        merged_summary = {}
        
        # Priority mapping
        priority = {'CORRIGENDUM': 3, 'REFERENCE_UPDATE': 2, 'BASE_RFP': 1}
        
        # Record tracking: section -> list of items (with priority info)
        section_data = {}
        
        for rec in records:
            sec = rec['section']
            if sec not in section_data:
                section_data[sec] = []
            
            # Simple heuristic: if a record from a higher priority source exists in the same section,
            # we might want to replace or append.
            # Tender management usually wants to see the TRACE.
            section_data[sec].append({
                "content": rec['content'],
                "source": rec['source_type'],
                "file": rec['source_file_name'],
                "timestamp": rec['created_at'].isoformat() if hasattr(rec['created_at'], 'isoformat') else str(rec['created_at'])
            })
            
        return {
            "project_id": project_id,
            "merged_analysis": section_data,
            "timestamp": datetime.now().isoformat()
        }
