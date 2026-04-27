"""Reset vector store and test the app retriever with chunked indexing."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import chromadb
from semantic_layer_fvl.vectorstore.embeddings import EmbeddingService

PERSIST_DIR = ROOT / "vectorstore"
COLLECTION = "fvl_knowledge"

# Step 1: Initialize without deleting
print("=== Initializing ===")
client = chromadb.PersistentClient(path=str(PERSIST_DIR))

# Step 2: Use the app retriever (which will auto-index with chunks)
print("\n=== Building retriever (will auto-index with chunks) ===")
from app.retriever import build_retriever

knowledge_dir = ROOT / "knowledge"
retriever = build_retriever(knowledge_dir, PERSIST_DIR)
print(f"Total chunks indexed: {retriever.count}")

# Step 3: Test searches
print("\n=== Search: 'historia del valle del lili' ===")
context = retriever.retrieve("historia del valle del lili", k=5)
print(context[:1500])

print("\n=== Search: 'misión de la fundación' ===")
context2 = retriever.retrieve("misión de la fundación", k=3)
print(context2[:800])
