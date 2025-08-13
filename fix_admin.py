from app import app
from models.database import db, User
from werkzeug.security import generate_password_hash
import os
import sys

def fix_admin_user():
    """Fix admin user account and ensure it works properly"""
    with app.app_context():
        try:
            print("\n===== FIXING ADMIN USER =====")
            
            # Check if admin user exists
            admin = User.query.filter_by(email='admin@msu.edu.my').first()
            
            if admin:
                print(f"Found existing admin user (ID: {admin.id})")
                
                # Update admin user with correct values
                admin.name = 'Admin User'
                admin.is_active = True
                # Force set password hash directly
                admin.password_hash = generate_password_hash('admin123')
                
                db.session.commit()
                print("Updated admin user successfully")
            else:
                print("Admin user not found. Creating new admin user...")
                
                # Create new admin user
                new_admin = User(
                    email='admin@msu.edu.my',
                    name='Admin User',
                    is_active=True,
                    password_hash=generate_password_hash('admin123')
                )
                
                db.session.add(new_admin)
                db.session.commit()
                print(f"Created new admin user with ID: {new_admin.id}")
            
            # Verify admin user
            admin = User.query.filter_by(email='admin@msu.edu.my').first()
            if admin and admin.check_password('admin123'):
                print("Admin user verified successfully")
                print(f"Email: {admin.email}")
                print(f"Password: admin123")
                print(f"Active: {admin.is_active}")
            else:
                print("ERROR: Admin user verification failed")
            
            # Create a test user
            test_user = User.query.filter_by(email='test@msu.edu.my').first()
            if not test_user:
                test_user = User(
                    email='test@msu.edu.my',
                    name='Test User',
                    is_active=True,
                    password_hash=generate_password_hash('test123')
                )
                db.session.add(test_user)
                db.session.commit()
                print(f"Created test user with ID: {test_user.id}")
                print("Test user credentials: test@msu.edu.my / test123")
            
        except Exception as e:
            print(f"Error fixing admin user: {str(e)}")
            db.session.rollback()

if __name__ == '__main__':
    fix_admin_user()
