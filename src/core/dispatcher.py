"""
Intelligent PDF Processing Dispatcher

This module implements the intelligent dispatcher described in the hybrid architecture:
- Routes PDFs to appropriate processing engines based on content and tags
- Supports local processing (PyMuPDF, Tesseract) and planned cloud services
- Handles the /to_process -> /processed workflow with Zotero integration
"""

import io
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

# Local imports
from ..config import CFG

try:
    from .zotero_client import ZoteroClient, create_zotero_client
    from ..pipeline.extract import extract_pdf  # This is the correct function name
    ZOTERO_AVAILABLE = True
except ImportError:
    ZoteroClient = None  # type: ignore
    create_zotero_client = None  # type: ignore
    extract_pdf = None  # type: ignore
    ZOTERO_AVAILABLE = False

logger = logging.getLogger(__name__)

# Constants
ERROR_NO_ENGINE_AVAILABLE = "No processing engine available"


class ProcessingEngine(Enum):
    """Available PDF processing engines."""
    PYMUPDF = "pymupdf"      # Fast text extraction for text-based PDFs
    TESSERACT = "tesseract"   # OCR for scanned documents
    NOUGAT = "nougat"        # Scientific papers with formulas (local)
    MATHPIX = "mathpix"      # Scientific papers with formulas (cloud)


@dataclass
class ProcessingResult:
    """Result of PDF processing."""
    success: bool
    text: str
    engine_used: ProcessingEngine
    metadata: Dict[str, Any]
    error_message: Optional[str] = None
    processing_time: float = 0.0


@dataclass 
class DocumentRoute:
    """Routing decision for a document."""
    engine: ProcessingEngine
    confidence: float
    reason: str


