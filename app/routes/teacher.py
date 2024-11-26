from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from app.models.syllabus import Syllabus
# from app import db
from app.extensions import db, bcrypt  # Use this instead of from app import db
from app.forms.teacher_forms import SyllabusUploadForm
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from functools import wraps
from app.routes.admin import admin_required
from app.services.pdf_service import process_pdf
from sqlalchemy import func, distinct
from flask import jsonify, send_from_directory
from app.models.chat import Chat
from app.models.user import User
import traceback
from flask import jsonify
from sqlalchemy import func
import logging

logger = logging.getLogger(__name__)


teacher_bp = Blueprint('teacher', __name__)
admin_bp = Blueprint('admin', __name__)

def teacher_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'teacher':
            flash('You need to be a teacher to access this page.', 'error')
            return redirect(url_for('main.index'))
        if not current_user.is_approved:
            flash('Your account is pending approval.', 'warning')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

@teacher_bp.route('/teacher/dashboard')
@login_required
@teacher_required
def dashboard():
    syllabi = Syllabus.query.filter_by(user_id=current_user.id).all()
    upload_form = SyllabusUploadForm()
    return render_template('teacher/dashboard.html', 
                         syllabi=syllabi,
                         upload_form=upload_form)

@teacher_bp.route('/teacher/upload_syllabus', methods=['POST'])
@login_required
@teacher_required
def upload_syllabus():
    form = SyllabusUploadForm()
    if form.validate_on_submit():
        try:
            # Save the PDF file
            file = form.syllabus_file.data
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            unique_filename = f"{timestamp}_{filename}"
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
            
            # Ensure upload directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Log file details
            current_app.logger.info(f"Attempting to save file: {unique_filename}")
            current_app.logger.info(f"File path: {file_path}")
            
            file.save(file_path)
            
            # Verify file was saved
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Failed to save file at {file_path}")
            
            # Create syllabus record
            syllabus = Syllabus(
                user_id=current_user.id,
                title=form.title.data,
                department=form.department.data,
                course_number=form.course_number.data,
                file_path=unique_filename
            )
            
            # Add to session but don't commit yet
            db.session.add(syllabus)
            db.session.flush()  # This assigns an ID to syllabus without committing
            
            current_app.logger.info(f"Processing PDF for syllabus ID: {syllabus.id}")
            
            # Process PDF and generate embeddings
            process_pdf(syllabus)
            
            # If we get here, processing was successful
            db.session.commit()
            current_app.logger.info(f"Successfully processed and saved syllabus ID: {syllabus.id}")
            
            flash('Syllabus uploaded successfully!', 'success')
            
        except FileNotFoundError as e:
            db.session.rollback()
            error_msg = str(e)
            current_app.logger.error(f"File error: {error_msg}")
            current_app.logger.error(f"Traceback: {traceback.format_exc()}")
            flash(f'Error saving file: {error_msg}', 'error')
            
        except Exception as e:
            db.session.rollback()
            # Get the full error traceback
            error_traceback = traceback.format_exc()
            current_app.logger.error(f"Error uploading syllabus: {str(e)}")
            current_app.logger.error(f"Full traceback: {error_traceback}")
            
            # Provide more specific error message to user
            error_type = type(e).__name__
            error_msg = str(e)
            flash(f'Error uploading syllabus ({error_type}): {error_msg}. Please try again.', 'error')
            
            # Clean up file if it was saved
            if 'file_path' in locals() and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    current_app.logger.info(f"Cleaned up file after error: {file_path}")
                except Exception as cleanup_error:
                    current_app.logger.error(f"Error cleaning up file: {str(cleanup_error)}")
    
    else:
        # Log form validation errors
        current_app.logger.error(f"Form validation errors: {form.errors}")
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{field}: {error}', 'error')
    
    return redirect(url_for('teacher.dashboard'))

@teacher_bp.route('/teacher/delete_syllabus/<int:syllabus_id>', methods=['POST'])
@login_required
@teacher_required
def delete_syllabus(syllabus_id):
    syllabus = Syllabus.query.get_or_404(syllabus_id)
    if syllabus.user_id != current_user.id:
        flash('You do not have permission to delete this syllabus.', 'error')
        return redirect(url_for('teacher.dashboard'))
    
    try:
        # Delete the file
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], syllabus.file_path)
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Delete from database
        db.session.delete(syllabus)
        db.session.commit()
        flash('Syllabus deleted successfully!', 'success')
    except Exception as e:
        current_app.logger.error(f"Error deleting syllabus: {str(e)}")
        flash('Error deleting syllabus. Please try again.', 'error')
    
    return redirect(url_for('teacher.dashboard'))


