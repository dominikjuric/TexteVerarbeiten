import chromadb
from sentence_transformers import SentenceTransformer
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from ..config import CFG

def ask(question: str, k: int = 5):
    enc = SentenceTransformer("all-MiniLM-L6-v2").encode([question], convert_to_numpy=True)[0].tolist()
    coll = chromadb.PersistentClient(path=".chroma").get_or_create_collection("papers")
    res = coll.query(query_embeddings=[enc], n_results=k)
    ctx = "\n\n".join(res["documents"][0]) if res["documents"] else ""
    prompt = ChatPromptTemplate.from_template(
        "Beantworte die Frage ausschließlich anhand des Kontexts.\n\nKontext:\n{context}\n\nFrage: {q}"
    )
    llm = ChatOpenAI(api_key=CFG["OPENAI_API_KEY"], model="gpt-4o-mini", temperature=0)
    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"context": ctx, "q": question})