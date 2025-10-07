#!/usr/bin/env python3
"""Relevance analysis module based on keyword counts."""

import argparse
from pathlib import Path
import csv

TXT_DIR = Path("txt")
META_DIR = Path("metadata")
META_DIR.mkdir(exist_ok=True, parents=True)


def count_keywords(text: str, keywords: list[str]) -> dict[str, int]:
    """Count occurrences of keywords in text (case-insensitive)."""
    counts = {}
    low = text.lower()
    for kw in keywords:
        c = low.count(kw.lower())
        counts[kw] = c
    return counts


def analyze_relevance(keywords: list[str]) -> list[dict]:
    """Analyze relevance of all text files based on keyword counts."""
    rows = []
    txt_files = list(TXT_DIR.glob("*.txt"))
    
    for f in txt_files:
        text = f.read_text(encoding="utf-8", errors="ignore")
        counts = count_keywords(text, keywords)
        total_hits = sum(counts.values())
        rows.append({
            "doc": f.name,
            "total_hits": total_hits,
            **counts
        })
    
    # Sort by total_hits desc
    rows.sort(key=lambda r: r["total_hits"], reverse=True)
    return rows


def save_relevance_report(rows: list[dict], keywords: list[str]) -> Path:
    """Save relevance analysis to CSV file."""
    out_file = META_DIR / "relevance_report.csv"
    with out_file.open("w", newline="", encoding="utf-8") as csvfile:
        fieldnames = ["doc", "total_hits"] + keywords
        w = csv.DictWriter(csvfile, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return out_file


def print_relevance_summary(rows: list[dict], top_n: int = 5):
    """Print summary of top relevant documents."""
    print(f"Top {top_n}:")
    for r in rows[:top_n]:
        print(f"{r['doc']}: {r['total_hits']} hits")


def generate_relevance_report(keywords_str: str = "reconstruction,super-resolution,gappy,POD,uncertainty"):
    """Generate complete relevance report."""
    keywords = [k.strip() for k in keywords_str.split(",") if k.strip()]
    rows = analyze_relevance(keywords)
    out_file = save_relevance_report(rows, keywords)
    
    print(f"Report geschrieben: {out_file}")
    print_relevance_summary(rows)
    
    return rows, out_file