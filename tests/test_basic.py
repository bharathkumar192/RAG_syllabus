from app.models.user import User

def test_app_creation(app):
    assert app is not None
    assert app.testing
    assert app.config['TESTING']

def test_client_creation(client):
    assert client is not None

def test_session_creation(session):
    assert session is not None
    
def test_db_operations(session):
    # Create a test user
    user = User(username="test", email="test@test.com", role="student")
    user.set_password("password")
    
    session.add(user)
    session.commit()
    
    # Query the user back
    retrieved_user = session.query(User).filter_by(username="test").first()
    assert retrieved_user is not None
    assert retrieved_user.username == "test"