@teacher_bp.route('/teacher/syllabus/<int:syllabus_id>')
@login_required
@teacher_required
def get_syllabus_details(syllabus_id):
    try:
        syllabus = Syllabus.query.get_or_404(syllabus_id)
        
        if syllabus.user_id != current_user.id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Get statistics with error handling
        total_views = db.session.query(func.count(distinct(Chat.user_id)))\
            .filter(Chat.syllabus_id == syllabus_id).scalar() or 0
        total_questions = db.session.query(func.count(Chat.id))\
            .filter(Chat.syllabus_id == syllabus_id).scalar() or 0
        
        print("=========file content=========")
        print({
            'id': syllabus.id,
            'title': syllabus.title,
            'department': syllabus.department,
            'course_number': syllabus.course_number,
            'uploaded_at': syllabus.uploaded_at.isoformat(),
            'status': 'active' if syllabus.vector_store_id else 'processing',
            'stats': {
                'views': total_views,
                'questions': total_questions,
                'avg_response_time': '0s'  # You can add actual calculation later
            }
        })
        
        return jsonify({
            'id': syllabus.id,
            'title': syllabus.title,
            'department': syllabus.department,
            'course_number': syllabus.course_number,
            'uploaded_at': syllabus.uploaded_at.isoformat(),
            'status': 'active' if syllabus.vector_store_id else 'processing',
            'stats': {
                'views': total_views,
                'questions': total_questions,
                'avg_response_time': '0s'  # You can add actual calculation later
            }
        })
    except Exception as e:
        current_app.logger.error(f"Error getting syllabus details: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@teacher_bp.route('/teacher/download/<int:syllabus_id>')
@login_required
@teacher_required
def download_syllabus(syllabus_id):
    syllabus = Syllabus.query.get_or_404(syllabus_id)
    
    if syllabus.user_id != current_user.id:
        flash('Unauthorized access.', 'error')
        return redirect(url_for('teacher.dashboard'))

    try:
        # Get the absolute path to the upload folder
        upload_dir = os.path.abspath(current_app.config['UPLOAD_FOLDER'])
        
        # Log the paths for debugging
        current_app.logger.info(f"Upload directory: {upload_dir}")
        current_app.logger.info(f"File path: {syllabus.file_path}")
        current_app.logger.info(f"Full file path: {os.path.join(upload_dir, syllabus.file_path)}")
        
        # Verify file exists
        if not os.path.exists(os.path.join(upload_dir, syllabus.file_path)):
            raise FileNotFoundError(f"File not found: {syllabus.file_path}")

        # Get directory and filename
        directory = os.path.dirname(upload_dir)
        filename = os.path.basename(syllabus.file_path)
        
        return send_from_directory(
            directory=upload_dir,
            path=filename,
            as_attachment=True,
            download_name=f"{syllabus.course_number}_{syllabus.title}.pdf"
        )
    except Exception as e:
        current_app.logger.error(f"Error downloading syllabus: {str(e)}")
        current_app.logger.error(f"Upload folder: {current_app.config['UPLOAD_FOLDER']}")
        current_app.logger.error(f"File path: {syllabus.file_path}")
        current_app.logger.error(f"Working directory: {os.getcwd()}")
        flash('Error downloading file.', 'error')
        return redirect(url_for('teacher.dashboard'))
    

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('You need to be an admin to access this page.', 'error')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/teacher/<int:teacher_id>')
@login_required
@admin_required
def get_teacher_details(teacher_id):
    try:
        logger.info(f"Fetching details for teacher ID: {teacher_id}")
        teacher = User.query.get_or_404(teacher_id)
        
        # Verify this is a teacher account
        if teacher.role != 'teacher':
            logger.warning(f"Attempted to get teacher details for non-teacher user ID: {teacher_id}")
            return jsonify({'error': 'Not a teacher account'}), 400
            
        # Get statistics
        total_courses = db.session.query(func.count(Syllabus.id))\
            .filter(Syllabus.user_id == teacher_id).scalar() or 0
            
        active_students = db.session.query(func.count(distinct(Chat.user_id)))\
            .join(Syllabus)\
            .filter(Syllabus.user_id == teacher_id).scalar() or 0
            
        total_queries = db.session.query(func.count(Chat.id))\
            .join(Syllabus)\
            .filter(Syllabus.user_id == teacher_id).scalar() or 0
            
        # Get courses
        courses = [{
            'title': syllabus.title,
            'department': syllabus.department,
            'uploaded_at': syllabus.uploaded_at.isoformat(),
            'vector_store_id': syllabus.vector_store_id
        } for syllabus in teacher.syllabi]
        
        response_data = {
            'id': teacher.id,
            'username': teacher.username,
            'email': teacher.email,
            'is_approved': teacher.is_approved,
            'created_at': teacher.created_at.isoformat(),
            'last_login': teacher.last_login.isoformat() if teacher.last_login else None,
            'stats': {
                'total_courses': total_courses,
                'active_students': active_students,
                'total_queries': total_queries
            },
            'courses': courses
        }
        
        logger.info(f"Successfully retrieved details for teacher {teacher.username}")
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error getting teacher details: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500