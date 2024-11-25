# app/routes/student.py
from flask import Blueprint, render_template, jsonify, request, current_app, redirect, send_from_directory, flash, url_for
from flask_login import login_required, current_user
from app.models.syllabus import Syllabus
from app.models.chat import Chat
from app.services.chat_service import ChatService
from app.services.vector_store_service import VectorStoreService
from app import db
from functools import wraps
from sqlalchemy import or_
from flask import request

student_bp = Blueprint('student', __name__)

def student_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'student':
            flash('You need to be a student to access this page.', 'error')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function



@student_bp.route('/student/chat/<int:syllabus_id>')
@login_required
@student_required
def chat_view(syllabus_id):
    syllabus = Syllabus.query.get_or_404(syllabus_id)
    # Get chat history
    chat_history = Chat.query.filter_by(
        user_id=current_user.id,
        syllabus_id=syllabus_id
    ).order_by(Chat.timestamp.asc()).all()
    
    return render_template('student/chat.html', 
                         syllabus=syllabus,
                         chat_history=chat_history)

@student_bp.route('/student/chat/<int:syllabus_id>/send', methods=['POST'])
@login_required
@student_required
def send_message(syllabus_id):
    try:
        message = request.json.get('message')
        if not message:
            return jsonify({'error': 'Message is required'}), 400

        # Initialize services
        vector_store = VectorStoreService()
        chat_service = ChatService(vector_store)

        # Generate response
        result = chat_service.generate_response(
            user_id=current_user.id,
            syllabus_id=syllabus_id,
            message=message
        )

        return jsonify(result)

    except Exception as e:
        current_app.logger.error(f"Error processing message: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@student_bp.route('/student/chat/<int:syllabus_id>/history')
@login_required
@student_required
def get_chat_history(syllabus_id):
    chat_history = Chat.query.filter_by(
        user_id=current_user.id,
        syllabus_id=syllabus_id
    ).order_by(Chat.timestamp.asc()).all()
    
    return jsonify([{
        'id': chat.id,
        'message': chat.message,
        'response': chat.response,
        'timestamp': chat.timestamp.isoformat()
    } for chat in chat_history])



@student_bp.route('/student/dashboard')
@login_required
@student_required
def dashboard():
    page = request.args.get('page', 1, type=int)
    per_page = 9  # Number of syllabi per page
    search_query = request.args.get('search', '')
    department_filter = request.args.get('department', '')

    # Base query
    query = Syllabus.query.filter(Syllabus.vector_store_id.isnot(None))

    # Apply search if provided
    if search_query:
        search_filter = or_(
            Syllabus.title.ilike(f'%{search_query}%'),
            Syllabus.department.ilike(f'%{search_query}%'),
            Syllabus.course_number.ilike(f'%{search_query}%')
        )
        query = query.filter(search_filter)

    # Apply department filter if provided
    if department_filter:
        query = query.filter(Syllabus.department == department_filter)

    # Get unique departments for filter dropdown
    departments = db.session.query(Syllabus.department)\
        .distinct()\
        .order_by(Syllabus.department)\
        .all()

    # Paginate results
    pagination = query.order_by(Syllabus.title).paginate(
        page=page, 
        per_page=per_page,
        error_out=False
    )
    syllabi = pagination.items

    return render_template('student/dashboard.html',
                         syllabi=syllabi,
                         pagination=pagination,
                         departments=departments,
                         search_query=search_query,
                         department_filter=department_filter)


@student_bp.route('/student/syllabus/<int:syllabus_id>/view')
@login_required
@student_required
def view_pdf(syllabus_id):
    syllabus = Syllabus.query.get_or_404(syllabus_id)
    return render_template('student/pdf_viewer.html', syllabus=syllabus)

@student_bp.route('/student/syllabus/<int:syllabus_id>/pdf')
@login_required
@student_required
def get_pdf(syllabus_id):
    syllabus = Syllabus.query.get_or_404(syllabus_id)
    try:
        return send_from_directory(
            current_app.config['UPLOAD_FOLDER'],
            syllabus.file_path,
            as_attachment=False
        )
    except Exception as e:
        current_app.logger.error(f"Error serving PDF: {str(e)}")
        flash('Error loading PDF.', 'error')
        return redirect(url_for('student.dashboard'))