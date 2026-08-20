"""End-to-end Pipeline Orchestrator coordinating Ingestion -> OCR -> Extraction -> Classification -> Drafting."""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

import config
from pipeline.classification import DepartmentClassifier
from pipeline.database import get_source_details, init_db, log_audit, record_source, save_ocr_correction
from pipeline.extraction import TamilEntityExtractor
from pipeline.generation import TamilDraftGenerator
from pipeline.ocr_engine import IndicOCREngine

logger = logging.getLogger("PipelineOrchestrator")


class WorkflowPipeline:
    """Orchestrator managing end-to-end workflow execution for petitions."""

    def __init__(self):
        self.ocr_engine = IndicOCREngine()
        self.extractor = TamilEntityExtractor()
        self.classifier = DepartmentClassifier()
        self.drafter = TamilDraftGenerator()

    def process_source(self, source_id: str, file_path: Optional[Path] = None, force_reocr: bool = False) -> Dict[str, Any]:
        """Execute full pipeline for a registered source."""
        logger.info(f"== Starting Pipeline Run for Source: {source_id} ==")

        details = get_source_details(source_id)
        if not details and not file_path:
            raise ValueError(f"Source {source_id} not registered and no path provided.")

        raw_path = Path(file_path if file_path else details["raw_path"])
        if not raw_path.exists():
            raise FileNotFoundError(f"Source file not found at: {raw_path}")

        # Step 1: Indic OCR & Preprocessing (or use existing if not forcing)
        ocr_results = self.ocr_engine.process_document(raw_path, source_id=source_id)
        
        # Check if officer made manual text corrections
        details_updated = get_source_details(source_id)
        ocr_pages = details_updated.get("ocr_pages", []) if details_updated else []
        
        text_chunks = []
        for page in ocr_pages:
            corrected = page.get("full_text_corrected")
            if corrected and corrected.strip():
                text_chunks.append(corrected)
            else:
                text_chunks.append(page.get("full_text", ""))

        combined_text = "\n\n".join(text_chunks) if text_chunks else "\n\n".join([page["full_text"] for page in ocr_results])

        # Step 2: Tamil Entity Extraction & Geography Validation
        entities = self.extractor.extract_entities(combined_text, source_id=source_id)

        # Step 3: Rule-Based / Ollama Classification
        classification = self.classifier.classify(combined_text, source_id=source_id)
        department = classification["department"]

        # Step 4: Jinja2 Anti-Hallucination Grounded Draft Generation
        draft = self.drafter.render_draft(
            source_id=source_id,
            department=department,
            extracted_entities=entities,
        )

        log_audit(
            source_id=source_id,
            action="PIPELINE_COMPLETE",
            officer_id="SYSTEM_ORCHESTRATOR",
            details=f"Pipeline completed. Status: draft_ready, Dept: {department}, Hallucination Score: {draft.get('hallucination_score')}",
        )

        return {
            "source_id": source_id,
            "status": "draft_ready",
            "ocr_results": ocr_results,
            "entities": entities,
            "classification": classification,
            "draft": draft,
        }

    def reprocess_from_corrected_ocr(
        self,
        source_id: str,
        page_number: int,
        corrected_text: str,
        officer_id: str,
    ) -> Dict[str, Any]:
        """Save officer OCR corrections and re-run extraction, classification, and grounded drafting."""
        logger.info(f"Officer {officer_id} submitted OCR correction for {source_id} (Page {page_number})")
        
        # Persist correction
        save_ocr_correction(
            source_id=source_id,
            page_number=page_number,
            corrected_text=corrected_text,
            officer_id=officer_id,
        )

        log_audit(
            source_id=source_id,
            action="OFFICER_CORRECTED_OCR",
            officer_id=officer_id,
            details=f"Updated Page {page_number} text ({len(corrected_text)} chars)",
        )

        # Re-run extraction & drafting on corrected text
        entities = self.extractor.extract_entities(corrected_text, source_id=source_id)
        classification = self.classifier.classify(corrected_text, source_id=source_id)
        department = classification["department"]

        draft = self.drafter.render_draft(
            source_id=source_id,
            department=department,
            extracted_entities=entities,
        )

        log_audit(
            source_id=source_id,
            action="OFFICER_REGENERATED_DRAFT",
            officer_id=officer_id,
            details=f"Re-extracted entities and rendered draft from corrected OCR text",
        )

        return {
            "source_id": source_id,
            "status": "draft_ready",
            "entities": entities,
            "classification": classification,
            "draft": draft,
        }
