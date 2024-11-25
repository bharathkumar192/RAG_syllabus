# app/routes/__init__.py
from .main import main_bp
from .auth import auth_bp
from .admin import admin_bp
from .teacher import teacher_bp
from .student import student_bp
from .monitoring import monitoring_bp

__all__ = ['main_bp', 'auth_bp', 'admin_bp', 'teacher_bp', 'student_bp', 'monitoring_bp']