import os
import json
import hashlib
from pathlib import Path
from typing import List, Dict
import subprocess
import uuid

# Placeholder imports – implement konkret
# from unstructured.partition.pdf import partition_pdf
# from qdrant_client import QdrantClient
# from sentence_transformers import SentenceTransformer

CONFIG_PATH = "config.json"

def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)

def ensure_dirs(cfg):
    for d in cfg["directories"].values():
        Path(d).mkdir(parents=True, exist_ok=True)

def ocr_pdf(input_path: Path, output_path: Path):
    if output_path.exists():
        return
    cmd = [
        "ocrmypdf",
        "--optimize", "3",
        "--skip-text",
        "--language", "deu+eng",
        str(input_path),
        str(output_path)
    ]
    subprocess.run(cmd, check=True)

def hash_text(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()[:12]

def parse_pdf(path: Path) -> List[Dict]:
    # blocks = partition_pdf(filename=str(path))  # uncomment real call
    # Fake structure for skeleton
    return [
        {"type": "title", "text": "Dummy Title", "page": 1},
        {"type": "paragraph", "text": "Some paragraph with formula FORMULA_[abc123].", "page": 1}
    ]

def extract_formulas(parsed_blocks: List[Dict]) -> List[Dict]:
    # Placeholder: in real usage integrate Nougat or Mathpix API
    formulas = []
    for b in parsed_blocks:
        # Detect markers or LaTeX
        # Append stub
        pass
    return formulas

def chunk_blocks(blocks: List[Dict], max_chars=1200) -> List[Dict]:
    chunks = []
    current = []
    length = 0
    for b in blocks:
        t = b["text"]
        if length + len(t) > max_chars and current:
            chunks.append({"id": str(uuid.uuid4()), "text": "\n".join(x["text"] for x in current), "page_span": list({x["page"] for x in current})})
            current = []
            length = 0
        current.append(b)
        length += len(t)
    if current:
        chunks.append({"id": str(uuid.uuid4()), "text": "\n".join(x["text"] for x in current), "page_span": list({x["page"] for x in current})})
    return chunks

def build_bm25_index(chunks: List[Dict], index_dir: Path):
    # Implement Whoosh or elastic call
    pass

def build_vector_index(chunks: List[Dict], cfg):
    # model = SentenceTransformer(cfg["embeddings"]["model"])
    # qdrant = QdrantClient(url=cfg["vector_store"]["url"])
    # for c in chunks: embed = model.encode(c["text"])
    pass

def generate_relevance_report(chunks: List[Dict], report_path: Path):
    # Placeholder
    header = "chunk_id\tpages\tpreview\n"
    with open(report_path, "w") as f:
        f.write(header)
        for c in chunks[:10]:
            f.write(f"{c['id']}\t{c['page_span']}\t{c['text'][:80].replace('\n',' ')}\n")

def main():
    cfg = load_config()
    ensure_dirs(cfg)
    raw_dir = Path(cfg["directories"]["raw"])
    ocr_dir = Path(cfg["directories"]["ocr"])
    parsed_dir = Path(cfg["directories"]["parsed"])
    chunk_dir = Path(cfg["directories"]["chunks"])
    report_dir = Path(cfg["directories"]["reports"])
    report_dir.mkdir(exist_ok=True, parents=True)

    pdf_files = list(raw_dir.glob("*.pdf"))
    print(f"Found {len(pdf_files)} PDFs")

    all_chunks = []
    for pdf in pdf_files:
        ocr_out = ocr_dir / pdf.name
        if cfg["pipeline"]["ocr"]:
            ocr_pdf(pdf, ocr_out)
            parse_target = ocr_out
        else:
            parse_target = pdf
        blocks = parse_pdf(parse_target)
        chunks = chunk_blocks(blocks)
        for c in chunks:
            c["doc_id"] = pdf.name
        all_chunks.extend(chunks)

    # Index
    if cfg["pipeline"]["bm25"]:
        build_bm25_index(all_chunks, Path(cfg["directories"]["indexes"]) / "bm25")
    if cfg["pipeline"]["vector"]:
        build_vector_index(all_chunks, cfg)

    # Report
    generate_relevance_report(all_chunks, report_dir / "relevance_report.tsv")
    print("Done.")

if __name__ == "__main__":
    main()