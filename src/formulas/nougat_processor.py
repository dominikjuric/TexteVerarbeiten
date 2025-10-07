"""
Nougat OCR Integration for Scientific PDF Processing

This module provides Nougat integration for processing scientific PDFs with
mathematical formulas, tables, and complex layouts. Nougat converts PDFs to
structured Markdown with LaTeX formulas.
"""

import logging
import os
import time
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import subprocess
import shutil
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

# Model constants
NOUGAT_MODEL_SMALL = "0.1.0-small"
NOUGAT_MODEL_BASE = "0.1.0-base"

# Use CLI-only approach to avoid import conflicts
NOUGAT_AVAILABLE = False  # Python API disabled due to naming conflicts
NougatModel: Optional[Any] = None

# Configuration
RAW_DIRS = [Path("raw/Paper"), Path("raw/Bücher"), Path("raw")]
NOUGAT_OUTPUT_DIR = Path("processed/nougat_md")
NOUGAT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@lru_cache(maxsize=1)
def _resolve_nougat_cli() -> Optional[str]:
    """Return the preferred nougat CLI path, if any."""
    candidates = []

    env_cli = os.getenv("NOUGAT_CLI")
    if env_cli:
        candidates.append(Path(env_cli).expanduser())

    candidates.append(PROJECT_ROOT / ".venv" / "bin" / "nougat")
    candidates.append(PROJECT_ROOT / "venv" / "bin" / "nougat")

    which_cli = shutil.which("nougat")
    if which_cli:
        candidates.append(Path(which_cli))

    for cand in candidates:
        if cand and cand.exists():
            return str(cand)
    return None


def _build_cli_command(pdf: Path, output_dir: Path, model_name: Optional[str] = None,
                        pages: Optional[str] = None) -> Optional[list[str]]:
    cli_path = _resolve_nougat_cli()
    if not cli_path:
        return None

    cmd = [cli_path, str(pdf), "--out", str(output_dir)]

    if model_name and model_name != NOUGAT_MODEL_SMALL:
        cmd.extend(['--model', model_name])

    if pages:
        cmd.extend(['--pages', pages])

    return cmd

def check_nougat_cli() -> bool:
    """Check if nougat CLI is available."""
    cli_path = _resolve_nougat_cli()
    if not cli_path:
        return False
    try:
        result = subprocess.run([cli_path, '--help'],
                               capture_output=True, text=True, timeout=10)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def run_nougat_single(pdf: Path) -> Tuple[str, bool, str]:
    """Run Nougat OCR on a single PDF file using CLI."""
    # Nougat schreibt je nach Version .mmd (Math-Markdown) oder .md
    out_mmd = NOUGAT_OUTPUT_DIR / (pdf.stem + ".mmd")
    out_md = NOUGAT_OUTPUT_DIR / (pdf.stem + ".md")
    if out_mmd.exists() or out_md.exists():
        return (pdf.name, True, "skip (exists)")

    # Bevorzuge MPS (Apple GPU) – Fallback auf CPU erlauben
    env = {
        **os.environ,
        "PYTORCH_ENABLE_MPS_FALLBACK": "1",
        # optional: weniger Tokenizer-Warnungen
        "TOKENIZERS_PARALLELISM": "false",
    }
    cmd = _build_cli_command(pdf, NOUGAT_OUTPUT_DIR)
    if not cmd:
        return (pdf.name, False, "nougat CLI not found")
    try:
        res = subprocess.run(
            cmd, capture_output=True, text=True, check=True, env=env, timeout=900
        )
        msg = (res.stderr or res.stdout or "ok").strip()
        return (pdf.name, True, msg)
    except subprocess.TimeoutExpired as e:
        return (pdf.name, False, f"timeout after {e.timeout}s")
    except subprocess.CalledProcessError as e:
        msg = (e.stderr or e.stdout or str(e))[-500:]
        return (pdf.name, False, msg)
    except Exception as e:
        return (pdf.name, False, str(e))


def get_pdf_files() -> list[Path]:
    """Get all PDF files from raw directories."""
    pdfs = []
    for d in RAW_DIRS:
        if d.exists():
            pdfs.extend(sorted(p for p in d.rglob("*.pdf") if p.is_file()))
    return pdfs


