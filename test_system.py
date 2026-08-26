import unittest
from flask import Flask
from werkzeug.security import generate_password_hash

from extensions import db
from models.user import User
from front import front_bp
from admin import admin_bp
from auth import auth_bp
from utils.helpers import get_cart_from_cookie, is_valid_product_id

# 1. Create a dedicated isolated test Flask application
test_app = Flask(__name__)
test_app.config['TESTING'] = True
test_app.config['WTF_CSRF_ENABLED'] = False
test_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
test_app.secret_key = 'test_secret_key'

# 2. Register context processors and blue prints
@test_app.context_processor
def inject_cart_count():
    cart = get_cart_from_cookie()
    total_qty = sum(qty for k, qty in cart.items() if is_valid_product_id(k))
    return {"cart_count": total_qty}

db.init_app(test_app)
test_app.register_blueprint(front_bp)
test_app.register_blueprint(admin_bp)
test_app.register_blueprint(auth_bp)

class SystemTestCase(unittest.TestCase):
    def setUp(self):
        # Establish application context for the test
        self.app_context = test_app.app_context()
        self.app_context.push()
        self.client = test_app.test_client()
        
        # Only operate on the in-memory database
        db.create_all()
        
        self.admin = User(username='admin', email='admin@example.com', password=generate_password_hash('admin123'), role='Admin')
        self.vendor = User(username='vendor', email='vendor@example.com', password=generate_password_hash('vendor123'), role='Vendor')
        self.customer = User(username='customer', email='customer@example.com', password=generate_password_hash('customer123'), role='Customer')
        db.session.add_all([self.admin, self.vendor, self.customer])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_guest_restrictions(self):
        resp = self.client.get('/admin/dashboard')
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/login', resp.location)

        resp = self.client.get('/admin/users')
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/login', resp.location)

        resp = self.client.post('/add_to_cart/1', follow_redirects=True)
        self.assertIn(b'Please login first', resp.data)

        resp = self.client.get('/wishlist/1', follow_redirects=True)
        self.assertIn(b'Please login first', resp.data)

        resp = self.client.get('/checkout', follow_redirects=True)
        self.assertIn(b'Please login first', resp.data)

    def test_admin_flow(self):
        resp = self.client.post('/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
        self.assertIn(b'admin', resp.data)
        
        resp = self.client.get('/admin/dashboard')
        self.assertEqual(resp.status_code, 200)

        resp = self.client.get('/admin/users')
        self.assertEqual(resp.status_code, 200)

    def test_vendor_flow(self):
        resp = self.client.post('/login', data={'username': 'vendor', 'password': 'vendor123'}, follow_redirects=True)
        self.assertIn(b'vendor', resp.data)

        resp = self.client.get('/admin/dashboard')
        self.assertEqual(resp.status_code, 200)

        resp = self.client.get('/admin/users', follow_redirects=True)
        self.assertIn(b'Vendors are not allowed', resp.data)

    def test_customer_flow(self):
        resp = self.client.post('/login', data={'username': 'customer', 'password': 'customer123'}, follow_redirects=True)
        self.assertIn(b'customer', resp.data)

        resp = self.client.get('/admin/dashboard', follow_redirects=True)
        self.assertIn(b'Access Denied', resp.data)

        resp = self.client.post('/add_to_cart/1', data={'quantity': 1}, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

    def test_registration_flow(self):
        resp = self.client.post('/register', data={
            'username': 'newcustomer',
            'email': 'newcustomer@example.com',
            'password': 'password123',
            'confirm_password': 'password123'
        }, follow_redirects=True)
        self.assertIn(b'Registration successful', resp.data)
        
        u = User.query.filter_by(username='newcustomer').first()
        self.assertIsNotNone(u)
        self.assertEqual(u.role, 'Customer')

if __name__ == '__main__':
    unittest.main()


