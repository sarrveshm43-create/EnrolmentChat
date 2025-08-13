from app import app
from models.database import db, User

def create_admin_user():
    """Create an admin user for testing login"""
    with app.app_context():
        try:
            # Check if admin user already exists
            admin = User.query.filter_by(email='admin@msu.edu.my').first()
            if not admin:
                # Create a new admin user with all required fields
                user = User(
                    email='admin@msu.edu.my',
                    name='Admin User',
                    is_active=True
                )
                user.set_password('admin123')
                db.session.add(user)
                db.session.commit()
                print('Admin user created successfully')
            else:
                # Update existing admin user
                admin.name = 'Admin User'
                admin.is_active = True
                admin.set_password('admin123')
                db.session.commit()
                print('Admin user updated successfully')
                
            # Verify the user exists and can be loaded
            admin = User.query.filter_by(email='admin@msu.edu.my').first()
            if admin and admin.check_password('admin123'):
                print('Admin user verified successfully')
                print(f'User ID: {admin.get_id()}')
                print(f'Is Active: {admin.is_active}')
            else:
                print('Error: Admin user verification failed')
                
        except Exception as e:
            print(f'Error creating/updating admin user: {str(e)}')
            db.session.rollback()

if __name__ == '__main__':
    create_admin_user()
