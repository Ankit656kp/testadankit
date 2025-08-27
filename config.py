import os
from datetime import timedelta

BOT_TOKEN = os.getenv('BOT_TOKEN')
OWNER_ID = int(os.getenv('OWNER_ID'))
OWNER_LOGS_GROUP = os.getenv('OWNER_LOGS_GROUP')  # group id or @username

FORCE_CHANNEL = os.getenv('FORCE_CHANNEL', '@YourChannel')
FORCE_GROUP = os.getenv('FORCE_GROUP', '@YourGroup')

UPI_ID = os.getenv('UPI_ID', 'me@upi')
PAYMENT_QR_URL = os.getenv('PAYMENT_QR_URL', '')
PAYMENT_CONTACT = os.getenv('PAYMENT_CONTACT', '@YourAdmin')

START_IMAGE = os.getenv('START_IMAGE', 'https://files.catbox.moe/thmj4x.jpg')

PLANS = {
    'blaze': {'name': 'Blaze', 'price': '49', 'days': 7, 'max_accounts': 2},
    'pro': {'name': 'Pro', 'price': '99', 'days': 30, 'max_accounts': 6},
    'elite': {'name': 'Elite', 'price': '199', 'days': 90, 'max_accounts': 20},
}

MONGO_URI = os.getenv('MONGO_URI')
DB_NAME = os.getenv('DB_NAME', 'adsbot')

DEFAULT_DELAY_SECONDS = int(os.getenv('DEFAULT_DELAY_SECONDS', '8'))
RANDOMIZE_DELAY = os.getenv('RANDOMIZE_DELAY', 'True').lower() in ['1','true','yes']

BOT_NAME = os.getenv('BOT_NAME', 'AdsBot')
SUPPORT_GROUP = os.getenv('SUPPORT_GROUP', '@support')
UPDATES_LINK = os.getenv('UPDATES_LINK', '@updates')
GUIDE_TELEGRAPH_EN = os.getenv('GUIDE_TELEGRAPH_EN', '')

DAILY_FORWARD_LIMITS = {
    'freemium': 10,
    'blaze': 500,
    'pro': 2000,
    'elite': 10000,
}

SESSIONS_COLLECTION = os.getenv('SESSIONS_COLLECTION', 'sessions')
USERS_COLLECTION = os.getenv('USERS_COLLECTION', 'users')
ORDERS_COLLECTION = os.getenv('ORDERS_COLLECTION', 'orders')
BROADCASTS_COLLECTION = os.getenv('BROADCASTS_COLLECTION', 'broadcasts')
ADMINS = os.getenv('ADMINS', '').split(',') if os.getenv('ADMINS') else []