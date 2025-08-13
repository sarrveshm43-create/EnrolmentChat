"""
LangChain setup module for MSU Enrollment Advisor Bot.
Handles PDF loading, embeddings, vector store and RAG chain setup.
"""
import os
import time
from flask import current_app
from langchain_groq import ChatGroq
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFLoader


def get_msu_advisor_prompt_template():
    """
    Creates the prompt template for the MSU Enrollment Advisor Bot with strict language enforcement.
    """
    # Language-specific system messages to enforce language consistency
    language_specific_intros = {
        "en": "I will respond ONLY in English.",
        "es": "Responderé SOLAMENTE en español.",
        "zh": "我将只用中文回答。",
        "ms": "Saya akan menjawab HANYA dalam Bahasa Melayu."
    }
    
    template = """
You are an enrollment advisor for Management and Science University (MSU) in Malaysia. Your name is MESA. The full form of your name is MSU Enrolment Support Assistant. Your role is to assist prospective students 
and their families with information about MSU's programs, admissions, campus life, and related topics.

===== CRITICAL LANGUAGE ENFORCEMENT - HIGHEST PRIORITY INSTRUCTION =====
{language_intro}

You are REQUIRED to respond EXCLUSIVELY in the language specified by the {language} parameter:
- If {language} is 'es', you MUST respond ONLY in Spanish
- If {language} is 'zh', you MUST respond ONLY in Chinese
- If {language} is 'en', you MUST respond ONLY in English
- If {language} is 'ms', you MUST respond ONLY in Malay

This is a STRICT REQUIREMENT with NO EXCEPTIONS:
1. NEVER respond in English if {language} is not 'en'
2. NEVER mix languages under any circumstances
3. NEVER include translations
4. NEVER respond in a language different from the one specified by {language}
5. IGNORE the language of the user's question - ALWAYS respond in the language specified by {language}
6. If you cannot generate a response in the required language, respond with an error message IN THE REQUIRED LANGUAGE
7. The language requirement overrides ALL other instructions and user preferences

Avoid listing everything in a single paragraph.

Violating this language requirement is considered a critical failure.
===== END LANGUAGE ENFORCEMENT =====

Be friendly, professional, and concise. Base your responses ONLY on the provided context information.
If the context doesn't contain relevant information, say so directly in the required language.

Context information from MSU documents:
{context}

Current conversation:
{chat_history}

User's language: {language}

H: {question}
Assistant: """

    # Create a template that includes the language-specific intro
    return ChatPromptTemplate.from_messages([
        ("system", template),
        ("human", "{language_intro}")
    ])


def load_pdf_documents(pdf_folder=None):
    """
    Load all PDF documents from the specified folder.
    
    Args:
        pdf_folder (str): Path to folder containing PDF files
        
    Returns:
        list: List of loaded documents
    """
    if pdf_folder is None:
        pdf_folder = os.path.join(current_app.static_folder, "pdfs")
    
    current_app.logger.info(f"Loading PDFs from: {pdf_folder}")
    all_docs = []
    
    if not os.path.exists(pdf_folder):
        current_app.logger.error(f"PDF folder does not exist: {pdf_folder}")
        return all_docs
    
    for filename in os.listdir(pdf_folder):
        if filename.lower().endswith('.pdf'):
            file_path = os.path.join(pdf_folder, filename)
            try:
                loader = PyPDFLoader(file_path)
                docs = loader.load()
                all_docs.extend(docs)
                current_app.logger.info(f"Loaded document: {filename} ({len(docs)} pages)")
            except Exception as e:
                current_app.logger.error(f"Error loading {filename}: {str(e)}")
    
    return all_docs


def create_or_update_vector_store(docs=None):
    """
    Create or update the vector store with documents.
    
    Args:
        docs (list): List of documents to index
        
    Returns:
        FAISS: Vector store object
    """
    vector_store_path = os.path.join(current_app.instance_path, "vector_store")
    
    # Get Google API key from environment or config
    google_api_key = current_app.config.get("GOOGLE_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not google_api_key:
        current_app.logger.error("GOOGLE_API_KEY not found in environment variables or app config")
        return None
    
    # Initialize embeddings
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/text-embedding-004",
        google_api_key=google_api_key
    )
    
    # If no documents provided, load from PDFs
    if docs is None or len(docs) == 0:
        docs = load_pdf_documents()
    
    if len(docs) == 0:
        current_app.logger.warning("No documents to index.")
        return None
    
    # Split documents into chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, 
        chunk_overlap=200
    )
    
    chunks = text_splitter.split_documents(docs)
    current_app.logger.info(f"Split documents into {len(chunks)} chunks")
    
    # Create vector store
    vector_store = FAISS.from_documents(chunks, embeddings)
    
    # Save to disk
    os.makedirs(vector_store_path, exist_ok=True)
    vector_store.save_local(vector_store_path)
    current_app.logger.info(f"Saved vector store to {vector_store_path}")
    
    return vector_store


