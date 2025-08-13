import os
import json
import time
import google.generativeai as genai
from flask import current_app

# Import the base Groq client
from groq import Groq

from langchain_groq import ChatGroq
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains import create_retrieval_chain
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFLoader


class RAGProcessor:
    def __init__(self, groq_api_key=None):
        """Initialize the RAG processor with API keys and models"""
        self.groq_api_key = groq_api_key or os.environ.get("GROQ_API_KEY")
        if not self.groq_api_key:
            raise ValueError("GROQ_API_KEY must be set.")

        # Initialize the Langchain ChatGroq wrapper with Llama 3 for multilingual support
        self.llm = ChatGroq(
            model="llama3-70b-8192",  # Using Llama 3 model for multilingual support
            temperature=0.7,  # Slightly higher temperature for natural responses
            max_tokens=2048   # Maximum length of response
        )

        # Create the base prompt template with multilingual support
        self.prompt = ChatPromptTemplate.from_template(
            """
            You are a multilingual counselor and guide for Management & Science University (MSU). 
            Your job is to answer any enquiry about MSU (e.g., admissions, courses, campus life, facilities, events, fees, scholarships) clearly and accurately.
            
            Whenever you respond:
            1. Detect the user's language from their query and reply *entirely* in that language.
            
            Important rules:
            1. Answer questions based only on the provided context
            2. If information isn't in the context, admit that you don't know
            3. Keep the same language as the user's question throughout the response
            4. Be culturally sensitive and appropriate
            5. Use formal language suitable for academic communication
            
            <context>
            {context}
            </context>
            
            Question: {input}
            
            Provide a clear and concise response in a helpful and friendly tone.
            If asked about fees, programs, or requirements, be specific and accurate with the details provided.
            Remember to maintain the same language as the question.
            """
        )

        # Set up the document chain
        self.document_chain = create_stuff_documents_chain(self.llm, self.prompt)

        # Text splitter for chunking documents
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=200
        )

        # Initialize embeddings using Google Gemini with explicit API key
        google_api_key = os.environ.get("GOOGLE_API_KEY")
        if not google_api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables")
            
        genai.configure(api_key=google_api_key)
        
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004",
            google_api_key=google_api_key
        )

    # Removed problematic cache.memoize decorator that was causing errors
    def load_document(self, file_path):
        """Load and process a single PDF document"""
        try:
            current_app.logger.info(f"Loading document: {file_path}")
            
            # Check if file exists and is readable
            if not os.path.exists(file_path):
                current_app.logger.error(f"File does not exist: {file_path}")
                return []
                
            # Get file size for logging
            file_size = os.path.getsize(file_path)
            current_app.logger.info(f"File exists, size: {file_size} bytes")
            
            # Attempt to load PDF
            loader = PyPDFLoader(file_path)
            documents = loader.load()
            
            current_app.logger.info(f"Loaded {len(documents)} pages from {file_path}")
            if len(documents) == 0:
                current_app.logger.warning(f"No pages extracted from {file_path}")
                return []
                
            # Check if pages have content
            for i, doc in enumerate(documents):
                content_length = len(doc.page_content.strip())
                current_app.logger.info(f"Page {i+1} content length: {content_length} chars")
                
            # Split into chunks
            chunks = self.text_splitter.split_documents(documents)
            current_app.logger.info(f"Split into {len(chunks)} chunks")
            
            return chunks
        except Exception as e:
            current_app.logger.error(f"Error loading document {file_path}: {str(e)}", exc_info=True)
            return []

    def create_or_update_vector_store(self, file_paths):
        """Create or update the vector store from a list of file paths."""
        if not file_paths:
            current_app.logger.warning("No file paths provided to create_or_update_vector_store.")
            return False

        current_app.logger.info(f"Attempting to process {len(file_paths)} files: {file_paths}")
        
        all_docs = []
        successful_files = 0

        # Process each PDF from the provided list
        for file_path in file_paths:
            current_app.logger.info(f"Checking file path: {file_path}")
            current_app.logger.info(f"  - File exists: {os.path.exists(file_path)}")
            current_app.logger.info(f"  - Is PDF: {file_path.lower().endswith('.pdf')}")
            
            if os.path.exists(file_path) and file_path.lower().endswith(".pdf"):
                try:
                    current_app.logger.info(f"Processing document: {file_path}")
                    docs = self.load_document(file_path)
                    
                    if docs and len(docs) > 0:
                        all_docs.extend(docs)
                        successful_files += 1
                        current_app.logger.info(f"Successfully processed {file_path} and added {len(docs)} chunks")
                    else:
                        current_app.logger.warning(f"No content extracted from {file_path}")
                        
                except Exception as e:
                    current_app.logger.error(f"Error processing {file_path}: {str(e)}", exc_info=True)
            else:
                current_app.logger.warning(f"Skipping invalid or non-existent file path: {file_path}")
                
        current_app.logger.info(f"Successfully processed {successful_files} of {len(file_paths)} files")
        current_app.logger.info(f"Total document chunks extracted: {len(all_docs)}")


        # Create a new vector store if we have documents
        if all_docs:
            current_app.logger.info(f"Creating vector store with {len(all_docs)} chunks.")
            vector_store = FAISS.from_documents(all_docs, self.embeddings)

            # Save the vector store
            vector_store_path = os.path.join(current_app.instance_path, "vector_store")
            os.makedirs(vector_store_path, exist_ok=True)
            vector_store.save_local(vector_store_path)

            return True
        else:
            current_app.logger.warning("No valid documents processed, vector store not created.")
            return False

    def load_vector_store(self):
        current_app.logger.info("Caching for load_vector_store is currently disabled to avoid context errors.")
        """Load the vector store from disk"""
        vector_store_path = os.path.join(current_app.instance_path, "vector_store")

        if os.path.exists(vector_store_path):
            # Allow dangerous deserialization for FAISS
            return FAISS.load_local(
                vector_store_path,
                self.embeddings,  # Now uses Gemini embeddings
                allow_dangerous_deserialization=True,
            )

        # If not found, try to create it
        # This will now use Gemini embeddings if it needs to create the store
        self.create_or_update_vector_store([])

        # Try loading again
        if os.path.exists(vector_store_path):
            return FAISS.load_local(
                vector_store_path,
                self.embeddings,  # Now uses Gemini embeddings
                allow_dangerous_deserialization=True,
            )

        return None

    def process_query(self, query, language="en"):
        """Process a query using the RAG pipeline with multilingual support."""
        # Load the vector store (which uses Gemini embeddings)
        vector_store = self.load_vector_store()

        if vector_store is None:
            return {
                "answer": "I'm sorry, but I don't have any enrollment information loaded yet. Please contact the administrator.",
                "context": [],
                "processing_time": 0,
            }

        # Create a retriever from the vector store
        retriever = vector_store.as_retriever(
            search_kwargs={"k": 5}  # Retrieve top 5 most relevant chunks
        )

        # Update the prompt template to include the language parameter
        language_prompt = ChatPromptTemplate.from_template(
            """
            You are a multilingual counselor and guide for Management & Science University (MSU). 
            Your job is to answer any enquiry about MSU (e.g., admissions, courses, campus life, facilities, events, fees, scholarships) clearly and accurately.
            
            Whenever you respond:
            1. Detect the user's language from their query and reply *entirely* in that language.
            
            IMPORTANT: The user's selected language is: {language}. If this is specified, respond in this language.
            If no language is specified, detect the language of the user's question and respond in the same language.
            If you cannot detect the language, default to English.
            
            Important rules:
            1. Answer questions based only on the provided context
            2. If information isn't in the context, admit that you don't know
            3. Keep the same language as the user's question throughout the response
            4. Be culturally sensitive and appropriate
            5. Use formal language suitable for academic communication
            
            <context>
            {context}
            </context>
            
            Question: {input}
            
            Provide a clear and concise response in a helpful and friendly tone.
            If asked about fees, programs, or requirements, be specific and accurate with the details provided.
            Remember to maintain the same language as the question.
            """
        )

        # Create a document chain with the language-aware prompt
        document_chain = create_stuff_documents_chain(self.llm, language_prompt)

        # Create the retrieval chain
        retrieval_chain = create_retrieval_chain(retriever, document_chain)

        # Process the query and measure the time
        start_time = time.time()
        response = retrieval_chain.invoke({"input": query, "language": language})
        processing_time = time.time() - start_time

        return {
            "answer": response["answer"],
            "context": response["context"],
            "processing_time": processing_time,
        }
