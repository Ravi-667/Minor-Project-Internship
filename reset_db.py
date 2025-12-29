from qdrant_client import QdrantClient

def reset():
    print("Connecting to Qdrant...")
    client = QdrantClient(url="http://localhost:6333")
    
    # 1. Delete the PDF Collection
    try:
        client.delete_collection("study_knowledge_base")
        print("✅ Deleted old PDF collection.")
    except:
        pass

    # 2. Delete the Mem0/User Collection (This is the one causing your error!)
    try:
        client.delete_collection("user_long_term_memory")
        print("✅ Deleted old User Memory collection.")
    except:
        pass
        
    print("✨ Qdrant is now 100% clean.")

if __name__ == "__main__":
    reset()