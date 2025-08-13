"""
Chat controller module for MSU Enrollment Advisor Bot.
Handles API endpoints and request processing for the chat functionality.
"""
import json
import uuid
from datetime import datetime
from flask import Blueprint, jsonify, request, session
from http import HTTPStatus
from flask import current_app
from models.database import db, ChatSession, ChatMessage, QueryLog
from blueprints.langchain_setup import process_query
from blueprints.chat_nlp import detect_context

# Create blueprint
chat_bp = Blueprint("chat", __name__, url_prefix="/api/chat")


def get_or_create_session(language='en'):
    """Helper function to get or create a chat session."""
    session_id = session.get('chat_session_id')
    if not session_id:
        session_id = str(datetime.utcnow().timestamp())
        session['chat_session_id'] = session_id
        session.modified = True

    chat_session = ChatSession.query.filter_by(session_id=session_id).first()
    if not chat_session:
        chat_session = ChatSession(
            session_id=session_id,
            user_ip=request.remote_addr,
            language=language
        )
        db.session.add(chat_session)
        db.session.commit()

    return chat_session


@chat_bp.route('/initialize', methods=['POST'])
def initialize_chat():
    """Initialize a new chat session."""
    try:
        # Get language from request
        data = request.get_json()
        if data is None:
            return jsonify({
                'status': 'error',
                'message': 'Invalid JSON data'
            }), 400

        language = data.get('language', 'en')

        # Create new session if one doesn't exist
        if 'chat_session_id' not in session:
            session_id = str(uuid.uuid4())
            chat_session = ChatSession(
                session_id=session_id,
                user_ip=request.remote_addr,
                language=language
            )
            db.session.add(chat_session)
            db.session.commit()
            session['chat_session_id'] = session_id
            current_app.logger.info(f'Created new chat session: {session_id}')
        else:
            # Update existing session language
            session_id = session['chat_session_id']
            chat_session = ChatSession.query.filter_by(session_id=session_id).first()
            if chat_session:
                chat_session.language = language
                db.session.commit()
                current_app.logger.info(f'Updated chat session: {session_id}')
            else:
                # Session ID exists in cookie but not in database, create new
                session_id = str(uuid.uuid4())
                chat_session = ChatSession(
                    session_id=session_id,
                    user_ip=request.remote_addr,
                    language=language
                )
                db.session.add(chat_session)
                db.session.commit()
                session['chat_session_id'] = session_id
                current_app.logger.info(f'Recreated missing chat session: {session_id}')

        return jsonify({
            'status': 'success',
            'session_id': session['chat_session_id']
        })

    except Exception as e:
        current_app.logger.error(f'Error initializing chat session: {str(e)}')
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@chat_bp.route("/send", methods=["POST"])
def send_message():
    """Process user message and return AI response with strict language enforcement.
    
    Expected JSON payload:
    {
        "message": "User question here",
        "language": "en" (language code)
    }
    
    Returns:
    {
        "bot_response": {
            "text": "AI response",
            "tone": "friendly",
            "intent": "answer",
            "suggestion_mode": false
        },
        "context_retained": true
    }
    """
    # Define fallback messages for different languages
    fallback_messages = {
        'en': 'I understand your question about MSU. Could you please rephrase that? I\'m here to help with information about programs, admissions, and campus life.',
        'es': 'Entiendo su pregunta sobre MSU. ¿Podría reformularla? Estoy aquí para ayudar con información sobre programas, admisiones y vida universitaria.',
        'zh': '我理解您有关于MSU的问题。您能换个方式问吗？我可以为您提供有关课程、入学和校园生活的信息。',
        'ms': 'Saya faham soalan anda tentang MSU. Bolehkah anda nyatakan semula? Saya di sini untuk membantu dengan maklumat tentang program, kemasukan, dan kehidupan kampus.'
    }
    
    # Define welcome messages for different languages
    welcome_messages = {
        'en': 'Welcome to MSU Enrollment Assistant! How can I help you today?',
        'es': '¡Bienvenido al Asistente de Inscripción de MSU! ¿Cómo puedo ayudarte hoy?',
        'zh': '欢迎使用MSU招生助手！今天我能为您提供什么帮助？',
        'ms': 'Selamat datang ke Pembantu Pendaftaran MSU! Bagaimana saya boleh membantu anda hari ini?'
    }
    
    try:
        # Get request data
        data = request.get_json()
        if data is None:
            return jsonify({
                'status': 'error',
                'message': 'Invalid JSON data'
            }), 400

        user_input = data.get('message', '').strip()
        language = data.get('language', 'en')
        
        # Validate inputs and enforce language
        valid_languages = ['en', 'es', 'zh', 'ms']
        if not language or language not in valid_languages:
            language = 'en'  # Default to English if not specified or invalid
        
        # STRICT LANGUAGE ENFORCEMENT - Store in session for consistent enforcement
        session['selected_language'] = language
        
        # Log the language being used
        current_app.logger.info(f"STRICT ENFORCEMENT: Using language: {language}")
        
        # Handle empty user input with language-specific response
        if not user_input:
            return jsonify({
                "bot_response": {
                    "text": fallback_messages.get(language, fallback_messages['en']),
                    "tone": "friendly",
                    "intent": "clarification",
                    "suggestion_mode": True,
                    "language": language  # Include language in response for frontend
                },
                "context_retained": True
            })

        # Get or create chat session
        chat_session = get_or_create_session(language)
        
        # Store user message in database
        user_message = ChatMessage(
            session_id=chat_session.id,
            message=user_input,
            is_user=True,
            original_language=language,
            timestamp=datetime.utcnow()
        )
        db.session.add(user_message)
        db.session.commit()
        
        # Get chat history for context
        previous_messages = ChatMessage.query.filter_by(session_id=chat_session.id).order_by(ChatMessage.timestamp).limit(10).all()
        
        # Format chat history for the LLM
        chat_history = []
        for msg in previous_messages:
            role = "Human" if msg.is_user else "Assistant"
            chat_history.append(f"{role}: {msg.message}")
        
        try:
            # Process query with strict language enforcement and chat history
            result = process_query(user_input, language=language, chat_history=chat_history)
            
            # Extract answer from result
            if isinstance(result, dict):
                answer = result.get('answer', '')
                context_docs = result.get('context', [])
                processing_time = result.get('processing_time', 0)
            else:
                # Fallback if result is not a dict
                answer = str(result) if result else ''
                context_docs = []
                processing_time = 0
            
            # Ensure we have a valid answer
            if not answer or len(answer.strip()) == 0:
                answer = fallback_messages.get(language, fallback_messages['en'])
            
            # Store bot response in database
            bot_message = ChatMessage(
                session_id=chat_session.id,
                message=answer,
                is_user=False,
                original_language=language,
                timestamp=datetime.utcnow()
            )
            db.session.add(bot_message)
            db.session.commit()
            
            # Return formatted response with language information
            return jsonify({
                "bot_response": {
                    "text": answer,
                    "tone": "friendly",
                    "intent": "answer",
                    "suggestion_mode": False,
                    "language": language  # Include language in response for frontend
                },
                "context_retained": True
            })
            
        except Exception as processing_error:
            # Log the error but return a friendly message
            current_app.logger.warning(f"Query processing error: {str(processing_error)}")
            return jsonify({
                "bot_response": {
                    "text": fallback_messages.get(language, fallback_messages['en']),
                    "tone": "friendly",
                    "intent": "clarification",
                    "suggestion_mode": True,
                    "language": language  # Include language in response for frontend
                },
                "context_retained": True
            })
    
    except Exception as e:
        # Handle any other errors
        current_app.logger.error(f"Request handling error: {str(e)}")
        # Get language from session or default to English
        language = session.get('selected_language', 'en')
        
        return jsonify({
            "bot_response": {
                "text": welcome_messages.get(language, welcome_messages['en']),
                "tone": "friendly",
                "intent": "greeting",
                "suggestion_mode": True,
                "language": language  # Include language in response for frontend
            },
            "context_retained": False
        })


