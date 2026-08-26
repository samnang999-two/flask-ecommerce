from flask import Blueprint, render_template
from utils.auth import vendor_or_admin_required

admin_dashboard_bp = Blueprint(
    "admin_dashboard",
    __name__
)

@admin_dashboard_bp.route("/")
@admin_dashboard_bp.route("/dashboard")
@vendor_or_admin_required
def dashboard():
    return render_template("admin/dashboard/index.html")
