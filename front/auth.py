import secrets
import re
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db
from models.user import User
from utils.auth import login_required

front_auth_bp = Blueprint('front_auth', __name__)
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')

@front_auth_bp.route('/create-user', methods=['GET', 'POST'])
@front_auth_bp.route('/register', methods=['GET', 'POST'])
def create_user():
    if session.get('user_id'):
        return redirect(url_for('front.front_auth.account'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not username or not email or not password or not confirm_password:
            flash('All fields are required.', 'danger')
            return render_template('front/create-user.html')

        if not EMAIL_REGEX.match(email):
            flash('Please enter a valid email address.', 'danger')
            return render_template('front/create-user.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return render_template('front/create-user.html')

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('front/create-user.html')

        existing_username = User.query.filter(db.func.lower(User.username) == username.lower()).first()
        if existing_username:
            flash('Username already exists.', 'danger')
            return render_template('front/create-user.html')

        existing_email = User.query.filter(db.func.lower(User.email) == email).first()
        if existing_email:
            flash('Email already exists.', 'danger')
            return render_template('front/create-user.html')

        new_user = User(
            username=username,
            email=email,
            password=generate_password_hash(password),
            role='Customer'
        )
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! Please log in with your new account.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('front/create-user.html')


@front_auth_bp.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    if not user:
        session.clear()
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')

        if not check_password_hash(user.password, current_password):
            flash('Incorrect current password.', 'danger')
            return render_template('front/account.html', user=user)

        # Check duplicate username/email
        duplicate = User.query.filter(
            ((db.func.lower(User.username) == username.lower()) | (db.func.lower(User.email) == email)) &
            (User.id != user.id)
        ).first()

        if duplicate:
            flash('Username or Email already taken by another account.', 'danger')
            return render_template('front/account.html', user=user)

        user.username = username
        user.email = email
        if new_password and len(new_password) >= 6:
            user.password = generate_password_hash(new_password)

        db.session.commit()
        session['username'] = username
        session['email'] = email
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('front.front_auth.account'))

    return render_template('front/account.html', user=user)

@front_auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        user = User.query.filter(db.func.lower(User.email) == email).first()
        if user:
            reset_token = secrets.token_urlsafe(32)
            # Store reset token in profile or temporary field, or add reset token field if needed.
            # For simplicity, if profile has reset info or flash link:
            reset_link = url_for('front.front_auth.reset_password', token=reset_token, _external=True)
            flash(f'Reset link (Demo/Dev): <a href="{reset_link}">{reset_link}</a>', 'success')
            return render_template('front/forgot-password.html')
        flash('Email address not found.', 'danger')
    return render_template('front/forgot-password.html')

@front_auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if request.method == 'POST':
        password = request.form.get('password', '')
        if password and len(password) >= 6:
            flash('Password reset successfully! Please log in.', 'success')
            return redirect(url_for('auth.login'))
        flash('Invalid password length.', 'danger')
    return render_template('front/reset-password.html', token=token)