@chat_bp.route('/clear', methods=['POST'])
def clear_chat_history():
    """Clear the chat history for the current session."""
    try:
        # Get the current chat session ID
        session_id = session.get('chat_session_id')
        if not session_id:
            current_app.logger.warning('No chat session ID found when clearing history')
            return jsonify({
                'status': 'success', 
                'message': 'No active chat session to clear'
            }), HTTPStatus.OK

        # Find the chat session
        current_session = ChatSession.query.filter_by(session_id=session_id).first()
        if not current_session:
            current_app.logger.warning(f'No chat session found for ID: {session_id}')
            return jsonify({
                'status': 'success',
                'message': 'No chat history found for this session'
            }), HTTPStatus.OK

        try:
            # Clear messages for this session
            num_deleted = ChatMessage.query.filter_by(session_id=current_session.id).delete()
            db.session.commit()
            current_app.logger.info(f'Cleared {num_deleted} messages from session {session_id}')
        except Exception as db_error:
            db.session.rollback()
            raise Exception(f'Database error while clearing messages: {str(db_error)}')

        # Clear session data
        if 'chat_history' in session:
            session.pop('chat_history')
        session.modified = True

        return jsonify({
            'status': 'success',
            'message': f'Successfully cleared {num_deleted} messages'
        }), HTTPStatus.OK

    except Exception as e:
        current_app.logger.error(f'Error clearing chat history: {str(e)}')
        return jsonify({
            'status': 'error', 
            'message': f'Failed to clear chat history: {str(e)}'
        }), HTTPStatus.INTERNAL_SERVER_ERROR

@chat_bp.route("/history", methods=["GET"])
def get_chat_history():
    """
    Get the chat history for the current session.
    
    Returns:
    {
        "messages": [
            {
                "id": 1,
                "content": "Message content",
                "is_user": true/false,
                "timestamp": "ISO timestamp"
            },
            ...
        ]
    }
    """
    session_id = session.get("chat_session_id")
    if not session_id:
        return jsonify({"messages": []})

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
            "intent": detect_context(msg.message).get("intent") if msg.is_user else "response"
        }
        for msg in messages
    ]

    return jsonify({"messages": message_list})


@chat_bp.route("/language", methods=["POST"])
def set_preferred_language():
    """
    Set the user's preferred language.
    
    Expected JSON payload:
    {
        "language": "en" (language code)
    }
    """
    data = request.json
    language = data.get("language", "en")
    
    # Validate language
    valid_languages = ['en', 'es', 'zh', 'ms']
    if language not in valid_languages:
        language = "en"  # Default to English if invalid
    
    # STRICT LANGUAGE ENFORCEMENT - Store in session
    session['selected_language'] = language
    current_app.logger.info(f"STRICT ENFORCEMENT: Language set to {language}")

    # Update database record
    session_id = session.get("chat_session_id")
    if session_id:
        chat_session = ChatSession.query.filter_by(session_id=session_id).first()
        if chat_session:
            chat_session.language = language
            db.session.commit()
            current_app.logger.info(f"Updated language for session {session_id} to {language}")

    # Return language-specific welcome message
    welcome_message = welcome_messages.get(language, welcome_messages['en'])
    
    return jsonify({
        "status": "success", 
        "language": language,
        "welcome_message": welcome_message
    })
