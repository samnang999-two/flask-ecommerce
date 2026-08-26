from flask import Blueprint

admin_bp = Blueprint(
    "admin",
    __name__,
    url_prefix="/admin"
)

from .dashboard import admin_dashboard_bp
from .user import admin_user_bp

admin_bp.register_blueprint(admin_dashboard_bp)
admin_bp.register_blueprint(admin_user_bp)