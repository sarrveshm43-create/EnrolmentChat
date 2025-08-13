"""
Initialize language-specific vector stores for the MSU Enrollment Assistant.
This script creates separate vector stores for each supported language.
"""
import os
import sys
from flask import Flask
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader

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
        return
    
    if not file_path or not os.path.exists(file_path):
        print(f"Error: File not found for {language_code}: {file_path}")
        return
    
    # Define vector store path
    vector_store_dir = f"vector_store_{language_code}"
    vector_store_path = os.path.join(INSTANCE_PATH, vector_store_dir)
    
    # Check if vector store already exists
    if os.path.exists(vector_store_path):
        print(f"Vector store for {language_code} already exists at {vector_store_path}")
        return
    
    # Get Google API key
    google_api_key = app.config.get("GOOGLE_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not google_api_key:
        print("Error: GOOGLE_API_KEY not found in environment variables or app config")
        return
    
    try:
        # Load the language-specific markdown file
        print(f"Loading {language_code} content from {file_path}")
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Create a document from the content
        from langchain.schema.document import Document
        documents = [Document(page_content=content, metadata={"source": file_path})]
        
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
        
    except Exception as e:
        import traceback
        print(f"Error creating vector store for {language_code}: {str(e)}")
        print(traceback.format_exc())

def main():
    """Main function to initialize all language-specific vector stores."""
    print("Initializing language-specific vector stores...")
    
    # Create instance directory if it doesn't exist
    os.makedirs(INSTANCE_PATH, exist_ok=True)
    
    # Process each language
    for lang_code, filename in LANGUAGE_FILES.items():
        if filename:
            try:
                file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
                print(f"\n{'='*50}\nProcessing {lang_code} language file: {filename}\n{'='*50}")
                create_vector_store(lang_code, file_path)
                print(f"Completed processing {lang_code} language file.\n")
            except Exception as e:
                print(f"Failed to process {lang_code} language file: {str(e)}\n")
    
    print("Vector store initialization complete.")

if __name__ == "__main__":
    main()
