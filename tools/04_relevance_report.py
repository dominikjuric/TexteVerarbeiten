#!/usr/bin/env python3
import argparse
from pathlib import Path
import csv

TXT_DIR = Path("txt")
META_DIR = Path("metadata")
META_DIR.mkdir(exist_ok=True, parents=True)

def count_keywords(text, keywords):
    counts = {}
    low = text.lower()
    for kw in keywords:
        c = low.count(kw.lower())
        counts[kw] = c
    return counts

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keywords", type=str, default="reconstruction,super-resolution,gappy,POD,uncertainty")
    args = ap.parse_args()
    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
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
    # sort by total_hits desc
    rows.sort(key=lambda r: r["total_hits"], reverse=True)
    out_file = META_DIR / "relevance_report.csv"
    with out_file.open("w", newline="", encoding="utf-8") as csvfile:
        fieldnames = ["doc","total_hits"] + keywords
        w = csv.DictWriter(csvfile, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"Report geschrieben: {out_file}")
    print("Top 5:")
    for r in rows[:5]:
        print(r["doc"], r["total_hits"])

if __name__ == "__main__":
    main()