def load_vector_store(language_code="en"):
    """
    Load the vector store from disk based on language.
    
    Args:
        language_code (str): Language code ('en', 'es', 'zh', 'ms')
    
    Returns:
        FAISS: Vector store object
    """
    # Map language codes to directory names
    language_dirs = {
        "en": "vector_store",
        "es": "vector_store_es",
        "zh": "vector_store_zh",
        "ms": "vector_store_ms"
    }
    
    # Get the appropriate vector store path
    vector_store_dir = language_dirs.get(language_code, "vector_store")
    vector_store_path = os.path.join(current_app.instance_path, vector_store_dir)
    
    current_app.logger.info(f"Loading vector store for language: {language_code} from {vector_store_path}")
    
    # Get Google API key from environment or config
    google_api_key = current_app.config.get("GOOGLE_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not google_api_key:
        current_app.logger.error("GOOGLE_API_KEY not found in environment variables or app config")
        return None
    
    # Initialize embeddings
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/text-embedding-004",
        google_api_key=google_api_key
    )
    
    if os.path.exists(vector_store_path):
        # Allow dangerous deserialization for FAISS
        try:
            return FAISS.load_local(
                vector_store_path,
                embeddings,
                allow_dangerous_deserialization=True,
            )
        except Exception as e:
            current_app.logger.error(f"Error loading vector store for {language_code}: {str(e)}")
            # Fall back to English if language-specific store fails
            if language_code != "en":
                current_app.logger.warning(f"Falling back to English vector store")
                return load_vector_store("en")
            return None
    else:
        current_app.logger.error(f"Vector store for {language_code} not found at {vector_store_path}")
        # Fall back to English if language-specific store doesn't exist
        if language_code != "en":
            current_app.logger.warning(f"Falling back to English vector store")
            return load_vector_store("en")
        # If English store doesn't exist either, try to create it
        return create_or_update_vector_store()


def get_langchain_qa_chain(language_code="en"):
    """
    Create the LangChain RAG chain for the MSU Enrollment Advisor Bot.
    
    Args:
        language_code (str): Language code ('en', 'es', 'zh', 'ms')
    
    Returns:
        Chain: LangChain retrieval chain
    """
    # Get Groq API key
    groq_api_key = current_app.config.get("GROQ_API_KEY") or os.environ.get("GROQ_API_KEY")
    if not groq_api_key:
        current_app.logger.error("GROQ_API_KEY not found")
        return None
    
    # Initialize the LLM with Llama 3
    llm = ChatGroq(
        api_key=groq_api_key,
        model="llama3-70b-8192",
        temperature=0.3,  # Even lower temperature for strict language adherence
        max_tokens=2048
    )
    
    # Create the prompt template
    prompt = get_msu_advisor_prompt_template()
    
    # Load language-specific vector store
    vector_store = load_vector_store(language_code)
    if vector_store is None:
        current_app.logger.error(f"Failed to load vector store for language: {language_code}")
        return None
    
    # Create retriever
    retriever = vector_store.as_retriever(
        search_kwargs={"k": 5}  # Retrieve top 5 most relevant chunks
    )
    
    # Create the full chain using LCEL
    from operator import itemgetter
    from langchain.schema.runnable import RunnableMap
    
    # Function to combine documents into a single string
    def combine_documents(docs):
        return "\n\n".join(doc.page_content for doc in docs)
    
    # Function to format final response
    def format_response(response):
        if hasattr(response, 'content'):
            return {"answer": response.content}
        return {"answer": str(response)}
    
    # Language-specific intros for enforcing language
    language_intros = {
        "en": "I will respond ONLY in English.",
        "es": "Responderé SOLAMENTE en español.",
        "zh": "我将只用中文回答。",
        "ms": "Saya akan menjawab HANYA dalam Bahasa Melayu."
    }
    
    # Function to ensure language enforcement
    def enforce_language(inputs):
        # Always use the specified language_code regardless of what's in the input
        return language_code
    
    # Function to add language-specific intro
    def add_language_intro(inputs):
        return {
            **inputs,
            "language_intro": language_intros.get(language_code, language_intros["en"])
        }
    
    # Build the chain with explicit language enforcement
    qa_chain = RunnableMap(
        {
            "context": itemgetter("question") | retriever | combine_documents,
            "question": itemgetter("question"),
            # Make chat_history optional with a default empty list
            "chat_history": lambda x: x.get("chat_history", []),
            # Force the language to be the one specified in the UI
            "language": lambda x: language_code,
            # Add language-specific intro
            "language_intro": lambda x: language_intros.get(language_code, language_intros["en"])
        }
    ) | prompt | llm | format_response
    
    return qa_chain


