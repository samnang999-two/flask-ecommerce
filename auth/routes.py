from flask import (
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash
)
from werkzeug.security import check_password_hash

from models.user import User
from . import auth_bp

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        role = session.get("role", "").lower()
        if role in ["admin", "administrator", "vendor"]:
            return redirect(url_for("admin.admin_dashboard.dashboard"))
        return redirect(url_for("front.front_auth.account"))

    if request.method == "POST":
        username = (request.form.get("username") or request.form.get("email") or "").strip()
        password = request.form.get("password", "")
        remember = request.form.get("remember")

        if not username:
            flash("Username or email is required.", "danger")
            return render_template("auth/login.html", username=username)

        if not password:
            flash("Password is required.", "danger")
            return render_template("auth/login.html", username=username)

        user = User.query.filter(
            User.username.ilike(username) | User.email.ilike(username)
        ).first()

        if not user or not check_password_hash(user.password, password):
            flash("Invalid username or password.", "danger")
            return render_template("auth/login.html", username=username)

        role = user.role or "Customer"

        session.clear()
        session.permanent = bool(remember)
        session["user_id"] = user.id
        session["username"] = user.username
        session["email"] = user.email
        session["role"] = role
        session["profile"] = user.profile

        flash(f"Welcome back, {user.username}!", "success")

        next_page = request.args.get("next") or request.form.get("next")

        if role.lower() in ["admin", "administrator", "vendor"]:
            if next_page and not next_page.startswith("http"):
                return redirect(next_page)
            return redirect(url_for("admin.admin_dashboard.dashboard"))

        # For Customer
        if next_page and not next_page.startswith("/admin") and not next_page.startswith("http"):
            return redirect(next_page)
        return redirect(url_for("front.front_auth.account"))

    return render_template("auth/login.html")

@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for("auth.login"))
