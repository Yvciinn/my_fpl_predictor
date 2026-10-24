from paths import PYTHON
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

# ---------- 5a: load the existing store (no re-embedding) ----------
emb = OllamaEmbeddings(model="nomic-embed-text")
vectorstore = Chroma(
    collection_name="fpl_players",
    persist_directory=str(PYTHON / "chroma_db"),
    embedding_function=emb,
)
print("documents in store:", vectorstore._collection.count())   # 331

# ---------- 5b: retriever ----------
retriever = vectorstore.as_retriever(search_kwargs={"k": 4})

def format_docs(docs):
    return "\n\n".join(d.page_content for d in docs)

# ---------- 5c: strict prompt ----------
SYSTEM = """You are an assistant for Fantasy Premier League (FPL).
Answer using ONLY the player data in the context.

Rules:
1. Only use facts that appear in the context. Never use outside knowledge.
2. Quote numbers exactly as written in the context.
3. If the context does not contain the answer, reply exactly: I don't have that data.
4. Do not guess, estimate or invent statistics.
5. Keep the answer to 3 sentences or fewer."""

prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM),
    ("human", "Context:\n{context}\n\nQuestion: {question}"),
])

# ---------- 5d: the chain ----------
model = ChatOllama(model="llama3.1:8b", temperature=0)   # swap to "qwen2.5:3b" to compare

rag_chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | prompt
    | model
    | StrOutputParser()
)

# ---------- 5e: test and diagnose ----------
def ask(q: str):
    found = retriever.invoke(q)
    answer = rag_chain.invoke(q)
    print("\n==", q)
    print("retrieved:", [f"{d.metadata['name']} ({d.metadata['position']})" for d in found])
    print("answer:   ", answer)

if __name__ == "__main__":
    for q in [
        "where will Saka play?",
       
    ]:
        ask(q)