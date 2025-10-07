#!/usr/bin/env python3
"""Duplicate detection module."""

import hashlib
import os
from pathlib import Path
from rapidfuzz import fuzz, process

RAW_DIRS_ENV = os.getenv("RAW_DIRS")
if RAW_DIRS_ENV:
    RAW_DIRS = [Path(p).expanduser() for p in RAW_DIRS_ENV.split(os.pathsep) if p.strip()]
else:
    RAW_DIRS = [Path("raw")]

THRESH = int(os.getenv("DUPLICATE_NAME_THRESHOLD", "90"))


def file_hash(path: Path, max_bytes: int = 200_000) -> str | None:
    """
    Generate SHA256 hash from first portion of file for duplicate detection.
    
    Args:
        path: Path to the file to hash
        max_bytes: Maximum bytes to read from file start (default: 200KB)
        
    Returns:
        Hexadecimal hash string, or None if file cannot be read
        
    Note:
        Only reads first 200KB for performance - sufficient for duplicate detection
        of PDFs which typically have identical headers if they're the same file.
    """
    h = hashlib.sha256()
    try:
        with path.open("rb") as f:
            chunk = f.read(max_bytes)
            h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def iter_pdfs() -> list[Path]:
    """Get all PDF files from raw directories."""
    pdfs: list[Path] = []
    for base in RAW_DIRS:
        if not base.exists():
            continue
        pdfs.extend(sorted(p for p in base.rglob("*.pdf") if p.is_file()))
    return pdfs


def find_duplicate_hashes(files: list[Path]) -> dict[str, list[str]]:
    """Find files with identical content hashes."""
    hashes: dict[str | None, list[str]] = {}
    for p in files:
        h = file_hash(p)
        hashes.setdefault(h, []).append(p.name)
    
    return {k: v for k, v in hashes.items() if k and len(v) > 1}


def find_similar_names(names: list[str], threshold: int = THRESH) -> list[tuple[int, str, str]]:
    """Find files with similar names (potential duplicates/typos)."""
    similar_pairs = []
    reported: set[tuple[str, str]] = set()
    
    for name in names:
        matches = process.extract(name, names, scorer=fuzz.token_sort_ratio, limit=5)
        for cand, score, _ in matches:
            if cand == name or score < threshold:
                continue
            pair = tuple(sorted([name, cand]))
            if pair in reported:
                continue
            reported.add(pair)
            similar_pairs.append((score, pair[0], pair[1]))
    
    return sorted(similar_pairs, key=lambda x: x[0], reverse=True)


def scan_duplicates():
    """
    Comprehensive duplicate detection for PDF files.
    
    Performs two types of duplicate detection:
    1. Content-based: Files with identical hashes (same content)
    2. Name-based: Files with similar names (potential typos/duplicates)
    
    Returns:
        Dictionary with:
        - total_files: Number of PDF files found
        - duplicate_hashes: Dict mapping hash -> list of duplicate filenames  
        - similar_names: List of (score, name1, name2) tuples
        
    Example:
        >>> result = scan_duplicates()
        >>> print(f"Found {len(result['duplicate_hashes'])} hash duplicate groups")
        >>> print(f"Found {len(result['similar_names'])} similar name pairs")
    """
    files = iter_pdfs()
    if not files:
        print("Keine PDFs gefunden. Setze RAW_DIRS oder lege Dateien unter 'raw/' ab.")
        return
    
    names = [p.name for p in files]
    print(f"Gefundene PDFs: {len(files)}")

    # Check for identical hashes
    dup_hash = find_duplicate_hashes(files)
    if dup_hash:
        print("\n[Identische Inhalte (gleicher Hash)]")
        for h, group in dup_hash.items():
            print(f"- {h[:10]}: {group}")

    # Check for similar names
    print("\n[Ähnliche Dateinamen (potentielle Duplikate / Tippfehler)]")
    similar_pairs = find_similar_names(names)
    for score, name1, name2 in similar_pairs:
        print(f"{score:>3}% :: {name1}  <>  {name2}")
    
    print(f"\nHinweis: Prüfe Paare >= {THRESH}%. Entferne Tippfehler-Versionen oder vereinheitliche Schreibweise.")
    
    return {
        'total_files': len(files),
        'duplicate_hashes': dup_hash,
        'similar_names': similar_pairs
    }