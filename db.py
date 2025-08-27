from pymongo import MongoClient
import config

client = MongoClient(config.MONGO_URI)
DB = client[config.DB_NAME]

users = DB[config.USERS_COLLECTION]
orders = DB[config.ORDERS_COLLECTION]
sessions = DB[config.SESSIONS_COLLECTION]
broadcasts = DB[config.BROADCASTS_COLLECTION]

# indexes
users.create_index('plan_expire')
orders.create_index('order_id', unique=True)