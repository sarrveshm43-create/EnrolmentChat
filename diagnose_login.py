from app import app
from models.database import db, User
from flask_login import LoginManager, login_user
import sys

def diagnose_login_issues():
    """Diagnose login issues by checking user accounts and login functionality"""
    with app.app_context():
        try:
            print("\n===== DIAGNOSING LOGIN ISSUES =====")
            
            # Check if any users exist
            users = User.query.all()
            print(f"Total users in database: {len(users)}")
            
            for user in users:
                print(f"\nUser ID: {user.id}")
                print(f"Email: {user.email}")
                print(f"Name: {user.name}")
                print(f"Is Active: {user.is_active}")
                print(f"Password Hash: {user.password_hash[:20]}...")
                
                # Test password verification
                test_password = "admin123"
                password_check = user.check_password(test_password)
                print(f"Password 'admin123' check: {password_check}")
                
                # Test login_user function
                login_manager = LoginManager()
                login_manager.init_app(app)
                
                @login_manager.user_loader
                def load_user(user_id):
                    return User.query.get(int(user_id))
                
                try:
                    result = login_user(user)
                    print(f"login_user function result: {result}")
                except Exception as e:
                    print(f"Error with login_user function: {str(e)}")
            
            # If no users, create a new admin
            if len(users) == 0:
                print("\nNo users found. Creating a new admin user...")
                create_admin_user()
            
            # Fix any issues found
            fix_login_issues()
            
        except Exception as e:
            print(f"Error during diagnosis: {str(e)}")

def create_admin_user():
    """Create a new admin user with known credentials"""
    try:
        # Create a new admin user with all required fields
        admin = User(
            email='admin@msu.edu.my',
            name='Admin User',
            is_active=True
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print("Admin user created successfully")
        
        # Verify the user exists
        admin = User.query.filter_by(email='admin@msu.edu.my').first()
        if admin:
            print(f"Admin user verified with ID: {admin.id}")
        else:
            print("Failed to verify admin user after creation")
    except Exception as e:
        print(f"Error creating admin user: {str(e)}")
        db.session.rollback()

def fix_login_issues():
    """Fix common login issues"""
    try:
        # 1. Update login_view in app.py
        print("\n===== FIXING LOGIN ISSUES =====")
        
        # 2. Ensure all users have is_active=True
        inactive_users = User.query.filter_by(is_active=False).all()
        if inactive_users:
            print(f"Found {len(inactive_users)} inactive users. Activating them...")
            for user in inactive_users:
                user.is_active = True
                print(f"Activated user: {user.email}")
            db.session.commit()
        else:
            print("No inactive users found.")
        
        # 3. Reset admin password
        admin = User.query.filter_by(email='admin@msu.edu.my').first()
        if admin:
            admin.set_password('admin123')
            db.session.commit()
            print("Reset admin password to 'admin123'")
        
        print("Login fixes applied successfully")
        
    except Exception as e:
        print(f"Error fixing login issues: {str(e)}")
        db.session.rollback()

if __name__ == '__main__':
    diagnose_login_issues()
