"""
Fix language-specific vector stores for the MSU Enrollment Assistant.
This script creates separate vector stores for each supported language.
"""
import os
import sys
import shutil
from flask import Flask
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema.document import Document

# Create a minimal Flask app for configuration
app = Flask(__name__)
app.config.from_pyfile('instance/config.py', silent=True)

# Initialize language-specific paths
INSTANCE_PATH = app.instance_path
LANGUAGE_FILES = {
    "en": None,  # English is already handled by the main vector store
    "es": "spanish.md",
    "zh": "chinese.md",
    "ms": "bahasa.md"
}

def create_vector_store(language_code, file_path=None):
    """
    Create a language-specific vector store.
    
    Args:
        language_code (str): Language code ('en', 'es', 'zh', 'ms')
        file_path (str): Path to the language-specific markdown file
    """
    if language_code == "en":
        print(f"Skipping English vector store creation (should already exist)")
        return True
    
    if not file_path or not os.path.exists(file_path):
        print(f"Error: File not found for {language_code}: {file_path}")
        return False
    
    # Define vector store path
    vector_store_dir = f"vector_store_{language_code}"
    vector_store_path = os.path.join(INSTANCE_PATH, vector_store_dir)
    
    # Remove existing vector store if it exists
    if os.path.exists(vector_store_path):
        print(f"Removing existing vector store for {language_code} at {vector_store_path}")
        try:
            shutil.rmtree(vector_store_path)
        except Exception as e:
            print(f"Error removing existing vector store: {str(e)}")
            return False
    
    # Get Google API key
    google_api_key = app.config.get("GOOGLE_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not google_api_key:
        print("Error: GOOGLE_API_KEY not found in environment variables or app config")
        return False
    
    try:
        # Load the language-specific markdown file
        print(f"Loading {language_code} content from {file_path}")
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Create a document from the content
        documents = [Document(page_content=content, metadata={"source": file_path, "language": language_code})]
        
        # Split documents into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, 
            chunk_overlap=200
        )
        chunks = text_splitter.split_documents(documents)
        print(f"Split {language_code} content into {len(chunks)} chunks")
        
        # Initialize embeddings
        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004",
            google_api_key=google_api_key
        )
        
        # Create vector store
        print(f"Creating vector store for {language_code}")
        vector_store = FAISS.from_documents(chunks, embeddings)
        
        # Save vector store
        os.makedirs(INSTANCE_PATH, exist_ok=True)
        vector_store.save_local(vector_store_path)
        print(f"Successfully created vector store for {language_code} at {vector_store_path}")
        return True
        
    except Exception as e:
        import traceback
        print(f"Error creating vector store for {language_code}: {str(e)}")
        print(traceback.format_exc())
        return False

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
    
    print(f"Verifying {language_code} vector store at {vector_store_path}")
    
    # Check if vector store exists
    if not os.path.exists(vector_store_path):
        print(f"Vector store for {language_code} does not exist at {vector_store_path}")
        return False
    
    # Get Google API key
    google_api_key = app.config.get("GOOGLE_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not google_api_key:
        print("Error: GOOGLE_API_KEY not found in environment variables or app config")
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
        
        print(f"Successfully verified vector store for {language_code}")
        print(f"Sample document: {results[0].page_content[:100]}...")
        return True
        
    except Exception as e:
        print(f"Error verifying vector store for {language_code}: {str(e)}")
        return False

def main():
    """Main function to fix all language-specific vector stores."""
    print("\n=== Fixing language-specific vector stores ===\n")
    
    # Create instance directory if it doesn't exist
    os.makedirs(INSTANCE_PATH, exist_ok=True)
    
    # Process each language
    success_count = 0
    for lang_code, filename in LANGUAGE_FILES.items():
        try:
            print(f"\n{'='*50}\nProcessing {lang_code} language file\n{'='*50}")
            
            if lang_code == "en":
                # Just verify English vector store
                if verify_vector_store(lang_code):
                    success_count += 1
                continue
                
            if filename:
                file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
                if create_vector_store(lang_code, file_path):
                    if verify_vector_store(lang_code):
                        success_count += 1
                        print(f"Successfully processed {lang_code} language file.")
            
        except Exception as e:
            print(f"Failed to process {lang_code} language file: {str(e)}")
    
    print(f"\n=== Summary: {success_count}/{len(LANGUAGE_FILES)} vector stores fixed ===")
    
    if success_count < len(LANGUAGE_FILES):
        print("\nSome vector stores could not be created or verified.")
        print("Please check the logs for details.")
    else:
        print("\nAll vector stores are properly initialized and verified.")

if __name__ == "__main__":
    main()
