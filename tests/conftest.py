import pytest
from app import create_app, db
from app.config import Config
from app.models.user import User

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    UPLOAD_FOLDER = 'tests/test_uploads'
    SECRET_KEY = 'test-secret-key'

@pytest.fixture(scope='function')
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture(scope='function')
def client(app):
    return app.test_client()

@pytest.fixture(scope='function')
def session(app):
    with app.app_context():
        connection = db.engine.connect()
        transaction = connection.begin()
        session = db.session
        yield session
        session.close()
        transaction.rollback()
        connection.close()

@pytest.fixture(scope='function')
def test_user(session):
    user = User(
        username='testuser',
        email='test@example.com',
        role='student',
        is_approved=True
    )
    user.set_password('testpass')
    session.add(user)
    session.commit()
    return user

@pytest.fixture(scope='function')
def test_teacher(session):
    teacher = User(
        username='testteacher',
        email='teacher@example.com',
        role='teacher',
        is_approved=True
    )
    teacher.set_password('teacherpass')
    session.add(teacher)
    session.commit()
    return teacher

@pytest.fixture(scope='function')
def clean_db(session):
    """Clean up the database before each test."""
    for table in reversed(db.metadata.sorted_tables):
        session.execute(table.delete())
    session.commit()