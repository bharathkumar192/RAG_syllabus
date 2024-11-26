# app/routes/admin.py
from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models.user import User
# from app import db
from app.extensions import db, bcrypt  # Use this instead of from app import db
from functools import wraps

admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('You need to be an admin to access this page.', 'error')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/admin/dashboard')
@login_required
@admin_required
def dashboard():
    pending_teachers = User.query.filter_by(role='teacher', is_approved=False).all()
    approved_teachers = User.query.filter_by(role='teacher', is_approved=True).all()
    return render_template('admin/dashboard.html', 
                         pending_teachers=pending_teachers,
                         approved_teachers=approved_teachers)

@admin_bp.route('/admin/approve/<int:user_id>')
@login_required
@admin_required
def approve_teacher(user_id):
    user = User.query.get_or_404(user_id)
    if user.role != 'teacher':
        flash('Only teacher accounts can be approved.', 'error')
        return redirect(url_for('admin.dashboard'))
    
    user.is_approved = True
    db.session.commit()
    flash(f'Teacher {user.username} has been approved.', 'success')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/admin/reject/<int:user_id>')
@login_required
@admin_required
def reject_teacher(user_id):
    user = User.query.get_or_404(user_id)
    if user.role != 'teacher':
        flash('Only teacher accounts can be rejected.', 'error')
        return redirect(url_for('admin.dashboard'))
    
    db.session.delete(user)
    db.session.commit()
    flash(f'Teacher account {user.username} has been rejected and removed.', 'success')
    return redirect(url_for('admin.dashboard'))