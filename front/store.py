from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, make_response, session

from product import products as products_data
from utils.helpers import (
    is_valid_product_id, get_cart_from_cookie,
    save_cart_to_cookie, send_telegram_message
)

front_store_bp = Blueprint('front_store', __name__)


@front_store_bp.route("/")
def home():
    return render_template('front/index.html', featured_products=products_data[:9])


@front_store_bp.route("/products")
def products_route():
    page = request.args.get('page', 1, type=int)
    per_page = 12
    total_products = len(products_data)
    total_pages = (total_products + per_page - 1) // per_page
    paginated_products = products_data[(page - 1) * per_page: page * per_page]

    return render_template('front/products.html', products=paginated_products, current_page=page,
                           total_pages=total_pages)


@front_store_bp.route("/categories")
def categories():
    unique_categories = list(set(p['category'] for p in products_data if 'category' in p))
    categories_list = [{"name": cat, "count": sum(1 for p in products_data if p.get('category') == cat)} for cat in
                       unique_categories]
    selected_category = request.args.get('cat')
    filtered_products = [p for p in products_data if
                         p.get('category') == selected_category] if selected_category else products_data

    return render_template('front/category.html', categories=categories_list, products=filtered_products,
                           selected_category=selected_category)


@front_store_bp.route("/about")
def about():
    return render_template('front/about.html')


@front_store_bp.route('/product/<int:id>')
def product(id):
    product_item = next((p for p in products_data if p['id'] == id), None)
    if not product_item:
        flash("រកមិនឃើញផលិតផលនេះទេ!", "danger")
        return redirect(url_for('front.front_store.products_route'))

    related_items = [p for p in products_data if
                     p.get('category') == product_item.get('category') and p['id'] != id]
    cart = get_cart_from_cookie()
    return render_template('front/product.html', product=product_item, related_products=related_items[:4],
                           current_qty=cart.get(str(id), 0))


@front_store_bp.route('/cart')
def cart():
    if not session.get("user_id"):
        flash("Please login first to add products to your cart.", "warning")
        return redirect(url_for("auth.login", next=request.path))

    cart_data = get_cart_from_cookie()
    cart_items = []
    total = 0.0
    for product_id_str, qty in cart_data.items():
        if product_id_str.isdigit():
            product_item = next((p for p in products_data if p['id'] == int(product_id_str)), None)
            if product_item:
                subtotal = float(product_item.get('price', 0)) * qty
                cart_items.append({'product': product_item, 'quantity': qty, 'subtotal': subtotal})
                total += subtotal
    return render_template('front/cart.html', cart_items=cart_items, total=total)


@front_store_bp.route('/add_to_cart/<int:id>', methods=['POST'])
@front_store_bp.route('/add-to-cart/<int:id>', methods=['POST'])
def add_to_cart(id):
    if not session.get("user_id"):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'status': 'error',
                'message': 'Please login first to add products to your cart.',
                'redirect': url_for('auth.login', next=url_for('front.front_store.product', id=id))
            }), 401
        flash("Please login first to add products to your cart.", "warning")
        return redirect(url_for("auth.login", next=request.path))

    if not is_valid_product_id(id):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'status': 'error', 'message': 'Invalid product'}), 400
        flash("ផលិតផលមិនត្រឹមត្រូវ!", "danger")
        return redirect(url_for('front.front_store.cart'))

    cart = get_cart_from_cookie()
    quantity = max(1, request.form.get('quantity', 1, type=int))
    key = str(id)
    cart[key] = cart.get(key, 0) + quantity
    product_item = next((p for p in products_data if p['id'] == id), None)
    title = product_item['title'] if product_item else "Product"

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        response = make_response(
            jsonify({'status': 'success', 'message': f"'{title}' added to cart!", 'cart_qty': sum(cart.values())}), 200)
        return save_cart_to_cookie(response, cart)

    flash(f"បានបន្ថែម '{title}' ទៅក្នុងកន្ត្រកជោគជ័យ!", 'success')
    return save_cart_to_cookie(redirect(url_for('front.front_store.cart')), cart)


@front_store_bp.route('/remove_from_cart/<int:id>', methods=['POST'])
@front_store_bp.route('/remove-from-cart/<int:id>', methods=['POST'])
def remove_from_cart(id):
    if not session.get("user_id"):
        flash("Please login first to add products to your cart.", "warning")
        return redirect(url_for("auth.login", next=request.path))

    cart = get_cart_from_cookie()
    key = str(id)
    if key in cart:
        del cart[key]
        flash("បានលុបផលិតផលចេញពីកន្ត្រក។", 'success')
    return save_cart_to_cookie(redirect(url_for('front.front_store.cart')), cart)


