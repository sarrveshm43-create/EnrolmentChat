import json
import time
import uuid
from flask import Blueprint, jsonify, request
from models.database import db, Document, ChatSession, ChatMessage, QueryLog
from models.rag_utils import RAGProcessor

api = Blueprint("api", __name__)

@api.route("/chat", methods=["POST"])
def chat():
    """API endpoint for chat interactions."""
    data = request.json

    if not data:
        return jsonify({"status": "error", "message": "No data provided"}), 400

    # Extract parameters
    query = data.get("message", "").strip()
    session_id = data.get("session_id")
    language = data.get("language", "en")

    if not query:
        return jsonify({"status": "error", "message": "No message provided"}), 400

    # Create or get session
    if not session_id:
        session_id = str(uuid.uuid4())
        chat_session = ChatSession(
            session_id=session_id, user_ip=request.remote_addr, language=language
        )
        db.session.add(chat_session)
        db.session.commit()
    else:
        chat_session = ChatSession.query.filter_by(session_id=session_id).first()
        if not chat_session:
            # Create a new session if not found
            chat_session = ChatSession(
                session_id=session_id, user_ip=request.remote_addr, language=language
            )
            db.session.add(chat_session)
            db.session.commit()

    # Save the user message
    user_message = ChatMessage(
        session_id=chat_session.id,
        is_user=True,
        message=query,
        original_language=language,
    )
    db.session.add(user_message)
    db.session.commit()

    # Process the query
    try:
        rag_processor = RAGProcessor(
            groq_api_key=current_app.config.get("GROQ_API_KEY"),
            openai_api_key=current_app.config.get("OPENAI_API_KEY"),
        )

        start_time = time.time()
        response = rag_processor.process_query(query, language)
        processing_time = time.time() - start_time

        # Save the bot response
        bot_message = ChatMessage(
            session_id=chat_session.id,
            is_user=False,
            message=response["answer"],
            original_language=language,
        )
        db.session.add(bot_message)

        # Log the query
        query_log = QueryLog(
            query=query,
            chat_message_id=user_message.id,
            language=language,
            processed_time=response["processing_time"],
            response_length=len(response["answer"]),
            relevant_docs=json.dumps([str(doc) for doc in response["context"]]),
        )
        db.session.add(query_log)
        db.session.commit()

        return jsonify(
            {
                "status": "success",
                "session_id": chat_session.session_id,
                "answer": response["answer"],
                "context": [doc.page_content for doc in response["context"]],
                "processing_time": processing_time,
            }
        )

    except Exception as e:
        current_app.logger.error(f"API Error processing query: {str(e)}")
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Error processing query",
                    "error": str(e),
                }
            ),
            500,
        )


@api.route("/sessions/<session_id>/messages", methods=["GET"])
def get_messages(session_id):
    """Get all messages for a session."""
    chat_session = ChatSession.query.filter_by(session_id=session_id).first()

    if not chat_session:
        return jsonify({"status": "error", "message": "Session not found"}), 404

    messages = (
        ChatMessage.query.filter_by(session_id=chat_session.id)
        .order_by(ChatMessage.timestamp)
        .all()
    )

    message_list = [
        {
            "id": msg.id,
            "content": msg.message,
            "is_user": msg.is_user,
            "timestamp": msg.timestamp.isoformat(),
        }
        for msg in messages
    ]

    return jsonify(
        {"status": "success", "session_id": session_id, "messages": message_list}
    )


@api.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    # Check database connection
    try:
        db.session.execute("SELECT 1")
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    # Check RAG system
    try:
        rag_processor = RAGProcessor(
            groq_api_key=current_app.config.get("GROQ_API_KEY"),
            openai_api_key=current_app.config.get("OPENAI_API_KEY"),
        )
        vector_store = rag_processor.load_vector_store()
        rag_status = "available" if vector_store else "unavailable"
    except Exception as e:
        rag_status = f"error: {str(e)}"

    return jsonify(
        {
            "status": "ok",
            "database": db_status,
            "rag_system": rag_status,
            "version": "1.0.0",
        }
    )
