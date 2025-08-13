"""
Verify language-specific vector stores for the MSU Enrollment Assistant.
This script checks if all language vector stores exist and are properly loaded.
"""
import os
import sys
from flask import Flask
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS

# Create a minimal Flask app for configuration
app = Flask(__name__)
app.config.from_pyfile('instance/config.py', silent=True)

# Initialize language-specific paths
INSTANCE_PATH = app.instance_path
LANGUAGE_CODES = ["en", "es", "zh", "ms"]
LANGUAGE_NAMES = {
    "en": "English",
    "es": "Spanish",
    "zh": "Chinese",
    "ms": "Malay"
}

def verify_vector_store(language_code):
    """
    Verify that a language-specific vector store exists and can be loaded.
    
    Args:
        language_code (str): Language code ('en', 'es', 'zh', 'ms')
    
    Returns:
        bool: True if vector store exists and can be loaded, False otherwise
    """
    # Define vector store path
    vector_store_dir = "vector_store" if language_code == "en" else f"vector_store_{language_code}"
    vector_store_path = os.path.join(INSTANCE_PATH, vector_store_dir)
    
    print(f"Checking {LANGUAGE_NAMES.get(language_code, language_code)} vector store at {vector_store_path}")
    
    # Check if vector store exists
    if not os.path.exists(vector_store_path):
        print(f"❌ Vector store for {language_code} does not exist at {vector_store_path}")
        return False
    
    # Get Google API key
    google_api_key = app.config.get("GOOGLE_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not google_api_key:
        print("❌ Error: GOOGLE_API_KEY not found in environment variables or app config")
        return False
    
    try:
        # Initialize embeddings
        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004",
            google_api_key=google_api_key
        )
        
        # Try to load the vector store
        vector_store = FAISS.load_local(
            vector_store_path,
            embeddings,
            allow_dangerous_deserialization=True,
        )
        
        # Test a simple query to verify it works
        results = vector_store.similarity_search("test query", k=1)
        
        print(f"✅ Successfully loaded vector store for {language_code}")
        print(f"   Sample document: {results[0].page_content[:100]}...\n")
        return True
        
    except Exception as e:
        print(f"❌ Error loading vector store for {language_code}: {str(e)}")
        return False

def main():
    """Main function to verify all language-specific vector stores."""
    print("\n=== Verifying language-specific vector stores ===\n")
    
    success_count = 0
    
    # Check each language
    for lang_code in LANGUAGE_CODES:
        if verify_vector_store(lang_code):
            success_count += 1
    
    # Print summary
    print(f"\n=== Summary: {success_count}/{len(LANGUAGE_CODES)} vector stores verified ===")
    
    if success_count < len(LANGUAGE_CODES):
        print("\nSome vector stores are missing or cannot be loaded.")
        print("Please run init_language_db.py to initialize them.")
    else:
        print("\nAll vector stores are properly initialized and can be loaded.")

if __name__ == "__main__":
    main()
