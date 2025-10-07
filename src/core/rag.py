import chromadb
from sentence_transformers import SentenceTransformer
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from ..config import CFG

def ask(question: str, k: int = 5):
    embedding_model = CFG.get("models", {}).get("embedding", "all-MiniLM-L6-v2")
    enc = SentenceTransformer(embedding_model).encode([question], convert_to_numpy=True)[0].tolist()
    persist_path = CFG.get("rag", {}).get("persist_path") or CFG.get("paths", {}).get("chroma", ".chroma")
    collection_name = CFG.get("rag", {}).get("collection", "papers")
    coll = chromadb.PersistentClient(path=persist_path).get_or_create_collection(collection_name)
    res = coll.query(query_embeddings=[enc], n_results=k)
    ctx = "\n\n".join(res["documents"][0]) if res["documents"] else ""
    prompt = ChatPromptTemplate.from_template(
        "Beantworte die Frage ausschließlich anhand des Kontexts.\n\nKontext:\n{context}\n\nFrage: {q}"
    )
    openai_api_key = CFG.get("services", {}).get("openai", {}).get("api_key")
    if not openai_api_key:
        raise RuntimeError("OPENAI_API_KEY fehlt. Bitte in der Konfiguration oder Umgebung setzen.")
    chat_model = CFG.get("models", {}).get("chat", "gpt-4o-mini")
    llm = ChatOpenAI(api_key=openai_api_key, model=chat_model, temperature=0)
    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"context": ctx, "q": question})