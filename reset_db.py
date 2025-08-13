from app import app
from models.database import db, User
import os

def reset_database():
    """Reset the database by dropping all tables and recreating them"""
    with app.app_context():
        try:
            # Drop all tables
            db.drop_all()
            print("All database tables dropped successfully")
            
            # Recreate all tables
            db.create_all()
            print("Database tables recreated successfully")
            
            # Create a fresh admin user
            admin = User(
                email='admin@msu.edu.my',
                name='Admin User',
                is_active=True
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("Fresh admin user created successfully")
            
            # Verify the admin user
            admin = User.query.filter_by(email='admin@msu.edu.my').first()
            if admin and admin.check_password('admin123'):
                print(f"Admin user verified: ID={admin.get_id()}, Email={admin.email}")
            else:
                print("Error: Admin user verification failed")
                
        except Exception as e:
            print(f"Error resetting database: {str(e)}")
            db.session.rollback()

if __name__ == '__main__':
    # Stop the server first
    print("Resetting the database...")
    reset_database()
    print("Database reset complete")
