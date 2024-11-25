from flask import Blueprint, jsonify, current_app
from flask_login import login_required, current_user
from functools import wraps

monitoring_bp = Blueprint('monitoring', __name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            return jsonify({'error': 'Unauthorized'}), 403
        return f(*args, **kwargs)
    return decorated_function

@monitoring_bp.route('/monitoring/api-stats')
@login_required
@admin_required
def api_stats():
    """Get API monitoring statistics."""
    stats = current_app.api_monitor.get_stats()
    return jsonify(stats)

@monitoring_bp.route('/monitoring/system-stats')
@login_required
@admin_required
def system_stats():
    """Get system monitoring statistics."""
    current = current_app.system_monitor.get_current_stats()
    history = current_app.system_monitor.get_stats_history()
    return jsonify({
        'current': current,
        'history': history
    })