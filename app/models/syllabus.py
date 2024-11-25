# app/models/syllabus.py
from app import db
from datetime import datetime

class Syllabus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    department = db.Column(db.String(100))
    course_number = db.Column(db.String(20))
    file_path = db.Column(db.String(255), nullable=False)
    vector_store_id = db.Column(db.String(255))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    chats = db.relationship('Chat', backref='syllabus', lazy='dynamic')