class PDFDispatcher:
    """
    Intelligent dispatcher that routes PDFs to appropriate processing engines.
    
    Routing Logic:
    1. Try PyMuPDF first (fastest for text-based PDFs)
    2. Check Zotero tags for routing hints (#scientific, #math_heavy, etc.)
    3. Fall back to appropriate OCR engine
    4. Always run table extraction separately
    """
    
    def __init__(self, zotero_client = None):
        """
        Initialize the dispatcher.
        
        Args:
            zotero_client: Optional Zotero client for tag-based routing
        """
        if zotero_client is None and create_zotero_client is not None:
            try:
                self.zotero_client = create_zotero_client()
            except Exception as e:
                logger.warning(f"Could not create Zotero client: {e}")
                self.zotero_client = None
        else:
            self.zotero_client = zotero_client
        
        # Tag-based routing rules
        self.scientific_tags = {
            '#scientific', '#math_heavy', '#journal_article', 
            '#formulas', '#equations', '#latex', '#research_paper'
        }
        
        # Processing engine availability
        self.engines_available = {
            ProcessingEngine.PYMUPDF: self._check_pymupdf_available(),
            ProcessingEngine.TESSERACT: self._check_tesseract_available(),
            ProcessingEngine.NOUGAT: self._check_nougat_available(),
            ProcessingEngine.MATHPIX: self._check_mathpix_available()
        }
        
        logger.info(f"📊 Available engines: {[e.value for e, available in self.engines_available.items() if available]}")
    
    def _check_pymupdf_available(self) -> bool:
        """Check if PyMuPDF is available."""
        try:
            import importlib.util
            return importlib.util.find_spec("fitz") is not None
        except ImportError:
            return False
    
    def _check_tesseract_available(self) -> bool:
        """Check if Tesseract OCR is available."""
        try:
            import importlib.util
            if importlib.util.find_spec("pytesseract") is None or importlib.util.find_spec("PIL") is None:
                return False
            # Try to get version to ensure it's properly installed
            import pytesseract
            pytesseract.get_tesseract_version()
            return True
        except (ImportError, OSError):
            return False
    
    def _check_nougat_available(self) -> bool:
        """Check if Nougat CLI-based processing is available."""
        try:
            from ..formulas.nougat_processor import check_nougat_cli
            return check_nougat_cli()
        except Exception:
            return False
    
    def _check_mathpix_available(self) -> bool:
        """Check if Mathpix API is configured."""
        mathpix_cfg = CFG.get("services", {}).get("mathpix", {})
        return bool(mathpix_cfg.get("app_key"))
    
    def analyze_document(self, pdf_path: Path, zotero_item_key: Optional[str] = None) -> DocumentRoute:
        """
        Analyze a document and determine the best processing route.
        
        Args:
            pdf_path: Path to the PDF file
            zotero_item_key: Optional Zotero item key for tag analysis
            
        Returns:
            DocumentRoute with engine recommendation and reasoning
        """
        
        # Step 1: Try PyMuPDF first (fastest check)
        pymupdf_route = self._try_pymupdf_extraction(pdf_path)
        if pymupdf_route:
            return pymupdf_route
        
        # Step 2: Check Zotero tags for routing hints
        zotero_route = self._analyze_zotero_tags(zotero_item_key)
        if zotero_route:
            return zotero_route
        
        # Step 3: Fall back to standard OCR
        ocr_route = self._get_fallback_route()
        if ocr_route:
            return ocr_route
        
        # Step 4: Last resort
        return self._get_last_resort_route()
    
    def _try_pymupdf_extraction(self, pdf_path: Path) -> Optional[DocumentRoute]:
        """Try PyMuPDF extraction."""
        if not self.engines_available[ProcessingEngine.PYMUPDF]:
            return None
            
        try:
            if extract_pdf is not None:
                sample_text = extract_pdf(pdf_path)
                if sample_text and len(sample_text.strip()) > 100:
                    return DocumentRoute(
                        engine=ProcessingEngine.PYMUPDF,
                        confidence=0.95,
                        reason="Text-based PDF with sufficient extractable content"
                    )
        except Exception as e:
            logger.debug(f"PyMuPDF extraction failed for {pdf_path}: {e}")
        return None
    
    def _analyze_zotero_tags(self, zotero_item_key: Optional[str]) -> Optional[DocumentRoute]:
        """Analyze Zotero tags for routing hints."""
        if not (self.zotero_client and zotero_item_key):
            return None
            
        try:
            metadata = self.zotero_client.get_item_metadata(zotero_item_key)
            tags = set(metadata.get('tags', []))
            
            # Check for scientific content tags
            if tags.intersection(self.scientific_tags):
                return self._get_scientific_route(tags)
                
        except Exception as e:
            logger.warning(f"Could not analyze Zotero tags for {zotero_item_key}: {e}")
        return None
    
    def _get_scientific_route(self, tags: set) -> Optional[DocumentRoute]:
        """Get route for scientific documents."""
        scientific_tags = tags.intersection(self.scientific_tags)
        
        if self.engines_available[ProcessingEngine.NOUGAT]:
            return DocumentRoute(
                engine=ProcessingEngine.NOUGAT,
                confidence=0.85,
                reason=f"Scientific document with tags: {scientific_tags}"
            )
        elif self.engines_available[ProcessingEngine.MATHPIX]:
            return DocumentRoute(
                engine=ProcessingEngine.MATHPIX,
                confidence=0.80,
                reason=f"Scientific document, using cloud API: {scientific_tags}"
            )
        return None
    
    def _get_fallback_route(self) -> Optional[DocumentRoute]:
        """Get fallback OCR route."""
        if self.engines_available[ProcessingEngine.TESSERACT]:
            return DocumentRoute(
                engine=ProcessingEngine.TESSERACT,
                confidence=0.70,
                reason="Scanned or image-based PDF, using standard OCR"
            )
        return None
    
    def _get_last_resort_route(self) -> DocumentRoute:
        """Get last resort route."""
        for engine, available in self.engines_available.items():
            if available and engine != ProcessingEngine.PYMUPDF:
                return DocumentRoute(
                    engine=engine,
                    confidence=0.50,
                    reason=f"Fallback to {engine.value} (other engines unavailable)"
                )
        
        # No engines available
        return DocumentRoute(
            engine=ProcessingEngine.PYMUPDF,  # Default
            confidence=0.0,
            reason=ERROR_NO_ENGINE_AVAILABLE
        )
    
    def check_nougat_availability(self) -> bool:
        """Check if Nougat processing is available."""
        return self.engines_available.get(ProcessingEngine.NOUGAT, False)
    
    def check_engine_availability(self, engine: ProcessingEngine) -> bool:
        """Check if a specific processing engine is available."""
        return self.engines_available.get(engine, False)
    
    def process_document(self, pdf_path: Path, route: DocumentRoute) -> ProcessingResult:
        """
        Process a document using the specified engine.
        
        Args:
            pdf_path: Path to the PDF file
            route: Routing decision from analyze_document()
            
        Returns:
            ProcessingResult with extracted text and metadata
        """
        import time
        start_time = time.time()
        
        try:
            if route.engine == ProcessingEngine.PYMUPDF:
                return self._process_with_pymupdf(pdf_path, start_time)
            elif route.engine == ProcessingEngine.TESSERACT:
                return self._process_with_tesseract(pdf_path, start_time)
            elif route.engine == ProcessingEngine.NOUGAT:
                return self._process_with_nougat(pdf_path, start_time)
            elif route.engine == ProcessingEngine.MATHPIX:
                return self._process_with_mathpix(pdf_path, start_time)
            else:
                return ProcessingResult(
                    success=False,
                    text="",
                    engine_used=route.engine,
                    metadata={},
                    error_message=f"Engine {route.engine.value} not implemented",
                    processing_time=time.time() - start_time
                )
                
        except Exception as e:
            return ProcessingResult(
                success=False,
                text="",
                engine_used=route.engine,
                metadata={},
                error_message=str(e),
                processing_time=time.time() - start_time
            )
    
    def _process_with_pymupdf(self, pdf_path: Path, start_time: float) -> ProcessingResult:
        """Process with PyMuPDF."""
        if extract_pdf is None:
            raise ImportError("PyMuPDF extraction not available")
        
        text = extract_pdf(pdf_path)
        
        return ProcessingResult(
            success=bool(text.strip()),
            text=text,
            engine_used=ProcessingEngine.PYMUPDF,
            metadata={'pages': 'unknown', 'method': 'text_extraction'},
            processing_time=time.time() - start_time
        )
    
    def _process_with_tesseract(self, pdf_path: Path, start_time: float) -> ProcessingResult:
        """Process with Tesseract OCR."""
        try:
            import pytesseract
            from PIL import Image
            import fitz  # PyMuPDF for image extraction
            
            # Convert PDF pages to images and OCR
            doc = fitz.open(pdf_path)
            full_text = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                pix = page.get_pixmap()
                img_data = pix.tobytes("ppm")
                
                # Convert to PIL Image and OCR
                img = Image.open(io.BytesIO(img_data))
                page_text = pytesseract.image_to_string(img, lang='deu+eng')
                full_text.append(page_text)
            
            doc.close()
            text = "\n\n".join(full_text)
            
            return ProcessingResult(
                success=bool(text.strip()),
                text=text,
                engine_used=ProcessingEngine.TESSERACT,
                metadata={'pages': len(full_text), 'method': 'ocr'},
                processing_time=time.time() - start_time
            )
            
        except ImportError as e:
            raise ImportError(f"Tesseract dependencies not available: {e}")
    
    def _process_with_nougat(self, pdf_path: Path, start_time: float) -> ProcessingResult:
        """Process with Nougat OCR."""
        try:
            from ..formulas.nougat_processor import create_nougat_processor
            
            processor = create_nougat_processor()
            if not processor:
                return ProcessingResult(
                    success=False,
                    text="",
                    engine_used=ProcessingEngine.NOUGAT,
                    metadata={},
                    error_message="Nougat processor not available",
                    processing_time=time.time() - start_time
                )
            
            # Process PDF with Nougat
            result = processor.process_pdf(pdf_path)
            
            if result['success']:
                return ProcessingResult(
                    success=True,
                    text=result['markdown'],
                    engine_used=ProcessingEngine.NOUGAT,
                    metadata=result.get('metadata', {}),
                    processing_time=time.time() - start_time
                )
            else:
                return ProcessingResult(
                    success=False,
                    text="",
                    engine_used=ProcessingEngine.NOUGAT,
                    metadata={},
                    error_message=result.get('error', 'Unknown Nougat error'),
                    processing_time=time.time() - start_time
                )
                
        except ImportError as e:
            return ProcessingResult(
                success=False,
                text="",
                engine_used=ProcessingEngine.NOUGAT,
                metadata={},
                error_message=f"Nougat dependencies not available: {e}",
                processing_time=time.time() - start_time
            )
    
    def _process_with_mathpix(self, pdf_path: Path, start_time: float) -> ProcessingResult:
        """Process with Mathpix API (not implemented - use Nougat instead)."""
        _ = pdf_path  # Unused but keep for API consistency
        return ProcessingResult(
            success=False,
            text="",
            engine_used=ProcessingEngine.MATHPIX,
            metadata={},
            error_message="Mathpix API not implemented - use Nougat instead",
            processing_time=time.time() - start_time
        )
    
    def process_zotero_queue(self, max_items: int = 10) -> List[Tuple[str, ProcessingResult]]:
        """
        Process items from the Zotero /to_process queue.
        
        Args:
            max_items: Maximum number of items to process
            
        Returns:
            List of (item_key, ProcessingResult) tuples
        """
        if not self.zotero_client:
            logger.error("No Zotero client available")
            return []
        
        # Get items to process
        items = self.zotero_client.get_items_to_process(limit=max_items)
        if not items:
            logger.info("No items found with /to_process tag")
            return []
        
        logger.info(f"📋 Processing {len(items)} items from Zotero queue")
        results = []
        
        for item in items:
            item_key = item['key']
            try:
                # Get PDF attachments
                pdfs = self.zotero_client.get_pdf_attachments(item_key)
                
                if not pdfs:
                    logger.warning(f"No PDF attachments found for item {item_key}")
                    self.zotero_client.mark_as_error(item_key, "No PDF attachments found")
                    continue
                
                # Process first PDF (could be extended for multiple PDFs)
                pdf_attachment = pdfs[0]
                
                # Download PDF to temp location
                temp_dir = Path("tmp_processing")
                temp_dir.mkdir(exist_ok=True)
                
                pdf_path = self.zotero_client.download_pdf(pdf_attachment['key'], temp_dir)
                if not pdf_path:
                    self.zotero_client.mark_as_error(item_key, "Failed to download PDF")
                    continue
                
                # Analyze and process
                route = self.analyze_document(pdf_path, item_key)
                logger.info(f"📄 {pdf_path.name}: {route.reason} -> {route.engine.value}")
                
                result = self.process_document(pdf_path, route)
                
                if result.success:
                    # Mark as processed in Zotero
                    self.zotero_client.mark_as_processed(item_key)
                    logger.info(f"✅ Successfully processed {item_key}")
                else:
                    # Mark as error in Zotero
                    self.zotero_client.mark_as_error(item_key, result.error_message)
                    logger.error(f"❌ Failed to process {item_key}: {result.error_message}")
                
                results.append((item_key, result))
                
                # Clean up temp file
                try:
                    pdf_path.unlink()
                except Exception:
                    pass
                
            except Exception as e:
                logger.error(f"❌ Error processing item {item_key}: {e}")
                self.zotero_client.mark_as_error(item_key, str(e))
        
        return results


