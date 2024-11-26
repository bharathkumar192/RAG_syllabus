from app.models.user import User
from app.models.syllabus import Syllabus
from datetime import datetime

def test_new_user(test_db):
    """Test user creation."""
    user = User(
        username='testuser',
        email='test@example.com',
        role='student'
    )
    user.set_password('testpass')
    test_db.session.add(user)
    test_db.session.commit()

    assert user.username == 'testuser'
    assert user.email == 'test@example.com'
    assert user.role == 'student'
    assert user.check_password('testpass')
    assert not user.check_password('wrongpass')

def test_new_teacher(test_db):
    """Test teacher creation."""
    teacher = User(
        username='teacher',
        email='teacher@example.com',
        role='teacher',
        is_approved=False
    )
    teacher.set_password('teacherpass')
    test_db.session.add(teacher)
    test_db.session.commit()

    assert teacher.role == 'teacher'
    assert not teacher.is_approved

def test_new_syllabus(test_db, test_teacher):
    """Test syllabus creation."""
    syllabus = Syllabus(
        title='Test Course',
        department='CS',
        course_number='101',
        file_path='test.pdf',
        user_id=test_teacher.id
    )
    test_db.session.add(syllabus)
    test_db.session.commit()

    assert syllabus.title == 'Test Course'
    assert syllabus.department == 'CS'
    assert syllabus.user_id == test_teacher.id
    assert isinstance(syllabus.uploaded_at, datetime)