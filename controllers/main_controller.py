from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user

# Create blueprint
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Render the home page."""
    # If user is logged in, redirect to dashboard
    if current_user.is_authenticated:
        return redirect(url_for('route_bp.index'))
        
    # Otherwise show the landing page
    return render_template('index.html', title='Welcome to Route Analytics')

@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Render the main dashboard."""
    # Get recent routes for the current user
    from models import Route
    recent_routes = Route.query.filter_by(user_id=current_user.id).order_by(Route.created_at.desc()).limit(5).all()
    
    return render_template('dashboard.html', 
                          title='Dashboard',
                          recent_routes=recent_routes)

@main_bp.route('/about')
def about():
    """Render the about page."""
    return render_template('about.html', title='About Route Analytics')

@main_bp.route('/contact')
def contact():
    """Render the contact page."""
    return render_template('contact.html', title='Contact Us')

@main_bp.route('/help')
def help():
    """Render the help page."""
    return render_template('help.html', title='Help & Documentation')