def create_dispatcher() -> Optional[PDFDispatcher]:
    """
    Factory function to create a PDF dispatcher with Zotero integration.
    
    Returns:
        PDFDispatcher instance or None if setup failed
    """
    try:
        return PDFDispatcher()
    except Exception as e:
        logger.error(f"Failed to create PDF dispatcher: {e}")
        return None


if __name__ == "__main__":
    """Test the dispatcher setup."""
    
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    # Test dispatcher creation
    dispatcher = create_dispatcher()
    if dispatcher:
        print("✅ PDF Dispatcher created successfully")
        
        # Show available engines
        available = [e.value for e, avail in dispatcher.engines_available.items() if avail]
        print(f"📊 Available engines: {available}")
        
        if dispatcher.zotero_client:
            print("✅ Zotero integration enabled")
            
            # Test queue processing (dry run)
            try:
                items = dispatcher.zotero_client.get_items_to_process(limit=1)
                print(f"📋 Found {len(items)} items in processing queue")
            except Exception as e:
                print(f"⚠️ Could not access Zotero queue: {e}")
        else:
            print("⚠️ Zotero integration not available")
            print("   Set ZOTERO_USER_ID and ZOTERO_API_KEY environment variables")
    else:
        print("❌ Failed to create PDF dispatcher")