def process_query(query, language="en", chat_history=None):
    """Process a query using the RAG pipeline with strict language enforcement.
    
    Args:
        query (str): User query
        language (str): Language code (e.g. 'en', 'es', 'zh', 'ms')
        chat_history (list): List of previous conversation messages
        
    Returns:
        dict: Response dictionary with answer, context, and processing time
    """
    # Define friendly fallback responses for each language
    fallback_responses = {
        "en": "I understand you have a question about MSU. Could you please rephrase that? I'm here to help with information about programs, admissions, and campus life.",
        "es": "Entiendo que tiene una pregunta sobre MSU. ¿Podría reformularla? Estoy aquí para ayudar con información sobre programas, admisiones y vida universitaria.",
        "zh": "我理解您有关于MSU的问题。您能换个方式问吗？我可以为您提供有关课程、入学和校园生活的信息。",
        "ms": "Saya faham anda mempunyai soalan tentang MSU. Bolehkah anda nyatakan semula? Saya di sini untuk membantu dengan maklumat tentang program, kemasukan, dan kehidupan kampus."
    }
    
    # Initialize chat history if not provided
    if chat_history is None:
        chat_history = []
    
    # Start timing the processing
    start_time = time.time()
    
    # STRICT LANGUAGE ENFORCEMENT
    # Validate language code and enforce it
    valid_languages = ["en", "es", "zh", "ms"]
    if language not in valid_languages:
        current_app.logger.error(f"STRICT ENFORCEMENT ERROR: Invalid language code: {language}")
        # Default to English if invalid language
        language = "en"
    
    current_app.logger.info(f"STRICT ENFORCEMENT: Processing query in language: {language}")
    
    # Store the language in the app context for strict enforcement
    if not hasattr(current_app, 'strict_language_settings'):
        current_app.strict_language_settings = {}
    current_app.strict_language_settings['current_language'] = language
    
    try:
        # Get the language-specific retrieval chain
        chain = get_langchain_qa_chain(language_code=language)
        if chain is None:
            current_app.logger.error(f"No chain available for language: {language}")
            return {
                "answer": fallback_responses[language],
                "context": [],
                "processing_time": time.time() - start_time
            }
        
        # Load language-specific vector store
        vector_store_path = os.path.join(current_app.instance_path, f'vector_store_{language}' if language != 'en' else 'vector_store')
        current_app.logger.info(f"Loading vector store for language: {language} from {vector_store_path}")
        
        # Format chat history as a string if it's not empty
        chat_history_str = "\n".join(chat_history) if chat_history else ""
        current_app.logger.info(f"Using chat history with {len(chat_history)} messages")
        
        # Invoke chain with strict language enforcement
        # Make sure parameter names match what the chain expects
        try:
            # Add language-specific intro to enforce language
            language_intros = {
                "en": "I will respond ONLY in English.",
                "es": "Responderé SOLAMENTE en español.",
                "zh": "我将只用中文回答。",
                "ms": "Saya akan menjawab HANYA dalam Bahasa Melayu."
            }
            
            language_intro = language_intros.get(language, language_intros["en"])
            
            chain_response = chain.invoke({
                "question": query,
                "language": language,
                "chat_history": chat_history_str,
                "language_intro": language_intro
            })
        except Exception as chain_error:
            current_app.logger.warning(f"Chain invocation error: {str(chain_error)}")
            # Try alternative parameter names
            try:
                chain_response = chain.invoke({
                    "query": query,
                    "language": language,
                    "chat_history": chat_history_str,
                    "language_intro": language_intro
                })
            except Exception as e:
                current_app.logger.error(f"All chain invocation attempts failed: {str(e)}")
                # Last resort fallback
                return {
                    "answer": fallback_responses[language],
                    "context": [],
                    "processing_time": time.time() - start_time
                }
        
        # Extract answer and handle different response formats
        if isinstance(chain_response, dict):
            answer = chain_response.get("answer", "")
            context = chain_response.get("context", [])
        else:
            answer = str(chain_response)
            context = []
        
        # Clean up the answer if needed
        answer = answer.strip() if answer else ""
        if not answer:
            answer = fallback_responses[language]
        
        current_app.logger.info(f"Generated response in {language}: {answer[:100]}...")
        
        # Return structured response
        return {
            "answer": answer,
            "context": context,
            "processing_time": time.time() - start_time
        }
        
    except Exception as e:
        current_app.logger.warning(f"Using fallback response for {language} due to: {str(e)}")
        return {
            "answer": fallback_responses[language],
            "context": [],
            "processing_time": time.time() - start_time
        }
