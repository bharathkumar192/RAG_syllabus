# from app import db
from app.extensions import db, bcrypt  # Use this instead of from app import db
from datetime import datetime

class Chat(db.Model):
    __tablename__ = 'chats'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    syllabus_id = db.Column(db.Integer, db.ForeignKey('syllabi.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    response = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    response_time = db.Column(db.Float)
    error_type = db.Column(db.String(50))