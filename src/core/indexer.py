try:
    from sentence_transformers import SentenceTransformer
    import chromadb
    EMBEDDING_AVAILABLE = True
    _model = SentenceTransformer("all-MiniLM-L6-v2")
    _client = chromadb.PersistentClient(path=".chroma")
    _coll = _client.get_or_create_collection("papers")
except ImportError:
    EMBEDDING_AVAILABLE = False
    _model = None
    _client = None
    _coll = None

def purge_by_source(source: str):
    """Entfernt vorhandene Einträge zu einer Quelle (z. B. Datei-Pfad) aus der Collection."""
    if not EMBEDDING_AVAILABLE:
        raise ImportError("Embedding dependencies not available")
    
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
    """Add document to ChromaDB collection."""
    if not EMBEDDING_AVAILABLE:
        raise ImportError("Embedding dependencies not available. Install with: pip install sentence-transformers chromadb")
    
    chunks = chunk(text)
    embs = _model.encode(chunks, convert_to_numpy=True).tolist()
    _coll.add(
        documents=chunks,
        metadatas=[meta]*len(chunks),
        ids=[f"{doc_id}:{i}" for i in range(len(chunks))],
        embeddings=embs
    )
    return len(chunks)