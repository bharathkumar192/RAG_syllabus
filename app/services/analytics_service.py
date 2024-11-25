from datetime import datetime, timedelta
from sqlalchemy import func, desc, distinct
from app import db
from app.models.user import User
from app.models.chat import Chat
from app.models.syllabus import Syllabus
import logging
from collections import defaultdict
import time

logger = logging.getLogger(__name__)

class AnalyticsService:
    @staticmethod
    def get_user_activity(days=30):
        """Get user activity statistics for the specified number of days."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Get active users count
            active_users = db.session.query(
                func.date(Chat.timestamp).label('date'),
                func.count(distinct(Chat.user_id)).label('user_count')
            ).filter(Chat.timestamp >= cutoff_date)\
             .group_by(func.date(Chat.timestamp))\
             .all()
            
            # Get query count per day
            daily_queries = db.session.query(
                func.date(Chat.timestamp).label('date'),
                func.count(Chat.id).label('query_count')
            ).filter(Chat.timestamp >= cutoff_date)\
             .group_by(func.date(Chat.timestamp))\
             .all()
            
            return {
                'active_users': [(str(day.date), count) for day, count in active_users],
                'daily_queries': [(str(day.date), count) for day, count in daily_queries]
            }
        except Exception as e:
            logger.error(f"Error getting user activity: {str(e)}")
            return None

    @staticmethod
    def get_document_usage(days=30):
        """Get document usage statistics."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Get most accessed syllabi
            popular_docs = db.session.query(
                Syllabus.id,
                Syllabus.title,
                func.count(Chat.id).label('access_count')
            ).join(Chat)\
             .filter(Chat.timestamp >= cutoff_date)\
             .group_by(Syllabus.id)\
             .order_by(desc('access_count'))\
             .limit(10)\
             .all()
            
            # Get department-wise usage
            dept_usage = db.session.query(
                Syllabus.department,
                func.count(Chat.id).label('query_count')
            ).join(Chat)\
             .filter(Chat.timestamp >= cutoff_date)\
             .group_by(Syllabus.department)\
             .all()
            
            return {
                'popular_documents': [
                    {'title': doc.title, 'count': count} 
                    for doc, count in popular_docs
                ],
                'department_usage': [
                    {'department': dept, 'count': count} 
                    for dept, count in dept_usage
                ]
            }
        except Exception as e:
            logger.error(f"Error getting document usage: {str(e)}")
            return None

    @staticmethod
    def get_response_times(days=7):
        """Get average response times and performance metrics."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Get hourly average response times
            response_times = db.session.query(
                func.date_trunc('hour', Chat.timestamp).label('hour'),
                func.avg(Chat.response_time).label('avg_time')
            ).filter(Chat.timestamp >= cutoff_date)\
             .group_by('hour')\
             .order_by('hour')\
             .all()
            
            return {
                'response_times': [
                    {
                        'hour': hour.strftime('%Y-%m-%d %H:00'),
                        'avg_time': float(avg_time)
                    }
                    for hour, avg_time in response_times
                ]
            }
        except Exception as e:
            logger.error(f"Error getting response times: {str(e)}")
            return None

    @staticmethod
    def get_error_rates(days=7):
        """Get error rates and types."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Get error counts by type
            error_counts = db.session.query(
                Chat.error_type,
                func.count(Chat.id).label('error_count')
            ).filter(
                Chat.timestamp >= cutoff_date,
                Chat.error_type.isnot(None)
            ).group_by(Chat.error_type)\
             .all()
            
            return {
                'error_counts': [
                    {'type': error_type, 'count': count}
                    for error_type, count in error_counts
                ]
            }
        except Exception as e:
            logger.error(f"Error getting error rates: {str(e)}")
            return None