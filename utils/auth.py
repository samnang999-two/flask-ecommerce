from functools import wraps
from flask import session, redirect, url_for, flash, request


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in first.", "warning")
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in first.", "warning")
            return redirect(url_for("auth.login", next=request.path))

        role = session.get("role", "")
        role_lower = role.lower()

        if role_lower == "customer":
            flash("Access Denied. You do not have permission to access the admin area.", "danger")
            return redirect(url_for("front.front_auth.account"))

        if role_lower == "vendor":
            flash("Access Denied. Vendors are not allowed to manage users.", "danger")
            return redirect(url_for("admin.admin_dashboard.dashboard"))

        if role_lower not in ["admin", "administrator"]:
            flash("You do not have permission to access this page.", "danger")
            return redirect(url_for("auth.login"))

        return view(*args, **kwargs)

    return wrapped


def vendor_or_admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in first.", "warning")
            return redirect(url_for("auth.login", next=request.path))

        role = session.get("role", "")
        role_lower = role.lower()

        if role_lower == "customer":
            flash("Access Denied. You do not have permission to access the admin area.", "danger")
            return redirect(url_for("front.front_auth.account"))

        if role_lower not in ["admin", "administrator", "vendor"]:
            flash("You do not have permission to access this page.", "danger")
            return redirect(url_for("auth.login"))

        return view(*args, **kwargs)

    return wrapped
