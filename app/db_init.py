# app/db_init.py
from app import create_app, db
from app.models.user import User

def init_db():
    app = create_app()
    with app.app_context():
        # Create all tables
        db.create_all()

        # Check if admin user exists
        admin = User.query.filter_by(role='admin').first()
        if not admin:
            admin = User(
                username='admin',
                email='admin@example.com',
                role='admin',
                is_approved=True
            )
            admin.set_password('admin123')  # Change this password in production
            db.session.add(admin)
            db.session.commit()
            print("Admin user created successfully!")

if __name__ == '__main__':
    init_db()