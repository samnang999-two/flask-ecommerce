from flask import Blueprint
from front.store import front_store_bp
from front.auth import front_auth_bp

front_bp = Blueprint('front', __name__)

# Register Sub-blueprints ចូលក្នុង front_bp
front_bp.register_blueprint(front_store_bp)
front_bp.register_blueprint(front_auth_bp)