def process_nougat_batch(max_workers: int = 2) -> dict:
    """Process all PDFs with Nougat OCR in batch mode."""
    pdfs = get_pdf_files()
    print(f"Nougat Batch: {len(pdfs)} PDFs")

    if not check_nougat_cli():
        print("❌ Nougat CLI not available.")
        return {
            'total': len(pdfs),
            'success': 0,
            'failed': len(pdfs),
            'errors': [(str(p), 'nougat CLI not found') for p in pdfs],
            'output_dir': NOUGAT_OUTPUT_DIR
        }

    ok = 0
    fail = 0
    errors = []

    # M1: 1–2 Threads sind sinnvoll; nougat CLI startet intern eigene Prozesse
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(run_nougat_single, p): p for p in pdfs}
        for fut in as_completed(futures):
            name, success, msg = fut.result()
            if success:
                ok += 1
                print(f"[OK ] {name}")
            else:
                fail += 1
                last_line = (msg.splitlines()[-1] if msg else "").strip()
                print(f"[ERR] {name} :: {last_line}")
                errors.append((name, msg))

    print(f"Fertig: {ok} OK, {fail} Fehler. Output: {NOUGAT_OUTPUT_DIR}")
    if errors:
        error_log = NOUGAT_OUTPUT_DIR / "_errors.log"
        error_log.write_text(
            "\n\n".join([f"{n}\n{m}" for n, m in errors]), encoding="utf-8"
        )
        print(f"Details: {error_log}")
    
    return {
        'total': len(pdfs),
        'success': ok,
        'failed': fail,
        'errors': errors,
        'output_dir': NOUGAT_OUTPUT_DIR
    }


