import pytest
from app.models.user import User
from flask_login import current_user

def test_home_redirect(client):
    response = client.get('/', follow_redirects=True)
    assert response.status_code == 200
    assert b'Login' in response.data

def test_login_page(client):
    response = client.get('/login')
    assert response.status_code == 200
    assert b'Login' in response.data

def test_register_page(client):
    response = client.get('/register')
    assert response.status_code == 200
    assert b'Register' in response.data

def test_login_success(client, test_user, session):
    response = client.post('/login', data={
        'username': test_user.username,
        'password': 'testpass',
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Dashboard' in response.data

def test_login_failure(client):
    response = client.post('/login', data={
        'username': 'wronguser',
        'password': 'wrongpass',
    }, follow_redirects=True)
    assert b'Invalid username or password' in response.data

def test_unauthorized_access(client):
    response = client.get('/teacher/dashboard', follow_redirects=True)
    assert response.status_code == 200
    assert b'Please log in' in response.data

def test_student_dashboard_access(client, test_user, session):
    # Login first
    response = client.post('/login', data={
        'username': 'testuser',
        'password': 'testpass'
    }, follow_redirects=True)
    assert response.status_code == 200
    
    # Then access dashboard
    response = client.get('/student/dashboard', follow_redirects=True)
    assert response.status_code == 200

def test_teacher_dashboard_access(client, test_teacher, session):
    # Login first
    response = client.post('/login', data={
        'username': 'testteacher',
        'password': 'teacherpass'
    }, follow_redirects=True)
    assert response.status_code == 200
    
    # Then access dashboard
    response = client.get('/teacher/dashboard', follow_redirects=True)
    assert response.status_code == 200
    assert b'Upload Syllabus' in response.data

def test_admin_dashboard_access(client, session):
    # Create admin user if not exists
    admin = User.query.filter_by(username='testadmin').first()
    if not admin:
        admin = User(
            username='testadmin',
            email='testadmin@example.com',
            role='admin',
            is_approved=True
        )
        admin.set_password('adminpass')
        session.add(admin)
        session.commit()
    
    # Login as admin
    response = client.post('/login', data={
        'username': 'testadmin',
        'password': 'adminpass'
    }, follow_redirects=True)
    assert response.status_code == 200
    
    # Access dashboard
    response = client.get('/admin/dashboard', follow_redirects=True)
    assert response.status_code == 200
    assert b'Pending Teacher Approvals' in response.data