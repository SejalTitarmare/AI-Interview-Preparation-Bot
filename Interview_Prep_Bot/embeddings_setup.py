import json
import os
import chromadb
from sentence_transformers import SentenceTransformer

# ── Config ──────────────────────────────────────────
JSON_PATH       = "data/final_interview_dataset.json"
CHROMA_PATH     = "./db"
COLLECTION_NAME = "interview_questions"
EMBED_MODEL     = "all-MiniLM-L6-v2"
# ────────────────────────────────────────────────────

# STEP 1 — Load JSON dataset
print("Step 1: Loading dataset...")
with open(JSON_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)
print(f"✅ Loaded {len(data)} questions from JSON")

# STEP 2 — Build text chunks
print("\nStep 2: Building text chunks...")
documents = []
metadatas = []
ids = []

for i, entry in enumerate(data):
    # Combine topic + difficulty + question + answer into one string
    chunk = (
        f"Topic: {entry['topic']}\n"
        f"Difficulty: {entry['difficulty']}\n"
        f"Question: {entry['question']}\n"
        f"Answer: {entry['answer']}"
    )
    documents.append(chunk)

    # Metadata stored separately for filtering later
    metadatas.append({
        "topic":        entry["topic"],
        "difficulty":   entry["difficulty"],
        "question":     entry["question"],
        "company_tags": ", ".join(entry["company_tags"])
    })

    ids.append(f"q_{i}")

print(f"✅ Built {len(documents)} text chunks")

# STEP 3 — Load HuggingFace embedding model
print("\nStep 3: Loading HuggingFace embedding model...")
print("   (First run downloads ~90MB model — please wait...)")
model = SentenceTransformer(EMBED_MODEL)
print(f"✅ Model loaded: {EMBED_MODEL}")

# STEP 4 — Generate embeddings
print("\nStep 4: Generating embeddings for all questions...")
print("   (This converts each text chunk into a 384-number vector)")
embeddings = model.encode(documents, show_progress_bar=True)
print(f"✅ Generated embeddings — shape: {embeddings.shape}")
# shape will be (215, 384) — 215 questions, each 384 numbers

# STEP 5 — Store in ChromaDB
print("\nStep 5: Storing in ChromaDB...")
os.makedirs(CHROMA_PATH, exist_ok=True)
client = chromadb.PersistentClient(path=CHROMA_PATH)

# Delete old collection if it exists (safe to re-run)
try:
    client.delete_collection(name=COLLECTION_NAME)
    print("   (Old collection deleted — creating fresh)")
except:
    pass

collection = client.get_or_create_collection(
    name=COLLECTION_NAME,
    metadata={"hnsw:space": "cosine"}
)

collection.add(
    documents=documents,
    embeddings=embeddings.tolist(),
    metadatas=metadatas,
    ids=ids
)
print(f"✅ Stored {collection.count()} entries in ChromaDB")
print(f"✅ Database saved to: {CHROMA_PATH}/")

# STEP 6 — Test retrieval
print("\nStep 6: Testing retrieval...")
test_queries = [
    "explain gradient descent",
    "what is overfitting",
    "how does LSTM work"
]

for query in test_queries:
    query_embedding = model.encode([query]).tolist()
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=2
    )
    print(f"\n  Query: '{query}'")
    for meta in results["metadatas"][0]:
        print(f"    → [{meta['topic']}] {meta['question'][:60]}...")

print("\n" + "="*55)
print("DAY 3 COMPLETE — EMBEDDING SETUP DONE")
print("="*55)
print(f"✅ {len(data)} questions embedded and stored in ChromaDB")
print(f"✅ Database location: {CHROMA_PATH}/")
print("✅ Ready for Day 4 — RAG pipeline with Groq LLM")