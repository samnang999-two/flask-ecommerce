import os
import uuid
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    current_app
)
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename

from extensions import db
from models.user import User
from utils.auth import admin_required

admin_user_bp = Blueprint(
    "admin_user",
    __name__
)

def save_profile_image(file):
    if not file or file.filename == "":
        return None

    original_filename = secure_filename(file.filename)
    extension = os.path.splitext(original_filename)[1].lower()
    allowed_extensions = {".jpg", ".jpeg", ".png", ".gif"}

    if extension not in allowed_extensions:
        return None

    filename = f"{uuid.uuid4().hex}{extension}"
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_folder, exist_ok=True)
    file.save(os.path.join(upload_folder, filename))

    return f"uploads/{filename}"

def delete_profile_image(profile_path):
    if not profile_path:
        return

    image_path = os.path.join(current_app.root_path, "static", profile_path)

    if os.path.exists(image_path):
        try:
            os.remove(image_path)
        except OSError:
            pass

@admin_user_bp.route("/users")
@admin_required
def index():
    user_list = User.query.all()
    return render_template("admin/user/index.html", users=user_list)

@admin_user_bp.route("/users/create", methods=["GET", "POST"])
@admin_required
def create():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        role = request.form.get("role", "Customer")

        if not username:
            flash("Username is required!", "danger")
            return redirect(request.url)

        if not email:
            flash("Email is required!", "danger")
            return redirect(request.url)

        if not password:
            flash("Password is required!", "danger")
            return redirect(request.url)

        if password != confirm_password:
            flash("Passwords do not match!", "danger")
            return redirect(request.url)

        existing_email = User.query.filter(db.func.lower(User.email) == email).first()
        if existing_email:
            flash(f'The email "{email}" is already registered!', "warning")
            return redirect(request.url)

        existing_username = User.query.filter(db.func.lower(User.username) == username.lower()).first()
        if existing_username:
            flash(f'The username "{username}" is already taken!', "warning")
            return redirect(request.url)

        profile_path = save_profile_image(request.files.get("avatar"))

        new_user = User(
            username=username,
            email=email,
            password=generate_password_hash(password),
            role=role,
            profile=profile_path
        )

        try:
            db.session.add(new_user)
            db.session.commit()
            flash(f'User "{username}" created successfully!', "success")
            return redirect(url_for("admin.admin_user.index"))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating user: {e}")
            delete_profile_image(profile_path)
            flash("An error occurred while creating the user.", "danger")
            return redirect(request.url)

    return render_template("admin/user/create.html")

@admin_user_bp.route("/users/edit/<int:id>", methods=["GET", "POST"])
@admin_required
def edit(id):
    user = User.query.get_or_404(id)

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        role = request.form.get("role")

        if not username:
            flash("Username is required!", "danger")
            return redirect(request.url)

        if not email:
            flash("Email is required!", "danger")
            return redirect(request.url)

        duplicate_username = User.query.filter(
            db.func.lower(User.username) == username.lower(),
            User.id != user.id
        ).first()

        if duplicate_username:
            flash(f'The username "{username}" is already taken!', "warning")
            return redirect(request.url)

        duplicate_email = User.query.filter(
            db.func.lower(User.email) == email,
            User.id != user.id
        ).first()

        if duplicate_email:
            flash(f'The email "{email}" is already registered!', "warning")
            return redirect(request.url)

        user.username = username
        user.email = email
        user.role = role

        file = request.files.get("avatar")
        if file and file.filename != "":
            old_profile = user.profile
            new_profile = save_profile_image(file)

            if new_profile:
                user.profile = new_profile
                delete_profile_image(old_profile)

        try:
            db.session.commit()
            flash(f'User "{username}" updated successfully!', "success")
            return redirect(url_for("admin.admin_user.index"))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating user: {e}")
            flash("Error updating user.", "danger")
            return redirect(request.url)

    return render_template("admin/user/edit.html", user=user)

@admin_user_bp.route("/user/delete/<int:id>", methods=["GET", "POST"])
@admin_required
def delete(id):
    user = User.query.get_or_404(id)

    if request.method == "POST":
        username = user.username
        profile_path = user.profile

        try:
            db.session.delete(user)
            db.session.commit()
            delete_profile_image(profile_path)
            flash(f'User "{username}" deleted successfully!', "success")
            return redirect(url_for("admin.admin_user.index"))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error deleting user: {e}")
            flash("Error deleting user.", "danger")
            return redirect(request.url)

    return render_template("admin/user/delete.html", user=user)