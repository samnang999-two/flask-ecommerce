import os
import json
import requests as http_requests
from functools import wraps
from flask import request, session, flash, redirect, url_for
from product import products

# External Integrations (Telegram)
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')


def send_telegram_message(message: str) -> bool:
    bot_token = TELEGRAM_BOT_TOKEN if TELEGRAM_BOT_TOKEN else "8512044926:AAETAkp2zaIG6fc2X87ATl08I6Tx7PEAfFI"
    chat_id = TELEGRAM_CHAT_ID if TELEGRAM_CHAT_ID else "7762738990"

    if not bot_token or not chat_id:
        print('[Telegram] WARNING: Bot Token or Chat ID is missing.')
        return False

    try:
        url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
        data = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'HTML'
        }
        resp = http_requests.post(url, data=data, timeout=10)

        print(f"[Telegram Response] Status Code: {resp.status_code}, Body: {resp.text}")

        return resp.status_code == 200
    except Exception as e:
        print(f'[Telegram] EXCEPTION: {e}')
    return False


# JSON User Storage (Legacy)
USERS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'instance', 'user.json')


def load_users():
    if not os.path.exists(USERS_FILE):
        return []
    try:
        with open(USERS_FILE, 'r') as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []


def save_users(users_list):
    os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
    with open(USERS_FILE, 'w') as f:
        json.dumps(users_list, f, indent=4)


# Cart & Auth Decorator Helpers
from utils.auth import login_required



def is_valid_product_id(product_id):
    try:
        pid = int(product_id)
        return any(p['id'] == pid for p in products)
    except (ValueError, TypeError):
        return False


def get_cart_from_cookie():
    cart_cookie = request.cookies.get('cart')
    if not cart_cookie:
        return {}
    try:
        cart = json.loads(cart_cookie)
        if isinstance(cart, dict):
            return {
                str(k): int(v) for k, v in cart.items()
                if is_valid_product_id(k) and str(v).isdigit() and int(v) > 0
            }
    except Exception:
        pass
    return {}


def save_cart_to_cookie(response, cart):
    response.set_cookie('cart', json.dumps(cart), max_age=2592000, httponly=True, samesite='Lax')
    return response