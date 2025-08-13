import uuid
import json
from datetime import datetime
from flask import (
    Blueprint, render_template, request, jsonify,
    session, current_app, url_for
)
from models.database import db, Document, ChatSession, ChatMessage, QueryLog
from flask_caching import Cache
from models.rag_utils import RAGProcessor

cache = Cache()

main = Blueprint('main', __name__)


@main.route("/")
def index():
    """Render the main chat interface."""
    # Generate or retrieve a session ID
    if "chat_session_id" not in session:
        session["chat_session_id"] = str(uuid.uuid4())

        # Create a new chat session in the database
        chat_session = ChatSession(
            session_id=session["chat_session_id"],
            user_ip=request.remote_addr,
            language="en",  # Default language
        )
        db.session.add(chat_session)
        db.session.commit()

    return render_template("index.html")


@main.route("/chat", methods=["POST"])
def chat():
    """Redirect to the new chat controller endpoint for backward compatibility."""
    # This function now redirects to the new chat controller endpoint
    # for backward compatibility with existing frontend code
    data = request.json
    query = data.get("message", "").strip()
    language = data.get("language", "en")
    user_name = data.get("user_name", "there")
    
    if not query:
        # Define error messages for different languages
        error_messages = {
            "en": "Please enter a question.",
            "es": "Por favor, ingrese una pregunta.",
            "zh": "请输入问题。",
            "ms": "Sila masukkan soalan anda."
        }
        return jsonify({"answer": error_messages.get(language, error_messages["en"]), "context": []}), 400

    # Get the chat session ID
    session_id = session.get("chat_session_id")
    if not session_id:
        return jsonify({"answer": "Session expired. Please refresh the page.", "context": []}), 400

    try:
        # Forward to the new chat controller via internal request
        from blueprints.chat_controller import send_message as chat_send_message
        from flask import make_response
        
        # Create a mock request context
        with current_app.test_request_context(
            "/api/chat/send", 
            method="POST",
            data=json.dumps({
                "message": query,
                "language": language,
                "user_name": user_name
            }),
            headers={"Content-Type": "application/json"}
        ):
            # Copy the session data
            with current_app.test_client() as client:
                with client.session_transaction() as test_session:
                    test_session["chat_session_id"] = session_id
                
                # Call the new chat controller function
                response = chat_send_message()
                data = json.loads(response.get_data(as_text=True))
                
                # Convert the response format to match the old format
                return jsonify({
                    "answer": data.get("bot_response", {}).get("text", ""),
                    "context": [],  # Context format has changed in the new API
                })
    
    except Exception as e:
        current_app.logger.error(f"Error forwarding to chat controller: {str(e)}")
        return jsonify({
            "answer": "I'm sorry, but I encountered an error processing your question. Please try again later.",
            "context": [],
        }), 500


@main.route("/language", methods=["POST"])
def set_language():
    """Set the user's preferred language."""
    data = request.json
    language = data.get("language", "en")

    session_id = session.get("chat_session_id")
    if session_id:
        chat_session = ChatSession.query.filter_by(session_id=session_id).first()
        if chat_session:
            chat_session.language = language
            db.session.commit()

    return jsonify({"status": "success", "language": language})


@main.route("/chat-history")
def chat_history():
    """Redirect to the new chat history endpoint for backward compatibility."""
    # This function now redirects to the new chat controller endpoint
    # for backward compatibility with existing frontend code
    session_id = session.get("chat_session_id")
    if not session_id:
        return jsonify({"messages": []})
    
    try:
        # Forward to the new chat controller via internal request
        from blueprints.chat_controller import get_chat_history as chat_get_history
        
        # Create a mock request context
        with current_app.test_request_context(
            "/api/chat/history", 
            method="GET"
        ):
            # Copy the session data
            with current_app.test_client() as client:
                with client.session_transaction() as test_session:
                    test_session["chat_session_id"] = session_id
                
                # Call the new chat controller function
                response = chat_get_history()
                data = json.loads(response.get_data(as_text=True))
                
                # Return the response directly as it has the same format
                return jsonify(data)
    
    except Exception as e:
        current_app.logger.error(f"Error forwarding to chat history endpoint: {str(e)}")
        
        # Fallback to the original implementation if forwarding fails
        chat_session = ChatSession.query.filter_by(session_id=session_id).first()
        if not chat_session:
            return jsonify({"messages": []})

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

        return jsonify({"messages": message_list})
