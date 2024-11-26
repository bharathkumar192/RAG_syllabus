# app/errors.py
from flask import render_template
from flask import Blueprint, current_app
import logging
from logging.handlers import RotatingFileHandler
import os

errors = Blueprint('errors', __name__)

@errors.app_errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@errors.app_errorhandler(500)
def internal_error(error):
    # from app import db
    from app.extensions import db, bcrypt
    db.session.rollback()
    return render_template('errors/500.html'), 500

def init_logging(app):
    if not os.path.exists('logs'):
        os.mkdir('logs')
    
    # Set up file handler
    file_handler = RotatingFileHandler('logs/syllabus_chatbot.log', 
                                     maxBytes=10240, 
                                     backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)

    # Set up console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    app.logger.addHandler(console_handler)

    app.logger.setLevel(logging.INFO)
    app.logger.info('Syllabus Chatbot startup')