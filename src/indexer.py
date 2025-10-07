from sentence_transformers import SentenceTransformer
import chromadb

_model = SentenceTransformer("all-MiniLM-L6-v2")
_client = chromadb.PersistentClient(path=".chroma")
_coll = _client.get_or_create_collection("papers")

def purge_by_source(source: str):
    """Entfernt vorhandene Einträge zu einer Quelle (z. B. Datei-Pfad) aus der Collection."""
    try:
        _coll.delete(where={"source": source})
    except Exception:
        pass

def chunk(text: str, max_chars: int = 1200):
    buf, out = [], []
    for line in text.splitlines():
        if sum(len(x) for x in buf) + len(line) > max_chars:
            out.append("\n".join(buf)); buf = []
        buf.append(line)
    if buf: out.append("\n".join(buf))
    return [c for c in out if c.strip()]

def add_document(doc_id: str, text: str, meta: dict):
    chunks = chunk(text)
    embs = _model.encode(chunks, convert_to_numpy=True).tolist()
    _coll.add(
        documents=chunks,
        metadatas=[meta]*len(chunks),
        ids=[f"{doc_id}:{i}" for i in range(len(chunks))],
        embeddings=embs
    )
    return len(chunks)
