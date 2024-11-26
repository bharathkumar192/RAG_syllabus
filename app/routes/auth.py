from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app.models.user import User
# from app import db
from app.extensions import db, bcrypt  # Use this instead of from app import db
from app.forms.auth_forms import RegistrationForm, LoginForm
from sqlalchemy.orm.session import Session
from datetime import datetime

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            role=form.role.data
        )
        user.set_password(form.password.data)
        
        # Automatically approve students, teachers need admin approval
        if form.role.data == 'student':
            user.is_approved = True
            
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html', form=form)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        try:
            # Query user and keep session active
            user = db.session.query(User).filter_by(username=form.username.data).first()
            
            if user and user.check_password(form.password.data):
                if not user.is_approved and user.role == 'teacher':
                    flash('Your account is pending admin approval.', 'warning')
                    return redirect(url_for('auth.login'))
                
                # Update last login time within the same session
                user.last_login = datetime.utcnow()
                db.session.add(user)
                db.session.commit()
                
                # Login user with the fresh session
                login_succeeded = login_user(user, remember=form.remember_me.data)
                
                if login_succeeded:
                    next_page = request.args.get('next')
                    return redirect(next_page or url_for('main.index'))
                else:
                    db.session.rollback()
                    flash('Error during login. Please try again.', 'error')
            else:
                flash('Invalid username or password', 'error')
        except Exception as e:
            current_app.logger.error(f"Login error: {str(e)}")
            db.session.rollback()
            flash('An error occurred during login. Please try again.', 'error')
    
    return render_template('auth/login.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    try:
        user = current_user
        logout_user()
        db.session.commit()
        flash('Successfully logged out.', 'success')
    except Exception as e:
        current_app.logger.error(f"Logout error: {str(e)}")
        db.session.rollback()
        flash('An error occurred during logout.', 'error')
    
    return redirect(url_for('auth.login'))