@front_store_bp.route('/update_cart/<int:id>', methods=['POST'])
@front_store_bp.route('/update-cart/<int:id>', methods=['POST'])
def update_cart(id):
    if not session.get("user_id"):
        flash("Please login first to add products to your cart.", "warning")
        return redirect(url_for("auth.login", next=request.path))

    if not is_valid_product_id(id):
        return redirect(url_for('front.front_store.cart'))

    cart = get_cart_from_cookie()
    key = str(id)
    if key in cart:
        action = request.form.get('action')
        quantity = request.form.get('quantity', type=int)
        if action == 'increase':
            cart[key] += 1
        elif action == 'decrease':
            cart[key] = max(1, cart[key] - 1)
        elif quantity is not None:
            cart[key] = max(1, quantity)

    return save_cart_to_cookie(redirect(url_for('front.front_store.cart')), cart)


@front_store_bp.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if not session.get("user_id"):
        flash("Please login first to checkout.", "warning")
        return redirect(url_for("auth.login", next=request.path))

    cart_data = get_cart_from_cookie()
    cart_items = []
    total = 0.0
    for product_id_str, qty in cart_data.items():
        if product_id_str.isdigit():
            product_item = next((p for p in products_data if p['id'] == int(product_id_str)), None)
            if product_item:
                subtotal = float(product_item.get('price', 0)) * qty
                cart_items.append({'product': product_item, 'quantity': qty, 'subtotal': subtotal})
                total += subtotal

    if not cart_items and request.method == 'GET':
        flash("កន្ត្រកទំនិញរបស់អ្នកទទេស្អាត!", "warning")
        return redirect(url_for('front.front_store.cart'))

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        notes = request.form.get('notes', '').strip()

        if not full_name or not phone or not address:
            flash('សូមបំពេញព័ត៌មានដែលចាំបាច់ឱ្យបានគ្រប់!!', 'danger')
            return render_template('front/checkout.html', cart_items=cart_items, total=total)

        tax = total * 0.08
        grand = total + tax
        order_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        products_lines = '\n'.join(
            [f"  • {item['product']['title']} x{item['quantity']} — ${item['subtotal']:.2f}" for item in cart_items])

        telegram_text = (
            f"🛒 <b>NEW ORDER RECEIVED!</b>\n\n"
            f"👤 <b>Customer:</b> {full_name}\n"
            f"📞 <b>Phone:</b> {phone}\n"
            f"📍 <b>Address:</b> {address}\n"
            f"📝 <b>Notes:</b> {notes or '—'}\n\n"
            f"🛍 <b>Products:</b>\n{products_lines}\n\n"
            f"💵 <b>Subtotal:</b> ${total:.2f}\n"
            f"🧾 <b>Tax (8%):</b> ${tax:.2f}\n"
            f"💰 <b>Grand Total:</b> ${grand:.2f}\n"
            f"🕐 <b>Order Time:</b> {order_time}"
        )

        send_telegram_message(telegram_text)

        flash('ការបញ្ជាទិញបានជោគជ័យ! អរគុណសម្រាប់ការគាំទ្រ។', 'success')
        response = make_response(redirect(url_for('front.front_store.home')))
        response.set_cookie('cart', '', max_age=0, expires=0)
        return response

    return render_template('front/checkout.html', cart_items=cart_items, total=total)


@front_store_bp.route('/wishlist')
@front_store_bp.route('/wishlist/<int:id>')
@front_store_bp.route('/add-to-wishlist/<int:id>')
@front_store_bp.route('/add_to_wishlist/<int:id>')
@front_store_bp.route('/favourite')
@front_store_bp.route('/favourite/<int:id>')
@front_store_bp.route('/favorite')
@front_store_bp.route('/favorite/<int:id>')
def wishlist(id=None):
    if not session.get("user_id"):
        flash("Please login first to add products to your wishlist.", "warning")
        return redirect(url_for("auth.login", next=request.path))
    if id:
        flash("Product added to your wishlist!", "success")
        return redirect(url_for("front.front_store.product", id=id))
    flash("Your wishlist.", "info")
    return redirect(url_for("front.front_store.home"))


@front_store_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        subject = request.form.get('subject', '').strip()
        message = request.form.get('message', '').strip()

        if not name or not email or not subject or not message:
            flash('សូមបំពេញគ្រប់ប្រអប់ទិន្នន័យ!', 'danger')
            return render_template('front/contact.html')

        telegram_text = (
            f"📩 <b>New Contact Message</b>\n"
            f"👤 <b>Name:</b> {name}\n"
            f"📧 <b>Email:</b> {email}\n"
            f"📌 <b>Subject:</b> {subject}\n"
            f"💬 <b>Message:</b>\n{message}"
        )
        send_telegram_message(telegram_text)
        flash('សាររបស់អ្នកត្រូវបានផ្ញើរួចរាល់ហើយ!', 'success')
        return redirect(url_for('front.front_store.contact'))

    return render_template('front/contact.html')