class NougatProcessor:
    """
    Modern Nougat OCR processor for scientific PDFs.
    
    This processor uses the Nougat model to convert scientific PDFs containing
    mathematical formulas, tables, and complex layouts into structured Markdown
    with LaTeX math notation.
    """
    
    def __init__(self, model_name: str = NOUGAT_MODEL_SMALL, device: str = "auto"):
        """
        Initialize Nougat processor.
        
        Args:
            model_name: Nougat model version (NOUGAT_MODEL_SMALL, NOUGAT_MODEL_BASE) 
            device: Device to use ("auto", "cpu", "mps", "cuda")
        """
        self.model_name = model_name
        self.device = self._select_device(device)
        self.model = None
        self.use_cli = check_nougat_cli()
        
        logger.info(f"🧠 Nougat processor: model={model_name}, device={self.device}, cli_available={self.use_cli}")
    
    def _select_device(self, device: str) -> str:
        """Select appropriate device for processing."""
        if device == "auto":
            # For M1/M2 Macs, prefer MPS if available
            import platform
            if platform.system() == "Darwin":
                try:
                    import torch
                    if torch.backends.mps.is_available():
                        return "mps"
                except ImportError:
                    pass
            return "cpu"
        return device
    
    def process_pdf(self, pdf_path: Path, output_dir: Optional[Path] = None, pages: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a PDF with Nougat OCR using CLI approach.
        
        Args:
            pdf_path: Path to the PDF file
            output_dir: Optional output directory for markdown files
            pages: Optional page range string for faster tests, e.g. "1-5,8"
            
        Returns:
            Dictionary with processing results
        """
        start_time = time.time()
        
        if not pdf_path.exists():
            return {
                'success': False,
                'error': f"PDF file not found: {pdf_path}",
                'processing_time': time.time() - start_time
            }
        
        # Set up output directory
        if output_dir is None:
            output_dir = NOUGAT_OUTPUT_DIR
        else:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
        
        # Check if already processed
        out_mmd = output_dir / f"{pdf_path.stem}.mmd"
        out_md = output_dir / f"{pdf_path.stem}.md"
        
        if out_mmd.exists():
            markdown_content = out_mmd.read_text(encoding='utf-8')
            return {
                'success': True,
                'markdown': markdown_content,
                'output_path': out_mmd,
                'processing_time': time.time() - start_time,
                'metadata': {'method': 'cached', 'file_type': 'mmd'}
            }
        elif out_md.exists():
            markdown_content = out_md.read_text(encoding='utf-8')
            return {
                'success': True,
                'markdown': markdown_content,
                'output_path': out_md,
                'processing_time': time.time() - start_time,
                'metadata': {'method': 'cached', 'file_type': 'md'}
            }
        
        # Process with CLI
        if self.use_cli:
            return self._process_with_cli(pdf_path, output_dir, start_time, pages=pages)
        else:
            return {
                'success': False,
                'error': "Nougat CLI not available",
                'processing_time': time.time() - start_time
            }
    
    def _process_with_cli(self, pdf_path: Path, output_dir: Path, start_time: float, pages: Optional[str] = None) -> Dict[str, Any]:
        """Process using Nougat CLI."""
        logger.info(f"🔬 Processing {pdf_path.name} with Nougat CLI...")
        
        # Set up environment for M1 optimization
        env = {
            **os.environ,
            "PYTORCH_ENABLE_MPS_FALLBACK": "1",
            "TOKENIZERS_PARALLELISM": "false",
        }
        
        cmd = _build_cli_command(pdf_path, output_dir, model_name=self.model_name, pages=pages)
        if not cmd:
            return {
                'success': False,
                'error': 'Nougat CLI not available',
                'processing_time': time.time() - start_time
            }

        try:
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=900,  # 15 minute timeout
                env=env
            )
            
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout or "Unknown error"
                logger.error(f"Nougat CLI failed: {error_msg}")
                return {
                    'success': False,
                    'error': f"Nougat CLI error: {error_msg}",
                    'processing_time': time.time() - start_time
                }
            
            # Find output file
            out_mmd = output_dir / f"{pdf_path.stem}.mmd"
            out_md = output_dir / f"{pdf_path.stem}.md"
            
            output_file = None
            if out_mmd.exists():
                output_file = out_mmd
            elif out_md.exists():
                output_file = out_md
            else:
                return {
                    'success': False,
                    'error': "No markdown output file found",
                    'processing_time': time.time() - start_time
                }
            
            # Read the markdown content
            markdown_content = output_file.read_text(encoding='utf-8')
            
            logger.info(f"💾 Nougat output saved to: {output_file}")
            
            return {
                'success': True,
                'markdown': markdown_content,
                'output_path': output_file,
                'processing_time': time.time() - start_time,
                'metadata': {
                    'method': 'cli',
                    'model': self.model_name,
                    'device': self.device,
                    'file_type': output_file.suffix[1:]  # .mmd -> mmd
                }
            }
            
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': "Nougat processing timed out (15 minutes)",
                'processing_time': time.time() - start_time
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'processing_time': time.time() - start_time
            }
    
    def is_available(self) -> bool:
        """Check if Nougat processing is available."""
        return self.use_cli
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the processor."""
        return {
            'model_name': self.model_name,
            'device': self.device,
            'cli_available': self.use_cli,
            'processing_method': 'cli' if self.use_cli else 'none'
        }


def create_nougat_processor(model_name: str = NOUGAT_MODEL_SMALL) -> Optional[NougatProcessor]:
    """
    Factory function to create a Nougat processor.
    
    Args:
        model_name: Model version to use
        
    Returns:
        NougatProcessor instance or None if not available
    """
    try:
        processor = NougatProcessor(model_name=model_name)
        if processor.is_available():
            return processor
        else:
            logger.error("❌ Nougat processor not available")
            return None
    except Exception as e:
        logger.error(f"❌ Failed to create Nougat processor: {e}")
        return None


def process_pdf_with_nougat(pdf_path: Path, output_dir: Optional[Path] = None, 
                           model_name: str = NOUGAT_MODEL_SMALL) -> Dict[str, Any]:
    """
    Convenience function to process a single PDF with Nougat.
    
    Args:
        pdf_path: Path to PDF file
        output_dir: Optional output directory
        model_name: Nougat model version
        
    Returns:
        Processing result dictionary
    """
    processor = create_nougat_processor(model_name)
    if processor:
        return processor.process_pdf(pdf_path, output_dir)
    else:
        return {
            'success': False,
            'error': 'Nougat processor not available',
            'processing_time': 0.0
        }


if __name__ == "__main__":
    """Test Nougat integration."""
    
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    print("🧠 Testing Nougat OCR Integration")
    print("=" * 40)
    
    # Test CLI availability
    cli_available = check_nougat_cli()
    print(f"🔧 Nougat CLI available: {cli_available}")
    
    if cli_available:
        # Test processor creation
        processor = create_nougat_processor()
        if processor:
            print("✅ Nougat processor created successfully")
            
            # Show model info
            info = processor.get_model_info()
            print(f"📊 Model: {info['model_name']}")
            print(f"💻 Device: {info['device']}")
            print(f"🔧 Method: {info['processing_method']}")
            
            # Test with a PDF if available
            test_pdfs = get_pdf_files()
            if test_pdfs:
                test_pdf = test_pdfs[0]
                print(f"\n🧪 Testing with: {test_pdf.name}")
                
                # Process PDF
                result = processor.process_pdf(test_pdf)
                
                if result['success']:
                    print("✅ Processing successful!")
                    print(f"⏱️ Time: {result['processing_time']:.2f}s")
                    if result.get('output_path'):
                        print(f"💾 Output: {result['output_path']}")
                        print(f"📝 Content length: {len(result['markdown'])} characters")
                        
                        # Show first few lines
                        lines = result['markdown'].split('\n')[:5]
                        print("📖 Preview:")
                        for line in lines:
                            print(f"   {line}")
                else:
                    print(f"❌ Processing failed: {result.get('error', 'Unknown error')}")
            else:
                print("ℹ️ No test PDFs found")
                print("📁 Checked directories:", [str(d) for d in RAW_DIRS])
        else:
            print("❌ Could not create Nougat processor")
    else:
        print("❌ Nougat CLI not available")
        print("\nTo install Nougat:")
        print("  pip install nougat-ocr")
        print("\nThen test with:")
        print("  nougat --help")