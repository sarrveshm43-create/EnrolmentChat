from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

# Initialize db here but configure it in app.py
db = SQLAlchemy()


class User(UserMixin, db.Model):
    """Model for university staff users"""
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        return str(self.id)

    def __repr__(self):
        return f'<User {self.email}>'


class Document(db.Model):
    """Model for PDF documents uploaded to the system"""

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(100), nullable=True)
    language = db.Column(db.String(20), default="en")
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f"<Document {self.original_filename}>"


class ChatSession(db.Model):
    """Model for tracking user chat sessions"""

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), unique=True, nullable=False)
    user_ip = db.Column(db.String(50), nullable=True)
    language = db.Column(db.String(20), default="en")
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime, nullable=True)
    messages = db.relationship("ChatMessage", backref="session", lazy=True)

    def __repr__(self):
        return f"<ChatSession {self.session_id}>"


class ChatMessage(db.Model):
    """Model for storing chat messages"""

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("chat_session.id"), nullable=False)
    is_user = db.Column(
        db.Boolean, default=True
    )  # True for user message, False for bot
    message = db.Column(db.Text, nullable=False)
    original_language = db.Column(db.String(20), default="en")
    translated_message = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        message_type = "User" if self.is_user else "Bot"
        return f"<{message_type}Message {self.id}>"


class QueryLog(db.Model):
    """Model for logging and analyzing user queries"""

    id = db.Column(db.Integer, primary_key=True)
    query = db.Column(db.Text, nullable=False)
    chat_message_id = db.Column(
        db.Integer, db.ForeignKey("chat_message.id"), nullable=True
    )
    language = db.Column(db.String(20), default="en")
    processed_time = db.Column(
        db.Float, nullable=True
    )  # Time taken to process in seconds
    response_length = db.Column(db.Integer, nullable=True)
    relevant_docs = db.Column(
        db.Text, nullable=True
    )  # JSON string of document IDs used
    query_metadata = db.Column(
        db.Text, nullable=True
    )  # JSON string of additional metadata like student profile
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<QueryLog {self.query[:20]}...>"
