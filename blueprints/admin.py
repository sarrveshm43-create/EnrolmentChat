import os
import uuid
import re
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, current_app, jsonify, send_from_directory
)
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models.database import db, User, Document, QueryLog, ChatSession
from models.rag_utils import RAGProcessor

admin = Blueprint('admin', __name__)

def is_valid_university_email(email):
    """Check if email is from a valid university domain"""
    # Add your university domain patterns here
    university_domains = ['msu.edu.my', 'management.msu.edu.my']
    pattern = r'^[a-zA-Z0-9._%+-]+@(?:' + '|'.join(university_domains) + ')$'
    return bool(re.match(pattern, email))

@admin.route('/login', methods=['GET', 'POST'])
def login():
    # If already logged in, redirect to admin index
    if current_user.is_authenticated:
        return redirect(url_for('admin.index'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # Validate input
        if not email or not password:
            flash('Please provide both email and password', 'danger')
            return render_template('admin/login.html')

        # Debug log
        current_app.logger.info(f"Login attempt for email: {email}")
        
        try:
            # Find user by email
            user = User.query.filter_by(email=email).first()

            # Check if user exists and password is correct
            if user and user.check_password(password):
                # Ensure user is active
                if not user.is_active:
                    flash('Your account is inactive. Please contact an administrator.', 'warning')
                    return render_template('admin/login.html')
                
                # Log in the user
                login_user(user, remember=True)
                
                # Update last login time
                user.last_login = datetime.utcnow()
                db.session.commit()
                
                current_app.logger.info(f"User logged in successfully: {email}")
                flash('Successfully logged in!', 'success')
                
                # Handle redirect
                next_page = request.args.get('next')
                if next_page and next_page != '/logout' and not next_page.startswith('//'):
                    return redirect(next_page)
                return redirect(url_for('admin.index'))
            
            # Invalid credentials
            current_app.logger.warning(f"Failed login attempt for email: {email}")
            flash('Invalid email or password', 'danger')
            
        except Exception as e:
            current_app.logger.error(f"Login error: {str(e)}")
            flash('An error occurred during login. Please try again.', 'danger')
        
    return render_template('admin/login.html')

@admin.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('admin.index'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')

        # Debug log
        current_app.logger.info(f"Signup attempt for email: {email}")

        # Validate input
        if not email or not password or not name:
            flash('Please fill in all fields', 'danger')
            return render_template('admin/signup.html')

        # For testing purposes, allow any email format
        # Comment this out to enforce university email validation
        # if not is_valid_university_email(email):
        #     flash('Please use a valid university email address', 'danger')
        #     return render_template('admin/signup.html')

        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return render_template('admin/signup.html')

        try:
            # Create new user with all required fields
            user = User(email=email, name=name, is_active=True)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            
            current_app.logger.info(f"User registered successfully: {email}")
            flash('Registration successful. Please login.', 'success')
            return redirect(url_for('admin.login'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating user: {str(e)}")
            flash(f'Registration failed: {str(e)}', 'danger')
            return render_template('admin/signup.html')

    return render_template('admin/signup.html')

@admin.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('admin.login'))


def allowed_file(filename):
    """Check if the file is an allowed type (PDF)."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() == "pdf"


@admin.route("/")
@login_required
def index():
    """Admin dashboard homepage."""
    # Gather some statistics for the dashboard
    document_count = db.session.query(Document).count()
    active_document_count = db.session.query(Document).filter_by(is_active=True).count()
    session_count = db.session.query(ChatSession).count()
    # Corrected query to avoid attribute conflict
    query_count = db.session.query(QueryLog).count()

    # Get the 5 most recent documents
    recent_documents = (
        db.session.query(Document).order_by(Document.upload_date.desc()).limit(5).all()
    )
    
    # Get the 10 most recent user queries
    recent_queries = (
        db.session.query(QueryLog).order_by(QueryLog.timestamp.desc()).limit(10).all()
    )

    return render_template(
        "admin/index.html",
        document_count=document_count,
        active_document_count=active_document_count,
        session_count=session_count,
        query_count=query_count,
        recent_documents=recent_documents,
        recent_queries=recent_queries,
    )


@admin.route("/documents")
@login_required
def list_documents():
    """List all documents in the system."""
    documents = db.session.query(Document).order_by(Document.upload_date.desc()).all()
    return render_template("admin/documents.html", documents=documents)


@admin.route("/documents/view/<filename>")
@login_required
def view_document(filename):
    """View a document's contents"""
    document = Document.query.filter_by(filename=filename).first_or_404()
    file_path = os.path.join(current_app.config['PDF_FOLDER'], filename)
    if os.path.exists(file_path):
        return send_from_directory(current_app.config['PDF_FOLDER'], filename)
    flash('Document file not found.', 'error')
    return redirect(url_for('admin.list_documents'))


@admin.route("/documents/manage/<filename>")
@login_required
def manage_document(filename):
    """Manage a document's settings"""
    document = Document.query.filter_by(filename=filename).first_or_404()
    return render_template('admin/manage_document.html', document=document)

@admin.route("/documents/update/<int:document_id>", methods=["POST"])
@login_required
def update_document(document_id):
    """Update document settings"""
    document = Document.query.get_or_404(document_id)
    
    document.description = request.form.get('description')
    document.category = request.form.get('category')
    document.language = request.form.get('language')
    document.is_active = 'is_active' in request.form
    
    try:
        db.session.commit()
        flash('Document settings updated successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error updating document settings.', 'error')
        current_app.logger.error(f'Error updating document {document_id}: {str(e)}')
    
    return redirect(url_for('admin.documents'))


@admin.route("/documents/upload", methods=["GET", "POST"])
@login_required
def upload_document():
    """Handle document uploads."""
    if request.method == "POST":
        # Check if a file was uploaded
        if "document" not in request.files:
            flash("No file selected", "danger")
            return redirect(request.url)

        file = request.files["document"]

        # If no file selected
        if file.filename == "":
            flash("No file selected", "danger")
            return redirect(request.url)

        # Check if file is allowed and process it
        if file and allowed_file(file.filename):
            # Secure the filename and generate a unique name
            original_filename = secure_filename(file.filename)
            filename = f"{uuid.uuid4().hex}__{original_filename}"

            # Get additional form data
            description = request.form.get("description", "")
            category = request.form.get("category", "")
            language = request.form.get("language", "en")

            # Save the file
            file_path = os.path.join(current_app.config["PDF_FOLDER"], filename)
            file.save(file_path)

            # Create a new document record
            document = Document(
                filename=filename,
                original_filename=original_filename,
                description=description,
                category=category,
                language=language,
                is_active=True,
            )

            db.session.add(document)
            db.session.commit()

            # Update the vector store with the new document
            try:
                # Instantiate RAGProcessor (now only needs Groq key)
                rag_processor = RAGProcessor(
                    groq_api_key=current_app.config.get("GROQ_API_KEY")
                )
                rag_processor.create_or_update_vector_store()
                flash(
                    "Document uploaded successfully and added to the knowledge base.",
                    "success",
                )
            except Exception as e:
                current_app.logger.error(f"Error updating vector store: {str(e)}")
                flash(
                    f"Document uploaded successfully, but there was an error updating the knowledge base: {str(e)}",
                    "warning",
                )

            return redirect(url_for("admin.list_documents"))

        flash("Invalid file type. Only PDF files are allowed.", "danger")
        return redirect(request.url)

    # GET request - display the upload form
    return render_template("admin/upload_document.html")


@admin.route("/documents/toggle/<int:document_id>", methods=["POST"])
@login_required
def toggle_document_status(document_id):
    """Toggle a document's active status."""
    document = db.session.get(Document, document_id)
    if not document:
        flash("Document not found.", "danger")
        return redirect(url_for("admin.list_documents"))

    document.is_active = not document.is_active
    db.session.commit()

    # Update the vector store
    try:
        # Instantiate RAGProcessor (now only needs Groq key)
        rag_processor = RAGProcessor(
            groq_api_key=current_app.config.get("GROQ_API_KEY")
        )
        rag_processor.create_or_update_vector_store()
    except Exception as e:
        current_app.logger.error(f"Error updating vector store: {str(e)}")

    status = "activated" if document.is_active else "deactivated"
    flash(f"Document {status} successfully.", "success")

    return redirect(url_for("admin.list_documents"))


@admin.route("/documents/delete/<int:document_id>", methods=["POST"])
@login_required
def delete_document(document_id):
    """Delete a document from the system."""
    document = db.session.get(Document, document_id)
    if not document:
        flash("Document not found.", "danger")
        return redirect(url_for("admin.list_documents"))

    # Delete the file
    file_path = os.path.join(current_app.config["PDF_FOLDER"], document.filename)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except OSError as e:
            current_app.logger.error(f"Error deleting file {file_path}: {e}")
            flash(f"Error deleting file: {e}", "danger")
            # Decide if you want to proceed with DB deletion or stop

    # Delete from database
    db.session.delete(document)
    db.session.commit()

    # Update the vector store
    try:
        # Instantiate RAGProcessor (now only needs Groq key)
        rag_processor = RAGProcessor(
            groq_api_key=current_app.config.get("GROQ_API_KEY")
        )
        rag_processor.create_or_update_vector_store()
    except Exception as e:
        current_app.logger.error(f"Error updating vector store: {str(e)}")

    flash("Document deleted successfully.", "success")
    return redirect(url_for("admin.list_documents"))


@admin.route("/stats")
@login_required
def stats():
    """View system statistics."""
    # Query statistics
    # Corrected query to avoid attribute conflict
    total_queries = db.session.query(QueryLog).count()

    # Group queries by day
    from sqlalchemy import func

    query_by_day = (
        db.session.query(
            func.date(QueryLog.timestamp).label("date"), func.count().label("count")
        )
        .group_by("date")
        .order_by("date")
        .all()
    )

    # Average processing time
    avg_processing_time = (
        db.session.query(func.avg(QueryLog.processed_time)).scalar() or 0
    )

    # Sessions
    total_sessions = db.session.query(ChatSession).count()
    active_sessions = (
        db.session.query(ChatSession).filter(ChatSession.end_time.is_(None)).count()
    )

    # Prepare data for JSON serialization (convert Row objects to dicts)
    query_data_for_chart = [
        {"date": row.date, "count": row.count} for row in query_by_day
    ]

    return render_template(
        "admin/stats.html",
        total_queries=total_queries,
        query_by_day=query_data_for_chart,  # Pass the JSON-serializable list
        avg_processing_time=avg_processing_time,
        total_sessions=total_sessions,
        active_sessions=active_sessions,
    )


@admin.route("/rebuild-vectorstore", methods=["POST"])
@login_required
def rebuild_vectorstore():
    """Rebuild the vector store from all active documents in the database."""
    try:
        # Query active documents from the database
        active_documents = Document.query.filter_by(is_active=True).all()
        if not active_documents:
            flash("No active documents found in the database to build the knowledge base.", "warning")
            return redirect(url_for("admin.index"))

        # Extract file paths
        file_paths = [
            os.path.join(current_app.config["PDF_FOLDER"], doc.filename)
            for doc in active_documents
            if doc.filename and os.path.exists(os.path.join(current_app.config["PDF_FOLDER"], doc.filename))
        ]

        if not file_paths:
            flash(
                "Active documents found, but their file paths are missing or invalid. Cannot build knowledge base.",
                "danger",
            )
            return redirect(url_for("admin.index"))

        current_app.logger.info(f"Found {len(file_paths)} valid document paths to process.")

        # Instantiate RAGProcessor
        rag_processor = RAGProcessor(
            groq_api_key=current_app.config.get("GROQ_API_KEY")
        )

        # Pass the list of file paths to the updated function
        success = rag_processor.create_or_update_vector_store(file_paths)

        if success:
            flash("Knowledge base rebuilt successfully from active documents.", "success")
        else:
            flash(
                "Processing started, but no valid content could be extracted from the documents.",
                "warning",
            )

    except Exception as e:
        current_app.logger.error(f"Error rebuilding vector store: {str(e)}", exc_info=True)
        flash(f"Error rebuilding knowledge base: {str(e)}", "danger")

    return redirect(url_for("admin.index"))
