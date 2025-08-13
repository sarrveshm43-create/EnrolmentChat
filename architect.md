Here’s a high-level architectural analysis of your system, based on the files and code you provided. I will now generate a Mermaid diagram that captures the main architectural components and their relationships.
Key Architectural Components Identified:
Flask Application Factory (app.py)
Blueprints: main, admin, api, chat_controller
Models: User, Document, ChatSession, ChatMessage, QueryLog
RAG/AI Layer: RAGProcessor (LangChain, Groq, OpenAI, Gemini, FAISS)
Templates (Jinja2): base.html, index.html, admin/*
Static Assets: CSS, JS, images, PDFs, uploads
Database: SQLite (msu_chatbot.sqlite)
Logging: Rotating file handler
Extensions: Flask-Login, Flask-Caching, SQLAlchemy
Admin Dashboard
Relationships:
Blueprints register routes and use models for DB operations.
RAGProcessor is used by API and chat controllers for AI responses.
Templates render UI, using data from blueprints/models.
Static files are served for frontend assets.
Database stores users, documents, chat sessions, messages, and logs.
I will now create a Mermaid diagram file (architecture.mmd) to visually represent this architecture.
The architectural analysis is complete!
I have created a Mermaid diagram file named architecture.mmd that visually represents all the main components and their relationships in your system, including:
Flask app factory and extensions
Blueprints (main, admin, api, chat_controller)
Database models (User, Document, ChatSession, ChatMessage, QueryLog)
RAG/AI layer (LangChain, Groq, OpenAI, Gemini, FAISS)
Templates and static assets
SQLite database
Logging
You can view or render this Mermaid file using any Mermaid live editor or compatible tool. If you want the diagram in another format (e.g., PNG, SVG), let me know!
