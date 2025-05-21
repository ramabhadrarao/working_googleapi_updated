#!/usr/bin/env python3
import os
import sys
import datetime
from flask import Flask
from models import db, User

# Import app configuration
from config import config

def create_app(config_name='development'):
    """Create a minimal app for database operations."""
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    # Initialize database
    db.init_app(app)
    
    return app

def create_admin_user(app, username, email, password, first_name, last_name):
    """Create an admin user."""
    with app.app_context():
        # Check if the user already exists
        user = User.query.filter_by(email=email).first()
        if user:
            print(f"User with email {email} already exists.")
            # Refresh the user from the session to avoid detached instance error
            admin_details = {
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': user.role
            }
            return admin_details
        
        # Check if username is taken
        user = User.query.filter_by(username=username).first()
        if user:
            print(f"Username {username} is already taken.")
            return None
        
        # Create new admin user
        admin = User(
            username=username,
            email=email,
            password=password,  # This will be hashed by the User model
            first_name=first_name,
            last_name=last_name,
            role='admin',
            created_at=datetime.datetime.utcnow(),
            is_active=True
        )
        
        # Add to database
        db.session.add(admin)
        db.session.commit()
        
        print(f"Admin user '{username}' created successfully!")
        
        # Return user details as a dictionary to avoid detached instance issues
        admin_details = {
            'username': username,
            'email': email,
            'first_name': first_name,
            'last_name': last_name,
            'role': 'admin'
        }
        return admin_details

if __name__ == "__main__":
    # Default admin credentials
    default_username = "admin"
    default_email = "admin@routeanalytics.com"
    default_password = "admin123"  # Change this in production!
    default_first_name = "Admin"
    default_last_name = "User"
    
    # Allow overriding defaults from command line
    if len(sys.argv) > 1:
        default_username = sys.argv[1]
    if len(sys.argv) > 2:
        default_email = sys.argv[2]
    if len(sys.argv) > 3:
        default_password = sys.argv[3]
    if len(sys.argv) > 4:
        default_first_name = sys.argv[4]
    if len(sys.argv) > 5:
        default_last_name = sys.argv[5]
    
    # Create application
    env = os.getenv('FLASK_ENV', 'development')
    app = create_app(env)
    
    # Create tables if they don't exist
    with app.app_context():
        db.create_all()
    
    # Create admin user
    admin_details = create_admin_user(
        app,
        default_username,
        default_email,
        default_password,
        default_first_name,
        default_last_name
    )
    
    if admin_details:
        print("\nAdmin User Details:")
        print(f"Username: {admin_details['username']}")
        print(f"Email: {admin_details['email']}")
        print(f"First Name: {admin_details['first_name']}")
        print(f"Last Name: {admin_details['last_name']}")
        print(f"Role: {admin_details['role']}")
        print("\nUse these credentials to log in to the application.")
        print("IMPORTANT: Remember to change the default password in production!")