#!/usr/bin/env python3
import argparse, textwrap
from sentence_transformers import SentenceTransformer
import chromadb

def main():
    ap = argparse.ArgumentParser(description="Suche im lokalen Vektorindex (.chroma)")
    ap.add_argument("query", help="Suchfrage")
    ap.add_argument("-k", type=int, default=5, help="Anzahl der Treffer")
    args = ap.parse_args()

    model = SentenceTransformer("all-MiniLM-L6-v2")
    qemb = model.encode([args.query], convert_to_numpy=True)[0].tolist()
    coll = chromadb.PersistentClient(path=".chroma").get_or_create_collection("papers")

    res = coll.query(
    query_embeddings=[qemb],
    n_results=args.k,
    include=["documents","metadatas","distances"]
    )

    docs  = res.get("documents", [[]])[0]
    metas = res.get("metadatas", [[]])[0]
    dists = res.get("distances", [[]])[0]
    ids   = res.get("ids", [[]])[0]
    if not res.get("documents") or not res["documents"]:
        print("Keine Treffer.")
        return

    docs  = res["documents"][0]
    metas = res["metadatas"][0]
    dists = res.get("distances", [[None]*len(docs)])[0]
    ids   = res["ids"][0]

    for i, (doc, meta, _id) in enumerate(zip(docs, metas, ids), 1):
        dist = dists[i-1] if i-1 < len(dists) else None
        title = meta.get("filename") or meta.get("source") or "?"
        dist_s = "" if dist is None else f" (dist={dist:.4f})"
        print(f"{i}. {title}{dist_s}  id={_id}")
        if "source" in meta: print(f"   source: {meta['source']}")
        note = meta.get("note") or meta.get("tag")
        if note: print(f"   meta: {note}")
        preview = " ".join(doc.strip().split())
        if len(preview) > 280: preview = preview[:280] + "…"
        print("   └─", preview)

if __name__ == "__main__":
    main()
