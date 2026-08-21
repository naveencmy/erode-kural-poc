"""Document Summarization and Dynamic Prompt Suggestions Module (Module 1).

Zero hardcoded data:
- Deterministic + AI content extraction and structure profiling
- Content Fingerprinting via local Qwen 2.5 7B
- Dynamic Context-Aware Prompt Suggestions with Grounding Verification
- Anti-Hallucination Barrier and Personalization Layer
- Structured Multi-Type Document Summaries with Page-Level Citations
"""

from modules.document_summary.extractor import ContentExtractor, detect_file_type
from modules.document_summary.fingerprinter import ContentFingerprinter
from modules.document_summary.suggestion_engine import DynamicSuggestionEngine
from modules.document_summary.hallucination_barrier import SuggestionHallucinationBarrier
from modules.document_summary.summarizer import DocumentSummarizer

__all__ = [
    "ContentExtractor",
    "detect_file_type",
    "ContentFingerprinter",
    "DynamicSuggestionEngine",
    "SuggestionHallucinationBarrier",
    "DocumentSummarizer",
]
