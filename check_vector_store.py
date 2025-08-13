from app import app
from blueprints.langchain_setup import load_vector_store, create_or_update_vector_store, load_pdf_documents

def check_vector_store():
    with app.app_context():
        # Try to load existing vector store
        vector_store = load_vector_store()
        if vector_store is not None:
            print("✅ Vector store loaded successfully!")
            return True
        
        # If loading fails, try to create a new one
        print("❌ Vector store not found. Creating new vector store...")
        docs = load_pdf_documents()
        if not docs:
            print("❌ No PDF documents found!")
            return False
        
        print(f"📚 Loaded {len(docs)} documents")
        vector_store = create_or_update_vector_store(docs)
        if vector_store is not None:
            print("✅ Vector store created successfully!")
            return True
        else:
            print("❌ Failed to create vector store")
            return False

if __name__ == "__main__":
    check_vector_store()
