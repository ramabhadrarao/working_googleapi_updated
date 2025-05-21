from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
from models import User, db
from datetime import datetime

# Create blueprint
auth = Blueprint('auth', __name__)

# Define forms
class LoginForm(FlaskForm):
    """User login form."""
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Log In')

class RegistrationForm(FlaskForm):
    """User registration form."""
    username = StringField('Username', validators=[DataRequired(), Length(3, 64)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(1, 64)])
    password = PasswordField('Password', validators=[DataRequired(), Length(8, 128)])
    password2 = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    first_name = StringField('First Name', validators=[DataRequired(), Length(1, 64)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(1, 64)])
    company = StringField('Company', validators=[Length(0, 128)])
    submit = SubmitField('Register')
    
    def validate_username(self, field):
        """Validate that the username is not already in use."""
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('Username already in use.')
    
    def validate_email(self, field):
        """Validate that the email is not already in use."""
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')

# Route: Login
@auth.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.verify_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            user.update_last_login()
            
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.index'))
        
        flash('Invalid email or password.', 'danger')
    
    return render_template('auth/login.html', form=form, title='Login')

# Route: Logout
@auth.route('/logout')
@login_required
def logout():
    """Handle user logout."""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

# Route: Register
@auth.route('/register', methods=['GET', 'POST'])
def register():
    """Handle user registration."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            password=form.password.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            company=form.company.data
        )
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html', form=form, title='Register')

# Route: Profile
@auth.route('/profile')
@login_required
def profile():
    """Display user profile."""
    return render_template('auth/profile.html', title='My Profile')

# Route: Change Password
@auth.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Handle password change."""
    class ChangePasswordForm(FlaskForm):
        current_password = PasswordField('Current Password', validators=[DataRequired()])
        new_password = PasswordField('New Password', validators=[
            DataRequired(), Length(8, 128)])
        confirm_password = PasswordField('Confirm New Password', validators=[
            DataRequired(), EqualTo('new_password')])
        submit = SubmitField('Change Password')
    
    form = ChangePasswordForm()
    
    if form.validate_on_submit():
        if current_user.verify_password(form.current_password.data):
            current_user.password = form.new_password.data
            db.session.commit()
            flash('Your password has been updated.', 'success')
            return redirect(url_for('auth.profile'))
        else:
            flash('Invalid current password.', 'danger')
    
    return render_template('auth/change_password.html', form=form, title='Change Password')