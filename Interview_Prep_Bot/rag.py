import os
import chromadb
from sentence_transformers import SentenceTransformer
from langchain_groq import ChatGroq
from dotenv import load_dotenv
import streamlit as st

load_dotenv()

CHROMA_PATH     = "./db"
COLLECTION_NAME = "interview_questions"
EMBED_MODEL     = "all-MiniLM-L6-v2"
GROQ_MODEL      = "llama-3.1-8b-instant"
TOP_K           = 5

@st.cache_resource
def load_pipeline():
    """Load everything ONCE and cache — never reloads again"""
    print("Loading RAG pipeline (first time only)...")
    embed_model = SentenceTransformer(EMBED_MODEL)
    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = chroma_client.get_collection(name=COLLECTION_NAME)
    llm = ChatGroq(
        model=GROQ_MODEL,
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0.3,
        max_tokens=1024
    )
    print("✅ RAG pipeline ready")
    return embed_model, collection, llm


def generate_practice_answer(user_question: str) -> dict:
    embed_model, collection, llm = load_pipeline()

    # Retrieve
    query_embedding = embed_model.encode([user_question]).tolist()
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=TOP_K,
        include=["documents", "metadatas", "distances"]
    )

    chunks = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0]
    ):
        chunks.append({
            "document": doc,
            "topic": meta["topic"],
            "difficulty": meta["difficulty"],
            "question": meta["question"],
            "similarity": round(1 - dist, 3)
        })

    # Build context
    context = ""
    for i, chunk in enumerate(chunks):
        context += f"\n--- Reference {i+1} (Topic: {chunk['topic']}) ---\n"
        context += chunk["document"] + "\n"

    # Prompt
    prompt = f"""You are an expert AI interview coach for Data Science and AI interviews.

Student question: "{user_question}"

Relevant information from database:
{context}

Give a clear, structured interview-ready answer with:
1. Definition
2. Key points
3. Real example
4. Code if relevant
5. One follow-up question

Keep it concise and clear."""

    response = llm.invoke(prompt)

    return {
        "question": user_question,
        "answer": response.content,
        "retrieved_topics": [c["topic"] for c in chunks],
        "top_match": chunks[0]["question"] if chunks else "",
        "top_similarity": chunks[0]["similarity"] if chunks else 0,
        "chunks_used": len(chunks)
    }