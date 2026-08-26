import os
from datetime import timedelta
from flask import Flask
from flask_migrate import Migrate
from dotenv import load_dotenv

from extensions import db
from config import Config
from utils.helpers import get_cart_from_cookie, is_valid_product_id

load_dotenv()

app = Flask(__name__)
app.config.from_object(Config)

app.secret_key = os.environ.get("SECRET_KEY", "ecommerce_secret_key_2026_premium")
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=30)

db.init_app(app)
import models  # Import all models to register metadata before migrate
migrate = Migrate(app, db)

@app.context_processor
def inject_cart_count():
    cart = get_cart_from_cookie()
    total_qty = sum(qty for k, qty in cart.items() if is_valid_product_id(k))
    return {"cart_count": total_qty}

from front import front_bp
from admin import admin_bp
from auth import auth_bp

app.register_blueprint(front_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(auth_bp)

if __name__ == "__main__":
    app.run(debug=True)