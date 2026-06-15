from flask import Flask, render_template, request, redirect, url_for, make_response, session, flash, jsonify
import json
import random
import os
import secrets
import requests as http_requests
from datetime import datetime, timedelta
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from product import products

# Load environment variables from .env (if present)
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'ecommerce_secret_key_2026_premium')

products_data = products

# ── Telegram configuration ────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID   = os.environ.get('TELEGRAM_CHAT_ID', '')


def send_telegram_message(message: str) -> bool:
    """
    Send a plain-text message to a Telegram chat via the Bot API.
    Returns True on success, False on any failure.
    Errors are logged to the terminal but never raised to the caller.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print('[Telegram] WARNING: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is not set. Message not sent.')
        return False
    try:
        url  = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
        data = {
            'chat_id':    TELEGRAM_CHAT_ID,
            'text':       message,
            'parse_mode': 'HTML',
        }
        resp = http_requests.post(url, data=data, timeout=10)
        if resp.status_code == 200:
            return True
        print(f'[Telegram] ERROR: API returned {resp.status_code} — {resp.text}')
    except Exception as e:
        print(f'[Telegram] EXCEPTION: {e}')
    return False

# JSON file storage for user persistence
USERS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'users.json')

def load_users():
    if not os.path.exists(USERS_FILE):
        return []
    try:
        with open(USERS_FILE, 'r') as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            return []
    except Exception:
        return []

def save_users(users):
    os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=4)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def get_cart_from_cookie():
    cart_cookie = request.cookies.get('cart')
    if not cart_cookie:
        return {}
    try:
        cart = json.loads(cart_cookie)
        if isinstance(cart, dict):
            cleaned_cart = {}
            for k, v in cart.items():
                if is_valid_product_id(k):
                    try:
                        quantity = int(v)
                        if quantity > 0:
                            cleaned_cart[str(k)] = quantity
                    except (ValueError, TypeError):
                        continue
            return cleaned_cart
    except Exception:
        pass
    return {}


def save_cart_to_cookie(response, cart):
    response.set_cookie(
        'cart',
        json.dumps(cart),
        max_age=2592000,  # 30 days
        httponly=True,
        samesite='Lax'
    )
    return response


def is_valid_product_id(product_id):
    try:
        pid = int(product_id)
        return any(p['id'] == pid for p in products_data)
    except (ValueError, TypeError):
        return False


@app.context_processor
def inject_cart_count():
    cart = get_cart_from_cookie()
    total_qty = 0
    for product_id_str, qty in cart.items():
        if is_valid_product_id(product_id_str):
            total_qty += qty
    return {'cart_count': total_qty}


@app.get("/")
def home():
    return render_template('front/index.html', featured_products=products_data[:9])


@app.get("/products")
def products_route():
    page = request.args.get('page', 1, type=int)
    per_page = 12

    total_products = len(products_data)
    total_pages = (total_products + per_page - 1) // per_page

    start_index = (page - 1) * per_page
    end_index = start_index + per_page
    paginated_products = products_data[start_index:end_index]

    return render_template(
        'front/products.html',
        products=paginated_products,
        current_page=page,
        total_pages=total_pages
    )

@app.get("/categories")
def categories():
    unique_categories = list(set(p['category'] for p in products_data))

    categories_list = []
    for cat in unique_categories:
        count = sum(1 for p in products_data if p['category'] == cat)
        categories_list.append({
            "name": cat,
            "count": count
        })

    selected_category = request.args.get('cat')

    if selected_category:
        filtered_products = [p for p in products_data if p['category'] == selected_category]
    else:
        filtered_products = products_data

    return render_template(
        'front/category.html',
        categories=categories_list,
        products=filtered_products,
        selected_category=selected_category
    )


@app.get("/about")
def about():
    return render_template('front/about.html')


@app.get('/product/<int:id>')
def product(id):
    product_item = next((p for p in products_data if p['id'] == id), None)

    related_items = []
    if product_item:
        related_items = [p for p in products_data if p['category'] == product_item['category'] and p['id'] != id]

    # Retrieve current quantity in cart to display in detail page
    cart = get_cart_from_cookie()
    current_qty = cart.get(str(id), 0)

    return render_template(
        'front/product.html',
        product=product_item,
        related_products=related_items[:4],
        current_qty=current_qty
    )


@app.get('/cart')
def cart():
    cart_data = get_cart_from_cookie()
    cart_items = []
    total = 0.0

    for product_id_str, qty in cart_data.items():
        try:
            pid = int(product_id_str)
        except ValueError:
            continue

        product_item = next((p for p in products_data if p['id'] == pid), None)
        if product_item:
            price = float(product_item.get('price', 0))
            subtotal = price * qty
            cart_items.append({
                'product': product_item,
                'quantity': qty,
                'subtotal': subtotal
            })
            total += subtotal

    return render_template('front/cart.html', cart_items=cart_items, total=total)


@app.post('/add_to_cart/<int:id>')
def add_to_cart(id):
    if not is_valid_product_id(id):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'status': 'error', 'message': 'Invalid product'}), 400
        return redirect(url_for('cart'))

    cart = get_cart_from_cookie()
    quantity = request.form.get('quantity', 1, type=int)
    if quantity <= 0:
        quantity = 1

    key = str(id)
    cart[key] = cart.get(key, 0) + quantity

    product_item = next((p for p in products_data if p['id'] == id), None)
    title = product_item['title'] if product_item else "Product"

    # AJAX request from product detail page — return JSON, don't redirect
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        response = make_response(jsonify({'status': 'success', 'message': f"'{title}' added to cart!", 'cart_qty': sum(cart.values())}), 200)
        return save_cart_to_cookie(response, cart)

    flash(f"'{title}' added to cart successfully!", 'success')
    response = redirect(url_for('cart'))
    return save_cart_to_cookie(response, cart)


@app.post('/remove_from_cart/<int:id>')
def remove_from_cart(id):
    cart = get_cart_from_cookie()
    key = str(id)
    product_item = next((p for p in products_data if p['id'] == id), None)
    title = product_item['title'] if product_item else "Product"

    if key in cart:
        del cart[key]
        flash(f"Removed '{title}' from cart.", 'success')

    response = redirect(url_for('cart'))
    return save_cart_to_cookie(response, cart)


@app.post('/update_cart/<int:id>')
def update_cart(id):
    if not is_valid_product_id(id):
        return redirect(url_for('cart'))

    cart = get_cart_from_cookie()
    key = str(id)

    if key in cart:
        action = request.form.get('action')
        quantity = request.form.get('quantity', type=int)
        product_item = next((p for p in products_data if p['id'] == id), None)
        title = product_item['title'] if product_item else "Product"

        if action == 'increase':
            cart[key] += 1
            flash(f"Increased quantity of '{title}'.", 'success')
        elif action == 'decrease':
            if cart[key] > 1:
                cart[key] -= 1
                flash(f"Decreased quantity of '{title}'.", 'success')
            else:
                flash(f"Quantity of '{title}' cannot be less than 1. Use the remove button to delete it.", 'warning')
        elif quantity is not None:
            if quantity <= 0:
                cart[key] = 1
                flash(f"Quantity must be at least 1.", 'warning')
            else:
                cart[key] = quantity
                flash(f"Updated quantity of '{title}' to {quantity}.", 'success')

    response = redirect(url_for('cart'))
    return save_cart_to_cookie(response, cart)


@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    # ── Build cart summary (shared by GET and POST) ───────────────────────────
    cart_data  = get_cart_from_cookie()
    cart_items = []
    total      = 0.0

    for product_id_str, qty in cart_data.items():
        try:
            pid = int(product_id_str)
        except ValueError:
            continue
        product_item = next((p for p in products_data if p['id'] == pid), None)
        if product_item:
            price    = float(product_item.get('price', 0))
            subtotal = price * qty
            cart_items.append({
                'product':  product_item,
                'quantity': qty,
                'subtotal': subtotal,
            })
            total += subtotal

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        phone     = request.form.get('phone', '').strip()
        address   = request.form.get('address', '').strip()
        notes     = request.form.get('notes', '').strip()

        # ── Validation ────────────────────────────────────────────────────────
        errors = []
        if not cart_items:
            errors.append('Your cart is empty. Add items before checking out.')
        if not full_name:
            errors.append('Full Name is required.')
        if not phone:
            errors.append('Phone Number is required.')
        if not address:
            errors.append('Delivery Address is required.')

        if errors:
            for err in errors:
                flash(err, 'danger')
            return render_template('front/checkout.html',
                                   cart_items=cart_items, total=total,
                                   form_full_name=full_name, form_phone=phone,
                                   form_address=address, form_notes=notes)

        # ── Build Telegram order message ──────────────────────────────────────
        order_time    = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        products_lines = '\n'.join(
            f"  • {item['product']['title']} x{item['quantity']}  —  ${item['subtotal']:.2f}"
            for item in cart_items
        )
        tax       = total * 0.08
        grand     = total + tax

        telegram_text = (
            f"🛒 <b>NEW ORDER</b>\n"
            f"{'═' * 32}\n\n"
            f"👤 <b>Customer:</b> {full_name}\n"
            f"📞 <b>Phone:</b> {phone}\n"
            f"📍 <b>Address:</b> {address}\n"
            f"📝 <b>Notes:</b> {notes if notes else '—'}\n\n"
            f"🛍 <b>Products:</b>\n{products_lines}\n\n"
            f"💰 <b>Subtotal:</b> ${total:.2f}\n"
            f"🧾 <b>Tax (8%):</b> ${tax:.2f}\n"
            f"✅ <b>Grand Total:</b> ${grand:.2f}\n\n"
            f"🕐 <b>Order Time:</b> {order_time}"
        )

        telegram_ok = send_telegram_message(telegram_text)
        if not telegram_ok:
            print(f'[Checkout] Telegram notification failed for order by {full_name} ({phone}). '
                  f'Order time: {order_time}')

        # ── Always succeed — clear cart and redirect ───────────────────────────
        flash('order_success', 'checkout_success')
        response = make_response(redirect(url_for('home')))
        # Clear cart cookie
        response.set_cookie('cart', '', max_age=0, expires=0)
        return response

    return render_template('front/checkout.html', cart_items=cart_items, total=total)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('account'))
    if request.method == 'POST':
        email_or_username = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        
        if not email_or_username or not password:
            flash('Please enter email/username and password.', 'danger')
            return render_template('front/login.html')
            
        users = load_users()
        authenticated_user = None
        
        for u in users:
            if u['email'].lower() == email_or_username.lower() or u['username'].lower() == email_or_username.lower():
                if check_password_hash(u['password_hash'], password):
                    authenticated_user = u
                    break
                    
        if authenticated_user:
            session['user_id'] = authenticated_user['id']
            session['username'] = authenticated_user['username']
            flash(f"Welcome back, {authenticated_user['username']}!", 'success')
            return redirect(url_for('account'))
        else:
            flash('Invalid email/username or password.', 'danger')
            return render_template('front/login.html')
            
    return render_template('front/login.html')


@app.route('/create-user', methods=['GET', 'POST'])
def create_user():
    if 'user_id' in session:
        return redirect(url_for('account'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validations
        if not username or not email or not password:
            flash('All fields are required.', 'danger')
            return render_template('front/create-user.html')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('front/create-user.html')
            
        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return render_template('front/create-user.html')
            
        users = load_users()
        # Check if username or email already exists
        for u in users:
            if u['username'].lower() == username.lower():
                flash('Username already registered.', 'danger')
                return render_template('front/create-user.html')
            if u['email'].lower() == email.lower():
                flash('Email address already registered.', 'danger')
                return render_template('front/create-user.html')
                
        # Register user
        user_id = secrets.token_hex(8)
        new_user = {
            'id': user_id,
            'username': username,
            'email': email,
            'password_hash': generate_password_hash(password),
            'reset_token': None,
            'reset_token_expiry': None
        }
        users.append(new_user)
        save_users(users)
        
        flash('Account created successfully! Please sign in.', 'success')
        return redirect(url_for('login'))
        
    return render_template('front/create-user.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been signed out.', 'success')
    return redirect(url_for('login'))


@app.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    users = load_users()
    user_id = session['user_id']
    user = None
    user_index = -1
    for i, u in enumerate(users):
        if u['id'] == user_id:
            user = u
            user_index = i
            break
    
    if not user:
        session.clear()
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        new_password = request.form.get('new_password', '')
        confirm_new_password = request.form.get('confirm_new_password', '')
        current_password = request.form.get('current_password', '')
        
        if not username or not email or not current_password:
            flash('Username, Email and Current Password are required.', 'danger')
            return render_template('front/account.html', user=user)
            
        # Verify current password
        if not check_password_hash(user['password_hash'], current_password):
            flash('Incorrect current password.', 'danger')
            return render_template('front/account.html', user=user)
            
        # Check for username or email duplicates
        for u in users:
            if u['id'] != user_id:
                if u['username'].lower() == username.lower():
                    flash('Username already taken.', 'danger')
                    return render_template('front/account.html', user=user)
                if u['email'].lower() == email.lower():
                    flash('Email address already registered.', 'danger')
                    return render_template('front/account.html', user=user)
                    
        # Verify new password if entered
        if new_password:
            if len(new_password) < 6:
                flash('New password must be at least 6 characters long.', 'danger')
                return render_template('front/account.html', user=user)
            if new_password != confirm_new_password:
                flash('New passwords do not match.', 'danger')
                return render_template('front/account.html', user=user)
            user['password_hash'] = generate_password_hash(new_password)
            
        # Save updates
        user['username'] = username
        user['email'] = email
        users[user_index] = user
        save_users(users)
        
        session['username'] = username
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('account'))
        
    return render_template('front/account.html', user=user)


@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        if not email:
            flash('Please enter your email address.', 'danger')
            return render_template('front/forgot-password.html')
            
        users = load_users()
        user_index = -1
        for i, u in enumerate(users):
            if u['email'].lower() == email.lower():
                user_index = i
                break
                
        if user_index != -1:
            # Generate reset token valid for 30 minutes
            token = secrets.token_urlsafe(32)
            expiry = datetime.now() + timedelta(minutes=30)
            users[user_index]['reset_token'] = token
            users[user_index]['reset_token_expiry'] = expiry.isoformat()
            save_users(users)
            
            # Since this is a database-free/no-email mock, we display/flash the reset link on the UI
            reset_link = url_for('reset_password', token=token, _external=True)
            flash(f'Reset link generated successfully! <br><br><strong>Link:</strong> <a href="{reset_link}" class="alert-link">{reset_link}</a>', 'success')
            print(f"\n====================================\nPASSWORD RESET LINK:\n{reset_link}\n====================================\n")
        else:
            flash('Email address not found.', 'danger')
            
    return render_template('front/forgot-password.html')


@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    users = load_users()
    user_index = -1
    
    # Find user by token
    for i, u in enumerate(users):
        if u.get('reset_token') == token:
            user_index = i
            break
            
    if user_index == -1:
        flash('Invalid or expired reset token.', 'danger')
        return redirect(url_for('forgot_password'))
        
    # Check expiry
    user_data = users[user_index]
    expiry_str = user_data.get('reset_token_expiry')
    if expiry_str:
        expiry = datetime.fromisoformat(expiry_str)
        if datetime.now() > expiry:
            flash('Reset token has expired.', 'danger')
            return redirect(url_for('forgot_password'))
            
    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        if not password or len(password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return render_template('front/reset-password.html', token=token)
            
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('front/reset-password.html', token=token)
            
        # Update user password
        users[user_index]['password_hash'] = generate_password_hash(password)
        users[user_index]['reset_token'] = None
        users[user_index]['reset_token_expiry'] = None
        save_users(users)
        
        flash('Password reset successfully! Please sign in with your new password.', 'success')
        return redirect(url_for('login'))
        
    return render_template('front/reset-password.html', token=token)


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name    = request.form.get('name', '').strip()
        email   = request.form.get('email', '').strip()
        subject = request.form.get('subject', '').strip()
        message = request.form.get('message', '').strip()

        # ── Server-side validation ────────────────────────────────────────
        errors = []
        if not name:
            errors.append('Name is required.')
        if not email:
            errors.append('Email is required.')
        elif '@' not in email or '.' not in email.split('@')[-1]:
            errors.append('Please enter a valid email address.')
        if not subject:
            errors.append('Subject is required.')
        if not message:
            errors.append('Message is required.')

        if errors:
            for err in errors:
                flash(err, 'danger')
            return render_template('front/contact.html',
                                   form_name=name, form_email=email,
                                   form_subject=subject, form_message=message)

        # ── Build Telegram message ────────────────────────────────────────
        telegram_text = (
            f"📩 <b>New Contact Message</b>\n"
            f"{'─' * 30}\n"
            f"👤 <b>Name:</b> {name}\n"
            f"📧 <b>Email:</b> {email}\n"
            f"📌 <b>Subject:</b> {subject}\n"
            f"💬 <b>Message:</b>\n{message}"
        )

        telegram_ok = send_telegram_message(telegram_text)

        if telegram_ok:
            flash('Your message has been sent successfully! We will get back to you soon.', 'contact_success')
        else:
            # Still show success to the user even if Telegram failed
            flash('Your message has been received! We will get back to you soon.', 'contact_success')
            print(f'[Contact] Telegram delivery failed for message from {email}. '
                  f'Subject: {subject}')

        return redirect(url_for('contact'))

    return render_template('front/contact.html')


@app.get('/test')
def test():
    test_products = ["Coca", "Pepsi", "Fanta"]
    name = "coca"
    hour = 6

    return render_template(
        'test.html',
        products=test_products,
        name=name,
        hour=hour,
    )


@app.get('/test_template')
def test_template():
    for item in products:
        item['qty'] = random.randint(1, 100)
        item['discount_pct'] = random.randint(0, 100)
        item['title'] = item.get('title', '')[:20]

    return render_template(
        'test_template.html',
        products=products
    )


if __name__ == '__main__':
    app.run(debug=True)