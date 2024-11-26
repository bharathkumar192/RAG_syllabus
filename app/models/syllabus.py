# from app import db
from app.extensions import db, bcrypt  # Use this instead of from app import db
from datetime import datetime

class Syllabus(db.Model):
    __tablename__ = 'syllabi'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # Updated to match User table name
    title = db.Column(db.String(200), nullable=False)
    department = db.Column(db.String(100))
    course_number = db.Column(db.String(20))
    file_path = db.Column(db.String(255), nullable=False)
    vector_store_id = db.Column(db.String(255))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    chats = db.relationship('Chat', backref='syllabus', lazy='dynamic')