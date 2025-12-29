import os
import sys
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_qdrant import QdrantVectorStore

# Try to import your loader, or fail gracefully
try:
    from document_loader import load_any_file
except ImportError:
    print("❌ Error: missing 'document_loaders.py'")
    sys.exit(1)

# --- CONFIGURATION ---
DOCS_FOLDER = "./data"
QDRANT_URL = "http://localhost:6333" 
COLLECTION_NAME = "study_knowledge_base"
EMBED_MODEL = "nomic-embed-text:v1.5"

def ingest_documents():
    if not os.path.exists(DOCS_FOLDER):
        os.makedirs(DOCS_FOLDER)
        print(f"Please put files in {DOCS_FOLDER}")
        return

    all_docs = []
    print(f" Scanning {DOCS_FOLDER}...")

    for root, dirs, files in os.walk(DOCS_FOLDER):
        for file_name in files:
            if file_name.startswith("."): continue
            file_path = os.path.join(root, file_name)
            
            try:
                docs = load_any_file(file_path)
                if docs:
                    # Tag with folder name
                    cat = os.path.basename(root)
                    for d in docs: d.metadata["category"] = cat
                    all_docs.extend(docs)
                    print(f"   ✅ Loaded: {file_name}")
            except Exception as e:
                print(f"    Error {file_name}: {e}")

    if not all_docs:
        print("No documents found.")
        return

    print(f"\n  Splitting {len(all_docs)} docs...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_documents(all_docs)

    print(f"\n🧠 Saving to Qdrant (Docker)...")
    embedding_model = OllamaEmbeddings(model=EMBED_MODEL)

    QdrantVectorStore.from_documents(
        documents=chunks,
        embedding=embedding_model,
        url=QDRANT_URL,
        collection_name=COLLECTION_NAME,
        force_recreate=True 
    )

    print("🎉 Ingestion Complete!")

if __name__ == "__main__":
    ingest_documents()